"""
PJ Fire — Centralized Configuration Module
Version: 2025-06-21
Purpose: Holds ALL constants, thresholds, mappings, and paths for every PJ Fire component.
Contains NO business logic or side-effects; just import what you need.
Secrets come from .env; codebase stays credentials-free.
"""


import os
from pathlib import Path
from dotenv import load_dotenv

# ----------------------------------------------------------------------
#  Environment bootstrap
# ----------------------------------------------------------------------
load_dotenv()  # ensures .env variables are loaded

# ----------------------------------------------------------------------
#  Secrets
# ----------------------------------------------------------------------
OPENAI_API_KEY: str | None    = os.getenv("OPENAI_API_KEY")
JQUANTS_EMAIL: str | None     = os.getenv("JQUANTS_EMAIL")
JQUANTS_PASSWORD: str | None  = os.getenv("JQUANTS_PASSWORD")
GOOGLE_API_KEY: str | None    = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID: str | None     = os.getenv("GOOGLE_CSE_ID")
NEWSAPI_KEY: str              = os.getenv("NEWSAPI_KEY", "")
GNEWS_API_KEY: str            = os.getenv("GNEWS_API_KEY", "")
BRAVE_API_KEY: str            = os.getenv("BRAVE_API_KEY", "")

required_env = {
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "JQUANTS_EMAIL": JQUANTS_EMAIL,
    "JQUANTS_PASSWORD": JQUANTS_PASSWORD,
    "GOOGLE_API_KEY": GOOGLE_API_KEY,
    "GOOGLE_CSE_ID": GOOGLE_CSE_ID
}
missing = [k for k, v in required_env.items() if not v]
if missing:
    raise EnvironmentError(
        f"The following required .env variables are missing: {', '.join(missing)}"
    )

# ----------------------------------------------------------------------
#  Database locations (strict separation ⇒ no cross-contamination)
# ----------------------------------------------------------------------
SIM_DB_FILE: str = os.getenv(
    "PJ_FIRE_SIM_DB",
    str(Path("simulation") / "pjfire.db"),
)
BT_DB_FILE: str = os.getenv(
    "PJ_FIRE_BT_DB",
    str(Path("backtest") / "backtest_bt.db"),
)

# ----------------------------------------------------------------------
#  Data files & universe
# ----------------------------------------------------------------------
UNIVERSE_CSV               = os.getenv("PJ_FIRE_UNIVERSE_CSV", "topix_company_list_cleaned.csv")
VARIANT_CSV                = os.getenv("PJ_FIRE_VARIANT_CSV", "topix_company_list_cleaned.csv")
TRADING_CALENDAR_CSV       = os.getenv("PJ_FIRE_CALENDAR_CSV", "trading_calendar.csv")
LOG_PATH                   = (Path("logs") / "pj_fire.log").as_posix()  # Ensure log path is POSIX for consistency

# ----------------------------------------------------------------------
#  Strategy/Scoring Constants
# ----------------------------------------------------------------------
DEFAULT_LOT_SIZE           = 100            # shares per trade
LOT_UNIT_SIZE              = 100            # Minimum unit for TSE stocks
MIN_TRADE_AMOUNT           = 10_000         # ¥ — ignore micro signals
FORCED_EXIT_THRESHOLD      = 0.07           # ≥ 7 % score gap ⇒ forced exit
TOP_N_RANK                 = 10             # candidates forwarded to signal stage
MAX_SIGNAL_PER_DAY         = 5              # UX guard-rail
MIN_VOLUME                 = 50_000         # minimum daily volume for screening
RSI_THRESHOLD              = 30             # default RSI filter
DROP_PCT_THRESHOLD         = -0.04          # -4% or worse for drop filter
ENTRY_BUFFER               = 0.005  
GAP_DOWN_LIMIT             = 0.02
USE_FUNDAMENTAL_FILTER = os.getenv("PJ_FIRE_USE_FUNDAMENTAL_FILTER", "1") == "1" ## enable fundamental strength filter
ENABLE_SCORE_FILTER = False  # Set True if you want to filter
SCORE_FILTER_THRESHOLD = 90


