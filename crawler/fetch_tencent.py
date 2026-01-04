# Renamed from get_tencent_morning_news.py
import time
import os
import sys
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

TAG_CONFIG = {
    "morning": {"id": "aEWqxLtdgmQ=", "name": "早报"},
    "evening": {"id": "bEeox7NdhmM=", "name": "晚报"}
}

def get_links_with_selenium(tag_id, count):
    url = f"https://news.qq.com/tag/{tag_id}"
    print(f"Starting browser to visit: {url} for {count} links...")

    links = []
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Path to chromium-browser in GitHub Actions runner
    options.binary_location = "/usr/bin/chromium-browser"
    
    service = Service() # Assumes chromedriver is in PATH

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(5) # Wait for initial load

        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while len(links) < count:
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/rain/a/'], a[href*='/omn/']")
            for el in elements:
                try:
                    href = el.get_attribute("href")
                    if href and href not in links:
                        links.append(href)
                        print(f"[{len(links)}] Found: {href}")
                        if len(links) >= count:
                            break
                except:
                    continue
            
            if len(links) >= count:
                break
                
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached end of page, stopping scroll.")
                break
            last_height = new_height

    except Exception as e:
        print(f"Selenium error in Tencent fetcher: {e}")
    finally:
        if driver:
            driver.quit()
            
    return links[:count]

def get_article_details(url):
    print(f"  Parsing: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag = soup.find('h1') or soup.find('h2', class_='title')
        if not title_tag:
            # This is likely not a valid article page (e.g., an author page)
            return None
        title = title_tag.get_text(strip=True)

        content_div = soup.find('div', class_='content-article') or soup.find('div', id='ArticleContent')
        content = content_div.get_text(strip=True) if content_div else title
        og_img = soup.find('meta', property='og:image')
        image_url = og_img['content'] if og_img else ""
        
        return {
            "title": title,
            "content": content,
            "source_platform": "Tencent",
            "source_url": url,
            "image": image_url
        }
    except Exception as e:
        print(f"  Failed to parse article {url}: {e}")
        return None

def main(report_type="morning", limit=10):
    if report_type not in TAG_CONFIG:
        print(f"Invalid report type: {report_type}. Use 'morning' or 'evening'.")
        return []
    
    cfg = TAG_CONFIG[report_type]
    links = get_links_with_selenium(cfg['id'], limit)
    
    if not links:
        print("Failed to fetch any Tencent links.")
        return []

    results = []
    for i, link in enumerate(links, 1):
        details = get_article_details(link)
        if details:
            details["rank"] = i
            results.append(details)
        time.sleep(0.5)
        
    print(f"Successfully fetched {len(results)} items from Tencent.")
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tencent News Scraper")
    parser.add_argument("type", choices=["morning", "evening"], help="Report type")
    parser.add_argument("--limit", type=int, default=10, help="Number of items")
    args = parser.parse_args()
    main(report_type=args.type, limit=args.limit)
