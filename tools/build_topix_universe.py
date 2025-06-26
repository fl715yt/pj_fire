"""
PJ Fire — TOPIX Universe Builder v3

- Fetches full TOPIX stock list from J-Quants.
- Expands with company names, sector, and full-width ticker.
- Uses GPT-4 with 3 context prompts (NEWS, SNS, HEADLINE) to generate up to 5 company name variants (abbreviations/nicknames) and up to 5 product/brand names, sorted by usage/popularity.
- Cleans and deduplicates variants (removes generic and junk words, strips bad GPT patterns and generic prefixes/suffixes).
- Outputs canonical universe CSV for news/searching.

Config:
- Requires config/config.py with GENERIC_SUFFIXES, GENERIC_PREFIXES, GENERIC_WORDS, BAD_PATTERNS, and all credentials.
- Set UNIVERSE_CSV as desired output path.
"""

import os
import requests
import pandas as pd
import openai
import time
import json
from collections import Counter
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
from config.config import (
    JQUANTS_EMAIL, JQUANTS_PASSWORD, JQ_BASE_URL, OPENAI_API_KEY,
    GPT_MODEL, GPT_DELAY_SEC, UNIVERSE_CSV,
    GENERIC_SUFFIXES, GENERIC_PREFIXES, GENERIC_WORDS, BAD_PATTERNS
)

PROMPT_NEWS = """
日本の金融ニュースで「{company_name}」（証券コード: {ticker}）について、下記2リストをそれぞれ「最もよく使われる順」に最大5個ずつ挙げてください。

1. 会社の略称・ニックネーム・通称・英語名（ブランド名や製品名は除外）
2. 代表的なブランド名・製品名（あれば）

重複や一般的な言葉は除外し、カンマ区切りで出力してください。

会社名: ...,
ブランド名: ...
"""

PROMPT_SNS = """
日本のSNSやトレーダー間で「{company_name}」（証券コード: {ticker}）について、下記2リストをそれぞれ「最もよく使われる順」に最大5個ずつ挙げてください。

1. 会社の略称・ニックネーム・通称・英語名（ブランド名や製品名は除外）
2. 代表的なブランド名・製品名（あれば）

重複や一般的な言葉は除外し、カンマ区切りで出力してください。

会社名: ...,
ブランド名: ...
"""

PROMPT_HEADLINE = """
日本の金融ニュースや見出しで「{company_name}」（証券コード: {ticker}）を表現する際によく使われる略称・ニックネーム・ブランド名・製品名（最大5個ずつ、短いものを優先）を挙げてください。

1. 会社名（ブランドや製品名は除外）
2. ブランド名・製品名（あれば）

カンマ区切りで出力してください。

会社名: ...,
ブランド名: ...
"""

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

def get_id_token():
    data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
    r = requests.post(f"{JQ_BASE_URL}/token/auth_user", data=json.dumps(data), headers={"Content-Type": "application/json"})
    r.raise_for_status()
    refresh_token = r.json()["refreshToken"]
    r = requests.post(f"{JQ_BASE_URL}/token/auth_refresh?refreshtoken={refresh_token}")
    r.raise_for_status()
    return r.json()["idToken"]

def fetch_topix_metadata():
    token = get_id_token()
    url = f"{JQ_BASE_URL}/listed/info"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    info = resp.json().get("info", [])
    df = pd.DataFrame(info)
    # TOPIX stocks only
    df = df[df["ScaleCategory"].str.contains("TOPIX", na=False)].copy().reset_index(drop=True)
    df["ticker"] = df["Code"].astype(str)
    df["ticker_fullwidth"] = df["ticker"].apply(halfwidth_to_fullwidth)
    df = df[["ticker", "ticker_fullwidth", "CompanyName", "Sector17CodeName"]]
    df.rename(columns={
        "CompanyName": "company_name",
        "Sector17CodeName": "sector17"
    }, inplace=True)
    return df

def strip_prefixes(name, prefixes):
    for pre in prefixes:
        if name.startswith(pre):
            name = name[len(pre):].strip()
    return name

def strip_suffixes(name, suffixes):
    for suf in suffixes:
        if name.endswith(suf):
            name = name[:-len(suf)].strip()
    return name

def normalize_name(name, prefixes, suffixes):
    return strip_suffixes(strip_prefixes(name, prefixes), suffixes)

