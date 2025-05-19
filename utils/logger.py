"""
PJ Fire — Central Logging Utility

Handles timestamped logs for all modules:
- Info, Warning, Trade events
- Outputs to console (and optionally to a log file if enabled)
"""

import logging
import os
from datetime import datetime
from config.config import LOG_PATH, PROJECT_NAME

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# === Logger Setup ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def log_info(message: str):
    """Info log (general status)"""
    logging.info(f"ℹ️  {message}")

def log_warning(message: str):
    """Warning log (potential problem)"""
    logging.warning(f"⚠️  {message}")

def log_trade(message: str):
    """Trade/execution log"""
    logging.info(f"💹 {message}")

# Optional: log_error, log_debug, etc.
def log_error(message: str):
    """Error log (critical)"""
    logging.error(f"❌ {message}")

# Usage in modules:
# from utils.logger import log_info, log_warning, log_trade

