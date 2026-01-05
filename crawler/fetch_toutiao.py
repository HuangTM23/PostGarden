# Renamed from fetch_toutiao_hot.py
import argparse
import csv
import json
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

API_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_headers():
    return {"User-Agent": USER_AGENT, "Accept": "*/*", "Referer": "https://www.toutiao.com/"}

def init_driver():
    if not SELENIUM_AVAILABLE: return None
    print("Initializing Selenium...")
    try:
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-proxy-server")
        options.add_argument("--disable-images")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f"user-agent={USER_AGENT}")

        # 设置页面加载策略为 eager (不等待图片加载完成)
        options.page_load_strategy = 'eager'

        options.binary_location = "/usr/bin/google-chrome"
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 注入 JS 隐藏 Selenium 特征
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
          "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
        })
        
        driver.set_page_load_timeout(60) # 增加到60秒
        return driver
    except Exception as e:
        print(f"Failed to init driver: {e}")
        return None

def fetch_hot_list(limit=10):
    print(f"Fetching hot list...")
    try:
        resp = requests.get(API_URL, headers=get_headers(), timeout=15)
        return resp.json().get("data", [])[:limit]
    except Exception as e:
        print(f"  [Error] Failed to fetch hot list: {e}")
        return []

def download_image(url, path):
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15, stream=True)
        if resp.status_code == 200:
            with open(path, "wb") as f:
                for chunk in resp.iter_content(8192): f.write(chunk)
            return True
    except: return False

def resolve_data(rank, title, initial_url, hot_index, driver):
    """
    Core Logic (Synced with verify_toutiao_logic.py):
    1. Visit initial URL.
    2. If it's a 'Trending' page, find the specific content link (/video/, /w/, /article/).
    3. Visit the content page.
    4. Extract Platform and Content using verified selectors.
    """
    source_platform = "Toutiao"
    source_url = initial_url
    content = ""

    try:
        # --- Step 1 & 2: Resolve Target URL ---
        if "/trending/" in initial_url:
            driver.get(initial_url)
            target_href = None
            link_type = "unknown"
            
            try:
                # Wait for any valid content link
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/video/') or contains(@href, '/w/') or contains(@href, '/article/')]" ))
                )
                links = driver.find_elements(By.XPATH, "//a[contains(@href, '/video/') or contains(@href, '/w/') or contains(@href, '/article/')]" )
                
                for link in links:
                    h = link.get_attribute("href")
                    if not h: continue
                    
                    if "/video/" in h and re.search(r"/video/\d+", h):
                        target_href = h; link_type = "video"; break
                    if "/w/" in h and re.search(r"/w/\d+", h):
                        target_href = h; link_type = "w"; break
                    if "/article/" in h and re.search(r"/article/\d+", h):
                        target_href = h; link_type = "article"; break
            except Exception as e:
                print(f"  [Warn] No content link found on trending page: {e}")

            if target_href:
                source_url = target_href
                if source_url.startswith("//"): source_url = "https:" + source_url
                elif source_url.startswith("/"): source_url = "https://www.toutiao.com" + source_url
            else:
                print(f"  [Warn] Failed to resolve trending URL, using original.")
        else:
            # Direct article link
            link_type = "article" 

        # --- Step 3: Visit Target Content Page ---
        if source_url != driver.current_url:
            driver.get(source_url)
        
        # Wait slightly for render
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # --- Step 4: Extract Data ---
        
        # A. Source Platform
        # Priority: .author-info .name -> .article-meta .name -> .author-name -> .user-card-name
        platform_el = soup.select_one(".author-info .name") or \
                      soup.select_one(".article-meta .name") or \
                      soup.select_one(".author-info .author-name") or \
                      soup.select_one(".user-card-name") or \
                      soup.select_one(".media-info .name")
        
        if platform_el:
            source_platform = platform_el.get_text(strip=True)
        else:
            # Fallback to meta tags
            meta_name = soup.find('meta', attrs={'name': 'author'}) or \
                        soup.find('meta', property='og:site_name')
            if meta_name:
                source_platform = meta_name.get('content', 'Toutiao')

        # B. Content
        if link_type == "video" or ("/video/" in source_url):
            # Video: Use Title
            content = title
        else:
            # Article / Micro Headline
            # Priority 1: Specific Article Tag (syl-article-base, etc.)
            article_tag = soup.select_one('article.syl-page-article, article.tt-article-content, article.syl-article-base')
            
            if article_tag:
                content = article_tag.get_text(separator="\n", strip=True)
            else:
                # Priority 2: Micro Headline HTML
                w_div = soup.select_one(".weitoutiao-html")
                if w_div:
                    content = w_div.get_text(separator="\n", strip=True)
                else:
                    # Priority 3: Fallback Paragraphs
                    ps = soup.select(".article-content p, article p")
                    if ps:
                        content = "\n".join([p.get_text(strip=True) for p in ps])

        if not content: content = title # Fallback

    except Exception as e:
        print(f"  [Error] Processing {initial_url}: {e}")

    return source_platform, source_url, content

def main(limit=10, out_dir="output"):
    # Clean proxy envs to avoid Selenium issues
    for k in list(os.environ.keys()):
        if k.lower().endswith('_proxy'): del os.environ[k]

    driver = init_driver()
    if not driver:
        print("Selenium is required. Exiting.")
        return []

    try:
        items = fetch_hot_list(limit)
        if not items: return []

        out_dir_path = Path(out_dir)
        # images_dir = out_dir_path / "images" # Pipeline handles images
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # out_dir_path.mkdir(parents=True, exist_ok=True)
        # images_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        print(f"Processing {len(items)} items from Toutiao...")
        for idx, item in enumerate(items, 1):
            title = item.get("Title", "N/A")
            hot_index = item.get("HotValue", "N/A")
            initial_url = item.get("Url", "")
            image_url = item.get("Image", {}).get("url", "")
            
            print(f"#{idx}: {title} (Hot: {hot_index})")
            
            source_platform, source_url, content = resolve_data(idx, title, initial_url, hot_index, driver)
            
            # For pipeline, we just return the remote image URL.
            # Pipeline will handle downloading.
            saved_image_path = image_url 
            
            record = {
                "rank": idx,
                "title": title,
                "hot_index": hot_index,
                "source_platform": source_platform,
                "source_url": source_url,
                "content": content,
                "image": saved_image_path
            }
            results.append(record)
            # Small delay to be polite
            time.sleep(1)

        print(f"\nDone. Fetched {len(results)} items from Toutiao.")
        return results

    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Toutiao Hot News Scraper")
    parser.add_argument("--limit", type=int, default=10, help="Number of items")
    parser.add_argument("--out-dir", type=str, default="toutiao", help="Output directory")
    args = parser.parse_args()
    
    results = main(limit=args.limit, out_dir=args.out_dir)
    
    if results:
        out_path = Path(args.out_dir) / "toutiao_raw.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
