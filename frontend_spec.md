# 前端界面规格

> 目的：指导 Vue 前端的页面布局、组件与交互实现。与 `spec.md` 数据/流程一致，默认采用 **Vue 3 + Vite + TypeScript + Pinia + Vue Router**，全项目以 TypeScript 实现，UI 组件可选 Element Plus 或 Naive UI。开发过程需严格遵循 TDD：先编写/更新测试，再实现功能，所有 PR 必须附带对应的单元/集成测试。

## 1. 全局架构

- **语言 & 编译**：全部组件、store、API 类型必须使用 TypeScript；启用严格模式（`"strict": true`），IDE lints 需开启 `eslint + typescript-eslint`。
- **TDD 原则**：新增/修改功能前先编写对应的单元/组件测试（Vitest + Vue Test Utils），关键流程必须有端到端测试（Playwright）；CI 不通过测试不得合并。
- **布局**：三栏式主框架（侧边导航 + 顶部工具栏 + 内容区）。
- **状态管理**：Pinia 负责核心状态（题目列表、Session、Task、Lexeme、收藏、设置等），支持持久化部分视图状态（如筛选条件）。
- **API 客户端**：统一封装在 `src/api/`，提供请求/响应类型、错误拦截与 token/headers（如需）。
- **任务与通知**：全局顶部展示任务图标，点击展开抽屉查看队列；操作结果通过通知系统（成功/错误 Toast）反馈。
- **国际化**：暂不实现多语言，但在组件中保留字符串集中管理，未来易于扩展。
- **测试约束**：
  - 页面级交互（题目 CRUD、抓取流程、学习流程、Lexeme 合并等）需有 Playwright 测试脚本。
  - 组件/store 单测使用 Vitest；例如 FilterBar、TaskIndicator、LexemeForm 等需覆盖 props/事件。
  - API 客户端需 mock（msw 或自定义 mock）以验证错误处理逻辑。

## 2. 页面导航

| 路由 | 页面 | 功能概述 |
| --- | --- | --- |
| `/questions` | 题目管理 | 列表、筛选、CRUD、CSV 导入、抓取对话框 |
| `/questions/:id` | 题目详情 | 查看题目元数据、答案组、开始学习/复习、抓取记录 |
| `/sessions/:id` | 学习工作台 | 进行答案撰写、LLM 评估、确认流程 |
| `/answers/:id` | 答案结构浏览 | 段落/句子详情、翻译、图结构、拆分状态 |
| `/flashcards` | 抽认卡训练 | 句子/lexeme 复习、结果提交 |
| `/collections` | 收藏与播放列表 | 管理多个收藏列表/播放列表、播放设置、导出 |
| `/lexemes` | Lexeme 管理 | 查询/编辑/合并/重新关联 |
| `/tasks` | 任务中心 | 查看全部后台任务，支持重试/取消 |
| `/settings/user-profile` | 设置 | 管理全局考生人设、偏好 |

## 3. 共享组件

- **FilterBar**：支持关键字、年份、来源、标签、题型（T2/T3）等筛选。标签选择器从 `/tags` 获取。
- **TagEditor**：题目/答案表单共用，可新增/删除标签，内部调 `QuestionTag` API。
- **TaskIndicator**：显示当前任务数与状态，点击进入任务中心。
- **LLMStatusLog**：在学习工作台和答案详情显示任务日志（来源于 `LLMConversation` 或 `Task.result_summary`）。
- **ConfirmDrawer**：用于批量确认抓取结果、批量导入。

## 4. 题目管理页（`/questions`）

1. **列表区域**
   - 表格列：来源、年份、月份、套题（suite）、题号、题型、slug（根据 source/year/month/suite/number 自动拼接的只读标识）、标题（中文摘要）、标签、最新更新时间、抓取来源（链接图标）。
   - 每行提供 `LLM 生成标题/标签` 按钮（调用 `POST /questions/{id}/generate-metadata`，更新 title + tags）以及编辑/删除操作；编辑表单仅允许修改 title 和 tags，其他字段锁定。
   - 支持分页、多选（批量删除/标签编辑）。
