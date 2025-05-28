import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build
import time
import re

# --- CONFIG ---
load_dotenv()
# DB_FILE and CACHE_TABLE must be set by the caller or default
DB_FILE = os.getenv("PJ_FIRE_DB", "simulation/pjfire.db")
CACHE_TABLE = os.getenv("PJ_FIRE_NEWS_CACHE", "news_cache")
VARIANT_CSV = os.getenv("PJ_FIRE_VARIANT_CSV", "pjfire_topix_company_patterns_filtered.csv")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
MAX_RESULTS = 10

ALLOWED_DOMAINS = [
    "nikkei.com", "kabutan.jp", "bloomberg.co.jp", "reuters.com",
    "irbank.net", "minkabu.jp", "moneyworld.jp", "fisco.jp"
]
JUNK_DOMAINS = [
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "wikipedia.org", "linkedin.com", "youtube.com", "ameblo.jp",
    "note.com", "shop", "rakuten.co.jp", "amazon.co.jp"
]
JUNK_URL_PATTERNS = [
    "/wiki/", "/mypage/", "/profile/", "/about/", "/support/", "/blog/", "/career/", "/job/", "/shop/", "/event/", "/guide/", "/faq", "/posts/", "/users/", "/account/", "/company/", "/news/all/", "/ir/", "/corp/"
]

SIGNAL_KEYWORDS = [
    "下方修正", "上方修正", "買収", "合併", "子会社化", "不正", "訴訟", "監査", "粉飾",
    "大幅減益", "黒字転換", "赤字転落", "新製品", "新サービス", "サービス開始",
    "製品発表", "新規事業", "事業撤退", "生産停止", "販売停止", "リコール", "不祥事",
    "人事異動", "退任", "新任", "大型契約", "受注", "資本提携", "株式交換", "TOB",
    "公募増資", "第三者割当増資", "ストックオプション"
]
BONUS_KEYWORDS = [
    "決算発表", "株主総会", "新規上場", "M&A", "業務提携", "IR発表", "開発成功",
    "認可取得", "配当金", "新商品", "リニューアル", "役員報酬", "資本業務提携", "開示",
    "役員変更", "市場変更", "公募増資", "資本提携", "IR", "株式分割"
]
JUNK_KEYWORDS = [
    "ADRランキング", "ADR", "出来高ランキング", "売買高ランキング", "売買代金ランキング",
    "PTS", "注目銘柄", "個別銘柄", "上昇銘柄", "動き", "出来高上位", "PBR", "PER", "時価総額",
    "株価チャート", "理論株価", "目標株価", "掲示板", "株予報", "信用残", "時系列", "株価データ",
    "レーティング", "トレンド", "株価", "株式", "チャート", "株価情報", "株式情報",
    "日々株価", "週間株価", "年間株価", "四本値推移", "取引情報", "株式掲示板", "SBI証券",
    "マネックス証券", "楽天証券", "証券会社", "株式ニュース", "銘柄情報", "会社情報",
    "アセットアライブ", "株価・配当", "ピックアップ", "株価ヒストリー", "過去10年間",
    "過去1か月", "株価指数", "指標", "モーニングスター", "ストップ高", "ストップ安",
    "高値更新", "安値更新", "中途採用", "求人", "企業概要", "株価時系列", "転職",
    "企業情報", "就職", "就活", "公式サイト",
    "Stock Price & Latest News"
]
LOW_QUALITY_PATTERNS = [
    "ランキング", "予想", "株主", "配当", "IRバンク", "MINKABU", "株探", "PR TIMES",
    "チャート", "株価", "日々株価", "週間株価", "年間株価", "株価予想", "株価情報",
    "株式情報", "株予報", "四本値推移", "配当情報", "会社概要", "証券コード", "株式指標", "優待",
    "時系列", "株式分割", "過去10年間", "過去1か月", "個人投資家", "ピックアップ", "主要株主",
    "株価データ", "株主総会", "銘柄情報", "ニュース一覧", "情報", "IR情報", "四季報"
]

def strip_trailing_zero(code):
    code = str(code)
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code

def halfwidth_to_fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in str(s))

# --- LOAD VARIANTS TABLE ---
variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
variant_df["ticker"] = variant_df["ticker"].apply(strip_trailing_zero)
TICKER_TO_VARIANTS = {
    row["ticker"]: [v.strip() for v in str(row["variants"]).split(" / ")
                    if v.strip() and not v.strip().isdigit()]
    for _, row in variant_df.iterrows()
}

def is_allowed_domain(url):
    return any(dom in url for dom in ALLOWED_DOMAINS)

def is_junk_domain(url):
    return any(dom in url for dom in JUNK_DOMAINS)

def is_junk_url(url):
    return any(pat in url for pat in JUNK_URL_PATTERNS)

