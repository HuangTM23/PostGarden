"""
World News Polish Script
国际新闻润色与聚合主程序
"""
import os
import json
import requests
import argparse
import shutil
from datetime import datetime
from dotenv import load_dotenv

# Import scrapers
try:
    from . import fetch_bbc
    from . import fetch_cnn
    from . import fetch_nytimes
    from . import fetch_sky
except ImportError:
    import fetch_bbc
    import fetch_cnn
    import fetch_nytimes
    import fetch_sky

# 加载 .env 文件
load_dotenv()

# --- Configuration ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "worldnews_history.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
MAX_HISTORY_SIZE = 36  # 历史库最大容量

# V2 Prompt Template
V2_PROMPT_TEMPLATE = """
你是一名专业的中文国际新闻编辑，负责制作一期国际新闻精选内容。

核心目标：从"最新抓取新闻"中，通过"事件级去重 + 内容筛选"，直接选出 9 条"完全不同新闻事件"的国际新闻。

【重要：历史排重参考】
以下是过去已发布过的新闻（History），请严格回避与这些历史内容重复或高度相似的事件：
{history_context_str}

⚠️ 强制过滤规则 (Negative Filter) - 优先级最高
必须剔除以下新闻：
1. 涉及中国国内的政治、法律、政府决策等。
2. 涉及中国军事、国防、领土争议等。
3. 重复的国际事件。

保留的新闻应侧重于：全球科技与商业、重大国际地缘政治（非中国相关）、民生与社会热点、文化、体育、奇闻。

写作要求：
- 使用专业、正式的新闻体。
- 每条新闻正文：不超过 50 个汉字，只保留"发生了什么 + 关键结果"。
- 单条新闻标题：不超过 20 个汉字。
- **必须翻译**：将英文标题和内容翻译成中文。

**Rank 0 总结标题（核心任务）**：
你是一名顶级"标题党"编辑，擅长制作**极具爆炸性和冲击力的新闻标题**。

【核心策略】
1. **不必面面俱到**：可以只聚焦 9 条新闻中**最具冲击力的 1-2 条事件**
2. **制造紧迫感**：使用"正在"、"突发"、"紧急"等词汇
3. **突出对抗**：强调冲突、博弈、撕裂、反转
4. **引发好奇**：可以用疑问句或感叹句结尾
5. **具体胜于抽象**：可以提及具体国家/地区/事件，但要有冲击力

【标题公式（任选其一）】
- **对抗型**：XX vs XX！谁将胜出？
- **危机型**：XX告急！XX面临崩溃边缘
- **反转型**：惊天反转！XX突然……
- **疑问型**：XX为何突然……？真相令人震惊
- **爆料型**：独家！XX内幕曝光
- **趋势型**：XX失控！全球XX陷入混乱

【标题要求】
- 字数：**15-25 个汉字**
- 风格：**爆炸性、刺激性、冲突对抗**
- **必须使用**："！"或"？"结尾
- **可以包含**：具体国家、地区、人物、事件名称
- **禁止**：危言耸听、虚假信息、过度夸张

【示例参考】
- "格陵兰主权争夺战！美丹关系陷入空前危机"
- "AI巨头突然崩盘？硅谷震荡不止"
- "欧洲能源告急！冬季断气危机迫在眉睫"
- "特朗普回归倒计时！全球秩序面临重组？"
- "中东和平协议破裂！战火重燃在即"

输出格式要求（必须严格遵守 JSON 格式）
你必须输出一个包含 10 条数据的列表（Rank 0 为总结 + Rank 1-9 为 9 条精选新闻）。

注意：Rank 0 需要包含所有字段，但 content、title0、source_platform、source_url、index、author、image 都留空。

[
  {{
    "rank": 0,
    "title": "爆炸性中文总结标题！或？",
    "title0": "",
    "content": "",
    "index": 0,
    "author": "",
    "source_platform": "",
    "source_url": "",
    "image": ""
  }},
  {{
    "rank": 1,
    "title": "中文新闻标题",
    "title0": "原始英文标题",
    "source_platform": "来源平台",
    "source_url": "原始链接",
    "content": "50字以内中文正文",
    "index": 热度指数,
    "author": "平台名称",
    "image": "图片URL"
  }},
  ... (直到 Rank 9)
]

以下是原始新闻数据:
{news_data}
"""

