import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import re

# --- API modules ---
from googleapiclient.discovery import build

# CONFIG: Your main config values
from config.config import (
    SIM_DB_FILE,
    VARIANT_CSV,
    GOOGLE_API_KEY,
    GOOGLE_CSE_ID,
    GPT_DELAY_SEC,
    ALLOWED_DOMAINS,
    JUNK_DOMAINS,
    JUNK_URL_PATTERNS,
    SIGNAL_KEYWORDS,
    BONUS_KEYWORDS,
    JUNK_KEYWORDS,
    LOW_QUALITY_PATTERNS
)


# ========================
# 1. Google CSE Fetcher
# ========================

MAX_RESULTS = 10

def strip_trailing_zero(code):
    code = str(code)
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
variant_df["ticker"] = variant_df["ticker"].apply(strip_trailing_zero)
TICKER_TO_VARIANTS = {
    row["ticker"]: [v.strip() for v in str(row["variants"]).split(" / ")
                    if v.strip() and not v.strip().isdigit()]
    for _, row in variant_df.iterrows()
}

def is_allowed_domain(url):
    return any(dom in url for dom in ALLOWED_DOMAINS)

def is_junk_domain(url):
    return any(dom in url for dom in JUNK_DOMAINS)

def is_junk_url(url):
    return any(pat in url for pat in JUNK_URL_PATTERNS)

def is_junk_headline(text):
    generic = ["公式サイト", "マイページ", "会社概要", "プロフィール", "お問い合わせ", "サポート", "コーポレート", "求人", "採用情報"]
    if any(word in text for word in generic):
        return True
    if "掲示板" in text or "ADRランキング" in text:
        return True
    if re.fullmatch(r"[A-Za-z0-9\-_/ ]+", text):
        return True
    if re.fullmatch(r"\d{4,6}", text):
        return True
    if len(text) < 10 and not any(w in text for w in SIGNAL_KEYWORDS + BONUS_KEYWORDS):
        return True
    return False

def mentions_wrong_company(text, search_terms):
    return not any(v in text for v in search_terms)

def score_headline(text, url, search_terms):
    score = 0
    if any(term in text for term in SIGNAL_KEYWORDS):
        score += 5
    if any(term in text for term in BONUS_KEYWORDS):
        score += 3
    if any(domain in url for domain in ALLOWED_DOMAINS):
        score += 2
    if any(v in text for v in search_terms):
        score += 1
    if any(term in text for term in JUNK_KEYWORDS):
        score -= 3
    if is_junk_domain(url) or is_junk_url(url) or is_junk_headline(text):
        score -= 5
    if any(term in text for term in LOW_QUALITY_PATTERNS):
        score -= 1
    return score

def get_search_terms(ticker, variants):
    ticker = strip_trailing_zero(ticker)
    ticker_fw = halfwidth_to_fullwidth(ticker)
    terms = [ticker, ticker_fw] + [v for v in variants if v not in {ticker, ticker_fw}]
    return list(dict.fromkeys([t for t in terms if t and len(t) > 1]))

def fetch_news_google(ticker, signal_date):
    try:
        ticker = strip_trailing_zero(ticker)
        variants = TICKER_TO_VARIANTS.get(str(ticker), [])
        search_terms = get_search_terms(ticker, variants)
        if not search_terms:
            return "No variants or ticker for news search.", "fail: no_search_terms"

        # --- CACHE HANDLING OMITTED FOR BREVITY, ADD BACK IF NEEDED ---

        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        base_date = datetime.strptime(signal_date, "%Y-%m-%d")
        headlines = []

        for offset in range(-3, 2):  # -3 to +1 inclusive
            q_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            for term in search_terms:
                for suffix in ["", " 株", " ニュース"]:
                    query = f'{term}{suffix}'
                    try:
                        result = service.cse().list(
                            q=query,
                            cx=GOOGLE_CSE_ID,
                            lr="lang_ja",
                            num=MAX_RESULTS,
                            sort="date"
                        ).execute()
                    except Exception as e:
                        continue
                    items = result.get("items", [])
                    for item in items:
                        title = item.get("title", "")
                        link = item.get("link", "")
                        if is_junk_domain(link) or is_junk_url(link) or is_junk_headline(title):
                            continue
                        if mentions_wrong_company(title, search_terms):
                            continue
                        score = score_headline(title, link, search_terms)
                        if score > 0 or is_allowed_domain(link):
                            headlines.append((score, f"- {title} ({link})"))
                    time.sleep(GPT_DELAY_SEC)  # Rate limit by config

        seen_titles = set()
        cleaned = []
        for s, line in sorted(headlines, reverse=True):
            title = line.split(" (")[0].replace("- ", "")
            if title not in seen_titles:
                cleaned.append((s, line))
                seen_titles.add(title)
        top_n = [line for _, line in cleaned[:3]]
        headlines_str = "\n".join(top_n) if top_n else "No high-quality headlines found."
        return headlines_str, "success"
    except Exception as e:
        return "", f"fail: {e}"

# ===========================
# 2. Dummy Stubs For Others
# ===========================

def fetch_news_newsapi(ticker, signal_date):
    # TODO: Implement for real, then return (headlines, status)
    return "", "fail: not_implemented"

def fetch_news_gnews(ticker, signal_date):
    # TODO: Implement for real, then return (headlines, status)
    return "", "fail: not_implemented"

def fetch_news_newsdata(ticker, signal_date):
    # TODO: Implement for real, then return (headlines, status)
    return "", "fail: not_implemented"

# ===========================
# 3. Multi-API Logic
# ===========================

# Add/remove as needed
NEWS_API_POOL = [
    {"name": "GoogleCSE",  "func": fetch_news_google,   "quota": 100, "used": 0},
    {"name": "NewsAPI",    "func": fetch_news_newsapi,  "quota": 100, "used": 0},
    {"name": "GNews",      "func": fetch_news_gnews,    "quota": 100, "used": 0},
    {"name": "NewsDataIO", "func": fetch_news_newsdata, "quota": 100, "used": 0},
]

def fetch_news_for_ticker(ticker, signal_date):
    """
    Tries each enabled news API in order, returns (headlines, api_used, api_status).
    Rotates across APIs based on quota.
    """
    for api in NEWS_API_POOL:
        if api["used"] >= api["quota"]:
            continue
        try:
            headlines, status = api["func"](ticker, signal_date)
            api["used"] += 1
            if status == "success" and headlines:
                return headlines, api["name"], status
        except Exception as e:
            return "", api["name"], f"fail: {e}"
    return "", "none", "all_failed"
