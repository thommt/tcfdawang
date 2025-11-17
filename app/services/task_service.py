from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession

from app.db.schemas import (
    Task,
    Session as SessionSchema,
    Question,
    LLMConversation,
)
from app.models.fetch_task import TaskRead
from app.services.llm_service import QuestionLLMClient, LLMError


class TaskService:
    def __init__(self, session: DBSession, llm_client: QuestionLLMClient) -> None:
        self.session = session
        self.llm_client = llm_client

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
        self.session.refresh(task)
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
