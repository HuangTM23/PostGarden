# 计划：爬虫重构与优化 (2026-01-14)

## 目标
重构新闻爬虫流程，实现图片下载解耦、分库历史去重、标题党风格标题生成，以及服务器端长图 1:1 顶部裁剪。

## 需求

1.  **图片下载解耦**:
    *   简化原始爬虫脚本 (Baidu, Toutiao, Tencent, World, Entertainment)。
    *   **移除** 抓取时的即时图片下载逻辑。
    *   **保留** 原始图片 URL 到 JSON 输出中。
2.  **分类历史库**:
    *   重构 `HistoryManager` 以支持 `history_home.json`, `history_world.json`, `history_ent.json` 分类。
    *   在发送给 DeepSeek 之前，针对特定类别进行输入去重。
3.  **DeepSeek 与润色优化**:
    *   筛选逻辑：从约 27 条候选中选出 9 条（结合历史库查重 + 自我去重 + 平台多样性）。
    *   **Prompt 升级**: Rank 0 标题必须是“爆炸性/标题党”风格。
    *   **新字段**: 在中间处理的 JSON 中增加 `title0` (原始标题) 和 `source_platform0` (爬虫源平台，如 'baidu', 'bbc') 用于内部处理。
4.  **后处理与图片处理**:
    *   仅利用保留的 URL 为最终入选的 9 条新闻下载图片。
    *   **兜底**: 如果下载失败，根据 `source_platform0` 使用本地公版占位图。
    *   **条件裁剪**: 服务器端检查图片宽高比。**仅针对长图**（例如高度 > 宽度 * 1.2）进行 1:1 顶部裁剪，以防止在 App 端显示效果不佳；正常比例图片保持原样。
    *   **压缩包**: 打包为最终格式（最终面向用户的 JSON 中需剔除 `title0`/`source_platform0` 字段）。
5.  **调试与清理**:
    *   中间 JSON 文件命名前缀增加 `test_`。
    *   更新清理逻辑，确保总是保留*最新*的一套输出结果（不被自动清空）。
6.  **详细中文日志**:
    *   全流程输出清晰、结构化的中文日志。
    *   明确显示当前步骤、正在处理的平台/模块、关键数据统计及状态（成功/失败/兜底）。

## 阶段

### 阶段 1: 爬虫简化 (移除下载)
- [x] 修改 `crawler/homenews/fetch_baidu.py` (仅返回 URL，增加中文日志)。
- [x] 修改 `crawler/homenews/fetch_toutiao.py` (仅返回 URL，增加中文日志)。
- [x] 修改 `crawler/homenews/fetch_tencent.py` (仅返回 URL，增加中文日志)。
- [x] 修改 World News 爬虫 (BBC, CNN, NYT, Sky) 仅返回 URL。
- [x] 修改 Entertainment 聚合器仅返回 URL。

### 阶段 2: 历史记录与去重逻辑
- [x] 重构 `crawler/history_manager.py` 支持 `home`, `world`, `ent` 分类。
- [x] 更新 `pipeline.py` 以在每次运行时初始化/使用正确的历史类别。

### 阶段 3: 管道与润色逻辑 (核心)
- [x] 更新 `crawler/homenews/polish.py` (Home) 和 `crawler/worldnews/process_news.py` (World) 的提示词 (Prompts):
    *   Rank 0 增加“爆炸性/标题党”指令。
    *   确保严格筛选出 9 条。
- [x] 更新 `pipeline.py` 逻辑以注入/保留 `title0` 和 `source_platform0`。

### 阶段 4: 图片处理器与打包
- [x] 创建 `crawler/image_utils.py`:
    *   函数: `download_and_process(url, save_path)` (实现下载及**条件性** 1:1 顶部裁剪)。
    *   函数: `get_placeholder(platform0)` (返回本地资源路径)。
- [x] 更新 `crawler/pipeline.py` 打包函数:
    *   遍历最终 JSON。
    *   调用处理函数。若失败，调用 `get_placeholder`。
    *   在打包 Zip 前清理最终 JSON（移除 `title0`, `source_platform0`）。
    *   中间文件增加 `test_` 前缀。
    *   添加详细中文日志打印。

### 阶段 5: 清理与收尾
- [x] 更新 `crawler/pipeline.py` 清理函数，严格保留最新的一组（不被清空）。
- [x] 验证完整流程。
