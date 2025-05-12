import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime
from config.backtest_config import BACKTEST_START, BACKTEST_END, RSI_PERIOD

DB_FILE = "db/backtest.db"
TOPIX_CSV = "db/topix_stocks.csv"
CHUNK_SIZE = 100

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ma(series, window=5):
    return series.rolling(window=window).mean()

def fetch_chunked_data(tickers):
    all_data = []
    for i in range(0, len(tickers), CHUNK_SIZE):
        chunk = tickers[i:i + CHUNK_SIZE]
        print(f"📈 Fetching {len(chunk)} tickers: {chunk}")
        try:
            data = yf.download(chunk, start=BACKTEST_START, end=BACKTEST_END, group_by='ticker', auto_adjust=False, threads=True)
            if not isinstance(data.columns, pd.MultiIndex):
                print(f"[WARN] Skipping single-ticker fetch for: {chunk}")
                continue
            for ticker in chunk:
                try:
                    t_df = data[ticker].copy()
                    if t_df.empty:
                        continue
                    t_df["ticker"] = ticker
                    t_df["rsi"] = calculate_rsi(t_df["Close"], RSI_PERIOD)
                    t_df["ma5"] = calculate_ma(t_df["Close"], 5)
                    t_df = t_df.reset_index()
                    t_df = t_df[["Date", "ticker", "Open", "High", "Low", "Close", "Volume", "rsi", "ma5"]]
                    t_df.columns = ["date", "ticker", "open", "high", "low", "close", "volume", "rsi", "ma5"]
                    all_data.append(t_df)
                except Exception as e:
                    print(f"[ERROR] Failed processing {ticker}: {e}")
        except Exception as e:
            print(f"[ERROR] YF fetch failed: {e}")
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def save_to_db(df, conn):
    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        try:
            cur.execute("""
                INSERT OR REPLACE INTO bt_prices
                (date, ticker, open, high, low, close, volume, rsi, ma5)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["date"].strftime("%Y-%m-%d") if isinstance(row["date"], pd.Timestamp) else row["date"],
                row["ticker"],
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row["volume"]),
                float(row["rsi"]) if pd.notna(row["rsi"]) else None,
                float(row["ma5"]) if pd.notna(row["ma5"]) else None
            ))
            inserted += 1
        except Exception as e:
            print(f"[ERROR] Insert failed for {row['ticker']} on {row['date']}: {e}")
    print(f"✅ Inserted {inserted} rows into bt_prices")

def main():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS bt_prices")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bt_prices (
            date TEXT,
            ticker TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            rsi REAL,
            ma5 REAL,
            PRIMARY KEY (date, ticker)
        )
    """)
    tickers = pd.read_csv(TOPIX_CSV)["Ticker"].tolist()
    df = fetch_chunked_data(tickers)
    if not df.empty:
        save_to_db(df, conn)
    else:
        print("⚠️ No data fetched.")
    conn.commit()
    conn.close()
    print("✅ Backtest price storage complete.")

if __name__ == "__main__":
    main()
