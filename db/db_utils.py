"""
PJ Fire — Central Database Utilities

Handles SQLite connections, schema creation, and query utilities.
Supports both simulation and backtest databases via config.
"""

import sqlite3
from contextlib import contextmanager
from config.config import SIM_DB_PATH, BT_DB_PATH

# === Context Manager for DB Connections ===
@contextmanager
def get_db_connection(simulation=True):
    """Context-managed DB connection (auto-close)."""
    db_path = SIM_DB_PATH if simulation else BT_DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()

# === Schema Initialization (One-time Setup) ===
def initialize_db(simulation=True):
    """
    Initialize database schema.
    Extend this with CREATE TABLE statements as needed.
    """
    schema = """
    CREATE TABLE IF NOT EXISTS stock_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        UNIQUE(ticker, date)
    );
    CREATE TABLE IF NOT EXISTS stock_fundamentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        fiscal_year TEXT NOT NULL,
        net_sales REAL,
        eps REAL,
        profit REAL,
        UNIQUE(ticker, fiscal_year)
    );
    CREATE TABLE IF NOT EXISTS sim_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        trade_type TEXT NOT NULL, -- buy/sell/forced_exit etc
        reason TEXT,
        UNIQUE(ticker, trade_date, trade_type)
    );
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        qty INTEGER NOT NULL,
        avg_price REAL NOT NULL,
        last_update TEXT NOT NULL,
        UNIQUE(ticker)
    );
    """
    with get_db_connection(simulation) as conn:
        cursor = conn.cursor()
        for statement in schema.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)
        conn.commit()

# === General Query Utility (if needed) ===
def execute_query(query, params=None, simulation=True):
    """
    Execute any query (DML/DDL) with optional params.
    Returns cursor.fetchall() result.
    """
    with get_db_connection(simulation) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        if query.strip().lower().startswith("select"):
            return cursor.fetchall()
        conn.commit()
        return None

# Example usage:
# from db.db_utils import initialize_db, execute_query, get_db_connection

