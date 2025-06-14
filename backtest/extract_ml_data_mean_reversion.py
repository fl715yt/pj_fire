"""
PJ Fire — Mean Reversion ML Training Data Extraction (ALL FEATURES)

- Uses full config thresholds from config/config.py
- Reads tickers from topic_company_list.csv, trims one trailing zero if ticker is 5 digits and ends in 0
- Builds a day-by-day candidate list until Google CSE query count would exceed 100
- For every candidate:
    - Collects MODEL_FEATURES as of the signal date (including reason_category and green_candle_n_1)
    - Computes binary label (TP hit in 3 days: 1, else 0)
    - Outputs one row per signal
"""

import pandas as pd
import sqlite3
from tqdm import tqdm

from config.config import DROP_PCT_THRESHOLD, RSI_THRESHOLD, MIN_VOLUME, START_DATE, END_DATE
from strategies.common.screening import screen_stocks
from strategies.common.technical import get_ma_from_db
from simulation.fetch_news import fetch_news_for_ticker
from strategies.mean_reversion.reasoning import categorize_drop_reason

DB_PATH = "backtest/backtest_bt.db"
TOPIX_CSV = "topix_company_list.csv"

# 1. Read tickers
df_topic = pd.read_csv(TOPIX_CSV)
ALL_TICKERS = ["{}0".format(str(x).rstrip("0")) if len(str(x)) == 4 else str(x) for x in df_topic["ticker"]]
# print(ALL_TICKERS)

# 2. Get trading dates (from your price table or a calendar)
conn = sqlite3.connect(DB_PATH)
dates_df = pd.read_sql(
    "SELECT DISTINCT date FROM prices WHERE date >= ? AND date <= ? ORDER BY date",
    conn,
    params=[START_DATE, END_DATE]
)
ALL_DATES = dates_df["date"].tolist()

# 3. Build candidate dates list with Google CSE query budget
selected_dates = []
cumulative_queries = 0
for date in ALL_DATES:
    num_candidates = 0
    for ticker in ALL_TICKERS:
        # Only count if a candidate (otherwise don't count)
        # You may optimize this with a single screening call per date.
        pass  # We'll do screening for real below
    # Assume: 1 query per ticker if that ticker is a candidate for the date
    # We'll do this efficiently below by screening per day
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
        # Reason category (news fetch + gpt reasoning)
        try:
            news = fetch_news_for_ticker(ticker, date)
        except Exception:
            news = []
        try:
            reason_result = categorize_drop_reason(
                ticker=ticker,
                date=date,
                price_drop_pct=c.get("price_drop_pct", 0.0),
                news_items=news
            )
            reason_category = reason_result["reason_category"]
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
            "label": tp_label
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
