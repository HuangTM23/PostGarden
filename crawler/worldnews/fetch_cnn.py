"""
CNN News Scraper
抓取 CNN 国际新闻
"""
import requests
from bs4 import BeautifulSoup
import re
import urllib3
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

BASE_URL = 'https://edition.cnn.com'
WORLD_URL = f'{BASE_URL}/world'

def sanitize_filename(filename):
    """文件名安全处理"""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def absolute_url(url_path):
    """转换为绝对 URL"""
    if url_path and not url_path.startswith('http'):
        return f"{BASE_URL}{url_path}"
    return url_path

def extract_cards_from_section(soup, section_name):
    """从指定分类查找所有文章卡片"""
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
                    if not current:
                        break
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

def process_article_card(article_card, current_rank, processed_urls, section_name):
    """提取卡片中的文章信息"""
    # 查找链接
    link_tag = article_card.find('a', class_=re.compile(r'container__link'))
    if not link_tag:
        link_tag = article_card.find('a', href=True)
    if not link_tag:
        return None, current_rank

    source_url = absolute_url(link_tag.get('href'))
    if not source_url or source_url in processed_urls:
        return None, current_rank

    # 提取标题
    title_span = article_card.find('span', class_='container__headline-text')
    if not title_span:
        title_span = article_card.find(class_=re.compile(r'headline-text'))
    title = title_span.get_text(strip=True) if title_span else link_tag.get_text(strip=True)
    
    if not title or len(title) < 5:
        return None, current_rank

    # 提取图片
    img_tag = article_card.find('img', class_='image__dam-img')
    if not img_tag:
        img_tag = article_card.find('img')
    
    img_url = ""
    if img_tag:
        if 'src' in img_tag.attrs:
            img_url = absolute_url(img_tag.get('src'))
        elif 'data-src' in img_tag.attrs:
            img_url = absolute_url(img_tag.get('data-src'))

    # 如果列表页没有图片，进入详情页获取
    if not img_url:
        try:
            print(f"      ℹ 列表页无图，尝试访问详情页: {source_url[:60]}...")
            resp = requests.get(source_url, headers=HEADERS, verify=False, timeout=10)
            if resp.status_code == 200:
                detail_soup = BeautifulSoup(resp.content, 'html.parser')
                og_img = detail_soup.find('meta', property='og:image')
                if og_img:
                    img_url = og_img.get('content', '')
                    print(f"      ✓ 详情页获取图片成功")
        except Exception as e:
            print(f"      [!] 详情页图片获取失败: {type(e).__name__}")

    # 确保图片 URL 完整
    if img_url and not img_url.startswith('http'):
        if img_url.startswith('//'):
            img_url = 'https:' + img_url

    data = {
        "rank": current_rank,
        "title": title,
        "title0": title,
        "content": "",
        "index": current_rank,
        "author": "CNN",
        "source_platform": "CNN",
        "source_url": source_url,
        "image": img_url
    }
    
    print(f"    [{section_name}] ✓ {title[:70]}")
    if img_url:
        print(f"                     图片: {img_url}")
    return data, current_rank + 1

def scrape(limit=10):
    """
    抓取 CNN 新闻 (使用轮询策略)
    Args:
        limit: 抓取数量
    Returns:
        list: 标准格式新闻列表
    """
    print("[CNN] 开始抓取新闻...")
    
    # 定义目标分类（优先级顺序）
    target_sections = [
        "World",
        "Travel",
        "Style",
        "Weather",
        "Architecture",
        "Sports",
        "Tech",
        "Asia",
        "Americas",
        "Europe",
        "Middle East",
    ]
    
    try:
        print("[CNN] ℹ 正在加载页面...")
        response = requests.get(WORLD_URL, headers=HEADERS, verify=False, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"[CNN] ✗ 页面加载失败: {type(e).__name__}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 第一步：收集所有分类的候选文章
    print("[CNN] 分析分类中...")
    section_queues = {}
    processed_urls = set()
    
    for section_name in target_sections:
        cards = extract_cards_from_section(soup, section_name)
        if cards:
            section_queues[section_name] = cards
            print(f"  ✓ '{section_name}': 找到 {len(cards)} 条候选")
        else:
            print(f"  ✗ '{section_name}': 未找到")

    if not section_queues:
        print("[CNN] ✗ 未找到任何分类")
        return []

    # 第二步：轮询选择（round-robin）
    print(f"\n[CNN] 抓取中 (目标: {limit} 条)...")
    scraped_data = []
    rank = 1
    active_sections = list(section_queues.keys())

    while len(scraped_data) < limit and active_sections:
        for section_name in list(active_sections):
            if len(scraped_data) >= limit:
                break
            
            queue = section_queues[section_name]
            article_found = False
            
            while queue:
                card = queue.pop(0)
                article_data, new_rank = process_article_card(card, rank, processed_urls, section_name)
                
                if article_data:
                    scraped_data.append(article_data)
                    processed_urls.add(article_data["source_url"])
                    rank = new_rank
                    article_found = True
                    break
            
            if not article_found and not queue:
                # 该分类已无可用文章
                active_sections.remove(section_name)

    print(f"\n[CNN] ✓ 抓取完成，共 {len(scraped_data)} 条新闻\n")
    return scraped_data
