import argparse
import csv
import json
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# Clear system proxy settings to avoid connection errors if proxy is down
for k in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    if k in os.environ:
        del os.environ[k]

# Try importing Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Constants
BOARD_API_URL = "https://top.baidu.com/api/board?platform=pc&tab=realtime"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

def get_headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://top.baidu.com/board?tab=realtime",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def init_driver():
    """Initialize Headless Chrome Driver"""
    if not SELENIUM_AVAILABLE:
        print("Error: Selenium not installed or failed to import.")
        return None
        
    print("Initializing Selenium WebDriver...")
    try:
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # Explicitly disable proxy for Selenium to avoid environment variable issues
        options.add_argument("--no-proxy-server")
        
        # options.add_argument(f"user-agent={USER_AGENT}") # Optional, sometimes helps
        options.binary_location = "/usr/bin/google-chrome"
        
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)
        return driver
    except Exception as e:
        print(f"Failed to init driver: {e}")
        return None

def fetch_top_list(limit: int = 10) -> List[Dict]:
    """
    Fetch the top news list from Baidu Hot Board API.
    """
    print(f"Fetching top {limit} items from {BOARD_API_URL}...")
    try:
        resp = requests.get(BOARD_API_URL, headers=get_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        cards = data.get("data", {}).get("cards", [])
        if not cards:
            print("Warning: No cards found in API response.")
            return []
            
        content = cards[0].get("content", [])
        items = []
        for idx, item in enumerate(content[:limit], 1):
            search_url = item.get("url") or item.get("rawUrl") or ""
            items.append({
                "rank": idx,
                "title": item.get("word") or item.get("query") or "",
                "desc": item.get("desc") or "",
                "search_url": search_url,
                "image_url": item.get("img") or "",
                "hot_score": item.get("hotScore") or ""
            })
        return items
    except Exception as e:
        print(f"Error fetching top list: {e}")
        return []

def extract_from_html(html: str) -> Tuple[str, str, str]:
    """
    Helper to parse HTML content using the s-data logic.
    """
    found_url = ""
    found_source = ""

    # Logic: Look for <!--s-data:{...}-->
    s_data_pattern = r'<!--s-data:(.*?)-->'
    matches = re.findall(s_data_pattern, html, re.DOTALL)
    
    if matches:
        for match in matches:
            try:
                data = json.loads(match)
                
                # Strategy 1: Check citationList (Preferred for Baijiahao URLs)
                card_data = data.get("cardData", {})
                citation_list = card_data.get("citationList", {})
                
                if citation_list:
                    ref_data = citation_list.get("data", {})
                    ref_list = ref_data.get("referenceList", [])
                    
                    if ref_list and isinstance(ref_list, list) and len(ref_list) > 0:
                        first_ref = ref_list[0]
                        real_url = first_ref.get("url", "")
                        source = first_ref.get("source", "")
                        
                        if isinstance(source, dict):
                            source = source.get("name", "")
                        
                        if real_url:
                            found_url = real_url
                            found_source = str(source)
                            # If we have both, we can break, but maybe we want to keep checking if source is empty?
                            if found_source:
                                break

                # Strategy 2: Check blocksList for "sourceList" (Fallback)
                if not found_url:
                    blocks_list = data.get("cardData", {}).get("blocksList", [])
                    for block in blocks_list:
                        items = block.get("data", {}).get("items", [])
                        for item in items:
                            # Check sourceList
                            source_list = item.get("sourceList", [])
                            if source_list and isinstance(source_list, list) and len(source_list) > 0:
                                src_text = source_list[0].get("text", "")
                                if src_text:
                                    # Try to find a link in this item too
                                    link_info = item.get("linkInfo", {})
                                    link = link_info.get("href", "") or link_info.get("url", "")
                                    
                                    found_url = link
                                    found_source = src_text
                                    if found_url and found_source:
                                        break
                        if found_url and found_source:
                            break

            except json.JSONDecodeError:
                continue
            except Exception:
                continue
            
            if found_url and found_source:
                break
    else:
        # Fallback: simple Baijiahao links if no s-data
        bjh_pattern = r'https://baijiahao\.baidu\.com/s\?id=\d+'
        bjh_matches = re.findall(bjh_pattern, html)
        if bjh_matches:
             found_url = bjh_matches[0]
             found_source = "Baidu (Fallback)"

    # Strategy 3: BeautifulSoup DOM Parsing
    if not found_source or found_source == "Baidu (Fallback)":
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # 3.1 Check for specific "cosc-source-text"
            cosc_source = soup.select_one(".cosc-source-text")
            if cosc_source:
                src_text = cosc_source.get_text(strip=True)
                if src_text:
                    found_source = src_text
                    
                    # If we also missed the URL, try to find it near the source
                    if not found_url:
                        link_el = soup.select_one("a.title_dIF3B, a.c-blocka")
                        found_url = link_el.get("href", "") if link_el else ""

            # 3.2 Look for other standard classes if still no source
            if not found_source:
                # Try more specific Baidu search result selectors
                source_el = soup.select_one(".c-showurl, .source_1V_v6, .c-source, .c-gray, .c-color-gray")
                if source_el:
                    src_text = source_el.get_text(strip=True)
                    # Clean up: remove date, etc.
                    src_text = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', src_text).strip()
                    src_text = src_text.split(' ')[0]
                    if src_text and len(src_text) < 20:
                        found_source = src_text
                
                if not found_source:
                    first_result = soup.select_one(".result, .c-container, .new-pmd")
                    if first_result:
                        source_el = first_result.select_one(".source-text, .c-color-gray, span.c-gray, .newTimeFactor_vocab, .c-source")
                        if source_el:
                            src_text = source_el.get_text(strip=True)
                            if src_text and len(src_text) < 20 and ":" not in src_text:
                                found_source = src_text
                            
                    if not found_url:
                        link_el = first_result.select_one("a")
                        found_url = link_el.get("href", "") if link_el else ""

        except Exception:
            pass

    return found_url, found_source, ""

def resolve_real_source(search_url: str, driver=None) -> Tuple[str, str, str]:
    """
    Access the search page and extract real info.
    Uses Selenium if 'driver' is provided, else 'requests'.
    """
    if not search_url:
        return "", "", ""

    print(f"  -> resolving: {search_url[:60]}...")
    html = ""
    
    # 1. Try Selenium if available
    if driver:
        try:
            driver.get(search_url)
            time.sleep(2) 
            html = driver.page_source
            
            # Check for Captcha immediately
            if "百度安全验证" in driver.title or "security-verification" in html:
                print("    [!] BLOCKING DETECTED: Baidu Security Verification (Captcha).")
                return "", "Baidu (Captcha Blocked)", ""
                
        except Exception as e:
            print(f"    [!] Selenium error: {e}")
            return "", "Selenium Error", ""
    else:
        # 2. Try Requests
        try:
            resp = requests.get(search_url, headers=get_headers(), timeout=10)
            if "wappass.baidu.com" in resp.url or "security-verification" in resp.text:
                print("    [!] Captcha detected (Requests).")
                return "", "Security Check", ""
            html = resp.text
        except Exception as e:
            print(f"    [!] Request error: {e}")
            return "", "Request Error", ""

    # Parse what we got
    real_url, source, content = extract_from_html(html)
    
    # If we got a Baijiahao link but no specific source, try to resolve it from the article page
    if real_url and "baijiahao.baidu.com" in real_url and source == "Baidu (Fallback)":
        print(f"    [+] Resolving specific source from Baijiahao: {real_url}")
        bj_source = resolve_baijiahao_source(real_url, driver)
        if bj_source:
            source = bj_source
            
    return real_url, source, content

def resolve_baijiahao_source(url: str, driver=None) -> str:
    """
    Visit a Baijiahao page and extract the author/source name using BeautifulSoup.
    """
    try:
        html = ""
        if driver:
            driver.get(url)
            time.sleep(3)
            html = driver.page_source
        else:
            resp = requests.get(url, headers=get_headers(), timeout=10)
            html = resp.text
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Try author name selectors
        author = soup.select_one(".author-name, span.author-name, a.author-name, span[class*='author'], a[class*='author']")
        if author:
            name = author.get_text(strip=True)
            if 1 < len(name) < 30:
                return name

        # 2. Try meta og:site_name
        meta = soup.find("meta", attrs={"property": "og:site_name"})
        if meta and meta.get("content"):
            return meta["content"].strip()
            
        # 3. Try meta name=source
        meta = soup.find("meta", attrs={"name": "source"})
        if meta and meta.get("content"):
            return meta["content"].strip()

    except Exception as e:
        print(f"    [!] Error resolving Baijiahao source: {e}")
        
    return ""

def download_image(url: str, save_path: Path) -> bool:
    if not url:
        return False
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        if resp.status_code == 200:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False

def main(limit=10, out_dir="output", use_selenium=False):
    print("\n" + "-"*30)
    print("🔍 [Baidu] Starting Hot News Scraper")
    print("-"*30)
    
    # Init Driver if requested
    driver = None
    if use_selenium:
        driver = init_driver()
        if not driver:
            print("  [!] Falling back to requests (Selenium init failed).")
    
    try:
        # 1. Get Top List
        items = fetch_top_list(limit=limit)
        if not items:
            print("  [!] No items found from Baidu API.")
            return []

        print(f"  [✓] Successfully fetched top list. Processing {len(items)} items...")
        
        results = []
        
        # 2. Process each item
        for item in items:
            print(f"\n  [#{item['rank']}] Processing: {item['title']}")
            
            # Resolve real source
            real_url, source_name, _ = resolve_real_source(item['search_url'], driver=driver)
            
            # If we couldn't resolve, fallback
            final_url = real_url if real_url else item['search_url']
            final_source = source_name if source_name else "Baidu"
            
            print(f"      - Source: {final_source}")
            print(f"      - URL: {final_url[:70]}...")

            # Logic: If content is empty, use title
            content_val = item['desc']
            if not content_val:
                content_val = item['title']

            record = {
                "rank": item['rank'],
                "title": item['title'],
                "source_platform": final_source,
                "source_url": final_url,
                "content": content_val,
                "hot_index": item['hot_score'],
                "image": item['image_url'] # Return REMOTE URL for pipeline
            }
            results.append(record)
            
            if not use_selenium:
                time.sleep(1) # sleep if using requests

        print(f"\n  [✓] Baidu scraping complete. Total items: {len(results)}")
        return results

    finally:
        if driver:
            print("Closing Selenium Driver...")
            driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detailed Baidu Hot News Scraper")
    parser.add_argument("--limit", type=int, default=10, help="Number of items to scrape")
    parser.add_argument("--out-dir", type=str, default="output", help="Output directory")
    parser.add_argument("--use-selenium", action="store_true", help="Use Selenium for better anti-bot evasion")
    args = parser.parse_args()
    
    results = main(limit=args.limit, out_dir=args.out_dir, use_selenium=args.use_selenium)
    
    # Dump to JSON for verification if run standalone
    if results:
        out_path = Path(args.out_dir) / "baidu_raw.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

