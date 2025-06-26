import pandas as pd
import openai
import time
import os
import re
import logging
from typing import List, Set
from config.config import (
    GENERIC_PREFIXES,
    GENERIC_SUFFIXES,
    GENERIC_WORDS,
    OPENAI_API_KEY,
    GPT_MODEL,
    NEWS_BATCH_SIZE,
    MAX_API_RETRIES,
    API_SLEEP
)

# === SETUP ===
INPUT_CSV = "topix_company_list.csv"
OUTPUT_CSV = "topix_company_list_cleaned.csv"

if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY is not set in config or env. Exiting.")
    raise RuntimeError("OPENAI_API_KEY not set.")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# === UTILITY FUNCTIONS ===

def strip_prefixes(name: str, prefixes: List[str]) -> str:
    """Remove any generic prefix from the start of a name."""
    for pre in prefixes:
        if name.startswith(pre):
            name = name[len(pre):].strip()
    return name

def strip_suffixes(name: str, suffixes: List[str]) -> str:
    """Remove any generic suffix from the end of a name."""
    for suf in suffixes:
        if name.endswith(suf):
            name = name[:-len(suf)].strip()
    return name

def normalize_name(name: str, prefixes: List[str], suffixes: List[str]) -> str:
    """Remove both generic prefixes and suffixes."""
    return strip_suffixes(strip_prefixes(name, prefixes), suffixes)

def dedup_by_root(names: Set[str], prefixes: List[str], suffixes: List[str]) -> Set[str]:
    """Keep only root forms of names by removing generic affixes and deduping."""
    normalized_map = {}
    for n in names:
        n_norm = normalize_name(n, prefixes, suffixes)
        if not n_norm or n_norm in GENERIC_WORDS: continue
        normalized_map[n] = n_norm
    # Only keep names that aren't a superset of another normalized name
    result = set()
    normalized_set = set(normalized_map.values())
    for orig, root in normalized_map.items():
        if not any(other != root and (root in other or other in root) for other in normalized_set):
            result.add(orig)
    return result

def build_prompt(ticker, company_name, variants):
    # Escape any special CSV-breaking characters (defensive)
    def esc(s):
        return s.replace('\n', ' ').replace('\r', ' ').replace('"', "'")
    return f"""
You are a Japanese financial data expert and data cleaner.

Given the following info:
- ticker: {esc(ticker)}
- company_name: {esc(company_name)}
- variants: {esc(variants)}

1. Split the variants into two fields:
   - company_name_variants: All names/aliases for the company itself (official, short, nicknames, ticker, ticker in full-width, English, common abbreviations), but NOT product/brand names or generic/junk/common words. Exclude any "株式会社", "Co.", "Inc.", "Ltd." etc unless essential for disambiguation.
   - product_names: Only actual product/brand names. EXCLUDE generic/common/junk words (e.g. "ちくわ", "商品", "サービス" etc.) and any words whose only difference from the company name is the addition/removal of such generic prefixes or suffixes.

2. Apply redundancy rule: If several product_names share the same root word but only differ by generic prefixes/suffixes (like "の家", "の注文住宅", etc), keep only the root product/brand name (e.g., keep "タマホーム", drop "タマホームの家" and "タマホームの注文住宅").

3. Output format: Output only this CSV header and one line (no comments or explanation):
ticker,company_name_variants,product_names
"""

def clean_company_name_variants(raw: str) -> str:
    # Remove duplicates, empty, generic/junk
    variants = set([v.strip() for v in re.split(r'[|/,]', raw) if v.strip()])
    variants = [v for v in variants if v and v not in GENERIC_WORDS]
    return "|".join(sorted(variants, key=len))

def clean_product_names(product_names_raw: str, company_name_variants: str) -> str:
    if not product_names_raw:
        return ""
    products = set([p.strip() for p in re.split(r'[|/,]', product_names_raw) if p.strip()])
    # Remove generic words
    cleaned = [p for p in products if p not in GENERIC_WORDS]
    # Remove if identical to company variant (or trivial prefix/suffix diff)
    company_tokens = set()
    for c in re.split(r'[|/,]', company_name_variants or ""):
        c = c.strip()
        if not c: continue
        company_tokens.add(c)
        # Also try removing prefixes/suffixes
        for suf in GENERIC_SUFFIXES:
            if c.endswith(suf):
                company_tokens.add(c[:-len(suf)].strip())
        for pre in GENERIC_PREFIXES:
            if c.startswith(pre):
                company_tokens.add(c[len(pre):].strip())
    filtered = []
    for p in cleaned:
        p_norm = normalize_name(p, GENERIC_PREFIXES, GENERIC_SUFFIXES)
        # Skip if cleaned product matches any company name variant or vice versa (strict token)
        if any(p_norm == c or c == p_norm for c in company_tokens if c):
            continue
        # Also skip if only trivial noun remains
        if p_norm in GENERIC_WORDS or not p_norm:
            continue
        filtered.append(p)
    # Remove redundant variants with only generic prefix/suffix difference
    filtered = dedup_by_root(set(filtered), GENERIC_PREFIXES, GENERIC_SUFFIXES)
    return "|".join(sorted(filtered, key=len))

def gpt_call_with_retry(messages, max_retries=MAX_API_RETRIES):
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": messages}],
                max_tokens=256,
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"GPT API error (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("GPT API failed after retries.")

def main():
    df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
    results = []
    for idx, row in df.iterrows():
        ticker = row.get("ticker", "")
        company_name = row.get("company_name", "")
        variants = row.get("variants", "")
        prompt = build_prompt(ticker, company_name, variants)
        logging.info(f"Processing ticker: {ticker} ({company_name})")
        try:
            text = gpt_call_with_retry(prompt)
            lines = text.strip().split("\n")
            # Extract first data line (skip header if present)
            company_name_variants, product_names = "", ""
            for line in lines:
                if "," in line and not line.lower().startswith("ticker"):
                    parts = line.strip().split(",", 2)
                    if len(parts) == 3:
                        _ticker, company_name_variants, product_names = parts
                    elif len(parts) == 2:
                        company_name_variants, product_names = parts
                    break
        except Exception as e:
            logging.error(f"[FATAL] GPT API error at row {idx}: {e}")
            company_name_variants, product_names = "", ""
            # If failed, mark as error and skip
        # --- Post-processing for further cleaning ---
        company_name_variants_cleaned = clean_company_name_variants(company_name_variants)
        product_names_cleaned = clean_product_names(product_names, company_name_variants_cleaned)
        logging.info(f"  → company_name_variants: {company_name_variants_cleaned}")
        logging.info(f"  → product_names: {product_names_cleaned}")
        results.append({
            "original_company_name": company_name,
            "company_name_variants": company_name_variants_cleaned,
            "product_names": product_names_cleaned
        })
        time.sleep(API_SLEEP)
    # Save original and cleaned columns
    df["original_company_name"] = [r["original_company_name"] for r in results]
    df["company_name_variants"] = [r["company_name_variants"] for r in results]
    df["product_names"] = [r["product_names"] for r in results]
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ Saved cleaned variants to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
