# 项目规格说明（TCF 学习系统）

## 1. 概述

- **目标**：构建一个专注 TCF Canada 口语 Tache 2 / Tache 3 的学习与题库管理系统，支持 Web 前端，后端以 FastAPI 为核心，LangChain 负责与 OpenAI LLM 交互。
- **运行栈**：Python（使用 `uv` 管理依赖）、FastAPI + Pydantic、SQLite（可替换 PostgreSQL）、LangChain、Vue 前端。
- **部署形态**：首阶段以本地/自托管为主，支持将来容器化；默认 SQLite 嵌入式数据库，保留 PostgreSQL 兼容层。

## 2. 范围与非目标

### 2.1 功能范围
1. **题目管理**
   - CRUD 表单（来源、年/月、套题、题号、题型 T2/T3、标题、详情、任意标签）。
   - CSV 导入（同来源+年+月+套题+题号唯一；重复时执行更新）。
2. **学习流程**
   - 选题 → 用户作答 → LLM 多轮评估/反馈 → 确认最终答案 → LLM 拆解 & 构建篇章结构 → 句子/短语抽认卡学习。
   - 复习时比较主旨/结构，自动判断是否建立新答案；若沿用原主旨，则标注不足并生成 i+1 版本，再进入学习模式。
3. **篇章结构与句子管理**
   - 答案拆解为段落、语块、句子；句子带中英翻译。
   - 可选触发“句子 → 记忆 Chunk → 关键词 Lexeme”两段式拆分：先将句子拆成 3-6 个记忆块（带中英翻译），再针对每个 chunk 生成关键词/词条，便于抽认卡复习。
   - 将段落/语块关系存为图（顶点/边）以表达篇章逻辑。
4. **抽认卡训练**
   - 支持句子级与词块级练习，默认为固定间隔复习策略；未来可替换为真正的间隔重复算法。
5. **LLM 集成**
   - LangChain 封装 OpenAI API；定义多个独立 flow：评估反馈、答案标题/标签生成、篇章结构分析、句子拆分、词块拆解、复习时主旨比较与 i+1 生成等。
6. **前端**
   - Vue 单页应用：题目管理页面、学习工作台、抽认卡训练界面、答案/句子浏览视图。

### 2.2 非目标（首阶段）
- 暂不实现用户体系/权限（单人使用假设）。
- 暂不提供导出功能。
- 暂不支持浏览器端 IndexedDB、本地离线同步。
- 无多模型/自托管 LLM 适配（仅 OpenAI）。

### 2.3 非功能性要求
- **编码规范**：仓库所有文本与源代码文件采用 UTF-8（无 BOM）、LF 换行；在 CI 中加入格式检查。
- **测试策略**：每个功能自搭建阶段起即配套最小化单元测试/集成测试，遵循 TDD；提交需通过 pytest、前端测试及 LLM mock 流程。

## 3. 系统架构

```
Vue SPA  →  FastAPI (REST/WS)  →  Service 层  →  Repository 层  →  SQLite/PostgreSQL
                                   ↓
                                 LangChain Orchestrators
```

- **API 层**：FastAPI 提供 REST（题目管理、学习会话、抽认卡数据、CSV 导入）。必要时使用 WebSocket 推送 LLM 反馈状态。
- **服务层**：组织业务流程（题目 CRUD、学习流程、篇章拆解、复习判定等），隔离 LLM 调用与数据库事务。
- **数据访问**：使用 SQLAlchemy/SQLModel，抽象 `Repository` 支持 SQLite 与 PostgreSQL。图结构以顶点/边表落地。
- **LLM 流程**：LangChain 工程层封装 Prompt、Parser、工具函数。每个流程（评估、结构化等）作为可测试的模块。
- **前端**：Vue + Vite（或 Nuxt 作为 SPA 模式），调用 REST API；后续可集成组件库（Element Plus / Naive UI）。

## 4. 数据模型（初稿）

