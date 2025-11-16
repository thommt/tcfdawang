# TCF 学习系统

本项目基于 `spec.md`、`frontend_spec.md` 与 `agents.md`，旨在构建一个支持 FastAPI 后端与 Vue 前端的 TCF Canada 学习平台。

## 仓库结构

详见 `docs/project_structure.md`。

## 开发约定

- 统一使用 **UTF-8 (LF)**。
- 全面采用 **TDD**：后端 Pytest，前端 Vitest/Playwright。
- LLM 交互通过 LangChain 模块实现，所有 Prompt 需结构化输入/输出。

## 当前状态

- 已提供 FastAPI 骨架及 `/health`、`/questions` CRUD API（使用 SQLModel + SQLite）。
- 前端使用 Vite + Vue3 + TypeScript (Pinia/Vue Router) 初始化完毕。
- 新增可配置的题目抓取器与 API（`POST /questions/fetch`、`GET /questions/fetch/results`），目前支持多个官方口语题发布站点（代称 Seikou、Tanpaku）。
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

后续将依照 spec 分阶段实现 LLM 流程、抓取页面、收藏/播放列表等功能。
