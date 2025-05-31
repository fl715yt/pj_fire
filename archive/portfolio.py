# simulation/portfolio.py

import sqlite3
import os
from dotenv import load_dotenv
from simulation.db_utils import init_pjfire_tables

load_dotenv()
DB_FILE = os.getenv("PJ_FIRE_DB", "simulation/pjfire.db")  # Use backtest/backtest_bt.db for backtest if needed
PORTFOLIO_TABLE = "portfolio"
CASH_TABLE = "cash"

def init_portfolio():
    """Ensure all necessary tables exist for portfolio and cash management."""
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    conn.close()

# --- POSITION CRUD ---

def add_position(ticker, entry_date, quantity, entry_price, strategy="main"):
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    c = conn.cursor()
    c.execute(f"""
        INSERT OR REPLACE INTO {PORTFOLIO_TABLE} (ticker, entry_date, quantity, entry_price, status, strategy)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ticker, entry_date, quantity, entry_price, "open", strategy))
    conn.commit()
    conn.close()

def close_position(ticker, entry_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"""
        UPDATE {PORTFOLIO_TABLE}
        SET status = 'closed'
        WHERE ticker = ? AND entry_date = ?
    """, (ticker, entry_date))
    conn.commit()
    conn.close()

def get_open_positions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"""
        SELECT ticker, entry_date, quantity, entry_price, strategy FROM {PORTFOLIO_TABLE}
        WHERE status = 'open'
    """)
    rows = c.fetchall()
    conn.close()
    return rows

# --- CASH CRUD ---

def update_cash(amount, as_of_date):
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    c = conn.cursor()
    c.execute(f"""
        INSERT OR REPLACE INTO {CASH_TABLE} (as_of, balance) VALUES (?, ?)
    """, (as_of_date, amount))
    conn.commit()
    conn.close()

def get_latest_cash():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"SELECT balance FROM {CASH_TABLE} ORDER BY as_of DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def get_portfolio_snapshot():
    return {
        "positions": get_open_positions(),
        "cash": get_latest_cash()
    }

# --- TEST ---
if __name__ == "__main__":
    print("[INIT] Portfolio DB setup...")
    init_portfolio()
    print("[ADD] Example position...")
    add_position("7203", "2024-05-10", 100, 3500.5)
    print("[CLOSE] Closing position...")
    close_position("7203", "2024-05-10")
    print("[CASH] Update cash...")
    update_cash(1000000, "2024-05-10")
    print("[SNAPSHOT]")
    print(get_portfolio_snapshot())
