# simulation/logger.py
"""
Logger utility for PJ Fire simulation (and optionally backtest).
Supports trade/event logging, warnings, and info messages.
"""

from datetime import datetime
import os
LOG_USE_EMOJI = os.getenv("PJ_FIRE_LOG_USE_EMOJI", "1") == "1"
EMOJI_TRADE = "💹" if LOG_USE_EMOJI else "[TRADE]"
EMOJI_WARN = "⚠️" if LOG_USE_EMOJI else "[WARN]"
EMOJI_INFO = "ℹ️" if LOG_USE_EMOJI else "[INFO]"

try:
    from config.config import LOG_PATH
except ImportError:
    LOG_PATH = None  # fallback

LOG_LEVEL = os.getenv("PJ_FIRE_LOG_LEVEL", "INFO")  # "DEBUG", "INFO", "WARN", "ERROR"

def _timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def log_trade(ticker, side, price, qty, score, date, reason=""):
    msg = f"[TRADE] {date} {side} {ticker} {qty}@{price} Score:{score} {reason}"
    print(msg)
    _log_to_file(msg)

def log_warning(msg):
    text = f"[WARN] {_timestamp()} ⚠️ {msg}"
    print(text)
    _log_to_file(text)

def log_info(msg):
    if LOG_LEVEL in ("DEBUG", "INFO"):
        text = f"[INFO] {_timestamp()} ℹ️ {msg}"
        print(text)
        _log_to_file(text)

def _log_to_file(msg):
    if LOG_PATH:
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass  # Fail silently if logging fails

# Optionally add a debug function
def log_debug(msg):
    if LOG_LEVEL == "DEBUG":
        text = f"[DEBUG] {_timestamp()} {msg}"
        print(text)
        _log_to_file(text)
