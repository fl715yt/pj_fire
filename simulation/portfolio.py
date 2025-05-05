# portfolio.py
import sqlite3
from datetime import datetime

DB_FILE = "db/pj_fire.db"

DEFAULT_CASH = 1_000_000  # 円


def get_cash():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT amount FROM sim_cash LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else DEFAULT_CASH


def update_cash(new_amount):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO sim_cash (id, amount) VALUES (1, ?)", (new_amount,))
    conn.commit()
    conn.close()


def get_open_positions():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM sim_trades WHERE exit_date IS NULL")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def log_sim_trade(ticker, strategy, price, shares, date):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sim_trades (ticker, strategy, entry_price, shares, entry_date)
        VALUES (?, ?, ?, ?, ?)
    """, (ticker, strategy, price, shares, date))
    conn.commit()
    conn.close()