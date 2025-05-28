import sqlite3
import os

DB_FILE = "db/pj_fire.db"
os.makedirs("db", exist_ok=True)

def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # ─── Stock Metadata ────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_metadata (
        ticker TEXT PRIMARY KEY,
        stock_code TEXT,
        stock_name TEXT,
        sector TEXT
    )
    """)

    # ─── Daily Snapshots ───────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_snapshots (
        date TEXT,
        ticker TEXT,
        close_price REAL,
        volume INTEGER,
        PRIMARY KEY (date, ticker)
    )
    """)

    # ─── Market Index Snapshots ────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshots (
        date TEXT,
        index_name TEXT,
        percent_change REAL,
        PRIMARY KEY (date, index_name)
    )
    """)

    # ─── Fundamentals with TDNet Risk ──────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_fundamentals (
        ticker TEXT,
        fiscal_year TEXT,
        revenue REAL,
        net_income REAL,
        equity_ratio REAL,
        equity REAL,
        operating_profit REAL,
        eps REAL,
        dividend REAL,
        tdnet_risk BOOLEAN DEFAULT 0,
        PRIMARY KEY (ticker, fiscal_year)
    )
    """)

    # ─── Simulated Trades ──────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sim_trades (
        date TEXT,
        ticker TEXT,
        action TEXT,
        quantity INTEGER,
        price REAL,
        reason TEXT,
        realized_pnl REAL,
        PRIMARY KEY (date, ticker, action)
    )
    """)

    # ─── TDNet Log Table to Prevent Duplicate Scans ────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tdnet_logs (
        pub_date TEXT PRIMARY KEY,
        title TEXT
    )
    """)

    conn.commit()
    conn.close()
    print("✅ All tables created or verified.")

if __name__ == "__main__":
    create_tables()
