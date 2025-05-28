"""
PJ Fire — Technical Indicators
(Canonical version, used by both simulation and backtest systems)
"""

import pandas as pd

def calc_rsi(prices, window=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
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

def add_indicators(df):
    # Core indicators
    df["rsi_14"] = calc_rsi(df["close"], window=14)
    df["ma5"] = calc_sma(df["close"], window=5)
    df["ma25"] = calc_sma(df["close"], window=25)
    # Optional/future: more indicators
    df["ema12"] = calc_ema(df["close"], window=12)
    df["ema26"] = calc_ema(df["close"], window=26)
    df["volatility20"] = calc_volatility(df["close"], window=20)
    macd, macd_signal = calc_macd(df["close"])
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    return df
