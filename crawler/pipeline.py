import os
import json
import sys
import shutil
import requests
from datetime import datetime

# Add crawler directory to path to import other modules
sys.path.append(os.path.dirname(__file__))

import fetch_baidu
import fetch_toutiao
import fetch_tencent
import polish

import zipfile

# --- Configuration ---
OUTPUT_DIR = "output"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
NEWS_LIMIT_PER_PLATFORM = 9

def download_image(url, local_path):
    """Downloads an image from a URL to a local path."""
    if not url or not url.startswith('http'):
        return False, "Invalid URL"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.qq.com/" # Use a common referer
    }

    try:
        response = requests.get(url, stream=True, timeout=15, headers=headers)
        response.raise_for_status()
        
        # Check if content is actually an image
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type and not url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            return False, f"Non-image content type: {content_type}"

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Minimum size check (skip tiny icons/placeholders)
        file_size = os.path.getsize(local_path)
        if file_size < 3072: # 3KB
            os.remove(local_path)
            return False, f"File too small ({file_size} bytes)"
            
        return True, "Success"
    except Exception as e:
        return False, str(e)

def run_pipeline(report_type):
    """
    Main pipeline to fetch, process, and save news.
    :param report_type: 'morning' or 'evening'
    """
    print("\n" + "█"*60)
    print(f"  POSTGARDEN PIPELINE: {report_type.upper()}")
    print("█"*60)

    # 1. Setup output directories
    print(f"\n[Step 1/6] Preparing environment...")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"  ✓ Output directory: {OUTPUT_DIR}")

    # 2. Fetch raw news from all platforms
    print(f"\n[Step 2/6] Fetching raw news from platforms...")
    all_raw_news = []
    
    try:
        baidu_news = fetch_baidu.main(limit=NEWS_LIMIT_PER_PLATFORM)
        all_raw_news.extend(baidu_news)
        print(f"  ✓ Baidu: {len(baidu_news)} items")
    except Exception as e:
        print(f"  ✗ Baidu failed: {e}")

    try:
        toutiao_news = fetch_toutiao.main(limit=NEWS_LIMIT_PER_PLATFORM)
        all_raw_news.extend(toutiao_news)
        print(f"  ✓ Toutiao: {len(toutiao_news)} items")
    except Exception as e:
        print(f"  ✗ Toutiao failed: {e}")

    try:
        tencent_news = fetch_tencent.main(report_type=report_type, limit=NEWS_LIMIT_PER_PLATFORM)
        all_raw_news.extend(tencent_news)
        print(f"  ✓ Tencent: {len(tencent_news)} items")
    except Exception as e:
        print(f"  ✗ Tencent failed: {e}")

    if not all_raw_news:
        print("\n❌ CRITICAL: No news items fetched from any platform. Aborting.")
        return

    print(f"\n✅ Total news items collected: {len(all_raw_news)}")

    # 3. Polish news with AI
    print(f"\n[Step 3/6] Polishing and filtering news with AI...")
    polished_data = polish.main(all_raw_news)

    if not polished_data or "news" not in polished_data:
        print("❌ CRITICAL: AI polishing failed. Aborting.")
        return
    
    polished_items = polished_data["news"]
    
    # Define unified timestamp for this run (Polished Time)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    polished_data["timestamp"] = timestamp_str  # Inject into JSON

    # 4. Download images for polished items and update paths
    print(f"\n[Step 4/6] Downloading images for selected items...")
    download_count = 0
    for item in polished_items:
        if item.get("rank", 0) == 0: continue # Skip summary item

        remote_image_url = item.get("image")
        if remote_image_url and remote_image_url.startswith('http'):
            # Sanitize title for filename (use first 4 chars of title as prefix)
            title = item.get('title', 'NoTitle')
            raw_prefix = title[:4]
            # FS safe: replace / \ : * ? " < > |
            safe_prefix = "".join([c if c not in r'/\:*?"<>|' else '_' for c in raw_prefix])
            if not safe_prefix: safe_prefix = "Img"

            ext = os.path.splitext(remote_image_url.split('?')[0])[-1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
                ext = '.jpg'
            
            # Format: rank{N}_{Prefix}_{Timestamp}.{ext}
            filename = f"rank{item['rank']}_{safe_prefix}_{timestamp_str}{ext}"
            local_image_path = os.path.join(IMAGES_DIR, filename)
            
            success, reason = download_image(remote_image_url, local_image_path)
            if success:
                item["image"] = f"images/{filename}"
                download_count += 1
                print(f"  ✓ Rank {item['rank']} [{safe_prefix}] image downloaded.")
            else:
                item["image"] = ""
                print(f"  ✗ Rank {item['rank']} [{safe_prefix}] image failed: {reason} (URL: {remote_image_url})")
        else:
            item["image"] = ""
            print(f"  - Rank {item['rank']} image skipped (No valid URL or not http-prefixed)")
    
    print(f"\n  ✓ Successfully downloaded {download_count} images.")

    # 5. Save final JSON to output directory
    print(f"\n[Step 5/6] Saving final report...")
    new_json_name = f"polished_all_{timestamp_str}.json"
    output_json_path = os.path.join(OUTPUT_DIR, new_json_name)
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(polished_data, f, ensure_ascii=False, indent=4)
    
    # Also keep a legacy copy for the App's direct JSON fetch
    legacy_json_path = os.path.join(OUTPUT_DIR, f"{report_type}.json")
    shutil.copy2(output_json_path, legacy_json_path)
    
    print(f"  ✓ {new_json_name} created.")
    print(f"  ✓ Legacy {report_type}.json updated.")

    # 6. Create ZIP archive
    print(f"\n[Step 6/6] Packaging for distribution...")
    create_zip_archive_v2(report_type, output_json_path, timestamp_str)

    print("\n" + "█"*60)
    print("  🏆 PIPELINE COMPLETE!")
    print("█"*60 + "\n")

def create_zip_archive_v2(report_type, json_path, timestamp):
    """
    Improved zip creation using the already generated polished_all_...json.
    """
    new_json_name = os.path.basename(json_path)
    new_zip_name = f"SampleNews_{timestamp}.zip"
    legacy_zip_name = f"{report_type}_report.zip"
    
    zip_path = os.path.join(OUTPUT_DIR, new_zip_name)
    legacy_zip_path = os.path.join(OUTPUT_DIR, legacy_zip_name)

    print(f"  Creating ZIP archive at {zip_path}...")
    try:
        # 1. Clean up legacy zip to ensure fresh overwrite
        if os.path.exists(legacy_zip_path):
            os.remove(legacy_zip_path)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 2. Add the JSON file with the EXACT new name
            zf.write(json_path, arcname=new_json_name)
            
            # 3. Add images
            for item in data.get("news", []):
                relative_image_path = item.get("image")
                if relative_image_path:
                    full_image_path = os.path.join(OUTPUT_DIR, relative_image_path)
                    if os.path.exists(full_image_path):
                        zf.write(full_image_path, arcname=relative_image_path)
        
        # 4. Copy to legacy name
        shutil.copy2(zip_path, legacy_zip_path)
        print(f"  ✓ ZIP created: {new_zip_name}")
        print(f"  ✓ Inside ZIP: {new_json_name}")
    except Exception as e:
        print(f"  ✗ Failed to create ZIP archive: {e}")

if __name__ == "__main__":
    # Default based on current hour
    current_hour = datetime.now().hour
    pipeline_type = "morning" if current_hour < 12 else "evening"
    
    # Optional override via command line
    if len(sys.argv) >= 2 and sys.argv[1] in ['morning', 'evening']:
        pipeline_type = sys.argv[1]
    
    run_pipeline(pipeline_type)
