import requests
import json
import csv
import os

def fetch_rank_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.douyin.com/hot',
        'Cookie': 's_v_web_id=verify_ley4g474_KV2s6Q1F_8jF8_4r6G_8jF8_8jF88jF88jF8;' # Helper cookie
    }
    # Using the API endpoint we found
    url = 'https://www.douyin.com/aweme/v1/web/hot/search/list/'

    print(f"Fetching data from {url}...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def process_and_save(raw_data):
    if not raw_data or not raw_data.get('data'):
        print("Invalid data received.")
        return

    # Douyin's structure: data -> word_list
    items = raw_data.get('data', {}).get('word_list', [])

    processed_list = []
    for index, item in enumerate(items):
        rank = index + 1
        title = item.get('word', '')
        # Douyin hot list is topics, not specific authors usually.
        # Sometimes there is associated video info but it's nested or missing.
        author = "Douyin Hot Topic"

        # 'hot_value' is the metric for hotness
        view_count = item.get('hot_value', 0)

        # Comment count is not directly available for the topic itself in this view
        comment_count = 0

        # Cover image
        cover_image = ""
        if item.get('word_cover') and item.get('word_cover').get('url_list'):
            cover_image = item.get('word_cover').get('url_list')[0]

        sentence_id = item.get('sentence_id', '')
        # Construct link to the hot topic page
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

    # Save as JSON
    json_output_file = 'douyin_rank.json'
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved {len(processed_list)} items to {json_output_file}")

    # Save as CSV
    csv_output_file = 'douyin_rank.csv'
    if processed_list:
        headers = processed_list[0].keys()
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(processed_list)
        print(f"Successfully saved {len(processed_list)} items to {csv_output_file}")

def get_douyin_rank():
    data = fetch_rank_data()
    process_and_save(data)

if __name__ == "__main__":
    get_douyin_rank()