| 实体 | 关键字段 |
| --- | --- |
| `Question` | id、type(T2/T3)、source、year、month、suite、number、title（LLM/用户生成的简短中文总结）、body、created_at、updated_at；返回给前端时根据 source/year/month/suite/number 自动拼出 slug（如 `RE202508.T3.P04S01`），仅用于展示 |
| `AnswerGroup` | id、question_id、slug（可读标识）、title（LLM 生成的简短中文总结）、descriptor（对立场/主题/主旨的简短描述，如 support/oppose 或 “math”）、dialogue_profile(json，记录 T2 对话设定：考官设定、考生临时人设、态度、语体、语法难度、提问深度等)、created_at |
| `Answer` | id、answer_group_id、version_index（最新为最高）、status(active/archived)、text、title、created_at |
| `Paragraph` | id、answer_id、order_index、summary、role_label（如 intro/body/conclusion 或 T2 的 opening/turn/closing）、semantic_label（可选，用于描述语块主题） |
| `Sentence` | id、paragraph_id、order_index、text_fr、translation_en、translation_zh, difficulty(optional) |
| `SentenceChunk` | id、sentence_id、order_index、text、translation_en、translation_zh、chunk_type(可选)、extra |
| `Lexeme` | id、headword(原 lemma)、sense_label、gloss、pos_tags(enum: noun/verb/adj/adv/expr/… )、translation_en、translation_zh、complexity_level(enum: A1~C2)、hash(基于 headword+sense+chunk text)、extra |
| `ChunkLexeme` | chunk_id、lexeme_id、order_index、role? |
| `Session` | id、question_id、answer_id?、user_answer_draft、session_type(first/review)、status(enum:draft/in_progress/submitted/completed)、progress_state(json，记录反馈轮次、LLM 日志指针等)、started_at、completed_at |
| `Task` | id、session_id?、answer_id?、type(enum: eval, compose_answer, structure, translate, split_phrase, compare, gap_highlight, refine, …)、status(enum: pending/running/succeeded/failed/canceled)、payload(json)、result_summary(json)、progress(0-1)、error_message、created_at、updated_at、conversation_id? |
| `LLMConversation` | id、session_id、task_id、purpose(eval/structure/compare/phrase_split等)、messages(json TEXT/JSONB)、result(json TEXT/JSONB)、model_name、latency_ms |

> **LLMConversation 存储**：`messages` 与 `result` 字段需使用大容量类型（SQLite TEXT / PostgreSQL JSONB）以容纳完整对话记录；必要时可启用压缩或归档策略，确保长对话不会截断。`Task` 只记录执行状态与 `conversation_id` 引用，具体 prompt/response 由 `LLMConversation` 保存。
| `ParagraphGraphNode` | id、answer_id、paragraph_id、label、metadata(json) |
| `ParagraphGraphEdge` | id、answer_id、from_node_id、to_node_id、relation(enum: support/contrast/example/summary/follow_up/clarification/contain/expand)、metadata(json，可存权重/注释) |
| `FlashcardProgress` | id、entity_type(sentence/chunk/lexeme)、entity_id、last_score、due_at、streak、interval_days |
| `Favorite` | id、entity_type(answer/paragraph/sentence/lexeme)、entity_id、note、created_at |
| `QuestionTag` | id、question_id、tag |

> **图结构设计**：段落拆解后，可选地调用结构关系分析任务，生成节点列表（指向 Paragraph）以及边关系（支持 support/contrast/example 等语义）。若用户未触发该分析，则不生成图数据，默认仅使用段落顺序。后续学习场景中可根据 Graph 数据做篇章对比或可视化。

> **答案分组说明**：`descriptor` 字段用来概括答案的主旨或主题——对于需要表态的问题，可取值如 `support`/`oppose`；对于开放题（例如“最喜欢的科目是什么”），则可用 `math`、`physics` 等描述内容的标签。若题目存在多个主旨/结构完全不同的回答，就分别建立 `AnswerGroup(descriptor=…)`。T2 对话还可利用 `dialogue_profile`（例如 `examiner_attitude=stern`、`detail_level=concise`、`user_persona` 来源于全局设置）区分“同主题但不同考官态度/语体/人设”的答案组。

> **Chunk & Lexeme 拆分说明**：对句子进行拆解时，先触发 `chunk_sentence` 任务生成 3-6 个记忆块（`SentenceChunk`，含原文与中英翻译，顺序与句子对应）；通过质检确保 chunk 覆盖与翻译一致并可重复迭代。随后触发 `lexeme_from_chunks` 任务：以 chunk 为输入，生成若干 `Lexeme`（命名为 headword、附带 sense/gloss/pos/difficulty，并与 chunk 建立 `ChunkLexeme` 关联）。`Lexeme` 可跨句复用，`ChunkLexeme` 仅与所属 chunk 关联，无需对句全局排序。前端需显示句子是否已有 chunk/lexeme，可单独重试 chunk 或 lexeme 任务。
>
> 质检失败时需要记录问题（`chunk_issues` / `lexeme_issues`）到 `sentence.extra`，并在 LLMConversation 中保留完整 prompt 与失败原因，前端应提示用户并允许重试。

## 5. 关键流程

### 5.1 题目导入
1. 用户上传 CSV。
2. FastAPI 解析并验证（Pydantic Schema）。
3. 对每行：按照唯一键（source, year, month, suite, number）查找现有题目，存在则更新；否则创建。
4. 记录导入日志并返回统计。

