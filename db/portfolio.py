"""
PJ Fire — Simulation Portfolio State Management

Handles portfolio holdings and cash balance for simulation.
All DB I/O is routed via db_utils for consistency and safety.
"""

from db.db_utils import get_db_connection, execute_query
from config.config import SIM_DB_PATH

# === Portfolio Cash Tracking ===

def get_cash_balance():
    """Returns current simulation cash balance (default to 1,000,000 if none set)."""
    query = "SELECT amount FROM cash_balance WHERE id = 1"
    result = execute_query(query, simulation=True)
    if result and result[0][0] is not None:
        return float(result[0][0])
    else:
        # Default starting cash
        return 1_000_000.0

def set_cash_balance(amount):
    """Sets the simulation cash balance (idempotent)."""
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cash_balance (id, amount) VALUES (1, ?)", (amount,)
        )
        conn.commit()

# === Portfolio Holdings Management ===

def get_all_holdings():
    """Returns all portfolio holdings as a list of dicts."""
    query = "SELECT ticker, qty, avg_price FROM portfolio"
    result = execute_query(query, simulation=True)
    holdings = [
        {"ticker": r[0], "qty": r[1], "avg_price": r[2]} for r in result
    ]
    return holdings

def get_holding(ticker):
    """Get specific ticker holding (qty, avg_price) or None."""
    query = "SELECT qty, avg_price FROM portfolio WHERE ticker = ?"
    result = execute_query(query, (ticker,), simulation=True)
    if result:
        return {"qty": result[0][0], "avg_price": result[0][1]}
    else:
        return None

def update_holding(ticker, qty, avg_price):
    """Add/update holding for a ticker."""
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO portfolio (ticker, qty, avg_price, last_update) VALUES (?, ?, ?, DATE('now'))",
            (ticker, qty, avg_price),
        )
        conn.commit()

def delete_holding(ticker):
    """Remove a holding (when position is fully sold)."""
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM portfolio WHERE ticker = ?", (ticker,)
        )
        conn.commit()

# Example usage:
# from db.portfolio import get_cash_balance, set_cash_balance, get_all_holdings, update_holding, delete_holding

