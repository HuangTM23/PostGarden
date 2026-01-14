import argparse
import json
import re
import time
import os
import sys
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup

# Selenium 导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Constants
BOARD_API_URL = "https://top.baidu.com/api/board?platform=pc&tab=realtime"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

def get_headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://top.baidu.com/board?tab=realtime",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
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
    print("\n百度热搜需要 Selenium 来绕过验证并提取真实新闻源。")
    print("\n📦 安装步骤：")
    print("\n1. 安装 Selenium：")
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

def fetch_top_list(limit: int = 9) -> List[Dict]:
    """从百度热搜API获取榜单"""
    print(f"    [*] 从API获取前{limit}条热搜...")
    try:
        session = get_no_proxy_session()
        resp = session.get(BOARD_API_URL, headers=get_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        cards = data.get("data", {}).get("cards", [])
        if not cards:
            print("    [!] API 响应中未找到cards")
            return []
            
        content = cards[0].get("content", [])
        items = []
        for idx, item in enumerate(content[:limit], 1):
            search_url = item.get("url") or item.get("rawUrl") or ""
            items.append({
                "rank": idx,
                "title": item.get("word") or item.get("query") or "",
                "desc": item.get("desc") or "",
                "search_url": search_url,
                "image_url": item.get("img") or "",
                "hot_score": item.get("hotScore") or 0
            })
        
        print(f"    [✓] API 获取成功，共{len(items)}条")
        return items
    except Exception as e:
        print(f"    [!] API 获取失败: {type(e).__name__}")
        return []

def extract_from_html(html: str) -> Tuple[str, str]:
    """从HTML中提取真实URL和来源"""
    found_url = ""
    found_source = ""

    # 策略1: 从<!--s-data:{...}-->提取
    s_data_pattern = r'<!--s-data:(.*?)-->'
    matches = re.findall(s_data_pattern, html, re.DOTALL)
    
    if matches:
        for match in matches:
            try:
                data = json.loads(match)
                
                # 子策略1: citationList (优先)
                card_data = data.get("cardData", {})
                citation_list = card_data.get("citationList", {})
                
                if citation_list:
                    ref_data = citation_list.get("data", {})
                    ref_list = ref_data.get("referenceList", [])
                    
                    if ref_list and isinstance(ref_list, list) and len(ref_list) > 0:
                        first_ref = ref_list[0]
                        real_url = first_ref.get("url", "")
                        source = first_ref.get("source", "")
                        
                        if isinstance(source, dict):
                            source = source.get("name", "")
                        
                        if real_url:
                            found_url = real_url
                            found_source = str(source)
                            if found_source:
                                break

                # 子策略2: blocksList (备选)
                if not found_url:
                    blocks_list = data.get("cardData", {}).get("blocksList", [])
                    for block in blocks_list:
                        items = block.get("data", {}).get("items", [])
                        for item in items:
                            source_list = item.get("sourceList", [])
                            if source_list and isinstance(source_list, list) and len(source_list) > 0:
                                src_text = source_list[0].get("text", "")
                                if src_text:
                                    link_info = item.get("linkInfo", {})
                                    link = link_info.get("href", "") or link_info.get("url", "")
                                    
                                    found_url = link
                                    found_source = src_text
                                    if found_url and found_source:
                                        break
                        if found_url and found_source:
                            break

            except (json.JSONDecodeError, Exception):
                continue
            
            if found_url and found_source:
                break
    else:
        # 备选: 简单的百家号链接
        bjh_pattern = r'https://baijiahao\.baidu\.com/s\?id=\d+'
        bjh_matches = re.findall(bjh_pattern, html)
        if bjh_matches:
            found_url = bjh_matches[0]
            found_source = "Baidu (Fallback)"

    # 策略2: BeautifulSoup DOM 解析
    if not found_source or found_source == "Baidu (Fallback)":
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # 查找 cosc-source-text
            cosc_source = soup.select_one(".cosc-source-text")
            if cosc_source:
                src_text = cosc_source.get_text(strip=True)
                if src_text:
                    found_source = src_text
                    
                    if not found_url:
                        link_el = soup.select_one("a.title_dIF3B, a.c-blocka")
                        found_url = link_el.get("href", "") if link_el else ""

            # 更多标准选择器
            if not found_source:
                source_el = soup.select_one(".c-showurl, .source_1V_v6, .c-source, .c-gray, .c-color-gray")
                if source_el:
                    src_text = source_el.get_text(strip=True)
                    src_text = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', src_text).strip()
                    src_text = src_text.split(' ')[0]
                    if src_text and len(src_text) < 20:
                        found_source = src_text
                
                if not found_source:
                    first_result = soup.select_one(".result, .c-container, .new-pmd")
                    if first_result:
                        source_el = first_result.select_one(".source-text, .c-color-gray, span.c-gray, .newTimeFactor_vocab, .c-source")
                        if source_el:
                            src_text = source_el.get_text(strip=True)
                            if src_text and len(src_text) < 20 and ":" not in src_text:
                                found_source = src_text
                            
                    if not found_url:
                        link_el = first_result.select_one("a") if first_result else None
                        found_url = link_el.get("href", "") if link_el else ""

        except Exception:
            pass

    return found_url, found_source

def resolve_real_source(search_url: str, driver=None) -> Tuple[str, str]:
    """访问搜索页面提取真实URL和来源（Selenium优先）"""
    if not search_url:
        return "", "百度"

    print(f"        正在解析: {search_url[:60]}...")
    html = ""
    
    # 使用 Selenium
    if driver:
        try:
            driver.get(search_url)
            time.sleep(2)
            html = driver.page_source
            
            # 检测验证码
            if "百度安全验证" in driver.title or "security-verification" in html:
                print(f"        [!] 检测到百度安全验证")
                return search_url, "百度"
                
        except Exception as e:
            print(f"        [!] Selenium 错误: {type(e).__name__}")
            return search_url, "百度"
    else:
        # 备选: requests
        try:
            session = get_no_proxy_session()
            resp = session.get(search_url, headers=get_headers(), timeout=10)
            if "wappass.baidu.com" in resp.url or "security-verification" in resp.text:
                print(f"        [!] 检测到验证码 (requests)")
                return search_url, "百度"
            html = resp.text
        except Exception as e:
            print(f"        [!] Request 错误: {type(e).__name__}")
            return search_url, "百度"

    # 解析 HTML
    real_url, source = extract_from_html(html)
    
    # 如果是百家号且来源未知,尝试进一步解析
    if real_url and "baijiahao.baidu.com" in real_url and source == "Baidu (Fallback)":
        print(f"        [+] 解析百家号来源: {real_url[:50]}...")
        bj_source = resolve_baijiahao_source(real_url, driver=driver)
        if bj_source:
            source = bj_source
    
    final_url = real_url if real_url else search_url
    final_source = source if source else "百度"
    
    return final_url, final_source

def resolve_baijiahao_source(url: str, driver=None) -> str:
    """访问百家号页面提取作者名"""
    try:
        html = ""
        if driver:  # Selenium driver object
            driver.get(url)
            time.sleep(2)
            html = driver.page_source
        else:
            session = get_no_proxy_session()
            resp = session.get(url, headers=get_headers(), timeout=10)
            html = resp.text
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. 作者名选择器
        author = soup.select_one(".author-name, span.author-name, a.author-name, span[class*='author'], a[class*='author']")
        if author:
            name = author.get_text(strip=True)
            if 1 < len(name) < 30:
                return name

        # 2. Meta 标签
        meta = soup.find("meta", attrs={"property": "og:site_name"})
        if meta and meta.get("content"):
            return meta["content"].strip()
            
        meta = soup.find("meta", attrs={"name": "source"})
        if meta and meta.get("content"):
            return meta["content"].strip()

    except Exception as e:
        print(f"        [!] 解析百家号失败: {type(e).__name__}")
        
    return ""

def get_baidu_news(count: int = 9) -> List[dict]:
    """
    抓取百度热搜新闻
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Baidu] 开始抓取热搜新闻...")
    
    # 检查 Selenium
    if not SELENIUM_AVAILABLE:
        install_selenium_hint()
    
    # 1. 获取热榜列表
    items = fetch_top_list(limit=count)
    if not items:
        print("[Baidu] ✗ 未获取到任何新闻")
        return []
    
    print(f"[Baidu] ✓ 获取{len(items)}条候选新闻")
    results = []
    
    # 2. 初始化 Selenium
    driver = init_driver()
    if not driver:
        print("[Baidu] ✗ 浏览器初始化失败")
        return []
    
    try:
        for item in items:
            print(f"\n[Baidu] 处理第{item['rank']}/{len(items)}条:")
            print(f"  标题: {item['title']}")
            
            # 解析真实来源
            real_url, source_name = resolve_real_source(item['search_url'], driver=driver)
            
            print(f"  来源: {source_name}")
            
            # 内容优先使用desc
            content_val = item['desc'] or item['title']
            if len(content_val) > 100:
                content_preview = content_val[:100] + "..."
            else:
                content_preview = content_val
            print(f"  内容: {content_preview}")
            print(f"  链接: {real_url[:60]}...")
            
            results.append({
                "rank": len(results) + 1,
                "title": item['title'],
                "title0": "",
                "content": content_val,
                "index": item['hot_score'],
                "author": "baidu",
                "source_platform": source_name,
                "source_url": real_url,
                "image": item['image_url']
            })
            print(f"  ✓ 第{len(results)}条新闻已保存")
            
            time.sleep(0.5)
    
    finally:
        if driver:
            driver.quit()
            print("    [✓] 浏览器已关闭")
    
    print(f"\n[Baidu] ✓ 抓取完成，共{len(results)}条新闻\n")
    return results

def main(limit: int = 9):
    results = get_baidu_news(count=limit)
    if results:
        print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baidu Hot News Scraper")
    parser.add_argument("--limit", type=int, default=9, help="Number of items to scrape")
    args = parser.parse_args()
    
    main(limit=args.limit)

