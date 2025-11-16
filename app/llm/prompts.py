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
