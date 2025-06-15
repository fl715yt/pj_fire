# news_apis/brave_news_fetcher.py

from .base_fetcher import BaseNewsFetcher
from datetime import datetime, timedelta
import time
import re
import pandas as pd
import urllib.parse
import requests
from simulation.utils import get_ticker_to_variants
from simulation.logger import log_warning, log_error
from config.config import (
    BRAVE_API_KEY,          # <-- must be set in your config/env
    GPT_DELAY_SEC,
    DAILY_QUOTAS,
    VARIANT_CSV,
    ALLOWED_DOMAINS,
    JUNK_DOMAINS,
    JUNK_URL_PATTERNS,
    SIGNAL_KEYWORDS,
    BONUS_KEYWORDS,
    JUNK_KEYWORDS,
    LOW_QUALITY_PATTERNS,
    MAX_NEWS_RESULTS
)

MAX_NEWS_RESULTS = 10  # Brave default is 10 per request
ENDPOINT = "https://api.search.brave.com/res/v1/news/search"

class BraveNewsFetcher(BaseNewsFetcher):
    def __init__(self):
        self.api_key = BRAVE_API_KEY
        self.quota_per_day = DAILY_QUOTAS.get("brave_news", 100)  # Set in config
        self.queries_today = 0
        self.variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
        self.TICKER_TO_VARIANTS = get_ticker_to_variants()

    def strip_trailing_zero(self, code):
        code = str(code)
        if len(code) == 5 and code.endswith("0"):
            return code[:-1]
        return code

    def halfwidth_to_fullwidth(self, s):
        return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

    def get_search_terms(self, ticker, variants):
        ticker = self.strip_trailing_zero(ticker)
        ticker_fw = self.halfwidth_to_fullwidth(ticker)
        terms = [ticker, ticker_fw] + [v for v in variants if v not in {ticker, ticker_fw}]
        return list(dict.fromkeys([t for t in terms if t and len(t) > 1]))

    def is_allowed_domain(self, url):
        return any(dom in url for dom in ALLOWED_DOMAINS)

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
        return not any(v in text for v in search_terms)

    def score_headline(self, text, url, search_terms):
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
        if self.is_junk_domain(url) or self.is_junk_url(url) or self.is_junk_headline(text):
            score -= 5
        if any(term in text for term in LOW_QUALITY_PATTERNS):
            score -= 1
        return score

    def fetch(self, ticker, signal_date):
        if self.get_remaining_quota() <= 0:
            return []

        ticker = self.strip_trailing_zero(ticker)
        variants = self.TICKER_TO_VARIANTS.get(str(ticker), [])
        search_terms = self.get_search_terms(ticker, variants)
        if not search_terms:
            print(f"[WARN] No search terms for ticker {ticker}.")
            return []

        base_date = datetime.strptime(signal_date, "%Y-%m-%d")
        headlines = []

        for offset in range(-3, 2):  # -3 to +1 inclusive
            q_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            for term in search_terms:
                params = {
                    "q": term,
                    "count": MAX_NEWS_RESULTS,
                    "lang": "ja",  # Prefer Japanese news
                    "freshness": "day",  # Brave freshness values: "day", "week", "month"
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
                    if response.status_code != 200:
                        print(f"[BraveNewsFetcher] HTTP {response.status_code}: {response.text}")
                        continue
                    data = response.json()
                    articles = data.get("results", [])
                except Exception as e:
                    print(f"[BraveNewsFetcher] Failed for {ticker} ({term}) on {q_date}: {e}")
                    self.log_query()
                    continue

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
                time.sleep(GPT_DELAY_SEC)  # To enforce 1qps rate limit

        # Deduplicate by headline text
        seen_titles = set()
        cleaned = []
        for s, line in sorted(headlines, reverse=True):
            title = line["headline"]
            if title not in seen_titles:
                cleaned.append(line)
                seen_titles.add(title)

        top_n = cleaned[:3]
        return top_n

    def get_remaining_quota(self):
        return self.quota_per_day - self.queries_today

    def log_query(self):
        self.queries_today += 1

    def get_name(self):
        return "BraveNews"

