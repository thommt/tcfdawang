from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Set

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import (
    Task,
    Session as SessionSchema,
    Question,
    LLMConversation,
    Answer as AnswerSchema,
    AnswerGroup as AnswerGroupSchema,
    Paragraph,
    Sentence,
    Lexeme,
    SentenceLexeme,
)
from app.models.fetch_task import TaskRead
from app.models.flashcard import FlashcardProgressCreate
from app.services.llm_service import QuestionLLMClient, LLMError
from app.services.flashcard_service import FlashcardService


class TaskService:
    def __init__(self, session: DBSession, llm_client: QuestionLLMClient) -> None:
        self.session = session
        self.llm_client = llm_client
        self.flashcard_service = FlashcardService(session)

    def run_eval_task(self, session_id: int) -> TaskRead:
        session_entity = self.session.get(SessionSchema, session_id)
        if not session_entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        task = Task(type="eval", status="pending", payload={"session_id": session_id}, session_id=session_id)
        self.session.add(task)
        self.session.commit()
        try:
            start = datetime.now(timezone.utc)
            eval_result = self.llm_client.evaluate_answer(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_draft=session_entity.user_answer_draft or "",
            )
            latency = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="eval",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                },
                result=eval_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            session_entity.progress_state = session_entity.progress_state or {}
            session_entity.progress_state["last_eval"] = eval_result
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = eval_result
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return TaskRead.model_validate(task)

    def run_compose_task(self, session_id: int) -> TaskRead:
        session_entity = self.session.get(SessionSchema, session_id)
        if not session_entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        task = Task(type="compose", status="pending", payload={"session_id": session_id}, session_id=session_id)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        try:
            start = datetime.now(timezone.utc)
            compose_result = self.llm_client.compose_answer(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_draft=session_entity.user_answer_draft or "",
            )
            latency = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="compose",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                },
                result=compose_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            session_entity.progress_state = session_entity.progress_state or {}
            session_entity.progress_state["last_compose"] = compose_result
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = compose_result
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return TaskRead.model_validate(task)

    def retry_task(self, task_id: int) -> TaskRead:
        task = self._get_task(task_id)
        if not task.session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task not linked to session")
        if task.type == "eval":
            return self.run_eval_task(task.session_id)
        if task.type == "compose":
            return self.run_compose_task(task.session_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported task type for retry")

    def cancel_task(self, task_id: int) -> TaskRead:
        task = self._get_task(task_id)
        if task.status not in {"pending", "failed"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task cannot be canceled")
        task.status = "canceled"
        task.updated_at = datetime.now(timezone.utc)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return TaskRead.model_validate(task)

    def _ensure_sentence_flashcard(self, sentence_id: int) -> None:
        self.flashcard_service.get_or_create(
            FlashcardProgressCreate(entity_type="sentence", entity_id=sentence_id)
        )

    def _ensure_lexeme_flashcard(self, lexeme_id: int) -> None:
        self.flashcard_service.get_or_create(
            FlashcardProgressCreate(entity_type="lexeme", entity_id=lexeme_id)
        )

    def _cleanup_orphan_lexemes(self, candidate_ids: Set[int]) -> None:
        if not candidate_ids:
            return
        for lexeme_id in candidate_ids:
            lexeme = self.session.get(Lexeme, lexeme_id)
            if not lexeme:
                continue
            linked = self.session.exec(
                select(SentenceLexeme.id).where(SentenceLexeme.lexeme_id == lexeme_id)
            ).first()
            if linked:
                continue
            self.session.delete(lexeme)

    def _get_task(self, task_id: int) -> Task:
        task = self.session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def run_structure_task_for_answer(self, answer_id: int) -> TaskRead:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        group = self.session.get(AnswerGroupSchema, answer.answer_group_id)
        question = self.session.get(Question, group.question_id) if group else None
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        task = Task(
            type="structure",
            status="pending",
            payload={"answer_id": answer_id},
            session_id=None,
            answer_id=answer_id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        try:
            structure = self.llm_client.structure_answer(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_text=answer.text,
            )
            if not isinstance(structure, dict):
                raise LLMError("LLM 没有返回结构化结果")
            paragraphs_payload = structure.get("paragraphs") or []
            with self.session.begin_nested():
                existing_paragraphs = self.session.exec(
                    select(Paragraph).where(Paragraph.answer_id == answer_id)
                ).all()
                for paragraph in existing_paragraphs:
                    sentences = self.session.exec(
                        select(Sentence).where(Sentence.paragraph_id == paragraph.id)
                    ).all()
                    for sentence in sentences:
                        self.session.delete(sentence)
                    self.session.delete(paragraph)

                for idx, para in enumerate(paragraphs_payload, start=1):
                    paragraph = Paragraph(
                        answer_id=answer_id,
                        order_index=idx,
                        role_label=para.get("role"),
                        summary=para.get("summary"),
                        extra={},
                    )
                    self.session.add(paragraph)
                    self.session.flush()
                    for s_idx, sentence_data in enumerate(para.get("sentences", []), start=1):
                        sentence = Sentence(
                            paragraph_id=paragraph.id,
                            order_index=s_idx,
                            text=sentence_data.get("text", ""),
                            translation_en=sentence_data.get("translation"),
                            translation_zh=sentence_data.get("translation_zh"),
                            difficulty=sentence_data.get("difficulty"),
                            extra={},
                        )
                        self.session.add(sentence)

                conversation = LLMConversation(
                    session_id=None,
                    task_id=task.id,
                    purpose="structure",
                    messages={"answer": answer.text},
                    result=structure,
                    model_name=getattr(self.llm_client, "model", None),
                    latency_ms=None,
                )
                self.session.add(conversation)
                task.status = "succeeded"
                task.result_summary = structure
                task.updated_at = datetime.now(timezone.utc)
                task.error_message = None
                self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            self.session.rollback()
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="结构化任务处理失败") from exc
        return TaskRead.model_validate(task)

    def run_sentence_translation_for_answer(self, answer_id: int) -> TaskRead:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        group = self.session.get(AnswerGroupSchema, answer.answer_group_id)
        question = self.session.get(Question, group.question_id) if group else None
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        task = Task(
            type="sentence_translate",
            status="pending",
            payload={"answer_id": answer_id},
            session_id=None,
            answer_id=answer_id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        try:
            sentence_statement = (
                select(Sentence, Paragraph.order_index)
                .join(Paragraph, Paragraph.id == Sentence.paragraph_id)
                .where(Paragraph.answer_id == answer_id)
                .order_by(Paragraph.order_index, Sentence.order_index)
            )
            rows = self.session.exec(sentence_statement).all()
            if not rows:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No sentences to translate")
            sentences = [row[0] for row in rows]
            texts = [sentence.text for sentence in sentences]
            translation_result = self.llm_client.translate_sentences(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                sentences=texts,
            )
            translations = translation_result.get("translations") or []
            updated = 0
            sentence_ids_for_cards: Set[int] = set()
            for item in translations:
                idx = item.get("sentence_index")
                if not isinstance(idx, int) or idx < 1 or idx > len(sentences):
                    continue
                sentence = sentences[idx - 1]
                sentence.translation_en = item.get("translation_en") or sentence.translation_en
                sentence.translation_zh = item.get("translation_zh") or sentence.translation_zh
                sentence.difficulty = item.get("difficulty") or sentence.difficulty
                self.session.add(sentence)
                updated += 1
                sentence_ids_for_cards.add(sentence.id)
            self.session.commit()
            for sentence_id in sentence_ids_for_cards:
                self._ensure_sentence_flashcard(sentence_id)
            conversation = LLMConversation(
                session_id=None,
                task_id=task.id,
                purpose="sentence_translation",
                messages={"sentences": texts},
                result=translation_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=None,
            )
            self.session.add(conversation)
            task.status = "succeeded"
            task.result_summary = {"updated_count": updated}
            task.updated_at = datetime.now(timezone.utc)
            task.error_message = None
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return TaskRead.model_validate(task)

    def run_sentence_split_task(self, sentence_id: int) -> TaskRead:
        sentence = self.session.get(Sentence, sentence_id)
        if not sentence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentence not found")
        paragraph = self.session.get(Paragraph, sentence.paragraph_id)
        if not paragraph:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paragraph not found")
        answer = self.session.get(AnswerSchema, paragraph.answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        group = self.session.get(AnswerGroupSchema, answer.answer_group_id)
        question = self.session.get(Question, group.question_id) if group else None
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        task = Task(
            type="split_phrase",
            status="pending",
            payload={"sentence_id": sentence_id},
            session_id=None,
            answer_id=answer.id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        try:
            split_result = self.llm_client.split_sentence(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                sentence_text=sentence.text,
            )
            phrases = split_result.get("phrases") or []
            existing_links = self.session.exec(
                select(SentenceLexeme).where(SentenceLexeme.sentence_id == sentence_id)
            ).all()
            orphan_candidates = {link.lexeme_id for link in existing_links if link.lexeme_id}
            for link in existing_links:
                self.session.delete(link)
            self.session.commit()
            created = 0
            lexeme_ids_for_cards: Set[int] = set()
            for idx, phrase in enumerate(phrases, start=1):
                lemma = (phrase.get("lemma") or phrase.get("phrase") or "").strip()
                if not lemma:
                    continue
                sense_label = (phrase.get("sense_label") or "").strip()
                phrase_text = (phrase.get("phrase") or "").strip()
                hash_value = self._build_lexeme_hash(lemma, sense_label, phrase_text)
                lexeme = self.session.exec(select(Lexeme).where(Lexeme.hash == hash_value)).first()
                if not lexeme:
                    lexeme = Lexeme(
                        lemma=lemma,
                        sense_label=sense_label or None,
                        gloss=phrase.get("gloss"),
                        translation_en=phrase.get("translation_en"),
                        translation_zh=phrase.get("translation_zh"),
                        pos_tags=phrase.get("pos_tags"),
                        notes=phrase.get("notes"),
                        complexity_level=phrase.get("difficulty"),
                        hash=hash_value,
                        is_manual=False,
                        extra={},
                    )
                    self.session.add(lexeme)
                    self.session.commit()
                    self.session.refresh(lexeme)
                lexeme_ids_for_cards.add(lexeme.id)
                sentence_lexeme = SentenceLexeme(
                    sentence_id=sentence_id,
                    lexeme_id=lexeme.id,
                    order_index=idx,
                    context_note=phrase.get("context_note"),
                    translation_override=phrase.get("translation_override"),
                    extra={},
                )
                self.session.add(sentence_lexeme)
                created += 1
            self.session.commit()
            for lexeme_id in lexeme_ids_for_cards:
                self._ensure_lexeme_flashcard(lexeme_id)
            self._cleanup_orphan_lexemes(orphan_candidates)
            conversation = LLMConversation(
                session_id=None,
                task_id=task.id,
                purpose="split_phrase",
                messages={"sentence": sentence.text},
                result=split_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=None,
            )
            self.session.add(conversation)
            task.status = "succeeded"
            task.result_summary = {"created": created}
            task.updated_at = datetime.now(timezone.utc)
            task.error_message = None
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return TaskRead.model_validate(task)

    def _build_lexeme_hash(self, lemma: str, sense_label: str, phrase_text: str) -> str:
        normalized_lemma = " ".join(lemma.strip().lower().split())
        normalized_sense = " ".join((sense_label or "").strip().lower().split())
        normalized_phrase = " ".join((phrase_text or "").strip().lower().split())
        parts = [normalized_lemma]
        if normalized_sense:
            parts.append(normalized_sense)
        if normalized_phrase:
            parts.append(normalized_phrase)
        return "::".join(parts)
