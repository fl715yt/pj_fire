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

def detect_candlestick_reversal(df):
    """
    Simple example: returns Series with 1 if bullish engulfing pattern, -1 if bearish, 0 otherwise.
    """
    open_ = df['open']
    close = df['close']
    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    # Bullish engulfing: yesterday red, today green, today body engulfs yesterday
    bullish = ((prev_close < prev_open) & (close > open_) & (close > prev_open) & (open_ < prev_close))
    # Bearish engulfing: yesterday green, today red, today body engulfs yesterday
    bearish = ((prev_close > prev_open) & (close < open_) & (open_ > prev_close) & (close < prev_open))
    return bullish.astype(int) - bearish.astype(int)

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

    # NEW: Candlestick reversal
    df["candlestick_reversal"] = detect_candlestick_reversal(df)

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
