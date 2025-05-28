import os
import pandas as pd
import csv
import time
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build

# --- CONFIG ---
load_dotenv()
VARIANT_CSV = "pjfire_topix_company_patterns_filtered.csv"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
MAX_RESULTS = 10
OUTPUT_CSV = "batch_headlines_raw.csv"

# --- Minimal strict junk filter ---
HARD_JUNK = ["掲示板", "message board", "stock message", "出来高ランキング"]

def strip_trailing_zero(code):
    code = str(code)
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

# --- LOAD VARIANTS TABLE ---
variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
variant_df["ticker"] = variant_df["ticker"].apply(strip_trailing_zero)
TICKER_TO_VARIANTS = {
    row["ticker"]: [v.strip() for v in str(row["variants"]).split(" / ")
                    if v.strip() and not v.strip().isdigit()]
    for _, row in variant_df.iterrows()
}

# --- Insert your ticker list here ---
raw_tickers = [
    '9984', '7203', '8306', '4751', '4568', '2413', '6501', '8591', '6752', '3436',
    '8035', '6506', '9202', '9983', '80650', '29080', '18870', '90700', '45590', '43100',
    '40910', '31760', '90440', '27680', '83370', '90680', '72690', '25870', '77290', '63230',
    '19390', '19290', '26780', '40530', '41940', '69150', '78320', '18930', '74510', '38800',
    '88040', '81310', '86000', '63060', '40640', '64740', '77210', '45780', '98240', '15180',
    '93240', '97660', '34010', '85700', '63260', '52880', '33600', '40410', '93860', '52140',
    '26740', '59850', '27260', '57020', '53440', '78460', '45070', '97870', '20020', '90080',
    '65330', '72200', '30640', '59750', '24620', '73370', '47140', '80140', '79650', '57130',
    '75900', '37780', '86160', '23350', '21080', '82030', '41160', '95010', '46810', '24750',
    '27530', '65010', '80520', '58010', '34330', '58570', '54820', '39930', '82790', '45260',
    '86010', '83660', '81250', '23710', '79140', '80510', '35610', '72010', '90070', '34360',
    '65710', '59810', '45380', '80700', '83930', '73890', '40620', '83700', '49970', '94320',
    '95070', '22060', '41800', '99600', '97570', '49310', '61840', '45280', '23050', '40050',
    '74830', '88480', '49270', '40220'
]

# --- De-duplicate and normalize tickers to 4-digit format ---
TICKERS = []
seen = set()
for t in raw_tickers:
    norm = strip_trailing_zero(t)
    if norm not in seen:
        TICKERS.append(norm)
        seen.add(norm)

# --- Diverse date list for event/routine coverage ---
DATE_LIST = [
    "2023-11-10",  # Q2 earnings
    "2024-02-13",  # Q3 earnings
    "2024-05-10",  # FY earnings
    "2024-04-12",  # Post-fiscal
    "2024-01-17",  # Routine
    "2024-03-14",  # Dividend/earnings
    # Add/remove dates as desired for runtime
]

def get_search_terms(ticker, variants):
    ticker = strip_trailing_zero(ticker)
    ticker_fw = halfwidth_to_fullwidth(ticker)
    terms = [ticker, ticker_fw] + [v for v in variants if v not in {ticker, ticker_fw}]
    return list(dict.fromkeys([t for t in terms if t and len(t) > 1]))

def is_hard_junk(title):
    return any(jk in title for jk in HARD_JUNK)

def fetch_all_headlines():
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    except Exception as e:
        print(f"[ERROR] Google CSE API error: {e}")
        return

    total_searches = 0
    total_headlines = 0
    start_time = time.time()
    with open(OUTPUT_CSV, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "date", "headline", "url", "search_term"])
        for i, ticker in enumerate(TICKERS, 1):
            variants = TICKER_TO_VARIANTS.get(str(ticker), [])
            search_terms = get_search_terms(ticker, variants)
            ticker_headline_count = 0
            for signal_date in DATE_LIST:
                for term in search_terms:
                    query = f'{term} 株式'
                    print(f"[{i}/{len(TICKERS)}] {ticker} | {signal_date} | term: '{term}' ...", end="")
                    try:
                        result = service.cse().list(
                            q=query,
                            cx=GOOGLE_CSE_ID,
                            lr="lang_ja",
                            num=MAX_RESULTS,
                            sort="date"
                        ).execute()
                    except Exception as e:
                        print(f" [ERROR: {e}]")
                        time.sleep(1.2)
                        continue

                    items = result.get("items", [])
                    kept = 0
                    for item in items:
                        title = item.get("title", "")
                        link = item.get("link", "")
                        if is_hard_junk(title):
                            continue
                        writer.writerow([ticker, signal_date, title, link, term])
                        kept += 1
                        total_headlines += 1
                        ticker_headline_count += 1
                    total_searches += 1
                    print(f" {kept} headlines")
                    time.sleep(1.2)  # Google CSE rate limit

            print(f"[{i}/{len(TICKERS)}] {ticker} complete. {ticker_headline_count} headlines saved.\n")

    elapsed = time.time() - start_time
    print(f"\nBatch done. {total_headlines} headlines fetched from {total_searches} searches in {elapsed/60:.1f} minutes. Output: {OUTPUT_CSV}")

if __name__ == "__main__":
    fetch_all_headlines()
