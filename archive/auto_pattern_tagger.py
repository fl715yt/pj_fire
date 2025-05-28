import pandas as pd
import re
from collections import Counter, defaultdict

INPUT_CSV = "batch_headlines_raw.csv"
TOP_UNIGRAMS = 300
TOP_BIGRAMS = 200
JUNK_FREQ_THRESH = 0.008    # >0.8% of headlines = junk
SIGNAL_FREQ_THRESH = 0.0004 # <0.04% of headlines = signal
BONUS_WORDS = ["決算発表", "株主総会", "配当金", "株式分割", "新規上場", "市場変更", "新商品", "リニューアル", "業務提携", "新規受注", "上場廃止", "業績予想修正", "役員報酬", "資本業務提携", "IR発表", "開発成功", "認可取得", "増資", "M&A"]
SIGNAL_SEEDS = ["下方修正", "上方修正", "減益", "増益", "買収", "合併", "子会社化", "不正", "訴訟", "監査", "粉飾", "大幅減益", "黒字転換", "赤字転落", "新製品", "新サービス", "サービス開始", "製品発表", "新規事業", "事業撤退", "生産停止", "販売停止", "リコール", "不祥事", "人事異動", "退任", "新任", "大型契約", "受注", "資本提携", "株式交換", "TOB", "公募増資", "第三者割当増資", "ストックオプション"]
LOW_QUAL_SEEDS = ["予想", "配当", "決算短信", "業績", "進捗", "増配", "減配", "優待", "業績予想", "新高値", "新安値", "連結決算", "修正", "見通し", "業績修正", "速報", "情報", "IR情報", "四季報", "PR TIMES", "MINKABU", "株主", "IRバンク", "投資判断", "アナリスト", "株価目標", "配当利回り", "取締役", "監査", "開示", "発表"]

# Regex for splitting Japanese/English
TOKENIZER = re.compile(r"[・、。『』【】「」（）()|：:;,.!?\s\dA-Za-z]+")

def get_tokens(text):
    return [t for t in TOKENIZER.split(str(text)) if t]

def get_ngrams(tokens, n):
    return ["".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def auto_pattern_tag(csv_path):
    df = pd.read_csv(csv_path)
    headlines = df["headline"].dropna().astype(str).tolist()
    n = len(headlines)
    print(f"Loaded {n} headlines.")

    # Count unigrams and bigrams
    unigram_counter = Counter()
    bigram_counter = Counter()
    for h in headlines:
        tokens = get_tokens(h)
        unigram_counter.update(tokens)
        bigram_counter.update(get_ngrams(tokens, 2))

    # Tagging logic
    junk_keywords = set()
    signal_keywords = set()
    bonus_keywords = set(BONUS_WORDS)
    low_quality_patterns = set(LOW_QUAL_SEEDS)

    for word, freq in unigram_counter.most_common(TOP_UNIGRAMS):
        rel_freq = freq / n
        if word in SIGNAL_SEEDS:
            signal_keywords.add(word)
        elif word in BONUS_WORDS:
            bonus_keywords.add(word)
        elif word in LOW_QUAL_SEEDS:
            low_quality_patterns.add(word)
        elif rel_freq > JUNK_FREQ_THRESH:
            junk_keywords.add(word)
        elif rel_freq < SIGNAL_FREQ_THRESH and len(word) > 1:
            signal_keywords.add(word)
        elif rel_freq < 3 * JUNK_FREQ_THRESH:
            low_quality_patterns.add(word)
    # Add top bigrams (good for patterns like "株価チャート", "出来高ランキング")
    for bg, freq in bigram_counter.most_common(TOP_BIGRAMS):
        rel_freq = freq / n
        if any(seed in bg for seed in SIGNAL_SEEDS):
            signal_keywords.add(bg)
        elif any(seed in bg for seed in BONUS_WORDS):
            bonus_keywords.add(bg)
        elif any(seed in bg for seed in LOW_QUAL_SEEDS):
            low_quality_patterns.add(bg)
        elif rel_freq > JUNK_FREQ_THRESH:
            junk_keywords.add(bg)
        elif rel_freq < SIGNAL_FREQ_THRESH and len(bg) > 2:
            signal_keywords.add(bg)
        elif rel_freq < 3 * JUNK_FREQ_THRESH:
            low_quality_patterns.add(bg)

    # Clean out trivial overlaps (signal > junk > lowqual)
    bonus_keywords -= (signal_keywords | junk_keywords)
    low_quality_patterns -= (signal_keywords | junk_keywords | bonus_keywords)
    signal_keywords -= junk_keywords

    # Sort by frequency for pretty output
    junk_keywords = sorted(junk_keywords, key=lambda x: -unigram_counter.get(x, 0) - bigram_counter.get(x, 0))
    signal_keywords = sorted(signal_keywords, key=lambda x: -unigram_counter.get(x, 0) - bigram_counter.get(x, 0))
    bonus_keywords = sorted(bonus_keywords)
    low_quality_patterns = sorted(low_quality_patterns)

    # Output: Python lists
    print("\n\n### JUNK_KEYWORDS ###")
    print("JUNK_KEYWORDS = [")
    for k in junk_keywords: print(f'    "{k}",')
    print("]\n")
    print("### SIGNAL_KEYWORDS ###")
    print("SIGNAL_KEYWORDS = [")
    for k in signal_keywords: print(f'    "{k}",')
    print("]\n")
    print("### BONUS_KEYWORDS ###")
    print("BONUS_KEYWORDS = [")
    for k in bonus_keywords: print(f'    "{k}",')
    print("]\n")
    print("### LOW_QUALITY_PATTERNS ###")
    print("LOW_QUALITY_PATTERNS = [")
    for k in low_quality_patterns: print(f'    "{k}",')
    print("]\n")

    # Output: CSVs for optional review
    pd.DataFrame({"junk": junk_keywords}).to_csv("junk_keywords.csv", index=False)
    pd.DataFrame({"signal": signal_keywords}).to_csv("signal_keywords.csv", index=False)
    pd.DataFrame({"bonus": bonus_keywords}).to_csv("bonus_keywords.csv", index=False)
    pd.DataFrame({"low_quality": low_quality_patterns}).to_csv("low_quality_patterns.csv", index=False)
    print("\nCSV files saved for manual review (if needed).")

if __name__ == "__main__":
    auto_pattern_tag(INPUT_CSV)