### 5.2 首次学习流程
> **默认 Session 学习路径**：每次 Session（无论首次还是复习）都遵循“用户先独立写完整草稿 → 触发评估任务 → 阅读反馈并决定下一步 → 如有需要，再触发 LLM 生成范文 → 对生成结果执行结构/翻译/Chunk/Lexeme 拆解 → 进入 chunk→句子学习”的顺序。首次 Session 结束后，题目至少会拥有一个 `AnswerGroup` 与其 `Answer(version_index=1)`，并在 `AnswerGroup.descriptor`/`dialogue_profile` 中记录主旨与人设。
1. 用户在前端选择题目并点击“开始学习”，系统在后台自动创建 `Session(session_type=first)`（用户不直接管理 Session 实体）。
2. 用户录入答案（富文本/Markdown），前端调用 `POST /sessions/{id}/answers/draft`。
3. 服务层调用 LangChain 流程“Answer Evaluation”，执行多轮对话（每轮提供指导、要求用户改进）。该评估通过异步任务（`Task` type=`eval`）完成，`Session.progress_state` 持久化当前轮次、草稿与 LLM 消息，用户可在前端查看任务进度、必要时手动重试。
4. 用户确认最终答案 → 生成 `AnswerGroup`（若不存在，触发 LLM 生成 title/descriptor）与 `Answer(version_index=1)`。
5. LangChain 流程分阶段、异步执行（每个阶段对应一个 `Task`）：
   - **AnswerComposer**（task type=`compose_answer`）：根据题型、风格、难度要求生成自然连贯的法语文本（确保满足词汇/语法/篇章框架约束；T2 需生成考官/考生对话，结合全局 `user_profile` 与临时设定，生成自然的提问、评论、追问，并遵守 `dialogue_profile` 的态度、详尽度、语体设置），输出最终 `Answer.text`。
   - **StructureExtractor**（`structure`）：在 `Answer` 固化后，再独立调用 LLM 拆解段落→句子→关系，返回 JSON（包括排序、角色、关系，T2 需识别追问链路、角色以及“问/答/追问/评论”类型）。
   - `GraphBuilder`（`structure_graph`，可选）：从结构 JSON 解析节点与边，写入图表。仅在用户主动触发“篇章图分析”或题目设置要求时运行；默认可跳过，仅保留段落顺序。
   - `SentenceTranslator`（`translate`）：为每个句子生成中英翻译。
   - **ChunkExtractor**（`chunk_sentence`）：对选定句子调用 LLM，将句子拆成若干个 `SentenceChunk`（含原文与中英翻译），并进行质检（覆盖度、语法完整性）。Chunk 记录直接与句子关联，可多次重试。
   - **LexemeExtractor**（`lexeme_from_chunks`）：以 chunk 输出为输入，调用 LLM 为每个 chunk 提取 1~N 个关键词/中心词，生成 `Lexeme` 并通过 `ChunkLexeme` 关联。词性/难度需匹配约定枚举；若命中已有 lexeme 则复用。
   - 所有 Task 均进入全局队列异步执行；前端通过任务 API 轮询/订阅进度，用户可离开页面稍后再查看结果；在答案详情页需展示尚未完成/失败的任务，并提供单个任务的重试按钮。
6. 生成抽认卡初始计划：为句子/短语创建 `FlashcardProgress`，设定固定间隔（如 1/3/7 天）。

### 5.3 复习流程
1. 用户再次选择题目并进入复习界面时，系统自动创建 `Session(session_type=review)`。
2. 用户提交新答案草稿。
3. LangChain 流程 `AnswerComparator`（task type=`compare`）对比主旨与结构：
   - 判断类别：`MAJOR_SHIFT`（主旨或结构变化大） vs `ALIGNED`。
   - 若 `MAJOR_SHIFT`：提示用户创建新 `AnswerGroup`（不同立场/结构），其 version_index 从 1 开始。
4. 若 `ALIGNED`：
   - `GapHighlighter`（task=`gap_highlight`）标出未覆盖段落/句子、语法词汇问题。
   - `RefinedAnswerGenerator`（task=`refine`）在保持主旨结构的前提下，融合用户新答案亮点生成 `Answer` 的下一版本（version_index +1）。
5. 触发与首次相同的结构化与抽认卡流程；仅对新/变更句子更新 Flashcard 进度。
6. 复习 Session 完成后，也必须重新执行 chunk→句子学习，以确保 flashcard 数据覆盖该版本（不论是新答案组还是既有组的 i+1 版本）。

### 5.2.1 自动化任务状态机
为保证中断可恢复且用户不会跳过关键步骤，后端 `Session.progress_state.phase` 需遵循以下状态机，并在每个阶段自动触发对应任务（同时保留手动调试按钮用于重试）：

1. `draft`：用户编辑草稿，仅允许保存或点击“请求评估”。保存后立即触发 eval 任务。
2. `await_eval_confirm`：eval 成功后自动触发 compare；compare 成功则进入下一个阶段。若 compare 判定需新答案组，则提示用户确认创建（phase 仍为 `await_eval_confirm`，直到用户确认）。
3. `gap_highlight`：对于需要复用现有答案组的场景，compare 结束后自动触发 GapHighlighter；若 compare 决策为新组，可跳过该阶段。
4. `refine`：GapHighlighter 完成后自动执行 Refined Answer 生成；用户确认采用后进入 `structure_pipeline`。
5. `structure_pipeline`：串行触发 `structure`、`sentence_translate`、`chunk_sentence`、`chunk_lexeme`。任一任务失败时 phase 保持不变，用户可在调试按钮中单独重试。
6. `learning`：当结构/翻译/拆分全部完成后，phase 进入 `learning`，前端仅展示 chunk→句子学习按钮。所有句子完成 chunk 生成后，允许用户点击“完成本轮学习”。
7. `completed`：用户点击“完成本轮学习”或系统检测到全部 chunk 学习完毕时，将 Session 状态设为 completed，并在前端隐藏草稿/评估等入口。

