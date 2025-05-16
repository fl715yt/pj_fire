# backtest/reasoning_bt.py

import sqlite3
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from backtest.news_fetcher_bt_cse import fetch_news_for_ticker

load_dotenv()
DB_FILE = "backtest/backtest.db"
GPT_MODEL = "gpt-3.5-turbo"
RETRY_LIMIT = 3
RETRY_DELAY = 5  # seconds

# Initialize v1.x OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_uncategorized_signals():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, ticker, signal_date, price_drop_pct
        FROM bt_signals
        WHERE drop_reason IS NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def categorize_reason(news_headlines, price_drop_pct):
    prompt = f"""
The following stock dropped by {price_drop_pct:.1f}% on the Tokyo Stock Exchange.

Recent news headlines:
{news_headlines}

Categorize the reason into one of the following:
1. Misinterpreted news — Keep (score high)
2. Slightly bad news — Keep (score low)
3. Very bad news — Exclude
4. Unknown / no news — Keep (core signal)
5. Macro or sector-wide drop — Exclude

Only return the number and short reason. Example: "2. Slight downgrade in earnings forecast."
"""

    for attempt in range(RETRY_LIMIT):
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ GPT request failed (attempt {attempt + 1}/{RETRY_LIMIT}): {e}")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
            else:
                return "5. GPT ERROR: Could not classify"


def update_drop_reason(signal_id, reason):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bt_signals
        SET drop_reason = ?
        WHERE id = ?
    """, (reason, signal_id))
    conn.commit()
    conn.close()


def main():
    rows = get_uncategorized_signals()
    for signal_id, ticker, signal_date, drop_pct in rows:
        print(f"🟡 Processing {ticker} on {signal_date}...")
        headlines = fetch_news_for_ticker(ticker, signal_date)
        reason = categorize_reason(headlines, drop_pct)
        update_drop_reason(signal_id, reason)
        print(f"✅ [{ticker} on {signal_date}] → {reason}")


if __name__ == "__main__":
    main()
