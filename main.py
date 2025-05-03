from screening.fetcher import fetch_all_data
from screening.screener import run_screening_pipeline
from line_bot.line_sender import send_signals
from utils.logger import log_info

def main():
    log_info("===== PJ Fire Daily Run Started =====")
    
    market_data = fetch_all_data()
    screened_signals = run_screening_pipeline(market_data)
    send_signals(screened_signals)

    log_info("===== PJ Fire Daily Run Complete =====")

if __name__ == "__main__":
    main()