> 为保障可维护性，自动流程在每个阶段都需记录最近一次任务的结果与失败信息，并在 UI 提供一个“调试/手动操作”面板，允许用户手动重试 eval/compare/gap/refine/structure/translate/chunk/lexeme 等任务。

### 5.4 抽认卡（固定间隔 mock SRS）
1. 后端根据 `FlashcardProgress.due_at` 输出今日到期卡片，分为两种模式：
   - **Guided（默认）**：按句子推进。若某句还有 chunk 卡片到期，则先返回该句的 chunk 卡（按 chunk 顺序/到期时间排序），所有 chunk 复习完成后才返回同一句的 sentence 卡，再切换到下一句。Guided 模式忽略 lexeme 卡片。
   - **Manual**：与早期版本一致，可通过 `entity_type=chunk/sentence/lexeme` 过滤，适合针对特定实体单独训练或排查问题。
2. 默认 Session 的 Guided 抽认卡训练必须做到“本轮掌握”：若用户在当前会话中对某张卡的评分 < `掌握`（score=5），则该卡立即排到本轮列队末尾，直至获得 `掌握` 才会从本轮列表中移除；全部卡片都达到 `掌握` 后才能解锁“标记学习完成”。
3. 前端 `FlashcardsView`：
   - 默认进入 Guided 模式，自动呈现“本句 chunk → 本句整句 → 下一句”的序列；同时保留手动筛选按钮以切换到 chunk/句子/lexeme 独立练习。
   - 支持 `answer_id` 过滤：当用户从某个答案详情页或收藏入口点进来时，仅复习该答案关联的 chunk/句子/lexeme。
   - 每张卡片显示来源句/段落信息与翻译；若 `sentence.extra` 有 `chunk_issues` 或 `lexeme_issues`，在 Guided 模式下提示用户是否需要重试拆分任务。
4. 用户提交结果（对/错/困难），后端更新 `streak`、`interval_days`（使用简化表，例如 1→3→7→14→...），同时记录答题日志；Guided/Manual 模式共享同一套 `FlashcardProgress` 数据。
5. 抽认卡调度可通过后台任务（批量更新 due_at、生成 new cards）运行，避免长事务。

### 5.5 T2 对话结构特例
1. **固定架构**：每个 T2 答案版本包含：开篇（引导/问候）、若干问答对（`QuestionPrompt` + `Response` + 可选追问/评论）、结尾（告别/总结）。需在 `Paragraph` 中标注 `section_type`/`semantic_label` 以区分这些固定块，并记录对应的角色（考官/考生）、追问层级等信息。
2. **学习流程调整**：
   - 在首次与复习阶段，LLM 反馈需遵守对话脚本格式，确保每次迭代都包含完整的问答对。
   - 结构拆解时，`Paragraph` 需映射至开篇、问答对、结尾等角色；句子关系图可简化为按对话顺序的链式结构，并附加“follow-up”“clarification”等关系，通过 `semantic_label`/metadata 表示具体语块，追踪追问链路。
   - 抽认卡训练支持“按问答对”模式：先提示对方提问，再要求用户复述回答；必要时加入追问提示以模拟真实对话。
3. **对话设定**：T2 答案需先调用 `AnswerComposer` 生成自然流畅的双人对话（考官/考生角色、态度、语体、追问方式明确），可结合全局 `user_profile`（从用户设置中获取）与每次会话的临时设定。前端可配置考官态度（友好/严苛）、话题延展度、语法难度等；所选设定写入 `AnswerGroup.dialogue_profile`，以便区分不同 T2 答案组（例如“友好版”“严苛版”“跨文化版”）。
4. **版本管理**：虽然 T2 结构固定，但仍遵循“答案组 + 多版本”模型；`AnswerComparator` 在判定差异时重点考察讨论内容主题、双方人设、考官态度、问答对数量/内容是否变化，以决定是否生成新答案或升级为 i+1 版本。

### 5.6 后台任务与重试
1. 所有 LLM 相关步骤（评估、AnswerComposer、结构化、翻译、拆分、比较、Gap 标注等）都生成 `Task` 记录，进入全局任务队列（可选用 Celery/RQ/BackgroundTasks 等实现），确保异步执行，不占用长连接。
2. 前端需提供“任务中心”与 Answer 详情页的任务面板，展示当前 Answer/Session 的任务列表、状态、进度、最近日志。
3. 用户可以：
   - 手动重试单个失败任务（如结构化卡住）。
   - 补充尚未执行的任务（例如 Answer 已生成但还未翻译，可单独发起 `translate` 任务）。
   - 取消长时间执行的任务。
