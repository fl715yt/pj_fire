# db/init_backtest_db.py
import sqlite3

DB_FILE = "db/backtest.db"

schema = """
CREATE TABLE IF NOT EXISTS bt_price_history (
    code TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    ma5 REAL,
    rsi14 REAL,
    PRIMARY KEY (code, date)
);

CREATE TABLE IF NOT EXISTS bt_fundamentals (
    code TEXT PRIMARY KEY,
    net_income REAL,
    revenue_growth REAL,
    equity_ratio REAL
);

CREATE TABLE IF NOT EXISTS bt_signals (
    signal_date TEXT,
    code TEXT,
    close_price REAL,
    ma5 REAL,
    rsi REAL,
    price_drop_pct REAL,
    next_open REAL,
    d1_high REAL,
    d2_high REAL,
    d3_high REAL,
    gap_pct REAL,
    gpt_category TEXT,
    hit_ma5 INTEGER,
    reason_score REAL,
    score REAL
);

CREATE TABLE IF NOT EXISTS bt_results (
    month TEXT,
    total_signals INTEGER,
    hit_count INTEGER,
    avg_gap REAL
);
"""

def init_backtest_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.executescript(schema)
    conn.commit()
    conn.close()
    print(f"✅ Created backtest database: {DB_FILE}")

if __name__ == "__main__":
    init_backtest_db()
