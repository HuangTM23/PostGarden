# Renamed from fetch_toutiao_hot.py
import argparse
import json
import time
import random
import requests
import os
import re
import sys
from typing import Tuple, List
from bs4 import BeautifulSoup

# Selenium 导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

API_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Referer": "https://www.toutiao.com/"
}

def get_no_proxy_session():
    """创建一个不使用系统代理的 Session"""
    session = requests.Session()
    session.trust_env = False
    return session

def install_selenium_hint():
    """提示安装 Selenium"""
    print("\n" + "!"*50)
    print("❌ 错误：未检测到 Selenium 库")
    print("!"*50)
    print("\nSelenium 是浏览器自动化库,今日头条需要它来提取真实新闻来源。")
    print("\n📦 安装步骤：")
    print("\n1. 安装 Selenium 相关库：")
    print("   pip install selenium webdriver-manager")
    print("\n2. 安装 Chrome 浏览器（如未安装）")
    print("\n安装完成后，请重新运行本脚本。")
    print("\n" + "!"*50 + "\n")
    sys.exit(1)

def init_driver():
    """初始化 Selenium WebDriver"""
    if not SELENIUM_AVAILABLE:
        install_selenium_hint()
    
    print("    [*] 正在初始化浏览器...")
    try:
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-proxy-server")
        options.add_argument("--disable-images")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f"user-agent={USER_AGENT}")
        options.page_load_strategy = 'eager'
        
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 隐藏 Selenium 特征
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
          "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
        })
        
        driver.set_page_load_timeout(60)
        print("    [✓] 浏览器初始化成功")
        return driver
    except Exception as e:
        print(f"    [!] 浏览器初始化失败: {type(e).__name__}")
        return None

def fetch_hot_list(limit: int = 9) -> List[dict]:
    """从今日头条热榜API获取链接"""
    try:
        print("    [*] 从热榜API获取文章列表...")
        session = get_no_proxy_session()
        response = session.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('data', [])[:limit]
        
        if items:
            print(f"    [✓] 热榜API获取成功，获得 {len(items)} 条链接")
        return items
        
    except Exception as e:
        print(f"    [!] 热榜API获取失败: {type(e).__name__}")
        return []

def resolve_article_data(rank: int, title: str, initial_url: str, driver) -> Tuple[str, str, str, str]:
    """
    核心逻辑：
    1. 访问初始URL
    2. 如果是trending页面,找到具体内容链接
    3. 访问内容页面
    4. 提取真实来源和内容
    """
    source_platform = "今日头条"
    source_url = initial_url
    content = title
    image_url = ""
    
    try:
        # 步骤1 & 2: 解析目标URL
        if "/trending/" in initial_url:
            driver.get(initial_url)
            target_href = None
            link_type = "unknown"
            
            try:
                # 等待内容链接出现
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//a[contains(@href, '/video/') or contains(@href, '/w/') or contains(@href, '/article/')]"))
                )
                links = driver.find_elements(By.XPATH, 
                    "//a[contains(@href, '/video/') or contains(@href, '/w/') or contains(@href, '/article/')]")
                
                for link in links:
                    h = link.get_attribute("href")
                    if not h:
                        continue
                    
                    if "/video/" in h and re.search(r"/video/\d+", h):
                        target_href = h
                        link_type = "video"
                        break
                    if "/w/" in h and re.search(r"/w/\d+", h):
                        target_href = h
                        link_type = "w"
                        break
                    if "/article/" in h and re.search(r"/article/\d+", h):
                        target_href = h
                        link_type = "article"
                        break
            except Exception as e:
                print(f"        未找到内容链接: {type(e).__name__}")
            
            if target_href:
                source_url = target_href
                if source_url.startswith("//"):
                    source_url = "https:" + source_url
                elif source_url.startswith("/"):
                    source_url = "https://www.toutiao.com" + source_url
        else:
            link_type = "article"
        
        # 步骤3: 访问目标内容页面
        if source_url != driver.current_url:
            driver.get(source_url)
        
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 步骤4: 提取数据
        
        # A. 提取来源平台
        platform_el = soup.select_one(".author-info .name, .article-meta .name, .author-name, .user-card-name, .media-info .name")
        
        if platform_el:
            source_platform = platform_el.get_text(strip=True)
        else:
            meta_name = soup.find('meta', attrs={'name': 'author'}) or \
                       soup.find('meta', property='og:site_name')
            if meta_name:
                source_platform = meta_name.get('content', '今日头条')
        
        # B. 提取内容
        if link_type == "video" or "/video/" in source_url:
            # 视频：使用标题
            content = title
        else:
            # 文章/微头条
            article_tag = soup.select_one('article.syl-page-article, article.tt-article-content, article.syl-article-base')
            
            if article_tag:
                content = article_tag.get_text(separator="\n", strip=True)[:200]
            else:
                w_div = soup.select_one(".weitoutiao-html")
                if w_div:
                    content = w_div.get_text(separator="\n", strip=True)[:200]
                else:
                    ps = soup.select(".article-content p, article p")
                    if ps:
                        content = "\n".join([p.get_text(strip=True) for p in ps[:3]])
        
        if not content:
            content = title
        
        # C. 提取图片
        og_img = soup.find('meta', property='og:image')
        if og_img:
            image_url = og_img.get('content', '')
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
        
        print(f"        来源: {source_platform}")
        
    except Exception as e:
        print(f"        [!] 处理失败: {type(e).__name__}")
    
    return source_platform, source_url, content, image_url

