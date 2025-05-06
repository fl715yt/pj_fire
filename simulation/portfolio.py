# portfolio.py

import sqlite3
from datetime import datetime

DB_FILE = "db/pj_fire.db"
DEFAULT_CASH = 1_000_000


def get_simulation_cash():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT amount FROM sim_cash WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else DEFAULT_CASH


def update_simulation_cash(amount):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO sim_cash (id, amount) VALUES (1, ?)", (amount,))
    conn.commit()
    conn.close()


def get_held_stocks():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM sim_trades WHERE exit_date IS NULL")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


def log_sim_trade(ticker, strategy, price, shares, date):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sim_trades (ticker, strategy, entry_price, shares, entry_date)
        VALUES (?, ?, ?, ?, ?)
    """, (ticker, strategy, price, shares, date))
    conn.commit()
    conn.close()
