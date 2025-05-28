"""
PJ Fire — Utility Functions

General-purpose helpers used across modules.
Keep pure, side-effect-free, and minimal.
"""

import datetime

def safe_float(val, default=0.0):
    """Convert to float, or return default on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def format_jp_date(date_obj):
    """Formats a datetime.date to Japanese YYYY/MM/DD string."""
    return date_obj.strftime("%Y/%m/%d")

def today_str():
    """Returns today's date string in YYYY-MM-DD format."""
    return datetime.date.today().isoformat()

# Example usage:
# val = safe_float("12.34")
# date_str = format_jp_date(datetime.date.today())

