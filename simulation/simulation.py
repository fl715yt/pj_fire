# simulation/simulation.py

import sqlite3
from datetime import datetime
from simulation.db_utils import init_pjfire_tables
from simulation.portfolio import add_position, close_position, update_cash, get_latest_cash

DB_FILE = "simulation/pjfire.db"  # Or use os.getenv("PJ_FIRE_DB") for more flexibility

def execute_trade(ticker, quantity, price, trade_type, strategy, reason):
    """
    Executes a trade and logs it into trades table,
    then updates portfolio and cash tables.
    """
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    cur = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Insert trade into log
    cur.execute("""
        INSERT INTO trades (
            datetime, ticker, quantity, price, trade_type, strategy, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now, ticker, quantity, price, trade_type, strategy, reason))

    # Update portfolio & cash
    today = datetime.now().strftime("%Y-%m-%d")
    cash = get_latest_cash()
    if trade_type == "buy":
        add_position(ticker, today, quantity, price, strategy)
        update_cash(cash - quantity * price, today)
    elif trade_type == "sell":
        close_position(ticker, today)
        update_cash(cash + quantity * price, today)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    # 🔧 Example manual test run
    execute_trade(
        ticker="7203",
        quantity=100,
        price=2000,
        trade_type="buy",
        strategy="mean_reversion",
        reason="Oversold with good fundamentals"
    )
