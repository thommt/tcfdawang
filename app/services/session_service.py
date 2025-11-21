from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlmodel import Session as DBSession, select

from app.db.schemas import (
    AnswerGroup as AnswerGroupSchema,
    Answer as AnswerSchema,
    Question,
    Session as SessionSchema,
    Task,
    LLMConversation,
    Paragraph as ParagraphSchema,
    Sentence as SentenceSchema,
    SentenceChunk,
    ChunkLexeme,
    Lexeme,
    FlashcardProgress,
    LiveTurn,
)
from app.models.answer import (
    AnswerCreate,
    AnswerRead,
    AnswerGroupCreate,
    AnswerGroupRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
    SessionFinalizePayload,
    AnswerHistoryRead,
    LLMConversationRead,
    SessionHistoryRead,
)
from app.models.fetch_task import TaskRead


class SessionService:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    # Session operations
    def list_sessions(self) -> List[SessionRead]:
        statement = select(SessionSchema)
        sessions = self.session.exec(statement).all()
        return [self._to_session_read(item) for item in sessions]

    def create_session(self, data: SessionCreate) -> SessionRead:
        question = self.session.get(Question, data.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        self._ensure_question_metadata_ready(question)
        progress_state = dict(data.progress_state or {})
        progress_state.setdefault("phase", "draft")
        progress_state.setdefault("phase_status", "idle")
        progress_state.pop("phase_error", None)
        entity = SessionSchema(
            question_id=data.question_id,
            answer_id=data.answer_id,
            session_type=data.session_type,
            status=data.status,
            user_answer_draft=data.user_answer_draft,
            progress_state=progress_state,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_session_read(entity)

    def delete_session(self, session_id: int, *, force: bool = False) -> None:
        session_entity = self._get_session_entity(session_id)
        if session_entity.answer_id and not force:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已关联答案的 Session 不可删除")
        tasks = self.session.exec(select(Task).where(Task.session_id == session_id)).all()
        for task in tasks:
            conversation = self.session.exec(
                select(LLMConversation).where(LLMConversation.task_id == task.id)
            ).first()
            if conversation:
                self.session.delete(conversation)
            self.session.delete(task)
        conversations = self.session.exec(
            select(LLMConversation)
            .where(LLMConversation.session_id == session_id)
            .where(LLMConversation.task_id.is_(None))
        ).all()
        for log in conversations:
            self.session.delete(log)
        live_turns = self.session.exec(
            select(LiveTurn).where(LiveTurn.session_id == session_id)
        ).all()
        for turn in live_turns:
            self.session.delete(turn)
        self.session.delete(session_entity)
        self.session.commit()

    def get_session(self, session_id: int) -> SessionRead:
        session = self._get_session_entity(session_id)
        return self._to_session_read(session)

    def update_session(self, session_id: int, data: SessionUpdate) -> SessionRead:
        entity = self._get_session_entity(session_id)
        update_data = data.model_dump(exclude_unset=True)
        if "answer_id" in update_data and update_data["answer_id"] is not None:
            self._ensure_answer_exists(update_data["answer_id"])
        if "user_answer_draft" in update_data and entity.answer_id is None:
            progress_state = dict(entity.progress_state or {})
            progress_state["phase"] = "draft"
            progress_state["phase_status"] = "idle"
            for key in ["last_eval", "last_compare", "last_compose"]:
                progress_state.pop(key, None)
            progress_state.pop("phase_error", None)
            entity.progress_state = progress_state
            entity.status = self._status_from_phase("draft")
            entity.completed_at = None
        if data.progress_state is not None:
            entity.progress_state = data.progress_state
            update_data.pop("progress_state", None)
        for key, value in update_data.items():
            setattr(entity, key, value)
        entity.updated_at = datetime.now(timezone.utc)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_session_read(entity)

    def start_live_session(self, session_id: int) -> SessionRead:
        entity = self._get_session_entity(session_id)
        question = self.session.get(Question, entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        if question.type != "T2":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅 T2 题目可使用实时对话模式")
        progress = dict(entity.progress_state or {})
        progress["mode"] = "live"
        progress["phase"] = "live"
        progress["phase_status"] = "idle"
        progress["live_status"] = "active"
        progress["live_turn_count"] = int(progress.get("live_turn_count") or 0)
        progress["live_stream_token"] = progress.get("live_stream_token") or uuid4().hex
        entity.progress_state = progress
        entity.status = self._status_from_phase("live")
        entity.updated_at = datetime.now(timezone.utc)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_session_read(entity)

    def create_live_turn(
        self,
        session_id: int,
        candidate_query: str,
        candidate_followup: Optional[str] = None,
    ) -> LiveTurn:
        entity = self._get_session_entity(session_id)
        self._ensure_live_mode(entity)
        progress = dict(entity.progress_state or {})
        next_index = int(progress.get("live_turn_count") or 0) + 1
        turn = LiveTurn(
            session_id=session_id,
            turn_index=next_index,
            candidate_query=candidate_query,
            candidate_followup=candidate_followup,
            meta={},
        )
        self.session.add(turn)
        progress["live_turn_count"] = next_index
        progress["live_status"] = "active"
        progress["phase"] = "live"
        progress["phase_status"] = "running"
        entity.progress_state = progress
        entity.updated_at = datetime.now(timezone.utc)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(turn)
        return turn

    def record_live_reply(
        self,
        turn_id: int,
        reply_text: str,
        meta: Optional[dict] = None,
    ) -> LiveTurn:
        turn = self.session.get(LiveTurn, turn_id)
        if not turn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live turn not found")
        turn.examiner_reply = reply_text
        if meta:
            merged = dict(turn.meta or {})
            merged.update(meta)
            turn.meta = merged
        self.session.add(turn)
        session_entity = self._get_session_entity(turn.session_id)
        progress = dict(session_entity.progress_state or {})
        progress["phase_status"] = "idle"
        progress["live_status"] = "active"
        session_entity.progress_state = progress
        session_entity.updated_at = datetime.now(timezone.utc)
        self.session.add(session_entity)
        self.session.commit()
        self.session.refresh(turn)
        return turn

    def mark_live_turn_error(self, turn_id: int, message: str) -> None:
        turn = self.session.get(LiveTurn, turn_id)
        if not turn:
            return
        meta = dict(turn.meta or {})
        meta["error"] = message
        turn.meta = meta
        self.session.add(turn)
        session_entity = self._get_session_entity(turn.session_id)
        progress = dict(session_entity.progress_state or {})
        progress["phase_status"] = "failed"
        progress["phase_error"] = message
        session_entity.progress_state = progress
        session_entity.updated_at = datetime.now(timezone.utc)
        self.session.add(session_entity)
        self.session.commit()

    def update_live_status(self, session_id: int, status_value: str) -> None:
        entity = self._get_session_entity(session_id)
        progress = dict(entity.progress_state or {})
        progress["live_status"] = status_value
        entity.progress_state = progress
        entity.updated_at = datetime.now(timezone.utc)
        self.session.add(entity)
        self.session.commit()

    def list_live_turns(self, session_id: int) -> List[LiveTurn]:
        statement = (
            select(LiveTurn)
            .where(LiveTurn.session_id == session_id)
            .order_by(LiveTurn.turn_index)
        )
        return self.session.exec(statement).all()

    def prepare_live_finalize_payload(self, session_id: int, *, force: bool = False) -> SessionFinalizePayload:
        entity = self._get_session_entity(session_id)
        question = self.session.get(Question, entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        self._ensure_live_mode(entity, require_active=False)
        turns = self.list_live_turns(session_id)
        min_turns = 1 if force else 12
        if len(turns) < min_turns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"实时对话至少需要 {min_turns} 轮才能完成，目前仅 {len(turns)} 轮",
            )
        transcript = self._render_live_transcript(turns)
        progress = dict(entity.progress_state or {})
        title = self._title_with_direction(question.title, progress.get("selected_direction_descriptor"))
        payload = SessionFinalizePayload(
            answer_group_id=progress.get("selected_answer_group_id"),
            group_title=None,
            group_descriptor=None,
            dialogue_profile=None,
            answer_title=title,
            answer_text=transcript,
        )
        return payload

    def _render_live_transcript(self, turns: List[LiveTurn]) -> str:
        sections: List[str] = []
        for turn in turns:
            prefix = f"Tour {turn.turn_index}"
            question_text = turn.candidate_query.strip()
            reply_text = (turn.examiner_reply or "").strip()
            followup = (turn.candidate_followup or "").strip()
            block_lines = []
            if question_text:
                block_lines.append(f"考生: {question_text}")
            if reply_text:
                block_lines.append(f"考官: {reply_text}")
            if followup:
                block_lines.append(f"考生: {followup}")
            if block_lines:
                sections.append(f"{prefix}\n" + "\n".join(block_lines))
        return "\n\n".join(sections)

    def _ensure_live_mode(self, entity: SessionSchema, *, require_active: bool = True) -> None:
        progress = entity.progress_state or {}
        if progress.get("mode") != "live":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该 Session 未开启实时对话模式")
        if require_active and progress.get("live_status") == "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="实时对话已结束")

    def finalize_session(self, session_id: int, payload: SessionFinalizePayload) -> SessionRead:
        session_entity = self._get_session_entity(session_id)
        progress_state = dict(session_entity.progress_state or {})
        phase = progress_state.get("phase", "draft")
        if not (progress_state.get("mode") == "live" and phase == "live") and phase not in {"await_finalize", "await_new_group"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前阶段不可完成 Session")
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        progress_state = dict(session_entity.progress_state or {})
        if payload.answer_group_id:
            group = self.session.get(AnswerGroupSchema, payload.answer_group_id)
            if not group:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")
        else:
            title = payload.group_title or self._title_with_direction(question.title, progress_state.get("selected_direction_descriptor"))
            group = AnswerGroupSchema(
                question_id=question.id,
                title=title,
                slug=question.type + "-" + str(question.id),
                descriptor=payload.group_descriptor,
                dialogue_profile=payload.dialogue_profile or {},
            )
            self.session.add(group)
            self.session.commit()
            self.session.refresh(group)
        progress_state["selected_answer_group_id"] = group.id
        selected_direction = progress_state.get("selected_direction_descriptor")
        if selected_direction and (not group.direction_descriptor):
            group.direction_descriptor = selected_direction
            self.session.add(group)
            self.session.commit()
            self.session.refresh(group)

        version_index = self._next_version_index(group.id)
        answer_title = payload.answer_title or self._title_with_direction(
            question.title, progress_state.get("selected_direction_descriptor")
        )
        answer = AnswerSchema(
            answer_group_id=group.id,
            version_index=version_index,
            status="active",
            title=answer_title,
            text=payload.answer_text,
        )
        self.session.add(answer)
        self.session.commit()
        self.session.refresh(answer)
        session_entity.answer_id = answer.id
        progress_state = dict(session_entity.progress_state or {})
        progress_state["phase"] = "structure_pipeline"
        progress_state["phase_status"] = "running"
        session_entity.progress_state = progress_state
        session_entity.status = self._status_from_phase("structure_pipeline")
        session_entity.completed_at = None
        session_entity.updated_at = datetime.now(timezone.utc)
        self.session.add(session_entity)
        self.session.commit()
        self.session.refresh(session_entity)
        return self._to_session_read(session_entity)

    def mark_learning_complete(self, session_id: int) -> SessionRead:
        session = self._get_session_entity(session_id)
        progress = dict(session.progress_state or {})
        if progress.get("phase") != "learning":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前阶段不可完成")
        if progress.get("phase_status") == "running":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="学习数据生成中，请稍候")
        progress["phase"] = "completed"
        progress["phase_status"] = "idle"
        session.progress_state = progress
        session.status = self._status_from_phase("completed")
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return self._to_session_read(session)

    # Answer group operations
    def create_answer_group(self, data: AnswerGroupCreate) -> AnswerGroupRead:
        self._ensure_question_exists(data.question_id)
        entity = AnswerGroupSchema(
            question_id=data.question_id,
            slug=data.slug,
            title=data.title,
            descriptor=data.descriptor,
            dialogue_profile=data.dialogue_profile,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_answer_group_read(entity)

    def get_answer_group(self, group_id: int) -> AnswerGroupRead:
        group = self.session.get(AnswerGroupSchema, group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")
        return self._to_answer_group_read(group)

    def list_answer_groups(self, question_id: int) -> List[AnswerGroupRead]:
        self._ensure_question_exists(question_id)
        statement = (
            select(AnswerGroupSchema)
            .where(AnswerGroupSchema.question_id == question_id)
            .order_by(AnswerGroupSchema.created_at)
        )
        groups = self.session.exec(statement).all()
        return [self._to_answer_group_read(group, include_answers=True) for group in groups]

    def delete_answer_group(self, group_id: int) -> None:
        group = self.session.get(AnswerGroupSchema, group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")
        answers = self.session.exec(select(AnswerSchema).where(AnswerSchema.answer_group_id == group_id)).all()
        for answer in answers:
            sessions = self.session.exec(
                select(SessionSchema).where(SessionSchema.answer_id == answer.id)
            ).all()
            for session in sessions:
                self.delete_session(session.id, force=True)
            self._delete_answer_dependencies(answer.id)
            self.session.delete(answer)
        self.session.delete(group)
        self.session.commit()

    def delete_answer(self, answer_id: int) -> None:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        latest = self.session.exec(
            select(AnswerSchema)
            .where(AnswerSchema.answer_group_id == answer.answer_group_id)
            .order_by(AnswerSchema.version_index.desc())
        ).first()
        if latest and latest.id != answer.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能删除最新版本的答案",
            )
        self._delete_answer_dependencies(answer_id)
        self.session.delete(answer)
        self.session.commit()

    # Answer operations
    def create_answer(self, data: AnswerCreate) -> AnswerRead:
        self._ensure_answer_group_exists(data.answer_group_id)
        entity = AnswerSchema(
            answer_group_id=data.answer_group_id,
            version_index=data.version_index,
            status=data.status,
            title=data.title,
            text=data.text,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_answer_read(entity)

    def get_answer(self, answer_id: int) -> AnswerRead:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        return self._to_answer_read(answer)

    def create_review_session(self, answer_id: int) -> SessionRead:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        group = self.session.get(AnswerGroupSchema, answer.answer_group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")
        question = self.session.get(Question, group.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        self._ensure_question_metadata_ready(question)
        progress_state = {
            "review_source_answer_id": answer.id,
            "phase": "draft",
            "phase_status": "idle",
            "selected_answer_group_id": group.id,
        }
        entity = SessionSchema(
            question_id=question.id,
            answer_id=answer.id,
            session_type="review",
            status="draft",
            user_answer_draft=answer.text,
            progress_state=progress_state,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_session_read(entity)

    def get_session_history(self, session_id: int) -> SessionHistoryRead:
        session_entity = self._get_session_entity(session_id)
        tasks = self.session.exec(
            select(Task).where(Task.session_id == session_id).order_by(Task.created_at.desc())
        ).all()
        task_reads = [TaskRead.model_validate(task) for task in tasks]
        task_ids = [task.id for task in tasks if task.id is not None]
        conversation_conditions = [LLMConversation.session_id == session_id]
        if task_ids:
            conversation_conditions.append(LLMConversation.task_id.in_(task_ids))
        conversation_statement = (
            select(LLMConversation)
            .where(or_(*conversation_conditions))
            .order_by(LLMConversation.created_at.desc())
        )
        conversations = self.session.exec(conversation_statement).all()
        conversation_reads = [LLMConversationRead.model_validate(conv) for conv in conversations]
        return SessionHistoryRead(
            session=self._to_session_read(session_entity),
            tasks=task_reads,
            conversations=conversation_reads,
        )

    def get_answer_history(self, answer_id: int) -> AnswerHistoryRead:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        group = self.session.get(AnswerGroupSchema, answer.answer_group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")

        sessions = (
            self.session.exec(
                select(SessionSchema)
                .where(SessionSchema.answer_id == answer_id)
                .order_by(SessionSchema.started_at)
            ).all()
        )
        session_reads = [self._to_session_read(item) for item in sessions]
        session_ids = [item.id for item in sessions if item.id is not None]

        task_statement = select(Task)
        if session_ids:
            task_statement = task_statement.where(
                or_(Task.answer_id == answer_id, Task.session_id.in_(session_ids))
            )
        else:
            task_statement = task_statement.where(Task.answer_id == answer_id)
        task_statement = task_statement.order_by(Task.created_at.desc())
        tasks = self.session.exec(task_statement).all()
        task_reads = [TaskRead.model_validate(task) for task in tasks]
        task_ids = [task.id for task in tasks if task.id is not None]

        conversation_conditions = []
        if session_ids:
            conversation_conditions.append(LLMConversation.session_id.in_(session_ids))
        if task_ids:
            conversation_conditions.append(LLMConversation.task_id.in_(task_ids))
        if conversation_conditions:
            conversation_statement = select(LLMConversation).order_by(LLMConversation.created_at.desc())
            if len(conversation_conditions) == 1:
                conversation_statement = conversation_statement.where(conversation_conditions[0])
            else:
                conversation_statement = conversation_statement.where(
                    or_(*conversation_conditions)  # type: ignore[arg-type]
                )
            conversations = self.session.exec(conversation_statement).all()
        else:
            conversations = []
        conversation_reads = [LLMConversationRead.model_validate(conv) for conv in conversations]

        return AnswerHistoryRead(
            answer=self._to_answer_read(answer),
            group=self._to_answer_group_read(group, include_answers=True),
            sessions=session_reads,
            tasks=task_reads,
            conversations=conversation_reads,
        )

    # Helpers
    def _ensure_question_exists(self, question_id: int) -> None:
        if not self.session.get(Question, question_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    def _ensure_question_metadata_ready(self, question: Question) -> None:
        plan = question.direction_plan if isinstance(question.direction_plan, dict) else None
        recommended = (plan or {}).get("recommended") if isinstance(plan, dict) else None
        if not recommended or not recommended.get("title"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="题目尚未完成 LLM 元数据分析，请先在题目页运行“生成标题/结构”。",
            )

    def _ensure_answer_group_exists(self, group_id: int) -> None:
        if not self.session.get(AnswerGroupSchema, group_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")

    def _ensure_answer_exists(self, answer_id: int) -> None:
        if not self.session.get(AnswerSchema, answer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    def _title_with_direction(self, base: str | None, direction: str | None) -> str:
        base_title = (base or "新答案组").strip()
        trimmed_direction = (direction or "").strip()
        if not trimmed_direction:
            return base_title
        if trimmed_direction in base_title:
            return base_title
        return f"{base_title}（{trimmed_direction}）"

    def _delete_answer_dependencies(self, answer_id: int | None) -> None:
        if not answer_id:
            return
        paragraphs = self.session.exec(
            select(ParagraphSchema).where(ParagraphSchema.answer_id == answer_id)
        ).all()
        for paragraph in paragraphs:
            sentences = self.session.exec(
                select(SentenceSchema).where(SentenceSchema.paragraph_id == paragraph.id)
            ).all()
            for sentence in sentences:
                self._delete_sentence_with_chunks(sentence)
                self.session.delete(sentence)
            self.session.delete(paragraph)
        sessions = self.session.exec(
            select(SessionSchema).where(SessionSchema.answer_id == answer_id)
        ).all()
        for session in sessions:
            session.answer_id = None
            session.updated_at = datetime.now(timezone.utc)
            self.session.add(session)
        tasks = self.session.exec(select(Task).where(Task.answer_id == answer_id)).all()
        for task in tasks:
            conversation = self.session.exec(
                select(LLMConversation).where(LLMConversation.task_id == task.id)
            ).first()
            if conversation:
                self.session.delete(conversation)
            self.session.delete(task)

    def _delete_sentence_with_chunks(self, sentence: SentenceSchema) -> None:
        if not sentence.id:
            return
        self._delete_flashcards_for_entities("sentence", [sentence.id])
        chunks = self.session.exec(
            select(SentenceChunk).where(SentenceChunk.sentence_id == sentence.id)
        ).all()
        if not chunks:
            return
        chunk_ids = [chunk.id for chunk in chunks if chunk.id is not None]
        if chunk_ids:
            self._delete_flashcards_for_entities("chunk", chunk_ids)
            links = self.session.exec(
                select(ChunkLexeme).where(ChunkLexeme.chunk_id.in_(chunk_ids))
            ).all()
            lexeme_ids: set[int] = set()
            for link in links:
                if link.lexeme_id:
                    lexeme_ids.add(link.lexeme_id)
                self.session.delete(link)
            for chunk in chunks:
                self.session.delete(chunk)
            for lexeme_id in lexeme_ids:
                self._cleanup_lexeme_if_orphan(lexeme_id)

    def _cleanup_lexeme_if_orphan(self, lexeme_id: int | None) -> None:
        if not lexeme_id:
            return
        linked = self.session.exec(
            select(ChunkLexeme.id).where(ChunkLexeme.lexeme_id == lexeme_id)
        ).first()
        if linked:
            return
        self._delete_flashcards_for_entities("lexeme", [lexeme_id])
        lexeme = self.session.get(Lexeme, lexeme_id)
        if lexeme:
            self.session.delete(lexeme)

    def _delete_flashcards_for_entities(self, entity_type: str, entity_ids: list[int | None]) -> None:
        valid_ids = [entity_id for entity_id in entity_ids if entity_id is not None]
        if not valid_ids:
            return
        rows = self.session.exec(
            select(FlashcardProgress)
            .where(FlashcardProgress.entity_type == entity_type)
            .where(FlashcardProgress.entity_id.in_(valid_ids))
        ).all()
        for row in rows:
            self.session.delete(row)

    def _status_from_phase(self, phase: str | None) -> str:
        if not phase or phase == "draft":
            return "draft"
        if phase == "completed":
            return "completed"
        return "in_progress"

    def _get_session_entity(self, session_id: int) -> SessionSchema:
        entity = self.session.get(SessionSchema, session_id)
        if not entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return entity

    def _next_version_index(self, group_id: int) -> int:
        statement = select(AnswerSchema).where(AnswerSchema.answer_group_id == group_id)
        answers = self.session.exec(statement).all()
        if not answers:
            return 1
        return max(answer.version_index for answer in answers) + 1

    def _to_session_read(self, session: SessionSchema) -> SessionRead:
        return SessionRead(
            id=session.id,
            question_id=session.question_id,
            answer_id=session.answer_id,
            session_type=session.session_type,
            status=session.status,
            user_answer_draft=session.user_answer_draft,
            progress_state=session.progress_state,
            started_at=session.started_at,
            completed_at=session.completed_at,
        )

    def _to_answer_group_read(self, group: AnswerGroupSchema, include_answers: bool = False) -> AnswerGroupRead:
        data = group.model_dump()
        data["created_at"] = group.created_at
        if include_answers:
            answers = (
                self.session.exec(
                    select(AnswerSchema)
                    .where(AnswerSchema.answer_group_id == group.id)
                    .order_by(AnswerSchema.version_index)
                ).all()
            )
            data["answers"] = [self._to_answer_read(ans) for ans in answers]
        else:
            data["answers"] = []
        return AnswerGroupRead(**data)

    def _to_answer_read(self, answer: AnswerSchema) -> AnswerRead:
        return AnswerRead(
            id=answer.id,
            answer_group_id=answer.answer_group_id,
            version_index=answer.version_index,
            status=answer.status,
            title=answer.title,
            text=answer.text,
            created_at=answer.created_at,
        )
