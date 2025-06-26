# news_apis/google_cse_fetcher.py

from .base_fetcher import BaseNewsFetcher
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
import time
import re
import pandas as pd
import random
import ssl
import csv
import os
import pytz
from config.config import (
    GOOGLE_API_KEY,
    GOOGLE_CSE_ID,
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
    GOOGLE_CSE_USE_NEWS_SUFFIX
)

QUOTA_CSV_PATH = "google_cse_quota_log.csv"
JST = pytz.timezone("Asia/Tokyo")
RESET_HOUR = 9  # 9AM Tokyo time

class GoogleCSEFetcher(BaseNewsFetcher):
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.quota_per_day = DAILY_QUOTAS.get("google_cse", 100)

        self.variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
        self.variant_df['ticker'] = self.variant_df['ticker'].str.strip()
        self.variant_df['ticker'] = self.variant_df['ticker'].apply(
            lambda x: x[:-1] if len(x) > 4 and x.endswith('0') else x
        )
        self.ticker_row_map = {str(row["ticker"]): row for _, row in self.variant_df.iterrows()}

        # Make sure CSV exists
        if not os.path.isfile(QUOTA_CSV_PATH):
            with open(QUOTA_CSV_PATH, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date_str", "queries_used"])

    def _get_jst_now(self):
        return datetime.now(JST)

    def _get_reset_window(self):
        """
        Returns the string key for the quota window, e.g. "2024-07-01_09"
        Quota resets every day at 09:00 JST
        """
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
        # Read all
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

    def strip_trailing_zero(self, code):
        code = str(code)
        if len(code) == 5 and code.endswith("0"):
            return code[:-1]
        return code

    def halfwidth_to_fullwidth(self, s):
        return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

    def build_company_product_queries(self, ticker):
        row = self.ticker_row_map.get(str(ticker))
        if row is None:
            print(f"[WARN] No variants row for ticker {ticker}")
            return []

        company_names = set()
        if pd.notna(row.get("company_name")):
            n = row["company_name"].strip()
            if n and not n.isnumeric():
                company_names.add(n)
        if pd.notna(row.get("company_name_variants")):
            for v in str(row["company_name_variants"]).split("|"):
                v = v.strip()
                if v and not v.isnumeric():
                    company_names.add(v)

        product_names = set()
        if pd.notna(row.get("product_names")):
            for v in str(row["product_names"]).split("|"):
                v = v.strip()
                if v and not v.isnumeric():
                    product_names.add(v)

        company_names = {n for n in company_names if n}
        product_names = {n for n in product_names if n}

        def make_block(names):
            if not names:
                return None
            if len(names) > 1:
                return "(" + " OR ".join([f'"{n}"' for n in names]) + ")"
            else:
                return f'"{list(names)[0]}"'

        company_block = make_block(company_names)
        product_block = make_block(product_names)

        queries = []
        if company_block and product_block:
            queries.append(f"{company_block} AND {product_block}")
        if company_block:
            queries.append(f"{company_block}")
        if product_block and not company_block:
            queries.append(f"{product_block}")
        if not queries:
            print(f"[WARN] No company or product names for ticker {ticker}, using ticker fallback.")
            queries.append(f'"{ticker}" OR "{self.halfwidth_to_fullwidth(ticker)}"')

        if GOOGLE_CSE_USE_NEWS_SUFFIX:
            queries = [q + " ニュース" for q in queries]
        return queries

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

    def score_headline(self, text, url, search_terms=None):
        score = 0
        if any(term in text for term in SIGNAL_KEYWORDS):
            score += 5
        if any(term in text for term in BONUS_KEYWORDS):
            score += 3
        if any(domain in url for domain in NEWS_DOMAINS_WHITELIST):
            score += 2
        if any(term in text for term in JUNK_KEYWORDS):
            score -= 3
        if self.is_junk_domain(url) or self.is_junk_url(url) or self.is_junk_headline(text):
            score -= 5
        if any(term in text for term in LOW_QUALITY_PATTERNS):
            score -= 1
        return score

    def fetch(self, ticker, signal_date):
        if self.get_remaining_quota() <= 0:
            print(f"[GoogleCSEFetcher] Daily quota exhausted.")
            return []

        ticker = self.strip_trailing_zero(ticker)
        queries = self.build_company_product_queries(ticker)
        if not queries:
            print(f"[WARN] No search terms for ticker {ticker}.")
            return []

        try:
            service = build("customsearch", "v1", developerKey=self.api_key)
        except Exception as e:
            print(f"[ERROR] Google CSE API error: {e}")
            return []

        base_date = datetime.strptime(signal_date, "%Y-%m-%d")
        headlines = []
        queries_run = 0

        for offset in range(-3, 2):  # -3 to +1 inclusive
            q_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            for query in queries:
                print(f"[GoogleCSEFetcher] Boolean Query: '{query}' for ticker {ticker} ({q_date})")
                try:
                    result = service.cse().list(
                        q=query,
                        cx=self.cse_id,
                        lr="lang_ja",
                        num=MAX_NEWS_RESULTS,
                        sort="date"
                    ).execute()
                    self.log_query()
                except KeyboardInterrupt:
                    print("[ERROR] Manual interrupt. Exiting fetch early.")
                    return []
                except ssl.SSLError as ssl_err:
                    print(f"[ERROR] SSL Error: {ssl_err}")
                    continue
                except Exception as e:
                    print(f"\u26a0\ufe0f Google CSE failed for {ticker} ({query}) on {q_date}: {e}")
                    continue

                items = result.get("items", [])
                for item in items:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    if self.is_junk_domain(link) or self.is_junk_url(link) or self.is_junk_headline(title):
                        continue
                    # Only allow whitelisted news domains
                    if not self.is_allowed_domain(link):
                        continue
                    score = self.score_headline(title, link)
                    if score > 0:
                        headlines.append((score, {
                            "headline": title,
                            "date": q_date,
                            "url": link,
                            "source": "GoogleCSE"
                        }))
                time.sleep(GPT_DELAY_SEC + random.uniform(0.3, 1.2))
                queries_run += 1

        # Deduplicate by headline text
        seen_titles = set()
        cleaned = []
        for s, line in sorted(headlines, key=lambda x: x[0], reverse=True):
            title = line["headline"]
            if title not in seen_titles:
                cleaned.append(line)
                seen_titles.add(title)

        top_n = cleaned[:MAX_NEWS_RESULTS]
        return top_n


    def get_remaining_quota(self):
        used = self._read_quota()
        return self.quota_per_day - used

    def log_query(self):
        used = self._read_quota()
        self._write_quota(used + 1)

    def get_name(self):
        return "GoogleCSE"
