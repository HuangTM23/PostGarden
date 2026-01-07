import os
import json
import subprocess
import shutil
import requests
import re
import time
import argparse
import zipfile
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# --- Configuration ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"

# 脚本路径
SCRAPERS = [
    '/home/dawn/codes/python/worldnews/scrape_bbc_news.py',
    '/home/dawn/codes/python/worldnews/scrape_cnn.py',
    '/home/dawn/codes/python/worldnews/scrape_nytimes.py',
    '/home/dawn/codes/python/worldnews/scrape_sky_news.py'
]

# 数据源配置
SOURCE_CONFIG = {
    'bbc_news_data': 'bbc',
    'cnn_data': 'cnn',
    'nytimes_data': 'nytimes',
    'sky_news_data': 'sky'
}

# 目录路径
SAMPLE_DIR = 'SampleNewsG'
IMAGES_SUBDIR = 'images'
BACKUP_DIR = 'RawData_Backup'

# V2 Prompt Template (Updated)
# Remove strict image path requirement from prompt since we use URL lookup
V2_PROMPT_TEMPLATE = """
你是一名专业的中文国际新闻编辑，负责为“小红书”和“微信公众号”制作一期国际新闻精选。

输入数据说明（Input）
你将接收来自 4 个国际新闻平台 的新闻 JSON 数据，共 4 × N 条新闻。
字段说明：
- rank：原平台排序
- title：英文原始标题
- content：英文新闻正文
- source_url：原文链接 (唯一标识)

核心目标（Core Objective）
从输入数据中，通过“事件级去重”和“质量筛选”，选出 {limit} 条最具价值的国际新闻，并进行翻译润色。
最后，你需要为这一期内容起一个**极具吸引力、抽象且有深度的总标题**。

任务要求与执行逻辑

1️⃣ 筛选与去重 (保留 {limit} 条)
- **去重**：同一事件仅保留 1 条。
- **筛选**：优先选择有重大影响力、有冲突感或新奇感的国际新闻（政治、战争、科技变革、重大灾难）。
- **图片优先**：请优先保留那些重要的新闻，即使它们可能没有图片（如果有图片最好）。

2️⃣ 翻译与润色 (针对这 {limit} 条新闻)
- **中文标题**：<20字。准确、吸睛，拒绝标题党但要有张力。
- **中文正文**：<50字。极简新闻体。只讲核心事实（发生了什么+结果）。
- **source_url**：**必须**准确保留，用于匹配原始图片。

3️⃣ ⭐️ 总标题生成 (Rank 0) ⭐️
- **要求**：为这 {limit} 条新闻生成一个总标题。
- **风格**：抽象、文艺、有深意，适合小红书/公众号封面。
- **禁止**：不要使用“今日国际新闻”、“新闻速览”这种无聊的标题。
- **建议方向**：使用隐喻、对比、宏观概括。
- **范例**：
  - “战火与玫瑰：中东局势下的平凡生活”
  - “巨人的黄昏：全球地缘政治新变局”
  - “硅谷的裂痕与世界的脉动”
- **字数**：20字以内。

输出格式要求 (JSON List)
请直接输出一个 JSON 列表，包含 {limit} + 1 个对象。

第 1 个对象 (Rank 0 - 总标题)：
{{
  "rank": 0,
  "title": "这里填写你生成的绝佳总标题",
  "content": ""  <-- 必须留空
}}

后续 {limit} 个对象 (Rank 1 - {limit})：
{{
  "rank": 1,
  "title": "单条新闻中文标题",
  "source_platform": "来源平台",
  "source_url": "原文链接 (必须准确)",
  "content": "50字以内的中文精简正文"
}}
...

强制约束
1. 仅输出 JSON，不要有markdown标记。
2. Rank 0 的 content 必须为空字符串。
3. 必须选出 {limit} 条新闻，不能少。

以下是原始新闻数据:
{news_data}
"""

