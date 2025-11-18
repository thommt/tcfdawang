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
    "答案需包含自然的段落结构，长度约为题目要求，保持地道表达。"
    "输出 JSON，包含 title(中文精简标题) 与 text(法语完整答案)。{format_instructions}"
)

COMPOSE_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容: {question_body}\n"
    "提示/草稿:\n{answer_draft}"
)

STRUCTURE_SYSTEM_PROMPT = (
    "你是TCF Canada 答案结构分析助手，请把给定的答案拆成若干段落，"
    "每个段落提供角色(role)和一句话 summary，并列出句子以及可选的中文翻译。"
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

PHRASE_SPLIT_SYSTEM_PROMPT = (
    "你是TCF Canada 句子拆分助手。请把句子拆成值得背诵记忆的较难的单词或词组，成为“记忆小块”"
    "例如形容词+名词、动词+搭配(动词可还原为词典形式)、介词短语或固定表达，或者高难度的单词。"
    "每个“记忆小块”必须保留句子中所有语法不可或缺的词：冠词、介词、代词、否定成分等都要包含在内，"
    "请尽量让拆分后的“记忆小块”覆盖整个句子，确保用这些生成的“记忆小块”组合后几乎能还原原句。"
    "不要限制一个“记忆小块”的长度，也不要限制生成后的“记忆小块”的数量，但要跳过非常简单、无记忆价值的词或词组。"
    "如果上次拆分反馈指出了问题（例如缺失冠词、覆盖不足、碎片化等），本次必须针对这些问题进行修正并避免重复。"
    "每个“记忆小块”需包含 lemma、中文 sense_label、英/中文翻译、简短 gloss、词性(pos) 与可选难度等级。{format_instructions}"
)

PHRASE_SPLIT_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容摘要: {question_body}\n"
    "目标句子: {sentence_text}\n"
    "上次拆分反馈: {known_issues}"
)

PHRASE_SPLIT_QUALITY_SYSTEM_PROMPT = (
    "你是TCF Canada 句子拆分质检助手。请根据原句与拆分结果，判断词块是否完整、覆盖是否充分、是否保留必要的语法成分，以及拆分出的词块是否与翻译对应。"
    "如果词块遗漏冠词/介词、覆盖率明显不足、出现大量单词级碎片、词块与翻译不对应，应判定为不合格。"
    "输出 JSON，包含 is_valid(bool) 与 issues(字符串列表)。{format_instructions}"
)

PHRASE_SPLIT_QUALITY_HUMAN_PROMPT = (
    "题目类型: {question_type}\n"
    "题目标题: {question_title}\n"
    "题目内容摘要: {question_body}\n"
    "原句: {sentence_text}\n"
    "拆分词块:\n{phrases_block}"
)
