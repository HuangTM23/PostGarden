import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import argparse
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://news.sky.com"
OUTPUT_DIR = "sky_news_data"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
DATA_FILE = os.path.join(OUTPUT_DIR, "data.json")

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def setup_directories():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

def sanitize_filename(text):
    """Sanitize text to be safe for filenames."""
    text = re.sub(r'[\\/*?:\"<>|]', "", text)
    return text.replace(" ", "_").lower()[:50]

def download_image(url, filename):
    try:
        if not url:
            return None
        response = requests.get(url, headers=HEADERS, stream=True)
        response.raise_for_status()
        filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filepath
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return None

def fetch_article_details(url):
    try:
        time.sleep(1) # Polite delay
        print(f"  Fetching article: {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract Title
        title_tag = soup.find('h1', class_='sdc-article-header__title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

        # Extract Subtitle (User requested specifically)
        subtitle_tag = soup.find('p', class_='sdc-article-header__sub-title')
        subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

        # Extract Content
        # Primary method: look for sdc-article-body
        article_body = soup.find('div', class_='sdc-article-body')
        body_text = ""
        if article_body:
            paragraphs = article_body.find_all('p')
            body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        else:
            # Fallback for live blogs or other formats
            # ... (keep existing fallback logic if needed, or rely on subtitle)
            # Retaining fallback search for consistency
            divs = soup.find_all('div')
            best_div = None
            max_p = 0
            for d in divs:
                cls = str(d.get('class', '')).lower()
                if 'header' in cls or 'footer' in cls or 'nav' in cls or 'menu' in cls:
                    continue
                p_count = len(d.find_all('p', recursive=False))
                if p_count > max_p:
                    max_p = p_count
                    best_div = d
            
            if best_div and max_p > 2:
                paragraphs = best_div.find_all('p', recursive=False)
                body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
        # Logic: If body text is empty, use subtitle. Otherwise, use body text.
        final_content = body_text
        if not final_content.strip() and subtitle:
            final_content = subtitle

        # Extract Image URL
        image_url = None
        meta_img = soup.find('meta', property='og:image')
        if meta_img:
            image_url = meta_img.get('content')
        
        return {
            "title": title,
            "content": final_content,
            "image_url": image_url
        }

    except Exception as e:
        print(f"  Error fetching article {url}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=10, help="Number of news items to scrape.")
    args = parser.parse_args()

    setup_directories()
    
    print(f"Fetching {BASE_URL}...")
    try:
        response = requests.get(BASE_URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate Most Read section
        # Based on previous analysis:
        # Container: div with class ui-trending or data-testid="trending"
        trending_section = soup.find('div', attrs={'data-testid': 'trending'})
        
        if not trending_section:
            # Fallback to class search
            trending_section = soup.find('div', class_='ui-trending')
            
        if not trending_section:
            print("Could not find 'Most Read' (Trending) section.")
            return

        items = trending_section.find_all('li', class_='ui-trending-item')
        print(f"Found {len(items)} items in Most Read.")
        
        data_list = []
        
        for index, item in enumerate(items):
            if len(data_list) >= args.limit:
                break
            
            rank = index + 1
            link_tag = item.find('a', class_='ui-trending-link')
            
            if not link_tag:
                continue
                
            href = link_tag.get('href')
            full_url = urljoin(BASE_URL, href)
            
            # Initial title from the list (fallback if article fetch fails)
            list_title = link_tag.get_text(strip=True)
            
            print(f"[{rank}] Processing: {list_title}")
            
            # Fetch details
            details = fetch_article_details(full_url)
            
            if details:
                final_title = details['title'] if details['title'] != "No Title Found" else list_title
                
                # Handle Image Download
                local_image_path = None
                if details['image_url']:
                    ext = os.path.splitext(details['image_url'].split('?')[0])[1]
                    if not ext: ext = ".jpg"
                    img_filename = f"{rank}_{sanitize_filename(final_title)}{ext}"
                    local_image_path = download_image(details['image_url'], img_filename)
                
                record = {
                    "rank": rank,
                    "title": final_title,
                    "source_platform": "Sky News",
                    "source_url": full_url,
                    "content": details['content'],
                    "image_url_remote": details['image_url'],
                    "local_image_path": local_image_path
                }
                
                data_list.append(record)
            else:
                print(f"  Skipping {rank} due to fetch error.")

        # Save to JSON
        print(f"Saving data to {DATA_FILE}...")
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)
            
        print("Done.")

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    main()
