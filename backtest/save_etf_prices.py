"""
PJ Fire — Save ETF Prices to DB using existing fetch/save pipeline and config dates.
"""

import os
from config.config import BT_DB_FILE, MARKET_ETF, SECTOR_ETF_MAP, START_DATE, END_DATE
from simulation.save_prices import fetch_and_save_prices

if __name__ == "__main__":
    # ETF tickers from config
    etf_tickers = [str(MARKET_ETF).zfill(5)] + [str(x).zfill(5) for x in SECTOR_ETF_MAP.values()]

    # Use date range from config.py (with fallback defaults set in config)
    start_date = START_DATE
    end_date = END_DATE
    db_path = BT_DB_FILE

    print(f"[INFO] Loading ETF prices from {start_date} to {end_date} for {len(etf_tickers)} ETFs")
    fetch_and_save_prices(start_date, end_date, etf_tickers, db_path=db_path, force=True)
    print("[FINISHED]")
