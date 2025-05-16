# tdnet_fetcher.py

import os
import json
import requests
import sqlite3
from datetime import datetime, timedelta

TDNET_FEED_URL = "https://www.release.tdnet.info/inbs/I_list_00.js"
DB_FILE = "backtest/backtest.db"

# Helper: parse TDnet date/time to ISO format
def parse_jst_datetime(date_str, time_str):
    dt_str = f"{date_str} {time_str}"
    return datetime.strptime(dt_str, "%Y/%m/%d %H:%M:%S").isoformat()

# Fetch disclosure list from TDnet
def fetch_tdnet_disclosures():
    res = requests.get(TDNET_FEED_URL)
    if res.status_code != 200:
        print("[ERROR] Failed to fetch TDnet feed")
        return []

    # JS file is like: var infoList = [...];
    raw_text = res.text.strip()
    json_str = raw_text[raw_text.find("["): raw_text.rfind("]") + 1]
    try:
        disclosures = json.loads(json_str)
    except Exception as e:
        print("[ERROR] Failed to parse TDnet feed:", e)
        return []

    return disclosures

# Filter by ticker and date
def get_disclosures_for_ticker(ticker, signal_date, days=3):
    target_date = datetime.strptime(signal_date, "%Y-%m-%d")
    end_date = target_date + timedelta(days=days)

    all_disclosures = fetch_tdnet_disclosures()
    results = []

    for entry in all_disclosures:
        code, company_name, title, doc_url, date_str, time_str = entry[:6]
        if not doc_url.endswith(".pdf"):
            continue

        # Match ticker (TDnet codes are 4-digit strings)
        if code != ticker:
            continue

        dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
        if target_date <= dt <= end_date:
            results.append({
                "ticker": code,
                "company_name": company_name,
                "title": title,
                "timestamp": dt.isoformat(),
                "url": f"https://www.release.tdnet.info/inbs/{doc_url}"
            })

    return results

# Test example
if __name__ == "__main__":
    from pprint import pprint
    pprint(get_disclosures_for_ticker("9984", "2025-04-05"))
