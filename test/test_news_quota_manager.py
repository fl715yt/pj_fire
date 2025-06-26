from news_apis.google_cse_fetcher import GoogleCSEFetcher
from news_apis.gnews_fetcher import GNewsFetcher
from news_apis.brave_news_fetcher import BraveNewsFetcher
from news_apis.quota_manager import NewsQuotaManager

TEST_TICKERS = [
    ("7203", "2024-05-10"),
    ("2502", "2024-05-10"),
    ("9997", "2024-05-10"),
]

class MockExhaustedFetcher(GoogleCSEFetcher):
    def get_remaining_quota(self):
        return 0
    def fetch(self, ticker, date):
        raise Exception("Should never be called; quota is 0")

def test_quota_manager():
    # Force first fetcher to be exhausted, test fallback
    fetchers = [
        MockExhaustedFetcher(),
        GNewsFetcher(),
        BraveNewsFetcher(),
    ]
    manager = NewsQuotaManager(fetchers)
    for ticker, date in TEST_TICKERS:
        headlines, api_used = manager.fetch_news(ticker, date)
        print(f"\n[{ticker}] Used API: {api_used}, {len(headlines)} headlines")
        assert api_used in ["GNews", "BraveNews"], f"Did not fallback: {api_used}"
        for h in headlines:
            assert isinstance(h, dict), f"Headline not a dict: {h}"
            assert 'headline' in h and h['headline'], f"Headline missing: {h}"
            assert 'url' in h and h['url'], f"URL missing: {h}"
            print("  -", h['headline'], "|", h['url'])
    print("\nPASS: Quota manager fallback logic tested and output validated.")

if __name__ == "__main__":
    test_quota_manager()
