# simulation/logger.py
"""
Logger utility for PJ Fire simulation (and optionally backtest).
Supports trade/event logging, warnings, and info messages.
"""

from datetime import datetime

def log_trade(ticker, side, price, qty, score, date, reason=""):
    print(f"[TRADE] {date} {side} {ticker} {qty}@{price} Score:{score} {reason}")

def log_warning(msg):
    print(f"[WARN] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ⚠️ {msg}")

def log_info(msg):
    print(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ℹ️ {msg}")
