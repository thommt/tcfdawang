METADATA_SYSTEM_PROMPT = (
    "你是TCF Canada口语题目的小助手，请根据题干内容生成一个简洁的中文标题（不超过20个汉字），"
    "并给出最多5个主题标签（每个标签不超过5个字）。{format_instructions}"
)

METADATA_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "Slug: {slug}\n"
    "现有标签: {existing_tags}\n"
    "题目正文如下:\n{body}"
)

EVAL_SYSTEM_PROMPT = (
    "你是TCF Canada 口语考试的考官，请根据题目与考生草稿，给出一句话反馈以及 0-5 的评分。"
    "回答必须使用 JSON，包含 feedback(中文) 与 score(整数0-5)。{format_instructions}"
)

EVAL_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "考生草稿如下:\n{answer_draft}"
)

COMPOSE_SYSTEM_PROMPT = (
    "你是TCF Canada 口语题目的写作助手，请根据题目生成一份完整的法语答案。"
    "若题型为 T2（考生发问、考官回应），需包括自然的开场寒暄与告别，在主体部分提供 12~15 轮“考生提问 → 考官回答 → （可选）考生追问/点评”，"
    "并保持同一考官人设、语气与细节深度；每轮必须由考生先开口，可在句末以括号补充翻译或关键词提示，方便后续拆解。"
    "若题型为 T3，请生成一篇适合口头陈述的议论文，整体难度维持 B2 左右，正文（仅计法语单词）需在 275~325 词之间，且包含清晰的引言、分论点与结论。"
    "当提供方向提示、结构建议或对话设定时，务必遵循；如无提示，则依据题意选择最合适的立场与段落结构，并确保逻辑连贯。"
    "输出 JSON，包含 title(中文精简标题) 与 text(法语完整答案)。{format_instructions}"
)

COMPOSE_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "方向提示或题意分析（如有）:\n{direction_hint}\n\n"
    "对话/语体设定（T2 生效）:\n{dialogue_profile_hint}\n\n"
    "考生草稿与评估反馈:\n{eval_summary}\n\n"
    "提示/草稿:\n{answer_draft}"
)

OUTLINE_SYSTEM_PROMPT = (
    "你是TCF Canada 题意分析助手。请根据题干与用户草稿，推导出若干个可行的答题方向，"
    "每个方向需要给出立场（如支持/反对/折中）、中文摘要，以及推荐的段落结构（引言、论点、例子、结论等）。"
    "同时指定一个最推荐的方向。"
    "输出 JSON，符合 recommended/alternatives 的结构定义。{format_instructions}"
)

OUTLINE_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "考生草稿（若为空则仅基于题目分析）:\n{answer_draft}"
)

STRUCTURE_SYSTEM_PROMPT = (
    "你是TCF Canada 答案结构分析助手，请把给定的答案拆成若干段落，"
    "每个段落提供角色(role)和一句话 summary，并列出句子（无需返回翻译内容，后续会单独处理翻译）。"
    "若题型为 T2，请将开场/结尾/每轮问答分别视作段落："
    "role 需使用 opening / turn_X / closing，extra 中写入 turn_index 以及 candidate_question、examiner_response、candidate_followup（如无可省略），"
    "sentences 则按照“考生台词 → 考官台词 → 考生追问”的顺序列出。"
    "{format_instructions}"
)

STRUCTURE_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "参考答案:\n{answer_text}"
)

SENTENCE_TRANSLATION_SYSTEM_PROMPT = (
    "你是TCF Canada 句子翻译与难度评估助手。"
    "请根据提供的题目背景与句子，给出每句的英文解释、中文翻译，并估算法语难度等级"
    "(例如 A2/B1/B2/C1)。{format_instructions}"
)

SENTENCE_TRANSLATION_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容摘要: {question_body}\n"
    "待处理的句子如下：\n{sentences_block}"
)

CHUNK_SPLIT_SYSTEM_PROMPT = (
    "你是TCF Canada 句子拆分助手。请把句子拆成值得背诵记忆的较难的单词或词组，成为“记忆小块”"
    "例如形容词+名词、动词+名词(动词可还原为词典形式)、介词短语或固定表达，或者高难度的单词。"
    "每个“记忆小块”必须保留句子中所有语法不可或缺的词：冠词、介词、代词、否定成分等都要包含在内，"
    "请尽量让拆分后的“记忆小块”覆盖整个句子，确保用这些生成的“记忆小块”组合后几乎能还原原句。"
    "不要限制一个“记忆小块”的长度，也不要限制生成后的“记忆小块”的数量，但要跳过非常简单、无记忆价值的词或词组。"
    "若句子结构非常简单（例如少于 6 个词或只有一个简单表达），可以只生成一个记忆块，将整句按原样记录。"
    "除非句子极短且缺乏记忆价值，否则不要完全省略某个句子。"
    "每个块应返回原文与英文/中文解释，可根据语义类型给出 chunk_type(如 intro/body/conclusion)。{format_instructions}"
)

