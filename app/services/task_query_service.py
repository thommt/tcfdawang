from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session as DBSession, select

from app.db.schemas import Task, Session as SessionSchema
from app.models.fetch_task import TaskRead


class TaskQueryService:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    def list_tasks(
        self,
        *,
        session_id: Optional[int] = None,
        question_id: Optional[int] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        answer_id: Optional[int] = None,
    ) -> List[TaskRead]:
        statement = select(Task)
        if session_id is not None:
            statement = statement.where(Task.session_id == session_id)
        if answer_id is not None:
            statement = statement.where(Task.answer_id == answer_id)
        if task_type is not None:
            statement = statement.where(Task.type == task_type)
        if status is not None:
            statement = statement.where(Task.status == status)
        if question_id is not None:
            statement = statement.join(SessionSchema).where(SessionSchema.question_id == question_id)
        statement = statement.order_by(Task.created_at.desc())
        tasks = self.session.exec(statement).all()
        return [TaskRead.model_validate(task) for task in tasks]

    def get_task(self, task_id: int) -> TaskRead:
        task = self.session.get(Task, task_id)
        if not task:
            raise ValueError("Task not found")
        return TaskRead.model_validate(task)
