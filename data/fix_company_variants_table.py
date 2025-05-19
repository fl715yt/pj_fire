import pandas as pd
from collections import Counter

# --- Config ---
INPUT = "pjfire_topix_company_patterns_expanded.csv"
OUTPUT = "pjfire_topix_company_patterns_filtered.csv"
GENERIC_NOUNS = {
    "ファミレス", "ステーキ", "飲料", "銀行", "食品", "ゲーム", "証券", "家電", "自動車",
    "スマホ", "ビール", "医薬品", "電機", "住宅", "不動産", "建設", "化学", "鉄鋼", "通信",
    "サービス", "メーカー", "業界", "株式", "ニュース"
}
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
    # Add more if new suffixes appear in future scans
]

BAD_PATTERNS = [
    "申し訳ありません",
    "情報は持ち合わせていません",
    "公式ウェブサイト",
    "お勧めします",
    "一般的に",
    "異なることがあります"
]

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

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

# Load your CSV
df = pd.read_csv(INPUT, dtype=str)
df["ticker_fullwidth"] = df["ticker"].apply(halfwidth_to_fullwidth)

# Step 1: Collect all variants and map to tickers
variant_to_tickers = {}
for _, row in df.iterrows():
    ticker = row["ticker"]
    variants = [v.strip() for v in str(row["variants"]).split(" / ")]
    for v in variants:
        if v not in variant_to_tickers:
            variant_to_tickers[v] = set()
        variant_to_tickers[v].add(ticker)

# Step 2: Identify duplicated variants (not ticker code or ticker_fullwidth)
duplicates = set(
    v for v, tickers in variant_to_tickers.items()
    if len(tickers) > 1 and not v.isdigit() and not (len(v) == 4 or len(v) == 5 and all(c.isdigit() for c in v))
)

# Step 3: Clean and enhance variants per company
def clean_variants(row):
    ticker = row["ticker"]
    ticker_fw = row["ticker_fullwidth"]
    company_name = row["company_name"]
    variants = [v.strip() for v in str(row["variants"]).split(" / ")]
    filtered = [
        v for v in variants
        if v != ticker and v != ticker_fw and v not in GENERIC_NOUNS
        and v not in duplicates and len(v) > 1
        and not is_gpt_junk_variant(v)
    ]
    # Add abbreviation rules
    filtered += generate_abbreviations(company_name)
    # Remove empty, dedupe, etc.
    seen = set()
    deduped = []
    for v in filtered:
        if v and v not in seen:
            deduped.append(v)
            seen.add(v)
    return " / ".join(deduped)

df["variants"] = df.apply(clean_variants, axis=1)
df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
print(f"Saved: {OUTPUT}")
print(df.head(10))
