from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class LLMError(Exception):
    """Raised when the LLM client fails to return usable data."""


@dataclass
class GeneratedQuestionMetadata:
    title: str
    tags: List[str]


class QuestionMetadataSchema(BaseModel):
    title: str = Field(..., description="不超过20个汉字的简洁标题")
    tags: List[str] = Field(default_factory=list, description="最多5个主题标签，每个不超过5个字")


class QuestionLLMClient:
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self._parser = JsonOutputParser(pydantic_object=QuestionMetadataSchema)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "你是TCF Canada口语题目的小助手，请根据题干内容生成一个简洁的中文标题（不超过20个汉字），"
                        "并给出最多5个主题标签（每个标签不超过5个字）。{format_instructions}"
                    ),
                ),
                (
                    "human",
                    "题目类型: {question_type}\nSlug: {slug}\n现有标签: {existing_tags}\n题目正文如下:\n{body}",
                ),
            ]
        )
        self._llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        self._chain = self._prompt | self._llm | self._parser

    def generate_metadata(
        self,
        *,
        slug: Optional[str],
        body: str,
        question_type: str,
        tags: List[str],
    ) -> GeneratedQuestionMetadata:
        existing_tags = ", ".join(tags) if tags else "无"
        try:
            result = self._chain.invoke(
                {
                    "slug": slug or "未知",
                    "body": body,
                    "question_type": question_type,
                    "existing_tags": existing_tags,
                    "format_instructions": self._parser.get_format_instructions(),
                }
            )
        except Exception as exc:  # pragma: no cover - LangChain errors depend on runtime env
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc

        title = (result.get("title") or "").strip()
        new_tags = result.get("tags") or []
        if not title:
            raise LLMError("LLM 没有生成标题")
        if not isinstance(new_tags, list):
            raise LLMError("LLM 返回的标签格式不正确")

        normalized_tags: List[str] = []
        for tag in new_tags:
            if isinstance(tag, str):
                cleaned = tag.strip()
                if cleaned and cleaned not in normalized_tags:
                    normalized_tags.append(cleaned)
        return GeneratedQuestionMetadata(title=title, tags=normalized_tags[:5])
