"""
New York Times News Scraper
抓取纽约时报国际新闻
"""
import requests
from bs4 import BeautifulSoup
import re
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.nytimes.com"
WORLD_URL = "https://www.nytimes.com/section/world"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Cache-Control': 'max-age=0',
}

def fetch_article_content_full(url, max_retries=3):
    """获取文章完整内容和图片（带重试机制）"""
    for attempt in range(max_retries):
        try:
            time.sleep(2 + attempt)
            print(f"    [*] 正在获取: {url}")
            if attempt > 0:
                print(f"        (重试 {attempt}/{max_retries-1})")
            
            response = requests.get(url, headers=HEADERS, verify=False, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取内容
            article_body = soup.find('section', attrs={'name': 'articleBody'})
            content = ""
            if article_body:
                paragraphs = article_body.find_all('p')
                content = "\n\n".join([p.get_text(strip=True) for p in paragraphs[:3]])
            else:
                paragraphs = soup.find_all('p', class_=re.compile(r'css-axufdj|css-158dogj|css-at9mc1'))
                if paragraphs:
                    content = "\n\n".join([p.get_text(strip=True) for p in paragraphs[:3]])
            
            # 提取图片
            image_url = ""
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                image_url = meta_img.get('content', '')
            
            if image_url and not image_url.startswith('http'):
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = BASE_URL + image_url
            
            print(f"    [✓] 内容获取成功")
            if image_url:
                print(f"        图片: {image_url}")
            return content, image_url
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"    [!] 访问被拒 (403)")
                return None, None
            else:
                print(f"    [!] HTTP 错误: {e.response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    return None, None
        
        except requests.exceptions.SSLError:
            print(f"    [!] SSL 错误")
            if attempt < max_retries - 1:
                print(f"        等待 {2 * (attempt + 1)} 秒后重试...")
                time.sleep(2 * (attempt + 1))
                continue
            else:
                return None, None
        
        except requests.exceptions.Timeout:
            print(f"    [!] 请求超时")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            else:
                return None, None
        
        except Exception as e:
            print(f"    [!] 获取失败: {type(e).__name__}")
            if attempt < max_retries - 1:
                continue
            else:
                return None, None
    
    return None, None

def scrape(limit=10):
    """抓取 NYTimes 新闻"""
    print("[NYTimes] 开始抓取新闻...")
    
    try:
        print("[NYTimes] ℹ 正在加载页面...")
        response = requests.get(WORLD_URL, headers=HEADERS, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[NYTimes] ✗ 页面加载失败: {type(e).__name__}")
        return []

    # 收集所有文章候选
    all_articles = []
    candidates = soup.find_all('li')
    processed_urls = set()
    
    print(f"[NYTimes] 分析页面中...")
    
    rank = 0
    for item in candidates:
        # 查找标题和链接
        headline_tag = item.find(['h2', 'h3'])
        link_tag = item.find('a', href=True)
        
        if not headline_tag or not link_tag:
            continue
        
        href = link_tag.get('href', '')
        if not href or href.startswith('#') or 'crosswords' in href or 'video' in href:
            continue
        
        # 转换为完整 URL
        full_url = urljoin(BASE_URL, href)
        
        # 检查重复
        if full_url in processed_urls:
            continue
        
        processed_urls.add(full_url)
        rank += 1
        
        # 提取标题
        title = headline_tag.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        
        # 提取摘要（作为备选内容）
        summary_tag = item.find('p')
        summary = summary_tag.get_text(strip=True) if summary_tag else ""
        
        # 提取列表中的图片
        img_tag = item.find('img')
        list_image_url = img_tag.get('src', '') if img_tag else ""
        
        print(f"  [{rank}] {title[:70]}")
        print(f"        链接: {full_url}")  # 完整 URL
        
        # 尝试获取完整内容和图片
        full_content, full_image_url = fetch_article_content_full(full_url)
        
        # 使用完整内容，如果失败则使用摘要
        final_content = full_content if full_content else summary
        if not final_content:
            final_content = title
        
        # 优先使用文章页面的图片，备选列表中的图片
        final_image_url = full_image_url if full_image_url else list_image_url
        
        # 确保 URL 完整
        if final_image_url and not final_image_url.startswith('http'):
            if final_image_url.startswith('//'):
                final_image_url = 'https:' + final_image_url
            elif final_image_url.startswith('/'):
                final_image_url = BASE_URL + final_image_url
        
        record = {
            "rank": rank,
            "title": title,
            "title0": title,
            "content": final_content,
            "index": len(candidates) - rank,
            "author": "NYTimes",
            "source_platform": "New York Times",
            "source_url": full_url,
            "image": final_image_url
        }
        
        all_articles.append(record)
        
        if rank >= limit:
            break
    
    print(f"\n[NYTimes] ✓ 抓取完成，共 {len(all_articles)} 条新闻\n")
    return all_articles

if __name__ == "__main__":
    scrape(limit=10)