def is_junk_headline(text):
    generic = ["公式サイト", "マイページ", "会社概要", "プロフィール", "お問い合わせ", "サポート", "コーポレート", "求人", "採用情報"]
    if any(word in text for word in generic):
        return True
    if "掲示板" in text or "ADRランキング" in text:
        return True
    if re.fullmatch(r"[A-Za-z0-9\-_/ ]+", text):
        return True
    if re.fullmatch(r"\d{4,6}", text):
        return True
    if len(text) < 10 and not any(w in text for w in SIGNAL_KEYWORDS + BONUS_KEYWORDS):
        return True
    return False

def mentions_wrong_company(text, search_terms):
    return not any(v in text for v in search_terms)

def score_headline(text, url, search_terms):
    score = 0
    if any(term in text for term in SIGNAL_KEYWORDS):
        score += 5
    if any(term in text for term in BONUS_KEYWORDS):
        score += 3
    if any(domain in url for domain in ALLOWED_DOMAINS):
        score += 2
    if any(v in text for v in search_terms):
        score += 1
    if any(term in text for term in JUNK_KEYWORDS):
        score -= 3
    if is_junk_domain(url) or is_junk_url(url) or is_junk_headline(text):
        score -= 5
    if any(term in text for term in LOW_QUALITY_PATTERNS):
        score -= 1
    return score

def get_search_terms(ticker, variants):
    ticker = strip_trailing_zero(ticker)
    ticker_fw = halfwidth_to_fullwidth(ticker)
    terms = [ticker, ticker_fw] + [v for v in variants if v not in {ticker, ticker_fw}]
    return list(dict.fromkeys([t for t in terms if t and len(t) > 1]))

def fetch_news_for_ticker(ticker, signal_date):
    ticker = strip_trailing_zero(ticker)
    variants = TICKER_TO_VARIANTS.get(str(ticker), [])
    search_terms = get_search_terms(ticker, variants)
    if not search_terms:
        print(f"[WARN] No search terms for ticker {ticker}.")
        return "No variants or ticker for news search."

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {CACHE_TABLE} (
            ticker TEXT,
            signal_date TEXT,
            headlines TEXT,
            PRIMARY KEY (ticker, signal_date)
        )
    """)
    cursor.execute(f"""
        SELECT headlines FROM {CACHE_TABLE}
        WHERE ticker = ? AND signal_date = ?
    """, (ticker, signal_date))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]

    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    except Exception as e:
        print(f"[ERROR] Google CSE API error: {e}")
        conn.close()
        return "No headlines due to Google API error."

    base_date = datetime.strptime(signal_date, "%Y-%m-%d")
    headlines = []

    for offset in range(-3, 2):  # -3 to +1 inclusive
        q_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
        for term in search_terms:
            for suffix in ["", " 株", " ニュース"]:
                query = f'{term}{suffix}'
                try:
                    result = service.cse().list(
                        q=query,
                        cx=GOOGLE_CSE_ID,
                        lr="lang_ja",
                        num=MAX_RESULTS,
                        sort="date"
                    ).execute()
                except Exception as e:
                    print(f"\u26a0\ufe0f Google CSE failed for {ticker} ({term}) on {q_date}: {e}")
                    continue

                items = result.get("items", [])
                for item in items:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    if is_junk_domain(link) or is_junk_url(link) or is_junk_headline(title):
                        continue
                    if mentions_wrong_company(title, search_terms):
                        continue
                    score = score_headline(title, link, search_terms)
                    if score > 0 or is_allowed_domain(link):
                        headlines.append((score, f"- {title} ({link})"))
                time.sleep(1.0)  # Google API rate limit

    # Deduplicate by headline text
    seen_titles = set()
    cleaned = []
    for s, line in sorted(headlines, reverse=True):
        title = line.split(" (")[0].replace("- ", "")
        if title not in seen_titles:
            cleaned.append((s, line))
            seen_titles.add(title)

    top_n = [line for _, line in cleaned[:3]]
    headlines_str = "\n".join(top_n) if top_n else "No high-quality headlines found."

    cursor.execute(f"""
        INSERT OR REPLACE INTO {CACHE_TABLE} (ticker, signal_date, headlines)
        VALUES (?, ?, ?)
    """, (ticker, signal_date, headlines_str))
    conn.commit()
    conn.close()

    return headlines_str

# --- Test loop ---
if __name__ == "__main__":
    test_cases = [
        ("7203", "2024-05-10"),
        ("9984", "2024-04-30"),
        ("3436", "2024-05-09"),
        ("8058", "2024-03-28"),
        ("8306", "2024-01-18"),
        ("9501", "2024-02-13"),
        ("3769", "2024-04-18"),
        ("2432", "2024-01-18"),
        ("7065", "2024-03-08"),
        ("6758", "2024-05-02"),
        ("2702", "2024-05-13"),
        ("4523", "2024-03-07"),
        ("9022", "2024-04-02"),
        ("6981", "2024-02-19"),
    ]
    for t, d in test_cases:
        print(f"\n=== {t} {d} ===")
        headlines = fetch_news_for_ticker(t, d)
        print(headlines)
