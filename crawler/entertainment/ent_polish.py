#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合娱乐新闻聚合器
包含平台抓取、AI筛选和内容聚合功能
"""

import json
import sys
import argparse
import time
import os
import requests
import shutil
from datetime import datetime, timedelta

# Import the three scraper modules
try:
    from .get_tencent_entertainment_hot import get_tencent_entertainment_hot
    from .get_douyin_rank import get_douyin_rank
    from .get_bilibili_rank import get_bilibili_rank
except ImportError:
    from get_tencent_entertainment_hot import get_tencent_entertainment_hot
    from get_douyin_rank import get_douyin_rank
    from get_bilibili_rank import get_bilibili_rank

# 配置
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "entertainment_history.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

def clean_output_dir():
    """清空输出目录"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        print(f"  已清空输出目录：{OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR)

def load_history():
    """加载历史库"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
            return history if isinstance(history, list) else []
    except:
        return []

def save_history(new_items):
    """保存历史库，最多保留36条"""
    history = load_history()
    
    # 添加新项目（每次添加9条）
    for item in new_items:
        history.append({
            "title": item.get('title', ''),
            "content": item.get('content', ''),
            "source_platform": item.get('source_platform', ''),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # 只保留最新的36条（4*9=36）
    initial_count = len(history)
    if len(history) > 36:
        history = history[-36:]
        deleted_count = initial_count - 36
        print(f"  历史库已更新：保留最新36条，删除早期{deleted_count}条")
    else:
        print(f"  历史库已更新：当前{len(history)}条")
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def save_aggregated_news(polished_data):
    """保存聚合的新闻JSON文件"""
    timestamp = polished_data.get('timestamp', '')
    filename = f"{OUTPUT_DIR}/entertainment_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(polished_data, f, ensure_ascii=False, indent=2)
    
    print(f"  [✓] 聚合数据已保存至：{filename}")
    return filename

def generate_clickbait_title(selected_news):
    """生成刺激性、爆炸性的摘要标题"""
    if not selected_news:
        beijing_time = datetime.utcnow() + timedelta(hours=8)
        return f"娱乐资讯精选 | {beijing_time.strftime('%m月%d日')}热点"
    
    # 提取关键词和明星名字
    keywords = []
    for item in selected_news[:5]:
        title = item.get('title', '')
        # 简单的关键词提取
        if '恋爱' in title or '婚礼' in title or '官宣' in title:
            keywords.append('感情八卦')
        if '分手' in title or '离婚' in title or '出轨' in title:
            keywords.append('婚变风波')
        if '争议' in title or '被骂' in title or '翻车' in title:
            keywords.append('明星风波')
        if '新剧' in title or '开播' in title or '上映' in title:
            keywords.append('作品热议')
        if '音乐' in title or '演唱会' in title:
            keywords.append('音乐盛事')
    
    beijing_time = datetime.utcnow() + timedelta(hours=8)
    date_str = beijing_time.strftime('%m月%d日')
    
    # 刺激性标题模板库
    titles = [
        f"【炸裂】{date_str}娱乐圈又闹翻天！这些大瓜你绝对想不到",
        f"【震撼】明星们的秘密在这里！{date_str}最火爆内幕大揭露",
        f"【爆料】{date_str}娱乐圈黑幕重重，这些事儿你可能永远都不知道",
        f"【独家】{date_str}最热议话题全在这！网友吵翻天的剧情",
        f"【反转】{date_str}一天内发生的娱乐圈大事，让人措手不及",
        f"【必看】这个{date_str}，娱乐圈的瓜大到停不下来！",
        f"【争议】{date_str}最具话题性新闻，有人欢喜有人忧",
        f"【曝光】{date_str}娱乐圈隐瞒的故事，今天全部浮出水面",
        f"【热议】{date_str}网友疯狂讨论的话题，究竟是什么真相？",
        f"【轰动】{date_str}娱乐圈再起风波，众明星或被卷入其中",
    ]
    
    # 根据关键词选择最合适的标题
    if '婚变风波' in keywords:
        titles = [
            f"【婚变】{date_str}娱乐圈感情线又崩了！多位明星卷入感情风波",
            f"【爆炸】{date_str}一连串分手官宣震撼娱乐圈，粉丝集体崩溃",
            f"【反转】感情故事反复无常，{date_str}明星爱情线谜团重重",
        ]
    elif '明星风波' in keywords:
        titles = [
            f"【翻车】{date_str}多位明星陷争议，网友讨伐声不断",
            f"【风波】{date_str}明星言行不当引众怒，舆论一边倒",
            f"【热议】{date_str}明星们的过往被扒出来，网友吵得不可开交",
        ]
    
    # 随机选择一个标题（使用内容长度作为伪随机）
    title_index = len(selected_news) % len(titles)
    return titles[title_index]

def deduplicate_with_deepseek(all_news, history_items):
    """使用DeepSeek API进行智能去重"""
    if not DEEPSEEK_API_KEY:
        print("  [!] 未设置DEEPSEEK_API_KEY，使用本地去重")
        return deduplicate_locally(all_news, history_items)
    
    print("  正在使用DeepSeek进行智能去重...")
    
    # 准备提示词
    history_titles = [item['title'] for item in history_items]
    all_titles = [f"{i+1}. {item['title']}" for i, item in enumerate(all_news)]
    
    prompt = f"""
