import os
import json
import sys
import shutil
import requests
import zipfile
from datetime import datetime

# Add crawler subdirectories to path
sys.path.append(os.path.dirname(__file__))

# Import modules
from homenews import fetch_baidu, fetch_toutiao, fetch_tencent, polish as home_polish
from worldnews import process_news as world_process
from entertainment import aggregator as ent_aggregator

# --- Configuration ---
OUTPUT_DIR = "output"
LATEST_VERSION_FILE = os.path.join(OUTPUT_DIR, "latest_versions.json")
KEEP_COUNT = 4  # Keep last 4 sets

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_image(url, local_path):
    """Generic image downloader."""
    if not url or not url.startswith('http'):
        return False, "Invalid URL"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        response = requests.get(url, stream=True, timeout=15, headers=headers)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        # Flexible check
        if 'image' not in content_type and not url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            pass

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        if os.path.getsize(local_path) < 3072: # 3KB
            os.remove(local_path)
            return False, "File too small"
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

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
    print(f"  ✓ Updated latest_versions.json: {section} -> {zip_filename}")

def package_section(section_prefix, polished_data, timestamp_str):
    """
    Creates ZIP archive in a temporary way, then moves result to output.
    Does NOT leave loose images or json in output.
    """
    print(f"\n[{section_prefix}] Packaging...")
    
    # Create a temp dir for this packaging session
    temp_dir = os.path.join(OUTPUT_DIR, f"temp_{section_prefix}_{timestamp_str}")
    temp_images_dir = os.path.join(temp_dir, "images")
    os.makedirs(temp_images_dir, exist_ok=True)
    
    try:
        polished_items = polished_data.get("news", [])
        polished_data["timestamp"] = timestamp_str
        
        # 1. Process Images (Download to temp_images_dir)
        for item in polished_items:
            if item.get("rank", 0) == 0: continue

            remote_url = item.get("image")
            is_local = not remote_url.startswith("http") if remote_url else False
            
            if remote_url:
                title = item.get('title', 'NoTitle')
                raw_prefix = title[:4]
                safe_prefix = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in raw_prefix])
                if not safe_prefix: safe_prefix = "Img"
                
                ext = ".jpg"
                if remote_url.lower().endswith(".png"): ext = ".png"
                if remote_url.lower().endswith(".webp"): ext = ".webp"
                
                filename = f"rank{item['rank']}_{safe_prefix}_{timestamp_str}{ext}"
                local_path = os.path.join(temp_images_dir, filename)
                
                success = False
                if is_local:
                    # Logic for local files (from World news processor) will be handled separately 
                    # or passed in differently. For standard package_section, we assume remote or pre-staged.
                    pass
                else:
                    success, _ = download_image(remote_url, local_path)
                
                if success:
                    item["image"] = f"images/{filename}"
                elif is_local:
                    pass
                else:
                    item["image"] = ""

        # 2. Save JSON to temp dir
        # In ZIP, we use standard name "polished_all_{timestamp}.json"
        json_filename_in_zip = f"polished_all_{timestamp_str}.json"
        json_path = os.path.join(temp_dir, json_filename_in_zip)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(polished_data, f, ensure_ascii=False, indent=4)
            
        # 3. Create ZIP directly in OUTPUT_DIR
        zip_name = f"{section_prefix}_{timestamp_str}.zip"
        zip_path = os.path.join(OUTPUT_DIR, zip_name)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add JSON
            zf.write(json_path, arcname=json_filename_in_zip)
            
            # Add Images
            for root, _, files in os.walk(temp_images_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = f"images/{file}"
                    zf.write(abs_path, arcname=rel_path)
                        
        print(f"  ✓ Created {zip_name}")
        
        # 4. Update Index
        update_latest_version(section_prefix.lower(), zip_name)
        
        return True

    finally:
        # Cleanup temp dir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- HOME NEWS PIPELINE ---
def run_home_news(timestamp_str):
    print("\n--- Running Home News ---")
    all_news = []
    try: all_news.extend(fetch_baidu.main(limit=9))
    except Exception as e: print(e)
    try: all_news.extend(fetch_toutiao.main(limit=9))
    except Exception as e: print(e)
    try: all_news.extend(fetch_tencent.main(report_type="morning", limit=9))
    except Exception as e: print(e)
    
    if not all_news: return
    
    polished = home_polish.main(all_news)
    if not polished or "news" not in polished: return
    
    package_section("Home", polished, timestamp_str)

# --- WORLD NEWS PIPELINE ---
def run_world_news(timestamp_str):
    print("\n--- Running World News ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    world_dir = os.path.join(base_dir, "worldnews")
    
    world_process.SCRAPERS = [
        os.path.join(world_dir, 'scrape_bbc_news.py'),
        os.path.join(world_dir, 'scrape_cnn.py'),
        os.path.join(world_dir, 'scrape_nytimes.py'),
        os.path.join(world_dir, 'scrape_sky_news.py')
    ]
    
    try:
        world_process.setup_directories()
        world_process.run_scrapers(limit=10)
        all_news, url_map = world_process.aggregate_data()
        
        if not all_news: return

        final_data_list = world_process.call_deepseek_v2(all_news, limit=10)
        if not final_data_list: return
            
        # Custom Packaging for World News (handling local images)
        print(f"\n[World] Packaging...")
        
        temp_dir = os.path.join(OUTPUT_DIR, f"temp_World_{timestamp_str}")
        temp_images_dir = os.path.join(temp_dir, "images")
        os.makedirs(temp_images_dir, exist_ok=True)
        
        try:
            polished_data = {"news": final_data_list, "timestamp": timestamp_str}
            
            # Move images from World crawler temp to our temp
            for item in final_data_list:
                rank = item.get('rank', 0)
                if rank == 0: continue
                
                url = item.get('source_url')
                original_data = url_map.get(url)
                item['image'] = "" 
                
                if original_data:
                    src_path = original_data.get('local_image_path')
                    if src_path and os.path.exists(src_path):
                        title = item.get('title', 'NoTitle')
                        raw_prefix = title[:4]
                        safe_prefix = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in raw_prefix])
                        if not safe_prefix: safe_prefix = "Img"
                        
                        ext = os.path.splitext(src_path)[1]
                        if not ext: ext = ".jpg"
                        
                        filename = f"rank{rank}_{safe_prefix}_{timestamp_str}{ext}"
                        dest_path = os.path.join(temp_images_dir, filename)
                        
                        shutil.copy2(src_path, dest_path)
                        item['image'] = f"images/{filename}"
            
            # Save JSON
            json_filename = f"polished_all_{timestamp_str}.json"
            json_path = os.path.join(temp_dir, json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(polished_data, f, ensure_ascii=False, indent=4)
                
            # Create ZIP
            zip_name = f"World_{timestamp_str}.zip"
            zip_path = os.path.join(OUTPUT_DIR, zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(json_path, arcname=json_filename)
                for root, _, files in os.walk(temp_images_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = f"images/{file}"
                        zf.write(abs_path, arcname=rel_path)
            
            print(f"  ✓ Created {zip_name}")
            update_latest_version("world", zip_name)
            
        finally:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"Error in World News Pipeline: {e}")
        import traceback
        traceback.print_exc()

# --- ENTERTAINMENT NEWS PIPELINE ---
def run_entertainment_news(timestamp_str):
    print("\n--- Running Entertainment News ---")
    try:
        # 1. Run aggregator (includes scraping and rule-based filtering)
        polished_data, temp_img_dir = ent_aggregator.aggregate_news(timestamp_str)
        
        if not polished_data or not polished_data.get("news"):
            print("Entertainment news aggregation failed or empty.")
            return

        print(f"[Entertainment] Packaging from {temp_img_dir}...")
        
        # 2. Save JSON to output (to be picked up by ZIP)
        json_filename = f"polished_ent_{timestamp_str}.json"
        json_path = os.path.join(OUTPUT_DIR, json_filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(polished_data, f, ensure_ascii=False, indent=4)
            
        # 3. Create ZIP
        zip_name = f"Entertainment_{timestamp_str}.zip"
        zip_path = os.path.join(OUTPUT_DIR, zip_name)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add JSON inside ZIP with standard name
            zf.write(json_path, arcname=f"polished_all_{timestamp_str}.json")
            
            # Add images from the temp directory provided by aggregator
            if os.path.exists(temp_img_dir):
                for root, _, files in os.walk(temp_img_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        # Images in zip should be in images/ folder
                        zf.write(abs_path, arcname=f"images/{file}")
        
        print(f"  ✓ Created {zip_name}")
        update_latest_version("entertainment", zip_name)
        
        # 4. Cleanup temp image dir
        if os.path.exists(temp_img_dir):
            shutil.rmtree(temp_img_dir)

    except Exception as e:
        print(f"Error in Entertainment News Pipeline: {e}")
        import traceback
        traceback.print_exc()

def cleanup(keep_count):
    print("\n--- Cleaning up ---")
    prefixes = ["Home_", "World_", "Entertainment_"]
    
    for prefix in prefixes:
        files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(prefix) and f.endswith(".zip")]
        files.sort(reverse=True)
        
        to_remove = files[keep_count:]
        for f in to_remove:
            try:
                os.remove(os.path.join(OUTPUT_DIR, f))
                print(f"  Deleted {f}")
            except Exception as e:
                print(f"Error deleting {f}: {e}")

def cleanup_intermediate_dirs():
    print("\n--- Cleaning up intermediate directories and loose files ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Directories in crawler/ root or current working dir
    dirs_to_remove = [
        "bbc_news_data", "cnn_data", "nytimes_data", "sky_news_data", 
        "SampleNewsG", "RawData_Backup", "tencent_ent_hot", "tencent", "images",
        os.path.join(OUTPUT_DIR, "images")
    ]
    
    for d in dirs_to_remove:
        path = d if os.path.isabs(d) else os.path.join(base_dir, d)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"  Deleted intermediate dir: {path}")
            except Exception as e:
                print(f"  Error deleting {path}: {e}")

    # Delete all polished_*.json files in output (they are inside ZIPs now)
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.startswith("polished_") and f.endswith(".json"):
                try:
                    os.remove(os.path.join(OUTPUT_DIR, f))
                    print(f"  Deleted loose JSON: {f}")
                except Exception as e:
                    print(f"  Error deleting {f}: {e}")

def main():
    ensure_dirs()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"Global Timestamp: {timestamp}")
    
    run_home_news(timestamp)
    run_world_news(timestamp)
    run_entertainment_news(timestamp)
    
    cleanup(KEEP_COUNT)
    cleanup_intermediate_dirs()

if __name__ == "__main__":
    main()