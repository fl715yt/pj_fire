import pandas as pd
import numpy as np

"""
PJ Fire / Signav Regime Detection Module

Defines all supported market regimes, their detection logic, and a mapping to enabled strategies.
MVP: Only regimes/strategies marked ACTIVE are implemented. All others are reserved for expansion.

Regime Table:
| Regime        | Detection Rule (Example)                                 | Strategies Enabled           | Active? |
|---------------|---------------------------------------------------------|------------------------------|---------|
| range_bound   | <2% index change, low vol (σ < 1.2%) over 10 days       | mean_reversion               | Yes     |
| bull          | Index +5%/20d or price > MA(50/200)                     | momentum                     | Yes     |
| bear          | Index –5%/20d or price < MA(50/200)                     | defensive                    | Yes     |
| panic         | 10d vol > 2x 1yr avg, VIX-J > 25                        | block_all                    | Yes     |
| macro_event   | ETF drop >3% in 2d, major calendar event                | block_all                    | Future  |
| sector_rotation | Sector ETF spread >4%                                  | sector_rotation              | Future  |
| earnings      | >20% stocks reporting this week                         | pead                         | Future  |
"""

def detect_range_bound(df: pd.DataFrame) -> bool:
    """Detects sideways/range-bound regime: low volatility, no big trend."""
    price = df['close']
    hi_lo_pct = (price.rolling(10).max() - price.rolling(10).min()) / price.rolling(10).min()
    vol_10d = price.pct_change().rolling(10).std()
    # Default thresholds: <2% range, <1.2% daily vol
    is_range = (hi_lo_pct.iloc[-1] < 0.02) and (vol_10d.iloc[-1] < 0.012)
    return is_range

def detect_bull(df: pd.DataFrame) -> bool:
    """Bull regime: sustained uptrend (price > MA50/MA200 or 5%+ gain/20d)"""
    price = df['close']
    ma50 = price.rolling(50).mean()
    ma200 = price.rolling(200).mean()
    change_20d = price.pct_change(20)
    return ((price.iloc[-1] > ma50.iloc[-1]) and (price.iloc[-1] > ma200.iloc[-1])) or (change_20d.iloc[-1] > 0.05)

def detect_bear(df: pd.DataFrame) -> bool:
    """Bear regime: sustained downtrend (price < MA50/MA200 or –5%/20d)"""
    price = df['close']
    ma50 = price.rolling(50).mean()
    ma200 = price.rolling(200).mean()
    change_20d = price.pct_change(20)
    return ((price.iloc[-1] < ma50.iloc[-1]) and (price.iloc[-1] < ma200.iloc[-1])) or (change_20d.iloc[-1] < -0.05)

def detect_panic(df: pd.DataFrame, vix_j: float = None) -> bool:
    """Panic regime: high realized volatility or VIX-J > 25."""
    price = df['close']
    vol_10d = price.pct_change().rolling(10).std()
    vol_1yr = price.pct_change().rolling(252).std()
    vix_j_condition = (vix_j is not None) and (vix_j > 25)
    return (vol_10d.iloc[-1] > 2 * vol_1yr.iloc[-1]) or vix_j_condition

def detect_regime(df: pd.DataFrame, vix_j: float = None) -> str:
    """Central regime detection dispatcher. Expand as needed."""
    if detect_panic(df, vix_j):
        return "panic"
    if detect_bear(df):
        return "bear"
    if detect_bull(df):
        return "bull"
    if detect_range_bound(df):
        return "range_bound"
    # Add more custom/future regimes here
    return "unknown"

def detect_sector_bull(df: pd.DataFrame) -> bool:
    price = df['close']
    ma50 = price.rolling(50).mean()
    ma200 = price.rolling(200).mean()
    change_20d = price.pct_change(20)
    return ((price.iloc[-1] > ma50.iloc[-1]) and (price.iloc[-1] > ma200.iloc[-1])) or (change_20d.iloc[-1] > 0.05)

def detect_sector_bear(df: pd.DataFrame) -> bool:
    price = df['close']
    ma50 = price.rolling(50).mean()
    ma200 = price.rolling(200).mean()
    change_20d = price.pct_change(20)
    return ((price.iloc[-1] < ma50.iloc[-1]) and (price.iloc[-1] < ma200.iloc[-1])) or (change_20d.iloc[-1] < -0.05)

def detect_sector_range_bound(df: pd.DataFrame) -> bool:
    price = df['close']
    hi_lo_pct = (price.rolling(10).max() - price.rolling(10).min()) / price.rolling(10).min()
    vol_10d = price.pct_change().rolling(10).std()
    return (hi_lo_pct.iloc[-1] < 0.02) and (vol_10d.iloc[-1] < 0.012)

def detect_sector_regime(df: pd.DataFrame) -> str:
    if detect_sector_bear(df):
        return "sector_bear"
    if detect_sector_bull(df):
        return "sector_bull"
    if detect_sector_range_bound(df):
        return "sector_range_bound"
    return "sector_unknown"


def is_regime_blocked(strategy: str, regime: str) -> bool:
    """
    Returns True if the given strategy is NOT allowed in the current regime.
    Uses the global regime_strategy_map.
    """
    allowed = regime_strategy_map.get(regime, [])
    return strategy not in allowed

# --- Regime-to-Strategy Mapping (MVP) ---
regime_strategy_map = {
    "range_bound": ["mean_reversion"],
    "bull": ["momentum"],
    "bear": ["defensive"],
    "panic": ["block_all"],
    "unknown": [],  # No signals if regime not identified
    # Add more as you expand strategies
}

# --- Docstring: For Notion ---
"""
Expansion slots (Future):
- macro_event: block_all, event-driven
- sector_rotation: sector_rotation, momentum
- earnings: pead, mean_reversion
"""