def get_toutiao_news(count: int = 9) -> List[dict]:
    """
    抓取今日头条新闻（提取真实新闻来源）
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Toutiao] 开始抓取热搜新闻...")
    
    # 初始化浏览器
    driver = init_driver()
    if not driver:
        print("[Toutiao] ✗ 浏览器初始化失败")
        return []
    
    try:
        # 获取热榜链接
        items = fetch_hot_list(limit=count)
        
        if not items:
            print("[Toutiao] ✗ 未找到任何文章链接")
            return []
        
        print(f"[Toutiao] ✓ 获取{len(items)}条文章链接")
        results = []
        
        for idx, item in enumerate(items, 1):
            if len(results) >= count:
                break
            
            title = item.get("Title", "")
            initial_url = item.get("Url", "")
            hot_index = item.get("HotValue", 0)
            api_image = item.get("Image", {}).get("url", "") if isinstance(item.get("Image"), dict) else ""
            
            print(f"\n[Toutiao] 处理第{len(results)+1}/{count}条:")
            print(f"  标题: {title}")
            print(f"  热度: {hot_index}")
            
            # 解析文章数据
            source_platform, source_url, content, image_url = resolve_article_data(
                len(results) + 1, title, initial_url, driver
            )
            
            if not source_platform:
                print(f"  ✗ 解析失败，跳过此条")
                continue
            
            if len(content) > 100:
                content_preview = content[:100] + "..."
            else:
                content_preview = content
            print(f"  内容: {content_preview}")
            
            # 优先使用页面提取的图片,备选API图片
            final_image = image_url or api_image
            if final_image:
                print(f"  图片: {final_image[:50]}...")
            
            results.append({
                "rank": len(results) + 1,
                "title": title,
                "title0": "",
                "content": content,
                "index": hot_index,
                "author": "toutiao",
                "source_platform": source_platform,  # 真实新闻源
                "source_url": source_url,
                "image": final_image
            })
            print(f"  ✓ 第{len(results)}条新闻已保存")
            
            time.sleep(random.uniform(0.8, 1.5))
        
        print(f"\n[Toutiao] ✓ 抓取完成，共{len(results)}条新闻\n")
        return results
    
    finally:
        if driver:
            driver.quit()
            print("    [✓] 浏览器已关闭")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Toutiao Hot News Scraper")
    parser.add_argument("--limit", type=int, default=9, help="Number of items to scrape")
    args = parser.parse_args()
    
    result = get_toutiao_news(count=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))