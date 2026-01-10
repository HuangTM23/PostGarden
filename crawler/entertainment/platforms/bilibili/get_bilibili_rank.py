import requests
import json
import csv
import os

def fetch_rank_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com/v/popular/rank/all'
    }
    url = 'https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all'

    print(f"Fetching data from {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def process_and_save(raw_data):
    if not raw_data or raw_data.get('code') != 0:
        print(f"Invalid data received: {raw_data.get('message') if raw_data else 'None'}")
        return

    items = raw_data.get('data', {}).get('list', [])

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

    # Save as JSON
    json_output_file = 'bilibili_rank.json'
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved {len(processed_list)} items to {json_output_file}")

    # Save as CSV
    csv_output_file = 'bilibili_rank.csv'
    if processed_list:
        headers = processed_list[0].keys()
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(processed_list)
        print(f"Successfully saved {len(processed_list)} items to {csv_output_file}")

def get_bilibili_rank():
    data = fetch_rank_data()
    process_and_save(data)

if __name__ == "__main__":
    get_bilibili_rank()