import pandas as pd
import sqlite3
from tqdm import tqdm

from config.config import DROP_PCT_THRESHOLD, RSI_THRESHOLD, MIN_VOLUME, START_DATE, END_DATE
from strategies.common.screening import screen_stocks
from strategies.common.technical import get_ma_from_db
from news_apis.quota_manager import NewsQuotaManager
from news_apis.google_cse_fetcher import GoogleCSEFetcher
from news_apis.gnews_fetcher import GNewsFetcher
from news_apis.brave_news_fetcher import BraveNewsFetcher
from news_apis.newsapi_fetcher import NewsAPIFetcher
from strategies.mean_reversion.reasoning import categorize_drop_reason

DB_PATH = "backtest/backtest_bt.db"
TOPIX_CSV = "topix_company_list.csv"

# 1. Read tickers
df_topic = pd.read_csv(TOPIX_CSV)
ALL_TICKERS = ["{}0".format(str(x).rstrip("0")) if len(str(x)) == 4 else str(x) for x in df_topic["ticker"]]

# 2. Get trading dates (from your price table or a calendar)
conn = sqlite3.connect(DB_PATH)
dates_df = pd.read_sql(
    "SELECT DISTINCT date FROM prices WHERE date >= ? AND date <= ? ORDER BY date",
    conn,
    params=[START_DATE, END_DATE]
)
ALL_DATES = dates_df["date"].tolist()

# 3. Build candidate dates list with API query budget
selected_dates = []
cumulative_queries = 0
for date in ALL_DATES:
    candidates = screen_stocks(
        conn,
        date,
        drop_pct_threshold=DROP_PCT_THRESHOLD,
        rsi_threshold=RSI_THRESHOLD,
        min_volume=MIN_VOLUME,
        strategy="mean_reversion"
    )
    unique_candidate_tickers = set([c["ticker"] for c in candidates])
    n_new_queries = len(unique_candidate_tickers)
    if cumulative_queries + n_new_queries > 100:
        break
    selected_dates.append(date)
    cumulative_queries += n_new_queries

# 4. Extract features and labels for all candidates within budget
rows = []
for date in tqdm(selected_dates, desc="Extracting features per date"):
    candidates = screen_stocks(
        conn,
        date,
        drop_pct_threshold=DROP_PCT_THRESHOLD,
        rsi_threshold=RSI_THRESHOLD,
        min_volume=MIN_VOLUME,
        strategy="mean_reversion"
    )
    for c in candidates:
        ticker = c["ticker"]
        # News fetching and logging API source/result
        fetchers = [GoogleCSEFetcher(), GNewsFetcher(), BraveNewsFetcher(), NewsAPIFetcher()]
        news_manager = NewsQuotaManager(fetchers)
        try:
            headlines, api_used = news_manager.fetch_news(ticker, date)
        except Exception as e:
            headllines = []
            api_used = "none"
        # Reason category (news + GPT reasoning)
        try:
            reason_result = categorize_drop_reason(
                ticker=ticker,
                date=date,
                price_drop_pct=c.get("price_drop_pct", 0.0),
                news_items=headlines
            )
            reason_category = reason_result.get("reason_category", "unknown")]
        except Exception:
            reason_category = "unknown"

        # Green candle on previous day (n-1)
        prev_day_query = """
            SELECT open, close FROM prices WHERE ticker = ? AND date = (
                SELECT date FROM prices
                WHERE ticker = ? AND date < ?
                ORDER BY date DESC LIMIT 1
            )
        """
        prev_row = conn.execute(prev_day_query, (ticker, ticker, date)).fetchone()
        if prev_row:
            open_n_1, close_n_1 = prev_row
            green_candle_n_1 = 1 if close_n_1 > open_n_1 else 0
        else:
            green_candle_n_1 = 0

        # TP hit within 3 days (label)
        ma_value = get_ma_from_db(conn, ticker, date, window=5)
        tp_label = 0
        if ma_value is not None:
            price_query = """
                SELECT close FROM prices WHERE ticker = ? AND date > ?
                ORDER BY date ASC LIMIT 3
            """
            future_prices = conn.execute(price_query, (ticker, date)).fetchall()
            for p in future_prices:
                if p[0] >= ma_value:
                    tp_label = 1
                    break

        # All other model features from candidate dict, fill missing as 0.0
        features = {f: c.get(f, 0.0) for f in [
            "price_drop_pct", "rsi_14", "ma5", "ma25", "volume_spike",
            "market_mean_return", "market_volatility", "sector_mean_return", "sector_volatility",
            "zscore_20", "atr_14", "volatility5", "candlestick_reversal",
            "eps", "eps_yoy", "profit", "profit_yoy", "revenue", "revenue_yoy", "piotroski_f_score"
        ]}

        row = {
            "date": date,
            "ticker": ticker,
            **features,
            "reason_category": reason_category,
            "green_candle_n_1": green_candle_n_1,
            "label": tp_label,
            "news_api_used": api_used,
            "news_api_status": api_status,
            "headlines": news
        }
        rows.append(row)

def get_price_on_date(conn, ticker, date):
    """
    Returns the close price for a ticker on a specific date.
    """
    query = "SELECT close FROM prices WHERE ticker = ? AND date = ?"
    row = conn.execute(query, (ticker, date)).fetchone()
    return float(row[0]) if row else None

# 5. Save final dataframe
df = pd.DataFrame(rows)
df = df.sort_values("date").reset_index(drop=True)
df.to_csv("X_full_mean_reversion.csv", index=False)
df[["label"]].to_csv("y_full_mean_reversion.csv", index=False)
print(f"Done. Wrote {len(df)} rows to X_full_mean_reversion.csv")