2. **筛选**
   - 顶部 FilterBar；支持按标签、年份范围、题型；实时更新 URL query，便于分享。
3. **操作按钮**
   - `新建题目`：弹出侧栏表单（source/year/month/suite/number/type/title/body/tags）。
   - `导入 CSV`：上传控件，调用 `POST /questions/import`，显示导入结果统计。
   - `抓取题目`：打开模态框，用户输入多个 URL（换行），可附带自定义 source name。提交后触发 `POST /questions/fetch`，返回 Task ID 并跳转至预览面板。
4. **抓取预览**
   - 模态或抽屉展示 `GET /questions/fetch-results?task_id=` 的数据：以表格呈现，每条可编辑 title/body/tags/type，选择“导入”或“丢弃”。
   - 底部 `导入选中` 按钮调用 `POST /questions/import` 或批量 API。

## 5. 题目详情页（`/questions/:id`）

- **基本信息卡片**：显示所有元数据、原始抓取 URL（点击在新标签页打开）、抓取时间、手工编辑记录。
- **标签管理**：内嵌 TagEditor，可即时更新并刷新列表。
- **答案组面板**：
  - 展示每个 `AnswerGroup` 的 descriptor、title、dialogue_profile（若为 T2，显示考官态度/语体等）。
  - 每组内列出版本（version_index、title、状态、创建时间）。
  - 操作：`开始学习`（创建新 Session）、`复习此版本`、`查看结构`（跳转 `/answers/:id`）。
- **抓取历史**：折叠面板显示该题目所有 fetch 记录，可再次触发“重新抓取并比对”功能（调用 fetch API 并自动比对差异）。

## 6. 学习工作台（`/sessions/:id`）

布局：左右分栏。

- **左侧**：题目内容、LLM 反馈历史、任务列表。
  - 题目内容区显示原题文本、标签、来源。
  - 反馈历史列表：每次 `eval` 任务的输出，按时间逆序；可展开查看详情/重新触发。
  - 任务列表：显示该 Session 的 Task 状态（eval, compose, structure...），未完成标记黄色。
- **右侧**：答案编辑器。
  - Markdown/富文本编辑器，支持草稿自动保存。
  - 操作按钮：
    - `提交评估`：触发 `POST /sessions/{id}/llm/eval`（后台任务）。
    - `确认答案`：在评估完成并满意后可点击，调用 `POST /answers/{id}/finalize`。
    - `查看任务`：打开全局任务中心并过滤当前 Session。
  - 状态引导：顶部 Stepper，标示“草稿 → 评估 → 确认 → 结构拆解 → 翻译 → 拆分 → 抽认卡”。

## 7. 答案结构页（`/answers/:id`）

- **摘要区**：显示 Answer title、版本信息、所属 Question/descriptor。
- **段落树**：左侧树/列表显示 Paragraph，点击展开句子（Sentence）。
- **句子卡片**：展示原文、翻译、难度、拆分状态（已/未）。按钮：
  - `生成拆分`（split_phrase）或 `重新拆分`。
  - `收藏句子`。
  - `查看 Lexeme`（弹出当前句子的词块列表，每项可跳转到 Lexeme 管理页面）。
- **图结构视图**（可选）：若已生成 graph，使用力导图或流程图展示；若未生成，显示按钮触发 `POST /answers/{id}/structure-graph`。
- **LLM 日志**：展示与此 Answer 相关的 LLMConversation，支持按目的过滤。

## 8. 抽认卡（`/flashcards`）

- **切换模式**：句子 / Lexeme。
- **队列视图**：显示今日待复习数、已完成数。
- **答题交互**：
  - 句子模式：显示中文或英文提示，输入法语答案或点击“显示答案”；用户选择“对/错/困难”。
  - Lexeme 模式：展示 sense_label/gloss，再让用户说出法语表达。
  - 支持快捷键（1=对，2=困难，3=错）。
