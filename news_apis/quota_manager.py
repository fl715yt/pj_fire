# news_apis/quota_manager.py

from datetime import datetime
import csv

class NewsQuotaManager:
    def __init__(self, fetchers, log_csv_path="news_fetch_log.csv"):
        """
        fetchers: list of BaseNewsFetcher instances (ordered by priority)
        log_csv_path: path to CSV log file (default: project root)
        """
        self.fetchers = fetchers
        self.log_csv_path = log_csv_path

    def fetch_news(self, ticker, date):
        """
        Try each fetcher in order. Use the first with quota that returns results.
        Log the API used and all results.
        Returns: (headlines, api_used)
        """
        for fetcher in self.fetchers:
            if fetcher.get_remaining_quota() <= 0:
                continue
            try:
                headlines = fetcher.fetch(ticker, date)
                api_name = fetcher.get_name()
                self.log_fetch(ticker, date, api_name, bool(headlines), headlines)
                if headlines:
                    return headlines, api_name
            except Exception as e:
                print(f"[{fetcher.get_name()}] Exception: {e}")
                self.log_fetch(ticker, date, fetcher.get_name(), False, [])
        # All APIs exhausted or failed
        self.log_fetch(ticker, date, "none", False, [])
        return [], None

    def log_fetch(self, ticker, date, api_name, success, headlines):
        """
        Append a row for each headline fetched.
        If no headlines, write a single row with blanks.
        """
        with open(self.log_csv_path, mode="a", encoding="utf-8", newline='') as f:
            writer = csv.writer(f)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not headlines:
                writer.writerow([
                    ticker, date, api_name, "fail", "", "", "", "", now
                ])
            else:
                for h in headlines:
                    writer.writerow([
                        ticker,
                        date,
                        api_name,
                        "success" if success else "fail",
                        h.get("headline", ""),
                        h.get("url", ""),
                        h.get("date", ""),
                        h.get("source", ""),
                        now
                    ])
