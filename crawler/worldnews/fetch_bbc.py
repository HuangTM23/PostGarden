"""
BBC News Scraper
抓取 BBC 国际新闻
"""
import requests
from bs4 import BeautifulSoup
import re
import time
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.bbc.com/news"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_article_details(url, max_retries=3):
    """抓取文章详情（带重试机制）"""
    for attempt in range(max_retries):
        try:
            time.sleep(1 + attempt)  # 逐次增加延迟
            print(f"    [*] 正在访问: {url}")
            if attempt > 0:
                print(f"        (重试 {attempt}/{max_retries-1})")
            
            response = requests.get(url, headers=HEADERS, verify=False, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

            # 提取内容
            article_body = soup.find('article')
            body_text = ""
            if article_body:
                # BBC 使用 data-component="text-block" 来标记文本内容
                text_blocks = article_body.find_all('div', attrs={'data-component': 'text-block'})
                if text_blocks:
                    body_text = "\n\n".join([block.get_text(strip=True) for block in text_blocks])
                else:
                    # 备选方案：标准段落
                    paragraphs = article_body.find_all('p')
                    body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
            # 如果仍未找到内容，尝试 main 标签
            if not body_text:
                main_tag = soup.find('main')
                if main_tag:
                    paragraphs = main_tag.find_all('p')
                    body_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs[:5]])

            # 提取图片 URL
            image_url = ""
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                image_url = meta_img.get('content', '')
            
            # 确保图片 URL 完整
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
                "content": body_text,
                "image_url": image_url
            }

        except requests.exceptions.SSLError as e:
            print(f"    [!] SSL 错误: {type(e).__name__}")
            if attempt < max_retries - 1:
                print(f"        等待 {2 * (attempt + 1)} 秒后重试...")
                time.sleep(2 * (attempt + 1))
                continue
            else:
                print(f"        所有重试失败")
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
    """抓取 BBC 新闻
    Args:
        limit: 抓取数量
    Returns:
        list: 标准格式新闻列表
    """
    print("[BBC] 开始抓取新闻...")
    data_list = []
    
    try:
        response = requests.get(BASE_URL, headers=HEADERS, verify=False, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找"Most Read"部分
        most_read_section = soup.find(attrs={'data-analytics_group_name': 'Most read'})
        
        if not most_read_section:
            print("[BBC] ℹ 未找到'Most read'分析属性，尝试文本搜索...")
            # 备选方案：按文本搜索
            heading = soup.find(string=lambda t: t and "Most read" in t)
            if heading:
                parent = heading.find_parent()
                for _ in range(5):
                    if parent:
                        if parent.find('ol') or parent.find(attrs={'data-testid': re.compile(r'.*card.*')}):
                            most_read_section = parent
                            break
                        parent = parent.find_parent()
        
        if not most_read_section:
            print("[BBC] ✗ 未找到'Most read'部分")
            return []

        # 查找排名跨度
        rank_spans = most_read_section.find_all('span', attrs={'data-testid': 'card-order'})
        
        items = []
        
        if not rank_spans:
            print("[BBC] ℹ 未找到排名标记，直接查找卡片...")
            items = most_read_section.find_all(attrs={'data-testid': re.compile(r'-card$')})
        else:
            # 从排名跨度查找父卡片
            for span in rank_spans:
                card = span.find_parent(attrs={'data-testid': re.compile(r'-card$')})
                if card and card not in items:
                    items.append(card)

        print(f"[BBC] ✓ 找到 {len(items)} 条候选新闻")
        
        for index, item in enumerate(items):
            if len(data_list) >= limit:
                break

            rank = index + 1
            
            # 查找链接
            link_tag = item.find('a', attrs={'data-testid': 'internal-link'})
            if not link_tag:
                link_tag = item.find('a')
            
            if not link_tag:
                continue
                
            href = link_tag.get('href')
            full_url = urljoin(BASE_URL, href)
            
            # 从列表中获取初始标题
            title_tag = item.find('h2', attrs={'data-testid': 'card-headline'})
            list_title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
            
            print(f"\n[BBC] 处理第{rank}/{min(len(items), limit)}条:")
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
                    "author": "BBC",
                    "source_platform": "BBC News",
                    "source_url": full_url,
                    "image": details['image_url']
                }
                
                data_list.append(record)
                print(f"  ✓ 已保存")
            else:
                print(f"  ✗ 获取详情失败，跳过")

        print(f"\n[BBC] ✓ 抓取完成，共 {len(data_list)} 条新闻\n")
        
    except Exception as e:
        print(f"[BBC] ✗ 全局异常: {type(e).__name__}")

    return data_list

if __name__ == "__main__":
    scrape(limit=10)
