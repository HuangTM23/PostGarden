import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import argparse
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://www.nytimes.com"
SECTION_URL = "https://www.nytimes.com/section/todayspaper"
OUTPUT_DIR = "nytimes_data"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
DATA_FILE = os.path.join(OUTPUT_DIR, "data.json")

# Improved Headers to mimic a real browser session
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def setup_directories():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

def sanitize_filename(text):
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    return text.replace(" ", "_").lower()[:50]

def download_image(url, filename):
    try:
        if not url:
            return None
        # Ensure URL is absolute
        if not url.startswith('http'):
             url = urljoin(BASE_URL, url)
             
        response = requests.get(url, headers=HEADERS, stream=True, timeout=10)
        response.raise_for_status()
        filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filepath
    except Exception as e:
        print(f"  Failed to download image {url}: {e}")
        return None

def fetch_article_content_full(url):
    """Attempts to fetch full content from article page. Returns (content, image_url)"""
    try:
        time.sleep(2) # Polite delay
        print(f"  Fetching full article: {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Content
        # NYT uses <section name="articleBody"> usually
        article_body = soup.find('section', attrs={'name': 'articleBody'})
        content = ""
        if article_body:
            paragraphs = article_body.find_all('p')
            content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        else:
            # Fallback
            paragraphs = soup.find_all('p', class_=re.compile(r'css-axufdj|css-158dogj|css-at9mc1')) 
            if paragraphs:
                 content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])

        # Image
        image_url = None
        meta_img = soup.find('meta', property='og:image')
        if meta_img:
            image_url = meta_img.get('content')
            
        return content, image_url
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("  Access Denied (403) for full article. Using summary.")
        else:
            print(f"  HTTP Error fetching article: {e}")
        return None, None
    except Exception as e:
        print(f"  Error fetching article: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=10, help="Number of news items to scrape.")
    args = parser.parse_args()

    setup_directories()
    
    print(f"Fetching {SECTION_URL}...")
    try:
        response = requests.get(SECTION_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Identify "The Front Page" section
        # Logic: Find header "The Front Page", get its parent section, find all article-like list items
        
        # We will look for all list items that contain an article link
        # This covers "The Front Page" and subsequent sections if we want to limit, we can.
        # Let's target specific sections if possible, or just the top X articles.
        # User asked for "Todays Paper" news data.
        
        all_articles = []
        
        # Find all LI elements that have an H3 (headline) and an A tag
        # This is a generic robust way to find articles on NYT section pages
        candidates = soup.find_all('li')
        
        rank = 0
        for item in candidates:
            # Check if it looks like an article
            headline_tag = item.find(['h2', 'h3'])
            link_tag = item.find('a')
            
            if headline_tag and link_tag:
                href = link_tag.get('href')
                if not href or href.startswith('#') or 'crosswords' in href:
                    continue
                    
                full_url = urljoin(BASE_URL, href)
                
                # Check for duplicate URLs
                if any(a['source_url'] == full_url for a in all_articles):
                    continue
                
                rank += 1
                title = headline_tag.get_text(strip=True)
                
                # Extract Summary from list item (Fallback content)
                summary_tag = item.find('p')
                summary = summary_tag.get_text(strip=True) if summary_tag else ""
                
                # Extract Image from list item (Thumbnail)
                img_tag = item.find('img')
                list_image_url = img_tag.get('src') if img_tag else None
                
                print(f"[{rank}] Found: {title}")
                
                # Try to fetch full content
                full_content, full_image_url = fetch_article_content_full(full_url)
                
                final_content = full_content if full_content else summary
                final_image_url = full_image_url if full_image_url else list_image_url
                
                # Download Image
                # Local path is not required in JSON per previous request, but we still download it
                local_image_path = None
                if final_image_url:
                    ext = os.path.splitext(final_image_url.split('?')[0])[1]
                    if not ext or len(ext) > 5: ext = ".jpg"
                    img_filename = f"{rank}_{sanitize_filename(title)}{ext}"
                    local_image_path = download_image(final_image_url, img_filename)
                
                record = {
                    "rank": rank,
                    "title": title,
                    "source_platform": "New York Times",
                    "source_url": full_url,
                    "content": final_content,
                    "image_url_remote": final_image_url,
                    "local_image_path": local_image_path
                }
                
                all_articles.append(record)
                
                if rank >= args.limit: # Limit to requested number
                    break
        
        print(f"Saving {len(all_articles)} articles to {DATA_FILE}...")
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, indent=4, ensure_ascii=False)
            
        print("Done.")

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    main()
