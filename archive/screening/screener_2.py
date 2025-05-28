import sqlite3
import pandas as pd
from datetime import datetime, timedelta

from screening.reasoning import attach_reason_to_stocks

DB_FILE = "db/pj_fire.db"

def screen_stocks():
    conn = sqlite3.connect(DB_FILE)

    # ─── Load Daily Stock Data ───────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("SELECT * FROM stock_snapshots WHERE date = ?", (today,))
    stock_rows = cur.fetchall()
    stock_df = pd.DataFrame(stock_rows, columns=["date", "ticker", "close_price", "volume"])
    if stock_df.empty:
        print("⚠️ No stock snapshot data found for today.")
        return pd.DataFrame()

    # ─── Load Fundamentals ───────────────────────────
    cur.execute("""
        SELECT f1.ticker,
               f1.revenue AS latest_revenue,
               f2.revenue AS prev_revenue,
               f1.net_income,
               f1.equity_ratio,
               f1.tdnet_risk
        FROM stock_fundamentals f1
        LEFT JOIN stock_fundamentals f2
          ON f1.ticker = f2.ticker AND CAST(f2.fiscal_year AS INTEGER) = CAST(f1.fiscal_year AS INTEGER) - 1
    """)
    fund_rows = cur.fetchall()
    fund_df = pd.DataFrame(fund_rows, columns=[
        "ticker", "latest_revenue", "prev_revenue", "net_income", "equity_ratio", "tdnet_risk"
    ])

    # ─── Merge & Calculate Derived Fields ────────────
    df = pd.merge(stock_df, fund_df, on="ticker", how="inner")
    df["price_yesterday"] = df["close_price"]  # fallback in case no yesterday data available
    df["price_drop_pct"] = 0.0  # Placeholder — real drop % to be updated below
    df["rsi"] = 30  # Placeholder — insert actual RSI later
    df["revenue_growth"] = ((df["latest_revenue"] - df["prev_revenue"]) / df["prev_revenue"]).round(3)
    df = df.dropna(subset=["latest_revenue", "prev_revenue", "net_income", "equity_ratio"])

    # ─── Apply Basic Filters ─────────────────────────
    df = df[df["net_income"] > 0]
    df = df[df["revenue_growth"] >= 0]
    df = df[(df["equity_ratio"] > 33)]
    df = df[df["tdnet_risk"].fillna(0) == 0]

    # ─── Calculate Actual Price Drop % ───────────────
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    cur.execute("SELECT ticker, close_price FROM stock_snapshots WHERE date = ?", (yesterday,))
    y_rows = cur.fetchall()
    df_yesterday = pd.DataFrame(y_rows, columns=["ticker", "price_yesterday"])

    df = pd.merge(df, df_yesterday, on="ticker", how="left", suffixes=("", "_y"))
    df["price_drop_pct"] = ((df["price_yesterday_y"] - df["close_price"]) / df["price_yesterday_y"] * 100).round(2)
    df.drop(columns=["price_yesterday_y"], inplace=True)

    # ─── Filter by Price Drop Threshold (e.g. > 3%) ──
    df = df[df["price_drop_pct"] > 3]

    # ─── Add Reason Category via GPT ─────────────────
    df = attach_reason_to_stocks(df)

    conn.close()
    return df.reset_index(drop=True)
