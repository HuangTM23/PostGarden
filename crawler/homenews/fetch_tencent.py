import json
import time
import random
import requests
import sys
import re
import os
from typing import Tuple, List
from bs4 import BeautifulSoup

def get_no_proxy_session():
    """创建一个不使用系统代理的 Session"""
    session = requests.Session()
    session.trust_env = False
    return session

# Selenium 导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://news.qq.com/",
}

# 腾讯新闻标签页ID（早报热点）
TAG_ID = "aEWqxLtdgmQ="

def install_selenium_hint():
    """提示安装 Selenium"""
    print("\n" + "!"*50)
    print("❌ 错误：未检测到 Selenium 库")
    print("!"*50)
    print("\nSelenium 是浏览器自动化库,腾讯新闻需要它来获取动态内容。")
    print("\n📦 安装步骤：")
    print("\n1. 安装 Selenium 相关库：")
    print("   pip install selenium webdriver-manager")
    print("\n2. 确保已安装 Chrome 浏览器")
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
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")
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

def get_links_with_selenium(tag_id: str, count: int, driver) -> List[str]:
    """使用 Selenium 获取动态加载的链接"""
    url = f"https://news.qq.com/tag/{tag_id}"
    print(f"    [*] 使用 Selenium 访问：{url}")
    print(f"    [*] 目标：抓取前 {count} 条链接...")

    links = []
    
    try:
        driver.get(url)
        time.sleep(3)  # 等待初始加载
        
        print(f"    [*] 页面标题: {driver.title}")
        
        # 滚动加载更多内容
        last_height = driver.execute_script("return document.body.scrollHeight")
        retry_count = 0
        
        while len(links) < count and retry_count < 3:
            # 查找所有链接
            from selenium.webdriver.common.by import By
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            
            for link_element in all_links:
                try:
                    href = link_element.get_attribute('href')
                    
                    if not href:
                        continue
                    
                    # 筛选有效的腾讯新闻链接
                    if ('/rain/a/' in href or '/omn/' in href) and 'news.qq.com' in href:
                        # 排除无效链接
                        if not any(x in href for x in ['author', 'video', 'zt', 'live']):
                            # 清理 URL
                            if '#' in href:
                                href = href.split('#')[0]
                            
                            if href not in links:
                                links.append(href)
                                if len(links) >= count:
                                    break
                except:
                    continue
            
            if len(links) >= count:
                break
            
            # 滚动到底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                retry_count += 1
            else:
                retry_count = 0
            last_height = new_height
        
        print(f"    [✓] Selenium 获取成功，找到 {len(links)} 条链接")
        
    except Exception as e:
        print(f"    [!] Selenium 出错: {type(e).__name__}")
    
    return links[:count]