- **统计面板**：展示连胜、下次复习日期。

## 9. 收藏与播放列表（`/collections`）

- 左侧导航列出所有收藏列表与播放列表，可创建、重命名、删除、复制。
- 收藏列表视图：
  - 表格列：实体类型（Answer/Paragraph/Sentence/Lexeme）、标题/摘要、来源、标签、备注、添加时间。
  - 支持拖拽排序、批量移除、跳转到实体详情、复制到其他列表。
  - “转换为播放列表”按钮：复制条目到新播放列表，并弹出默认播放设置对话框。
- 播放列表视图：
  - 顶部“全局设置”面板：停顿时长、播放速度、是否播放翻译（及语言）、重复次数、是否播放 Lexeme 音频。调整时提示“将覆盖所有条目的单独设置”。
  - 条目列表：展示顺序、单条播放设置（可覆盖全局）、重复次数、是否播放翻译等；提供拖拽排序、复制、插入空白停顿。
  - 操作按钮：`播放`（启动播放控件）、`导出 MP3`（调用后端合并音频）、`保存设置`、`下载单条音频`。
- 播放控制条（全局）：
  - 底部固定控件，显示当前播放项、进度、剩余条目。
  - 支持播放/暂停/上一条/下一条/重复、切换翻译、调整速度。
  - 集成 Media Session API，允许在后台或锁屏状态下控制。
- 下载 & 导出：
  - 每条条目提供“下载音频”链接（使用句子/lexeme 缓存音频）。
  - 播放列表支持“一键导出”为单个 MP3，供离线设备播放。

## 10. Lexeme 管理（`/lexemes`）

- **搜索栏**：按 lemma、sense_label、POS、收藏状态过滤。
- **表格列**：lemma、sense_label、gloss、pos、引用次数、上次编辑时间、是否人工、收藏/SRS 状态。
- **操作**：
  - `编辑`：侧栏表单修改 sense、翻译、笔记（设置 is_manual）。
  - `合并`：多选后点击“合并”，指定主 Lexeme，显示预览（将迁移 SentenceLexeme、收藏、SRS）。
  - `拆分/重新关联`：在某个 Lexeme 详情页列出引用句子，可移除并分配到新 Lexeme。

## 11. 任务中心（`/tasks`）

- 表格列：任务类型、关联实体（Session/Answer/Question）、状态、进度、开始/结束时间、错误信息。
- 支持过滤（进行中、失败、我的 Session）。
- 行操作：重试、取消、查看日志（链接到 LLMConversation）。
- 全局 TaskIndicator 点击后默认跳转到 `/tasks` 并带过滤条件。

## 12. 设置（`/settings/user-profile`）

- 表单字段：角色背景（中文描述）、沟通风格、语速、语体、偏好主题等。后端用于 `user_profile`。
- 表单应支持保存/重置，保存后提示成功。

## 13. 抓取任务 UI 流程

1. 用户在 `/questions` 点击“抓取题目”，输入 URL 列表，并可指定自定义来源名称、是否立即导入。
2. 提交后显示任务 ID，并提示可在任务中心查看进度。
3. 抓取完成后，自动打开预览面板（或通知）。预览表格提供编辑、选择导入。
4. 导入成功刷新题目列表，并显示导入统计。

## 14. 无障碍与响应式

- 支持键盘导航和高对比度主题（至少为组件库默认方案）。
- 响应式：桌面优先，保证在 1280px 以上布局舒适；在平板上缩为单列，隐藏次级面板（如任务列表可折叠）。

## 15. 开发与测试建议

- 组件层尽量原子化（表单模块化，方便在抓取预览/题目编辑重用）。
- 使用 Storybook 或类似工具展示关键组件（可选）。
- 前端测试覆盖：关键 store/action、API 客户端 mock、核心交互（学习流程、抓取导入、lexeme 合并）。

---

该文档将随实现演进更新，若页面或流程新增/调整，请同步维护。***
