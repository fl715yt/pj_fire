# db_utils.py

import sqlite3
import pandas as pd

def get_conn(db_path):
    """Open a SQLite connection for the specified DB path."""
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
            fiscal_year TEXT,
            revenue REAL,
            eps REAL,
            profit REAL,
            PRIMARY KEY (ticker, fiscal_year)
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
    """Insert a DataFrame of annual fundamentals into the unified fundamentals table."""
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
    AND TypeOfCurrentPeriod = ?
    ORDER BY fiscal_year DESC, CurrentPeriodEndDate DESC
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
    AND TypeOfCurrentPeriod IN ('1Q', '2Q', '3Q', '4Q')
    ORDER BY CurrentPeriodEndDate DESC
    LIMIT ?
    """
    df = pd.read_sql(query, conn, params=[ticker, n])
    return df