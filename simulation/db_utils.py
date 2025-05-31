"""
PJ Fire — Database Utilities
Handles DB connection and all table setup, using config-defined paths and schema.
"""

import sqlite3
import pandas as pd
from config.config import (
    SIM_DB_FILE,
    BT_DB_FILE,
)

def get_conn(db_path=None):
    """Open a SQLite connection for the specified DB path."""
    if db_path is None:
        db_path = SIM_DB_FILE
    return sqlite3.connect(db_path)

def init_pjfire_tables(conn):
    """Create all unified schema tables if they do not exist."""
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT,
            period_type TEXT,      -- e.g., "FY", "1Q", "2Q", "3Q", "4Q"
            period_end DATE,       -- End date of the fiscal or quarterly period
            revenue REAL,
            eps REAL,
            profit REAL,
            PRIMARY KEY (ticker, period_type, period_end)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            ticker TEXT,
            entry_date TEXT,
            quantity INTEGER,
            entry_price REAL,
            status TEXT,
            strategy TEXT,
            signal_score REAL,
            PRIMARY KEY (ticker, entry_date)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            ticker TEXT,
            quantity INTEGER,
            price REAL,
            trade_type TEXT,
            strategy TEXT,
            reason TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS cash (
            as_of TEXT PRIMARY KEY,
            balance REAL
        )
    """)
    conn.commit()

def insert_prices(conn, df):
    """Insert a DataFrame of daily prices into the unified prices table."""
    df.to_sql("prices", conn, if_exists="append", index=False)

def insert_fundamentals(conn, df):
    """Insert a DataFrame of fundamentals (FY and/or quarterly) into the table."""
    df.to_sql("fundamentals", conn, if_exists="append", index=False)

def get_prices(conn, ticker, start_date=None, end_date=None):
    """Fetch daily prices for a ticker and optional date range."""
    query = "SELECT * FROM prices WHERE ticker = ?"
    params = [ticker]
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [start_date, end_date]
    return pd.read_sql(query, conn, params=params)

def get_fundamentals(conn, ticker, period_type="FY", n=5):
    """
    Fetches up to n most recent fundamentals for a given ticker and period type.
    period_type: "FY" (annual) or "1Q"/"2Q"/"3Q"/"4Q" (quarterly)
    """
    query = """
    SELECT * FROM fundamentals
    WHERE ticker = ?
    AND period_type = ?
    ORDER BY period_end DESC
    LIMIT ?
    """
    df = pd.read_sql(query, conn, params=[ticker, period_type, n])
    return df
    
def get_quarterly_fundamentals(conn, ticker, n=4):
    """
    Fetches up to n most recent quarterly (Q1–Q4) reports for a given ticker.
    """
    query = """
    SELECT * FROM fundamentals
    WHERE ticker = ?
    AND period_type IN ('1Q', '2Q', '3Q', '4Q')
    ORDER BY period_end DESC
    LIMIT ?
    """
    df = pd.read_sql(query, conn, params=[ticker, n])
    return df
