from __future__ import annotations

from typing import List, Optional

from langchain_openai import ChatOpenAI

from app.llm import (
    GeneratedQuestionMetadata,
    build_metadata_chain,
    build_evaluation_chain,
    build_compose_chain,
    build_structure_chain,
    build_sentence_translation_chain,
    build_phrase_split_chain,
)


class LLMError(Exception):
    """Raised when the LLM client fails to return usable data."""


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
        self._llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        self._metadata_chain, self._metadata_parser = build_metadata_chain(self._llm)
        self._eval_chain, self._eval_parser = build_evaluation_chain(self._llm)
        self._compose_chain, self._compose_parser = build_compose_chain(self._llm)
        self._structure_chain, self._structure_parser = build_structure_chain(self._llm)
        self._sentence_translation_chain, self._sentence_translation_parser = build_sentence_translation_chain(
            self._llm
        )
        self._phrase_split_chain, self._phrase_split_parser = build_phrase_split_chain(self._llm)

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
            result = self._metadata_chain.invoke(
                {
                    "slug": slug or "未知",
                    "body": body,
                    "question_type": question_type,
                    "existing_tags": existing_tags,
                    "format_instructions": self._metadata_parser.get_format_instructions(),
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

    def evaluate_answer(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        answer_draft: str,
    ) -> dict:
        if not answer_draft:
            raise LLMError("暂无可评估的草稿")
        try:
            result = self._eval_chain.invoke(
                {
                    "question_type": question_type,
                    "question_title": question_title,
                    "question_body": question_body,
                    "answer_draft": answer_draft,
                    "format_instructions": self._eval_parser.get_format_instructions(),
                }
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def compose_answer(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        answer_draft: str,
    ) -> dict:
        try:
            result = self._compose_chain.invoke(
                {
                    "question_type": question_type,
                    "question_title": question_title,
                    "question_body": question_body,
                    "answer_draft": answer_draft,
                    "format_instructions": self._compose_parser.get_format_instructions(),
                }
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def structure_answer(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        answer_text: str,
    ) -> dict:
        if not answer_text:
            raise LLMError("暂无可拆解的答案")
        try:
            result = self._structure_chain.invoke(
                {
                    "question_type": question_type,
                    "question_title": question_title,
                    "question_body": question_body,
                    "answer_text": answer_text,
                    "format_instructions": self._structure_parser.get_format_instructions(),
                }
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def translate_sentences(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        sentences: List[str],
    ) -> dict:
        if not sentences:
            raise LLMError("暂无可翻译的句子")
        sentences_block = "\n".join(f"{idx+1}. {text}" for idx, text in enumerate(sentences))
        try:
            result = self._sentence_translation_chain.invoke(
                {
                    "question_type": question_type,
                    "question_title": question_title,
                    "question_body": question_body,
                    "sentences_block": sentences_block,
                    "format_instructions": self._sentence_translation_parser.get_format_instructions(),
                }
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def split_sentence(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        sentence_text: str,
    ) -> dict:
        if not sentence_text:
            raise LLMError("暂无可拆分的句子")
        try:
            result = self._phrase_split_chain.invoke(
                {
                    "question_type": question_type,
                    "question_title": question_title,
                    "question_body": question_body,
                    "sentence_text": sentence_text,
                    "format_instructions": self._phrase_split_parser.get_format_instructions(),
                }
            )
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result
