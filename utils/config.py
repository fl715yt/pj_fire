import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# Screening thresholds
DROP_THRESHOLD = -3.0
VOLUME_THRESHOLD = 100000

# --- Simulation Rules ---
DEFAULT_LOT_SIZE = 100
FORCED_EXIT_THRESHOLD = 0.05  # 5% higher score triggers forced exit

# --- Risk Management ---
MAX_PORTFOLIO_RISK_EXPOSURE = 0.03  # Phase 3: Max 3% of cash exposed across all trades
STOP_LOSS_PCT = -0.05  # Fixed stop-loss per trade: -5%