WEIGHTS = {
    "price_drop_pct": 3.0,
    "gpt_reason_score": 2.0,
    "fundamental_strength": 1.5,
    "volume_spike": 1.0,
    # add more if needed
}

SCORE_CUTOFF = 0.0  # Minimum score for signal consideration

CATEGORY_SCORING = {
    "misinterpreted_news": 1.2,
    "slightly_bad_news": 0.7,
    "very_bad_news": 0.0,
    "no_news": 1.1,
    "macro_or_sector_drop": 0.0
}

# ----------------------------------------------------------------------
#  Drawdown protection (Phase 1 live; Phase 3 adds portfolio exposure caps)
# ----------------------------------------------------------------------
DRAWDOWN_REDUCE_THRESHOLD  = 0.05           # 5 % DD ⇒ halve lot size
DRAWDOWN_STOP_THRESHOLD    = 0.10           # 10 % DD ⇒ pause new trades

# ----------------------------------------------------------------------
#  Exit rules
# ----------------------------------------------------------------------
# TAKE_PROFIT_PCT            = 0.05           # +5 % TP
STOP_LOSS_PCT              = 0.03          # –3 % SL
MAX_HOLDING_DAYS          = 3             # max days to hold a position

# ----------------------------------------------------------------------
#  Fundamentals import
# ----------------------------------------------------------------------
IMPORT_MODE = "FY"   # or "QUARTERLY"

# ----------------------------------------------------------------------
#  External endpoints (J-Quants Light Plan)
# ----------------------------------------------------------------------
JQ_BASE_URL                     = "https://api.jquants.com/v1"
PRICE_ENDPOINT                  = f"{JQ_BASE_URL}/prices/daily_quotes"
FY_ENDPOINT                     = f"{JQ_BASE_URL}/fins/statements"   # FY rows only
LISTED_INFO_ENDPOINT            = f"{JQ_BASE_URL}/listed/info"
TRADING_CALENDAR_ENDPOINT       = f"{JQ_BASE_URL}/markets/trading_calendar"
ANNOUNCEMENT_CALENDAR_ENDPOINT  = f"{JQ_BASE_URL}/fins/announcement"

# ----------------------------------------------------------------------
#  Project metadata / UX
# ----------------------------------------------------------------------
PROJECT_NAME               = "PJ Fire"
LINE_BOT_NAME              = "Signav シミュレータ"
VERSION                    = "1.0.0"
LINE_RICH_MENU_STYLE       = "compact"
LINE_LANGUAGE              = "ja"
UI_THEME                   = "light"

# ----------------------------------------------------------------------
#  Scheduling / automation
# ----------------------------------------------------------------------
DAILY_SIGNAL_TIME          = "08:45"        # JST, LINE push
WEEKLY_REPORT_DAY          = "FRI"          # Friday summary

# ----------------------------------------------------------------------
#  GPT / reasoning settings
# ----------------------------------------------------------------------
GPT_MODEL                  = os.getenv("PJ_FIRE_GPT_MODEL", "gpt-4o")
GPT_DELAY_SEC              = 1.2
EXCLUSION_KEYWORDS: list[str] = [
    "粉飾", "不正", "会計不正", "虚偽",        # Fraud/accounting
    "破産", "経営破綻", "倒産",              # Bankruptcy
    "上場廃止", "監理銘柄", "整理銘柄", "取引停止", # Delisting, halt
    "訴訟", "調査", "逮捕", "告発", "摘発", "処分", # Legal/compliance
    "赤字拡大", "債務超過", "無配",           # Financial trouble
    "社長辞任", "役員辞任", "経営危機",         # Management
    "重大事故", "大規模リコール", "火災", "爆発", "情報漏洩" # Other events
]
REASONING_CATEGORY_LABELS: list[str] = [
    "misinterpreted_news",
    "slightly_bad_news",
    "very_bad_news",
    "no_news",
    "macro_or_sector_drop"
]

