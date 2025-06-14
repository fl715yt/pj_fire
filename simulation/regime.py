import pandas as pd

def calc_market_regime(market_df, lookback=20, threshold=0.03):
    """
    Detects market regime using rolling mean and volatility.
    Returns one of: 'bull', 'bear', 'volatile', 'stable'
    """
    # Compute rolling returns
    market_df = market_df.sort_values("date")
    close = market_df["close"]
    returns = close.pct_change().rolling(lookback).mean()
    volatility = close.pct_change().rolling(lookback).std()

    if len(returns) == 0:
        return "stable"

    mean_ret = returns.iloc[-1]
    vol = volatility.iloc[-1]

    if mean_ret > threshold and vol < threshold:
        return "bull"
    elif mean_ret < -threshold and vol < threshold:
        return "bear"
    elif vol >= threshold:
        return "volatile"
    else:
        return "stable"

def calc_sector_regime(sector_df, lookback=20, threshold=0.03):
    """
    Same as market regime but for sector ETF or average.
    """
    return calc_market_regime(sector_df, lookback, threshold)

def is_regime_blocked(strategy: str, regime: str) -> bool:
    """
    Returns True if the given strategy should block signals under the given regime.
    Centralized regime gating logic.
    """
    # Define per-strategy regime block rules
    if strategy == "mean_reversion":
        return regime in ("bear", "volatile")
    elif strategy == "momentum":
        # Example: momentum allowed in all regimes → no block
        return False
    else:
        # Default: no blocking
        return False

