#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合娱乐新闻聚合器
包含平台抓取、AI筛选和内容聚合功能
"""

import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta
import re
import requests
from PIL import Image
import sys
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import HistoryManager (assuming it's in the parent directory path, which pipeline.py sets up)
# But since aggregator.py might be run standalone or from pipeline, we need to handle import path.
try:
    from history_manager import HistoryManager
except ImportError:
    # If run directly from entertainment folder
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from history_manager import HistoryManager
    except ImportError:
        HistoryManager = None

def sanitize_filename(name, max_length=20):
    """清理文件名，移除非法字符"""
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', '_', name).strip()
    return name[:max_length]

def resize_image(input_path, output_path, max_size=(800, 600)):
    """调整图片大小以节省空间"""
    try:
        with Image.open(input_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, quality=85, optimize=True)
    except Exception as e:
        print(f"调整图片大小失败 {input_path}: {e}")
        shutil.copy2(input_path, output_path)

# 腾讯娱乐抓取函数
def download_image(url, folder, index, headers):
    if not url: return "无图片"
    if not os.path.exists(folder):
        os.makedirs(folder)

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            ext = '.webp' if 'webp' in content_type else '.png' if 'png' in content_type else '.jpg'
            filename = f"{folder}/{index}{ext}"
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024): f.write(chunk)
            return filename
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return "下载失败"

def get_tencent_entertainment_hot():
    print("=== 腾讯网娱乐热榜抓取工具 ===")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.qq.com/",
    }

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={headers['User-Agent']}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    results = []

    try:
        print("正在访问 https://www.qq.com/ ...")
        driver.get("https://www.qq.com/")
        time.sleep(5)

        try:
            header = driver.find_element(By.XPATH, "//span[contains(@class, 'qqcom-rankName') and text()='娱乐热榜']")
            container = header.find_element(By.XPATH, "./ancestor::div[contains(@class, 'home-rank-list')]")
            items = container.find_elements(By.CSS_SELECTOR, "a.rank-item")
            print(f"找到 {len(items)} 条热榜内容。")

            for i, item in enumerate(items, 1):
                if i > 9: break 
                try:
                    link = item.get_attribute("href")
                    try:
                        title_el = item.find_element(By.CSS_SELECTOR, ".rank-info")
                        title = title_el.text.strip().split("\n")[0]
                    except:
                        title = "未知标题"

                    try:
                        img_el = item.find_element(By.CSS_SELECTOR, "img.rank-image")
                        img_url = img_el.get_attribute("src")
                    except:
                        img_url = ""

                    print(f"[{i}] {title}")
                    local_img = download_image(img_url, "images/ent_hot", i, headers)

                    results.append({
                        "序号": i,
                        "标题": title,
                        "链接": link,
                        "图片": local_img
                    })

                except Exception as e:
                    print(f"解析第 {i} 条时出错: {e}")

        except Exception as e:
            print(f"未找到娱乐热榜模块: {e}")

    finally:
        driver.quit()

    if results:
        with open('tencent_ent_hot.json', "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
    else:
        print("\n抓取失败，未获取到数据。")

# 抖音抓取函数
def fetch_douyin_rank_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.douyin.com/hot',
        'Cookie': 's_v_web_id=verify_ley4g474_KV2s6Q1F_8jF8_4r6G_8jF8_8jF88jF88jF8;'
    }
    url = 'https://www.douyin.com/aweme/v1/web/hot/search/list/'
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def process_douyin_rank_data(raw_data):
    if not raw_data or not raw_data.get('data'): return

    items = raw_data.get('data', {}).get('word_list', [])[:9] 
    processed_list = []
    for index, item in enumerate(items):
        rank = index + 1
        title = item.get('word', '')
        author = "Douyin Hot Topic"
        view_count = item.get('hot_value', 0)
        comment_count = 0
        cover_image = ""
        if item.get('word_cover') and item.get('word_cover').get('url_list'):
            cover_image = item.get('word_cover').get('url_list')[0]

        sentence_id = item.get('sentence_id', '')
        video_link = f"https://www.douyin.com/hot/{sentence_id}" if sentence_id else f"https://www.douyin.com/search/{title}"

        processed_item = {
            "rank": rank,
            "title": title,
            "author": author,
            "view_count": view_count,
            "comment_count": comment_count,
            "cover_image": cover_image,
            "video_link": video_link
        }
        processed_list.append(processed_item)

    json_output_file = 'douyin_rank.json'
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, ensure_ascii=False, indent=2)

def get_douyin_rank():
    data = fetch_douyin_rank_data()
    process_douyin_rank_data(data)

# 哔哩哔哩抓取函数
def fetch_bilibili_rank_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com/v/popular/rank/all'
    }
    url = 'https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def process_bilibili_rank_data(raw_data):
    if not raw_data or raw_data.get('code') != 0: return

    items = raw_data.get('data', {}).get('list', [])[:9]
    processed_list = []
    for index, item in enumerate(items):
        rank = index + 1
        title = item.get('title', '')
        author = item.get('owner', {}).get('name', '')
        view_count = item.get('stat', {}).get('view', 0)
        comment_count = item.get('stat', {}).get('reply', 0)
        cover_image = item.get('pic', '')
        bvid = item.get('bvid', '')
        video_link = f"https://www.bilibili.com/video/{bvid}" if bvid else ''

        processed_item = {
            "rank": rank,
            "title": title,
            "author": author,
            "view_count": view_count,
            "comment_count": comment_count,
            "cover_image": cover_image,
            "video_link": video_link
        }
        processed_list.append(processed_item)

    json_output_file = 'bilibili_rank.json'
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, ensure_ascii=False, indent=2)

def get_bilibili_rank():
    data = fetch_bilibili_rank_data()
    process_bilibili_rank_data(data)

def run_tencent_scraper():
    get_tencent_entertainment_hot()

def run_douyin_scraper():
    get_douyin_rank()

def run_bilibili_scraper():
    get_bilibili_rank()

def filter_content_by_rules(all_news):
    print("根据规则筛选内容...")
    tencent_news = [item for item in all_news if item.get('source_platform') == '腾讯娱乐']
    douyin_news = [item for item in all_news if item.get('source_platform') == '抖音']
    bilibili_news = [item for item in all_news if item.get('source_platform') == '哔哩哔哩']

    def is_political_or_military(title):
        political_keywords = ['政治', '政府', '官员', '政策', '军', '军队', '军事', '战争', '外交', '选举', '党', '纪委', '监察', '人大', '政协', '国家', '领导', '主席', '总理', '政治局', '中央', '法院', '检察院', '公安', '警察', '武警', '部队', '国防', '导弹', '核武器', '外交', '联合国', '选举', '投票', '政党', '议会', '国会', '立法', '司法', '行政', '公务员', '国企', '央企', '国资委', '发改委', '财政部', '央行', '货币政策', '财政政策', '经济政策', '贸易战', '制裁', '地缘', '冲突', '动乱', '暴乱', '抗议', '示威', '游行', '罢工', '罢课', '罢市', '弹劾', '问责', '调查', '审查', '审计', '监督', '举报', '控告', '起诉', '审判', '判决', '拘留', '逮捕', '审讯']
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in political_keywords)

    filtered_tencent = [item for item in tencent_news if not is_political_or_military(item.get('title', ''))]
    filtered_douyin = [item for item in douyin_news if not is_political_or_military(item.get('title', ''))]
    filtered_bilibili = [item for item in bilibili_news if not is_political_or_military(item.get('title', ''))]

    selected_items = []
    titles_set = set()

    for item in filtered_tencent:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 3:
            titles_set.add(title)
            selected_items.append(item)

    for item in filtered_douyin:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 6:
            titles_set.add(title)
            selected_items.append(item)

    for item in filtered_bilibili:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 9:
            titles_set.add(title)
            selected_items.append(item)

    all_filtered = [item for item in all_news if not is_political_or_military(item.get('title', ''))]
    for item in all_filtered:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 9:
            titles_set.add(title)
            selected_items.append(item)

    selected_items = selected_items[:9]
    summary_titles = [item['title'] for item in selected_items[:3]]
    summary_text = f"今日娱乐资讯精选：{'、'.join(summary_titles)}等热点话题"

    return selected_items, summary_text

def aggregate_news(timestamp):
    print("开始抓取各平台热点内容...")
    
    # Run scrapers
    print("正在抓取腾讯娱乐热点...")
    get_tencent_entertainment_hot()
    print("正在抓取抖音热点...")
    get_douyin_rank()
    print("正在抓取哔哩哔哩热点...")
    get_bilibili_rank()

    all_news = []
    
    if os.path.exists('tencent_ent_hot.json'):
        with open('tencent_ent_hot.json', 'r', encoding='utf-8') as f:
            tencent_data = json.load(f)
            for item in tencent_data:
                all_news.append({
                    'title': item.get('标题', ''),
                    'link': item.get('链接', ''),
                    'image': item.get('图片', ''),
                    'source_platform': '腾讯娱乐',
                    'content': item.get('标题', '')
                })

    if os.path.exists('douyin_rank.json'):
        with open('douyin_rank.json', 'r', encoding='utf-8') as f:
            douyin_data = json.load(f)
            for item in douyin_data:
                all_news.append({
                    'title': item.get('title', ''),
                    'link': item.get('video_link', ''),
                    'image': item.get('cover_image', ''),
                    'source_platform': '抖音',
                    'content': item.get('title', '')
                })

    if os.path.exists('bilibili_rank.json'):
        with open('bilibili_rank.json', 'r', encoding='utf-8') as f:
            bilibili_data = json.load(f)
            for item in bilibili_data:
                all_news.append({
                    'title': item.get('title', ''),
                    'link': item.get('video_link', ''),
                    'image': item.get('cover_image', ''),
                    'source_platform': '哔哩哔哩',
                    'content': item.get('title', '')
                })

    # --- HISTORY FILTERING ---
    if HistoryManager:
        history_mgr = HistoryManager()
        print(f"  [Entertainment] Total raw: {len(all_news)}")
        filtered_news = [n for n in all_news if not history_mgr.is_duplicate(n.get('title'), n.get('content', ''))]
        print(f"  [Entertainment] After history filtering: {len(filtered_news)}")
        all_news = filtered_news
    # -------------------------

    selected_news, summary_text = filter_content_by_rules(all_news)

    beijing_time = datetime.utcnow() + timedelta(hours=8)
    summary_title = f"娱乐资讯精选 | {beijing_time.strftime('%m月%d日')}热点"

    temp_images_dir = os.path.join(os.getcwd(), f"temp_images_ent_{timestamp}")
    os.makedirs(temp_images_dir, exist_ok=True)

    print(f"正在为筛选出的 {len(selected_news)} 条新闻处理图片...")
    
    processed_images = {}
    for i, news_item in enumerate(selected_news):
        image_url = news_item['image']
        news_item['local_image'] = "" 
        
        if image_url and image_url != "无图片" and "下载失败" not in image_url:
            try:
                safe_title = sanitize_filename(news_item['title'][:4], 10)
                
                if image_url.startswith('http'):
                    response = requests.get(image_url, timeout=15)
                    if response.status_code == 200:
                        ext = '.jpg'
                        if '.png' in image_url.lower(): ext = '.png'
                        elif '.webp' in image_url.lower(): ext = '.webp'
                        
                        image_filename = f"rank{i+1}_{safe_title}_{timestamp}{ext}"
                        image_path = os.path.join(temp_images_dir, image_filename)

                        with open(image_path, 'wb') as img_file:
                            img_file.write(response.content)

                        resized_path = image_path.replace(ext, f"_resized{ext}")
                        resize_image(image_path, resized_path)
                        if os.path.exists(image_path): os.remove(image_path)
                        
                        processed_images[i] = os.path.basename(resized_path)
                        news_item['local_image'] = resized_path 
                else:
                    if os.path.exists(image_url):
                        ext = os.path.splitext(image_url)[1] or ".jpg"
                        image_filename = f"rank{i+1}_{safe_title}_{timestamp}{ext}"
                        image_path = os.path.join(temp_images_dir, image_filename)
                        resize_image(image_url, image_path)
                        processed_images[i] = os.path.basename(image_path)
                        news_item['local_image'] = image_path
            except Exception as e:
                print(f"处理图片失败 {image_url}: {e}")

    final_result = [{
        "rank": 0,
        "title": summary_title[:20],
        "content": summary_text
    }]

    for i, news_item in enumerate(selected_news):
        image_filename = ""
        if i in processed_images:
            image_filename = f"images/{processed_images[i]}"

        final_result.append({
            "rank": i + 1,
            "title": news_item['title'],
            "source_platform": news_item.get('source_platform', '未知'),
            "source_url": news_item.get('link', ''),
            "content": news_item.get('content', news_item['title']),
            "image": image_filename
        })

    for f in ['tencent_ent_hot.json', 'douyin_rank.json', 'bilibili_rank.json', 'douyin_rank.csv', 'bilibili_rank.csv']:
        if os.path.exists(f): os.remove(f)
    
    shutil.rmtree('images/ent_hot', ignore_errors=True)

    polished_data = {"news": final_result, "timestamp": timestamp}
    return polished_data, temp_images_dir

def main():
    parser = argparse.ArgumentParser(description='综合娱乐新闻聚合器')
    parser.add_argument('mode', nargs='?', choices=['tencent', 'douyin', 'bilibili', 'all', 'aggregate'], default='aggregate')
    args = parser.parse_args()

    if args.mode == 'aggregate':
        # Use Beijing time if running locally/testing, though main pipeline passes timestamp usually
        beijing_time = datetime.utcnow() + timedelta(hours=8)
        timestamp = beijing_time.strftime("%Y%m%d_%H%M%S")
        data, img_dir = aggregate_news(timestamp)
        print(f"聚合完成。数据项: {len(data['news'])}, 图片目录: {img_dir}")
    else:
        if args.mode == 'tencent' or args.mode == 'all': run_tencent_scraper()
        if args.mode == 'douyin' or args.mode == 'all': run_douyin_scraper()
        if args.mode == 'bilibili' or args.mode == 'all': run_bilibili_scraper()

if __name__ == '__main__':
    main()
