from __future__ import annotations

from datetime import datetime, timezone
from typing import List

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
        self._ensure_question_exists(data.question_id)
        entity = SessionSchema(
            question_id=data.question_id,
            answer_id=data.answer_id,
            session_type=data.session_type,
            status=data.status,
            user_answer_draft=data.user_answer_draft,
            progress_state=data.progress_state,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return self._to_session_read(entity)

    def get_session(self, session_id: int) -> SessionRead:
        session = self._get_session_entity(session_id)
        return self._to_session_read(session)

    def update_session(self, session_id: int, data: SessionUpdate) -> SessionRead:
        entity = self._get_session_entity(session_id)
        update_data = data.model_dump(exclude_unset=True)
        if "answer_id" in update_data and update_data["answer_id"] is not None:
            self._ensure_answer_exists(update_data["answer_id"])
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

    def finalize_session(self, session_id: int, payload: SessionFinalizePayload) -> SessionRead:
        session_entity = self._get_session_entity(session_id)
        question = self.session.get(Question, session_entity.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        if payload.answer_group_id:
            group = self.session.get(AnswerGroupSchema, payload.answer_group_id)
            if not group:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")
        else:
            title = payload.group_title or question.title
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

        version_index = self._next_version_index(group.id)
        answer = AnswerSchema(
            answer_group_id=group.id,
            version_index=version_index,
            status="active",
            title=payload.answer_title,
            text=payload.answer_text,
        )
        self.session.add(answer)
        self.session.commit()
        self.session.refresh(answer)
        session_entity.answer_id = answer.id
        session_entity.status = "completed"
        session_entity.completed_at = datetime.now(timezone.utc)
        session_entity.updated_at = datetime.now(timezone.utc)
        self.session.add(session_entity)
        self.session.commit()
        self.session.refresh(session_entity)
        return self._to_session_read(session_entity)

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
        entity = SessionSchema(
            question_id=question.id,
            answer_id=answer.id,
            session_type="review",
            status="draft",
            user_answer_draft=answer.text,
            progress_state={"review_source_answer_id": answer.id},
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

    def _ensure_answer_group_exists(self, group_id: int) -> None:
        if not self.session.get(AnswerGroupSchema, group_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer group not found")

    def _ensure_answer_exists(self, answer_id: int) -> None:
        if not self.session.get(AnswerSchema, answer_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

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
