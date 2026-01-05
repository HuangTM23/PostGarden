# 技术栈 (Tech Stack)

## 后端与云端 (Backend & Cloud)
- **核心语言**: Python 3.8+
- **环境**: GitHub Actions (用于每日定时任务执行与产物托管)。
- **数据抓取**: 
    - `requests`: 用于基础 API 调用。
    - `BeautifulSoup4`: 用于 HTML 解析。
    - `Selenium` & `Webdriver-manager`: 用于处理动态加载的网页内容。
- **AI 智能逻辑**: DeepSeek API (用于内容的去重、润色和总结)。
- **编排与流水线**: `pipeline.py`。

## 移动端 (Android Client)
- **核心语言**: Kotlin
- **UI 框架**: Material Design 3 (Material You)。
- **并发处理**: Kotlin Coroutines。
- **网络通信**: OkHttp, Gson (用于解析云端下发的 JSON 数据)。
- **图片加载**: Glide。

## 数据交互 (Data Interop)
- **格式**: 标准化 JSON。
- **传输**: 基于公开链接的被动拉取机制。
