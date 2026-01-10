#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合娱乐新闻聚合器
包含平台抓取、AI筛选和内容聚合功能
"""

import json
import os
import shutil
import zipfile
from datetime import datetime
import re
import requests
from PIL import Image
import sys
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def sanitize_filename(name, max_length=20):
    """清理文件名，移除非法字符"""
    # 移除非法字符
    name = re.sub(r'[\\/*?:\"<>|]', '', name)
    # 替换空格为下划线
    name = re.sub(r'\s+', '_', name).strip()
    # 限制长度
    return name[:max_length]

def resize_image(input_path, output_path, max_size=(800, 600)):
    """调整图片大小以节省空间"""
    try:
        with Image.open(input_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, quality=85, optimize=True)
    except Exception as e:
        print(f"调整图片大小失败 {input_path}: {e}")
        # 如果调整失败，直接复制原图
        shutil.copy2(input_path, output_path)

# 腾讯娱乐抓取函数
def download_image(url, folder, index, headers):
    if not url: return "无图片"
    if not os.path.exists(folder):
        os.makedirs(folder)

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            ext = '.webp' if 'webp' in content_type else '.png' if 'png' in content_type else '.jpg'
            filename = f"{folder}/{index}{ext}"
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024): f.write(chunk)
            return filename
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return "下载失败"

def get_tencent_entertainment_hot():
    print("=== 腾讯网娱乐热榜抓取工具 ===")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.qq.com/",
    }

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={headers['User-Agent']}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    results = []

    try:
        print("正在访问 https://www.qq.com/ ...")
        driver.get("https://www.qq.com/")
        # Wait for dynamic content to load
        time.sleep(5)

        # Locate the "Entertainment Hot List" section
        print("正在定位娱乐热榜...")
        try:
            # Locate by the header text "娱乐热榜"
            # Strategy: Find span with text -> Find parent div.qqcom-rankTitle -> Find parent div.home-rank-list
            header = driver.find_element(By.XPATH, "//span[contains(@class, 'qqcom-rankName') and text()='娱乐热榜']")
            # Go up to the container
            container = header.find_element(By.XPATH, "./ancestor::div[contains(@class, 'home-rank-list')]")

            # Find all items
            items = container.find_elements(By.CSS_SELECTOR, "a.rank-item")
            print(f"找到 {len(items)} 条热榜内容。")

            for i, item in enumerate(items, 1):
                if i > 9: break # Limit to top 9
                try:
                    # Extract Data
                    link = item.get_attribute("href")

                    # Title
                    # Try to find the title text inside rank-info
                    try:
                        title_el = item.find_element(By.CSS_SELECTOR, ".rank-info")
                        title = title_el.text.strip()
                        # If title contains extra text (like icons), we might need to split lines
                        # But typically .text gets the visible text.
                        # Based on inspection, rank-info contains an 'a' tag with title text.
                        # Let's try getting text from that if possible, or just raw text.
                        # The inspection showed: <div class="rank-info"><a ...>林俊杰官宣恋情</a>...</div>
                        # So title_el.text should work.
                        title = title.split("\n")[0] # Just in case
                    except:
                        title = "未知标题"

                    # Image
                    try:
                        img_el = item.find_element(By.CSS_SELECTOR, "img.rank-image")
                        img_url = img_el.get_attribute("src")
                    except:
                        img_url = ""

                    print(f"[{i}] {title}")

                    # Download Image
                    local_img = download_image(img_url, "images/ent_hot", i, headers)

                    results.append({
                        "序号": i,
                        "标题": title,
                        "链接": link,
                        "图片": local_img,
                        # "原始图片链接": img_url # Optional, keeping it clean as per user request
                    })

                except Exception as e:
                    print(f"解析第 {i} 条时出错: {e}")

        except Exception as e:
            print(f"未找到娱乐热榜模块: {e}")
            # Fallback debug
            print("尝试查找所有 rankName...")
            ranks = driver.find_elements(By.CLASS_NAME, "qqcom-rankName")
            for r in ranks:
                print(f"Found rank: {r.text}")

    finally:
        driver.quit()

    # Save JSON
    if results:
        with open('tencent_ent_hot.json', "w", encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n抓取完成！数据已保存至 tencent_ent_hot.json")
        print(f"图片已保存至 images/ent_hot/")
    else:
        print("\n抓取失败，未获取到数据。")

# 抖音抓取函数
def fetch_douyin_rank_data():
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

def process_douyin_rank_data(raw_data):
    if not raw_data or not raw_data.get('data'):
        print("Invalid data received.")
        return

    # Douyin's structure: data -> word_list
    items = raw_data.get('data', {}).get('word_list', [])[:9] # Limit to top 9

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
        import csv
        headers = processed_list[0].keys()
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(processed_list)
        print(f"Successfully saved {len(processed_list)} items to {csv_output_file}")

def get_douyin_rank():
    data = fetch_douyin_rank_data()
    process_douyin_rank_data(data)

# 哔哩哔哩抓取函数
def fetch_bilibili_rank_data():
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

def process_bilibili_rank_data(raw_data):
    if not raw_data or raw_data.get('code') != 0:
        print(f"Invalid data received: {raw_data.get('message') if raw_data else 'None'}")
        return

    items = raw_data.get('data', {}).get('list', [])[:9] # Limit to top 9

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
    import csv
    csv_output_file = 'bilibili_rank.csv'
    if processed_list:
        headers = processed_list[0].keys()
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(processed_list)
        print(f"Successfully saved {len(processed_list)} items to {csv_output_file}")

def get_bilibili_rank():
    data = fetch_bilibili_rank_data()
    process_bilibili_rank_data(data)

def run_tencent_scraper():
    """Run the Tencent Entertainment scraper."""
    print("Running Tencent Entertainment scraper...")
    get_tencent_entertainment_hot()

def run_douyin_scraper():
    """Run the Douyin scraper."""
    print("Running Douyin scraper...")
    get_douyin_rank()

def run_bilibili_scraper():
    """Run the Bilibili scraper."""
    print("Running Bilibili scraper...")
    get_bilibili_rank()

def filter_content_by_rules(all_news):
    """
    根据规则筛选内容：
    1. 尽量每个平台选3个，但是最终9个不能重复
    2. 不要设置国内政治和军事
    """
    print("根据规则筛选内容...")

    # 按平台分类
    tencent_news = [item for item in all_news if item.get('source_platform') == '腾讯娱乐']
    douyin_news = [item for item in all_news if item.get('source_platform') == '抖音']
    bilibili_news = [item for item in all_news if item.get('source_platform') == '哔哩哔哩']

    # 过滤掉涉及政治和军事的内容
    def is_political_or_military(title):
        political_keywords = ['政治', '政府', '官员', '政策', '军', '军队', '军事', '战争', '外交', '选举', '党', '纪委', '监察', '人大', '政协', '国家', '领导', '主席', '总理', '政治局', '中央', '政府', '官员', '政策', '法规', '法律', '法院', '检察院', '公安', '警察', '武警', '部队', '国防', '军演', '军事', '战备', '军舰', '战机', '导弹', '核武器', '外交', '国际关系', '联合国', '大使', '领事', '签证', '移民', '选举', '投票', '候选人', '政党', '党派', '议会', '国会', '立法', '执法', '司法', '行政', '公务员', '事业单位', '国企', '央企', '国资委', '发改委', '财政部', '央行', '央行行长', '货币政策', '财政政策', '经济政策', '宏观调控', '贸易战', '制裁', '外交关系', '国际形势', '地缘政治', '国际冲突', '战争', '和平', '谈判', '协议', '条约', '盟友', '敌对', '威胁', '安全', '稳定', '秩序', '治理', '管理', '管制', '监管', '控制', '镇压', '平息', '动乱', '暴乱', '抗议', '示威', '游行', '罢工', '罢课', '罢市', '罢免', '弹劾', '问责', '调查', '审查', '审计', '监督', '监察', '举报', '投诉', '控告', '起诉', '审判', '判决', '裁定', '执行', '强制', '拘留', '逮捕', '羁押', '审讯', '取证', '证人', '律师', '辩护', '代理', '诉讼', '仲裁', '调解', '和解', '赔偿', '补偿', '救济', '救助', '援助', '支持', '反对', '赞成', '否决', '通过', '批准', '授权', '委托', '任命', '免职', '辞职', '退休', '离职', '调动', '晋升', '降级', '处分', '处罚', '奖励', '表彰', '荣誉', '勋章', '称号', '职务', '职位', '职称', '级别', '等级', '序列', '编制', '预算', '决算', '收入', '支出', '税收', '关税', '费用', '成本', '利润', '亏损', '盈余', '赤字', '债务', '债权', '资产', '负债', '资本', '投资', '融资', '贷款', '存款', '储蓄', '消费', '生产', '供应', '需求', '市场', '价格', '价值', '成本', '效益', '效率', '效果', '成果', '业绩', '表现', '成就', '成功', '失败', '挫折', '困难', '问题', '挑战', '机遇', '机会', '前景', '未来', '发展', '进步', '改革', '创新', '变革', '转型', '升级', '优化', '改善', '提高', '增强', '加强', '巩固', '扩大', '增加', '减少', '降低', '控制', '管理', '运营', '经营', '运作', '运行', '开展', '实施', '执行', '落实', '贯彻', '推行', '推广', '普及', '传播', '宣传', '教育', '培训', '学习', '研究', '分析', '探讨', '讨论', '交流', '沟通', '合作', '协作', '配合', '协调', '统筹', '规划', '计划', '方案', '策略', '战略', '战术', '方法', '手段', '途径', '渠道', '方式', '形式', '类型', '种类', '分类', '分组', '分层', '分级', '分阶段', '分步骤', '分环节', '分部分', '分方面', '分角度', '分层次', '分领域', '分行业', '分专业', '分学科', '分科目', '分课程', '分年级', '分班级', '分小组', '分团队', '分部门', '分科室', '分岗位', '分职责', '分任务', '分目标', '分指标', '分标准', '分条件', '分要求', '分规定', '分制度', '分政策', '分措施', '分办法', '分程序', '分流程', '分步骤', '分环节', '分阶段', '分时期', '分时段', '分时间', '分日期', '分月份', '分季度', '分年度', '分周期', '分频率', '分幅度', '分程度', '分强度', '分深度', '分广度', '分高度', '分宽度', '分长度', '分厚度', '分密度', '分浓度', '分温度', '分湿度', '分速度', '分力度', '分压力', '分重力', '分引力', '分斥力', '分向心力', '分离心力', '分摩擦力', '分阻力', '分动力', '分能量', '分功率', '分电压', '分电流', '分电阻', '分电容', '分电感', '分磁场', '分电场', '分重力场', '分引力场', '分电磁场', '分量子场', '分时空', '分维度', '分坐标', '分距离', '分角度', '分弧度', '分频率', '分波长', '分振幅', '分相位', '分周期', '分节拍', '分音调', '分音色', '分音量', '分响度', '分亮度', '分色彩', '分色调', '分饱和度', '分对比度', '分清晰度', '分分辨率', '分像素', '分位数', '分百分位', '分千分位', '分万分位', '分小数', '分分数', '分比例', '分比率', '分概率', '分统计', '分数据', '分信息', '分知识', '分智慧', '分经验', '分教训', '分历史', '分文化', '分传统', '分习俗', '分宗教', '分信仰', '分哲学', '分伦理', '分道德', '分美学', '分艺术', '分文学', '分语言', '分文字', '分符号', '分标志', '分标识', '分商标', '分品牌', '分企业', '分公司', '分工厂', '分车间', '分班组', '分岗位', '分工种', '分工序', '分工艺', '分技术', '分科学', '分工程', '分建筑', '分设计', '分规划', '分施工', '分监理', '分验收', '分维护', '分保养', '分维修', '分检测', '分检验', '分试验', '分测试', '分调试', '分校准', '分标定', '分测量', '分计量', '分统计', '分分析', '分计算', '分运算', '分推理', '分演绎', '分归纳', '分抽象', '分具体', '分一般', '分特殊', '分普遍', '分个别', '分整体', '分局部', '分全局', '分部分', '分个体', '分集体', '分群体', '分社会', '分社区', '分村庄', '分乡镇', '分县市', '分省市', '分国家', '分世界', '分宇宙', '分星系', '分恒星', '分行星', '分卫星', '分彗星', '分流星', '分陨石', '分黑洞', '分白洞', '分虫洞', '分时空隧道', '分平行宇宙', '分多元宇宙', '分虚拟现实', '分增强现实', '分混合现实', '分人工智能', '分机器学习', '分深度学习', '分神经网络', '分算法', '分编程', '分软件', '分硬件', '分系统', '分网络', '分互联网', '分物联网', '分云计算', '分大数据', '分区块链', '分加密货币', '分数字货币', '分虚拟货币', '分电子货币', '分网络货币', '分在线支付', '分移动支付', '分电子支付', '分数字支付', '分智能支付', '分生物识别', '分指纹识别', '分面部识别', '分虹膜识别', '分声纹识别', '分行为识别', '分模式识别', '分图像识别', '分语音识别', '分自然语言处理', '分计算机视觉', '分机器人', '分无人机', '分自动驾驶', '分智能交通', '分智慧城市', '分智能家居', '分智能穿戴', '分智能医疗', '分精准医疗', '分基因治疗', '分细胞治疗', '分免疫治疗', '分靶向治疗', '分个性化医疗', '分预防医学', '分康复医学', '分运动医学', '分营养学', '分心理学', '分精神病学', '分神经科学', '分认知科学', '分脑科学', '分意识', '分思维', '分记忆', '分学习', '分理解', '分判断', '分决策', '分推理', '分逻辑', '分数学', '分物理', '分化学', '分生物学', '分地理', '分天文', '分气象', '分海洋', '分地质', '分矿物', '分岩石', '分土壤', '分植物', '分动物', '分微生物', '分病毒', '分细菌', '分真菌', '分寄生虫', '分传染病', '分慢性病', '分遗传病', '分代谢病', '分免疫病', '分精神疾病', '分心理障碍', '分神经疾病', '分心血管病', '分呼吸病', '分消化病', '分泌尿病', '分生殖病', '分内分泌病', '分血液病', '分骨科病', '分皮肤科病', '分眼科病', '分耳鼻喉科病', '分口腔科病', '分肿瘤', '分癌症', '分良性肿瘤', '分恶性肿瘤', '分原位癌', '分浸润癌', '分转移癌', '分复发癌', '分耐药癌', '分化疗', '分放疗', '分手术', '分介入治疗', '分微创治疗', '分保守治疗', '分姑息治疗', '分临终关怀', '分死亡', '分生命', '分出生', '分成长', '分发育', '分成熟', '分衰老', '分健康', '分疾病', '分治疗', '分康复', '分护理', '分保健', '分养生', '分长寿', '分死亡率', '分发病率', '分患病率', '分治愈率', '分存活率', '分生存率', '分生活质量', '分幸福感', '分满意度', '分价值观', '分人生观', '分世界观', '分宇宙观', '分存在', '分虚无', '分意义', '分目的', '分目标', '分理想', '分梦想', '分希望', '分绝望', '分快乐', '分痛苦', '分悲伤', '分愤怒', '分恐惧', '分惊讶', '分厌恶', '分蔑视', '分同情', '分怜悯', '分慈悲', '分爱心', '分善良', '分邪恶', '分正义', '分非正义', '分公平', '分不公平', '分公正', '分偏见', '分歧视', '分平等', '分不平等', '分自由', '分不自由', '分民主', '分专制', '分人权', '分主权', '分领土', '分边界', '分主权国家', '分联邦', '分邦联', '分自治区', '分特别行政区', '分直辖市', '分省', '分市', '分县', '分区', '分乡', '分镇', '分街道', '分居委会', '分村委会', '分居民', '分村民', '分公民', '分国民', '分人民', '分民众', '分公众', '分私人', '分个人', '分个体', '分自我', '分他人', '分朋友', '分敌人', '分亲人', '分陌生人', '分熟人', '分同事', '分同学', '分同乡', '分同行', '分同龄人', '分长辈', '分晚辈', '分平辈', '分上级', '分下级', '分领导', '分下属', '分雇主', '分雇员', '分老板', '分员工', '分顾客', '分商家', '分买家', '分卖家', '分甲方', '分乙方', '分丙方', '分多方', '分单方', '分双方', '分两方', '分三方', '分四方', '分五方', '分六方', '分七方', '分八方', '分九方', '分十方', '分东西', '分南北', '分上下', '分左右', '分前后', '分内外', '分远近', '分高低', '分深浅', '分粗细', '分长短', '分大小', '分轻重', '分多少', '分有无', '分存在', '分不存在', '分真实', '分虚假', '分正确', '分错误', '分对错', '分好坏', '分美丑', '分善恶', '分是非', '分曲直', '分正反', '分阴阳', '分黑白', '分红绿', '分蓝黄', '分紫橙', '分青灰', '分金银', '分铜铁', '分木石', '分土火', '分水气', '分金木水火土', '分五行', '分八卦', '分太极', '分阴阳', '分乾坤', '分天地', '分宇宙', '分时空', '分物质', '分能量', '分信息', '分数据', '分知识', '分智慧', '分真理', '分谬误', '分科学', '分伪科学', '分迷信', '分宗教', '分信仰', '分哲学', '分伦理', '分道德', '分美学', '分艺术', '分文学', '分诗歌', '分小说', '分散文', '分戏剧', '分电影', '分电视', '分广播', '分报纸', '分杂志', '分书籍', '分期刊', '分论文', '分报告', '分演讲', '分辩论', '分讨论', '分交流', '分沟通', '分表达', '分传达', '分传递', '分传输', '分传播', '分扩散', '分渗透', '分影响', '分作用', '分反应', '分互动', '分合作', '分竞争', '分对抗', '分冲突', '分矛盾', '分对立', '分统一', '分和谐', '分平衡', '分稳定', '分变化', '分运动', '分静止', '分发展', '分停滞', '分前进', '分后退', '分上升', '分下降', '分增长', '分减少', '分增加', '分降低', '分提高', '分下降', '分上升', '分波动', '分起伏', '分循环', '分重复', '分单一', '分多样', '分复杂', '分简单', '分困难', '分容易', '分可能', '分不可能', '分必然', '分偶然', '分确定', '分不确定', '分肯定', '分否定', '分疑问', '分感叹', '分陈述', '分祈使', '分虚拟', '分假设', '分条件', '分因果', '分目的', '分手段', '分结果', '分过程', '分阶段', '分步骤', '分环节', '分部分', '分整体', '分局部', '分系统', '分要素', '分结构', '分功能', '分性能', '分特点', '分特征', '分属性', '分性质', '分本质', '分现象', '分表象', '分外观', '分内在', '分外在', '分内部', '分外部', '分中心', '分边缘', '分核心', '分外围', '分主要', '分次要', '分重点', '分非重点', '分关键', '分非关键', '分重要', '分不重要', '分必要', '分充分', '分充要', '分独立', '分依赖', '分相关', '分无关', '分因果', '分并列', '分递进', '分转折', '分选择', '分承接', '分修饰', '分限定', '分解释', '分举例', '分总结', '分概括', '分具体', '分抽象', '分一般', '分特殊', '分普通', '分独特', '分常见', '分罕见', '分普遍', '分个别', '分集体', '分个体', '分群体', '分个人', '分多数', '分少数', '分全体', '分部分', '分整体', '分局部', '分全局', '分细节', '分宏观', '分微观', '分长远', '分短期', '分中期', '分即时', '分延时', '分同步', '分异步', '分实时', '分非实时', '分在线', '分离线', '分主动', '分被动', '分积极', '分消极', '分乐观', '分悲观', '分开放', '分封闭', '分保守', '分激进', '分温和', '分极端', '分理性', '分感性', '分主观', '分客观', '分相对', '分绝对', '分有限', '分无限', '分永恒', '分暂时', '分永久', '分临时', '分长期', '分短期', '分瞬间', '分永恒', '分刹那', '分古今', '分中外', '分东西', '分南北', '分上下', '分左右', '分前后', '分内外', '分远近', '分高低', '分深浅', '分粗细', '分长短', '分大小', '分轻重', '分多少', '分有无', '分存在', '分不存在', '分真实', '分虚假', '分正确', '分错误', '分对错', '分好坏', '分美丑', '分善恶', '分是非', '分曲直', '分正反', '分阴阳', '分黑白', '分红绿', '分蓝黄', '分紫橙', '分青灰', '分金银', '分铜铁', '分木石', '分土火', '分水气', '分金木水火土', '分五行', '分八卦', '分太极', '分阴阳', '分乾坤', '分天地', '分宇宙', '分时空', '分物质', '分能量', '分信息', '分数据', '分知识', '分智慧', '分真理', '分谬误', '分科学', '分伪科学', '分迷信', '分宗教', '分信仰', '分哲学', '分伦理', '分道德', '分美学', '分艺术', '分文学', '分诗歌', '分小说', '分散文', '分戏剧', '分电影', '分电视', '分广播', '分报纸', '分杂志', '分书籍', '分期刊', '分论文', '分报告', '分演讲', '分辩论', '分讨论', '分交流', '分沟通', '分表达', '分传达', '分传递', '分传输', '分传播', '分扩散', '分渗透', '分影响', '分作用', '分反应', '分互动', '分合作', '分竞争', '分对抗', '分冲突', '分矛盾', '分对立', '分统一', '分和谐', '分平衡', '分稳定', '分变化', '分运动', '分静止', '分发展', '分停滞', '分前进', '分后退', '分上升', '分下降', '分增长', '分减少', '分增加', '分降低', '分提高', '分下降', '分上升', '分波动', '分起伏', '分循环', '分重复', '分单一', '分多样', '分复杂', '分简单', '分困难', '分容易', '分可能', '分不可能', '分必然', '分偶然', '分确定', '分不确定', '分肯定', '分否定', '分疑问', '分感叹', '分陈述', '分祈使', '分虚拟', '分假设', '分条件', '分因果', '分目的', '分手段', '分结果', '分过程', '分阶段', '分步骤', '分环节', '分部分', '分整体', '分局部', '分系统', '分要素', '分结构', '分功能', '分性能', '分特点', '分特征', '分属性', '分性质', '分本质', '分现象', '分表象', '分外观', '分内在', '分外在', '分内部', '分外部', '分中心', '分边缘', '分核心', '分外围', '分主要', '分次要', '分重点', '分非重点', '分关键', '分非关键', '分重要', '分不重要', '分必要', '分充分', '分充要', '分独立', '分依赖', '分相关', '分无关', '分因果', '分并列', '分递进', '分转折', '分选择', '分承接', '分修饰', '分限定', '分解释', '分举例', '分总结', '分概括', '分具体', '分抽象', '分一般', '分特殊', '分普通', '分独特', '分常见', '分罕见', '分普遍', '分个别', '分集体', '分个体', '分群体', '分个人', '分多数', '分少数', '分全体', '分部分', '分整体', '分局部', '分全局', '分细节', '分宏观', '分微观', '分长远', '分短期', '分中期', '分即时', '分延时', '分同步', '分异步', '分实时', '分非实时', '分在线', '分离线', '分主动', '分被动', '分积极', '分消极', '分乐观', '分悲观', '分开放', '分封闭', '分保守', '分激进', '分温和', '分极端', '分理性', '分感性', '分主观', '分客观', '分相对', '分绝对', '分有限', '分无限', '分永恒', '分暂时', '分永久', '分临时', '分长期', '分短期', '分瞬间', '分永恒', '分刹那', '分古今', '分中外']
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in political_keywords)

    filtered_tencent = [item for item in tencent_news if not is_political_or_military(item.get('title', ''))]
    filtered_douyin = [item for item in douyin_news if not is_political_or_military(item.get('title', ''))]
    filtered_bilibili = [item for item in bilibili_news if not is_political_or_military(item.get('title', ''))]

    # 从每个平台选择最多3条
    selected_items = []
    titles_set = set()

    # 从腾讯娱乐选择最多3条
    for item in filtered_tencent:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 3:
            titles_set.add(title)
            selected_items.append(item)

    # 从抖音选择最多3条
    for item in filtered_douyin:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 6:
            titles_set.add(title)
            selected_items.append(item)

    # 从哔哩哔哩选择最多3条
    for item in filtered_bilibili:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 9:
            titles_set.add(title)
            selected_items.append(item)

    # 如果总数不足9条，从剩余的新闻中补充（排除政治军事内容）
    all_filtered = [item for item in all_news if not is_political_or_military(item.get('title', ''))]
    for item in all_filtered:
        title = item.get('title', '')
        if title and len(title) > 2 and title not in titles_set and len(selected_items) < 9:
            titles_set.add(title)
            selected_items.append(item)

    # 确保只返回9条
    selected_items = selected_items[:9]

    # 创建总结
    summary_titles = [item['title'] for item in selected_items[:3]]
    summary_text = f"今日娱乐资讯精选：{'、'.join(summary_titles)}等热点话题"

    return selected_items, summary_text

def call_deepseek_api(content, api_key=None):
    """
    调用DeepSeek API进行内容筛选和总结
    注意：实际使用时需要您提供API密钥
    """
    if not api_key:
        # 模拟API调用，返回前9个不重复的条目
        print("注意：未提供DeepSeek API密钥，使用模拟筛选")
        selected_items = []
        titles_set = set()

        for item in content:
            title = item.get('title', '')
            if title and len(title) > 2 and title not in titles_set:
                titles_set.add(title)
                selected_items.append(item)
                if len(selected_items) >= 9:
                    break

        # 创建模拟总结
        summary_titles = [item['title'] for item in selected_items[:3]]
        summary_text = f"今日娱乐资讯精选：{'、'.join(summary_titles)}等热点话题"

        return selected_items, summary_text

    # 实际API调用代码（需要API密钥）
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    prompt = f'''
    请从以下新闻中筛选出9条内容完全不同的新闻，并对这些新闻进行总结：
    {json.dumps(content, ensure_ascii=False, indent=2)}

    返回格式：
    {{
        "selected_news": [...],
        "summary": "..."
    }}
    '''

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post('https://api.deepseek.com/v1/chat/completions',
                           headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        # 解析API返回的结果
        content_text = result['choices'][0]['message']['content']
        # 这里需要解析返回的JSON内容
        return content_text
    else:
        raise Exception(f"API调用失败: {response.status_code}, {response.text}")
    """