def get_article_details(url: str, max_retries: int = 2) -> Tuple[str, str, str, str]:
    """获取文章详情（带重试机制）"""
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(2)
            
            session = get_no_proxy_session()
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检测是否为视频 URL
            is_video = bool(re.search(r'/[a-zA-Z0-9]*V[a-zA-Z0-9]*', url))
            
            # --- 1. 提取标题 ---
            title = ""
            title_tag = soup.find('h1') or \
                       soup.find('div', class_='video-title') or \
                       soup.find('h2', class_='title')
            
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            if not title or is_video:
                if soup.title:
                    full_title = soup.title.get_text().strip()
                    title = full_title.split('_')[0].strip()
            
            if not title:
                title = "未找到标题"
            
            # --- 2. 提取内容 ---
            content = ""
            content_div = soup.find('div', class_='content-article') or soup.find('div', id='ArticleContent')
            
            if content_div:
                content = content_div.get_text(strip=True)[:200]
            else:
                if is_video:
                    desc = soup.find('div', class_='video-desc') or \
                           soup.find('p', class_='desc') or \
                           soup.find('meta', attrs={'name': 'description'})
                    
                    if desc:
                        if hasattr(desc, 'get_text'):
                            content = desc.get_text(strip=True)
                        elif 'content' in desc.attrs:
                            content = desc['content']
                    
                    if not content or len(content) < 5:
                        content = title
                else:
                    paragraphs = soup.find_all('p')
                    valid_ps = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10]
                    content = "\n".join(valid_ps[:3]) if valid_ps else title
            
            if not content:
                content = title
            
            # --- 3. 提取来源 ---
            source_platform = "腾讯新闻"
            
            author_info = soup.select_one(".author-info .name, .media-info .media-name, .author-name, .media-name")
            if author_info:
                source_platform = author_info.get_text(strip=True)
            
            if source_platform == "腾讯新闻":
                author_meta = soup.find('meta', property='article:author') or \
                             soup.find('meta', attrs={'name': 'author'})
                if author_meta:
                    source_platform = author_meta.get('content', source_platform)
            
            if source_platform == "腾讯新闻":
                media_elem = soup.find('div', class_='author-txt') or \
                            soup.find('div', class_='author-name') or \
                            soup.find('span', class_='media-name')
                if media_elem:
                    source_platform = media_elem.get_text(strip=True)
            
            # --- 4. 提取图片 ---
            cover_image = ""
            
            og_img = soup.find('meta', property='og:image')
            if og_img:
                cover_image = og_img.get('content', '')
            
            if not cover_image or "default" in cover_image or "logo" in cover_image:
                if content_div:
                    img = content_div.find('img')
                    if img:
                        cover_image = img.get('data-src') or img.get('src') or cover_image
            
            if not cover_image and is_video:
                video_tag = soup.find('video')
                if video_tag:
                    cover_image = video_tag.get('poster', '')
            
            if cover_image:
                if cover_image.startswith('//'):
                    cover_image = 'https:' + cover_image
                if "logo_gray" in cover_image or "default" in cover_image:
                    cover_image = ""
            
            return title, content, source_platform, cover_image
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                continue
    
    return "", "", "腾讯新闻", ""

def get_tencent_news(count: int = 9) -> List[dict]:
    """
    抓取腾讯早报新闻（使用 Selenium）
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Tencent] 开始抓取早报新闻...")
    
    # 初始化浏览器
    driver = init_driver()
    if not driver:
        print("[Tencent] ✗ 浏览器初始化失败")
        return []
    
    try:
        # 使用 Selenium 获取链接
        links = get_links_with_selenium(TAG_ID, count, driver)
        
        if not links:
            print("[Tencent] ✗ 未找到任何文章链接")
            return []
        
        print(f"[Tencent] ✓ 获取{len(links)}条文章链接，开始解析内容...")
        results = []
        
        for idx, link in enumerate(links, 1):
            if len(results) >= count:
                break
            
            print(f"\n[Tencent] 处理第{len(results)+1}/{count}条:")
            print(f"  链接: {link}")
            
            title, content, source_platform, cover_image = get_article_details(link)
            
            if not title:
                print(f"  ✗ 标题获取失败，跳过此条")
                continue
            
            print(f"  标题: {title}")
            print(f"  来源: {source_platform}")
            
            if len(content) > 100:
                content_preview = content[:100] + "..."
            else:
                content_preview = content
            print(f"  内容: {content_preview}")
            
            if cover_image:
                print(f"  图片: {cover_image[:50]}...")
            
            results.append({
                "rank": len(results) + 1,
                "title": title,
                "title0": "",
                "content": content,
                "index": 0,
                "author": "tencent",
                "source_platform": source_platform,
                "source_url": link,
                "image": cover_image
            })
            print(f"  ✓ 第{len(results)}条新闻已保存")
            
            time.sleep(random.uniform(0.5, 1.0))
        
        print(f"\n[Tencent] ✓ 抓取完成，共{len(results)}条新闻\n")
        return results
    
    finally:
        if driver:
            driver.quit()
            print("    [✓] 浏览器已关闭")

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    result = get_tencent_news(count)
    print(json.dumps(result, ensure_ascii=False, indent=2))
