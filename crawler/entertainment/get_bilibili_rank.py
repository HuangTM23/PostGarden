import requests
import json

def fetch_rank_data(retries=3):
    """抓取B站热榜数据"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/v/popular/rank/all'
    }
    
    for attempt in range(retries):
        try:
            urls = [
                'https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all',
                'https://api.bilibili.com/x/web-interface/ranking?rid=0&type=all'
            ]
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    return response.json()
                except:
                    continue
        except Exception as e:
            pass
    return None

def get_bilibili_rank(count=9):
    """
    抓取Bilibili热榜
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Bilibili] 开始抓取热榜...")
    
    raw_data = fetch_rank_data()
    if not raw_data or raw_data.get('code') != 0:
        print("[Bilibili] ✗ 未获取到热榜数据")
        return []

    items = raw_data.get('data', {}).get('list', [])[:count]
    print(f"[Bilibili] ✓ 获取{len(items)}条候选热榜")
    
    processed_list = []

    for index, item in enumerate(items):
        print(f"\n[Bilibili] 处理第{index+1}/{len(items)}条:")
        
        title = item.get('title', '')
        if not title or len(title) < 2:
            print(f"  ✗ 标题无效，跳过")
            continue

        print(f"  标题: {title}")

        bvid = item.get('bvid', '')
        video_link = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
        
        print(f"  链接: {video_link[:60]}..." if len(video_link) > 60 else f"  链接: {video_link}")

        author_name = item.get('owner', {}).get('name', '')
        print(f"  作者: {author_name}")

        cover_image = item.get('pic', '')
        if cover_image:
            print(f"  图片: {cover_image[:50]}...")

        view_count = item.get('stat', {}).get('view', 0)
        reply_count = item.get('stat', {}).get('reply', 0)

        processed_item = {
            "rank": len(processed_list) + 1,
            "title": title,
            "title0": "",  # 娱乐新闻无英文标题
            "content": title,
            "index": view_count,  # 使用播放量作为热度指数
            "author": "bilibili",
            "source_platform": author_name or "Bilibili",
            "source_url": video_link,
            "image": cover_image
        }
        processed_list.append(processed_item)
        print(f"  ✓ 第{len(processed_list)}条新闻已保存")

    print(f"\n[Bilibili] ✓ 抓取完成，共{len(processed_list)}条新闻\n")
    return processed_list

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    result = get_bilibili_rank(count)
    print(json.dumps(result, ensure_ascii=False, indent=2))