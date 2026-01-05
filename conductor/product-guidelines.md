# 产品准则 (Product Guidelines)

## 系统架构重心 (System Architecture Priority)
本项目的核心是一个**云端数据处理系统**，APP 仅作为展示终端。开发工作的重心应分配如下：
- **80% 后端/云端**: GitHub Actions 流程、Python 爬虫优化、DeepSeek API 集成、数据清洗与结构化。
- **20% 移动端**: Android 数据接收、解析与 Material Design 展示。

## 云端数据管道准则 (Cloud Data Pipeline Guidelines)
- **稳定性优先**: `pipeline.py` 必须具备强大的错误处理机制。单个源（如百度）的抓取失败不应导致整个流程崩溃，应采用降级策略。
- **AI 处理标准化**: `polish.py` 与 DeepSeek 的交互必须标准且可复用。
    - **输入**: 三个平台的原始“指纹数据”。
    - **处理**: 去重、筛选高价值内容、润色摘要。
    - **输出**: 严格的 "1+9" 结构化 JSON 格式。
- **自动化与部署**: 完全依赖 GitHub Actions 进行每日调度。产物（Artifacts）必须通过稳定的 URL 对外暴露，供客户端拉取。

## 客户端交互准则 (Client Interaction Guidelines)
- **极简接收端**: Android 端逻辑应保持“哑终端”状态，不进行任何业务逻辑处理，仅负责渲染 JSON。
- **视觉风格**: 采用 **Material You (Material Design 3)**，以 **Hero + List** 模式展示云端下发的 "1+9" 数据。
- **数据管理**: 支持“混合模式 (Selected Save)”，允许用户将云端最新的简报手动保存至本地存档（"花园"）。

## 扩展性规范 (Scalability)
- **板块化设计**: 后端数据结构设计时应包含 `category` 字段（如 `domestic`, `international`, `entertainment`），为未来扩展预留接口，即使当前仅实现国内版。
