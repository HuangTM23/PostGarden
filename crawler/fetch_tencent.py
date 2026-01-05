import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
import sys
import re

# 配置
TAG_CONFIG = {
    "morning": {
        "id": "aEWqxLtdgmQ=",
        "name": "早报",
        "json_prefix": "tencent_morning_news",
        "img_dir": "images/morning"
    },
    "evening": {
        "id": "bEeox7NdhmM=",
        "name": "晚报",
        "json_prefix": "tencent_evening_news",
        "img_dir": "images/evening"
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://news.qq.com/",
}

def install_selenium_hint():
    print("\n" + "!"*50)
    print("错误：未检测到 Selenium 库。")
    print("为了实现全自动化抓取（绕过腾讯的动态加密列表），必须使用浏览器自动化技术。")
    print("请在终端运行以下命令安装依赖：")
    print("\n    pip install selenium webdriver-manager\n")
    print("安装完成后，请重新运行本脚本。")
    print("!"*50 + "\n")
    sys.exit(1)

def get_links_auto(tag_id, count):
    """使用 Selenium 自动控制浏览器获取动态列表"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        install_selenium_hint()

    url = f"https://news.qq.com/tag/{tag_id}"
    print(f"正在启动后台浏览器，访问：{url}")
    print(f"目标：抓取前 {count} 条链接...")

    links = []
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(3) # 等待初始加载
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        retry_count = 0
        
        while len(links) < count and retry_count < 3:
            elements = driver.find_elements(By.CSS_SELECTOR, "a")
            current_found = 0
            for el in elements:
                try:
                    href = el.get_attribute("href")
                    # 腾讯新闻文章通常包含 /rain/a/ 或 /omn/
                    # 严格过滤掉 author(作者页), video(视频页), zt(专题页)
                    if href and ("/rain/a/" in href or "/omn/" in href) \
                       and "author" not in href \
                       and "video" not in href \
                       and "zt" not in href \
                       and href not in links:
                        links.append(href)
                        current_found += 1
                        print(f"[{len(links)}] 发现: {href}")
                        if len(links) >= count:
                            break
                except:
                    continue
            
            if len(links) >= count:
                break
                
            # 滚动加载
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                retry_count += 1
                print("页面未刷新，尝试继续等待...")
            else:
                retry_count = 0
            last_height = new_height

    except Exception as e:
        print(f"浏览器自动化出错: {e}")
    finally:
        if driver:
            driver.quit()
            
    return links[:count]

def download_image(url, folder, index):
    if not url: return "无图片"
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    try:
        # Filter out common logo/icon URLs strings
        if "icon" in url or "logo" in url:
            return None

        response = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, stream=True, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            ext = '.webp' if 'webp' in content_type else '.png' if 'png' in content_type else '.jpg'
            filename = f"{folder}/{index}{ext}"
            
            # Write to file
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024): f.write(chunk)
            
            # Check file size (Filter out small icons < 10KB)
            file_size = os.path.getsize(filename)
            if file_size < 10240: # 10KB
                os.remove(filename)
                return None # Signal to try next image
                
            return filename
    except: pass
    return "下载失败"

def get_article_details(url, index, config):
    print(f"[{index}] 解析: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if it's a video URL (Contains 'V' in the ID, e.g., 2025...V...)
        # Regex to check for the V pattern in the last segment of URL
        is_video = False
        if re.search(r'/[a-zA-Z0-9]*V[a-zA-Z0-9]*', url):
            is_video = True

        # --- 1. Title Extraction ---
        title = ""
        # Strategy A: Standard Tags
        title_tag = soup.find('h1') or \
                    soup.find('div', class_='video-title') or \
                    soup.find('h2', class_='title')
        
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Strategy B: <title> Tag (Fallback & Video Preference)
        # If title is missing OR it's a video (often <title> is cleaner than div.video-title), use <title>
        if not title or is_video:
            if soup.title:
                full_title = soup.title.get_text().strip()
                # Clean suffixes like "_腾讯新闻", "_腾讯网"
                title = full_title.split('_')[0].strip()

        if not title: title = "未找到标题"

        # --- 2. Content Extraction ---
        content = ""
        # Standard Article Content
        content_div = soup.find('div', class_='content-article') or soup.find('div', id='ArticleContent')
        
        if content_div:
            content = content_div.get_text(strip=True)
        else:
            # Video Page Logic
            if is_video:
                # Try finding description first
                desc = soup.find('div', class_='video-desc') or \
                       soup.find('p', class_='desc') or \
                       soup.find('meta', attrs={'name': 'description'})
                
                if desc:
                    if hasattr(desc, 'get_text'):
                        content = desc.get_text(strip=True)
                    elif 'content' in desc.attrs:
                        content = desc['content']
                
                # USER REQUIREMENT: For videos, if no detailed content, use Title
                if not content or len(content) < 5:
                    content = title
            else:
                # Text Page Fallback
                paragraphs = soup.find_all('p')
                valid_ps = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10]
                content = "\n".join(valid_ps)

        if not content: content = title # Ultimate fallback

        # --- 3. Source Platform ---
        source_platform = "未知平台"
        media_elem = soup.find('a', class_='media-name') or \
                     soup.find('span', class_='media-name') or \
                     soup.find('div', class_='author-txt') or \
                     soup.find('div', class_='author-name')
        
        if media_elem:
            source_platform = media_elem.get_text(strip=True)
        else:
            # Fallback for some article types
            meta_site = soup.find('meta', property='og:site_name') or \
                        soup.find('meta', name='author')
            if meta_site:
                source_platform = meta_site.get('content', '未知平台')
            else:
                author_meta = soup.find('meta', property='article:author')
                if author_meta:
                    source_platform = author_meta['content']

        # --- 4. Image Extraction ---
        cover_image_url = ""
        # Strategy A: OG Image
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            cover_image_url = og_img['content']
        
        # Strategy B: First image in content
        if not cover_image_url or "default" in cover_image_url:
            if content_div:
                img = content_div.find('img')
                if img:
                    cover_image_url = img.get('data-src') or img.get('src')
        
        # Strategy C: Video Poster (if video)
        if not cover_image_url and is_video:
            video_tag = soup.find('video')
            if video_tag:
                cover_image_url = video_tag.get('poster')

        local_image_path = "无图片"
        if cover_image_url and cover_image_url.startswith('http'):
            res = download_image(cover_image_url, config['img_dir'], index)
            if res and res != "下载失败":
                local_image_path = res

        return {
            "序号": index,
            "标题": title,
            "内容": content,
            "源平台": source_platform,
            "源平台的链接": url,
            "封面图片": local_image_path
        }
    except Exception as e:
        print(f"解析失败: {e}")
        return None

def main(report_type="morning", limit=10, out_dir=None):
    if out_dir is None:
        out_dir = os.getenv('TENCENT_OUT_DIR', 'tencent')
    
    print("=== 腾讯新闻自动化抓取工具 (早报/晚报) ===")
    
    # 1. 选择类型 (report_type maps to news_type logic)
    news_type = report_type
        
    if news_type not in TAG_CONFIG:
        print(f"Unknown report type: {news_type}, defaulting to morning")
        news_type = "morning"

    cfg = TAG_CONFIG[news_type]
    print(f"\n>>> 已选择：【{cfg['name']}】")
    
    # 2. 设置数量
    target_count = limit
        
    # 3. 全自动获取链接
    links = get_links_auto(cfg['id'], target_count)
    
    if not links:
        print("未获取到任何链接，程序退出。")
        return []

    print(f"\n成功获取 {len(links)} 条链接，开始解析内容...\n")
    
    # 调整图片保存目录到指定的 out_dir 下
    cfg['img_dir'] = os.path.join(out_dir, "images", news_type)

    all_data = []
    for i, link in enumerate(links, 1):
        data = get_article_details(link, i, cfg)
        if data:
            # Map Chinese keys to English keys for pipeline compatibility
            record = {
                "rank": data["序号"],
                "title": data["标题"],
                "content": data["内容"],
                "source_platform": data["源平台"], # FIXED: Use real source instead of hardcoded 'Tencent'
                "source_url": data["源平台的链接"],
                "image": data["封面图片"]
            }
            all_data.append(record)
        time.sleep(random.uniform(0.5, 1.0))
        
    # 4. 保存结果 (Optional now, pipeline handles aggregation)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    filename = os.path.join(out_dir, f"{cfg['json_prefix']}_{len(all_data)}pcs.json")
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n任务完成！")
    print(f"数据文件: {filename}")
    print(f"图片目录: {cfg['img_dir']}/")
    
    return all_data

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tencent News Scraper")
    parser.add_argument("--limit", type=int, default=10, help="Number of news items to fetch")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--type", type=str, default="morning", choices=["morning", "evening"], help="Report type")
    args = parser.parse_args()
    
    main(limit=args.limit, out_dir=args.out_dir, report_type=args.type)
