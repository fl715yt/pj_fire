"""
PJ Fire — Canonical Simulation Engine (Unified, Config-Driven)
Handles virtual trading, positions, and cash for simulation and backtest.
- All buy/sell/forced exit logic centralized
- Logging, portfolio, cash, and trade management
- Supports both live simulation and batch (backtest) via entrypoints
"""

import pandas as pd
import sqlite3
from datetime import datetime
from config.config import (
    SIM_DB_FILE, 
    BT_DB_FILE,
    DEFAULT_CASH, 
    DEFAULT_LOT_SIZE, 
    FORCED_EXIT_THRESHOLD, 
    DRAWDOWN_REDUCE_THRESHOLD, 
    DRAWDOWN_STOP_THRESHOLD, 
    ENTRY_BUFFER, 
    STOP_LOSS_PCT, 
    GAP_DOWN_LIMIT, 
    MAX_HOLDING_DAYS, 
    LOT_UNIT_SIZE
)

from simulation.utils import get_next_trading_day
from simulation.ranker import get_top_signals_for_day
from simulation.db_utils import init_pjfire_tables, get_prices, get_cash, update_cash, update_portfolio

PORTFOLIO_TABLE = "portfolio"
TRADE_LOG_TABLE = "trades"
CASH_TABLE = "cash"

def init_simulation_db(db_path=SIM_DB_FILE, start_cash=DEFAULT_CASH, start_date=None):
    """
    Ensures all tables exist and cash is initialized in the chosen DB.
    Use db_path=BT_DB_FILE for backtest, SIM_DB_FILE for simulation.
    If start_date is provided, use that for initial cash 'as_of'.
    """
    conn = sqlite3.connect(db_path)
    init_pjfire_tables(conn)
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {CASH_TABLE}")
    count = c.fetchone()[0]
    if count == 0:
        as_of = start_date if start_date else datetime.now().strftime("%Y-%m-%d")
        c.execute(f"INSERT INTO {CASH_TABLE} (as_of, balance) VALUES (?, ?)", (as_of, start_cash))
        conn.commit()
    conn.close()

def get_portfolio(conn):
    return pd.read_sql(f"SELECT * FROM {PORTFOLIO_TABLE} WHERE status = 'open'", conn)

def get_next_day_open(conn, ticker: str, date: str):
    """Return (next_date, next_open) for ticker after given date, or (None, None)."""
    df = get_prices(conn, ticker)
    idxs = df.index[df["date"] == date]
    if len(idxs) == 0:
        return None, None
    idx = idxs[0]
    if idx >= len(df) - 1:
        return None, None
    row = df.iloc[idx + 1]
    return row["date"], float(row["open"])

def execute_next_day_buy(conn, signal, qty=DEFAULT_LOT_SIZE):
    """Attempt a next-day entry based on MA5 buffer and gap-down rules."""
    ticker = signal["ticker"]
    date = signal["date"]
    ma5 = signal.get("ma5")
    close_price = signal.get("price")
    next_date, next_open = get_next_day_open(conn, ticker, date)
    if next_date is None:
        print(f"[SKIP] No next-day price for {ticker} on {date}.")
        return False, None, None
    if ma5 is None or pd.isna(ma5):
        print(f"[SKIP] Missing MA5 for {ticker} on {date}.")
        return False, next_date, next_open
    if next_open <= ma5 * (1 - ENTRY_BUFFER) and next_open >= close_price * (1 - GAP_DOWN_LIMIT):
        executed = execute_buy(conn, ticker, next_open, qty, signal.get("score", 0), next_date)
        return executed, next_date, next_open
    print(f"[SKIP] Entry criteria not met for {ticker} on {next_date} (open {next_open}).")
    return False, next_date, next_open

def execute_buy(conn, ticker, price, qty, signal_score, date, strategy="main"):
    cash = get_cash(conn)
    total_cost = price * qty
    if cash < total_cost:
        print(f"[SIM] Insufficient cash to buy {ticker}."
              f"need {total_cost:.0f}, have {cash:.0f}. Skipping buy.")
        return False
    c = conn.cursor()
    c.execute(f"""
        INSERT OR REPLACE INTO {PORTFOLIO_TABLE} (ticker, entry_date, quantity, entry_price, status, strategy, signal_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticker, date, qty, price, "open", strategy, signal_score))
    update_cash(conn, -qty * price)
    log_trade(conn, ticker, "BUY", price, qty, signal_score, date, strategy=strategy)
    conn.commit()  # <---- Commit after logging the trade
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
    update_cash(conn, qty * price)
    c.execute(f"UPDATE {PORTFOLIO_TABLE} SET status = 'closed' WHERE ticker = ? AND status = 'open'", (ticker,))
    log_trade(conn, ticker, "SELL", price, qty, 0, date, reason=reason)
    conn.commit()  # <---- Commit after logging the trade
    print(f"[SIM] Sold {qty}x {ticker} at {price} on {date}. Reason: {reason}")
    return True

def log_trade(conn, ticker, side, price, qty, signal_score, date, reason="", strategy="main"):
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(f"""
        INSERT INTO {TRADE_LOG_TABLE} (datetime, ticker, quantity, price, trade_type, strategy, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now, ticker, qty, price, side, strategy, reason))
    conn.commit()

