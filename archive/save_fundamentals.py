"""
PJ Fire — Fundamentals Saver

Fetches full-year company fundamentals via fetcher, stores to DB.
"""

from data.fetcher import fetch_jquants_token, fetch_fundamentals
from db.db_utils import get_db_connection
from utils.logger import log_info, log_warning, log_error

def save_fundamentals(ticker=None):
    """
    Fetches and saves fundamentals (FY only).
    If ticker is None, fetches all.
    """
    token = fetch_jquants_token()
    if not token:
        log_error("Failed to get J-Quants token. Aborting fundamentals save.")
        return

    fundamentals = fetch_fundamentals(token, ticker)
    if not fundamentals:
        log_warning("No fundamentals fetched. Nothing to save.")
        return

    n_inserted = 0
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        for row in fundamentals:
            # Only keep full fiscal year data
            if row.get("TypeOfCurrentPeriod") != "FY":
                continue
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO stock_fundamentals 
                        (ticker, fiscal_year, net_sales, eps, profit)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("Code"),
                        row.get("CurrentFiscalYear"),
                        row.get("NetSales"),
                        row.get("EarningsPerShare"),
                        row.get("ProfitAttributableToOwnersOfParent"),
                    )
                )
                n_inserted += 1
            except Exception as e:
                log_warning(f"Insert failed for {row.get('Code')} FY {row.get('CurrentFiscalYear')}: {e}")
        conn.commit()

    log_info(f"Saved {n_inserted} company fundamentals (FY only).")

# Example usage:
# save_fundamentals()  # Save all
# save_fundamentals("7203")  # Save for specific ticker

