# backtest/backtest_config.py

# ─── Backtest Range ─────────────────────────────
from datetime import datetime, timedelta
BACKTEST_END = datetime.now().strftime("%Y-%m-%d")
BACKTEST_START = (datetime.now() - timedelta(days=110)).strftime("%Y-%m-%d")


# ─── RSI Settings ───────────────────────────────
RSI_PERIOD = 14

# ─── Technical Thresholds ───────────────────────
DROP_THRESHOLD = -3.0  # % drop from previous close
VOLUME_THRESHOLD = 100000
MA5_DISTANCE_THRESHOLD = 5.0  # % away from MA5 (optional filter)

# ─── Scoring Weights ────────────────────────────
WEIGHTS = {
    "price_drop_pct": 0.35,
    "rsi": 0.20,
    "revenue_growth": 0.15,
    "net_income_positive": 0.10,
    "equity_ratio_check": 0.10,
    "reason_category": 0.10,
}

# ─── GPT Categorization Mapping ─────────────────
REASON_SCORES = {
    "misinterpreted_news": 1.0,
    "slightly_bad_news": 0.5,
    "unknown_or_no_news": 0.8,
    "very_bad_news": 0.0,
    "macro_or_sector": 0.0,
}