你是一个内容去重专家。请从以下最新的娱乐新闻列表中选择9个与历史记录无关且互相不重复的新闻。

【历史记录】（需要避免重复的内容）：
{chr(10).join(history_titles)}

【最新新闻列表】：
{chr(10).join(all_titles)}

请按照以下要求：
1. 选出9条与历史记录完全不同的新闻
2. 这9条新闻之间也应该互不重复
3. 优先选择不同来源的新闻
4. 返回结果格式为JSON，包含selected_indices字段，值为选中的新闻索引（从0开始），例如：{{"selected_indices": [0, 2, 5, 7, 9, 10, 12, 15, 18]}}

只返回JSON，不要有其他文字。
"""
    
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析JSON响应
            selected_data = json.loads(content)
            indices = selected_data.get('selected_indices', [])
            
            # 过滤选中的新闻
            selected_news = [all_news[i] for i in indices if i < len(all_news)]
            selected_news = selected_news[:9]
            
            print(f"  [✓] DeepSeek去重完成，选出 {len(selected_news)} 条新闻")
            return selected_news
        else:
            print(f"  [!] DeepSeek API返回错误: {response.status_code}")
            return deduplicate_locally(all_news, history_items)
            
    except Exception as e:
        print(f"  [!] DeepSeek调用失败: {e}")
        return deduplicate_locally(all_news, history_items)

def deduplicate_locally(all_news, history_items):
    """本地智能去重"""
    print("  正在进行本地去重...")
    
    history_titles = set(item['title'] for item in history_items)
    titles_set = set()
    selected_items = []

    def is_political_or_military(title):
        """检查是否为政治或军事相关内容"""
        political_keywords = ['政治', '政府', '官员', '政策', '军', '军队', '军事', '战争', '外交', '选举', '党', '纪委', '监察', '人大', '政协', '国家', '领导', '主席', '总理', '政治局', '中央', '法院', '检察院', '公安', '警察', '武警', '部队', '国防', '导弹', '核武器', '联合国', '投票', '政党', '议会', '国会', '立法', '司法', '行政', '公务员', '国企', '央企', '国资委', '发改委', '财政部', '央行', '货币政策', '财政政策', '经济政策', '贸易战', '制裁', '地缘', '冲突', '动乱', '暴乱', '抗议', '示威', '游行', '罢工', '罢课', '罢市', '弹劾', '问责', '调查', '审查', '审计', '监督', '举报', '控告', '起诉', '审判', '判决', '拘留', '逮捕', '审讯']
        return any(keyword in title for keyword in political_keywords)

    # 优先保证每个平台的代表
    tencent_news = [item for item in all_news if item.get('source_platform') == '腾讯娱乐']
    douyin_news = [item for item in all_news if item.get('source_platform') == '抖音热榜']
    bilibili_news = [item for item in all_news if item.get('source_platform') == 'Bilibili' or item.get('source_platform') == '哔哩哔哩']

    def add_if_valid(source_list, max_count):
        added = 0
        for item in source_list:
            if added >= max_count:
                break
            title = item.get('title', '')
            
            if not title or len(title) < 2:
                continue
            if is_political_or_military(title):
                continue
            if title in history_titles:  # 跟历史库去重
                continue
            if title in titles_set:  # 跟当前选择去重
                continue
            
            titles_set.add(title)
            selected_items.append(item)
            added += 1

    add_if_valid(tencent_news, 3)
    add_if_valid(douyin_news, 3)
    add_if_valid(bilibili_news, 3)
    
    # 补充不足的部分
    all_others = [i for i in all_news if i.get('title') not in titles_set and i.get('title') not in history_titles]
    add_if_valid(all_others, 9 - len(selected_items))

    selected_items = selected_items[:9]
    return selected_items

def aggregate_news(count=9):
    """聚合三个平台的娱乐新闻"""
    print("\n" + "="*30)
    print("🚀 [Entertainment] 开始聚合流程")
    print("="*30)
    
    # 清空输出目录
    print("  正在清理输出目录...")
    clean_output_dir()
    
    # 加载历史库
    history_items = load_history()
    print(f"  加载历史库：{len(history_items)} 条")
    
    # 调用三个脚本获取数据
    tencent_data = get_tencent_entertainment_hot(count)
    douyin_data = get_douyin_rank(count)
    bilibili_data = get_bilibili_rank(count)

    all_news = []
    
    # 处理腾讯数据
    if tencent_data:
        for item in tencent_data:
            all_news.append({
                'rank': item.get('rank', 0),
                'title': item.get('title', ''),
                'title0': item.get('title0', ''),
                'content': item.get('content', ''),
                'index': item.get('index', 0),
                'author': item.get('author', ''),
                'source_platform': item.get('source_platform', ''),
                'source_url': item.get('source_url', ''),
                'image': item.get('image', '')
            })

    # 处理抖音数据
    if douyin_data:
        for item in douyin_data:
            all_news.append({
                'rank': item.get('rank', 0),
                'title': item.get('title', ''),
                'title0': item.get('title0', ''),
                'content': item.get('content', ''),
                'index': item.get('index', 0),
                'author': item.get('author', ''),
                'source_platform': item.get('source_platform', ''),
                'source_url': item.get('source_url', ''),
                'image': item.get('image', '')
            })

    # 处理哔哩哔哩数据
    if bilibili_data:
        for item in bilibili_data:
            all_news.append({
                'rank': item.get('rank', 0),
                'title': item.get('title', ''),
                'title0': item.get('title0', ''),
                'content': item.get('content', ''),
                'index': item.get('index', 0),
                'author': item.get('author', ''),
                'source_platform': item.get('source_platform', ''),
                'source_url': item.get('source_url', ''),
                'image': item.get('image', '')
            })

    print(f"  抓取完成：共 {len(all_news)} 条新闻")

    # 使用DeepSeek或本地去重
    selected_news = deduplicate_with_deepseek(all_news, history_items)

    # 生成刺激性摘要标题
    summary_title = generate_clickbait_title(selected_news)

    # 构建最终结果：1个摘要 + 9条新闻
    final_result = []
    
    # 添加摘要（rank=0，所有字段都存在但除title外都为空）
    summary_item = {
        "rank": 0,
        "title": summary_title,
        "title0": "",
        "content": "",
        "index": 0,
        "author": "",
        "source_platform": "",
        "source_url": "",
        "image": ""
    }
    final_result.append(summary_item)

    # 添加9条新闻（rank从1-9）
    for i, news_item in enumerate(selected_news, 1):
        processed_item = {
            "rank": i,
            "title": news_item.get('title', ''),
            "title0": news_item.get('title0', ''),
            "content": news_item.get('content', ''),
            "index": news_item.get('index', 0),
            "author": news_item.get('author', ''),
            "source_platform": news_item.get('source_platform', ''),
            "source_url": news_item.get('source_url', ''),
            "image": news_item.get('image', '')
        }
        final_result.append(processed_item)

    beijing_time = datetime.utcnow() + timedelta(hours=8)
    polished_data = {
        "news": final_result,
        "timestamp": beijing_time.strftime("%Y%m%d_%H%M%S"),
        "total": len(final_result)
    }
    
    print(f"  [✓] 娱乐新闻聚合完成，共 {len(final_result)} 条（1个摘要+9条新闻）。")
    
    # 保存聚合的新闻JSON文件
    save_aggregated_news(polished_data)
    
    # 更新历史库
    print("  正在更新历史库...")
    save_history(selected_news)
    
    return polished_data

def main():
    parser = argparse.ArgumentParser(description='综合娱乐新闻聚合器')
    parser.add_argument('--count', type=int, default=9, help='每个平台抓取数量（默认9）')
    args = parser.parse_args()

    data = aggregate_news(args.count)
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()