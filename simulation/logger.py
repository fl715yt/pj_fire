"""
PJ Fire — Logger utility (PATCHED, FULL TRADE SCHEMA)
Logs all trade, skip, and rejection events using a unified, structured format.
Supports info, warning, and debug levels.
"""

from datetime import datetime
import os
import json
from config.config import LOG_EMOJI

EMOJI_TRADE = "💹" if LOG_EMOJI else "[TRADE]"
EMOJI_WARN = "⚠️" if LOG_EMOJI else "[WARN]"
EMOJI_INFO = "ℹ️" if LOG_EMOJI else "[INFO]"

try:
    from config.config import LOG_PATH
except ImportError:
    LOG_PATH = None

LOG_LEVEL = os.getenv("PJ_FIRE_LOG_LEVEL", "INFO")  # "DEBUG", "INFO", "WARN", "ERROR"

def _timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def log_trade_full(
    trade_id=None, signal_date=None, buy_date=None, sell_date=None, ticker=None, quantity=None,
    buy_price=None, sell_price=None, trade_type=None, strategy=None, regime=None, result=None, pl=None,
    score=None, normalized_score=None, technicals=None, fundamentals=None, gpt_summary=None, gpt_decision=None,
    news_url=None, reason=None, news_headlines=None, news_api_used=None, take_profit=None, stop_loss=None, extra=None
):
    """
    Unified trade logger for all trade/skipped/rejection events.
    Any missing fields will be set to None.
    """
    record = {
        "trade_id": trade_id,
        "signal_date": signal_date,
        "buy_date": buy_date,
        "sell_date": sell_date,
        "ticker": ticker,
        "quantity": quantity,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "trade_type": trade_type,
        "strategy": strategy,
        "regime": regime,
        "result": result,
        "pl": pl,
        "score": score,
        "normalized_score": normalized_score,
        "technicals": technicals,
        "fundamentals": fundamentals,
        "gpt_summary": gpt_summary,
        "gpt_decision": gpt_decision,
        "news_url": news_url,
        "reason": reason,
        "news_headlines": news_headlines,
        "news_api_used": news_api_used,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "logged_at": _timestamp()
    }
    # Merge in any extra fields
    if extra and isinstance(extra, dict):
        record.update(extra)
    # Print and log as JSON line for structure and downstream parsing
    msg = f"{EMOJI_TRADE} {json.dumps(record, ensure_ascii=False)}"
    print(msg)
    _log_to_file(msg)

def log_warning(msg):
    text = f"{EMOJI_WARN} {_timestamp()} {msg}"
    print(text)
    _log_to_file(text)

def log_info(msg):
    if LOG_LEVEL in ("DEBUG", "INFO"):
        text = f"{EMOJI_INFO} {_timestamp()} {msg}"
        print(text)
        _log_to_file(text)

def _log_to_file(msg):
    if LOG_PATH:
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass  # Fail silently if logging fails

def log_debug(msg):
    if LOG_LEVEL == "DEBUG":
        text = f"[DEBUG] {_timestamp()} {msg}"
        print(text)
        _log_to_file(text)

def log_error(msg):
    emoji = "❌" if LOG_EMOJI else "[ERROR]"
    print(f"{emoji} {_timestamp()} {msg}")
    _log_to_file(f"{emoji} {_timestamp()} {msg}")