"""
PJ Fire — TOPIX Universe Builder

- Fetches full list of TOPIX stocks from J-Quants.
- Expands with company names, sector17, and all major aliases (brand/short names).
- Calls GPT to add Japanese nicknames and variants.
- Cleans, deduplicates, and outputs the canonical universe CSV for screening and news search.
- Run regularly to keep ticker universe and news-matching aliases up to date.
"""


import os
import requests
import pandas as pd
import openai
import time
import re
import json
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
JQUANTS_EMAIL = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD = os.getenv("JQUANTS_PASSWORD")
JQ_BASE_URL = "https://api.jquants.com"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4o"
GPT_DELAY_SEC = 1.2
OUT_PATH = "topix_company_list.csv"
UNIVERSE_CSV

from config.config import (
    JQUANTS_EMAIL, JQUANTS_PASSWORD, JQ_BASE_URL, OPENAI_API_KEY,
    GPT_MODEL, GPT_DELAY_SEC, VARIANT_CSV, UNIVERSE_CSV
)

SUFFIX_ABBREVIATIONS = [
    ("ホールディングス", "HD"),
    ("グループ", "G"),
    ("工業", ""),
    ("商事", ""),
    ("不動産", ""),
    ("物流", ""),
    ("製作所", ""),
    ("サービス", ""),
    ("産業", ""),
    ("電機", ""),
    ("銀行", ""),
    ("証券", ""),
    ("リース", ""),
    ("建設", ""),
    ("製薬", ""),
]

GENERIC_NOUNS = {
    "ファミレス", "ステーキ", "飲料", "銀行", "食品", "ゲーム", "証券", "家電", "自動車",
    "スマホ", "ビール", "医薬品", "電機", "住宅", "不動産", "建設", "化学", "鉄鋼", "通信",
    "サービス", "メーカー", "業界", "株式", "ニュース"
}

BAD_PATTERNS = [
    "申し訳ありません", "情報は持ち合わせていません", "公式ウェブサイト", "お勧めします",
    "一般的に", "異なることがあります"
]

PROMPT = """
日本の金融ニュースやSNSで「{company_name}」（証券コード: {ticker}）を表す固有名詞（略称、ニックネーム、製品名、ブランド名など）を最大10個、日本語で挙げてください。
一般名詞や業界一般で使われる言葉（例：ファミレス、ステーキ、銀行、食品、家電、ゲーム、株式など）は除外してください。
固有名詞のみ、会社独自の呼び方やブランド・略称を含めてください。重複・曖昧な語や短縮形でも、会社特有でなければ除外してください。
回答はカンマ区切りで、例：A, B, C, D
"""

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

def get_id_token():
    data = {"mailaddress": JQUANTS_EMAIL, "password": JQUANTS_PASSWORD}
    r = requests.post(f"{JQ_BASE_URL}/v1/token/auth_user", data=json.dumps(data), headers={"Content-Type": "application/json"})
    r.raise_for_status()
    refresh_token = r.json()["refreshToken"]
    r = requests.post(f"{JQ_BASE_URL}/v1/token/auth_refresh?refreshtoken={refresh_token}")
    r.raise_for_status()
    return r.json()["idToken"]

def fetch_topix_metadata():
    token = get_id_token()
    url = f"{JQ_BASE_URL}/v1/listed/info"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    info = resp.json().get("info", [])
    df = pd.DataFrame(info)
    # Filter for TOPIX only
    df = df[
        (df["MarketCodeName"] == "プライム") & 
        (df["ScaleCategory"].str.contains("TOPIX", na=False))
    ].copy()
    df["ticker"] = df["Code"].astype(str)
    df["ticker_fullwidth"] = df["ticker"].apply(halfwidth_to_fullwidth)
    df = df[["ticker", "ticker_fullwidth", "CompanyName", "Sector17CodeName"]]
    df.rename(columns={
        "CompanyName": "company_name",
        "Sector17CodeName": "sector17"
    }, inplace=True)
    return df

def gpt_get_variants(company_name, ticker, client):
    prompt = PROMPT.format(company_name=company_name, ticker=ticker)
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.2,
        )
        result = response.choices[0].message.content
        return [v.strip() for v in result.split(",") if v.strip()]
    except Exception as e:
        print(f"[ERROR] GPT API for {company_name}: {e}")
        return []

def generate_abbreviations(company_name):
    abbrs = []
    for suffix, abbr in SUFFIX_ABBREVIATIONS:
        if company_name.endswith(suffix):
            base = company_name[:-len(suffix)]
            abbrs.append(base)
            if abbr:
                abbrs.append(base + abbr)
    return abbrs

def is_gpt_junk_variant(variant):
    return any(bad in variant for bad in BAD_PATTERNS)

def clean_variants(variants, ticker, ticker_fullwidth, company_name):
    filtered = [
        v for v in variants
        if v != ticker and v != ticker_fullwidth and v not in GENERIC_NOUNS and len(v) > 1 and not is_gpt_junk_variant(v)
    ]
    filtered += generate_abbreviations(company_name)
    seen = set()
    deduped = []
    for v in filtered:
        if v and v not in seen:
            deduped.append(v)
            seen.add(v)
    return " / ".join(deduped)

def main():
    print("[STEP 1] Fetching TOPIX metadata from J-Quants...")
    df = fetch_topix_metadata()
    print(f"[INFO] Fetched {len(df)} TOPIX stocks.")
    print("[STEP 2] Expanding company variants with GPT...")
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    all_variants = []
    for i, row in df.iterrows():
        print(f"Processing: {row['ticker']} {row['company_name']} ({i+1}/{len(df)})")
        variants = gpt_get_variants(row['company_name'], row['ticker'], openai_client)
        cleaned = clean_variants(variants, row['ticker'], row['ticker_fullwidth'], row['company_name'])
        all_variants.append(cleaned)
        time.sleep(GPT_DELAY_SEC)
    df["variants"] = all_variants
    print("[STEP 3] Saving to CSV...")
    df.to_csv(UNIVERSE_CSV, index=False, encoding="utf-8-sig")
    print(f"[DONE] Saved: {UNIVERSE_CSV}")
    print(df.head(10))

if __name__ == "__main__":
    main()