4. API 层需提供创建/重试/取消任务的接口，并保证任务与 Session/Answer 的权限绑定。

### 5.7 收藏与复习配置
1. 任意 `Answer`、`Paragraph`、`Sentence`、`Lexeme` 都可收藏到 `Favorite` 表；前端在对应视图提供“收藏/取消收藏”操作，并允许填写备注。
2. `FlashcardProgress.entity_type` 支持 `lexeme`：一旦多个句子引用同一 `Lexeme`，其复习进度共享，避免重复练习。
3. 当句子未进行拆分时，收藏列表中仍只展示 `Sentence`；拆分后可选择收藏某个语义片段或整体句子。
4. Question 标签使用 `QuestionTag` 表维护，便于按标签过滤；导入/编辑题目时同步更新该表。

### 5.8 题目抓取（Web UI）
1. 在题目管理界面提供“抓取题目”对话框，允许用户输入一个或多个 URL（例如若干站点的口语题页面）。前端将 URL 列表提交给后端 API（`POST /questions/fetch`），后端基于配置化抓取器（如 Seikou/Tanpaku）执行解析。
2. 抓取规则：
   - 识别 “Tâche / Partie / Sujet” 层级，组合生成唯一 slug（例：`202510.T3.P1S2`）。
   - 自动解析页面标题中的月份/年份；若缺失可由用户通过界面补充。
   - 默认将 `tache=2` 归类为 T2，`tache=3` 为 T3；其它值可忽略或显示警告。
3. 提交抓取任务后，后端创建 `Task(type=fetch_questions)`，异步抓取并将解析结果暂存（可写入临时表或直接生成待确认列表）。
4. 前端提供“抓取结果预览”表格：显示抓取出来的题目字段（来源、日期、Tache、Partie、Sujet、文本等），允许用户逐条编辑/确认或删除。
5. 用户确认后，调用 `POST /questions/import` 或专用 API，将选定题目写入数据库；利用 `(source, year, month, suite, number)` 作为唯一键决定更新/创建，slug 仅用于展示。
6. 新增 `POST /questions/fetch/import`：按 task_id 批量写入抓取结果，默认导入所有结果；如遇重复题目或未找到任务则返回可解析的错误。
7. 错误处理：对请求失败/解析异常的 URL 在 UI 上显示错误信息，并允许重新抓取；所有抓取过程记录日志。
7. **抓取器抽象与配置**：
   - 定义 `BaseQuestionFetcher` 接口（输入：URL + 配置；输出：标准化的题目信息），具体站点可实现各自的解析逻辑。
   - 在 `config/fetchers.yaml`（或类似文件）中列出可用抓取器，配置项包括：匹配域名/路径、CSS 选择器、标题提取正则、Tâche/Partie/Sujet 层级解析规则等。
   - 后端 `fetch` 任务根据 URL 匹配到的配置加载对应抓取器，允许通过配置文件轻松调整解析规则，而不修改代码。
   - 若 URL 不在配置范围内，则返回可解析的错误信息，由前端提示用户手动处理或后续配置新的抓取器。

### 5.9 Lexeme 管理与合并
1. 前端提供“Lexeme 管理”页面，列出每个词/短语的 `headword`, `sense_label`, `gloss`, 引用次数、收藏/SRS 状态。
2. 用户可手动：
   - 编辑 `sense_label/gloss/translation`（将 `is_manual` 置为 true）。
   - 合并多个 Lexeme（选择主条目，系统更新所有 `ChunkLexeme.lexeme_id` 指向主条目，旧条目标记为 archived）。
   - 拆分/重新关联：从 `ChunkLexeme` 中解除与某个 Lexeme 的关联，转而绑定新的条目或创建新的 Lexeme。
3. API 需提供：
   - `PUT /lexemes/{id}` 更新单个 Lexeme（含 sense/翻译）。
   - `POST /lexemes/{id}/merge` 将多个 lexeme 列表合并至目标 ID。
   - `PUT /sentences/{sentence_id}/lexemes` 批量更新某句与 Lexeme 的关联。
4. 合并时需同步更新 `FlashcardProgress` 与收藏，使其指向主 lexeme，保留历史记录。
5. 抓取题目产生的 `source_url`、`source_name` 应在 Question 中记录，供后续溯源；题目详情页显示原始 URL 并可一键重新抓取/更新。

### 5.10 收藏/播放列表与 TTS（下一期扩展）
1. **多收藏列表**：
   - 新建 `Collection` 表（id、name、description、type(enum: favorite/playlist)、settings(json)、created_at、updated_at）。
   - `CollectionItem` 表（collection_id、entity_type(answer/paragraph/sentence/lexeme)、entity_id、order_index、per_item_settings(json)、repeat_count）。
   - 允许一个实体加入多个收藏列表；原 `Favorite` 可视为系统默认收藏列表。
2. **播放列表**：
   - 播放列表由收藏列表复制生成，允许追加播放专属设置，如：播放顺序、全局句子停顿、播放速度、是否播放翻译（及选择翻译语言）、重复次数。
   - 用户可拖拽重排、复制某个条目、对单个条目覆盖全局设置。若启用全局设置覆盖，需弹窗提示会影响所有条目。
