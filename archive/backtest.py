# backtest/backtest.py

import pandas as pd
from simulation.db_utils import get_conn, get_prices, init_pjfire_tables
from strategies.common.technical import add_indicators
from strategies.mean_reversion.reasoning import categorize_drop_reason

DB_FILE = "backtest/backtest_bt.db"  # Use simulation/pjfire.db for simulation
START_CASH = 1_000_000
TP_COL = "ma5"      # Take profit at MA(5) (change as needed)
SL_PCT = -0.05      # 5% stop loss (e.g., -0.05 = -5%)
HOLD_DAYS = 3
ALLOWED_REASONS = {"Earnings", "Unknown"}

def simulate_trade(row, df, tp_col=TP_COL, sl_pct=SL_PCT, hold_days=HOLD_DAYS):
    entry_idx = row.name + 1
    if entry_idx >= len(df):
        return None  # Can't trade, no next day data

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
        # TP: Price hits MA
        if day["high"] >= day[tp_col]:
            result = "TP"
            exit_price = day[tp_col]
            exit_date = day["date"]
            pl = exit_price - entry_price
            break
        # SL: Price hits stop loss
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

def run_backtest(tickers, start_date, end_date):
    conn = get_conn(DB_FILE)
    init_pjfire_tables(conn)
    stats = []
    filter_stats = {}
    cash = START_CASH

    for ticker in tickers:
        print(f"\n=== {ticker} ===")
        df = get_prices(conn, ticker, start_date, end_date)
        if df.empty: continue
        df = add_indicators(df)
        for idx, row in df.iterrows():
            # Quantitative filter (e.g., RSI<30)
            if row["rsi_14"] < 30:
                # News/GPT filter
                # TODO: fetch real headlines for the date
                reason = categorize_drop_reason([])  # Pass headlines here
                # Track filter stats
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
                print(f"{row['date']}: BUY {ticker} {trade['entry_price']:.2f} → {trade['exit_price']:.2f} {trade['result']} (PL: {trade['pl']:.2f}) [{reason}]")
    conn.close()

    # --- Summary ---
    n = len(stats)
    n_win = sum(1 for t in stats if t["result"]=="TP")
    win_rate = n_win / n if n else 0
    final_pl = cash - START_CASH
    print("\n==== SUMMARY ====")
    print(f"Total trades: {n}")
    print(f"Win rate (TP): {win_rate:.2%}")
    print(f"Final P/L: {final_pl:.0f} yen")
    print("News categorization filter stats (signals that passed quant filter):")
    for reason, count in filter_stats.items():
        pass_count = sum(1 for t in stats if t["reason"]==reason)
        print(f"  {reason}: {count} (trades executed: {pass_count})")

    return stats

if __name__ == "__main__":
    run_backtest(["7203", "9984", "3436"], "2023-01-01", "2024-01-01")