def get_dynamic_lot_size(conn):
    # Example logic: halve size after 5% drawdown, stop after 10%
    initial_cash = DEFAULT_CASH  # import this from config
    cash = get_cash(conn)
    drawdown = (initial_cash - cash) / initial_cash
    if drawdown >= DRAWDOWN_STOP_THRESHOLD:
        return 0  # stop trading
    elif drawdown >= DRAWDOWN_REDUCE_THRESHOLD:
        return DEFAULT_LOT_SIZE // 2
    return DEFAULT_LOT_SIZE

def forced_exit_logic(conn, ranked_signals):
    held_df = get_portfolio(conn)
    for _, held in held_df.iterrows():
        held_score = held.get("signal_score", 0)
        ticker = held["ticker"]
        for s in ranked_signals:
            if s["score"] > held_score * (1 + FORCED_EXIT_THRESHOLD):
                print(f"[FORCED EXIT] {ticker} -> {s['ticker']} (score {s['score']:.2f})")
                execute_sell(conn, ticker, s["price"], s["date"], reason="ForcedExit")
                lot_size = get_dynamic_lot_size(conn)
                if lot_size > 0:
                    _ = execute_next_day_buy(conn, s, qty=lot_size)
                else:
                    print("[FORCED EXIT] Trading paused due to drawdown.")
                break

def time_exit_logic(conn, current_date):
    """Force-sell positions held longer than MAX_HOLDING_DAYS."""
    held_df = get_portfolio(conn)
    for _, held in held_df.iterrows():
        entry_date = held.get("entry_date")
        if not entry_date:
            continue
        days_held = (pd.to_datetime(current_date) - pd.to_datetime(entry_date)).days
        if days_held >= MAX_HOLDING_DAYS:
            ticker = held["ticker"]
            df = get_prices(conn, ticker, start_date=current_date, end_date=current_date)
            if not df.empty and "close" in df.columns:
                exit_price = df.iloc[0]["close"]
            else:
                exit_price = held.get("entry_price", 0)
            print(f"[TIME EXIT] {ticker} held {days_held} days. Closing at {exit_price}.")
            execute_sell(conn, ticker, exit_price, current_date, reason="TimeStop")

def run_simulation_for_day(candidates, date, db_path=SIM_DB_FILE):
    """
    Given pre-scored and filtered candidates, runs buy/sell logic for a single day.
    """
    conn = sqlite3.connect(db_path)
    init_pjfire_tables(conn)
    # --- 1. Get top signals
    ranked = get_top_signals_for_day(candidates)
    print(f"Top signals for {date}:")
    for sig in ranked:
        print(sig)
    # --- 2. Forced exit check
    forced_exit_logic(conn, ranked)
    # --- 3. Time-based exits
    time_exit_logic(conn, date)
    # --- 3. Execute new buys on next day's open
    for sig in ranked:
        _ = execute_next_day_buy(conn, sig)
    conn.close()

def simulate_trade_for_backtest(
    conn, signal, entry_date, trading_days,
    return_result=False, execute_trade=False
):
    """
    Simulates a single trade.
    If execute_trade=True, updates cash/portfolio in DB.
    Always returns result, P/L, entry date, entry price.
    """
    ticker = signal["ticker"]

    # 1. Get open price for entry date
    prices = get_prices(conn, ticker, start_date=entry_date, end_date=entry_date)
    if prices.empty:
        if return_result:
            return "NO_ENTRY_PRICE", 0, entry_date, None
        else:
            return

    entry_price = prices["open"].iloc[0]

    # 2. Determine max quantity (dynamic sizing by available cash and lot unit)
    cash = get_cash(conn)
    max_lots = int(cash // (entry_price * LOT_UNIT_SIZE))
    quantity = max_lots * LOT_UNIT_SIZE
    if quantity == 0:
        if return_result:
            return "NO_CASH", 0, entry_date, entry_price
        else:
            return

    target_tp = signal["ma5"]
    stop_loss = entry_price * (1 - STOP_LOSS_PCT)
    max_holding = MAX_HOLDING_DAYS

    result = "TIMEOUT"
    exit_price = None
    exit_date = None

    # 3. Simulate each day in holding period
    for offset in range(1, max_holding + 1):
        current_date = get_next_trading_day(entry_date, trading_days, offset)
        if not current_date:
            break
        day_prices = get_prices(conn, ticker, start_date=current_date, end_date=current_date)
        if day_prices.empty:
            continue
        high = day_prices["high"].iloc[0]
        low = day_prices["low"].iloc[0]
        close = day_prices["close"].iloc[0]
        # Take profit hit
        if high >= target_tp:
            exit_price = target_tp
            exit_date = current_date
            result = "TP"
            break
        # Stop loss hit
        if low <= stop_loss:
            exit_price = stop_loss
            exit_date = current_date
            result = "SL"
            break
        # Save close for TIMEOUT exit
        exit_price = close
        exit_date = current_date

    # 4. Timeout exit: exit at close of last day if TP/SL not hit
    pl = (exit_price - entry_price) * quantity if exit_price is not None else 0

    # 5. If real trade, update cash/portfolio
    if execute_trade and exit_price is not None:
        update_cash(conn, -quantity * entry_price)
        update_portfolio(conn, ticker, entry_date, quantity, entry_price, "OPEN", signal.get("strategy", "mean_reversion"), signal.get("score", 0))


    if return_result:
        return result, pl, entry_date, entry_price