3. **TTS 接口与存储**：
   - 句子级音频：首次播放时调用 TTS（OpenAI / 其他 API），生成 `sentence_id` 对应的音频文件（推荐保存为 `audio/sentences/{sentence_id}.mp3`），并记录 `AudioAsset` 表（id、entity_type、entity_id、locale、voice、path、duration_ms、created_at、generated_by）。
   - 句子翻译 TTS：用户播放时才生成并缓存（不同语言分别存储）。
   - Lexeme（词/短语）音频：按需生成并缓存。
   - 篇章音频：通过拼接句子音频临时合成，不持久化整篇文件，但允许用户导出时在后端生成合并音频。
   - 播放列表音频：可提供“导出 MP3”功能，将所选条目按播放设置合成一段音频供下载。
4. **播放器行为**：
   - 前端提供独立“播放列表”页面：展示条目顺序、每条的设置、拖拽、复制、删除。
   - 播放时使用 Web Audio API 或 Media Session API：即使 app 不在前台也可继续播放，并向系统注册播放控制（播放/暂停/下一条等）。移动端需兼容 OS 的全局播放控制。
   - 支持全局设置（停顿、速度、翻译开关）与 per-item 设置，UI 清楚提示覆盖关系。
5. **接口示例**：
   - `POST /collections`、`PUT /collections/{id}`、`DELETE /collections/{id}`
   - `POST /collections/{id}/items`（批量添加）、`PUT /collection-items/{id}`（更新顺序或设置）、`DELETE /collection-items/{id}`
   - `POST /audio/generate`（参数：entity_type/entity_id/voice/locale），返回音频资源 ID；若已存在则直接返回。
   - `GET /audio/{id}` 下载音频；`POST /playlists/{id}/export` 触发合成整列表音频。
6. **缓存与存储**：音频文件可存储在磁盘或对象存储，表中记录路径；需要定期清理未使用的音频（如长时间未播放的翻译音频）。
7. **TDD 要求**：对播放列表操作、设置继承、音频生成 API 需提供单测/集成测试；前端需有播放控制组件的单元测试和播放流程的 E2E 测试。

### 5.11 自定义学习路径（Spaced Repetition & 专项训练）
1. **Spaced Repetition（SRS）框架**  
   - 当前 Guided 模式使用简化的间隔算法（due_at/streak）作为占位实现。后续需替换为完整 SRS（如 SM-2 或 FSRS），并记录每次复习结果（score/时间）以便跨 Session 追踪。  
   - Guided 模式默认按句子推进：先复习同一句的 chunk 卡片，再出现整句卡片，完成后切换到下一句。Manual 模式允许按实体类型（chunk/sentence/lexeme）过滤。  
   - SRS 数据需复用同一套 `FlashcardProgress`，无论来自默认 Session、收藏专练、答案专练，统一更新 due_at/streak。

2. **答案版专练**  
   - 在 Answer 详情页提供“仅复习该答案”入口，跳转至 FlashcardsView 并携带 `answer_id`。Guided 模式仅遍历该答案关联的句子顺序，Manual 模式则允许在 chunk/句子/lexeme 间切换，但都限定在该版本范围内。  
   - 该专练直接消耗/更新该答案对应的 flashcard 进度，不会创建新的 Answer/AnswerGroup。

3. **收藏/列表训练**  
   - 收藏夹（以及未来的 Collection/播放列表）可直接发起 chunk/句子/lexeme 专项训练，不依赖当前 Session。  
   - 训练过程仍复用 `FlashcardProgress` 与 Guided/Manual 模式，需记录复习结果并更新 due_at/streak。  
   - 当某句尚未完成翻译/拆分时，自定义训练界面需提示并允许即时触发相应任务，确保 chunk→句子学习材料充足。

4. **答案复写自测（Custom Session）**
   - 提供“针对单个答案版本重新写一遍”的入口。流程：用户输入草稿 → LLM 将草稿与指定版本的 Answer 比较，给出差异反馈与改进建议，但不生成新 Answer/AnswerGroup，也不触发结构拆分或抽认卡。  
   - 将此类自测记入类型为 `custom` 的 Session，用于统计练习次数/历史记录，但不参与默认学习阶段。

## 6. API 初稿

