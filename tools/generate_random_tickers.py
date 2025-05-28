import pandas as pd
import random

# Load your variants file
VARIANT_CSV = "pjfire_topix_company_patterns_filtered.csv"
variant_df = pd.read_csv(VARIANT_CSV, dtype=str)
all_tickers = variant_df["ticker"].unique().tolist()

# Randomly sample (excluding "known eventful" stocks you'll add)
random.seed(42)  # for reproducibility
random_tickers = random.sample(all_tickers, 120)

# List of "eventful/volatile" tickers you want to prioritize (add as needed)
eventful_tickers = [
    "9984",  # SoftBank
    "7203",  # Toyota
    "8306",  # Mitsubishi UFJ
    "4751",  # CyberAgent
    "4568",  # Daiichi Sankyo
    "2413",  # M3
    "6501",  # Hitachi
    "8591",  # Orix
    "6752",  # Panasonic
    "3436",  # Sumco
    "8035",  # Tokyo Electron
    "6506",  # Yaskawa
    "9202",  # ANA
    "9983",  # Fast Retailing
    # ...add any others you want...
]

# Final deduped ticker list
TICKERS = list(dict.fromkeys(eventful_tickers + random_tickers))  # preserves order
print("Ticker sample:", TICKERS)