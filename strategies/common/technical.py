"""
PJ Fire — Technical Indicators
All constants and windows are referenced from config if needed.
"""

import pandas as pd
import numpy as np

def calc_rsi(prices, window=14):
    delta = prices.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(span=window, adjust=False).mean()
    ema_down = down.ewm(span=window, adjust=False).mean()
    rs = ema_up / (ema_down + 1e-8)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_sma(prices, window):
    return prices.rolling(window=window).mean()

def calc_ema(prices, window):
    return prices.ewm(span=window, adjust=False).mean()

def calc_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(prices, fast)
    ema_slow = calc_ema(prices, slow)
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

def calc_volatility(prices, window=20):
    return prices.pct_change().rolling(window).std()

def calc_bollinger_bands(prices, window=20, num_std=2):
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = sma + num_std * std
    lower_band = sma - num_std * std
    return upper_band, lower_band

def calc_zscore(prices, window=20):
    mean = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    zscore = (prices - mean) / (std + 1e-8)
    return zscore

def calc_atr(df, window=14):
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr

def calc_short_term_volatility(prices, window=5):
    return prices.pct_change().rolling(window).std()

def detect_hammer(df):
    """Hammer: small real body near top, long lower wick, small/no upper wick."""
    open_ = df['open']
    close = df['close']
    high = df['high']
    low = df['low']
    body = (close - open_).abs()
    candle_len = high - low
    lower_shadow = (open_ - low).where(open_ < close, close - low)
    upper_shadow = high - open_.where(open_ > close, close)
    cond = (
        (body / candle_len <= 0.3) &
        (lower_shadow >= body * 2) &
        (upper_shadow <= body * 0.5)
    )
    return cond.fillna(False)

def detect_bullish_engulfing(df):
    """Bullish Engulfing: prev day red, today green, today body engulfs prev body."""
    prev_open = df['open'].shift(1)
    prev_close = df['close'].shift(1)
    open_ = df['open']
    close = df['close']
    cond = (
        (prev_close < prev_open) & (close > open_) &
        (close > prev_open) & (open_ < prev_close)
    )
    return cond.fillna(False)

def detect_morning_star(df):
    """Morning Star: 3-candle pattern: red, small gap down, green closes above Day1 midpoint."""
    open_ = df['open']
    close = df['close']
    prev_open = df['open'].shift(1)
    prev_close = df['close'].shift(1)
    prev2_open = df['open'].shift(2)
    prev2_close = df['close'].shift(2)
    # Day 1: big red, Day 2: small real body, Day 3: green, closes above Day1 midpoint
    day1_body = (prev2_close - prev2_open).abs()
    day2_body = (prev_close - prev_open).abs()
    day3_body = (close - open_).abs()
    day1_mid = (prev2_close + prev2_open) / 2
    cond = (
        (prev2_close < prev2_open) &  # Day1 red
        (day2_body < day1_body * 0.5) &  # Day2 small
        (close > open_) &  # Day3 green
        (close > day1_mid)
    )
    return cond.fillna(False)

def detect_shooting_star(df):
    """Shooting Star: small real body near bottom, long upper wick, small/no lower wick."""
    open_ = df['open']
    close = df['close']
    high = df['high']
    low = df['low']
    body = (close - open_).abs()
    candle_len = high - low
    upper_shadow = high - open_.where(open_ > close, close)
    lower_shadow = (open_ - low).where(open_ < close, close - low)
    cond = (
        (body / candle_len <= 0.3) &
        (upper_shadow >= body * 2) &
        (lower_shadow <= body * 0.5)
    )
    return cond.fillna(False)

def detect_bearish_engulfing(df):
    """Bearish Engulfing: prev day green, today red, today body engulfs prev body."""
    prev_open = df['open'].shift(1)
    prev_close = df['close'].shift(1)
    open_ = df['open']
    close = df['close']
    cond = (
        (prev_close > prev_open) & (close < open_) &
        (open_ > prev_close) & (close < prev_open)
    )
    return cond.fillna(False)

def detect_evening_star(df):
    """Evening Star: 3-candle pattern: green, small gap up, red closes below Day1 midpoint."""
    open_ = df['open']
    close = df['close']
    prev_open = df['open'].shift(1)
    prev_close = df['close'].shift(1)
    prev2_open = df['open'].shift(2)
    prev2_close = df['close'].shift(2)
    day1_body = (prev2_close - prev2_open).abs()
    day2_body = (prev_close - prev_open).abs()
    day3_body = (close - open_).abs()
    day1_mid = (prev2_close + prev2_open) / 2
    cond = (
        (prev2_close > prev2_open) &  # Day1 green
        (day2_body < day1_body * 0.5) &  # Day2 small
        (close < open_) &  # Day3 red
        (close < day1_mid)
    )
    return cond.fillna(False)

def add_indicators(df):
    # Core indicators
    df["rsi_14"] = calc_rsi(df["close"], window=14)
    df["ma5"] = calc_sma(df["close"], window=5)
    df["ma25"] = calc_sma(df["close"], window=25)
    df["ema12"] = calc_ema(df["close"], window=12)
    df["ema26"] = calc_ema(df["close"], window=26)
    df["volatility20"] = calc_volatility(df["close"], window=20)
    macd, macd_signal = calc_macd(df["close"])
    df["macd"] = macd
    df["macd_signal"] = macd_signal

    # NEW: Bollinger Bands
    upper, lower = calc_bollinger_bands(df["close"])
    df["bb_upper"] = upper
    df["bb_lower"] = lower

    # NEW: Z-score
    df["zscore_20"] = calc_zscore(df["close"])

    # NEW: ATR
    df["atr_14"] = calc_atr(df)

    # NEW: Short-term volatility
    df["volatility5"] = calc_short_term_volatility(df["close"], window=5)

    # Candlestick pattern detection
    df["is_hammer"] = detect_hammer(df)
    df["is_bullish_engulfing"] = detect_bullish_engulfing(df)
    df["is_morning_star"] = detect_morning_star(df)
    df["is_shooting_star"] = detect_shooting_star(df)
    df["is_bearish_engulfing"] = detect_bearish_engulfing(df)
    df["is_evening_star"] = detect_evening_star(df)
    return df

    return df

def get_ma_from_db(conn, ticker, date, window=5):
    """
    Returns the simple moving average (MA) for a ticker as of a given date,
    using prices table in the DB.
    """
    query = """
        SELECT close FROM prices
        WHERE ticker = ? AND date <= ?
        ORDER BY date DESC
        LIMIT ?
    """
    rows = conn.execute(query, (ticker, date, window)).fetchall()
    if not rows or len(rows) < window:
        return None
    closes = [float(row[0]) for row in rows]
    return sum(closes) / len(closes)
