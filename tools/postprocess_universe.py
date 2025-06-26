"""
PJ Fire — TOPIX Universe Post-Processor

- Cleans company_name_variants and product_names fields from universe CSV.
- Removes:
    - Category/product type words (GENERIC_WORDS)
    - Ticker codes (as numbers or fullwidth)
    - Short or generic fragments
    - Apology patterns/BAD_PATTERNS
    - Numbers only
- Outputs cleaned CSV with same columns.

Requires:
    - config/config.py with updated GENERIC_WORDS, BAD_PATTERNS, GENERIC_PREFIXES, GENERIC_SUFFIXES
    - Original universe CSV (e.g. universe.csv)
    - Set CLEANED_CSV output path

Usage:
    python tools/postprocess_universe.py
"""

import pandas as pd
import re
from config.config import (
    GENERIC_WORDS, BAD_PATTERNS, GENERIC_PREFIXES, GENERIC_SUFFIXES,
    UNIVERSE_CSV
)

CLEANED_CSV = UNIVERSE_CSV

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

def is_junk(value, ticker):
    """Returns True if value is junk: generic word, ticker, number, ap ology pattern, or too short."""
    # Remove whitespace etc
    v = value.strip()
    # Ticker (half/fullwidth)
    if v == ticker or v == halfwidth_to_fullwidth(ticker):
        return True
    # Numbers only
    if re.fullmatch(r"\d{4,5}", v):
        return True
    if v.isdigit():
        return True
    # Generic words, including categories/products
    if v in GENERIC_WORDS:
        return True
    # Prefix/suffix only — skip if variant == stripped variant
    for pre in GENERIC_PREFIXES:
        if v.startswith(pre) and v == pre:
            return True
    for suf in GENERIC_SUFFIXES:
        if v.endswith(suf) and v == suf:
            return True
    # BAD_PATTERNS (substrings)
    for pat in BAD_PATTERNS:
        if pat in v:
            return True
    # "該当なし" or obvious no-data
    if v in {"該当なし", "N/A", "なし"}:
        return True
    # Very short and not a known 1-char company
    if len(v) < 2:
        return True
    return False

def clean_field(field, ticker):
    if not isinstance(field, str):
        return ""
    values = [v.strip() for v in field.split("|") if v.strip()]
    cleaned = []
    for v in values:
        if not is_junk(v, ticker):
            cleaned.append(v)
    # Remove duplicates, keep order
    seen = set()
    out = []
    for x in cleaned:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return "|".join(out)

def main():
    df = pd.read_csv(UNIVERSE_CSV, encoding="utf-8-sig")
    for idx, row in df.iterrows():
        ticker = str(row["ticker"])
        # Clean company_name_variants
        raw = row.get("company_name_variants", "")
        cleaned = clean_field(raw, ticker)
        df.at[idx, "company_name_variants"] = cleaned
        # Clean product_names
        raw_p = row.get("product_names", "")
        cleaned_p = clean_field(raw_p, ticker)
        df.at[idx, "product_names"] = cleaned_p
    df.to_csv(CLEANED_CSV, index=False, encoding="utf-8-sig")
    print(f"[DONE] Cleaned CSV saved as: {CLEANED_CSV}")

if __name__ == "__main__":
    main()
