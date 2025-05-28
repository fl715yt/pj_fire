from screening.screener import screen_stocks

df = screen_stocks()

if df.empty:
    print("❌ No stocks passed the screener.")
else:
    print(f"✅ {len(df)} stocks passed the screener.")
    print(df[["ticker", "price_drop_pct", "rsi", "revenue_growth", "reason_category"]].head(10))