# ----------------------------------------------------------------------
#  Sector ETF mapping (for macro/sector drop detection)
# ----------------------------------------------------------------------
SECTOR_ETF_MAP = {
    "食品": "1617",
    "エネルギー資源": "1618",
    "建設・資材": "1619",
    "素材・化学": "1620",
    "医薬品": "1621",
    "自動車・輸送機": "1622",
    "鉄鋼・非鉄": "1623",
    "機械": "1624",
    "電機・精密": "1625",
    "情報通信・サービスその他": "1626",
    "電気・ガス": "1627",
    "運輸・物流": "1628",
    "商社・卸売": "1629",
    "小売": "1630",
    "銀行": "1631",
    "金融（除く銀行）": "1632",
    "不動産": "1633",
}
MARKET_ETF = "1306"  # TOPIX ETF

# ----------------------------------------------------------------------
#  Backtest constants
# ----------------------------------------------------------------------
# START_DATE = os.getenv("PJ_FIRE_BACKTEST_START", "2023-06-01")
START_DATE = os.getenv("PJ_FIRE_BACKTEST_START", "2025-05-24") # temporary for testing
END_DATE   = os.getenv("PJ_FIRE_BACKTEST_END", "2025-06-07")
START_CASH = int(os.getenv("PJ_FIRE_START_CASH", 1_000_000))

# ----------------------------------------------------------------------
#  Sanity checks to avoid silent mis-imports
# ----------------------------------------------------------------------
if __name__ != "config.config":
    raise ImportError(
        "This module must ONLY be imported via 'from config.config import ...'. "
        "Do NOT copy, rename, or execute this file directly."
    )

# ----------------------------------------------------------------------
#  Supported strategies and regimes (for multi-strategy support)
# ----------------------------------------------------------------------
STRATEGIES: list[str] = [
    "mean_reversion",
    "momentum",  # Add more here in future
]

REGIMES: list[str] = [
    "bull",
    "bear",
    "volatile",
    "stable",
    "sector_up",
    "sector_down",
    "default",
]

# ----------------------------------------------------------------------
# News API / Fetcher Constants
# ----------------------------------------------------------------------
# MAX_NEWS_RESULTS = 10
MAX_NEWS_RESULTS = 5
NEWS_BATCH_SIZE = 5
MAX_API_RETRIES = 3
API_SLEEP = 1.2

# News search variant control
MAX_VARIANTS_PER_TICKER_GOOGLE = 2    # e.g., ["トヨタ自動車", "7203"]
MAX_VARIANTS_PER_TICKER_BRAVE = 3
MAX_VARIANTS_PER_TICKER_OTHER = 1     # Only main company name (no ticker) for non-Google APIs

# Google CSE only: use "ニュース" suffix
GOOGLE_CSE_USE_NEWS_SUFFIX = False  # Set to True if you want to append "ニュース" to queries

USE_NEWSAPI = False  # Only True if you specifically want global news fallback

DAILY_QUOTAS = {
    "google_cse": 100,
    "gnews": 100,
    "newsapi": 100,
    "brave_news": 67,  # 2000/month ÷ 30 ≈ 67/day, adjust as needed
}

GENERIC_PREFIXES: list[str] = [
    "新商品", "本店", "株式会社", "本社", "株式会社", "有限会社", "合同会社", "特定非営利活動法人",
    "証券コード", "証券", "金融", "保険", "銀行", "信託", "信販", "リース", "住宅ローン", "ローン"
]

