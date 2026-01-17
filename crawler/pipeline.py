import os
import json
import sys
import shutil
import zipfile
from datetime import datetime, timedelta

# Add crawler subdirectories to path
sys.path.append(os.path.dirname(__file__))

# Import modules
from homenews import home_polish
from worldnews import world_polish
from entertainment import ent_polish
import image_utils

# --- Configuration ---
OUTPUT_DIR = "output"
LATEST_VERSION_FILE = os.path.join(OUTPUT_DIR, "latest_versions.json")

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def update_latest_version(section, zip_filename):
    """Updates the latest_versions.json file."""
    versions = {}
    if os.path.exists(LATEST_VERSION_FILE):
        try:
            with open(LATEST_VERSION_FILE, 'r') as f:
                versions = json.load(f)
        except:
            pass
    
    versions[section] = zip_filename
    
    with open(LATEST_VERSION_FILE, 'w') as f:
        json.dump(versions, f, indent=4)
    print(f"  [✓] 更新最新版本记录: {section} -> {zip_filename}")

def package_section(section_prefix, polished_data, timestamp_str):
    """
    通用打包函数：
    1. 下载/处理图片 (长图用公版替代)
    2. 失败则使用公版图片
    3. 生成 ZIP 包
    """
    print(f"\n[{section_prefix}] 正在打包数据...")
    
    # 临时目录
    temp_dir = os.path.join(OUTPUT_DIR, f"temp_{section_prefix}_{timestamp_str}")
    temp_images_dir = os.path.join(temp_dir, "images")
    os.makedirs(temp_images_dir, exist_ok=True)
    
    try:
        polished_items = polished_data.get("news", [])
        
        # 先保存调试版（保存原始的 polished_data，图片URL未修改）
        debug_json_path = os.path.join(OUTPUT_DIR, f"test_{section_prefix}_{timestamp_str}.json")
        with open(debug_json_path, 'w', encoding='utf-8') as f:
            json.dump(polished_data, f, ensure_ascii=False, indent=4)
        print(f"  [✓] 调试文件已保存: test_{section_prefix}_{timestamp_str}.json")
        
        # 1. 处理图片
        print(f"  正在处理 {len(polished_items)-1} 条新闻图片...")
        
        for item in polished_items:
            rank = item.get("rank", 0)
            if rank == 0: 
                continue

            remote_url = item.get("image", "")
            title = item.get('title', 'NoTitle')
            author = item.get('author', '')
            
            # 生成安全文件名
            raw_prefix = title[:6]
            safe_prefix = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in raw_prefix])
            if not safe_prefix: 
                safe_prefix = "Img"
            
            # 统一使用 jpg 或根据原 url 后缀
            ext = ".jpg"
            if remote_url and ".png" in remote_url.lower(): 
                ext = ".png"
            if remote_url and ".webp" in remote_url.lower(): 
                ext = ".webp"
            
            filename = f"rank{rank}_{safe_prefix}_{timestamp_str}{ext}"
            local_path = os.path.join(temp_images_dir, filename)
            rel_path = f"images/{filename}"
            
            success = False
            
            # 尝试下载并处理（包含长图检测）
            if remote_url and remote_url.startswith("http"):
                success = image_utils.download_and_process(remote_url, local_path)
            
            # 失败或无效 URL，使用公版图片
            if not success:
                print(f"    [!] 图片获取失败 (Rank {rank})，使用公版图片: {author}")
                success = image_utils.copy_placeholder(author, local_path)

            # 更新 item.image 字段
            if success:
                item["image"] = rel_path
            else:
                # 彻底失败，保留空值或使用默认值
                item["image"] = ""
        
        # 2. 统一化 JSON 格式：只保留必要字段
        # 对于 ZIP 包内的 JSON，只保留：rank, title, source_platform, source_url, content, image
        cleaned_news = []
        for item in polished_items:
            cleaned_item = {
                "rank": item.get("rank", 0),
                "title": item.get("title", ""),
                "original_title": item.get("title0", ""),
                "source_platform": item.get("source_platform", ""),
                "source_url": item.get("source_url", ""),
                "content": item.get("content", ""),
                "image": item.get("image", "")
            }
            cleaned_news.append(cleaned_item)
            
        # 3. 保存用于 zip 的 json（图片路径已修改为本地相对路径）
        json_filename_in_zip = f"polished_all_{timestamp_str}.json"
        json_path_temp = os.path.join(temp_dir, json_filename_in_zip)
        
        # 重新组织 JSON 顺序：news 数组 + timestamp
        polished_data_ordered = {
            "news": cleaned_news,
            "timestamp": timestamp_str
        }
        
        with open(json_path_temp, 'w', encoding='utf-8') as f:
            json.dump(polished_data_ordered, f, ensure_ascii=False, indent=4)
            
        # 4. 创建 ZIP
        zip_name = f"{section_prefix}_{timestamp_str}.zip"
        zip_path = os.path.join(OUTPUT_DIR, zip_name)
        
        print(f"  正在生成压缩包: {zip_name}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_path_temp, arcname=json_filename_in_zip)
            for root, _, files in os.walk(temp_images_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = f"images/{file}"
                    zf.write(abs_path, arcname=rel_path)
                        
        print(f"  [✓] 打包完成。")
        update_latest_version(section_prefix.lower(), zip_name)
        
        return True

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- HOME NEWS PIPELINE ---
def run_home_news(count=9):
    print("\n" + "="*40)
    print("🏠 [Home] 开始执行国内新闻流程")
    print("="*40)
    
    try:
        # 调用主流程，传入新闻数量参数
        polished = home_polish.main(count=count)
        
        if not polished or "news" not in polished:
            print("  [!] 国内新闻润色失败。")
            return None
        
        return polished
        
    except Exception as e:
        print(f"  [!] Home 流程异常: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- WORLD NEWS PIPELINE ---
def run_world_news(count=9):
    print("\n" + "="*40)
    print("🌍 [World] 开始执行国际新闻流程")
    print("="*40)
    
    try:
        # 调用主流程，传入新闻数量参数（使用 limit 参数名）
        world_polish.main(limit=count)
        
        # 从 worldnews/output 读取最新生成的文件
        worldnews_output = os.path.join(os.path.dirname(__file__), "worldnews", "output")
        if os.path.exists(worldnews_output):
            files = os.listdir(worldnews_output)
            json_files = [f for f in files if f.endswith('.json')]
            if json_files:
                json_files.sort(reverse=True)
                latest_json = json_files[0]
                json_path = os.path.join(worldnews_output, latest_json)
                
                with open(json_path, 'r', encoding='utf-8') as f:
                    polished_data = json.load(f)
                
                polished_data = {"news": polished_data} if isinstance(polished_data, list) else polished_data
                return polished_data
            else:
                print("  [!] 未找到生成的 JSON 文件。")
                return None
        else:
            print("  [!] worldnews/output 目录不存在。")
            return None
        
    except Exception as e:
        print(f"  [!] World 流程异常: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- ENTERTAINMENT NEWS PIPELINE ---
def run_entertainment_news(count=9):
    print("\n" + "="*40)
    print("🎉 [Entertainment] 开始执行娱乐新闻流程")
    print("="*40)
    
    try:
        # 调用主流程，传入新闻数量参数
        polished_data = ent_polish.aggregate_news(count=count)
        
        if not polished_data or not polished_data.get("news"):
            print("  [!] 娱乐新闻聚合失败。")
            return None
        
        return polished_data
        
    except Exception as e:
        print(f"  [!] Entertainment 流程异常: {e}")
        import traceback
        traceback.print_exc()
        return None

def cleanup_output_directory():
    """
    清理 output 目录：
    1. 删除其他非 ZIP、非 latest_versions.json、非 test_*.json 的文件
    2. 对于每个平台（Home/World/Entertainment），只保留最新的 1 个 ZIP
    3. 保留最新的 3 个 test_*.json 调试文件（每个平台 1 个）
    4. 最终结果：3 个最新 ZIP + 3 个 test JSON + latest_versions.json
    """
    print("\n" + "="*40)
    print("🧹 [Cleanup] 清理输出目录")
    print("="*40)
    
    if not os.path.exists(OUTPUT_DIR):
        print("  output 目录不存在")
        return
    
    all_files = os.listdir(OUTPUT_DIR)
    
    # 1. 删除其他非 ZIP、非 latest_versions.json、非 test_*.json 的文件
    print("  正在删除无效文件...")
    invalid_files = [
        f for f in all_files 
        if not f.endswith('.zip') 
        and f != 'latest_versions.json' 
        and not f.startswith('test_')
        and not f.startswith('temp_')
        and not f.endswith('_history.json') # 防止误删历史记录文件
    ]
    for f in invalid_files:
        try:
            full_path = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(full_path):
                os.remove(full_path)
                print(f"    [✓] 删除: {f}")
        except Exception as e:
            print(f"    [!] 删除失败 {f}: {e}")
    
    # 2. 清理过期的 ZIP 包（每个平台只保留最新的 1 个）
    print("  正在清理过期 ZIP 包...")
    prefixes = ["Home_", "World_", "Entertainment_"]
    
    for prefix in prefixes:
        zip_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(prefix) and f.endswith(".zip")]
        
        if not zip_files:
            print(f"    {prefix}: 未找到 ZIP 文件")
            continue
        
        # 按时间戳倒序排序（最新的在前）
        zip_files.sort(reverse=True)
        
        print(f"    {prefix}: 现有 {len(zip_files)} 个，保留最新 1 个")
        
        # 删除除了最新的以外的所有文件
        for zip_file in zip_files[1:]:
            try:
                full_path = os.path.join(OUTPUT_DIR, zip_file)
                os.remove(full_path)
                print(f"      [✓] 删除旧版本: {zip_file}")
            except Exception as e:
                print(f"      [!] 删除失败 {zip_file}: {e}")
    
    # 3. 清理过期的 test_*.json 调试文件（每个平台只保留最新的 1 个）
    print("  正在清理过期调试文件...")
    test_prefixes = ["test_Home_", "test_World_", "test_Entertainment_"]
    
    for test_prefix in test_prefixes:
        test_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(test_prefix) and f.endswith(".json")]
        
        if not test_files:
            continue
        
        # 按时间戳倒序排序（最新的在前）
        test_files.sort(reverse=True)
        
        # 删除除了最新的以外的所有调试文件
        for test_file in test_files[1:]:
            try:
                full_path = os.path.join(OUTPUT_DIR, test_file)
                os.remove(full_path)
                print(f"    [✓] 删除旧调试文件: {test_file}")
            except Exception as e:
                print(f"    [!] 删除失败 {test_file}: {e}")
    
    # 4. 验证最终状态
    print("\n  最终文件状态：")
    remaining_files = os.listdir(OUTPUT_DIR)
    zip_count = 0
    test_count = 0
    
    for f in sorted(remaining_files):
        file_path = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            if size > 1024*1024:
                size_str = f"{size / (1024*1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            print(f"    ✓ {f} ({size_str})")
            
            if f.endswith('.zip'):
                zip_count += 1
            elif f.startswith('test_') and f.endswith('.json'):
                test_count += 1
    
    print(f"\n  [✓] 清理完成。保留 {zip_count} 个 ZIP + {test_count} 个调试文件 + latest_versions.json")

def cleanup_intermediate_dirs():
    """清理临时目录"""
    print("\n  正在清理临时抓取目录...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dirs_to_remove = [
        "bbc_news_data", "cnn_data", "nytimes_data", "sky_news_data", 
        "SampleNewsG", "RawData_Backup"
    ]
    for d in dirs_to_remove:
        path = d if os.path.isabs(d) else os.path.join(base_dir, d)
        if os.path.exists(path):
            try: 
                shutil.rmtree(path)
            except Exception: 
                pass

def main():
    print("\n" + "#"*50)
    print(f"🚀 启动 PostGarden 全流程爬虫任务")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*50)

    ensure_dirs()
    
    # Timestamp for packaging
    beijing_time = datetime.utcnow() + timedelta(hours=8)
    timestamp = beijing_time.strftime('%Y%m%d_%H%M%S')
    print(f"⏳ 全局时间戳 (北京时间): {timestamp}")
    
    # 配置：每个平台抓取的新闻数量
    news_count = 9
    
    # 运行三大板块，只传入新闻数量参数
    print("\n" + "="*50)
    print("📋 启动各平台数据采集和润色")
    print("="*50)
    
    home_data = run_home_news(count=news_count)
    world_data = run_world_news(count=news_count)
    ent_data = run_entertainment_news(count=news_count)
    
    # 打包阶段：使用时间戳为 ZIP 命名
    print("\n" + "="*50)
    print("📦 启动数据打包阶段")
    print("="*50)
    
    if home_data:
        package_section("Home", home_data, timestamp)
    
    if world_data:
        package_section("World", world_data, timestamp)
    
    if ent_data:
        package_section("Entertainment", ent_data, timestamp)
    
    # 收尾
    cleanup_output_directory()
    cleanup_intermediate_dirs()
    
    print("\n" + "#"*50)
    print("✅ 全流程任务执行完毕！")
    print("#"*50 + "\n")

if __name__ == "__main__":
    main()