def setup_directories():
    """创建必要的目录"""
    if os.path.exists(SAMPLE_DIR):
        shutil.rmtree(SAMPLE_DIR)
    os.makedirs(os.path.join(SAMPLE_DIR, IMAGES_SUBDIR))
    print(f"Created directory: {SAMPLE_DIR}")

def run_scrapers(limit=10):
    """运行所有抓取脚本"""
    print(f"\n--- 1. Starting Scrapers (Limit: {limit}) ---")
    for scraper in SCRAPERS:
        print(f"Running {os.path.basename(scraper)}...")
        try:
            subprocess.run(['python3', scraper, '--limit', str(limit)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {scraper}: {e}")
        except Exception as e:
            print(f"Unexpected error running {scraper}: {e}")

def sanitize_filename(text):
    """清理文件名，移除无效字符"""
    text = re.sub(r'[\\/*?:\"<>|]', "", text)
    # 取前几个词，避免过长
    words = text.split()[:5] 
    short_text = "_".join(words)
    return short_text[:50]

def aggregate_data():
    """收集所有平台的原始数据，并建立 URL 映射"""
    all_news_items = []
    url_map = {} # source_url -> item data
    
    for source_dir, prefix in SOURCE_CONFIG.items():
        json_file = os.path.join(source_dir, 'data.json')
        if not os.path.exists(json_file):
            print(f"Warning: {json_file} not found. Skipping.")
            continue
            
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Loaded {len(data)} items from {prefix}")
        
        for item in data:
            url = item.get('source_url')
            # 记录原始数据用于查找图片
            if url:
                url_map[url] = item
            
            # 传递给 DeepSeek 的数据 (精简版)
            processed_item = {
                "rank": item.get('rank'),
                "title": item.get('title'),
                "source_platform": item.get('source_platform'),
                "source_url": url,
                "content": item.get('content', '')[:800], # 截断
            }
            all_news_items.append(processed_item)
            
    return all_news_items, url_map

def call_deepseek_v2(all_news, limit):
    """调用 DeepSeek API 进行筛选和润色"""
    print(f"\n--- 2. Calling DeepSeek V2 (Limit: {limit}) ---")
    
    # 构造 Prompt
    news_json_str = json.dumps(all_news, ensure_ascii=False, indent=2)
    prompt = V2_PROMPT_TEMPLATE.format(limit=limit, news_data=news_json_str)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3, 
    }

    try:
        print("Sending request to DeepSeek... (This may take a while)")
        response = requests.post(API_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        content_str = result['choices'][0]['message']['content']
        
        # 清理可能存在的 markdown code block 标记
        content_str = content_str.replace("```json", "").replace("```", "").strip()
        
        try:
            if content_str.startswith("{") and "}{" in content_str:
                content_str = f"[{content_str.replace('}{', '},{')}]"
            elif content_str.startswith("{") and not content_str.strip().endswith("}"):
                 pass
            elif not content_str.startswith("["):
                 start = content_str.find("[")
                 end = content_str.rfind("]")
                 if start != -1 and end != -1:
                     content_str = content_str[start:end+1]
            
            final_data = json.loads(content_str)
            
            if isinstance(final_data, dict):
                final_data = [final_data]
                
            return final_data
            
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Raw Response: {content_str[:500]}...")
            return None

    except Exception as e:
        print(f"DeepSeek API Error: {e}")
        return None

def process_results(final_data, url_map):
    """处理 DeepSeek 返回的结果：匹配图片，重命名，保存"""
    print(f"\n--- 3. Processing Results ---")
    
    if not final_data:
        print("No data received from DeepSeek.")
        return

    processed_list = []
    
    for item in final_data:
        rank = item.get('rank')
        
        # Rank 0: 总结标题
        if rank == 0:
            processed_list.append(item)
            continue
            
        # Rank 1-N: 新闻内容
        url = item.get('source_url')
        original_data = url_map.get(url)
        
        final_img_path = ""
        
        if original_data:
            # 找到原始数据中的图片路径
            original_img_path = original_data.get('local_image_path')
            
            if original_img_path and os.path.exists(original_img_path) and not "failed" in original_img_path:
                # 构造新文件名
                # 格式: rank{rank}_{TitleSnippet}_{Timestamp}.ext
                # Use Chinese title if available (from item), otherwise fallback to English title
                # DeepSeek returns Chinese title in 'item["title"]'
                news_title = item.get('title', 'NoTitle')
                title_snippet = sanitize_filename(news_title)
                # Further limit to ~10 chars for cleaner filenames
                title_snippet = title_snippet[:10]
                
                ext = os.path.splitext(original_img_path)[1]
                if not ext: ext = ".jpg"
                
                img_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_filename = f"rank{rank}_{title_snippet}_{img_timestamp}{ext}"
                target_path = os.path.join(SAMPLE_DIR, IMAGES_SUBDIR, new_filename)
                
                try:
                    shutil.copy2(original_img_path, target_path)
                    # JSON 中保存相对路径
                    final_img_path = os.path.join(IMAGES_SUBDIR, new_filename)
                    print(f"  - [Rank {rank}] Copied image: {new_filename}")
                except Exception as e:
                    print(f"  - [Rank {rank}] Failed to copy image: {e}")
            else:
                print(f"  - [Rank {rank}] No local image found in original data.")
        else:
            print(f"  - [Rank {rank}] Warning: Could not find original data for URL: {url}")
        
        item['image'] = final_img_path
        processed_list.append(item)
        
    # 保存最终 JSON
    output_json = os.path.join(SAMPLE_DIR, "final_news.json")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, indent=4, ensure_ascii=False)
    print(f"Final JSON saved to: {output_json}")
    
    return processed_list

def create_zip_package():
    """创建最终的 ZIP 包"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"SampleNews_{timestamp}.zip"
    zip_filepath = os.path.join(SAMPLE_DIR, zip_filename)
    
    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 添加 JSON 文件
            json_file = "final_news.json"
            json_path = os.path.join(SAMPLE_DIR, json_file)
            if os.path.exists(json_path):
                # Rename JSON inside the zip
                new_json_name = f"polished_all_{timestamp}.json"
                zf.write(json_path, arcname=new_json_name)
            
            # 添加图片文件夹
            img_dir = os.path.join(SAMPLE_DIR, IMAGES_SUBDIR)
            if os.path.exists(img_dir):
                for root, dirs, files in os.walk(img_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.join(IMAGES_SUBDIR, file)
                        zf.write(abs_path, arcname=rel_path)
        print(f"Zip package created: {zip_filepath}")
    except Exception as e:
        print(f"Error creating zip package: {e}")

def cleanup_intermediate_data():
    """移动所有中间生成的抓取目录到备份文件夹"""
    print(f"\n--- 4. Moving Intermediate Data to {BACKUP_DIR} ---")
    for source_dir in SOURCE_CONFIG.keys():
        if os.path.exists(source_dir):
            try:
                # 目标路径: RawData_Backup/cnn_data
                target_path = os.path.join(BACKUP_DIR, source_dir)
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                shutil.move(source_dir, target_path)
                print(f"  - Moved: {source_dir} -> {target_path}")
            except Exception as e:
                print(f"  - Error moving {source_dir}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run news scrapers and processor V2.")
    parser.add_argument('--limit', type=int, default=10, help="Number of final news items to select (N).")
    args = parser.parse_args()

    setup_directories()
    # 扩大抓取数量，确保有足够的候选池 (例如 2倍)
    scrape_limit = max(args.limit, 5) # 至少抓取5个
    run_scrapers(limit=scrape_limit)
    
    all_news, url_map = aggregate_data()
    
    if not all_news:
        print("No news collected. Exiting.")
        exit()
        
    final_data = call_deepseek_v2(all_news, args.limit)
    
    if final_data:
        process_results(final_data, url_map)
        create_zip_package()
    else:
        print("DeepSeek processing failed.")
        
    cleanup_intermediate_data()
    print(f"\n--- Pipeline V2 Completed. Check {SAMPLE_DIR} ---")