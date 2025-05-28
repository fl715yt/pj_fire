"""
PJ Fire — Simulation Engine

Orchestrates daily/weekly simulation runs.
Runs screening, ranking, trade execution, and logs performance.
"""

from core.screen_stocks import screen_stocks
from core.ranker import rank_stocks
from core.execution import execute_trade
from config.config import DEFAULT_LOT_SIZE, MAX_SIGNAL_PER_DAY
from utils.logger import log_info

def run_daily_simulation(date):
    """
    Main entry for one simulation day.
    Screens, ranks, and executes up to MAX_SIGNAL_PER_DAY trades.
    """
    log_info(f"=== Running PJ Fire Simulation for {date} ===")
    candidates = screen_stocks(date)
    ranked = rank_stocks(candidates)

    n_trades = 0
    for stock in ranked:
        if n_trades >= MAX_SIGNAL_PER_DAY:
            break

        ticker = stock["ticker"]
        price = stock["close"]  # Or opening price, per your strategy
        qty = DEFAULT_LOT_SIZE  # Extend with dynamic sizing if needed
        # Insert further trade entry checks here (TP/SL, available cash, risk, etc.)

        executed = execute_trade("buy", ticker, qty, price, reason="simulation_signal")
        if executed:
            n_trades += 1

    log_info(f"Simulation: Executed {n_trades} trades for {date}.")

def run_weekly_summary():
    """
    Placeholder: Summarize weekly performance, P/L, hit ratio, etc.
    Extend as needed for reporting.
    """
    # Example: Aggregate sim_trades by week, report stats.
    log_info("Weekly summary not implemented yet.")

# Example usage:
# run_daily_simulation("2024-05-17")
# run_weekly_summary()

