# Renamed from polish_v3.py
import os
import json
import time
import requests
import shutil
import argparse
from datetime import datetime, timedelta

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"
# 修复：使用绝对路径指向当前目录的历史文件
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "homenews_history.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

SYSTEM_PROMPT = """你是一名专业中文新闻编辑与内容策划人员，负责从多个新闻平台的抓取结果中，进行事件级去重、筛选、专业简化与内容整合，生成一组适合发布在微信公众号与小红书的新闻精选内容。

核心目标是：从"最新抓取新闻"中，通过"事件级去重 + 内容筛选"，直接选出 9 条"完全不同新闻事件"的新闻。

【重要：历史排重参考】
以下是过去发布过的新闻（History），请严格回避与这些历史内容重复或高度相似的事件（即不要选旧闻）：
{history_context_str}

⚠️ 强制过滤规则 (Negative Filter) - 优先级最高
必须剔除所有涉及以下领域的新闻:
1. 政治 (Politics)
2. 军事 (Military)
3. 台湾 (Taiwan)

保留的新闻应侧重于：科技与商业、民生与社会热点、文化与娱乐、体育、奇闻轶事。

写作要求：
- 使用专业、正式的新闻体。
- 每条新闻正文：不超过 50 个汉字，只保留"发生了什么 + 关键结果"。
- 单条新闻标题：不超过 20 个汉字。

**Rank 0 总结标题（核心任务）**：
你是一名资深中文网络媒体编辑，擅长从大量热点新闻中提炼高度吸引眼球但不造谣、不歪曲事实的标题。

任务目标：
生成一个总结性热点标题，用于 Rank 0 位置。

强制要求：
- 标题风格允许“标题党”，追求点击率与传播力，但不得虚构事实、不得造谣、不得引入原文未出现的结论；
- **标题不超过 10 个汉字（含标点）**，优先使用短句、冲突、反转、情绪张力；
- 不要求全面概括所有信息，可以：
    - 抓住最具传播性的一个侧面；
    - 或在已有新闻标题基础上进行高度润色与压缩；
    - 或借鉴常见网络爆款标题结构（如“突然”“炸锅”“定了”“彻底”“没想到”等），但不得失真；

数据完整性要求：
- 对于选中的每条新闻，必须保留其原始的 `source_platform`, `source_url`, `source` 和 `image` 字段。
- `image` 字段必须原样复制，不要修改链接地址。
- `source` 字段表示来源平台（baidu/tencent/toutiao），必须保留。

输出格式要求（必须严格遵守）
你必须输出一个包含 "news" 字段的 JSON 对象。
"news" 字段是一个列表，必须严格包含 10 条数据（Rank 0 为总结 + Rank 1-9 为 9 条精选新闻）。

{{
  "news": [
    {{ 
      "rank": 0, 
      "title": "爆炸性疑问标题？", 
      "content": "",
      "source_platform": "",
      "source_url": "",
      "source": "",
      "image": "" 
    }},
    {{ 
      "rank": 1, 
      "title": "新闻1标题", 
      "content": "新闻1正文...", 
      "source_platform": "来源平台名称", 
      "source_url": "原始文章链接", 
      "source": "baidu",
      "image": "原始图片链接(必须保留)" 
    }},
    {{ 
      "rank": 2, 
      "title": "新闻2标题", 
      "content": "新闻2正文...", 
      "source_platform": "来源平台名称", 
      "source_url": "原始文章链接", 
      "source": "tencent",
      "image": "原始图片链接" 
    }},
    ...
    {{ "rank": 9, ... }}
  ]
}}

注意：Rank 0 的 title 必须以问号（?）结尾。
注意：Rank 0 的 content、source_platform、source_url、source、image 字段均留空。
Rank 1-9 的所有字段都必须填充完整。
"""