- `GET /questions`、`POST /questions`、`PUT /questions/{id}`、`DELETE /questions/{id}`
- `POST /questions/import` 上传 CSV
- `POST /questions/fetch`：接受 URL 列表，异步抓取题目，返回任务 ID
- `GET /questions/fetch-results?task_id=`：查看抓取结果预览，可过滤状态/确认情况
- `GET /questions/{id}/answers` 列出答案组与版本
- `POST /sessions` 创建学习会话（参数：question_id, answer_group_id?, session_type）
- `POST /sessions/{id}/draft` 更新用户草稿答案
- `POST /sessions/{id}/llm/eval` 触发评估轮次（可使用 WebSocket 推送）
- `POST /answers/{id}/finalize` 将 session 最终结果固化为 Answer
- `DELETE /answers/{id}` 删除指定答案版本（会清理段落/句子/Chunk 及相关 flashcard）
- `GET /answers/{id}` 查看答案结构、句子、图数据
   - `POST /sentences/{id}/tasks/chunks`：触发句子拆分为记忆块（可选参数：是否强制、指定范围）；成功后写入 `SentenceChunk`
   - `POST /sentences/{id}/tasks/chunk-lexemes`：基于已存在的 chunk 生成关键词 `Lexeme`，建立 `ChunkLexeme` 关联
   - `GET /sentences/{id}/chunks`：读取句子对应的 chunk+lexeme 结构，供前端展示/复习
- `POST /answers/{id}/structure-graph` 触发可选的篇章图分析任务
- `GET /flashcards/due`、`POST /flashcards/{id}/result`
- `GET /settings/user-profile`、`PUT /settings/user-profile`（全局考生人设配置，供 T2 生成使用）
- `POST /questions/fetch`：根据 URL 列表触发抓取任务，返回任务信息+结果预览
- `GET /questions/fetch/results`：根据 task_id 获取抓取结果列表
- `GET /tasks`、`GET /tasks/{id}`：查询后台任务状态；`POST /tasks/{id}/retry` 重试单个任务；`DELETE /tasks/{id}` 取消任务；`POST /answers/{id}/tasks` 以任务类型为参数补充未执行步骤
- `GET /llm-conversations`：列出最近的 LLM 调用记录（可按 session_id、task_id 过滤），便于排查 prompt 与输出
- `GET /favorites`、`POST /favorites`、`DELETE /favorites/{id}`：收藏列表及操作
- `GET /tags`（可选预设标签）、`GET /questions?tag=xxx`：基于 `QuestionTag` 表过滤；题目 CRUD 中需支持标签编辑
- `GET /lexemes`、`PUT /lexemes/{id}`、`POST /lexemes/{id}/merge`：Lexeme 管理；Chunk 绑定/解绑通过 `ChunkLexeme` API 完成
- `GET /collections`、`POST /collections`、`PUT /collections/{id}`、`DELETE /collections/{id}`
- `POST /collections/{id}/items`、`PUT /collection-items/{id}`、`DELETE /collection-items/{id}`
- `POST /audio/generate`、`GET /audio/{id}`、`POST /playlists/{id}/export`

（真实接口可根据实现细节调整）

## 7. LLM 流程分类

1. **Answer Evaluation Loop**：prompt 用户改进答案；维护上下文，直到用户确认。以后台任务运行，支持断点续作与手动重试。
2. **Title & Descriptor Generation**：生成答案标题、主旨描述（可作为 `stance/descriptor`）。
3. **Structure Extraction**：输出段落/语块/句子 JSON，并包含角色标签、关系描述。
4. **Graph Relation Builder**：基于结构描述构造图形节点/边。
5. **Sentence Translation**：生成句子中英翻译。
6. **Chunk Splitter & Lexeme Builder**：
   - Prompt A（`chunk_sentence`）：输入题目信息+原句+上次失败原因，输出 3-6 个 chunk，字段包含 text/translation_en/translation_zh/order；附带 chunk 质检（覆盖度、语法完整性、翻译对应），失败信息写回 `sentence.extra.split_issues` 以便下次 prompt。
   - Prompt B（`lexeme_from_chunks`）：输入句子与 chunk 列表，由 LLM 针对每个 chunk 生成 1-N 个 lexeme（headword/sense/gloss/translation/pos/difficulty）。输出中需指明所属 `chunk_order`，服务层据此写入 `Lexeme` 并创建 `ChunkLexeme`。此阶段也有质检（确保每个 chunk 至少有关键词、字段合法），失败信息写入 `chunk.extra`.
7. **Answer Comparator**：比较现有答案与新草稿主旨/结构差异。
8. **Gap Highlight & Feedback**：指出缺失内容、语法词汇问题。
9. **AnswerComposer / Refined Answer Generator**：调用链需先生成满足风格/难度/篇章要求的法语文本（T2 需输出自然的双人对话，结合全局 `user_profile` 与 `dialogue_profile` 生成合理人设、提问/追问/评论链路），再单独触发结构化流程；每个阶段由独立任务承载，便于并行与重试；对于 i+1 版本，同样遵循“先作文，后拆解”的顺序。

## 8. 前端页面草图

> 详见 `frontend_spec.md` 获取更细的组件与交互定义（包含 TypeScript 与 TDD 约束）。

1. **题目管理**
   - 列表、过滤（来源/年份/标签/T2T3）、增改表单。
   - 列表需显示 slug（只读）并提供“LLM 生成标题/标签”按钮：调用 `POST /questions/{id}/generate-metadata`，在后端写入新的中文标题与最多 5 个标签。
   - CSV 导入面板。
   - “抓取题目”对话框：填写 URL 列表，发起抓取任务，查看进度与预览，逐条确认后导入。
