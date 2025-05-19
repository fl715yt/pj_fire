"""
PJ Fire — Price Drop Reasoning & GPT Overlay

Classifies each price drop reason using rule-based and GPT logic.
Outputs a category for each ticker/day, used in filtering or scoring.
"""

import openai
from config.config import OPENAI_API_KEY, GPT_MODEL, REASONING_CATEGORY_LABELS
from utils.logger import log_info, log_warning, log_error

def classify_price_drop_gpt(ticker, date, price_drop_pct, news_headlines):
    """
    Uses GPT to classify the reason for a stock's price drop.
    Inputs: ticker, date, price drop %, recent headlines (list of strings)
    Returns: category string (one of REASONING_CATEGORY_LABELS)
    """
    openai.api_key = OPENAI_API_KEY

    prompt = (
        f"株式ティッカー: {ticker}\n"
        f"日付: {date}\n"
        f"株価下落率: {price_drop_pct:.2%}\n"
        "直近のニュース:\n"
        + "\n".join(news_headlines) +
        "\n\nこの株価下落の主な理由を、次の5カテゴリのいずれかで分類してください。\n"
        "1. Misinterpreted news\n"
        "2. Slightly bad news\n"
        "3. Very bad news\n"
        "4. Unknown / no news\n"
        "5. Macro/sector drop\n"
        "カテゴリ名だけを1つだけ答えてください。"
    )
    try:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8,
            temperature=0.2,
        )
        result = response["choices"][0]["message"]["content"].strip()
        if result not in REASONING_CATEGORY_LABELS:
            log_warning(f"Unrecognized category from GPT: {result}. Defaulting to 'Unknown / no news'.")
            return "Unknown / no news"
        return result
    except Exception as e:
        log_error(f"GPT classification failed for {ticker} on {date}: {e}")
        return "Unknown / no news"

def attach_reason_to_stocks(candidates, fetch_news_func):
    """
    Adds a 'reason' key (category) to each candidate using GPT.
    `fetch_news_func` should accept (ticker, date) and return list of headlines.
    Returns updated candidate list.
    """
    updated = []
    for c in candidates:
        news_headlines = fetch_news_func(c["ticker"], c["date"])
        category = classify_price_drop_gpt(
            c["ticker"],
            c["date"],
            c["price_drop_pct"],
            news_headlines,
        )
        c["reason"] = category
        updated.append(c)
    log_info(f"Price drop reason classified for {len(updated)} stocks.")
    return updated

# Example usage:
# from data.fetcher import fetch_news_for_ticker
# candidates = screen_stocks("2024-05-17")
# candidates_with_reason = attach_reason_to_stocks(candidates, fetch_news_for_ticker)

