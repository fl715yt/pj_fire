# backtest/backtest_engine.py
"""
PJ Fire — Unified Backtest Engine (Batch Orchestrator)
Runs multi-day, multi-ticker backtest using unified schema.
- Loads historical prices/fundamentals for each day
- Calls signal ranking (custom or via simulation.ranker)
- Simulates trades, tracks portfolio/cash, forced exits, and logs trades
- Outputs daily and final results
"""

import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from simulation.db_utils import init_pjfire_tables, get_conn, get_prices
from simulation.ranker import rank_candidates
from simulation.portfolio import add_position, close_position, update_cash, get_latest_cash, get_open_positions
from technical_bt import add_indicators
from reasoning_bt import categorize_drop_reason

DB_FILE = "backtest/backtest_bt.db"
START_CASH = 1_000_000
START_DATE = "2024-01-01"
END_DATE = "2024-05-24"
TP_COL = "ma5"
SL_PCT = -0.05
HOLD_DAYS = 3
ALLOWED_REASONS = {"Earnings", "Unknown"}

def simulate_trade(row, df, tp_col=TP_COL, sl_pct=SL_PCT, hold_days=HOLD_DAYS):
    entry_idx = row.name + 1
    if entry_idx >= len(df):
        return None
    entry_price = df.iloc[entry_idx]["open"]
    entry_date = df.iloc[entry_idx]["date"]
    exit_price = df.iloc[min(entry_idx+hold_days-1, len(df)-1)]["close"]
    exit_date = df.iloc[min(entry_idx+hold_days-1, len(df)-1)]["date"]
    result = "Timeout"
    pl = exit_price - entry_price

    for offset in range(hold_days):
        if entry_idx+offset >= len(df):
            break
        day = df.iloc[entry_idx+offset]
        if day["high"] >= day[tp_col]:
            result = "TP"
            exit_price = day[tp_col]
            exit_date = day["date"]
            pl = exit_price - entry_price
            break
        if day["low"] <= entry_price * (1 + sl_pct):
            result = "SL"
            exit_price = entry_price * (1 + sl_pct)
            exit_date = day["date"]
            pl = exit_price - entry_price
            break

    return {
        "entry_date": entry_date,
        "entry_price": entry_price,
        "exit_date": exit_date,
        "exit_price": exit_price,
        "pl": pl,
        "result": result
    }

def run_backtest_engine(tickers, start_date=START_DATE, end_date=END_DATE, start_cash=START_CASH):
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    # Reset state
    conn.execute("DELETE FROM portfolio")
    conn.execute("DELETE FROM trades")
    conn.execute("DELETE FROM cash")
    now = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT OR REPLACE INTO cash (as_of, balance) VALUES (?, ?)", (now, start_cash))
    conn.commit()
    cash = start_cash

    all_dates = pd.date_range(start=start_date, end=end_date, freq='B')
    stats = []
    filter_stats = {}

    for ticker in tickers:
        df = get_prices(conn, ticker, start_date, end_date)
        if df.empty: continue
        df = add_indicators(df)
        for idx, row in df.iterrows():
            # Quant filter
            if row["rsi_14"] < 30:
                # News filter
                reason = categorize_drop_reason([])  # TODO: real headlines if available
                filter_stats.setdefault(reason, 0)
                filter_stats[reason] += 1
                if reason not in ALLOWED_REASONS:
                    continue
                # Simulate trade
                trade = simulate_trade(row, df)
                if not trade: continue
                trade.update({
                    "ticker": ticker,
                    "signal_date": row["date"],
                    "rsi_14": row["rsi_14"],
                    "reason": reason
                })
                cash += trade["pl"]
                stats.append(trade)
                add_position(ticker, trade["entry_date"], 100, trade["entry_price"])
                update_cash(cash, trade["entry_date"])
                close_position(ticker, trade["exit_date"])
                update_cash(cash, trade["exit_date"])
                print(f"{row['date']}: BUY {ticker} {trade['entry_price']:.2f} → {trade['exit_price']:.2f} {trade['result']} (PL: {trade['pl']:.2f}) [{reason}]")

    conn.close()
    # Summary
    n = len(stats)
    n_win = sum(1 for t in stats if t["result"]=="TP")
    win_rate = n_win / n if n else 0
    final_pl = cash - start_cash
    print("\n==== FINAL SUMMARY ====")
    print(f"Total trades: {n}")
    print(f"Win rate (TP): {win_rate:.2%}")
    print(f"Final P/L: {final_pl:.0f} yen")
    print("News categorization filter stats (signals that passed quant filter):")
    for reason, count in filter_stats.items():
        pass_count = sum(1 for t in stats if t["reason"]==reason)
        print(f"  {reason}: {count} (trades executed: {pass_count})")
    return stats

if __name__ == "__main__":
    run_backtest_engine(["7203", "9984", "3436"], START_DATE, END_DATE)