2. **题目详情 / 答案管理**
   - 显示现有答案组及最新版本，提供“开始学习/复习”按钮。
3. **学习工作台**
   - 左侧展示题目和 LLM 反馈日志，右侧编辑器（用户答案）。
   - 多轮反馈的提示流。
4. **篇章浏览**
   - 段落/句子树状结构展示，显示翻译、关系图（图结构为可选功能；若尚未生成，提供“生成篇章图”按钮）。
   - 展示句子拆分状态，允许逐句触发/重试 `split_phrase`，并查看/管理 `Lexeme`。
5. **抽认卡**
   - 句子/词块练习模式切换，记录结果并显示下次复习时间。
6. **任务中心**
   - 全局或页面级展示后台任务列表/进度条，提供重试、取消、跳转到对应 Answer/Session 的入口。
7. **收藏面板**
   - 展示已收藏的答案/段落/句子/词块，支持筛选、跳转到来源。
8. **Lexeme 管理**
   - 列表展示所有 lexeme（带 sense/gloss/引用次数），提供编辑、合并、拆分、重新绑定句子的界面。

## 9. 可扩展性与后续工作

- 引入用户/权限、团队协作。
- 实现真正的 SRS（SM-2、FSRS）算法。
- 支持多 LLM 提供商、离线模型。
- 加入音频录入、语音识别。
- 导出功能、数据备份。
- 多收藏/播放列表与 TTS 播放系统。

## 10. 近期实现计划

以下能力仍在规划阶段，当前代码尚未覆盖：

1. **CSV 导入**：补齐 `/questions/import` API 及前端上传界面，支持基于 `(source, year, month, suite, number)` 的批量导入/更新。
2. **篇章语义图**：在结构拆解时生成 `semantic_label`/角色信息，并按 spec 要求构造句子关系图。
3. **T2 对话模式**：落实问答对结构、考官/考生人设，以及“按问答对”的抽认卡练习方式。
4. **收藏/播放列表**：实现 Favorite/Collection 模型，允许针对自定义列表启动 guided/manual 训练。
5. **实时任务推送**：引入 WebSocket 或 Server-Sent Events，让 Session/Task 进度实时更新，减少前端轮询。
6. **定制化学习模式**  
   - 强化 Spaced Repetition：在现有简化算法基础上接入真正的 SRS（SM-2/FSRS），跨 Session 追踪每张卡的 due_at/streak。  
   - 收藏专练：允许用户基于收藏的句子/Chunk/Lexeme 启动一次专练，与默认 Session 流程解耦。  
   - 答案单独专练：提供“仅复习某个答案版本”入口，仅在该答案范围内执行 Guided/Manual 练习。  
   - Answer 复写自测：针对某个答案版本发起 mini-session（类型记为 `custom`），用户输入草稿，LLM 与该版本对比并反馈差异，但不生成新 Answer/AnswerGroup，也不触发抽认卡。

---

本文档用于指导后续需求细化与自动化代码生成。可在实现过程中更新。***
### 5.12 题意分析与答案方向

1. **题目级题意解析**  
   - `Question.generate_metadata` 除生成标题/标签外，还要调用 Outline Planner，输出 2~3 个固定的方向候选（`direction_plan`）。  
   - 每个方向包含 `title`（方向名）、`summary`、`stance`、`structure` 数组；结果写入 `questions.direction_plan`，作为题目的长期元信息。  
   - Question API 返回 `direction_plan`，前端可展示推荐结构；同时 Question 记录哪些方向已经挂接了 AnswerGroup（由 `AnswerGroup.direction_descriptor` 反查）。

2. **答案组按方向划分**  
   - 创建 AnswerGroup 时必须指定 `direction_descriptor`，值应来自 Question 的 direction_plan，除非显式新增自定义方向。  
   - 同一方向只需一个 AnswerGroup；`Session` 若选择“新方向”但数据库没有对应 group，则自动创建新 group 并写入 descriptor。

3. **生成答案（AnswerComposer）**  
   - Compose Prompt 不再重新做题意分析，而是根据 Question.direction_plan + Session 中 `selected_direction_descriptor` 组装 `direction_hint`。  
   - 若 Session 尚未选择方向，默认使用 question plan 的推荐方向，并在 `_build_direction_hint` 中给出结构提示。

4. **方向匹配 / 决策**  
   - Compare 阶段向 LLM 提供：题目、草稿、`direction_plan` 文本、已有 AnswerGroup 的方向列表。  
   - LLM 判断草稿最贴近的方向并落在 `direction_descriptor` 中；若该方向已有 AnswerGroup → `decision=reuse` 且返回 `matched_answer_group_id`；否则 `decision=new_group` 并建议 descriptor。  
   - Session `progress_state` 存储 `selected_direction_descriptor`/`direction_match`，Finalize 时写入新 AnswerGroup；前端据此展示“沿用哪个方向”或“需新增方向”提示。
