# TCF 学习系统

本项目基于 `spec.md`、`frontend_spec.md` 与 `agents.md`，旨在构建一个支持 FastAPI 后端与 Vue 前端的 TCF Canada 学习平台。

## 仓库结构

详见 `docs/project_structure.md`。

## 开发约定

- 统一使用 **UTF-8 (LF)**。
- 全面采用 **TDD**：后端 Pytest，前端 Vitest/Playwright。
- LLM 交互采用 OpenAI Chat Completions API（`POST /questions/{id}/generate-metadata` 会调用），Prompt 需返回结构化 JSON。

## 当前状态

- 已提供 FastAPI 骨架及 `/health`、`/questions` CRUD API（使用 SQLModel + SQLite）。
- 前端使用 Vite + Vue3 + TypeScript (Pinia/Vue Router) 初始化完毕。
- 新增可配置的题目抓取器与 API（`POST /questions/fetch`、`GET /questions/fetch/results`、`POST /questions/fetch/import`），目前支持多个官方口语题发布站点（代称 Seikou、Tanpaku）。
- 句子拆解已升级为“Chunk → Lexeme”双阶段流程：`POST /sentences/{id}/tasks/chunks` 生成记忆块，`POST /sentences/{id}/tasks/chunk-lexemes` 在 chunk 内抽取关键词；所有质检问题会写入 `sentence.extra.{chunk|lexeme}_issues`，前端会提示用户重试。
- 抽认卡学习流程采用 **按句子推进** 的 guided 模式：同一句子下的 chunk 卡片需要全部复习完毕后，才会出现对应的整句卡片；完成该句后自动切换到下一句。需要按 chunk/句子/lexeme 独立练习时，可切换至 manual 模式使用传统过滤器。
- `/llm-conversations` API 及对应前端页面可查看最近的 LLM 调用记录，包含 prompt 与输出，便于调试/追踪拆分质量。
- 参考 `spec.md`、`frontend_spec.md` 获取业务与页面细节。

## 本地运行

```bash
# 使用 uv（推荐）安装依赖
uv sync --dev

# 运行后端（根目录）
# 若想模拟“前面有反向代理带 /api 前缀”的场景，可以：
# uv run uvicorn app.main:app --reload --root-path /api
# 这样 API 挂在 /api 下，与部署一致

# 后端测试
uv run pytest

# 前端使用 pnpm（默认通过 Vite proxy 访问 `http://localhost:8000/api`，如需自定义可设置 `VITE_API_BASE_URL`）
cd frontend
pnpm install
pnpm dev

# 前端单测 / 端到端测试
pnpm test:unit
pnpm test:e2e
```

## LLM 配置

若要启用“LLM 生成标题/标签”按钮，需要在后端环境变量中设置：

- `OPENAI_API_KEY`：必填，用于访问 OpenAI 兼容接口。
- `OPENAI_MODEL`：可选，默认 `gpt-4o-mini`。
- `OPENAI_BASE_URL`：可选，自建代理时填写对应地址（默认 `https://api.openai.com/v1`）。

元数据生成功能基于 LangChain（ChatOpenAI + JSON 输出解析），无需手写 HTTP 调用；前端在题目管理列表中每行都可以点击 “LLM 生成标题/标签” 调用 `POST /questions/{id}/generate-metadata`，服务端会写入新的中文标题以及最多 5 个标签。

> 注意：项目会在启动时通过 `python-dotenv` 自动加载 `.env` 文件，只需复制 `.env.example` 后填入上述变量即可，无需手动 `export`。

## Fetcher 域名哈希

抓取器不会在仓库中保存明文站点域名，`config/fetchers.yaml` 中的 `domain_hashes` 是域名（小写、去空格）的 SHA-256 哈希值。可用下面的脚本生成：

```bash
uv run python - <<'PY'
from app.fetchers.utils import hash_domain
print(hash_domain("example.com"))
PY
```

把生成的哈希填入 `domain_hashes`，抓取时程序会对输入 URL 的域名做同样处理以匹配对应的 fetcher。

## 任务中心

后端提供了 `/tasks` API，可按 `session_id`、`question_id`、`task_type`、`status` 查询任务列表；前端 `/tasks` 页面展示所有 LLM 评估/生成等任务，便于查看状态与跳转到对应 Session。

后续将依照 spec 分阶段实现 LLM 流程、抓取页面、收藏/播放列表等功能。

## 未来计划

以下能力在 `spec.md` 中已有规划，尚未在当前代码中落地，列为近期待办：

1. **CSV 导入**：实现 `/questions/import` API 及题目管理界面的 CSV 上传对话框，用于批量导入/更新题目。
2. **篇章语义图与角色标签**：在结构拆解阶段写入 `semantic_label`、问答角色，并生成句子关系图以展示篇章逻辑。
3. **T2 对话模式优化**：落实问答对结构、考官/考生人设配置，以及“按问答对”抽认卡练习流程。
4. **收藏 / 播放列表**：新增 Favorite/Collection 模型和相关 API，使用户能够按自定义列表或收藏实体启动学习/复习。
5. **实时任务推送**：提供 WebSocket/SSE 渠道，将 LLM 任务状态实时推送给前端，减少轮询。
6. **定制化学习模式**：接入真正的 SRS（SM-2/FSRS）、支持收藏专练/答案版专练，并新增“答案复写自测”流程（仅对比反馈，不生成新答案或抽认卡）。
