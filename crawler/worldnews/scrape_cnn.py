import requests
from bs4 import BeautifulSoup
import json
import os
import re
import argparse

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, default=10, help="Total number of news items to scrape.")
args = parser.parse_args()

# 创建目录
if not os.path.exists('cnn_data/images'):
    os.makedirs('cnn_data/images')

# 请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 目标URL
url = 'https://edition.cnn.com/world'

# 发送请求
try:
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Error fetching the URL: {e}")
    exit()

# 解析HTML
soup = BeautifulSoup(response.content, 'html.parser')

# 定义目标板块 (Priority Order)
target_sections = [
    "Travel",
    "Style",
    "Weather",
    "Architecture around the world",
    "Sports",
    "Tech",
    "Asia",
    "Americas",
    "Europe",
    "Middle East",
]

# Helpers
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:\"<>|]', "", filename)

def absolute_url(url_path):
    if url_path and not url_path.startswith('http'):
        return f"https://edition.cnn.com{url_path}"
    return url_path

def extract_cards_from_section(soup, section_name):
    """Find the container for a section and return all valid article cards."""
    candidates = soup.find_all(['h2', 'span', 'div', 'h3', 'a'])
    target_container = None
    
    for candidate in candidates:
        text = candidate.get_text(strip=True)
        if section_name.lower() in text.lower():
            classes = ' '.join(candidate.get('class', []))
            is_title_class = 'title' in classes or 'header' in classes
            is_heading_tag = candidate.name in ['h2', 'h3']
            
            if is_title_class or is_heading_tag:
                current = candidate
                possible_container = None
                for _ in range(6):
                    current = current.parent
                    if not current: break
                    if current.find(class_=re.compile(r'card|container__item|cards-wrapper')):
                        possible_container = current
                        break
                
                if possible_container:
                    target_container = possible_container
                    if section_name.lower() == text.lower():
                        break
    
    if not target_container:
        return []

    all_cards = target_container.find_all(class_=re.compile(r'card|container__item'))
    valid_cards = [card for card in all_cards if card.find('a')]
    return valid_cards

def process_article_card(article_card, current_rank, processed_urls):
    """Extract info from card."""
    link_tag = article_card.find('a', class_=re.compile(r'container__link'))
    if not link_tag: link_tag = article_card.find('a', href=True)
    if not link_tag: return None, current_rank

    source_url = absolute_url(link_tag.get('href'))
    if not source_url or source_url in processed_urls:
        return None, current_rank

    title_span = article_card.find('span', class_='container__headline-text')
    if not title_span: title_span = article_card.find(class_=re.compile(r'headline-text'))
    title = title_span.get_text(strip=True) if title_span else link_tag.get_text(strip=True)
    
    if not title or "No title found" in title:
        return None, current_rank

    # Image Extraction
    img_tag = article_card.find('img', class_='image__dam-img')
    if not img_tag: img_tag = article_card.find('img')
    
    img_url = ""
    if img_tag:
        if 'src' in img_tag.attrs: img_url = absolute_url(img_tag.get('src'))
        elif 'data-src' in img_tag.attrs: img_url = absolute_url(img_tag.get('data-src'))

    image_path = ""
    if img_url:
        try:
            # Check dup download? No, handled by processed_urls generally
            sanitized_title = sanitize_filename(title)[:50]
            img_ext = os.path.splitext(img_url.split('?')[0])[-1] or '.jpg'
            if len(img_ext) > 5: img_ext = '.jpg'
            
            image_filename = f"{current_rank}_{sanitized_title}{img_ext}"
            image_path = os.path.join('cnn_data', 'images', image_filename)
            
            # Simple check to avoid re-downloading if we somehow re-process (though logic prevents it)
            if not os.path.exists(image_path):
                img_response = requests.get(img_url, headers=headers, timeout=10)
                img_response.raise_for_status()
                with open(image_path, 'wb') as f:
                    f.write(img_response.content)
                print(f"  - [{section_name}] Image saved: {image_filename}")
            else:
                print(f"  - [{section_name}] Image exists: {image_filename}")

        except Exception as e:
            print(f"  - Image download failed: {e}")
            image_path = ""

    data = {
        "rank": current_rank,
        "title": title,
        "source_platform": "CNN",
        "source_url": source_url,
        "content": "",
        "image_path": image_path,
        "local_image_path": image_path
    }
    
    print(f"  - [{section_name}] Scraped: {title[:40]}...")
    return data, current_rank + 1


# --- Main Logic: Round Robin ---
section_queues = {}
processed_urls = set()
scraped_data = []

# 1. Collect all candidates
print("--- Analyzing Sections ---")
for section_name in target_sections:
    cards = extract_cards_from_section(soup, section_name)
    if cards:
        section_queues[section_name] = cards
        print(f"  Found {len(cards)} items in '{section_name}'")
    else:
        print(f"  Warning: Section '{section_name}' empty or not found.")

# 2. Round Robin Selection
print("\n--- Scraping Articles (Round Robin) ---")
rank = 1
active_sections = list(section_queues.keys())

while len(scraped_data) < args.limit and active_sections:
    # Iterate through a copy so we can remove empty sections
    for section_name in list(active_sections):
        if len(scraped_data) >= args.limit:
            break
            
        queue = section_queues[section_name]
        
        # Try to find a valid article in this section's queue
        article_found = False
        while queue:
            card = queue.pop(0) # Get first item
            article_data, new_rank = process_article_card(card, rank, processed_urls)
            
            if article_data:
                scraped_data.append(article_data)
                processed_urls.add(article_data["source_url"])
                rank = new_rank
                article_found = True
                break # Move to next section
        
        if not article_found and not queue:
            # No more items in this section
            active_sections.remove(section_name)

# 保存为JSON文件
with open('cnn_data/data.json', 'w', encoding='utf-8') as f:
    json.dump(scraped_data, f, indent=4, ensure_ascii=False)

print("\nCNN Scraping Completed!")
print(f"Total items: {len(scraped_data)}")