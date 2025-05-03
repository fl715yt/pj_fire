from screening.fetcher import (
    fetch_stock_data_from_jquants,
    fetch_market_index_from_jquants,
    fetch_news_for_ticker
)

import os

# ========== Settings ==========
API_TOKEN = os.getenv("JQUANTS_API_TOKEN")  # You must set this in your .env or environment
# ===============================

if __name__ == "__main__":
    # --- Fetch today's stock data ---
    print("===== Fetching today's stock data =====")
    today_stock_data = fetch_stock_data_from_jquants(API_TOKEN)
    print(f"✅ Fetched {len(today_stock_data)} stocks and ETF proxies.")
    for ticker, info in list(today_stock_data.items())[:5]:  # Show sample
        print(f"{ticker}: {info}")

    # --- Fetch yesterday's stock data ---
    print("\n===== Fetching yesterday's stock data =====")
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_stock_data = fetch_stock_data_from_jquants(API_TOKEN, date=yesterday)
    print(f"✅ Fetched {len(yesterday_stock_data)} stocks for yesterday.")

    # --- Compute market index % changes ---
    print("\n===== Calculating market index changes =====")
    market_data = fetch_market_index_from_jquants(today_stock_data, yesterday_stock_data)
    print(f"✅ Market index changes: {market_data}")

    # --- Fetch news headlines for sample ticker ---
    print("\n===== Fetching sample news headlines =====")
    sample_ticker = list(today_stock_data.keys())[0]  # Pick first ticker
    headlines = fetch_news_for_ticker(sample_ticker)
    print(f"✅ News for {sample_ticker}:")
    for headline in headlines:
        print(f"- {headline}")
