"""
PJ Fire — Block-All Strategy

Always returns no signals, fully blocks trading in panic/blocked regimes.
"""

def generate_block_all_signals(conn, date, regime=None, model=None):
    # No trades allowed in this regime.
    return []
