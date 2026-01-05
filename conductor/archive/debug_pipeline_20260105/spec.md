# Track Spec: 调试并完善云端数据管道 (Pipeline)

## 目标 (Goals)
1.  **修复抓取脚本**: 确保 `fetch_baidu.py`, `fetch_tencent.py`, `fetch_toutiao.py` 能稳定获取数据。
2.  **验证 Pipeline**: 确保 `pipeline.py` 能正确串联抓取、`polish.py` (DeepSeek) 和打包流程。
3.  **标准化输出**: 确保最终生成的 JSON 文件符合 "1+9" 结构且可被 Android 端解析。
4.  **Android 集成**: 验证 Android 端能正确下载并解析 JSON，展示 Hero + List UI。

## 成功标准 (Success Criteria)
- GitHub Actions 运行成功，产出符合规范的 `morning.json` 或 `evening.json`。
- `polish.py` 成功调用 DeepSeek API，生成的摘要准确、无重复。
- Android App 首页能展示最新的 1 条头条和 9 条列表。

## 详细需求 (Requirements)
- **后端**: 
    - 修复爬虫解析错误（如 HTML 结构变化）。
    - 完善 `polish.py` 的提示词（Prompt），确保输出格式严格为 JSON。
    - 在 `pipeline.py` 中添加错误捕获和日志。
- **Android**:
    - 更新 `OkHttp` 请求逻辑，指向 GitHub Actions 产出的正确 URL。
    - 确保 `Gson` 解析模型与后端 JSON 结构一致。