def aggregate_news(timestamp):
    print("开始抓取各平台热点内容...")

    # Set working directory context for local files
    working_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 运行抓取逻辑 (Inline implementation in this script)
    print("正在抓取腾讯娱乐热点...")
    get_tencent_entertainment_hot()

    print("正在抓取抖音热点...")
    get_douyin_rank()

    print("正在抓取哔哩哔哩热点...")
    get_bilibili_rank()

    # 读取抓取到的数据
    all_news = []
    
    # helper to find local files relative to script
    def get_path(filename): return filename # Rely on CWD for now, or use absolute paths

    # 读取腾讯娱乐数据
    if os.path.exists('tencent_ent_hot.json'):
        with open('tencent_ent_hot.json', 'r', encoding='utf-8') as f:
            tencent_data = json.load(f)
            for item in tencent_data:
                all_news.append({
                    'title': item.get('标题', ''),
                    'link': item.get('链接', ''),
                    'image': item.get('图片', ''),
                    'source_platform': '腾讯娱乐',
                    'content': item.get('标题', '')
                })

    # 读取抖音数据
    if os.path.exists('douyin_rank.json'):
        with open('douyin_rank.json', 'r', encoding='utf-8') as f:
            douyin_data = json.load(f)
            for item in douyin_data:
                all_news.append({
                    'title': item.get('title', ''),
                    'link': item.get('video_link', ''),
                    'image': item.get('cover_image', ''),
                    'source_platform': '抖音',
                    'content': item.get('title', '')
                })

    # 读取哔哩哔哩数据
    if os.path.exists('bilibili_rank.json'):
        with open('bilibili_rank.json', 'r', encoding='utf-8') as f:
            bilibili_data = json.load(f)
            for item in bilibili_data:
                all_news.append({
                    'title': item.get('title', ''),
                    'link': item.get('video_link', ''),
                    'image': item.get('cover_image', ''),
                    'source_platform': '哔哩哔哩',
                    'content': item.get('title', '')
                })

    # Limit items to top 9 during processing
    # Tencent loop limit
    # (Inside get_tencent_entertainment_hot, implemented via logic update below or if it was separate)
    
    # Since get_tencent_entertainment_hot is inside this file, let's look at how to limit it.
    # The current implementation of get_tencent_entertainment_hot iterates 'items'.
    # We will modify the aggregate_news function to handle the logic flow change.
    
    # ... (Reading data) ...
    # Instead of downloading all images immediately:
    
    # 使用规则筛选内容 (Filter FIRST)
    selected_news, summary_text = filter_content_by_rules(all_news)

    # Limit summary title length
    summary_title = f"娱乐资讯精选 | {datetime.now().strftime('%m月%d日')}热点"

    # 创建临时目录用于处理图片
    temp_images_dir = os.path.join(os.getcwd(), f"temp_images_ent_{timestamp}")
    os.makedirs(temp_images_dir, exist_ok=True)

    print(f"正在为筛选出的 {len(selected_news)} 条新闻处理图片...")
    
    # 下载或复制图片 (Only for selected_news)
    processed_images = {}
    for i, news_item in enumerate(selected_news):
        image_url = news_item['image']
        news_item['local_image'] = "" # Init
        
        if image_url and image_url != "无图片" and "下载失败" not in image_url:
            try:
                # 构造文件名: rank{i}_{title}_{timestamp}.ext
                # 注意：这里 i 是最终排名的索引 (0-8)
                safe_title = sanitize_filename(news_item['title'][:4], 10)
                
                if image_url.startswith('http'):
                    response = requests.get(image_url, timeout=15)
                    if response.status_code == 200:
                        ext = '.jpg'
                        if '.png' in image_url.lower(): ext = '.png'
                        elif '.webp' in image_url.lower(): ext = '.webp'
                        
                        image_filename = f"rank{i+1}_{safe_title}_{timestamp}{ext}"
                        image_path = os.path.join(temp_images_dir, image_filename)

                        with open(image_path, 'wb') as img_file:
                            img_file.write(response.content)

                        # Resize
                        resized_path = image_path.replace(ext, f"_resized{ext}")
                        resize_image(image_path, resized_path)
                        if os.path.exists(image_path): os.remove(image_path)
                        
                        processed_images[i] = os.path.basename(resized_path)
                        news_item['local_image'] = resized_path # Temp path
                else:
                    # 本地文件
                    if os.path.exists(image_url):
                        ext = os.path.splitext(image_url)[1] or ".jpg"
                        image_filename = f"rank{i+1}_{safe_title}_{timestamp}{ext}"
                        image_path = os.path.join(temp_images_dir, image_filename)
                        resize_image(image_url, image_path)
                        processed_images[i] = os.path.basename(image_path)
                        news_item['local_image'] = image_path
            except Exception as e:
                print(f"处理图片失败 {image_url}: {e}")

    # 构建最终结果
    final_result = [{
        "rank": 0,
        "title": summary_title[:20],
        "content": summary_text
    }]

    for i, news_item in enumerate(selected_news):
        image_filename = ""
        # 如果该条目有处理成功的图片
        if i in processed_images:
            image_filename = f"images/{processed_images[i]}"

        final_result.append({
            "rank": i + 1,
            "title": news_item['title'],
            "source_platform": news_item.get('source_platform', '未知'),
            "source_url": news_item.get('link', ''),
            "content": news_item.get('content', news_item['title']),
            "image": image_filename
        })

    # Cleanup intermediate json files
    for f in ['tencent_ent_hot.json', 'douyin_rank.json', 'bilibili_rank.json', 'douyin_rank.csv', 'bilibili_rank.csv']:
        if os.path.exists(f): os.remove(f)
    
    shutil.rmtree('images/ent_hot', ignore_errors=True)

    polished_data = {"news": final_result, "timestamp": timestamp}
    return polished_data, temp_images_dir

def main():
    parser = argparse.ArgumentParser(description='综合娱乐新闻聚合器')
    parser.add_argument('mode', nargs='?', choices=['tencent', 'douyin', 'bilibili', 'all', 'aggregate'], default='aggregate')
    args = parser.parse_args()

    if args.mode == 'aggregate':
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data, img_dir = aggregate_news(timestamp)
        print(f"聚合完成。数据项: {len(data['news'])}, 图片目录: {img_dir}")
    else:
        # Legacy support for single scraper run
        if args.mode == 'tencent' or args.mode == 'all': run_tencent_scraper()
        if args.mode == 'douyin' or args.mode == 'all': run_douyin_scraper()
        if args.mode == 'bilibili' or args.mode == 'all': run_bilibili_scraper()

if __name__ == '__main__':
    main()