"""
PJ Fire — Trade Execution Module

Handles simulated trade executions: entry, exit, forced exit.
Updates holdings and cash in the simulation portfolio.
"""

from db.portfolio import (
    get_cash_balance, set_cash_balance, 
    get_holding, update_holding, delete_holding
)
from db.db_utils import get_db_connection
from utils.logger import log_info, log_warning, log_error
from config.config import DEFAULT_LOT_SIZE

def execute_trade(trade_type, ticker, qty, price, reason=None):
    """
    Execute a buy/sell/forced_exit trade, update holdings and cash.
    Logs all trades to sim_trades table.
    """
    cash = get_cash_balance()
    if trade_type == "buy":
        cost = qty * price
        if cost > cash:
            log_warning(f"Insufficient cash for buy: {ticker} x {qty} at {price}")
            return False

        # Update holdings
        holding = get_holding(ticker)
        if holding:
            total_qty = holding["qty"] + qty
            total_cost = holding["avg_price"] * holding["qty"] + price * qty
            avg_price = total_cost / total_qty
        else:
            total_qty = qty
            avg_price = price
        update_holding(ticker, total_qty, avg_price)
        set_cash_balance(cash - cost)

    elif trade_type in ("sell", "forced_exit"):
        holding = get_holding(ticker)
        if not holding or holding["qty"] < qty:
            log_warning(f"Not enough shares to {trade_type}: {ticker} x {qty}")
            return False
        # Update holdings
        new_qty = holding["qty"] - qty
        if new_qty > 0:
            update_holding(ticker, new_qty, holding["avg_price"])
        else:
            delete_holding(ticker)
        set_cash_balance(cash + qty * price)
    else:
        log_warning(f"Invalid trade_type: {trade_type}")
        return False

    # Log trade in DB
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sim_trades
                (ticker, trade_date, qty, price, trade_type, reason)
            VALUES (?, DATE('now'), ?, ?, ?, ?)
            """,
            (ticker, qty, price, trade_type, reason)
        )
        conn.commit()
    log_info(f"Executed {trade_type} trade: {ticker} x {qty} at {price}. Reason: {reason}")
    return True

# Example usage:
# execute_trade("buy", "7203", 100, 1880)
# execute_trade("sell", "7203", 100, 1920, reason="TP hit")

