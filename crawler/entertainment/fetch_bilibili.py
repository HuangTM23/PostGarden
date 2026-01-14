"""
Bilibili Hot Search Scraper
抓取 Bilibili 热搜视频
"""
import requests
import time
import os

# Constants
API_URL = "https://api.bilibili.com/x/web-interface/popular?ps=50"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_bilibili_news(count: int = 9) -> list:
    """
    抓取B站热搜新闻
    :param count: 返回数量
    :return: JSON格式的列表
    """
    print("[Bilibili] 开始抓取热搜视频...")
    
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        items = data.get("data", {}).get("list", [])
        
        if not items:
            print("[Bilibili] ✗ 未获取到任何数据")
            return []
        
        print(f"[Bilibili] ✓ 获取{len(items)}条候选视频")
        results = []
        
        for idx, item in enumerate(items, 1):
            if len(results) >= count:
                break
            
            title = item.get("title", "")
            bvid = item.get("bvid", "")
            
            if not title or not bvid:
                continue
            
            # 使用 "B站热搜" 作为 source_platform
            print(f"\n[Bilibili] 处理第{len(results)+1}/{count}条:")
            print(f"  标题: {title}")
            print(f"  来源: B站热搜")
            
            video_url = f"https://www.bilibili.com/video/{bvid}"
            cover_url = item.get("pic", "")
            
            # 确保图片URL完整
            if cover_url and not cover_url.startswith('http'):
                if cover_url.startswith('//'):
                    cover_url = 'https:' + cover_url
            
            results.append({
                "rank": len(results) + 1,
                "title": title,
                "title0": "",
                "content": title,
                "index": item.get("hot_score", 0),
                "author": "bilibili",
                "source_platform": "B站热搜",  # 修改为固定的 "B站热搜"
                "source_url": video_url,
                "image": cover_url
            })
            print(f"  ✓ 第{len(results)}条视频已保存")
            
            time.sleep(0.3)
        
        print(f"\n[Bilibili] ✓ 抓取完成，共{len(results)}条视频\n")
        return results
        
    except Exception as e:
        print(f"[Bilibili] ✗ 抓取失败: {type(e).__name__}")
        return []