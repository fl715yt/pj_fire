"""
PJ Fire — News Reasoning via GPT
Uses GPT to classify price drop reasons based on headlines, price drop %, and date.
All category mappings, scoring, and GPT config are centralized via config/config.py.
"""

import os
import openai
import time
from dotenv import load_dotenv
from config.config import (
    OPENAI_API_KEY,
    GPT_MODEL,
    GPT_DELAY_SEC,
    REASONING_CATEGORY_LABELS,
    CATEGORY_SCORING,
)

load_dotenv()

def categorize_reason_with_gpt(ticker, date, price_drop_pct, headlines):
    """
    Use GPT to categorize the reason for a stock drop.
    Returns: category string (see REASONING_CATEGORY_LABELS)
    """
    openai.api_key = OPENAI_API_KEY

    if isinstance(headlines, str):
        headlines_text = headlines
    elif isinstance(headlines, list):
        headlines_text = "\n".join([f"- {h}" for h in headlines]) if headlines else "No news found."
    else:
        headlines_text = "No news found."

    prompt = f"""
ティッカー: {ticker}
日付: {date}
株価下落率: {price_drop_pct:.2f}%
関連ニュース:
{headlines_text}

上記の情報をもとに、この株価下落の主な理由を以下のカテゴリから1つだけ選び、そのカテゴリ名のみを出力してください。

1. misinterpreted_news – ニュースがあるが、市場が過剰反応や誤解をした場合
2. slightly_bad_news – 軽度の悪材料、やや悪い決算やガイダンス
3. very_bad_news – 明らかに悪材料（粉飾、不正、大幅赤字等）
4. no_news – 関連ニュースなし。下落理由が不明
5. macro_or_sector_drop – 市場全体またはセクター要因

カテゴリ名のみ（例: misinterpreted_news）のみ答えてください。余計な説明は不要です。
"""

    try:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=12,
            temperature=0,
        )
        category = response.choices[0].message["content"].strip()
        # Validate result
        if category not in REASONING_CATEGORY_LABELS:
            print(f"[WARN] Unrecognized GPT category for {ticker} on {date}: '{category}'")
            return "no_news"
        return category
    except Exception as e:
        print(f"[ERROR] GPT categorization failed for {ticker} on {date}: {e}")
        return "no_news"

# Example usage:
# cat = categorize_reason_with_gpt("7203", "2024-05-10", -0.07, ["決算悪化で急落", "新規IR発表"])
# print(cat)
