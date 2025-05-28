"""
PJ Fire — Stock Screening Module

Screens stocks for signals based on technical and fundamental filters.
All thresholds/rules are imported from config.
No database writes—output is list/dict for further processing.
"""

from db.db_utils import execute_query
from config.config import (
    MIN_PRICE_DROP_PCT,
    REQUIRED_FY_ONLY,
    # add other config constants as needed
)
from utils.logger import log_info

def screen_stocks(date):
    """
    Screen for candidate stocks based on technical and fundamental criteria.
    Returns a list of dicts for downstream processing.
    """
    # 1. Get price snapshot for the day
    price_query = """
        SELECT s.ticker, s.open, s.close, s.volume, s.date,
               (s.close - s.open) / s.open AS price_drop_pct
        FROM stock_snapshots s
        WHERE s.date = ?
    """
    prices = execute_query(price_query, (date,), simulation=True)
    candidates = []

    for row in prices:
        ticker, open_, close, volume, date_, price_drop_pct = row

        # Filter 1: Minimum price drop
        if price_drop_pct > -MIN_PRICE_DROP_PCT:
            continue  # Not enough drop

        # Filter 2: Example filter — sufficient volume
        if volume is not None and volume < 10000:
            continue

        # 3. Get fundamentals (FY only, latest)
        fundamentals_query = """
            SELECT net_sales, eps, profit, fiscal_year
            FROM stock_fundamentals
            WHERE ticker = ?
            ORDER BY fiscal_year DESC
            LIMIT 1
        """
        fundamentals = execute_query(fundamentals_query, (ticker,), simulation=True)
        if not fundamentals:
            continue
        net_sales, eps, profit, fiscal_year = fundamentals[0]

        # Optional: Add more fundamental filters as per your logic

        # Passed all filters; add to candidates
        candidates.append({
            "ticker": ticker,
            "date": date_,
            "open": open_,
            "close": close,
            "volume": volume,
            "price_drop_pct": price_drop_pct,
            "net_sales": net_sales,
            "eps": eps,
            "profit": profit,
            "fiscal_year": fiscal_year
        })

    log_info(f"Screened {len(candidates)} stock candidates for {date}.")
    return candidates

# Example usage:
# candidates = screen_stocks("2024-05-17")

