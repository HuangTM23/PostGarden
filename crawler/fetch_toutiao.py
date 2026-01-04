# Renamed from fetch_toutiao_hot.py
import argparse
import json
import os
import time
from collections import OrderedDict
from pathlib import Path

import requests

API_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_headers():
    return {"User-Agent": USER_AGENT, "Accept": "*/*", "Referer": "https://www.toutiao.com/"}

def main(limit=10, out_dir="output"):
    print(f"Fetching top {limit} items from Toutiao...")
    try:
        resp = requests.get(API_URL, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        items = resp.json().get("data", [])[:limit]
        
        results = []
        for idx, item in enumerate(items, 1):
            record = {
                "rank": idx,
                "title": item.get("Title", "N/A"),
                "hot_index": item.get("HotValue", "N/A"),
                "source_platform": "Toutiao",
                "source_url": item.get("Url", ""),
                "content": item.get("Title"), # Use title as content for simplicity
                "image": item.get("Image", {}).get("url", "")
            }
            results.append(record)
        
        print(f"Successfully fetched {len(results)} items from Toutiao.")
        return results
    except Exception as e:
        print(f"  [Error] Failed to fetch Toutiao hot list: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Toutiao Hot News Scraper")
    parser.add_argument("--limit", type=int, default=10, help="Number of items")
    args = parser.parse_args()
    main(limit=args.limit)
