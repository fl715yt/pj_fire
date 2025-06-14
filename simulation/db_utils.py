"""
PJ Fire — Database Utilities (PATCHED, CASH-LOGIC AUDITED)
Handles DB connection and all table setup, using config-defined paths and schema.
No duplicate or conflicting cash/portfolio logic.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from config.config import (
    SIM_DB_FILE,
    BT_DB_FILE,
    START_CASH,    # PATCH: Use only START_CASH from config, never DEFAULT_CASH
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
            period_type TEXT,
            period_end DATE,
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
            regime TEXT,
            PRIMARY KEY (ticker, entry_date, strategy, regime)
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
            regime TEXT,
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
    """Insert or update daily prices, avoiding duplicates and ensuring freshest data."""
    df = df.drop_duplicates(subset=["date", "ticker"])
    records = df.to_dict(orient="records")
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR REPLACE INTO prices
        (date, ticker, open, high, low, close, volume)
        VALUES (:date, :ticker, :open, :high, :low, :close, :volume)
    """, records)
    conn.commit()

def insert_fundamentals(conn, df):
    """Insert a DataFrame of fundamentals (FY and/or quarterly) into the table."""
    for _, row in df.iterrows():
        try:
            conn.execute("""
                INSERT OR REPLACE INTO fundamentals 
                    (ticker, period_type, period_end, revenue, eps, profit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (row['ticker'], row['period_type'], row['period_end'], row['revenue'], row['eps'], row['profit']))
        except Exception as e:
            print(f"[WARN] Insert failed for {row['ticker']} {row['period_type']} {row['period_end']}: {e}")
    conn.commit()

def get_prices(conn, ticker, start_date=None, end_date=None):
    """Fetch daily prices for a ticker and optional date range."""
    query = "SELECT * FROM prices WHERE ticker = ?"
    params = [ticker]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    df = pd.read_sql(query, conn, params=params)
    return df

def get_fundamentals(conn, ticker, period_type="FY", n=5):
    """Fetches up to n most recent fundamentals for a given ticker and period type."""
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
    """Fetches up to n most recent quarterly (1Q–4Q) reports for a given ticker."""
    query = """
    SELECT * FROM fundamentals
    WHERE ticker = ?
    AND period_type IN ('1Q', '2Q', '3Q', '4Q')
    ORDER BY period_end DESC
    LIMIT ?
    """
    df = pd.read_sql(query, conn, params=[ticker, n])
    return df

def get_cash(conn):
    """Fetch the latest cash balance from the cash table. If empty, initialize with START_CASH."""
    query = "SELECT balance FROM cash ORDER BY as_of DESC LIMIT 1"
    cur = conn.cursor()
    cur.execute(query)
    row = cur.fetchone()
    if row:
        return float(row[0])
    else:
        # PATCH: Initialize with START_CASH and today's date
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO cash (as_of, balance) VALUES (?, ?)", (now, float(START_CASH)))
        conn.commit()
        return float(START_CASH)

def update_cash(conn, delta):
    """
    Update the cash balance by a delta (positive or negative).
    Appends a new record with the current timestamp as 'as_of'.
    Ensures unique as_of values (microseconds appended).
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # PATCH: microseconds for unique PK
    cur = conn.cursor()
    cur.execute("SELECT balance FROM cash ORDER BY as_of DESC LIMIT 1")
    row = cur.fetchone()
    prev = float(row[0]) if row else float(START_CASH)
    new_balance = prev + delta
    cur.execute("INSERT INTO cash (as_of, balance) VALUES (?, ?)", (now, new_balance))
    conn.commit()
    return new_balance

def update_portfolio(conn, ticker, entry_date, quantity, entry_price, status, strategy, signal_score, regime):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO portfolio
            (ticker, entry_date, quantity, entry_price, status, strategy, signal_score, regime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticker, entry_date, quantity, entry_price, status, strategy, signal_score, regime)
    )
    conn.commit()