GENERIC_SUFFIXES: list[str] = [
    "の家", "の注文住宅", "の分譲住宅", "のリフォーム", "株式会社", "カンパニー", "ホールディングス",
    "ホールディングス株式会社", "HD", "HOLDINGS", "グループ", "GHD", "コーポレーション",
    "本社", "本店", "営業部", "支店", "事業", "会社", "商事", "事務所", "センター", "プロジェクト", "支社", "スタジオ",
    "サービス", "プロダクツ", "ソリューション", "ブランド", "ネットワーク", "システム", "インターナショナル",
    "プロパティ", "パートナーズ", "パートナー", "プロダクション", "エンターテインメント", "コミュニケーションズ", "エージェンシー",
    "デザイン", "エンジニアリング", "マネジメント", "ディビジョン", "エデュケーション", "テクノロジー", "リゾート", "ラボ", "サポート",
    "エステート", "インベストメント", "アセット", "インシュアランス", "インダストリー", "ディベロップメント", "ホスピタリティ",
    "ファシリティ", "コミュニティ", "バンク", "証券", "リース", "リテール", "ファイナンス", "ファイナンシャル", "リミテッド",
    "デパート", "ホテル", "クリエイティブ", "マーケティング", "ネット", "オンライン", "カフェ", "カスタマー", "カード",
    "ショッピング", "ショッピングセンター", "ショップ", "レストラン", "フーズ", "モバイル", "ミュージック", "イベント", "エクスプレス",
    "ストア", "モール", "マート", "ファーム", "パーク", "ホーム", "リフォーム", "リビング", "プロショップ", "プラザ", "タワー", "アリーナ",
    "アカデミー", "インスティテューション", "アプリ", "ギャラリー", "ドットコム", "クラブ", "コンソーシアム", "デジタル", "ビジネス", "ニュース",
    "チャンネル", "エレクトロニクス", "ファクトリー", "ギフト", "スタジアム", "シアター", "シネマ", "映画", "アニメーション",
    "アセットマネジメント", "リサーチ", "シールズ", "コンポーネント", "オートメーション", "セキュリティ", "ポイント", "ストラテジー", "パレス",
    "エンタープライズ", "インスティチュート", "マシン", "プロセス", "イノベーション", "プロダクト",
    "工業", "不動産", "物流", "製作所", "産業", "電機", "銀行", "建設", "製薬", "物産"
]

GENERIC_WORDS: list[str] = [
    "ちくわ", "かまぼこ", "シーフード", "海の幸", "魚", "食品", "商品", "製品", "サービス",
    "飲料", "ドリンク", "ご飯", "弁当", "惣菜", "海鮮丼の素", "おさかなソーセージ", "冷凍食品",
    "デザート", "野菜", "果物", "お菓子", "おかし", "米", "肉", "パン", "カレー", "サラダ",
    "レトルト", "冷凍", "和菓子", "洋菓子", "味噌", "醤油", "豆腐", "乳製品", "卵", "ソース", "油",
    "調味料", "砂糖", "塩", "水", "飲み物", "発酵食品", "乾物", "スナック", "グッズ",
    "証券コード", "証券", "証券番号", "金融", "保険", "銀行", "信託", "信販", "リース", "住宅ローン", "ローン",
    "アプリ", "ウェブ", "モバイル", "ネット", "オンライン", "広告", "カード", "ポイント", "クラブ",
    "イベント", "プロジェクト", "スタジオ", "コミュニティ", "パートナー", "パートナーズ", "グループ", "ホールディングス",
    "デザイン", "ラボ", "サポート", "サロン", "ストア", "ショップ", "カフェ", "モール", "ホテル",
    "ミュージック", "チャンネル", "シネマ", "映画", "アニメーション", "ビデオ", "オンデマンド", "レコード", "マート", "デパート",
    "百貨店", "スーパー", "コンビニ", "ショッピング", "アウトレット", "レストラン", "グルメ", "フード",
    "デリバリー", "テイクアウト", "宅配", "カスタマー", "ニュース", "ミュージカル", "レシピ", "レポート", "パーク",
    "バス", "タクシー", "鉄道", "バンク", "トラベル", "エクスプレス", "パス", "空港", "スタジアム", "スポーツ",
    "アリーナ", "リゾート", "クリニック", "メディカル", "メディア", "ガス", "電力", "エネルギー", "マネジメント", "アセット", "システム",
    "デジタル", "プラットフォーム", "クラウド", "IoT", "ソリューション", "テクノロジー", "プロセス", "イノベーション", "リサーチ", "ビジネス",
    "プラン", "ブランディング", "ディベロップメント", "マーケティング", "コミュニケーション", "プロダクト", "プレミアム", "リミテッド",
    "グリーン", "スマート", "フューチャー", "フレックス", "エコ", "リサイクル", "エディション", "ファミリー", "クラシック",
    "リーダーズ", "エリート", "トップ", "スペシャル", "マスター", "ベーシック", "スタンダード", "ベスト", "セレクト", "プラス",
    "さば缶", "かにかま", "まぐろ缶", "いわし缶", "ツナ缶", "鮭フレーク", "明太子", "蒲鉾", "カニカマ", 
    "納豆", "たまご", "オムレツ", "唐揚げ", "焼き魚", "寿司", "刺身", "サラダチキン", "グラタン",
    "冷やし中華", "ラーメン", "うどん", "そば", "パスタ", "ピザ", "ハンバーグ", "カップ麺",
    "ポテトチップス", "ポテチ", "ポップコーン", "チョコレート", "クッキー", "アイス", "プリン", "ゼリー",
    "キャンディ", "ガム", "おにぎり", "サンドイッチ", "パンケーキ", "フライドポテト", "ホットドッグ", "かに缶"
]

