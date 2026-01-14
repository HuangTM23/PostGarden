import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.qq.com/",
}

def get_tencent_entertainment_hot(count=9):
    """
    抓取腾讯娱乐热榜
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Tencent Entertainment] 开始抓取娱乐热榜...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    results = []

    try:
        driver.get("https://www.qq.com/")
        time.sleep(5)

        try:
            container = None
            try:
                header = driver.find_element(By.XPATH, "//span[contains(@class, 'qqcom-rankName') and text()='娱乐热榜']")
                container = header.find_element(By.XPATH, "./ancestor::div[contains(@class, 'home-rank-list')]")
            except:
                container = driver.find_element(By.XPATH, "//div[contains(@class, 'rank-list')]")
            
            items = container.find_elements(By.CSS_SELECTOR, "a.rank-item")
            if not items:
                items = container.find_elements(By.TAG_NAME, "a")

            print(f"[Tencent Entertainment] ✓ 找到 {len(items)} 条候选新闻")

            for i, item in enumerate(items):
                if len(results) >= count:
                    break
                
                print(f"\n[Tencent Entertainment] 处理第{i+1}/{min(len(items), count)}条:")
                
                try:
                    link = item.get_attribute("href")
                    if not link:
                        print(f"  ✗ 未找到链接，跳过")
                        continue
                    
                    try:
                        title_el = item.find_element(By.CSS_SELECTOR, ".rank-info")
                        title = title_el.text.strip().split("\n")[0]
                    except:
                        try:
                            title = item.text.strip()
                        except:
                            title = ""

                    if not title or len(title) < 2:
                        print(f"  ✗ 标题无效，跳过")
                        continue

                    print(f"  标题: {title}")
                    print(f"  链接: {link[:60]}..." if len(link) > 60 else f"  链接: {link}")

                    try:
                        img_el = item.find_element(By.CSS_SELECTOR, "img.rank-image")
                        cover_image = img_el.get_attribute("src")
                        if cover_image:
                            print(f"  图片: {cover_image[:50]}...")
                    except:
                        cover_image = ""

                    processed_item = {
                        "rank": len(results) + 1,
                        "title": title,
                        "title0": "",  # 娱乐新闻无英文标题
                        "content": title,  # 使用标题作为内容
                        "index": 0,  # 腾讯娱乐榜无热度指数
                        "author": "tencent",
                        "source_platform": "腾讯娱乐",
                        "source_url": link,
                        "image": cover_image
                    }
                    results.append(processed_item)
                    print(f"  ✓ 第{len(results)}条新闻已保存")

                except Exception as e:
                    print(f"  ✗ 处理失败: {e}")

        except Exception as e:
            print(f"[Tencent Entertainment] ✗ 抓取失败: {e}")

    finally:
        driver.quit()

    print(f"\n[Tencent Entertainment] ✓ 抓取完成，共{len(results)}条新闻\n")
    return results

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    result = get_tencent_entertainment_hot(count)
    print(json.dumps(result, ensure_ascii=False, indent=2))