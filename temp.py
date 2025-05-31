import sqlite3
from config.config import SIM_DB_FILE, BT_DB_FILE

CREATE_FUNDAMENTALS_SQL = """
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker TEXT,
    period_type TEXT,       -- "FY" or "Q"
    period_end DATE,
    revenue REAL,
    eps REAL,
    profit REAL,
    PRIMARY KEY (ticker, period_type, period_end)
)
"""

def ensure_fundamentals_table(db_file):
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute(CREATE_FUNDAMENTALS_SQL)
    conn.commit()
    conn.close()
    print(f"Fundamentals table ensured in {db_file}.")

if __name__ == "__main__":
    ensure_fundamentals_table(SIM_DB_FILE)
    ensure_fundamentals_table(BT_DB_FILE)