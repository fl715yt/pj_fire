# simulation/execution.py
"""
Handles trade execution for simulation (calls portfolio, logs trades).
Separates execution from simulation_engine for modularity and testability.
"""

from simulation.logger import log_trade, log_warning
from simulation.portfolio import Portfolio

def execute_trade(portfolio: Portfolio, ticker, side, qty, price, score, date, reason=""):
    if side == "BUY":
        result = portfolio.buy(ticker, qty, date, price, score)
    elif side == "SELL":
        result = portfolio.sell(ticker, date, price, reason)
    else:
        log_warning(f"Unknown trade side: {side}")
        return False

    if result:
        log_trade(ticker, side, price, qty, score, date, reason)
    else:
        log_warning(f"Failed to execute {side} for {ticker} on {date}")
    return result