def is_gpt_junk(variant):
    return any(bad in variant for bad in BAD_PATTERNS)

def clean_variants(raw_list, company_name, extra_abbrs):
    variants = [v.strip() for v in (raw_list + extra_abbrs) if v and isinstance(v, str)]
    variants = [
        v for v in variants
        if v not in GENERIC_WORDS
        and v != company_name
        and not is_gpt_junk(v)
        and len(v) > 1
    ]
    # Normalize with prefixes/suffixes for deduplication
    normalized = set()
    deduped = []
    for v in variants:
        root = normalize_name(v, GENERIC_PREFIXES, GENERIC_SUFFIXES)
        if root and root not in normalized:
            deduped.append(v)
            normalized.add(root)
    return "|".join(deduped[:5])

def parse_gpt_response(gpt_output):
    company_list = []
    brand_list = []
    for line in gpt_output.splitlines():
        if "会社名" in line:
            company_list = [v.strip() for v in line.split(":", 1)[-1].split(",") if v.strip()]
        if "ブランド名" in line:
            brand_list = [v.strip() for v in line.split(":", 1)[-1].split(",") if v.strip()]
    return company_list, brand_list

def gpt_context_prompts(company_name, ticker, client):
    prompts = [
        PROMPT_NEWS.format(company_name=company_name, ticker=ticker),
        PROMPT_SNS.format(company_name=company_name, ticker=ticker),
        PROMPT_HEADLINE.format(company_name=company_name, ticker=ticker),
    ]
    outputs = []
    for prompt in prompts:
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=160,
                temperature=0.2,
            )
            outputs.append(response.choices[0].message.content.strip())
            time.sleep(GPT_DELAY_SEC)
        except Exception as e:
            print(f"[WARN] GPT API for {company_name}: {e}")
            time.sleep(2)
    return outputs

def aggregate_variants(gpt_outputs):
    company_counter = Counter()
    brand_counter = Counter()
    for output in gpt_outputs:
        company_list, brand_list = parse_gpt_response(output)
        for v in company_list:
            company_counter[v] += 1
        for b in brand_list:
            brand_counter[b] += 1
    company_ranked = [v for v, _ in company_counter.most_common() if v]
    brand_ranked = [b for b, _ in brand_counter.most_common() if b]
    return company_ranked[:5], brand_ranked[:5]

def main():
    print("[STEP 1] Fetching TOPIX metadata from J-Quants...")
    df = fetch_topix_metadata()
    print(f"[INFO] Fetched {len(df)} TOPIX stocks.")
    print("[STEP 2] Expanding company and brand names with GPT-4 (multi-context prompts)...")
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    company_variants = []
    brand_names = []
    raw_gpt_outputs = []
    for i, row in df.iterrows():
        ticker = row['ticker']
        company_name = row['company_name']
        extra_abbrs = []
        for suf in GENERIC_SUFFIXES:
            if company_name.endswith(suf) and len(company_name) > len(suf):
                root = company_name[:-len(suf)].strip()
                if root and root != company_name:
                    extra_abbrs.append(root)
        for pre in GENERIC_PREFIXES:
            if company_name.startswith(pre) and len(company_name) > len(pre):
                root = company_name[len(pre):].strip()
                if root and root != company_name:
                    extra_abbrs.append(root)
        print(f"Processing: {ticker} {company_name} ({i+1}/{len(df)})")
        gpt_outputs = gpt_context_prompts(company_name, ticker, openai_client)
        c_list, b_list = aggregate_variants(gpt_outputs)
        company_cleaned = clean_variants(c_list, company_name, extra_abbrs)
        brand_cleaned = clean_variants(b_list, "", [])
        company_variants.append(company_cleaned)
        brand_names.append(brand_cleaned)
        raw_gpt_outputs.append(json.dumps(gpt_outputs, ensure_ascii=False))
    df["company_name_variants"] = company_variants
    df["product_names"] = brand_names
    df["gpt_raw_outputs"] = raw_gpt_outputs
    print("[STEP 3] Saving to CSV...")
    df.to_csv(UNIVERSE_CSV, index=False, encoding="utf-8-sig")
    print(f"[DONE] Saved: {UNIVERSE_CSV}")
    print(df.head(10))

if __name__ == "__main__":
    main()
