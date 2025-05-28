"""
PJ Fire — TDNet Disclosure/Risk Monitor

Fetches latest risk/disclosure events (TDNet or equivalent),
saves to DB or triggers logging/alerts.
"""

from utils.logger import log_info, log_warning, log_error
from db.db_utils import get_db_connection
# If you have a fetch_tdnet_disclosures in fetcher.py, import it:
# from data.fetcher import fetch_tdnet_disclosures

def fetch_tdnet_disclosures(date):
    """
    Placeholder: Replace with actual TDNet disclosure/news fetching logic.
    This should return a list of dicts: [{ 'ticker': ..., 'date': ..., 'headline': ..., 'risk_type': ... }, ...]
    """
    # TODO: Implement or connect to TDNet or equivalent
    log_warning("fetch_tdnet_disclosures is a placeholder and must be implemented.")
    return []

def save_tdnet_risk_events(date):
    """
    Fetch TDNet disclosures/news and save risk events to DB.
    """
    disclosures = fetch_tdnet_disclosures(date)
    if not disclosures:
        log_info(f"No new TDNet disclosures for {date}.")
        return

    n_inserted = 0
    with get_db_connection(simulation=True) as conn:
        cursor = conn.cursor()
        for row in disclosures:
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO risk_events
                        (ticker, date, headline, risk_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row.get("ticker"),
                        row.get("date"),
                        row.get("headline"),
                        row.get("risk_type"),
                    )
                )
                n_inserted += 1
            except Exception as e:
                log_warning(f"Insert failed for risk event {row.get('ticker')} on {date}: {e}")
        conn.commit()

    log_info(f"Saved {n_inserted} TDNet risk events for {date}.")

# Example usage:
# save_tdnet_risk_events("2024-05-17")

