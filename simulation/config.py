# simulation/config.py
"""
Central config for PJ Fire simulation and backtest.
Edit these values for threshold and rule changes.
"""

DEFAULT_CASH = 1_000_000
DEFAULT_LOT_SIZE = 100
FORCED_EXIT_THRESHOLD = 0.10  # 10% higher score triggers forced exit
TRADE_LOG_TABLE = "sim_trades"
PORTFOLIO_TABLE = "sim_portfolio"
DB_FILE = "simulation/sim.db"
