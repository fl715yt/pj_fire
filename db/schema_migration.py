import sqlite3

DB_FILE = "db/pj_fire.db"

def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # ---- Static Stock Metadata ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_metadata (
        ticker TEXT PRIMARY KEY,
        stock_code TEXT,
        stock_name TEXT,
        sector TEXT
    )
    """)

    # ---- Daily Price Snapshots ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_snapshots (
        date TEXT,
        ticker TEXT,
        close_price REAL,
        volume INTEGER,
        PRIMARY KEY (date, ticker)
    )
    """)

    # ---- Market Index Snapshots ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshots (
        date TEXT,
        index_name TEXT,
        percent_change REAL,
        PRIMARY KEY (date, index_name)
    )
    """)

    # ---- Fundamentals (Latest + Previous FY) ----
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
        PRIMARY KEY (ticker, fiscal_year)
    )
    """)

    # ---- Simulation Trade Logs ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sim_trades (
        date TEXT,
        ticker TEXT,
        action TEXT,  -- BUY / SELL
        quantity INTEGER,
        price REAL,
        reason TEXT,
        realized_pnl REAL,
        PRIMARY KEY (date, ticker, action)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Tables created or verified.")

if __name__ == "__main__":
    create_tables()
