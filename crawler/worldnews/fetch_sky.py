"""
Sky News Scraper
抓取 Sky News 国际新闻
"""
import requests
from bs4 import BeautifulSoup
import re
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://news.sky.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_article_details(url, max_retries=3):
    """抓取文章详情（带重试机制）"""
    for attempt in range(max_retries):
        try:
            time.sleep(1 + attempt)
            print(f"    [*] 正在访问: {url}")
            if attempt > 0:
                print(f"        (重试 {attempt}/{max_retries-1})")
            
            response = requests.get(url, headers=HEADERS, verify=False, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title_tag = soup.find('h1', class_='sdc-article-header__title')
            title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

            # 提取副标题
            subtitle_tag = soup.find('p', class_='sdc-article-header__sub-title')
            subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

            # 提取内容
            article_body = soup.find('div', class_='sdc-article-body')
            body_text = ""
            if article_body:
                paragraphs = article_body.find_all('p')
                body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs[:3]])
            else:
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
                    body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs[:3]])
            
            final_content = body_text if body_text.strip() else subtitle

            # 提取图片 URL
            image_url = ""
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                image_url = meta_img.get('content', '')
            
            if image_url and not image_url.startswith('http'):
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = BASE_URL + image_url
            
            print(f"    [✓] 成功解析")
            if image_url:
                print(f"        图片: {image_url}")
            else:
                print(f"        图片: (无)")
            
            return {
                "title": title,
                "content": final_content,
                "image_url": image_url
            }

        except requests.exceptions.SSLError:
            print(f"    [!] SSL 错误")
            if attempt < max_retries - 1:
                print(f"        等待 {2 * (attempt + 1)} 秒后重试...")
                time.sleep(2 * (attempt + 1))
                continue
            else:
                return None
        
        except requests.exceptions.Timeout:
            print(f"    [!] 请求超时")
            if attempt < max_retries - 1:
                print(f"        等待 {2 * (attempt + 1)} 秒后重试...")
                time.sleep(2 * (attempt + 1))
                continue
            else:
                return None
        
        except requests.exceptions.ConnectionError as e:
            print(f"    [!] 连接错误: {type(e).__name__}")
            if attempt < max_retries - 1:
                print(f"        等待 {2 * (attempt + 1)} 秒后重试...")
                time.sleep(2 * (attempt + 1))
                continue
            else:
                return None
        
        except Exception as e:
            print(f"    [!] 解析失败: {type(e).__name__}")
            if attempt < max_retries - 1:
                continue
            else:
                return None
    
    return None

def scrape(limit=10):
    """抓取 Sky News"""
    print("[Sky News] 开始抓取新闻...")
    data_list = []
    
    try:
        print("[Sky News] ℹ 正在加载页面...")
        response = requests.get(BASE_URL, headers=HEADERS, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找"Most Read"部分
        # 方法1: 使用 data-testid 属性
        trending_section = soup.find('div', attrs={'data-testid': 'trending'})
        
        # 方法2: 备选 class 查找
        if not trending_section:
            trending_section = soup.find('div', class_='ui-trending')
        
        # 方法3: 按文本搜索
        if not trending_section:
            heading = soup.find(string=lambda t: t and "Most read" in str(t).lower())
            if heading:
                parent = heading.find_parent()
                for _ in range(5):
                    if parent:
                        if parent.find('div', class_=re.compile(r'trending')):
                            trending_section = parent
                            break
                        parent = parent.find_parent()
        
        if not trending_section:
            print("[Sky News] ✗ 未找到'Most Read'部分")
            return []

        # 查找列表项
        items = trending_section.find_all('li', class_='ui-trending-item')
        
        if not items:
            print("[Sky News] ✗ 未找到趋势项")
            return []
        
        print(f"[Sky News] ✓ 找到 {len(items)} 条候选新闻")
        
        for index, item in enumerate(items):
            if len(data_list) >= limit:
                break
            
            rank = index + 1
            
            # 查找链接
            link_tag = item.find('a', class_='ui-trending-link')
            if not link_tag:
                link_tag = item.find('a', href=True)
            
            if not link_tag:
                continue
                
            href = link_tag.get('href', '')
            if not href:
                continue
            
            full_url = urljoin(BASE_URL, href)
            
            # 从列表中获取初始标题
            list_title = link_tag.get_text(strip=True)
            
            print(f"\n[Sky News] 处理第{rank}/{min(len(items), limit)}条:")
            print(f"  标题: {list_title[:70]}")
            print(f"  链接: {full_url}")  # 完整 URL
            
            # 获取详情
            details = fetch_article_details(full_url)
            
            if details:
                final_title = details['title'] if details['title'] != "No Title Found" else list_title
                
                record = {
                    "rank": rank,
                    "title": final_title,
                    "title0": final_title,
                    "content": details['content'],
                    "index": len(items) - index,
                    "author": "Sky News",
                    "source_platform": "Sky News",
                    "source_url": full_url,
                    "image": details['image_url']
                }
                
                data_list.append(record)
                print(f"  ✓ 已保存")
            else:
                print(f"  ✗ 获取详情失败，跳过")

        print(f"\n[Sky News] ✓ 抓取完成，共 {len(data_list)} 条新闻\n")
        
    except Exception as e:
        print(f"[Sky News] ✗ 全局异常: {type(e).__name__}")

    return data_list
