# Initial Concept
第一阶段我们只考虑抓取 `fetch_baidu.py`, `fetch_tencent.py`, `fetch_toutiao.py` 这三个脚本对应平台的数据。
核心架构调整：新闻抓取在 GitHub Actions 上执行，手机端通过链接获取打包好的数据。原始数据会经过 `polish.py` 调用 DeepSeek API 进行润色、去重、筛选和总结。整个流程由 `pipeline.py` 编排。

# 产品指南 (Product Guide)

## 愿景 (Vision)
PostGarden 旨在为日常新闻消费者提供一个统一的平台，通过将来自不同来源的热门话题和新闻汇总到单一、连贯的移动体验中，从而获取跨平台见解。

## 目标用户 (Target Users)
- **日常新闻消费者**：希望在不切换不同应用或网站的情况下，了解多个平台热门话题的个人。
- **信息分析人员**：寻求对比洞察不同平台（例如百度与今日头条）如何优先处理和报道各种主题的用户。

## 核心价值主张 (Core Value Proposition)
- **跨平台见解**：使用户能够比较和对比来自各种区域和全球来源的热门信息。
- **AI 增强的内容质量**：通过 DeepSeek API 提供的去重、润色和总结功能，为用户提供高信噪比的信息。
- **轻量级客户端**：移动端专注于流畅的阅读体验，无需消耗电量和流量进行后台抓取。

## 技术架构与数据流 (Technical Architecture & Data Flow)
1.  **云端执行 (Cloud Execution)**:
    -   **环境**: GitHub Actions。
    -   **入口**: `crawler/pipeline.py` 负责编排整个任务。
    -   **获取**: `fetch_*.py` 脚本负责从百度、腾讯、今日头条获取原始数据。
2.  **智能处理 (AI Processing)**:
    -   **组件**: `crawler/polish.py`。
    -   **功能**: 集成 DeepSeek API，对原始数据进行去重、筛选、润色和总结，生成高质量的结构化数据。
3.  **数据分发 (Data Distribution)**:
    -   处理后的数据被打包并托管（例如通过 GitHub Artifacts 或 Pages）。
    -   Android 客户端通过网络链接请求这些预处理好的数据包。

## 初始范围（第一阶段）(Initial Scope - Phase 1)
- **后端 (GitHub Actions)**: 配置 `pipeline.py` 以串联抓取和 `polish.py` 流程，确保 DeepSeek API 正确集成，并产出客户端可读的 JSON 格式数据。
- **移动端 (Android)**: 开发网络层以定期获取云端生成的“每日简报”数据包，并设计 UI 展示经过 AI 总结的新闻。
