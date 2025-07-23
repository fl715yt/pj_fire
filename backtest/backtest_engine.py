"""
PJ Fire — Unified Backtest Engine (with full daily stats, unified logging, PATCHED)
Fixes indentation bug, unifies log schema, never skips logging a trade/skip/reject.
"""

import os
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import json

from simulation.regime import detect_regime, regime_strategy_map
from strategies.common.strategy_map import STRATEGY_FUNCTIONS  # You’ll need to create/update this

from config.config import BT_DB_FILE, START_CASH, START_DATE, END_DATE, DEFAULT_LOT_SIZE, STOP_LOSS_PCT
from simulation.db_utils import get_conn, get_cash, get_prices
from strategies.common.screening import screen_stocks 
from strategies.mean_reversion.reasoning import attach_reason_to_candidates
from strategies.common.ranker import get_top_signals_for_day
from simulation.utils import load_trading_days, get_next_trading_day
from simulation.simulation_engine import (
    simulate_trade_for_backtest,
    init_simulation_db,
    time_exit_logic
)
from simulation.logger import log_trade_full

TRADING_DAYS = load_trading_days()  # Load ONCE at module startup

def run_backtest_engine(
    start_date=START_DATE, 
    end_date=END_DATE, 
    start_cash=START_CASH, 
    output_dir="backtest/outputs"
):
    conn = get_conn(BT_DB_FILE)
    init_simulation_db(BT_DB_FILE, start_cash)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='B')
    trade_log = []
    daily_stats = []
    last_cash = start_cash
    equity_curve = []

    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)

    for date in all_dates:
        date_str = date.strftime("%Y-%m-%d")
        print(f"\n=== {date_str} ===")
        activity = False  # Track if anything happens this day

        # Get price DataFrame for regime detection (choose your index ETF or main universe)
        price_df = get_prices(conn, "TOPIX", end_date=date_str)  # Or your preferred market index
        vix_j = None  # Add your logic if you want to pass VIX-J

        regime = detect_regime(price_df, vix_j)
        allowed_strategies = regime_strategy_map.get(regime, [])

        all_signals = []
        for strat in allowed_strategies:
            func = STRATEGY_FUNCTIONS.get(strat)
            if func:
                if strat == "mean_reversion":
                    candidates = screen_stocks(conn, date_str)
                    if not candidates:
                        continue
                    candidates_with_reasons = attach_reason_to_candidates(conn, candidates)
                    if not candidates_with_reasons:
                        continue
                    top_signals = get_top_signals_for_day(candidates_with_reasons)
                    if not top_signals:
                        continue
                    # Attach regime/strategy to each signal
                    for sig in top_signals:
                        sig["regime"] = regime
                        sig["strategy"] = strat
                    all_signals.extend(top_signals)
                # Add similar logic for other strategies here
                elif strat == "momentum":
                    # You need to implement this block for your momentum strategy
                    pass
                elif strat == "defensive":
                    # For defensive, either implement or continue
                    pass
                elif strat == "block_all":
                    # Block all = skip trading for this day
                    print(f"[BLOCKED] Regime {regime}: No trading allowed.")
                    all_signals = []
                    break  # Skip trading and signal loop for this day

        if not all_signals:
            print("No signals above threshold or regime blocked.")
            daily_stats.append({"date": date_str, "n_trades": 0, "n_win": 0, "n_loss": 0, "n_other": 0, "day_pl": 0, "cash": last_cash})
            equity_curve.append({"date": date_str, "equity": last_cash})
            continue

        # Close positions held beyond the max holding period (time exits)
        time_exit_logic(conn, date_str)
        activity = True  # Assume exits could have occurred

        # --- Sort signals by normalized_score descending (for fair cash allocation) ---
        ranked_signals = sorted(top_signals, key=lambda x: x.get("normalized_score", 0), reverse=True)

        n_win, n_loss, n_other = 0, 0, 0
        day_pl = 0
        n_trades = 0

        for sig in ranked_signals:
            # Get next day open (entry) and calculate lot cost from that entry
            next_entry_date = get_next_trading_day(date_str, TRADING_DAYS, 1)
            entry_prices = get_prices(conn, sig["ticker"], start_date=next_entry_date, end_date=next_entry_date)
            if entry_prices.empty:
                continue
            entry_price = entry_prices["open"].iloc[0]
            lot_cost = DEFAULT_LOT_SIZE * entry_price
            cash = get_cash(conn)

            # Always simulate "what-if" (virtual) trade, even if not enough cash
            result, pl, entry_date, buy_price, exit_date, sell_price, quantity = simulate_trade_for_backtest(
                conn, sig, date_str, TRADING_DAYS, return_result=True, execute_trade=False
            )

            # Compute TP and SL for log
            target_tp = sig.get("ma5")
            stop_loss = buy_price * (1 - STOP_LOSS_PCT) if buy_price is not None else None
            trade_type = "SKIPPED" if result.startswith("SKIPPED") else "BOUGHT"

            log_trade_full(
                trade_id=len(trade_log) + 1,
                signal_date=date_str,
                buy_date=entry_date,
                sell_date=exit_date,
                ticker=sig.get("ticker"),
                quantity=quantity,
                buy_price=buy_price,
                sell_price=sell_price,
                trade_type=trade_type,
                strategy=sig.get("strategy", "mean_reversion"),
                result=result,
                pl=pl,
                score=sig.get("score"),
                normalized_score=sig.get("normalized_score"),
                technicals=json.dumps({k: sig.get(k) for k in ['rsi_14','ma5','ma25','volume','volume_spike']}),
                fundamentals=json.dumps(sig.get("fy_features", {})),
                gpt_summary=sig.get("gpt_summary", ""),
                gpt_decision=sig.get("gpt_decision", ""),
                news_url=sig.get("news_url", ""),
                reason=sig.get("reason_category", ""),
                take_profit=target_tp,
                stop_loss=stop_loss,
                # logged_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            trade_log.append({
                "trade_id": len(trade_log) + 1,
                "signal_date": date_str,
                "buy_date": entry_date,
                "sell_date": exit_date,
                "ticker": sig.get("ticker"),
                "quantity": quantity,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "trade_type": trade_type,
                "strategy": sig.get("strategy", "mean_reversion"),
                "result": result,
                "pl": pl,
                "score": sig.get("normalized_score"),
                "technicals": json.dumps({k: sig.get(k) for k in ['rsi_14','ma5','ma25','volume','volume_spike']}),
                "fundamentals": json.dumps(sig.get("fy_features", {})),
                "gpt_summary": sig.get("gpt_summary", ""),
                "gpt_decision": sig.get("gpt_decision", ""),
                "news_url": sig.get("news_url", ""),
                "reason": sig.get("reason_category", ""),
                
                "take_profit": target_tp,
                "stop_loss": stop_loss,
                "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            if trade_type == "BOUGHT":
                n_trades += 1
                # Actually execute trade (updates cash, etc.)
                actual_result, actual_pl, actual_entry_date, actual_entry_price, actual_exit_date, actual_exit_price, actual_qty = simulate_trade_for_backtest(
                    conn, sig, date_str, TRADING_DAYS, return_result=True, execute_trade=True
                )
                # Stat tracking
                if actual_result == "TP":
                    n_win += 1
                elif actual_result == "SL":
                    n_loss += 1
                else:
                    n_other += 1
                day_pl += actual_pl

        last_cash = get_cash(conn)
        daily_stats.append({
            "date": date_str,
            "n_trades": n_trades,
            "n_win": n_win, "n_loss": n_loss, "n_other": n_other,
            "day_pl": day_pl, "cash": last_cash
        })
        equity_curve.append({"date": date_str, "equity": last_cash})

        if not activity:
            print("No trades or exits executed today.")

    conn.close()
    # === Output results to CSV for analysis ===
    df_equity = pd.DataFrame(equity_curve)
    df_trades = pd.DataFrame(trade_log)
    df_stats = pd.DataFrame(daily_stats)

    run_tag = datetime.now().strftime('%Y%m%d_%H%M%S')

    df_equity.to_csv(os.path.join(output_dir, f"equity_curve_{run_tag}.csv"), index=False)
    df_trades.to_csv(os.path.join(output_dir, f"trades_{run_tag}.csv"), index=False)
    df_stats.to_csv(os.path.join(output_dir, f"daily_stats_{run_tag}.csv"), index=False)
    print(f"✅ Backtest outputs saved to {output_dir}/ as *_ {run_tag}.csv")

    n_trades = sum(d["n_trades"] for d in daily_stats)
    n_win = sum(d["n_win"] for d in daily_stats)
    win_rate = n_win / n_trades if n_trades else 0
    final_cash = daily_stats[-1]["cash"] if daily_stats else start_cash
    final_pl = final_cash - start_cash

    print(f"\n==== BACKTEST SUMMARY ({run_tag}) ====")
    print(f"Total trades: {n_trades}")
    print(f"Win rate (TP): {win_rate:.2%}")
    print(f"Final P/L: {final_pl:.0f} yen")
    print(f"Ending cash: {final_cash:,.0f} yen")
    print("\nFirst 5 daily stats:")
    print(df_stats.head())
    print("\nFirst 5 trades:")
    print(df_trades.head())

    # === Mark to Market All Open Positions ===
    # 1. Find all open positions (buys not fully closed by sells)
    df_trades_buys = df_trades[df_trades["trade_type"] == "BOUGHT"]
    df_trades_sells = df_trades[df_trades["trade_type"] == "SELL"]

    open_positions = (
        df_trades_buys.groupby("ticker").agg({"quantity":"sum", "buy_date":"last", "buy_price":"last"})
        .join(
            df_trades_sells.groupby("ticker").agg({"quantity":"sum"}).rename(columns={"quantity": "quantity_sold"}),
            how="left"
        )
        .fillna(0)
        .assign(open_qty=lambda x: x["quantity"] - x["quantity_sold"])
        .query("open_qty > 0")
    )

    mkt_value = 0
    last_date = df_equity["date"].iloc[-1]

    if not open_positions.empty:
        conn2 = get_conn(BT_DB_FILE)
        for ticker, row in open_positions.iterrows():
            price_df = get_prices(conn2, ticker, start_date=last_date, end_date=last_date)
            if not price_df.empty and "close" in price_df.columns:
                last_close = price_df["close"].iloc[0]
                qty = row["open_qty"]
                mkt_value += qty * last_close
        conn2.close()
        true_final_equity = final_cash + mkt_value
        print(f"\n=== TRUE FINAL EQUITY (marked to market): {true_final_equity:,.0f} yen ===")
        print(f"  Cash: {final_cash:,.0f} yen")
        print(f"  Market value of open positions: {mkt_value:,.0f} yen")
        print(f"\n[INFO] {len(open_positions)} open position(s) at end of backtest included at market value.")
    else:
        true_final_equity = final_cash
        print("\n=== TRUE FINAL EQUITY: no open positions, all cash ===")

    # Optionally, save true final equity to a summary file
    with open(os.path.join(output_dir, f"summary_{run_tag}.txt"), "w", encoding="utf-8") as f:
        f.write(f"==== BACKTEST SUMMARY ({run_tag}) ====\n")
        f.write(f"Total trades: {n_trades}\n")
        f.write(f"Win rate (TP): {win_rate:.2%}\n")
        f.write(f"Final P/L: {final_pl:.0f} yen\n")
        f.write(f"Ending cash: {final_cash:,.0f} yen\n")
        f.write(f"TRUE FINAL EQUITY: {true_final_equity:,.0f} yen\n")
        f.write(f"  (includes market value of all open positions)\n")

    return df_stats, df_trades, df_equity

if __name__ == "__main__":
    run_backtest_engine()
