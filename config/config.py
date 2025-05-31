"""
PJ Fire — Centralized Configuration Module

* Holds **all** constants, thresholds, mappings, and paths for every PJ Fire component.
* Contains **no** business logic or side-effects; just import what you need.
* Secrets come from .env; codebase stays credentials-free.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ----------------------------------------------------------------------
#  Environment bootstrap
# ----------------------------------------------------------------------
load_dotenv()  # ensures .env variables are loaded

# ----------------------------------------------------------------------
#  Secrets
# ----------------------------------------------------------------------
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
JQUANTS_EMAIL     = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD  = os.getenv("JQUANTS_PASSWORD")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID     = os.getenv("GOOGLE_CSE_ID")

# ----------------------------------------------------------------------
#  Database locations (strict separation ⇒ no cross-contamination)
# ----------------------------------------------------------------------
SIM_DB_FILE: str = os.getenv(
    "PJ_FIRE_SIM_DB",
    str(Path("simulation") / "pjfire.db"),
)
BT_DB_FILE: str = os.getenv(
    "PJ_FIRE_BT_DB",
    str(Path("backtest") / "backtest_bt.db"),
)

# ----------------------------------------------------------------------
#  Data files & universe
# ----------------------------------------------------------------------
UNIVERSE_CSV      = os.getenv("PJ_FIRE_UNIVERSE_CSV", "topix_company_list.csv")
VARIANT_CSV       = os.getenv("PJ_FIRE_VARIANT_CSV", "topix_company_list.csv")
LOG_PATH          = str(Path("logs") / "pj_fire.log")

# ----------------------------------------------------------------------
#  Strategy/Scoring Constants
# ----------------------------------------------------------------------
DEFAULT_LOT_SIZE           = 100            # shares per trade
DEFAULT_CASH               = 1_000_000      # starting balance for new sim accounts
MIN_TRADE_AMOUNT           = 10_000         # ¥ — ignore micro signals
FORCED_EXIT_THRESHOLD      = 0.07           # ≥ 7 % score gap ⇒ forced exit
TOP_N_RANK                 = 10             # candidates forwarded to signal stage
MAX_SIGNAL_PER_DAY         = 5              # UX guard-rail
MIN_VOLUME                 = 10_000         # minimum daily volume for screening
RSI_THRESHOLD              = 30             # default RSI filter
DROP_PCT_THRESHOLD         = -0.04          # -4% or worse for drop filter

WEIGHTS = {
    "price_drop_pct": 3.0,
    "gpt_reason_score": 2.0,
    "fundamental_strength": 1.5,
    "volume_spike": 1.0,
    # add more if needed
}

SCORE_CUTOFF = 0.0  # Minimum score for signal consideration

CATEGORY_SCORING = {
    "misinterpreted_news": 1.2,
    "slightly_bad_news": 0.7,
    "very_bad_news": 0.0,
    "no_news": 1.1,
    "macro_or_sector_drop": 0.0
}

# ----------------------------------------------------------------------
#  Drawdown protection (Phase 1 live; Phase 3 adds portfolio exposure caps)
# ----------------------------------------------------------------------
DRAWDOWN_REDUCE_THRESHOLD  = 0.05           # 5 % DD ⇒ halve lot size
DRAWDOWN_STOP_THRESHOLD    = 0.10           # 10 % DD ⇒ pause new trades

# ----------------------------------------------------------------------
#  Exit rules
# ----------------------------------------------------------------------
TAKE_PROFIT_PCT            = 0.05           # +5 % TP
STOP_LOSS_PCT              = -0.05          # –5 % SL

# ----------------------------------------------------------------------
#  Fundamentals import
# ----------------------------------------------------------------------
REQUIRED_FY_ONLY           = True           # fundamentals: full-year rows only
ENABLE_QUARTERLY_IMPORT    = False          # flip True when /statements Q* rows are stored

# ----------------------------------------------------------------------
#  External endpoints (J-Quants Light Plan)
# ----------------------------------------------------------------------
JQ_BASE_URL                = "https://api.jquants.com/v1"
PRICE_ENDPOINT             = f"{JQ_BASE_URL}/prices/daily_quotes"
FY_ENDPOINT                = f"{JQ_BASE_URL}/fins/statements"   # FY rows only
LISTED_INFO_ENDPOINT       = f"{JQ_BASE_URL}/listed/info"

# ----------------------------------------------------------------------
#  Project metadata / UX
# ----------------------------------------------------------------------
PROJECT_NAME               = "PJ Fire"
LINE_BOT_NAME              = "PJ Fire シミュレータ"
VERSION                    = "1.0.0"
LINE_RICH_MENU_STYLE       = "compact"
LINE_LANGUAGE              = "ja"
UI_THEME                   = "light"

# ----------------------------------------------------------------------
#  Scheduling / automation
# ----------------------------------------------------------------------
DAILY_SIGNAL_TIME          = "08:45"        # JST, LINE push
WEEKLY_REPORT_DAY          = "FRI"          # Friday summary

# ----------------------------------------------------------------------
#  GPT / reasoning settings
# ----------------------------------------------------------------------
GPT_MODEL                  = os.getenv("PJ_FIRE_GPT_MODEL", "gpt-4o")
GPT_DELAY_SEC              = 1.2
REASONING_CATEGORY_LABELS  = [
    "misinterpreted_news",
    "slightly_bad_news",
    "very_bad_news",
    "no_news",
    "macro_or_sector_drop"
]

# ----------------------------------------------------------------------
#  Sector ETF mapping (for macro/sector drop detection)
# ----------------------------------------------------------------------
SECTOR_ETF_MAP = {
    "食品": "1617",
    "エネルギー資源": "1618",
    "建設・資材": "1619",
    "素材・化学": "1620",
    "医薬品": "1621",
    "自動車・輸送機": "1622",
    "鉄鋼・非鉄": "1623",
    "機械": "1624",
    "電機・精密": "1625",
    "情報通信・サービスその他": "1626",
    "電気・ガス": "1627",
    "運輸・物流": "1628",
    "商社・卸売": "1629",
    "小売": "1630",
    "銀行": "1631",
    "金融（除く銀行）": "1632",
    "不動産": "1633",
}
MARKET_ETF = "1306"  # TOPIX ETF

# ----------------------------------------------------------------------
#  Sanity checks to avoid silent mis-imports
# ----------------------------------------------------------------------
if __name__ != "config.config":
    raise ImportError(
        "Import constants via `from config.config import X`, "
        "not by copying this file or re-naming it."
    )
