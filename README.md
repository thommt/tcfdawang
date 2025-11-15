# TCF 学习系统

本项目基于 `spec.md`、`frontend_spec.md` 与 `agents.md`，旨在构建一个支持 FastAPI 后端与 Vue 前端的 TCF Canada 学习平台。

## 仓库结构

详见 `docs/project_structure.md`。

## 开发约定

- 统一使用 **UTF-8 (LF)**。
- 全面采用 **TDD**：后端 Pytest，前端 Vitest/Playwright。
- LLM 交互通过 LangChain 模块实现，所有 Prompt 需结构化输入/输出。

后续将依照 spec 分阶段实现 API、前端页面与异步任务队列。
