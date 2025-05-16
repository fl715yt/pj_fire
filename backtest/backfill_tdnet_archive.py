# backfill_tdnet_archive.py

import os
import json
from time import sleep
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TDNET_DATA_DIR = "data/tdnet"
BASE_URL = "https://www.release.tdnet.info/index.html"

# Initialize headless Chrome
def init_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)

# Scrape a single day
def scrape_day(driver, target_date):
    ymd = target_date.strftime("%Y/%m/%d")
    print(f"🟡 Scraping {ymd}...")

    driver.get(BASE_URL)
    sleep(2)

    try:
        date_input = driver.find_element(By.ID, "inputDate")
        date_input.clear()
        date_input.send_keys(ymd)

        search_button = driver.find_element(By.ID, "search_submit")
        search_button.click()
        sleep(2)
    except Exception as e:
        print(f"[ERROR] Navigation failure: {e}")
        return []

    rows = driver.find_elements(By.CSS_SELECTOR, "#main-table tr[class^='normal']")
    results = []

    for row in rows:
        try:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 5:
                continue
            code = cols[0].text.strip()
            name = cols[1].text.strip()
            title = cols[3].text.strip()
            timestamp = f"{target_date.strftime('%Y-%m-%d')}T{cols[4].text.strip()}:00"
            link = cols[3].find_element(By.TAG_NAME, "a").get_attribute("href")

            results.append({
                "ticker": code,
                "company_name": name,
                "title": title,
                "timestamp": timestamp,
                "url": link
            })
        except Exception as e:
            print(f"[WARN] Row skipped: {e}")
            continue

    return results

# Save results
def save_results(date_str, records):
    os.makedirs(TDNET_DATA_DIR, exist_ok=True)
    path = os.path.join(TDNET_DATA_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"✅ {date_str}: {len(records)} records saved")

# Main range controller
def run_backfill(start_date_str, end_date_str):
    driver = init_browser()

    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    delta = timedelta(days=1)

    current = start
    while current <= end:
        try:
            results = scrape_day(driver, current)
            save_results(current.strftime("%Y-%m-%d"), results)
        except Exception as e:
            print(f"[ERROR] Failed on {current.date()}: {e}")
        current += delta
        sleep(1)

    driver.quit()

if __name__ == "__main__":
    run_backfill("2024-04-14", "2024-05-14")