def clear_output_directory():
    """清空输出目录"""
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR)
            print(f"[✓] 已清空输出目录: {OUTPUT_DIR}")
        except Exception as e:
            print(f"[!] 清空输出目录失败: {e}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def setup_directories():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_history():
    """加载历史新闻记录"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except:
            return []
    return []

def save_history(news_items):
    """保存新闻到历史记录，维护最大容量36条"""
    try:
        history = load_history()
        
        # 添加新新闻到历史库
        for item in news_items:
            if item.get('rank', 0) > 0:  # 跳过 rank 0
                history.append({
                    'title': item.get('title'),
                    'title0': item.get('title0', ''),
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
        
        # 只保留最近 36 条
        history = history[-MAX_HISTORY_SIZE:]
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        print(f"[✓] 历史库已更新，当前包含 {len(history)} 条记录")
    except Exception as e:
        print(f"[!] 保存历史记录失败: {e}")

def print_news_item(platform, index, total, item):
    """打印单条新闻信息"""
    print(f"\n  [{index}/{total}] {item.get('title', 'N/A')[:70]}")
    print(f"       来源: {item.get('source_platform', 'N/A')}")
    # 打印完整 URL
    print(f"       链接: {item.get('source_url', 'N/A')}")
    if item.get('image'):
        # 打印完整图片 URL
        print(f"       图片: {item.get('image')}")

def run_scrapers(limit=10):
    """运行所有抓取脚本并返回数据"""
    print("\n" + "="*50)
    print("🔍 启动国际新闻抓取")
    print("="*50)
    
    all_news = []
    
    # 1. BBC
    print("\n[1/4] 抓取 BBC News...")
    try:
        bbc_data = fetch_bbc.scrape(limit)
        if bbc_data:
            for idx, item in enumerate(bbc_data, 1):
                print_news_item("BBC", idx, len(bbc_data), item)
            all_news.extend(bbc_data)
            print(f"\n  ✓ BBC 完成: {len(bbc_data)} 条")
        else:
            print(f"  ✗ BBC: 未获取到数据")
    except Exception as e:
        print(f"  ✗ BBC 失败: {e}")
    
    # 2. CNN
    print("\n[2/4] 抓取 CNN...")
    try:
        cnn_data = fetch_cnn.scrape(limit)
        if cnn_data:
            for idx, item in enumerate(cnn_data, 1):
                print_news_item("CNN", idx, len(cnn_data), item)
            all_news.extend(cnn_data)
            print(f"\n  ✓ CNN 完成: {len(cnn_data)} 条")
        else:
            print(f"  ✗ CNN: 未获取到数据")
    except Exception as e:
        print(f"  ✗ CNN 失败: {e}")
    
    # 3. NYTimes
    print("\n[3/4] 抓取 NYTimes...")
    try:
        nyt_data = fetch_nytimes.scrape(limit)
        if nyt_data:
            for idx, item in enumerate(nyt_data, 1):
                print_news_item("NYTimes", idx, len(nyt_data), item)
            all_news.extend(nyt_data)
            print(f"\n  ✓ NYTimes 完成: {len(nyt_data)} 条")
        else:
            print(f"  ✗ NYTimes: 未获取到数据")
    except Exception as e:
        print(f"  ✗ NYTimes 失败: {e}")
    
    # 4. Sky News
    print("\n[4/4] 抓取 Sky News...")
    try:
        sky_data = fetch_sky.scrape(limit)
        if sky_data:
            for idx, item in enumerate(sky_data, 1):
                print_news_item("Sky News", idx, len(sky_data), item)
            all_news.extend(sky_data)
            print(f"\n  ✓ Sky News 完成: {len(sky_data)} 条")
        else:
            print(f"  ✗ Sky News: 未获取到数据")
    except Exception as e:
        print(f"  ✗ Sky News 失败: {e}")
    
    print(f"\n{'='*50}")
    print(f"汇总: 共获取 {len(all_news)} 条原始新闻")
    print("="*50)
    return all_news

def call_deepseek(all_news, history_context=[]):
    """调用 DeepSeek API 进行筛选、翻译和润色"""
    print("\n" + "="*50)
    print("🤖 调用 DeepSeek AI 进行内容处理")
    print("="*50)
    
    # Format History
    history_str = "无历史记录"
    if history_context:
        history_lines = [
            f"- {h.get('title')} / {h.get('title0', '')} ({h.get('date')})" 
            for h in history_context
        ]
        history_str = "\n".join(history_lines)
    
    print(f"输入: {len(all_news)} 条候选新闻")
    print(f"历史: {len(history_context)} 条记录")
    
    # 构造 Prompt
    news_json_str = json.dumps(all_news, ensure_ascii=False, indent=2)
    prompt = V2_PROMPT_TEMPLATE.format(
        news_data=news_json_str,
        history_context_str=history_str
    )
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        print("正在请求 DeepSeek API...")
        response = requests.post(API_URL, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        content_str = result['choices'][0]['message']['content']
        
        # Cleanup markdown
        content_str = content_str.replace("```json", "").replace("```", "").strip()
        
        # Simple JSON repair
        if content_str.startswith("{") and "}{" in content_str:
            content_str = f"[{content_str.replace('}{', '},{')}]"
        elif not content_str.startswith("["):
            start = content_str.find("[")
            end = content_str.rfind("]")
            if start != -1 and end != -1:
                content_str = content_str[start:end+1]
        
        final_data = json.loads(content_str)
        
        if isinstance(final_data, dict):
            if "news" in final_data:
                final_data = final_data["news"]
            else:
                final_data = [final_data]
        
        # 确保 Rank 0 包含所有字段
        if final_data and final_data[0].get('rank') == 0:
            rank0 = final_data[0]
            rank0.setdefault('title0', '')
            rank0.setdefault('content', '')
            rank0.setdefault('index', 0)
            rank0.setdefault('author', '')
            rank0.setdefault('source_platform', '')
            rank0.setdefault('source_url', '')
            rank0.setdefault('image', '')
        
        print(f"[✓] DeepSeek 返回 {len(final_data)} 条结果")
        return final_data
        
    except Exception as e:
        print(f"[!] DeepSeek API 错误: {e}")
        return None

def main(limit=9):
    """主函数"""
    # 0. 清空输出目录
    clear_output_directory()
    
    # 1. 加载历史库
    history = load_history()
    print(f"\n历史库: {len(history)} 条记录")
    
    # 2. 抓取新闻
    raw_news = run_scrapers(limit=limit)
    
    if not raw_news:
        print("\n[!] 未获取到任何新闻，退出。")
        return None
    
    # 3. 调用 DeepSeek 处理
    final_news = call_deepseek(raw_news, history_context=history)
    
    if not final_news:
        print("\n[!] AI 处理失败，退出。")
        return None
    
    # 4. 保存输出文件到 worldnews/output 目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f"worldnews_{timestamp}.json")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_news, f, ensure_ascii=False, indent=2)
        print(f"\n[✓] 已保存到: {output_file}")
    except Exception as e:
        print(f"\n[!] 保存文件失败: {e}")
        return None
    
    # 5. 更新历史库
    save_history(final_news)
    
    # 6. 输出结果摘要
    print("\n" + "="*50)
    print("📰 处理完成")
    print("="*50)
    print(f"总结标题: {final_news[0].get('title', 'N/A')}")
    print(f"精选新闻: {len(final_news) - 1} 条")
    print(f"输出文件: {output_file}")
    print("="*50 + "\n")
    
    # 返回数据给 pipeline（返回列表格式）
    return final_news

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="World News Scraper and Polish Tool")
    parser.add_argument('--limit', type=int, default=10, 
                       help="每个平台抓取的新闻数量 (默认: 10)")
    args = parser.parse_args()
    
    main(limit=args.limit)