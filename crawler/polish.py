# Renamed from polish_v3.py
import os
import json
import time
import requests

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = """你是一名专业中文新闻编辑与内容策划人员，负责从多个新闻平台的抓取结果中，进行事件级去重、筛选、专业简化与内容整合，生成一组适合发布在微信公众号与小红书的新闻精选内容。

核心目标是：从全部新闻中，通过“事件级去重 + 内容筛选”，直接选出 9 条“完全不同新闻事件”的新闻。

⚠️ 强制过滤规则 (Negative Filter) - 优先级最高
必须剔除所有涉及以下领域的新闻:
1. 政治 (Politics)
2. 军事 (Military)
3. 台湾 (Taiwan)

保留的新闻应侧重于：科技与商业、民生与社会热点、文化与娱乐、体育、奇闻轶事。

写作要求：
- 使用专业、正式的新闻体。
- 每条新闻正文：不超过 50 个汉字，只保留“发生了什么 + 关键结果”。
- 单条新闻标题：不超过 20 个汉字。
- 整体总结性标题：15-25字，具有吸引力。

数据完整性要求：
- 对于选中的每条新闻，必须保留其原始的 `source_platform`, `source_url` 和 `image` 字段。
- `image` 字段必须原样复制，不要修改链接地址。

输出格式要求（必须严格遵守）
你必须输出一个包含 "news" 字段的 JSON 对象。
"news" 字段是一个列表，必须严格包含 10 条数据（Rank 0 为总结 + Rank 1-9 为 9 条精选新闻）。

{
  "news": [
    { 
      "rank": 0, 
      "title": "整体总结标题", 
      "content": "这里留空或写简短引导语",
      "image": "" 
    },
    { 
      "rank": 1, 
      "title": "新闻1标题", 
      "source_platform": "来源平台", 
      "source_url": "原始链接", 
      "content": "新闻1正文...", 
      "image": "原始图片链接(必须保留)" 
    },
    ...
    { "rank": 9, ... }
  ]
}
"""

def main(all_news_items, max_retries=3):
    if not DEEPSEEK_API_KEY:
        print("[!] 错误: 未设置 DEEPSEEK_API_KEY")
        return None

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
    print(f"    [AI] Sending {len(input_payload)} news items for polishing... (Payload size: {len(json_payload_str)} chars)")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json_payload_str}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "stream": False
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(DEEPSEEK_BASE_URL, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            result_json = response.json()
            answer_content = result_json["choices"][0]["message"]["content"]
            parsed_data = json.loads(answer_content)
            
            if isinstance(parsed_data, dict) and "news" in parsed_data:
                news_list = parsed_data["news"]
                if not isinstance(news_list, list):
                     print(f"    [!] 'news' field is not a list: {type(news_list)}")
                     continue # Retry
                
                print(f"    [AI] Successfully parsed response. Item count: {len(news_list)}")
                if len(news_list) < 10:
                    print(f"    [!] Warning: AI returned fewer items than requested ({len(news_list)}/10)")
                
                return parsed_data
            else:
                 print(f"    [!] API response format unexpected: {str(parsed_data)[:200]}")

        except Exception as e:
            print(f"    [!] AI API call failed (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                
    return None