JUNK_PRODUCT_NAMES: list[str] = [
    "ADRランキング", "ADR", "出来高ランキング", "売買高ランキング", "売買代金ランキング",
    "PTS", "注目銘柄", "個別銘柄", "上昇銘柄", "動き", "出来高上位", "PBR", "PER", "時価総額",
    "株価チャート", "理論株価", "目標株価", "掲示板", "株予報", "信用残", "時系列", "株価データ",
    "レーティング", "トレンド", "株価", "株式", "チャート", "株価情報", "株式情報",
    "日々株価", "週間株価", "年間株価", "四本値推移", "取引情報", "株式掲示板", "SBI証券",
    "マネックス証券", "楽天証券", "証券会社", "株式ニュース", "銘柄情報", "会社情報",
    "アセットアライブ", "株価・配当", "株価ヒストリー", "過去10年間", "過去1か月", "株価指数", "指標",
    "モーニングスター", "ストップ高", "ストップ安", "高値更新", "安値更新", "中途採用", "求人",
    "企業概要", "株価時系列", "転職", "企業情報", "就職", "就活", "公式サイト",
    "Stock Price & Latest News"
]

ALLOWED_DOMAINS: list[str] = [
    "nikkei.com", "kabutan.jp", "bloomberg.co.jp", "reuters.com",
    "irbank.net", "minkabu.jp", "moneyworld.jp", "fisco.jp"
]

# List of news domains to trust when fetching headlines
# NEWS_DOMAINS_WHITELIST restricts which domains are allowed in news fetcher results.
NEWS_DOMAINS_WHITELIST = [
    "news.yahoo.co.jp",
    "mainichi.jp",
    "jiji.com",
    "reuters.com",
    "kyodonews.jp",
    "sankei.com",
    "asahi.com",
    "yomiuri.co.jp",
    "tokyo-np.co.jp",
    "itmedia.co.jp",
    # "nikkei.com"
]

JUNK_DOMAINS: list[str] = [
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "wikipedia.org", "linkedin.com", "youtube.com", "ameblo.jp",
    "note.com", "shop", "rakuten.co.jp", "amazon.co.jp"
]

