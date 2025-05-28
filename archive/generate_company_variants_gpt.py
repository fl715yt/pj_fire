import os
import openai
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

CSV_PATH = "pjfire_topix_company_patterns.csv"
OUT_PATH = "pjfire_topix_company_patterns_expanded.csv"
DELAY_SEC = 1.2

PROMPT = """
日本の金融ニュースやSNSで「{company_name}」（証券コード: {ticker}）を表す固有名詞（略称、ニックネーム、製品名、ブランド名など）を最大10個、日本語で挙げてください。
一般名詞や業界一般で使われる言葉（例：ファミレス、ステーキ、銀行、食品、家電、ゲーム、株式など）は除外してください。
固有名詞のみ、会社独自の呼び方やブランド・略称を含めてください。重複・曖昧な語や短縮形でも、会社特有でなければ除外してください。
回答はカンマ区切りで、例：A, B, C, D
"""

def gpt_get_variants(company_name, ticker):
    prompt = PROMPT.format(company_name=company_name, ticker=ticker)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.2,
        )
        result = response.choices[0].message.content
        return [v.strip() for v in result.split(",") if v.strip()]
    except Exception as e:
        print(f"[ERROR] GPT API for {company_name}: {e}")
        return []

def main():
    df = pd.read_csv(CSV_PATH, dtype=str)
    all_variants = []
    for i, row in df.iterrows():
        print(f"Processing: {row['ticker']} {row['company_name']} ({i+1}/{len(df)})")
        variants = gpt_get_variants(row['company_name'], row['ticker'])
        all_variants.append(" / ".join(variants))
        time.sleep(DELAY_SEC)
    df["variants"] = all_variants
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved: {OUT_PATH}")
    print(df.head(10))

if __name__ == "__main__":
    main()
