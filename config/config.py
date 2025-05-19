"""
PJ Fire — Centralized Configuration Module

- All constants, thresholds, and settings for the entire PJ Fire system.
- No business logic or side effects. Import in all modules as needed.
- Sensitive information should be managed via environment variables (.env).

Author: [Your Name]
Updated: [YYYY-MM-DD]
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Ensures .env values are loaded

# === API KEYS & SECRETS ===
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
JQUANTS_EMAIL      = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD   = os.getenv("JQUANTS_PASSWORD")

# === J-Quants API Endpoints ===
JQUANTS_BASE_URL           = "https://api.jquants.com/v1"
JQUANTS_DAILY_QUOTES       = f"{JQUANTS_BASE_URL}/prices/daily_quotes"
JQUANTS_STATEMENTS         = f"{JQUANTS_BASE_URL}/fins/statements"
JQUANTS_LISTED_INFO        = f"{JQUANTS_BASE_URL}/listed/info"

# === DATABASE FILES ===
SIM_DB_PATH   = "db/pj_fire.db"
BT_DB_PATH    = "backtest/backtest.db"

# === SIMULATION SETTINGS ===
DEFAULT_LOT_SIZE          = 100      # Default shares per trade
MIN_TRADE_AMOUNT          = 10000    # Minimum yen per trade (example)
FORCED_EXIT_THRESHOLD     = 0.07     # 7% (example, adjust to match project rules)
DRAWDOWN_REDUCE_SIZE      = 0.05     # Reduce trade size after 5% drawdown
DRAWDOWN_STOP_THRESHOLD   = 0.10     # Stop trading after 10% drawdown

# === STRATEGY FILTERS ===
MIN_PRICE_DROP_PCT        = 0.03     # Minimum price drop (example: 3%)
MAX_MACRO_DROP_PCT        = 0.06     # Macro/sector drop exclusion (example: 6%)
REQUIRED_FY_ONLY          = True     # Use full fiscal year only for fundamentals

# === EXIT RULES ===
TAKE_PROFIT_PCT           = 0.05     # Example: 5% target
STOP_LOSS_PCT             = -0.05    # Example: -5% stop loss

# === SCHEDULING / AUTOMATION ===
DAILY_SIGNAL_TIME         = "08:45"  # JST, example for LINE delivery
WEEKLY_REPORT_DAY         = "FRI"    # Weekly summary trigger

# === OTHER CONSTANTS ===
PROJECT_NAME              = "PJ Fire"
LINE_BOT_NAME             = "PJ Fire シミュレータ"
VERSION                   = "1.0.0"

# === PATHS ===
LOG_PATH                  = "logs/pj_fire.log"

# === GPT SETTINGS ===
GPT_MODEL                 = "gpt-4o"        # Confirmed by user
REASONING_CATEGORY_LABELS = [
    "Misinterpreted news",    # Score high
    "Slightly bad news",      # Score low
    "Very bad news",          # Exclude
    "Unknown / no news",      # Core signal
    "Macro/sector drop",      # Exclude
]

# === UX SETTINGS ===
LINE_RICH_MENU_STYLE       = "compact"
LINE_LANGUAGE              = "ja"
UI_THEME                   = "light"

# === SAFETY / GUARDRAILS ===
MAX_SIGNAL_PER_DAY         = 5        # To avoid overtrading for users

# === Add new constants below as needed. ===

