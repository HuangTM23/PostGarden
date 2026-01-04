# Renamed from fetch_baidu_hot_detailed.py
import argparse
import csv
import json
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

BOARD_API_URL = "https://top.baidu.com/api/board?platform=pc&tab=realtime"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

def get_headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }

def init_driver():
    if not SELENIUM_AVAILABLE: return None
    print("Initializing Selenium WebDriver for Baidu...")
    try:
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        service = ChromeService() # In GitHub Actions, path is usually handled
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)
        return driver
    except Exception as e:
        print(f"Failed to init driver: {e}")
        return None

def fetch_top_list(limit: int = 10) -> List[Dict]:
    print(f"Fetching top {limit} items from Baidu...")
    try:
        resp = requests.get(BOARD_API_URL, headers=get_headers(), timeout=10)
        resp.raise_for_status()
        content = resp.json().get("data", {}).get("cards", [])[0].get("content", [])
        items = []
        for idx, item in enumerate(content[:limit], 1):
            items.append({
                "rank": idx,
                "title": item.get("word", ""),
                "desc": item.get("desc", ""),
                "search_url": item.get("url", ""),
                "image_url": item.get("img", ""),
                "hot_score": item.get("hotScore", "")
            })
        return items
    except Exception as e:
        print(f"Error fetching Baidu top list: {e}")
        return []

def main(limit=10, out_dir="output"):
    items = fetch_top_list(limit=limit)
    if not items:
        print("No Baidu items found.")
        return []

    # In this new architecture, we don't need to resolve details or save files here.
    # The pipeline will handle the aggregation. We just return the raw data.
    results = []
    for item in items:
        record = {
            "rank": item['rank'],
            "title": item['title'],
            "source_platform": "Baidu",
            "source_url": item['search_url'],
            "content": item['desc'] or item['title'],
            "hot_index": item['hot_score'],
            "image": item['image_url'] # Pass the remote image URL
        }
        results.append(record)
    
    print(f"Successfully fetched {len(results)} items from Baidu.")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baidu Hot News Scraper")
    parser.add_argument("--limit", type=int, default=10, help="Number of items to scrape")
    args = parser.parse_args()
    main(limit=args.limit)
