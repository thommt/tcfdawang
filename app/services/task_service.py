from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
        task = Task(type="structure", status="pending", payload={"answer_id": answer_id}, session_id=None)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        try:
            # Clear existing structure
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
            self.session.commit()

            structure = self.llm_client.structure_answer(
                question_type=question.type,
                question_title=question.title,
                question_body=question.body,
                answer_text=answer.text,
            )
            for idx, para in enumerate(structure.get("paragraphs", []), start=1):
                paragraph = Paragraph(
                    answer_id=answer_id,
                    order_index=idx,
                    role_label=para.get("role"),
                    summary=para.get("summary"),
                    extra={},
                )
                self.session.add(paragraph)
                self.session.commit()
                self.session.refresh(paragraph)
                for s_idx, sentence_data in enumerate(para.get("sentences", []), start=1):
                    sentence = Sentence(
                        paragraph_id=paragraph.id,
                        order_index=s_idx,
                        text=sentence_data.get("text", ""),
                        translation=sentence_data.get("translation"),
                        extra={},
                    )
                    self.session.add(sentence)
                self.session.commit()
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
