import requests
import json
from datetime import datetime, timedelta

TDNET_FEED_URL = "https://www.release.tdnet.info/inbs/I_list_00.js"

def parse_jst_datetime(date_str, time_str):
    dt_str = f"{date_str} {time_str}"
    return datetime.strptime(dt_str, "%Y/%m/%d %H:%M:%S")

def fetch_tdnet_disclosures():
    res = requests.get(TDNET_FEED_URL)
    if res.status_code != 200:
        print("[ERROR] Failed to fetch TDnet feed")
        return []
    # JS file: var infoList = [...]
    raw_text = res.text.strip()
    json_str = raw_text[raw_text.find("["): raw_text.rfind("]") + 1]
    try:
        disclosures = json.loads(json_str)
    except Exception as e:
        print("[ERROR] Failed to parse TDnet feed:", e)
        return []
    return disclosures

def get_disclosures_for_ticker(ticker, signal_date, days=2, keywords=("決算",)):
    """
    Returns list of TDnet disclosure dicts for `ticker` within ±days of signal_date, matching any keyword.
    """
    target_date = datetime.strptime(signal_date, "%Y-%m-%d")
    start_date = target_date - timedelta(days=days)
    end_date = target_date + timedelta(days=days)

    all_disclosures = fetch_tdnet_disclosures()
    results = []

    for entry in all_disclosures:
        code, company_name, title, doc_url, date_str, time_str = entry[:6]
        if not doc_url.endswith(".pdf"):
            continue
        if code != ticker:
            continue
        dt = parse_jst_datetime(date_str, time_str)
        if not (start_date <= dt <= end_date):
            continue
        if any(kw in title for kw in keywords):
            results.append({
                "ticker": code,
                "company_name": company_name,
                "title": title,
                "timestamp": dt.isoformat(),
                "url": f"https://www.release.tdnet.info/inbs/{doc_url}"
            })
    return results

# Test
if __name__ == "__main__":
    from pprint import pprint
    print("Testing TDnet fetcher...")
    results = get_disclosures_for_ticker("7203", "2024-07-10")
    pprint(results)
