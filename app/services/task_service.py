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
    SentenceChunk,
    ChunkLexeme,
    FlashcardProgress,
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

    def _question_has_answers(self, question_id: int) -> bool:
        exists = self.session.exec(
            select(AnswerSchema.id)
            .join(AnswerGroupSchema, AnswerGroupSchema.id == AnswerSchema.answer_group_id)
            .where(AnswerGroupSchema.question_id == question_id)
        ).first()
        return exists is not None

    def _set_session_phase(self, session_entity: SessionSchema, phase: str) -> None:
        progress_state = dict(session_entity.progress_state or {})
        progress_state["phase"] = phase
        session_entity.progress_state = progress_state
        session_entity.updated_at = datetime.now(timezone.utc)
        self.session.add(session_entity)

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
            prompt_messages = eval_result.pop("_prompt_messages", None)
            saved_at = datetime.now(timezone.utc)
            latency = int((saved_at - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="eval",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                    "prompt_messages": prompt_messages,
                },
                result=eval_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            progress_state = dict(session_entity.progress_state or {})
            eval_payload = dict(eval_result)
            eval_payload["saved_at"] = saved_at.isoformat()
            progress_state["last_eval"] = eval_payload
            progress_state["phase"] = "await_eval_confirm"
            session_entity.progress_state = progress_state
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = eval_payload
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
            if self._question_has_answers(question.id):
                try:
                    self.run_answer_compare_task(session_id)
                except HTTPException:
                    pass
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
            prompt_messages = compose_result.pop("_prompt_messages", None)
            saved_at = datetime.now(timezone.utc)
            latency = int((saved_at - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="compose",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                    "prompt_messages": prompt_messages,
                },
                result=compose_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            progress_state = dict(session_entity.progress_state or {})
            compose_payload = dict(compose_result)
            compose_payload["saved_at"] = saved_at.isoformat()
            progress_state["last_compose"] = compose_payload
            progress_state["phase"] = "compose_completed"
            session_entity.progress_state = progress_state
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = compose_payload
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
        if task.type == "compare":
            return self.run_answer_compare_task(task.session_id)
        if task.type == "gap_highlight":
            return self.run_gap_highlight_task(task.session_id)
        if task.type == "refine_answer":
            return self.run_refine_answer_task(task.session_id)
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

    def run_answer_compare_task(self, session_id: int) -> TaskRead:
        session_entity = self.session.get(SessionSchema, session_id)
        if not session_entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        answer_groups = self.session.exec(
            select(AnswerGroupSchema).where(AnswerGroupSchema.question_id == question.id)
        ).all()
        reference_answers: list[dict[str, Any]] = []
        for group in answer_groups:
            latest_answer = self.session.exec(
                select(AnswerSchema)
                .where(AnswerSchema.answer_group_id == group.id)
                .order_by(AnswerSchema.version_index.desc())
            ).first()
            if latest_answer:
                reference_answers.append(
                    {
                        "answer_group_id": group.id,
                        "version_index": latest_answer.version_index,
                        "text": latest_answer.text,
                    }
                )
        task = Task(type="compare", status="pending", payload={"session_id": session_id}, session_id=session_id)
        self.session.add(task)
        self.session.commit()
        try:
            start = datetime.now(timezone.utc)
            compare_result = self.llm_client.compare_answer(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_draft=session_entity.user_answer_draft or "",
                reference_answers=reference_answers,
            )
            prompt_messages = compare_result.pop("_prompt_messages", None)
            saved_at = datetime.now(timezone.utc)
            latency = int((saved_at - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="compare",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                    "reference_answers": reference_answers,
                    "prompt_messages": prompt_messages,
                },
                result=compare_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            progress_state = dict(session_entity.progress_state or {})
            compare_payload = dict(compare_result)
            compare_payload["saved_at"] = saved_at.isoformat()
            progress_state["last_compare"] = compare_payload
            decision = compare_payload.get("decision")
            if decision == "reuse":
                progress_state["phase"] = "gap_highlight"
            elif decision == "new_group":
                progress_state["phase"] = "await_new_group"
            session_entity.progress_state = progress_state
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = compare_payload
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
            if compare_payload.get("decision") == "reuse":
                try:
                    self.run_gap_highlight_task(session_id)
                except HTTPException:
                    pass
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return TaskRead.model_validate(task)

    def _get_reference_answer_text(self, question_id: int, prefer_group_id: int | None) -> str:
        group_ids = []
        if prefer_group_id:
            group_ids.append(prefer_group_id)
        groups = self.session.exec(
            select(AnswerGroupSchema.id).where(AnswerGroupSchema.question_id == question_id)
        ).all()
        for group in groups:
            gid = group if isinstance(group, int) else group[0]
            if gid not in group_ids:
                group_ids.append(gid)
        for gid in group_ids:
            latest = self.session.exec(
                select(AnswerSchema)
                .where(AnswerSchema.answer_group_id == gid)
                .order_by(AnswerSchema.version_index.desc())
            ).first()
            if latest:
                return latest.text
        return ""

    def run_gap_highlight_task(self, session_id: int) -> TaskRead:
        session_entity = self.session.get(SessionSchema, session_id)
        if not session_entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        compare_state = session_entity.progress_state or {}
        last_compare = compare_state.get("last_compare") or {}
        reference_text = self._get_reference_answer_text(
            question.id,
            last_compare.get("matched_answer_group_id"),
        )
        task = Task(type="gap_highlight", status="pending", payload={"session_id": session_id}, session_id=session_id)
        self.session.add(task)
        self.session.commit()
        try:
            start = datetime.now(timezone.utc)
            highlight = self.llm_client.highlight_gaps(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_draft=session_entity.user_answer_draft or "",
                reference_answer=reference_text,
            )
            prompt_messages = highlight.pop("_prompt_messages", None)
            saved_at = datetime.now(timezone.utc)
            latency = int((saved_at - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="gap_highlight",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                    "reference_answer": reference_text,
                    "prompt_messages": prompt_messages,
                },
                result=highlight,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            progress_state = dict(session_entity.progress_state or {})
            payload = dict(highlight)
            payload["saved_at"] = saved_at.isoformat()
            progress_state["last_gap_highlight"] = payload
            progress_state["phase"] = "refine"
            session_entity.progress_state = progress_state
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = payload
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
            try:
                self.run_refine_answer_task(session_id)
            except HTTPException:
                pass
        except LLMError as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return TaskRead.model_validate(task)

    def run_refine_answer_task(self, session_id: int) -> TaskRead:
        session_entity = self.session.get(SessionSchema, session_id)
        if not session_entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        gap_notes = session_entity.progress_state.get("last_gap_highlight") if session_entity.progress_state else None
        task = Task(type="refine_answer", status="pending", payload={"session_id": session_id}, session_id=session_id)
        self.session.add(task)
        self.session.commit()
        try:
            start = datetime.now(timezone.utc)
            refined = self.llm_client.refine_answer(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_draft=session_entity.user_answer_draft or "",
                gap_notes=gap_notes,
            )
            prompt_messages = refined.pop("_prompt_messages", None)
            saved_at = datetime.now(timezone.utc)
            latency = int((saved_at - start).total_seconds() * 1000)
            conversation = LLMConversation(
                session_id=session_id,
                task_id=task.id,
                purpose="refine_answer",
                messages={
                    "question": question.body,
                    "draft": session_entity.user_answer_draft or "",
                    "gap_notes": gap_notes,
                    "prompt_messages": prompt_messages,
                },
                result=refined,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=latency,
            )
            self.session.add(conversation)
            progress_state = dict(session_entity.progress_state or {})
            payload = dict(refined)
            payload["saved_at"] = saved_at.isoformat()
            progress_state["last_refine"] = payload
            progress_state["phase"] = "await_finalize"
            session_entity.progress_state = progress_state
            session_entity.updated_at = datetime.now(timezone.utc)
            self.session.add(session_entity)
            task.status = "succeeded"
            task.result_summary = payload
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

    def run_structure_pipeline_for_answer(self, answer_id: int, session_id: int | None = None) -> None:
        try:
            self.run_structure_task_for_answer(answer_id)
        except HTTPException:
            return
        try:
            self.run_sentence_translation_for_answer(answer_id)
        except HTTPException:
            pass
        sentence_rows = self.session.exec(
            select(Sentence.id)
            .join(Paragraph, Paragraph.id == Sentence.paragraph_id)
            .where(Paragraph.answer_id == answer_id)
            .order_by(Paragraph.order_index, Sentence.order_index)
        ).all()
        for row in sentence_rows:
            sentence_id = row if isinstance(row, int) else row[0]
            try:
                self.run_chunk_task(sentence_id)
            except HTTPException:
                continue
            try:
                self.run_chunk_lexeme_task(sentence_id)
            except HTTPException:
                continue
        if session_id:
            session_entity = self.session.get(SessionSchema, session_id)
            if session_entity:
                progress_state = dict(session_entity.progress_state or {})
                progress_state["phase"] = "learning"
                session_entity.progress_state = progress_state
                session_entity.updated_at = datetime.now(timezone.utc)
                self.session.add(session_entity)
                self.session.commit()

    def _ensure_sentence_flashcard(self, sentence_id: int) -> None:
        self.flashcard_service.get_or_create(
            FlashcardProgressCreate(entity_type="sentence", entity_id=sentence_id)
        )

    def _ensure_lexeme_flashcard(self, lexeme_id: int) -> None:
        self.flashcard_service.get_or_create(
            FlashcardProgressCreate(entity_type="lexeme", entity_id=lexeme_id)
        )

    def _ensure_chunk_flashcard(self, chunk_id: int) -> None:
        self.flashcard_service.get_or_create(
            FlashcardProgressCreate(entity_type="chunk", entity_id=chunk_id)
        )

    def _cleanup_orphan_lexemes(self, candidate_ids: Set[int]) -> None:
        if not candidate_ids:
            return
        for lexeme_id in candidate_ids:
            lexeme = self.session.get(Lexeme, lexeme_id)
            if not lexeme:
                continue
            linked = self.session.exec(
                select(ChunkLexeme.id).where(ChunkLexeme.lexeme_id == lexeme_id)
            ).first()
            if linked:
                continue
            self.session.delete(lexeme)

    def _remove_sentence_chunks(self, sentence_id: int) -> None:
        chunks = self.session.exec(
            select(SentenceChunk).where(SentenceChunk.sentence_id == sentence_id)
        ).all()
        if not chunks:
            return
        chunk_ids = [chunk.id for chunk in chunks if chunk.id is not None]
        orphan_candidates = self._clear_chunk_lexemes(chunk_ids)
        self._remove_chunk_flashcards(chunk_ids)
        for chunk in chunks:
            self.session.delete(chunk)
        self.session.commit()
        self._cleanup_orphan_lexemes(orphan_candidates)

    def _clear_chunk_lexemes(self, chunk_ids: list[int]) -> Set[int]:
        orphan_candidates: Set[int] = set()
        if not chunk_ids:
            return orphan_candidates
        links = self.session.exec(
            select(ChunkLexeme).where(ChunkLexeme.chunk_id.in_(chunk_ids))
        ).all()
        for link in links:
            if link.lexeme_id:
                orphan_candidates.add(link.lexeme_id)
            self.session.delete(link)
        self.session.commit()
        return orphan_candidates

    def _remove_chunk_flashcards(self, chunk_ids: list[int]) -> None:
        if not chunk_ids:
            return
        rows = self.session.exec(
            select(FlashcardProgress)
            .where(FlashcardProgress.entity_type == "chunk")
            .where(FlashcardProgress.entity_id.in_(chunk_ids))
        ).all()
        for row in rows:
            self.session.delete(row)

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

    def run_chunk_task(self, sentence_id: int) -> TaskRead:
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
            type="chunk_sentence",
            status="pending",
            payload={"sentence_id": sentence_id},
            session_id=None,
            answer_id=answer.id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        sentence_extra = dict(sentence.extra or {})
        known_issues: list[str] = sentence_extra.get("split_issues") or []
        self._remove_sentence_chunks(sentence_id)
        try:
            chunk_result = self.llm_client.chunk_sentence(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                sentence_text=sentence.text,
                known_issues=known_issues,
            )
            split_prompt_messages = chunk_result.pop("_prompt_messages", [])
            chunks = chunk_result.get("chunks") or []
            issues = self._assess_chunk_quality(sentence.text, chunks)
            if issues:
                sentence_extra["chunk_issues"] = issues
                sentence.extra = sentence_extra
                self.session.add(sentence)
                self.session.commit()
                conversation = LLMConversation(
                    session_id=None,
                    task_id=task.id,
                    purpose="chunk_sentence",
                    messages={
                        "split_prompt": split_prompt_messages,
                        "input_sentence": sentence.text,
                        "known_issues": known_issues,
                    },
                    result={
                        "chunks": chunks,
                        "error": "Chunk 质检失败",
                        "issues": issues,
                    },
                    model_name=getattr(self.llm_client, "model", None),
                    latency_ms=None,
                )
                self.session.add(conversation)
                self.session.commit()
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Chunk 质检失败；" + "；".join(issues))
            new_chunk_ids: list[int] = []
            for item in chunks:
                chunk = SentenceChunk(
                    sentence_id=sentence_id,
                    order_index=item.get("chunk_index") or len(chunks),
                    text=item.get("text") or "",
                    translation_en=item.get("translation_en"),
                    translation_zh=item.get("translation_zh"),
                    chunk_type=item.get("chunk_type"),
                    extra={},
                )
                self.session.add(chunk)
                self.session.flush()
                if chunk.id is not None:
                    new_chunk_ids.append(chunk.id)
            sentence_extra.pop("split_issues", None)
            sentence_extra.pop("chunk_issues", None)
            sentence.extra = sentence_extra
            self.session.add(sentence)
            self.session.commit()
            for chunk_id in new_chunk_ids:
                self._ensure_chunk_flashcard(chunk_id)
            conversation = LLMConversation(
                session_id=None,
                task_id=task.id,
                purpose="chunk_sentence",
                messages={
                    "split_prompt": split_prompt_messages,
                    "input_sentence": sentence.text,
                    "known_issues": known_issues,
                },
                result=chunk_result,
                model_name=getattr(self.llm_client, "model", None),
                latency_ms=None,
            )
            self.session.add(conversation)
            task.status = "succeeded"
            task.result_summary = {"chunks": len(chunks)}
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

    def run_chunk_lexeme_task(self, sentence_id: int) -> TaskRead:
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
        chunks = self.session.exec(
            select(SentenceChunk).where(SentenceChunk.sentence_id == sentence_id).order_by(SentenceChunk.order_index)
        ).all()
        if not chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先生成 Chunk")
        task = Task(
            type="chunk_lexeme",
            status="pending",
            payload={"sentence_id": sentence_id},
            session_id=None,
            answer_id=answer.id,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        chunk_ids = [chunk.id for chunk in chunks if chunk.id is not None]
        orphan_candidates = self._clear_chunk_lexemes(chunk_ids)
        try:
            chunk_dicts = [
                {
                    "chunk_index": chunk.order_index,
                    "text": chunk.text,
                    "translation_en": chunk.translation_en,
                    "translation_zh": chunk.translation_zh,
                }
                for chunk in chunks
            ]
            lexeme_result = self.llm_client.build_chunk_lexemes(
                question_type=question.type,
                question_title=question.title,
                sentence_text=sentence.text,
                chunks=chunk_dicts,
            )
            prompt_messages = lexeme_result.pop("_prompt_messages", [])
            lexeme_items = lexeme_result.get("lexemes") or []
            chunk_index_map = {chunk.order_index: chunk for chunk in chunks}
            per_chunk_counter: dict[int, int] = {chunk.order_index: 0 for chunk in chunks}
            created = 0
            lexeme_ids_for_cards: Set[int] = set()
            for item in lexeme_items:
                chunk_index = item.get("chunk_index")
                chunk_entity = chunk_index_map.get(chunk_index)
                if not chunk_entity:
                    continue
                headword = (item.get("headword") or "").strip()
                if not headword:
                    continue
                sense_label = (item.get("sense_label") or "").strip()
                hash_value = self._build_lexeme_hash(headword, sense_label, chunk_entity.text or "")
                lexeme = self.session.exec(select(Lexeme).where(Lexeme.hash == hash_value)).first()
                if not lexeme:
                    lexeme = Lexeme(
                        headword=headword,
                        lemma=headword,
                        sense_label=sense_label or None,
                        gloss=item.get("gloss"),
                        translation_en=item.get("translation_en"),
                        translation_zh=item.get("translation_zh"),
                        pos_tags=self._normalize_pos_tag(item.get("pos_tags")),
                        difficulty=self._normalize_difficulty(item.get("difficulty")),
                        hash=hash_value,
                        extra={},
                    )
                    self.session.add(lexeme)
                    self.session.commit()
                    self.session.refresh(lexeme)
                lexeme_ids_for_cards.add(lexeme.id)
                per_chunk_counter[chunk_index] = per_chunk_counter.get(chunk_index, 0) + 1
                chunk_lexeme = ChunkLexeme(
                    chunk_id=chunk_entity.id,
                    lexeme_id=lexeme.id,
                    order_index=per_chunk_counter[chunk_index],
                    role=item.get("role"),
                    extra={},
                )
                self.session.add(chunk_lexeme)
                created += 1
            missing_chunks = [idx for idx, count in per_chunk_counter.items() if count == 0]
            if missing_chunks:
                issues = [f"Chunk {idx} 未生成关键词" for idx in missing_chunks]
                sentence_extra = dict(sentence.extra or {})
                sentence_extra["lexeme_issues"] = issues
                sentence.extra = sentence_extra
                self.session.add(sentence)
                self.session.commit()
                conversation = LLMConversation(
                    session_id=None,
                    task_id=task.id,
                    purpose="chunk_lexeme",
                    messages={
                        "lexeme_prompt": prompt_messages,
                        "input_sentence": sentence.text,
                    },
                    result={"lexemes": lexeme_items, "error": "Lexeme 质检失败", "issues": issues},
                    model_name=getattr(self.llm_client, "model", None),
                    latency_ms=None,
                )
                self.session.add(conversation)
                self.session.commit()
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="部分 Chunk 未生成关键词；" + "；".join(issues))
            self.session.commit()
            self._cleanup_orphan_lexemes(orphan_candidates)
            for lexeme_id in lexeme_ids_for_cards:
                self._ensure_lexeme_flashcard(lexeme_id)
            sentence_extra = dict(sentence.extra or {})
            sentence_extra.pop("lexeme_issues", None)
            sentence.extra = sentence_extra
            self.session.add(sentence)
            self.session.commit()
            conversation = LLMConversation(
                session_id=None,
                task_id=task.id,
                purpose="chunk_lexeme",
                messages={
                    "lexeme_prompt": prompt_messages,
                    "input_sentence": sentence.text,
                },
                result=lexeme_result,
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

    def _normalize_pos_tag(self, pos_value: str | None) -> str | None:
        if not pos_value:
            return None
        normalized = " ".join(pos_value.strip().lower().split())
        mapping = {
            "noun": {"noun", "n", "名词"},
            "noun phrase": {"noun phrase", "名词短语", "np"},
            "verb": {"verb", "v", "动词"},
            "verb phrase": {"verb phrase", "动词短语", "vp"},
            "adjective": {"adjective", "adj", "形容词"},
            "adverb": {"adverb", "adv", "副词"},
            "expression": {"expression", "短语", "表达", "phrase"},
            "preposition phrase": {"preposition phrase", "介词短语"},
            "conjunction": {"conjunction", "连词"},
        }
        for canonical, aliases in mapping.items():
            if normalized in aliases:
                return canonical
        return None

    def _normalize_difficulty(self, difficulty: str | None) -> str | None:
        if not difficulty:
            return None
        normalized = difficulty.strip().upper()
        allowed = {"A1", "A2", "B1", "B2", "C1", "C2"}
        return normalized if normalized in allowed else None

    def _assess_chunk_quality(self, sentence_text: str, chunks: list[dict]) -> list[str]:
        issues: list[str] = []
        if not chunks:
            issues.append("未生成任何 Chunk")
            return issues
        total_length = len(sentence_text.strip()) or 1
        chunk_text = "".join((item.get("text") or "").strip() for item in chunks)
        if len(chunk_text) < total_length * 0.4:
            issues.append("Chunk 覆盖度不足")
        for idx, item in enumerate(chunks, start=1):
            if not (item.get("text") or "").strip():
                issues.append(f"Chunk {idx} 内容为空")
        return issues

    def _normalize_pos_tag(self, pos_value: str | None) -> str | None:
        if not pos_value:
            return None
        normalized = " ".join(pos_value.strip().lower().split())
        mapping = {
            "noun": {"noun", "n", "名词"},
            "noun phrase": {"noun phrase", "名词短语", "np"},
            "verb": {"verb", "v", "动词"},
            "verb phrase": {"verb phrase", "动词短语", "vp"},
            "adjective": {"adjective", "adj", "形容词"},
            "adverb": {"adverb", "adv", "副词"},
            "expression": {"expression", "短语", "表达", "phrase"},
            "preposition phrase": {"preposition phrase", "介词短语"},
            "conjunction": {"conjunction", "连词"},
        }
        for canonical, aliases in mapping.items():
            if normalized in aliases:
                return canonical
        return None

    def _normalize_difficulty(self, difficulty: str | None) -> str | None:
        if not difficulty:
            return None
        normalized = difficulty.strip().upper()
        allowed = {"A1", "A2", "B1", "B2", "C1", "C2"}
        return normalized if normalized in allowed else None
