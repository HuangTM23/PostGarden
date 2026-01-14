"""
图片处理工具模块
- 下载图片
- 检查长宽比（如果高:宽 > 3，视为长图）
- 长图使用公版图片
- 普通图片直接使用
"""

import os
import requests
import shutil
from PIL import Image
from io import BytesIO

# 公版图片目录
# 修复：使用绝对路径指向当前文件所在目录下的 CoverPictures
COVER_PICTURES_DIR = os.path.join(os.path.dirname(__file__), "CoverPictures")

# 默认图片映射（author/source_platform -> 公版图片文件名）
# 注意：公版图片应该命名为小写，不带特殊字符
PLACEHOLDER_MAPPING = {
    # Home 新闻平台
    "baidu": "baidu.jpg",
    "tencent": "tencent.jpg",
    "toutiao": "toutiao.jpg",
    
    # World 新闻平台
    "bbc": "bbc.jpg",
    "bbc news": "bbc.jpg",
    "cnn": "cnn.jpg",
    "skynews": "skynews.jpg",
    "sky news": "skynews.jpg",
    "nytimes": "nytimes.jpg",
    "new york times": "nytimes.jpg",
    "the new york times": "nytimes.jpg",
    
    # Entertainment 新闻平台
    "tencent_entertainment": "tencent_entertainment.jpg",
    "douyin": "douyin.jpg",
    "bilibili": "bilibili.jpg",
    
    # 备选名称
    "腾讯新闻": "tencent.jpg",
    "百度": "baidu.jpg",
    "今日头条": "toutiao.jpg",
    "腾讯娱乐": "tencent_entertainment.jpg",
    "抖音": "douyin.jpg",
    "哔哩哔哩": "bilibili.jpg",
    "bilibili video": "bilibili.jpg",
    "b站": "bilibili.jpg",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_placeholder_path(author):
    """
    根据 author 获取公版图片路径
    支持多种名称格式和备选方案
    """
    if not author:
        author = "default"
    
    # 规范化 author（小写）
    author_key = author.lower().strip()
    
    # 直接查找映射
    if author_key in PLACEHOLDER_MAPPING:
        filename = PLACEHOLDER_MAPPING[author_key]
    else:
        # 尝试模糊匹配
        filename = None
        for key, value in PLACEHOLDER_MAPPING.items():
            if key in author_key or author_key in key:
                filename = value
                break
        
        # 如果还是没找到，使用 default.jpg
        if not filename:
            filename = "default.jpg"
    
    placeholder_path = os.path.join(COVER_PICTURES_DIR, filename)
    
    # 如果指定的文件不存在，尝试备选方案
    if not os.path.exists(placeholder_path):
        # 尝试找任何 jpg 文件作为备选
        try:
            if os.path.exists(COVER_PICTURES_DIR):
                files = [f for f in os.listdir(COVER_PICTURES_DIR) 
                        if f.endswith('.jpg') and f != 'default.jpg']
                if files:
                    # 优先选择名字相似的
                    for f in files:
                        if author_key in f.lower() or f.lower() in author_key:
                            placeholder_path = os.path.join(COVER_PICTURES_DIR, f)
                            break
                    # 如果没有相似的，就用第一个
                    if not os.path.exists(placeholder_path) and files:
                        placeholder_path = os.path.join(COVER_PICTURES_DIR, files[0])
        except:
            pass
    
    # 最后的兜底方案
    if not os.path.exists(placeholder_path):
        default_path = os.path.join(COVER_PICTURES_DIR, "default.jpg")
        if os.path.exists(default_path):
            placeholder_path = default_path
    
    return placeholder_path

def download_image(url, local_path, timeout=10):
    """
    下载图片
    :param url: 图片 URL
    :param local_path: 本地保存路径
    :param timeout: 超时时间（秒）
    :return: (success, image_object) - 成功返回 True 和 PIL Image 对象，失败返回 False 和 None
    """
    if not url:
        print(f"    [!] 图片 URL 为空")
        return False, None
    
    print(f"    [*] 正在下载图片: {url[:80]}...")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        response.raise_for_status()
        
        # 尝试打开为 PIL Image
        img = Image.open(BytesIO(response.content))
        print(f"    [✓] 图片下载成功，格式: {img.format}, 尺寸: {img.size}")
        return True, img
        
    except requests.exceptions.Timeout:
        print(f"    [!] 图片下载超时 (>10秒)")
        return False, None
    except requests.exceptions.ConnectionError as e:
        print(f"    [!] 连接错误: {type(e).__name__}")
        return False, None
    except Exception as e:
        print(f"    [!] 图片下载失败: {type(e).__name__} - {str(e)[:60]}")
        return False, None

def is_long_image(img):
    """
    判断是否为长图（高:宽 > 3）
    :param img: PIL Image 对象
    :return: True 为长图，False 为普通图
    """
    width, height = img.size
    if width == 0:
        return False
    
    ratio = height / width
    is_long = ratio > 3
    print(f"    [*] 图片尺寸检查: {width}x{height}, 宽高比: {ratio:.2f}, 是否长图: {is_long}")
    return is_long

def convert_rgba_to_rgb(img):
    """
    将 RGBA 图片转换为 RGB
    :param img: PIL Image 对象
    :return: 转换后的 PIL Image 对象
    """
    if img.mode == 'RGBA':
        print(f"    [*] 转换 RGBA 到 RGB...")
        # 创建白色背景
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # 使用 Alpha 通道作为蒙版
        return background
    return img

def download_and_process(remote_url, local_path):
    """
    下载并处理图片：
    1. 下载图片
    2. 检查是否为长图（高:宽 > 3）
    3. 如果是长图，返回 False（使用公版图片）
    4. 如果是普通图片，直接保存并返回 True
    :param remote_url: 远程图片 URL
    :param local_path: 本地保存路径
    :return: True 成功，False 失败（需要使用公版图片）
    """
    success, img = download_image(remote_url, local_path)
    
    if not success or img is None:
        return False
    
    try:
        # 检查是否为长图
        if is_long_image(img):
            print(f"    [!] 检测到长图，使用公版图片替代")
            return False
        
        # 转换 RGBA 为 RGB（避免 JPEG 保存问题）
        img = convert_rgba_to_rgb(img)
        
        # 普通图片直接保存（不裁剪）
        print(f"    [*] 保存图片到: {local_path}")
        img.save(local_path, quality=85)
        print(f"    [✓] 图片保存成功")
        return True
        
    except Exception as e:
        print(f"    [!] 图片处理失败: {type(e).__name__} - {str(e)[:60]}")
        return False

def copy_placeholder(author, local_path):
    """
    复制公版图片到本地
    :param author: 作者/平台信息
    :param local_path: 本地保存路径
    :return: True 成功，False 失败
    """
    try:
        placeholder_src = get_placeholder_path(author)
        
        if not os.path.exists(placeholder_src):
            print(f"    [!] 公版图片不存在: {placeholder_src}")
            return False
        
        print(f"    [*] 使用公版图片: {os.path.basename(placeholder_src)}")
        shutil.copy2(placeholder_src, local_path)
        print(f"    [✓] 公版图片已复制")
        return True
        
    except Exception as e:
        print(f"    [!] 公版图片复制失败: {type(e).__name__}")
        return False
