# news_apis/brave_news_fetcher.py

from .base_fetcher import BaseNewsFetcher
from datetime import datetime, timedelta
import time
import re
import pandas as pd
import urllib.parse
import requests
import random
import csv
import os
import pytz
from simulation.logger import log_warning, log_error
from config.config import (
    BRAVE_API_KEY,
    GPT_DELAY_SEC,
    DAILY_QUOTAS,
    VARIANT_CSV,
    # ALLOWED_DOMAINS,
    NEWS_DOMAINS_WHITELIST,
    JUNK_DOMAINS,
    JUNK_URL_PATTERNS,
    SIGNAL_KEYWORDS,
    BONUS_KEYWORDS,
    JUNK_KEYWORDS,
    LOW_QUALITY_PATTERNS,
    MAX_NEWS_RESULTS,
    MAX_VARIANTS_PER_TICKER_BRAVE
)

ENDPOINT = "https://api.search.brave.com/res/v1/news/search"
QUOTA_CSV_PATH = "brave_quota_log.csv"
JST = pytz.timezone("Asia/Tokyo")
RESET_HOUR = 9  # 9AM Tokyo time

class BraveNewsFetcher(BaseNewsFetcher):
    def __init__(self):
        self.api_key = BRAVE_API_KEY
        self.quota_per_day = DAILY_QUOTAS.get("brave_news", 100)
        self.variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
        self.variant_df['ticker'] = self.variant_df['ticker'].str.strip()
        self.variant_df['ticker'] = self.variant_df['ticker'].apply(
            lambda x: x[:-1] if len(x) > 4 and x.endswith('0') else x
        )
        self.TICKER_TO_COMPANY_VARIANTS, self.TICKER_TO_PRODUCT_NAMES = self.build_ticker_to_variants()
        # Ensure quota file exists
        if not os.path.isfile(QUOTA_CSV_PATH):
            with open(QUOTA_CSV_PATH, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date_str", "queries_used"])

    def _get_jst_now(self):
        return datetime.now(JST)

    def _get_reset_window(self):
        now = self._get_jst_now()
        reset_today = now.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)
        if now < reset_today:
            reset_date = (reset_today - timedelta(days=1)).date()
        else:
            reset_date = reset_today.date()
        return reset_date.strftime("%Y-%m-%d")

    def _read_quota(self):
        window = self._get_reset_window()
        if not os.path.isfile(QUOTA_CSV_PATH):
            return 0
        with open(QUOTA_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date_str"] == window:
                    return int(row["queries_used"])
        return 0

    def _write_quota(self, used):
        window = self._get_reset_window()
        rows = []
        found = False
        if os.path.isfile(QUOTA_CSV_PATH):
            with open(QUOTA_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["date_str"] == window:
                        rows.append({"date_str": window, "queries_used": str(used)})
                        found = True
                    else:
                        rows.append(row)
        if not found:
            rows.append({"date_str": window, "queries_used": str(used)})
        with open(QUOTA_CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date_str", "queries_used"])
            writer.writeheader()
            writer.writerows(rows)

    def build_ticker_to_variants(self):
        company_map = {}
        product_map = {}
        for _, row in self.variant_df.iterrows():
            ticker = str(row["ticker"])
            company_variants = set()
            if pd.notna(row.get("company_name")):
                company_variants.add(row["company_name"].strip())
            for col in ["variants", "company_name_variants"]:
                if pd.notna(row.get(col)):
                    for v in re.split(r"[/|]", str(row[col])):
                        v = v.strip().strip('"').strip("'")
                        if v and not v.isnumeric() and len(v) > 1:
                            company_variants.add(v)
            company_map[ticker] = sorted(company_variants)
            product_names = set()
            if pd.notna(row.get("product_names")):
                for v in re.split(r"[/|]", str(row["product_names"])):
                    v = v.strip().strip('"').strip("'")
                    if v and not v.isnumeric() and len(v) > 1:
                        product_names.add(v)
            product_map[ticker] = sorted(product_names)
        return company_map, product_map

    def strip_trailing_zero(self, code):
        code = str(code)
        if len(code) == 5 and code.endswith("0"):
            return code[:-1]
        return code

    def get_query_terms(self, ticker):
        ticker = self.strip_trailing_zero(ticker)
        company_variants = self.TICKER_TO_COMPANY_VARIANTS.get(ticker, [])[:MAX_VARIANTS_PER_TICKER_BRAVE]
        product_names = self.TICKER_TO_PRODUCT_NAMES.get(ticker, [])[:MAX_VARIANTS_PER_TICKER_BRAVE]
        return company_variants, product_names

    def is_allowed_domain(self, url):
        # return any(dom in url for dom in ALLOWED_DOMAINS)
        return any(dom in url for dom in NEWS_DOMAINS_WHITELIST)

    def is_junk_domain(self, url):
        return any(dom in url for dom in JUNK_DOMAINS)

    def is_junk_url(self, url):
        return any(pat in url for pat in JUNK_URL_PATTERNS)

    def is_junk_headline(self, text):
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

    def mentions_wrong_company(self, text, search_terms):
        # Soft match: at least one search term must appear in the headline text.
        return not any(v in text for v in search_terms)

    def score_headline(self, text, url, search_terms):
        score = 0
        if any(term in text for term in SIGNAL_KEYWORDS):
            score += 5
        if any(term in text for term in BONUS_KEYWORDS):
            score += 3
        # if any(domain in url for domain in ALLOWED_DOMAINS):
        if any(domain in url for domain in NEWS_DOMAINS_WHITELIST):
            score += 2
        if any(v in text for v in search_terms):
            score += 1
        if any(term in text for term in JUNK_KEYWORDS):
            score -= 3
        if self.is_junk_domain(url) or self.is_junk_url(url) or self.is_junk_headline(text):
            score -= 5
        if any(term in text for term in LOW_QUALITY_PATTERNS):
            score -= 1
        return score

    def fetch(self, ticker, signal_date):
        if self.get_remaining_quota() <= 0:
            print(f"[BraveNewsFetcher] Daily quota exhausted.")
            return []

        ticker = self.strip_trailing_zero(ticker)
        company_variants, product_names = self.get_query_terms(ticker)
        if not (company_variants or product_names):
            print(f"[WARN] No search terms for ticker {ticker}.")
            return []

        base_date = datetime.strptime(signal_date, "%Y-%m-%d")
        headlines = []
        queries_run = 0

        for offset in range(-3, 2):  # -3 to +1 inclusive
            q_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            day_queries = []
            for name in company_variants:
                day_queries.append((f'"{name}"', company_variants + product_names))
            for pname in product_names:
                day_queries.append((f'"{pname}"', company_variants + product_names))
            if company_variants and product_names:
                day_queries.append(
                    (f'"{company_variants[0]}" AND "{product_names[0]}"', company_variants + product_names)
                )
            for query, search_terms in day_queries:
                self._brave_query(query, ticker, q_date, headlines, search_terms)
                queries_run += 1
                time.sleep(GPT_DELAY_SEC + random.uniform(0.25, 0.8))

        # Deduplicate by headline text
        seen_titles = set()
        cleaned = []
        for s, line in sorted(headlines, key=lambda x: x[0], reverse=True):
            title = line["headline"]
            if title not in seen_titles:
                cleaned.append(line)
                seen_titles.add(title)
        
        if not cleaned:
            print(f"[WARN] No headlines for ticker {ticker} after domain filtering.")

        print(f"[BraveNewsFetcher] Total queries run: {queries_run} for ticker {ticker}")
        return cleaned[:MAX_NEWS_RESULTS]

    def _brave_query(self, query, ticker, q_date, headlines, search_terms):
        print(f"[BraveNewsFetcher] Query: {query} for ticker {ticker} ({q_date})")
        params = {
            "q": query,
            "count": MAX_NEWS_RESULTS,
            "lang": "ja",
            "freshness": "day",
            "from": q_date + "T00:00:00Z",
            "to": q_date + "T23:59:59Z",
        }
        url = ENDPOINT + "?" + urllib.parse.urlencode(params)
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            self.log_query()
            if response.status_code == 429:
                log_warning(f"[BraveNewsFetcher] HTTP 429: Rate limited for ticker {ticker} ({query}) on {q_date}")
                time.sleep(2 + random.uniform(0.5, 1.5))
                return
            if response.status_code != 200:
                print(f"[BraveNewsFetcher] HTTP {response.status_code}: {response.text}")
                return
            data = response.json()
            articles = data.get("results", [])
        except Exception as e:
            log_error(f"[BraveNewsFetcher] Failed for {ticker} ({query}) on {q_date}: {e}")
            self.log_query()
            return

        for article in articles:
            title = article.get("title", "")
            link = article.get("url", "")
            if self.is_junk_domain(link) or self.is_junk_url(link) or self.is_junk_headline(title):
                continue
            if self.mentions_wrong_company(title, search_terms):
                continue
            score = self.score_headline(title, link, search_terms)
            if score > 0 or self.is_allowed_domain(link):
                headlines.append((score, {
                    "headline": title,
                    "date": q_date,
                    "url": link,
                    "source": "BraveNews"
                }))

    def get_remaining_quota(self):
        used = self._read_quota()
        return self.quota_per_day - used

    def log_query(self):
        used = self._read_quota()
        self._write_quota(used + 1)

    def get_name(self):
        return "BraveNews"
