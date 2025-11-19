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
    build_chunk_split_chain,
    build_chunk_lexeme_chain,
    build_answer_comparator_chain,
    build_gap_highlight_chain,
    build_refine_answer_chain,
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
        self._eval_chain, self._eval_parser, self._eval_prompt = build_evaluation_chain(self._llm)
        self._compose_chain, self._compose_parser, self._compose_prompt = build_compose_chain(self._llm)
        self._structure_chain, self._structure_parser = build_structure_chain(self._llm)
        self._sentence_translation_chain, self._sentence_translation_parser = build_sentence_translation_chain(
            self._llm
        )
        (
            self._chunk_split_chain,
            self._chunk_split_parser,
            self._chunk_split_prompt,
        ) = build_chunk_split_chain(self._llm)
        (
            self._chunk_lexeme_chain,
            self._chunk_lexeme_parser,
            self._chunk_lexeme_prompt,
        ) = build_chunk_lexeme_chain(self._llm)
        (
            self._answer_comparator_chain,
            self._answer_comparator_parser,
            self._answer_comparator_prompt,
        ) = build_answer_comparator_chain(self._llm)
        (
            self._gap_highlight_chain,
            self._gap_highlight_parser,
            self._gap_highlight_prompt,
        ) = build_gap_highlight_chain(self._llm)
        (
            self._refine_answer_chain,
            self._refine_answer_parser,
            self._refine_answer_prompt,
        ) = build_refine_answer_chain(self._llm)

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
            prompt_messages = self._eval_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                question_body=question_body,
                answer_draft=answer_draft,
                format_instructions=self._eval_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._eval_parser.parse(response_text)
            if hasattr(parsed, "model_dump"):
                result = parsed.model_dump()
            else:
                result = dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def chunk_sentence(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        sentence_text: str,
        known_issues: list[str] | None = None,
    ) -> dict:
        if not sentence_text:
            raise LLMError("暂无可拆分的句子")
        issues_block = (
            "上次拆分存在以下问题：\n" + "\n".join(f"- {issue}" for issue in known_issues)
            if known_issues
            else "无"
        )
        try:
            prompt_messages = self._chunk_split_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                question_body=question_body,
                sentence_text=sentence_text,
                known_issues=issues_block,
                format_instructions=self._chunk_split_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._chunk_split_parser.parse(response_text)
            result = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def build_chunk_lexemes(
        self,
        *,
        question_type: str,
        question_title: str,
        sentence_text: str,
        chunks: list[dict],
    ) -> dict:
        chunks_block = "\n".join(
            f"{item.get('chunk_index', idx+1)}. {item.get('text')} "
            f"(EN: {item.get('translation_en') or '—'} / ZH: {item.get('translation_zh') or '—'})"
            for idx, item in enumerate(chunks)
        )
        try:
            prompt_messages = self._chunk_lexeme_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                sentence_text=sentence_text,
                chunks_block=chunks_block,
                format_instructions=self._chunk_lexeme_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._chunk_lexeme_parser.parse(response_text)
            result = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
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
        eval_summary: str | None = None,
    ) -> dict:
        try:
            prompt_messages = self._compose_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                question_body=question_body,
                eval_summary=eval_summary or "暂无评估反馈",
                answer_draft=answer_draft,
                format_instructions=self._compose_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._compose_parser.parse(response_text)
            if hasattr(parsed, "model_dump"):
                result = parsed.model_dump()
            else:
                result = dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
        except Exception as exc:  # pragma: no cover
            raise LLMError("LLM 请求失败，请检查配置或响应格式") from exc
        return result

    def compare_answer(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        answer_draft: str,
        reference_answers: list[dict],
    ) -> dict:
        references_block = "\n".join(
            f"- group_id={item.get('answer_group_id')} (version {item.get('version_index')}): {item.get('text')}"
            for item in reference_answers
        ) or "（无参考答案）"
        try:
            prompt_messages = self._answer_comparator_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                question_body=question_body,
                answer_draft=answer_draft,
                reference_answers=references_block,
                format_instructions=self._answer_comparator_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._answer_comparator_parser.parse(response_text)
            if hasattr(parsed, "model_dump"):
                result = parsed.model_dump()
            else:
                result = dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
        except Exception as exc:  # pragma: no cover
            raise LLMError("对比现有答案组失败") from exc
        return result

    def highlight_gaps(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        answer_draft: str,
        reference_answer: str,
    ) -> dict:
        try:
            prompt_messages = self._gap_highlight_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                question_body=question_body,
                answer_draft=answer_draft,
                reference_answer=reference_answer or "（暂无参考答案）",
                format_instructions=self._gap_highlight_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._gap_highlight_parser.parse(response_text)
            result = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
        except Exception as exc:  # pragma: no cover
            raise LLMError("GapHighlighter 请求失败") from exc
        return result

    def refine_answer(
        self,
        *,
        question_type: str,
        question_title: str,
        question_body: str,
        answer_draft: str,
        gap_notes: dict | None = None,
    ) -> dict:
        notes_block = ""
        if gap_notes:
            missing = "\n".join(f"- {item}" for item in gap_notes.get("missing_points", []))
            grammar = "\n".join(f"- {item}" for item in gap_notes.get("grammar_notes", []))
            suggestions = "\n".join(f"- {item}" for item in gap_notes.get("suggestions", []))
            notes_block = f"缺失要点:\n{missing}\n语法词汇:\n{grammar}\n建议:\n{suggestions}"
        try:
            prompt_messages = self._refine_answer_prompt.format_messages(
                question_type=question_type,
                question_title=question_title,
                question_body=question_body,
                answer_draft=answer_draft,
                gap_notes=notes_block or "（暂无提示）",
                format_instructions=self._refine_answer_parser.get_format_instructions(),
            )
            raw = self._llm.invoke(prompt_messages)
            response_text = getattr(raw, "content", raw)
            if isinstance(response_text, list):
                response_text = "\n".join(
                    item["text"] if isinstance(item, dict) and item.get("type") == "text" else str(item)
                    for item in response_text
                )
            parsed = self._refine_answer_parser.parse(response_text)
            result = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
            result["_prompt_messages"] = self._serialize_messages(prompt_messages)
        except Exception as exc:  # pragma: no cover
            raise LLMError("RefinedAnswer 请求失败") from exc
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

    def _serialize_messages(self, messages):
        serialized = []
        for msg in messages:
            role = getattr(msg, "type", None) or msg.__class__.__name__.lower()
            serialized.append({"role": role, "content": msg.content})
        return serialized
