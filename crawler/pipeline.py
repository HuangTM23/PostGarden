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

# --- Configuration ---
OUTPUT_DIR = "output"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
NEWS_LIMIT_PER_PLATFORM = 9

def download_image(url, local_path):
    """Downloads an image from a URL to a local path."""
    if not url or not url.startswith('http'):
        return False
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  Failed to download image {url}: {e}")
        return False

def run_pipeline(report_type):
    """
    Main pipeline to fetch, process, and save news.
    :param report_type: 'morning' or 'evening'
    """
    print("="*60)
    print(f"🚀 Starting '{report_type}' news pipeline...")
    print("="*60)

    # 1. Setup output directories
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # 2. Fetch raw news from all platforms
    all_raw_news = []
    all_raw_news.extend(fetch_baidu.main(limit=NEWS_LIMIT_PER_PLATFORM))
    all_raw_news.extend(fetch_toutiao.main(limit=NEWS_LIMIT_PER_PLATFORM))
    all_raw_news.extend(fetch_tencent.main(report_type=report_type, limit=NEWS_LIMIT_PER_PLATFORM))

    if not all_raw_news:
        print("❌ No news items fetched. Aborting pipeline.")
        return

    print(f"\n✅ Total raw news items fetched: {len(all_raw_news)}")

    # 3. Polish news with AI
    polished_data = polish.main(all_raw_news)

    if not polished_data or "news" not in polished_data:
        print("❌ AI polishing failed or returned invalid format. Aborting pipeline.")
        return
    
    polished_items = polished_data["news"]
    print(f"\n✅ AI polishing complete. Got {len(polished_items)} final items.")

    # 4. Download images for polished items and update paths
    print("\n⏳ Downloading images for polished news...")
    timestamp = datetime.now().strftime('%Y%m%d')
    for item in polished_items:
        if item.get("rank", 0) == 0: continue # Skip summary item

        remote_image_url = item.get("image")
        if remote_image_url:
            # Create a unique, clean filename
            ext = os.path.splitext(remote_image_url.split('?')[0])[-1] or ".jpg"
            if len(ext) > 5: ext = '.jpg' # Handle invalid extensions
            
            # e.g., images/rank1_Baidu_20240101.jpg
            filename = f"rank{item['rank']}_{item.get('source_platform', 'X')}_{timestamp}{ext}"
            local_image_path = os.path.join(IMAGES_DIR, filename)
            
            if download_image(remote_image_url, local_image_path):
                # Update the image path to be a relative path for GitHub Pages
                item["image"] = f"images/{filename}"
                print(f"  ✓ Image downloaded for Rank {item['rank']}")
            else:
                item["image"] = "" # Clear image if download fails
        else:
            item["image"] = ""

    # 5. Save final JSON to output directory
    output_json_path = os.path.join(OUTPUT_DIR, f"{report_type}.json")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(polished_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Final {report_type}.json saved to {output_json_path}")
    print("\n" + "="*60)
    print("🏆 Pipeline finished successfully!")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['morning', 'evening']:
        print("Usage: python pipeline.py [morning|evening]")
        sys.exit(1)
    
    pipeline_type = sys.argv[1]
    run_pipeline(pipeline_type)