JUNK_URL_PATTERNS: list[str] = [
    "/wiki/", "/mypage/", "/profile/", "/about/", "/support/", "/blog/", "/career/", "/job/", "/shop/", "/event/", "/guide/", "/faq", "/posts/", "/users/", "/account/", "/company/", "/news/all/", "/ir/", "/corp/"
]

SIGNAL_KEYWORDS: list[str] = [
    "下方修正", "上方修正", "買収", "合併", "子会社化", "不正", "訴訟", "監査", "粉飾",
    "大幅減益", "黒字転換", "赤字転落", "新製品", "新サービス", "サービス開始",
    "製品発表", "新規事業", "事業撤退", "生産停止", "販売停止", "リコール", "不祥事",
    "人事異動", "退任", "新任", "大型契約", "受注", "資本提携", "株式交換", "TOB",
    "公募増資", "第三者割当増資", "ストックオプション"
]
BONUS_KEYWORDS: list[str] = [
    "決算発表", "株主総会", "新規上場", "M&A", "業務提携", "IR発表", "開発成功",
    "認可取得", "配当金", "新商品", "リニューアル", "役員報酬", "資本業務提携", "開示",
    "役員変更", "市場変更", "公募増資", "資本提携", "IR", "株式分割"
]

JUNK_KEYWORDS: list[str] = [
    # "株価", "株式", "チャート", "株価情報", "株式情報", "企業情報", "求人", "公式サイト", "サポート", "プロフィール", "会社概要", "お問い合わせ", "コーポレート", "採用情報",
    "ADRランキング", "ADR", "出来高ランキング", "売買高ランキング", "売買代金ランキング",
    "PTS", "注目銘柄", "注目個別銘柄", "話題株", "個別銘柄", "上昇銘柄", "動き", "出来高上位", "PBR", "PER", "時価総額",
    "株価チャート", "理論株価", "目標株価", "掲示板", "株予報", "信用残", "時系列", "株価データ",
    "レーティング", "トレンド", 
    "日々株価", "週間株価", "年間株価", "四本値推移", "取引情報", "株式掲示板", "SBI証券",
    "マネックス証券", "楽天証券", "証券会社", "株式ニュース", "銘柄情報", "会社情報",
    "アセットアライブ", "株価・配当", "株価ヒストリー", "過去10年間", "過去1か月", "株価指数", "指標",
    "モーニングスター", "ストップ高", "ストップ安", "高値更新", "安値更新", "中途採用", 
    "企業概要", "株価時系列", "転職",  "就職", "就活",
    "Stock Price & Latest News", "Research Memo", "アナリスト予想", "前場コメント", "後場コメント",
    "マイページ"
]

LOW_QUALITY_PATTERNS: list[str] = [
    "ランキング", "予想", "株主", "配当"
    # Keep only patterns that mean "not always junk, but often low value".
    # If any others are found to be absolute junk in future, migrate them to JUNK_KEYWORDS.
]

BAD_PATTERNS = [
    "申し訳ありません", "情報は持ち合わせていません", "公式ウェブサイト", "お勧めします",
    "一般的に", "異なることがあります", "ごめんなさい", "分かりません", "提供できません",
    "確認できません", "わかりません", "情報はありません", "ありません",
    # Append to BAD_PATTERNS:
    "該当なし", "N/A", "なし", "情報が不足している", "具体的な情報は持っていません", 
    "会社の略称やブランド名を提供することができません", "公式の企業ウェブサイトや金融ニュースを参照", 
    "情報がありません", "特定できません", "不明", "情報が不足しています", "..."
]

# ----------------------------------------------------------------------
#  Logging
# ----------------------------------------------------------------------
LOG_EMOJI = True   # Set to False to disable emoji in logs

def show_all_config():
    """Debug: Print all major config values for quick inspection."""
    from pprint import pprint
    pprint({k: v for k, v in globals().items() if k.isupper() and not k.startswith("__")})

# Optionally call: show_all_config() if run as main for audit/debug
if __name__ == "__main__":
    show_all_config()