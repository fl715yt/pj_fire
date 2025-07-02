import sys
from news_apis.gnews_fetcher import GNewsFetcher

# List of (ticker, date) pairs for test coverage
TEST_TICKERS = [
    ("9101", "2025-06-23"),   # 日本郵船、ドイツ金融システム会社を買収
    ("6723", "2025-06-23"),   # ルネサス、2500億円損失計上
    ("7453", "2025-06-25"),   # 良品計画、太陽光発電で新会社
    ("4452", "2025-06-18"),   # 花王、「キュレル」16万個回収
]

def assert_valid_headline(h, ticker):
    assert isinstance(h, dict), f"Headline is not a dict: {h}"
    assert 'headline' in h and h['headline'], f"No headline in: {h}"
    assert 'url' in h and h['url'], f"No URL in: {h}"

def test_gnews_fetcher():
    fetcher = GNewsFetcher()
    print(f"\n=== Testing {fetcher.get_name()} (GNews Primary) ===")
    for ticker, date in TEST_TICKERS:
        try:
            print(f"  {ticker} / {date} ...", end="")
            headlines = fetcher.fetch(ticker, date)
            print(f" got {len(headlines)} headlines")
            for h in headlines:
                print("    -", h.get("headline", ""), "|", h.get("url", ""))
                assert_valid_headline(h, ticker)
            if len(headlines) == 0:
                print(f"    [WARN] No headlines returned for {ticker}")
        except Exception as e:
            print(f"    [ERROR] {type(e).__name__}: {e}")
            raise
    print("\nGNews fetcher tests completed.")

if __name__ == "__main__":
    test_gnews_fetcher()
    print("PASS: GNews fetcher ran and validated output.")
