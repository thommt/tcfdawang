# Agents 指南

> 目的：为后续自动化/多 Agent 协作提供共识。所有 Agent 在开始工作前应阅读 `spec.md` 与 `frontend_spec.md` 并遵循以下职责与约定。

## 1. Agent 划分

| Agent | 职责概要 |
| --- | --- |
| **Product Agent** | 根据 spec 拆分迭代目标、维护待办、补充业务规则。必要时与用户沟通澄清。 |
| **Backend Agent** | 负责 FastAPI + SQLModel 层实现、数据库迁移、服务逻辑、CSV/抓取导入、LLM 流程编排接口、任务队列（Task）执行器。 |
| **LLM Orchestrator Agent** | 设计 LangChain Prompt、解析器、工具函数；定义各流程（评估、结构化、比较等）的输入输出契约，并提供模拟/测试用例；与 Backend 协作拆分异步任务。 |
| **Frontend Agent** | 实现 Vue 应用（Vite + Pinia/Router），包括题目管理、学习工作台、篇章浏览、抽认卡 UI。 |
| **Data/Infra Agent** | 确定数据库 schema 迁移、图结构存储方式、数据种子、SRS mock 实现、抓题 CLI（`scripts/fetch_questions.py`）以及部署/运行脚本（uv、Docker 示例）。 |
| **QA Agent** | 编写自动化测试（Pytest、Playwright 等）、验证 API/LLM 流程、确保 CSV 导入与抽认卡逻辑正确。 |

## 2. 通用约定

1. **依赖管理**：统一使用 `uv`；requirements 由 Backend Agent 维护。新增依赖需同步更新锁文件及文档。
2. **模块划分**：
   - `app/api`：FastAPI 路由。
   - `app/services`：业务用例。
   - `app/models`：Pydantic schema。
   - `app/db`：SQLModel 实体、迁移。
   - `app/llm`：LangChain chains 与 prompt 模板。
   - `frontend/`：Vue 源码。
3. **数据库图结构**：使用 `paragraph_graph_nodes` / `paragraph_graph_edges` 两张表（详见 spec）。任何 Agent 创建新的结构字段时需给出迁移脚本并更新 schema 文档。
4. **LLM 流程 I/O**：所有 chain 都应返回结构化 JSON（Pydantic 模型），方便持久化与测试；提供 mock 实现以便无 API Key 时开发；所有 LLM 任务通过统一队列（Task）异步执行，支持重试。
5. **错误处理**：API 返回标准化错误响应，前端显示清晰的提示；LLM 调用失败时应缓冲/重试，并允许用户查看日志；任务失败要记录可诊断信息并允许用户重新触发。
6. **文件/编码**：所有文本与源代码文件必须为 UTF-8（无 BOM）、LF 换行；在提交前运行格式化/检查。
7. **TDD 要求**：实现任何功能前应先补齐/更新单元测试，测试需覆盖 happy path 与关键异常。

## 3. 协作流程

1. Product Agent 依据 spec/需求排期，创建 issue/task。
2. 数据/Schema 改动需优先在 `db/schema.md`（待建）中记录，再由 Backend Agent 编写迁移。
3. Backend 与 Frontend 通过 OpenAPI schema 协作；路由变更需更新 `spec.md` 和前端 API 客户端。
4. LLM Orchestrator 提供最小可运行链路（含 Prompt 模板、解析器、假数据），QA Agent 基于此编写测试。
5. Merge 前需运行：后端 pytest、前端单元/构建、lint（ruff/eslint），并附结果；涉及 Task/队列的改动需附上任务处理单测或集成测试。

## 4. LLM 流程约束

- **Answer Evaluation Loop**：必须支持多轮提示，直到用户终止；每轮输出结构化建议（改进点、示例、是否已满足要求），以异步任务形式运行，可暂停/恢复。
- **Structure Extraction**：输出 `Paragraph[]`、`Sentence[]`，包含关系、角色标签；图关系由 Graph Builder 转换。
- **T2 特例**：回答需遵循“开篇→问答对→结尾”脚本；LLM Prompt 与解析器在处理 T2 时必须生成问答对结构（含追问/评论信息）。
- **Comparator**：返回主旨相似度、结构相似度、差异摘要；若差异大于阈值，需提示创建新答案。
- **Refined Answer Generator**：输入现有版本 + 用户最新草稿 + 评估反馈，输出 i+1 文本与亮点说明。
- 所有流程应记录在 `LLMConversation`，包括 prompt、response、模型信息，便于回溯，并在 Task 中记录状态与进度。

## 5. 前端约束

- 使用 Vue 3 + Vite + TypeScript，状态管理优先 Pinia。
- API 调用由统一客户端封装（axios/fetch），包含错误处理与 loading 状态。
- 学习工作台需支持：实时展示 LLM 反馈、用户编辑器（Markdown/富文本）、确认答案流程。
- 抽认卡界面支持键盘快捷键与答题结果上报。
- 全局需提供任务列表/进度指示器，前端通过轮询或 WebSocket 获取 Task 状态，允许用户重试/取消。

## 6. 质量与测试

- 后端：Pytest + httpx TestClient，覆盖核心 API、CSV 导入、SRS 计算。
- 前端：Vitest/Playwright 基础测试。
- LLM：提供 mock（固定 JSON）以便 CI 运行；真实调用需要环境变量 `OPENAI_API_KEY`。
- CSV 导入需提供示例与 schema 文档。

---

该文档为 Agents 的协作契约，随着实现推进可迭代更新。***
