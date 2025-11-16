from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import (
    AnswerGroup as AnswerGroupSchema,
    Answer as AnswerSchema,
    Question,
    Session as SessionSchema,
)
from app.models.answer import (
    AnswerCreate,
    AnswerRead,
    AnswerGroupCreate,
    AnswerGroupRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
)


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
        session = self.session.get(SessionSchema, session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return self._to_session_read(session)

    def update_session(self, session_id: int, data: SessionUpdate) -> SessionRead:
        entity = self.session.get(SessionSchema, session_id)
        if not entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
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

    def _to_answer_group_read(self, group: AnswerGroupSchema) -> AnswerGroupRead:
        return AnswerGroupRead(
            id=group.id,
            question_id=group.question_id,
            slug=group.slug,
            title=group.title,
            descriptor=group.descriptor,
            dialogue_profile=group.dialogue_profile,
            created_at=group.created_at,
        )

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
