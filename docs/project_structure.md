# 项目目录结构规划

> 目标：在着手编码前明确后端、前端与文档位置，方便 TDD、代码生成与 Agent 协作。

## 顶层

```
.
├── app/                    # 后端 FastAPI 代码
│   ├── api/                # 路由定义（REST / WebSocket）
│   ├── services/           # 业务逻辑（题目、Sessions、Tasks、LLM orchestrators的入口）
│   ├── models/             # Pydantic schema / 请求响应模型
│   ├── db/
│   │   ├── base.py         # SQLModel/SQLAlchemy 初始化
│   │   ├── schemas/        # SQLModel 实体定义（Question, Answer, Lexeme 等）
│   │   └── migrations/     # Alembic 或其他迁移脚本
│   ├── llm/                # LangChain prompt、chain、parser、mock
│   ├── tasks/              # 后台任务调度/执行（Task 队列实现、worker）
│   ├── repositories/       # 数据访问封装（可选）
│   ├── config/             # 配置加载（.env、settings）
│   ├── scripts/            # 实用脚本（数据种子、维护工具）
│   ├── tests/              # Pytest 测试（覆盖 API、服务、LLM mock）
│   └── main.py             # FastAPI 应用入口
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios/fetch 封装（TypeScript interfaces）
│   │   ├── components/     # 通用组件（FilterBar、TaskIndicator 等）
│   │   ├── stores/         # Pinia store
│   │   ├── views/          # 页面组件（Questions, Sessions, Lexemes...）
│   │   ├── router/         # Vue Router 配置
│   │   ├── utils/          # 工具函数（含类型定义）
│   │   └── styles/         # 全局样式
│   ├── tests/
│   │   ├── unit/           # Vitest + Vue Test Utils
│   │   └── e2e/            # Playwright
│   ├── vite.config.ts
│   └── tsconfig.json
├── docs/
│   ├── project_structure.md    # 本文件
│   └── references/             # 参考脚本/规格
├── spec.md
├── frontend_spec.md
├── agents.md
└── README.md（待建）
```

## 说明

- **TDD**：后端在 `app/tests` 中维护 Pytest；前端分别在 `frontend/tests/unit` 与 `frontend/tests/e2e` 中维护 Vitest/Playwright，所有功能需先写测试。
- **脚本与工具**：未来会把抓题逻辑集成进 API，不在仓库根目录存放一次性脚本；若需保留参考代码，放入 `docs/references/`。
- **Docs**：规范性文件（spec、frontend_spec、agents 等）位于根目录；项目结构、参考脚本说明放在 `docs/` 下，便于查阅。

如需新增模块（例如 CLI 客户端、桌面应用），按相同模式在顶层创建目录并在本文件中更新。***
