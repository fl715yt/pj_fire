"""
PJ Fire — Canonical Simulation Engine
Handles virtual trading, positions, and cash for simulation and backtest.
- All buy/sell/forced exit logic centralized
- Logging, portfolio, cash, and trade management
- Supports both live simulation and batch (backtest) via entrypoints
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from simulation.ranker import get_top_signals_for_day
from simulation.db_utils import init_pjfire_tables

load_dotenv()
DB_FILE = os.getenv("PJ_FIRE_DB", "simulation/pjfire.db")
PORTFOLIO_TABLE = "portfolio"
TRADE_LOG_TABLE = "trades"
CASH_TABLE = "cash"

DEFAULT_CASH = 1_000_000
DEFAULT_LOT_SIZE = 100
FORCED_EXIT_THRESHOLD = 0.10  # Score delta to trigger forced exit

def init_simulation_db():
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {CASH_TABLE}")
    count = c.fetchone()[0]
    if count == 0:
        now = datetime.now().strftime("%Y-%m-%d")
        c.execute(f"INSERT INTO {CASH_TABLE} (as_of, balance) VALUES (?, ?)", (now, DEFAULT_CASH))
        conn.commit()
    conn.close()

def get_portfolio(conn):
    return pd.read_sql(f"SELECT * FROM {PORTFOLIO_TABLE} WHERE status = 'open'", conn)

def get_cash(conn):
    cur = conn.cursor()
    cur.execute(f"SELECT balance FROM {CASH_TABLE} ORDER BY as_of DESC LIMIT 1")
    row = cur.fetchone()
    return float(row[0]) if row else DEFAULT_CASH

def update_cash(conn, amount, as_of_date):
    cur = conn.cursor()
    cur.execute(f"INSERT OR REPLACE INTO {CASH_TABLE} (as_of, balance) VALUES (?, ?)", (as_of_date, amount))
    conn.commit()

def execute_buy(conn, ticker, price, qty, signal_score, date, strategy="main"):
    cash = get_cash(conn)
    total_cost = price * qty
    if cash < total_cost:
        qty = max(int(cash // price), 0)
    if qty <= 0:
        print(f"[SIM] Insufficient cash to buy {ticker}.")
        return False
    c = conn.cursor()
    c.execute(f"""
        INSERT OR REPLACE INTO {PORTFOLIO_TABLE} (ticker, entry_date, quantity, entry_price, status, strategy, signal_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticker, date, qty, price, "open", strategy, signal_score))
    update_cash(conn, cash - (qty * price), date)
    log_trade(conn, ticker, "BUY", price, qty, signal_score, date, strategy=strategy)
    print(f"[SIM] Bought {qty}x {ticker} at {price} on {date}.")
    return True

def execute_sell(conn, ticker, price, date, reason="NormalExit"):
    c = conn.cursor()
    c.execute(f"SELECT quantity, entry_price FROM {PORTFOLIO_TABLE} WHERE ticker = ? AND status = 'open'", (ticker,))
    row = c.fetchone()
    if not row:
        print(f"[SIM] No position to sell for {ticker}.")
        return False
    qty, entry_price = row
    cash = get_cash(conn)
    update_cash(conn, cash + price * qty, date)
    c.execute(f"UPDATE {PORTFOLIO_TABLE} SET status = 'closed' WHERE ticker = ? AND status = 'open'", (ticker,))
    log_trade(conn, ticker, "SELL", price, qty, 0, date, reason=reason)
    print(f"[SIM] Sold {qty}x {ticker} at {price} on {date}. Reason: {reason}")
    conn.commit()
    return True

def log_trade(conn, ticker, side, price, qty, signal_score, date, reason="", strategy="main"):
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(f"""
        INSERT INTO {TRADE_LOG_TABLE} (datetime, ticker, quantity, price, trade_type, strategy, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now, ticker, qty, price, side, strategy, reason))
    conn.commit()

def forced_exit_logic(conn, ranked_signals):
    held_df = get_portfolio(conn)
    for _, held in held_df.iterrows():
        held_score = held.get("signal_score", 0)
        ticker = held["ticker"]
        for s in ranked_signals:
            if s["score"] > held_score * (1 + FORCED_EXIT_THRESHOLD):
                print(f"[FORCED EXIT] {ticker} -> {s['ticker']} (score {s['score']:.2f})")
                execute_sell(conn, ticker, s["price"], s["date"], reason="ForcedExit")
                execute_buy(conn, s["ticker"], s["price"], DEFAULT_LOT_SIZE, s["score"], s["date"])
                break

def run_simulation_for_day(candidates, date):
    """
    Given pre-scored and filtered candidates, runs buy/sell logic for a single day.
    """
    conn = sqlite3.connect(DB_FILE)
    init_pjfire_tables(conn)
    # --- 1. Get top signals
    ranked = get_top_signals_for_day(candidates)
    print(f"Top signals for {date}:")
    for sig in ranked:
        print(sig)
    # --- 2. Forced exit check
    forced_exit_logic(conn, ranked)
    # --- 3. Execute new buys
    for sig in ranked:
        execute_buy(conn, sig["ticker"], sig["price"], DEFAULT_LOT_SIZE, sig["score"], date)
    conn.close()

def simulate_trade_for_backtest(conn, signal, date, return_result=False):
    """
    Core trade logic for batch (backtest) mode.
    Returns (result, pl) for daily stats/tracking.
    """
    ticker = signal["ticker"]
    price = signal["price"]
    score = signal.get("score", 0)
    # Implement your real entry/exit logic here.
    # For now, fake logic as an example:
    # (You should implement your MA/TP/SL/timeout workflow here.)

    # --- Example: simulate buy/hold/sell over X days ---
    result = "Timeout"  # Or "TP" or "SL"
    pl = 0
    # ...your trade logic to compute result and pl...

    # Actually log the trade in DB as before
    execute_buy(conn, ticker, price, DEFAULT_LOT_SIZE, score, date)
    # If an exit occurs, also call execute_sell(...) and compute pl

    if return_result:
        return result, pl
