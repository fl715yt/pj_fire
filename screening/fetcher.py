import time
import yfinance as yf
import pandas as pd
import feedparser
from typing import List, Dict

CHUNK_SIZE = 100
ETF_PROXIES = {
    "TOPIX": "1306.T",
    "Nikkei225": "1321.T"
}

def fetch_stock_data_yf(tickers: List[str], sleep_seconds: int = 5) -> Dict[str, Dict[str, float]]:
    """
    Fetches latest close price and volume from yfinance.
    Chunks requests to avoid rate limits. Returns:
    {
        "ticker": { "price": ..., "volume": ... },
        ...
    }
    """
    all_data = {}

    for i in range(0, len(tickers), CHUNK_SIZE):
        chunk = tickers[i:i + CHUNK_SIZE]
        try:
            data = yf.download(
                tickers=chunk,
                period="1d",
                interval="1d",
                group_by="ticker",
                threads=True
            )
            if isinstance(data.columns, pd.MultiIndex):
                for ticker in chunk:
                    try:
                        t_data = data[ticker]
                        close = float(t_data["Close"].iloc[-1])
                        volume = int(t_data["Volume"].iloc[-1])
                        all_data[ticker] = {"price": close, "volume": volume}
                    except Exception as e:
                        print(f"[WARN] Skipping {ticker}: {e}")
            else:
                close = float(data["Close"].iloc[-1])
                volume = int(data["Volume"].iloc[-1])
                all_data[chunk[0]] = {"price": close, "volume": volume}
        except Exception as e:
            print(f"[ERROR] Failed to fetch chunk {i}-{i + CHUNK_SIZE}: {e}")
        time.sleep(sleep_seconds)

    return all_data

def fetch_market_index_from_yf(etf_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    """
    Calculate daily % change from 2-day ETF data (TOPIX, Nikkei225).
    """
    changes = {}

    for index_name, etf in ETF_PROXIES.items():
        etf_df = etf_data.get(etf)
        if isinstance(etf_df, pd.DataFrame) and len(etf_df) >= 2:
            try:
                p_yesterday = float(etf_df["Close"].iloc[0])
                p_today = float(etf_df["Close"].iloc[1])
                if p_yesterday != 0:
                    pct = round(((p_today - p_yesterday) / p_yesterday) * 100, 2)
                    changes[index_name] = pct
                    print(f"[DEBUG] {index_name} ({etf}) → Today: {p_today}, Yesterday: {p_yesterday}")
                else:
                    changes[index_name] = None
            except Exception as e:
                changes[index_name] = None
                print(f"[WARN] Error parsing {index_name}: {e}")
        else:
            changes[index_name] = None
            print(f"[WARN] No ETF data for {index_name} ({etf})")

    return changes

def fetch_news_for_ticker(ticker: str) -> List[str]:
    """
    Fetches latest news headlines for a specific ticker using Google News RSS.
    """
    try:
        query = f"{ticker} site:finance.yahoo.co.jp"
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
        feed = feedparser.parse(rss_url)
        return [entry.title for entry in feed.entries]
    except Exception as e:
        print(f"[WARN] Failed to fetch news for {ticker}: {e}")
        return []
