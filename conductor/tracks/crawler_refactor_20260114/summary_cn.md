# 爬虫重构与优化总结 (2026-01-14)

## 任务状态: [已完成]

本次重构旨在优化新闻抓取、筛选、润色及打包流程，重点解决图片质量、内容去重及标题吸引力问题。所有操作均在服务器端 (后端) 执行。

## 1. 核心变更点

### A. 图片处理 (服务器端)
*   **解耦下载**: 原始爬虫脚本不再下载图片，仅保留远程 URL。图片下载推迟到 AI 筛选出最终 9 条新闻后进行。
*   **长图裁剪**: 新增 `image_utils.py`，在下载时检测图片比例。若高度 > 宽度的 **3.0倍** 时，自动执行 **1:1 顶部裁剪**，防止 App 端显示过长。
*   **智能兜底**: 下载失败时，根据新闻来源（如 Baidu, BBC）自动使用目录 `/home/dawn/AndroidStudioProjects/PostGarden/crawler/CoverPictures` 下对应的公版占位图（已校准文件名：baidu.png, BBC.jpeg 等）。

### B. 历史去重 (分库管理)
*   **分库策略**: `HistoryManager` 现在维护三个独立的历史文件：
    *   `history_home.json` (国内)
    *   `history_world.json` (国际)
    *   `history_ent.json` (娱乐)
*   **精准查重**: 各板块仅针对自家历史库进行比对，大幅提高去重准确率，减少输入 Token。

### C. 内容润色 (AI Prompt)
*   **标题党风格**: 修改了 Rank 0 (总结标题) 的提示词，强制要求生成 **“爆炸性/标题党”** 风格的标题，限 20 字以内，拒绝平庸总结。
*   **严格筛选**: 强制要求 AI 从候选池中严格选出 9 条完全不同的新闻事件。

### D. 流程管控 (Pipeline)
*   **全流程中文日志**: 爬虫运行时的所有关键步骤均输出清晰的中文日志，包含进度、来源、成功/失败状态。
*   **调试文件**: 每次运行会生成带 `test_` 前缀的中间 JSON 文件，方便调试数据字段。
*   **清理策略**: 每次运行结束后，严格保留最新的一套 ZIP 包，自动清理旧文件。

## 2. 文件变更清单

| 模块 | 文件路径 | 变更说明 |
| :--- | :--- | :--- |
| **主控** | `crawler/pipeline.py` | 重写。集成新流程，管理分库历史，调用图片处理。 |
| **工具** | `crawler/history_manager.py` | 重写。支持多分类历史库 (`_home`, `_world`, `_ent`)。 |
| **工具** | `crawler/image_utils.py` | **新增**。负责图片下载、长图裁剪 (Pillow)、公版图替换。 |
| **国内** | `crawler/homenews/fetch_*.py` | 移除下载逻辑，仅返回 URL。增加中文日志。 |
| **国内** | `crawler/homenews/polish.py` | 升级 Prompt (标题党)，增加 `title0` 字段传递。 |
| **国际** | `crawler/worldnews/process_news.py` | 升级 Prompt，移除旧版打包逻辑，适配新 Pipeline。 |
| **国际** | `crawler/worldnews/scrape_*.py` | 移除下载逻辑，仅返回 URL。增加中文日志。 |
| **娱乐** | `crawler/entertainment/aggregator.py` | 移除下载/调整大小逻辑，仅返回 URL。 |

## 3. 使用指南

### 运行爬虫
在项目根目录下执行：
```bash
python3 crawler/pipeline.py
```

### 查看结果
*   **最终产物**: `output/Home_*.zip`, `output/World_*.zip`, `output/Entertainment_*.zip`
*   **调试数据**: `output/test_Home_*.json` 等 (包含 `title0` 等内部字段)
*   **日志**: 控制台将直接输出详细的中文流程日志。

## 4. 后续维护
*   若需调整长图裁剪阈值，请修改 `crawler/image_utils.py` 中的 `if height > width * 1.2:`。
*   若需修改“标题党”力度，请调整 `crawler/homenews/polish.py` 和 `crawler/worldnews/process_news.py` 中的 Prompt。
