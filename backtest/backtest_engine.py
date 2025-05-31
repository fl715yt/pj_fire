"""
PJ Fire — Unified Backtest Engine (with full daily stats and reporting)
"""

import os
import pandas as pd
from datetime import datetime
from config.config import BT_DB_FILE, START_CASH, START_DATE, END_DATE  # <- centralize config
from simulation.db_utils import get_conn
from simulation.screening import screen_stocks
from simulation.reasoning import attach_reason_to_candidates
from simulation.ranker import get_top_signals_for_day
from simulation.simulation_engine import simulate_trade_for_backtest, init_simulation_db, get_cash

def run_backtest_engine(start_date=START_DATE, end_date=END_DATE, start_cash=START_CASH):
    conn = get_conn(BT_DB_FILE)
    init_simulation_db(BT_DB_FILE)  # Ensure backtest DB is initialized
    all_dates = pd.date_range(start=start_date, end=end_date, freq='B')
    trade_log = []
    daily_stats = []
    last_cash = start_cash

    for date in all_dates:
        date_str = date.strftime("%Y-%m-%d")
        print(f"\n=== {date_str} ===")
        candidates = screen_stocks(conn, date_str)
        if not candidates:
            print("No candidates for this day.")
            daily_stats.append({"date": date_str, "n_trades": 0, "n_win": 0, "n_loss": 0, "n_other": 0, "day_pl": 0, "cash": last_cash})
            continue
        candidates_with_reasons = attach_reason_to_candidates(conn, candidates)
        if not candidates_with_reasons:
            print("No candidates passed reasoning filter.")
            daily_stats.append({"date": date_str, "n_trades": 0, "n_win": 0, "n_loss": 0, "n_other": 0, "day_pl": 0, "cash": last_cash})
            continue
        top_signals = get_top_signals_for_day(candidates_with_reasons)
        if not top_signals:
            print("No signals above threshold.")
            daily_stats.append({"date": date_str, "n_trades": 0, "n_win": 0, "n_loss": 0, "n_other": 0, "day_pl": 0, "cash": last_cash})
            continue

        n_win, n_loss, n_other = 0, 0, 0
        day_pl = 0
        for sig in top_signals:
            result, pl = simulate_trade_for_backtest(conn, sig, date_str, return_result=True)
            trade_log.append({**sig, "date": date_str, "result": result, "pl": pl})
            if result == "TP":
                n_win += 1
            elif result == "SL":
                n_loss += 1
            else:
                n_other += 1
            day_pl += pl
        last_cash = get_cash(conn)
        daily_stats.append({
            "date": date_str, "n_trades": len(top_signals),
            "n_win": n_win, "n_loss": n_loss, "n_other": n_other,
            "day_pl": day_pl, "cash": last_cash
        })

    conn.close()

    # === End of backtest summary ===
    n_trades = sum(d["n_trades"] for d in daily_stats)
    n_win = sum(d["n_win"] for d in daily_stats)
    n_loss = sum(d["n_loss"] for d in daily_stats)
    win_rate = n_win / n_trades if n_trades else 0
    final_cash = daily_stats[-1]["cash"] if daily_stats else start_cash
    final_pl = final_cash - start_cash

    print("\n==== BACKTEST SUMMARY ====")
    print(f"Total trades: {n_trades}")
    print(f"Win rate (TP): {win_rate:.2%}")
    print(f"Final P/L: {final_pl:.0f} yen")
    print(f"Ending cash: {final_cash:,.0f} yen")
    print("\nFirst 5 daily stats:")
    print(pd.DataFrame(daily_stats).head())
    print("\nFirst 5 trades:")
    print(pd.DataFrame(trade_log).head())

    return daily_stats, trade_log

if __name__ == "__main__":
    run_backtest_engine()
