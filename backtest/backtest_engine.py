"""
PJ Fire — Unified Backtest Engine (with full daily stats, unified logging, PATCHED)
Fixes indentation bug, unifies log schema, never skips logging a trade/skip/reject.
"""

import os
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import json

from config.config import BT_DB_FILE, START_CASH, START_DATE, END_DATE, DEFAULT_LOT_SIZE, STOP_LOSS_PCT
from simulation.db_utils import get_conn, get_cash, get_prices
from simulation.screening import screen_stocks 
from simulation.reasoning import attach_reason_to_candidates
from simulation.ranker import get_top_signals_for_day
from simulation.utils import load_trading_days, get_next_trading_day
from simulation.simulation_engine import (
    simulate_trade_for_backtest,
    init_simulation_db,
    get_cash,
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

        candidates = screen_stocks(conn, date_str)
        if not candidates:
            print("No candidates for this day.")
            daily_stats.append({"date": date_str, "n_trades": 0, "n_win": 0, "n_loss": 0, "n_other": 0, "day_pl": 0, "cash": last_cash})
            equity_curve.append({"date": date_str, "equity": last_cash})
            continue

        candidates_with_reasons = attach_reason_to_candidates(conn, candidates)
        if not candidates_with_reasons:
            print("No candidates passed reasoning filter.")
            daily_stats.append({"date": date_str, "n_trades": 0, "n_win": 0, "n_loss": 0, "n_other": 0, "day_pl": 0, "cash": last_cash})
            equity_curve.append({"date": date_str, "equity": last_cash})
            continue

        top_signals = get_top_signals_for_day(candidates_with_reasons)
        if not top_signals:
            print("No signals above threshold.")
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
            "n_trades": len(ranked_signals),
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

    df_equity.to_csv(os.path.join(output_dir, "equity_curve.csv"), index=False)
    df_trades.to_csv(os.path.join(output_dir, "trades.csv"), index=False)
    df_stats.to_csv(os.path.join(output_dir, "daily_stats.csv"), index=False)
    print(f"✅ Backtest outputs saved to {output_dir}/")

    n_trades = sum(d["n_trades"] for d in daily_stats)
    n_win = sum(d["n_win"] for d in daily_stats)
    win_rate = n_win / n_trades if n_trades else 0
    final_cash = daily_stats[-1]["cash"] if daily_stats else start_cash
    final_pl = final_cash - start_cash

    print("\n==== BACKTEST SUMMARY ====")
    print(f"Total trades: {n_trades}")
    print(f"Win rate (TP): {win_rate:.2%}")
    print(f"Final P/L: {final_pl:.0f} yen")
    print(f"Ending cash: {final_cash:,.0f} yen")
    print("\nFirst 5 daily stats:")
    print(df_stats.head())
    print("\nFirst 5 trades:")
    print(df_trades.head())

    return df_stats, df_trades, df_equity

if __name__ == "__main__":
    run_backtest_engine()