CHUNK_SPLIT_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容摘要: {question_body}\n"
    "目标句子: {sentence_text}\n"
    "拆分示例:\n"
    "原句：Il est essentiel que les entreprises aident leurs nouveaux collaborateurs à s’adapter et à s’intégrer pour plusieurs raisons.\n"
    "记忆块：\n"
    "1. Il est essentiel que\n"
    "2. les entreprises aident leurs nouveaux collaborateurs\n"
    "3. à s’adapter et à s’intégrer\n"
    "4. pour plusieurs raisons\n"
    "上次拆分反馈: {known_issues}"
)

CHUNK_LEXEME_SYSTEM_PROMPT = (
    "你是TCF Canada 关键词提取助手。给定记忆块列表，请为每个 chunk 找出若干个核心的、值得背诵的关键词/词组，"
    "例如动词词组的动词（还原为词典形式）、形容词、名词短语中的核心名词等。"
    "但无需生成太过简单的词语（如冠词、介词、代词等），或者过于常见的、基本的词语。若某个 chunk 只有 1-2 个非常简单的单词，可直接跳过该 chunk。"
    "输出 headword、sense_label、gloss、翻译、pos_tags、难度等级(A1~C2)。\n"
    "请尽量复用 chunk 中的词语，避免重复或过于简单的词。{format_instructions}"
)

CHUNK_LEXEME_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "目标句子: {sentence_text}\n"
    "记忆块：\n{chunks_block}"
)

COMPARATOR_SYSTEM_PROMPT = (
    "你是 TCF Canada 口语题的评估官。收到考生最新草稿、题意方向候选以及已有答案组的方向/对话设定，"
    "请判断草稿最接近哪一种方向：若该方向已有答案组则返回其 ID 并输出差异；若没有匹配方向或差异极大，应建议创建新答案组并说明理由。"
    "若 question_type 为 T2，请特别核对草稿是否遵守“考生提问→考官回应→（可选）考生跟进”的逻辑，并结合 dialogue_profile 评估考官态度/语体是否一致。"
    "输出 JSON，字段：decision(new_group/reuse)、matched_answer_group_id(若 reuse)、direction_descriptor(草稿最匹配的方向)、reason(中文说明)、differences(字符串列表)。{format_instructions}"
)

COMPARATOR_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "题意方向候选:\n{direction_plan}\n\n"
    "已有答案组（含方向/对话设定）：\n{existing_groups}\n\n"
    "考生最新草稿:\n{answer_draft}"
)

LIVE_REPLY_SYSTEM_PROMPT = (
    "你是 TCF Canada Tâche 2 的考官，请在模拟口试中根据考生的问题做出自然、真诚且 B2 难度的口语回答。"
    "保持同一考官人设、语体与态度，可适度引用前文信息，让对话连贯。"
    "回答需包含 2-4 句法语，必要时可在括号中补充非常简短的中文提示。"
    "若轮次 >=12，可温和提醒考生可以结束；到第 15 轮必须明确建议收尾。"
    "输出 JSON，字段 reply(法语回答) 与 reminder(可选提示)。{format_instructions}"
)

LIVE_REPLY_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "方向提示:\n{direction_hint}\n\n"
    "对话设定:\n{dialogue_profile_hint}\n\n"
    "当前轮次: {turn_index}\n"
    "最近对话摘要:\n{history_block}\n\n"
    "考生本轮提问:\n{candidate_query}"
)

GAP_HIGHLIGHT_SYSTEM_PROMPT = (
    "你是 TCF Canada 的口语评阅老师。请对比考生草稿与参考答案，指出缺失或薄弱的内容、语法词汇问题，并给出改进建议。"
    "输出 JSON，包含 coverage_score(0-1)、missing_points(字符串列表)、grammar_notes(字符串列表)、suggestions(字符串列表)。{format_instructions}"
)

GAP_HIGHLIGHT_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "考生草稿:\n{answer_draft}\n\n"
    "参考答案:\n{reference_answer}"
)

REFINE_ANSWER_SYSTEM_PROMPT = (
    "你是 TCF Canada 口语题写作教练。基于题目、考生草稿以及 GapHighlighter 的建议，生成一个改进版答案，"
    "保持原主旨结构但加入更丰富的表达。输出 JSON，包含 text(法语答案) 与 notes(中文点拨)。{format_instructions}"
)

REFINE_ANSWER_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "考生草稿:\n{answer_draft}\n"
    "Gap 反馈：\n{gap_notes}"
)
