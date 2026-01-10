import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import argparse
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://www.bbc.com/news"
OUTPUT_DIR = "bbc_news_data"
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
    text = re.sub(r'[\\/*?:"<>|]', "", text)
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
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

        # Extract Subtitle (No specific subtitle selector identified for BBC, usually part of body or header)
        # We'll leave it empty or try to find a lead paragraph if needed.
        subtitle = "" 

        # Extract Content
        article_body = soup.find('article')
        body_text = ""
        if article_body:
            # BBC uses data-component="text-block" for text content
            text_blocks = article_body.find_all('div', attrs={'data-component': 'text-block'})
            if text_blocks:
                body_text = "\n\n".join([block.get_text(strip=True) for block in text_blocks])
            else:
                # Fallback to standard paragraphs
                paragraphs = article_body.find_all('p')
                body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
        # Fallback if no article tag found (e.g. video pages or different layouts)
        if not body_text:
             paragraphs = soup.find_all('p')
             # Simple heuristic: ignore nav/footer, take substantial paragraphs
             # This is risky but a fallback.
             # A better fallback might be main tag.
             main_tag = soup.find('main')
             if main_tag:
                 paragraphs = main_tag.find_all('p')
                 body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs])

        final_content = body_text

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
        # Strategy: Find the section with data-analytics_group_name="Most read"
        most_read_section = soup.find(attrs={'data-analytics_group_name': 'Most read'})
        
        if not most_read_section:
            print("Could not find 'Most Read' section by analytics attribute. Trying text search...")
            # Fallback: search for heading "Most read"
            heading = soup.find(string=lambda t: t and "Most read" in t)
            if heading:
                # Go up parents until we find a container that has list items
                parent = heading.find_parent()
                # Use a reasonable depth
                for _ in range(5):
                    if parent:
                        if parent.find('ol') or parent.find(attrs={'data-testid': re.compile(r'.*card.*')}):
                            most_read_section = parent
                            break
                        parent = parent.find_parent()
        
        if not most_read_section:
            print("Could not find 'Most Read' section.")
            return

        # BBC seems to use cards. Let's find all cards within this section.
        # Based on inspection: data-testid="cambridge-card" or generally ending in -card
        # items = most_read_section.find_all(attrs={'data-testid': re.compile(r'-card$')})
        
        # Better yet, look for the rank '1', '2', etc. inside the items.
        # The rank is in <span data-testid="card-order">
        # So we can find all such spans and get their parent cards. 
        
        rank_spans = most_read_section.find_all('span', attrs={'data-testid': 'card-order'})
        
        data_list = []
        
        # If no explicit rank spans (maybe layout changed), try finding cards
        if not rank_spans:
             print("No card-order spans found. Falling back to finding cards directly.")
             items = most_read_section.find_all(attrs={'data-testid': re.compile(r'-card$')})
        else:
             # Sort spans by text just in case, though they should be ordered
             # Map span to its closest card container
             items = []
             for span in rank_spans:
                 card = span.find_parent(attrs={'data-testid': re.compile(r'-card$')})
                 if card and card not in items:
                     items.append(card)

        print(f"Found {len(items)} items in Most Read.")
        
        for index, item in enumerate(items):
            if len(data_list) >= args.limit:
                break

            rank = index + 1
            
            # Find link
            link_tag = item.find('a', attrs={'data-testid': 'internal-link'})
            if not link_tag:
                link_tag = item.find('a') # Fallback
            
            if not link_tag:
                continue
                
            href = link_tag.get('href')
            full_url = urljoin(BASE_URL, href)
            
            # Initial title from the list
            title_tag = item.find('h2', attrs={'data-testid': 'card-headline'})
            list_title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
            
            print(f"[{rank}] Processing: {list_title}")
            
            # Fetch details
            details = fetch_article_details(full_url)
            
            if details:
                final_title = details['title'] if details['title'] != "No Title Found" else list_title
                
                # Handle Image Download
                local_image_path = None
                if details['image_url']:
                    # BBC images might not have extension in URL sometimes, or complex URLs
                    # Remove query params
                    clean_url = details['image_url'].split('?')[0]
                    ext = os.path.splitext(clean_url)[1]
                    if not ext or len(ext) > 5: ext = ".jpg"
                    
                    img_filename = f"{rank}_{sanitize_filename(final_title)}{ext}"
                    local_image_path = download_image(details['image_url'], img_filename)
                
                record = {
                    "rank": rank,
                    "title": final_title,
                    "source_platform": "BBC News",
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
