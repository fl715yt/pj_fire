"""
PJ Fire — Daily Snapshot Saver

Fetches daily stock quotes via fetcher, stores to DB.
"""

from data.fetcher import fetch_jquants_token, fetch_daily_quotes
from db.db_utils import get_db_connection
from utils.logger import log_info, log_warning, log_error

def save_daily_snapshots(date):
    """
    Fetch daily quotes and save them to the stock_snapshots table.
    """
    token = fetch_jquants_token()
    if not token:
        log_error("Failed to get J-Quants token. Aborting snapshot save.")
        return

    quotes = fetch_daily_quotes(token, date)
    if not quotes:
        log_warning(f"No daily quotes found for {date}. Nothing to save.")
        return

    n_inserted = 0
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        for row in quotes:
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO stock_snapshots 
                        (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("Code"),
                        row.get("Date"),
                        row.get("Open"),
                        row.get("High"),
                        row.get("Low"),
                        row.get("Close"),
                        row.get("Volume"),
                    )
                )
                n_inserted += 1
            except Exception as e:
                log_warning(f"Insert failed for {row.get('Code')} on {date}: {e}")
        conn.commit()

    log_info(f"Saved {n_inserted} daily stock snapshots for {date}.")

# Example usage:
# save_daily_snapshots("2024-05-17")

