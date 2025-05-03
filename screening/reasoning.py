import openai
import time
from screening.fetcher import fetch_news_for_ticker
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Reason Category Scoring Model ===
CATEGORY_SCORING = {
    "misinterpreted_news": 1.2,
    "slightly_bad_news": 0.7,
    "very_bad_news": 0.0,
    "no_news": 1.1,
    "macro_or_sector_drop": 0.0
}
# =====================================

def categorize_reason_with_gpt(ticker, headlines, price_drop_pct):
    """
    Use GPT to categorize the reason for a stock drop based on headlines + drop size.
    """
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines]) or "No news found."
        drop_text = f"{ticker} dropped by {price_drop_pct:.2f}% today."

        prompt = f"""
{drop_text}
Here are the related news headlines:

{headlines_text}

Based on the headlines and the size of the price drop, categorize the reason for the decline using one of the following categories:

1. misinterpreted_news – news exists, but market overreacted or misunderstood
2. slightly_bad_news – mild earnings/guidance miss or soft negative
3. very_bad_news – clearly negative news, justified sharp drop
4. no_news – no relevant headlines, drop seems irrational
5. macro_or_sector_drop – drop appears driven by overall market or sector event

Return ONLY the category ID from the list above. Nothing else.
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        category = response.choices[0].message["content"].strip()
        return category

    except Exception as e:
        print(f"[ERROR] GPT categorization failed for {ticker}: {e}")
        return "unknown_error"

def attach_reason_to_stocks(filtered_stocks):
    """
    Attaches reason_category, reason_score, and headlines to each filtered stock.
    Drops stocks with excluded categories.
    """
    enriched = []

    for stock in filtered_stocks:
        ticker = stock["ticker"]
        drop_pct = stock.get("price_drop_pct", 0)
        headlines = fetch_news_for_ticker(ticker)
        category = categorize_reason_with_gpt(ticker, headlines, drop_pct)
        score = CATEGORY_SCORING.get(category, 0.0)

        if score == 0.0:
            print(f"[SKIP] {ticker} excluded due to reason: {category}")
            continue

        stock["reason_category"] = category
        stock["reason_score"] = score
        stock["headlines"] = headlines
        enriched.append(stock)

        time.sleep(1.5)  # Respect rate limits

    print(f"✅ {len(enriched)} stocks passed reasoning filter.")
    return enriched
