# Track Plan: 调试并完善云端数据管道 (Pipeline)

## Phase 1: 云端管道修复与 AI 集成调试
- [x] Task: 编写针对 `fetch_*.py` 的单元测试，验证解析逻辑的正确性 b9b5382
- [x] Task: 修复 `fetch_baidu.py`, `fetch_tencent.py`, `fetch_toutiao.py` 中的已知 Bug 34862d8
- [x] Task: 编写针对 `polish.py` 的测试，模拟 DeepSeek API 响应并验证 JSON 构造 4b44f3e
- [ ] Task: 优化 `polish.py` 的 Prompt 和异常处理，确保 1+9 结构的稳定性
- [ ] Task: 完善 `pipeline.py` 的串联逻辑，确保本地模拟运行成功
- [ ] Task: Conductor - User Manual Verification 'Phase 1: 云端管道修复' (Protocol in workflow.md)

## Phase 2: Android 端数据拉取与展示验证
- [ ] Task: 在 Android 端编写针对 JSON 解析模型的单元测试
- [ ] Task: 更新 Android 端网络层，配置正确的 GitHub Actions 数据产物 URL
- [ ] Task: 调整 MainActivity/UI 逻辑，确保 1+9 布局正确渲染
- [ ] Task: 验证“保存到花园”功能的持久化逻辑（单元测试 + 实现）
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Android 端验证' (Protocol in workflow.md)
