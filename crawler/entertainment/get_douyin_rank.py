import requests
import json

def fetch_rank_data(retries=3):
    """抓取抖音热榜数据"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.douyin.com/hot',
        'Accept': 'application/json, text/plain, */*',
    }
    url = 'https://www.douyin.com/aweme/v1/web/hot/search/list/'

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"  [!] 第 {attempt+1} 次抓取失败: {e}")
    return None

def get_douyin_rank(count=9):
    """
    抓取抖音热榜
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Douyin] 开始抓取热榜...")
    
    raw_data = fetch_rank_data()
    if not raw_data or not raw_data.get('data'):
        print("[Douyin] ✗ 未获取到热榜数据")
        return []

    items = raw_data.get('data', {}).get('word_list', [])[:count]
    print(f"[Douyin] ✓ 获取{len(items)}条候选热榜")
    
    processed_list = []

    for index, item in enumerate(items):
        print(f"\n[Douyin] 处理第{index+1}/{len(items)}条:")
        
        title = item.get('word', '')
        if not title or len(title) < 2:
            print(f"  ✗ 标题无效，跳过")
            continue

        print(f"  标题: {title}")

        sentence_id = item.get('sentence_id', '')
        video_link = f"https://www.douyin.com/hot/{sentence_id}" if sentence_id else f"https://www.douyin.com/search/{title}"
        
        print(f"  链接: {video_link[:60]}..." if len(video_link) > 60 else f"  链接: {video_link}")

        cover_image = ""
        if item.get('word_cover') and item.get('word_cover').get('url_list'):
            cover_image = item.get('word_cover').get('url_list')[0]
            if cover_image:
                print(f"  图片: {cover_image[:50]}...")

        hot_value = item.get('hot_value', 0)

        processed_item = {
            "rank": len(processed_list) + 1,
            "title": title,
            "title0": "",  # 娱乐新闻无英文标题
            "content": title,
            "index": hot_value,
            "author": "douyin",
            "source_platform": "抖音热榜",
            "source_url": video_link,
            "image": cover_image
        }
        processed_list.append(processed_item)
        print(f"  ✓ 第{len(processed_list)}条新闻已保存")

    print(f"\n[Douyin] ✓ 抓取完成，共{len(processed_list)}条新闻\n")
    return processed_list

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    result = get_douyin_rank(count)
    print(json.dumps(result, ensure_ascii=False, indent=2))