def clean_output_dir():
    """清空输出目录"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

def load_history():
    """加载历史库"""
    if not os.path.exists(HISTORY_FILE):
        print(f"  [*] 历史文件不存在，路径: {HISTORY_FILE}")
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
            return history if isinstance(history, list) else []
    except Exception as e:
        print(f"  [!] 历史文件读取失败: {e}")
        return []

def save_history(news_list):
    """保存历史库，最多保留36条"""
    history = load_history()
    
    # 添加新项目（rank 1-9）
    for item in news_list:
        if item.get('rank', 0) > 0:  # 跳过rank 0的摘要
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

def save_polished_news(polished_data):
    """保存润色后的新闻JSON文件"""
    timestamp = polished_data.get('timestamp', '')
    filename = f"{OUTPUT_DIR}/homenews_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(polished_data, f, ensure_ascii=False, indent=2)
    
    print(f"  [✓] 润色数据已保存至：{filename}")
    return filename

def fetch_news_from_scrapers(count=9):
    """调用三个新闻抓取脚本"""
    print("\n" + "="*50)
    print("📰 [Scraping] 开始从各平台抓取新闻")
    print("="*50)
    all_news = []
    
    try:
        from .fetch_baidu import get_baidu_news
        source1_data = get_baidu_news(count)
        if source1_data:
            all_news.extend(source1_data)
            print(f"📊 [Summary] Baidu: ✓ 成功抓取 {len(source1_data)} 条")
    except ImportError:
        try:
            from fetch_baidu import get_baidu_news
            source1_data = get_baidu_news(count)
            if source1_data:
                all_news.extend(source1_data)
                print(f"📊 [Summary] Baidu: ✓ 成功抓取 {len(source1_data)} 条")
        except Exception as e:
            print(f"📊 [Summary] Baidu: ✗ 失败 - {e}")
    except Exception as e:
        print(f"📊 [Summary] Baidu: ✗ 失败 - {e}")
    
    try:
        from .fetch_tencent import get_tencent_news
        source2_data = get_tencent_news(count)
        if source2_data:
            all_news.extend(source2_data)
            print(f"📊 [Summary] Tencent: ✓ 成功抓取 {len(source2_data)} 条")
    except ImportError:
        try:
            from fetch_tencent import get_tencent_news
            source2_data = get_tencent_news(count)
            if source2_data:
                all_news.extend(source2_data)
                print(f"📊 [Summary] Tencent: ✓ 成功抓取 {len(source2_data)} 条")
        except Exception as e:
            print(f"📊 [Summary] Tencent: ✗ 失败 - {e}")
    except Exception as e:
        print(f"📊 [Summary] Tencent: ✗ 失败 - {e}")
    
    try:
        from .fetch_toutiao import get_toutiao_news
        source3_data = get_toutiao_news(count)
        if source3_data:
            all_news.extend(source3_data)
            print(f"📊 [Summary] Toutiao: ✓ 成功抓取 {len(source3_data)} 条")
    except ImportError:
        try:
            from fetch_toutiao import get_toutiao_news
            source3_data = get_toutiao_news(count)
            if source3_data:
                all_news.extend(source3_data)
                print(f"📊 [Summary] Toutiao: ✓ 成功抓取 {len(source3_data)} 条")
        except Exception as e:
            print(f"📊 [Summary] Toutiao: ✗ 失败 - {e}")
    except Exception as e:
        print(f"📊 [Summary] Toutiao: ✗ 失败 - {e}")
    
    print("="*50)
    print(f"✓ 全部平台抓取完成，共获得 {len(all_news)} 条新闻候选\n")
    return all_news

def call_deepseek_api(all_news_items, history_context, max_retries=3):
    """调用DeepSeek API进行润色"""
    print("\n" + "-"*30)
    print("🤖 [AI] 正在启动新闻润色与筛选...")
    print("-"*30)

    if not DEEPSEEK_API_KEY:
        print("  [!] 错误: 未找到 DEEPSEEK_API_KEY。")
        return None

    # Format History
    history_str = "无历史记录"
    if history_context:
        history_lines = [f"- {h.get('title')} ({h.get('timestamp', '')[:10]})" for h in history_context]
        history_str = "\n".join(history_lines[:10])  # 只显示最新10条

    input_payload = []
    for item in all_news_items:
        content_text = item.get('content', '')
        if len(content_text) > 800:
            content_text = content_text[:800] + "..."
            
        entry = {
            "title": item.get('title', ''),
            "content": content_text,
            "source_platform": item.get('source_platform', 'Unknown'),
            "source_url": item.get('source_url', ''),
            "image": item.get('image', '')
        }
        if entry['title'] or entry['content']:
            input_payload.append(entry)

    json_payload_str = json.dumps(input_payload, ensure_ascii=False)
    print(f"  [>] 发送 {len(input_payload)} 条候选新闻 + {len(history_context)} 条历史记录给 AI...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    # 注入历史记录到提示词
    final_system_prompt = SYSTEM_PROMPT.format(history_context_str=history_str)
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": json_payload_str}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "stream": False
    }

    for attempt in range(max_retries):
        try:
            start_time = time.time()
            response = requests.post(DEEPSEEK_BASE_URL, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result_json = response.json()
            answer_content = result_json["choices"][0]["message"]["content"]
            parsed_data = json.loads(answer_content)
            
            elapsed = time.time() - start_time
            if isinstance(parsed_data, dict) and "news" in parsed_data:
                news_list = parsed_data["news"]
                if not isinstance(news_list, list):
                    print(f"  [!] Error: 'news' field is not a list: {type(news_list)}")
                    continue
                
                print(f"  [✓] AI 润色完成 ({elapsed:.1f}s). 结果数量: {len(news_list)}")
                if len(news_list) > 0:
                    summary = news_list[0].get('title', 'No Summary Title')
                    print(f"      总结标题: {summary}")
                
                if len(news_list) < 10:
                    print(f"  [!] 警告: AI 返回条目少于预期 ({len(news_list)}/10)")
                
                return parsed_data
            else:
                print(f"  [!] API response format unexpected.")

        except Exception as e:
            print(f"  [!] AI API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                
    print("  [!] 所有重试均失败。")
    return None

def main(count=9):
    """主流程"""
    print("\n" + "="*30)
    print("🚀 [Home News] 开始润色流程")
    print("="*30)
    
    # 清空输出目录
    print("  正在清理输出目录...")
    clean_output_dir()
    
    # 加载历史库
    history_items = load_history()
    print(f"  加载历史库：{len(history_items)} 条")
    
    # 抓取新闻
    all_news = fetch_news_from_scrapers(count)
    
    if not all_news:
        print("  [!] 未能抓取任何新闻")
        return None
    
    # 调用DeepSeek API进行润色
    polished_data = call_deepseek_api(all_news, history_items)
    
    if not polished_data:
        print("  [!] AI润色失败")
        return None
    
    # 添加时间戳
    beijing_time = datetime.utcnow() + timedelta(hours=8)
    timestamp = beijing_time.strftime("%Y%m%d_%H%M%S")
    
    # 确保新闻列表存在
    news_list = polished_data.get('news', [])
    
    # 重新组织数据结构：只保留必要字段，source_platform 使用新闻源而不是 author
    for item in news_list:
        if item.get('rank', 0) > 0:  # 跳过 rank 0
            # source_platform 已经在爬虫中设置为新闻源平台，这里保持不变
            pass
    
    # 保存中间文件到 output 目录（用于调试）
    polished_data_with_timestamp = {
        "news": news_list,
        "timestamp": timestamp
    }
    save_polished_news(polished_data_with_timestamp)
    
    print(f"  [✓] 新闻润色完成，共 {len(news_list)} 条。")
    
    # 更新历史库
    print("  正在更新历史库...")
    save_history(news_list)
    
    # 返回给 pipeline 的数据（不包含 timestamp）
    return {"news": news_list}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='新闻润色与聚合器')
    parser.add_argument('--count', type=int, default=9, help='每个平台抓取数量（默认9）')
    args = parser.parse_args()

    data = main(args.count)
    if data:
        print(json.dumps(data, ensure_ascii=False, indent=2))
