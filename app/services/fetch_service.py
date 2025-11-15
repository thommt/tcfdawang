from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.fetchers.manager import FetchManager
from app.models.fetch import FetchedQuestion
from app.models.question import QuestionCreate
from app.models.fetch_task import TaskRead
from app.db.schemas import Task, FetchResult
from app.services.question_service import QuestionService


class FetchTaskService:
    def __init__(self, session: Session, fetch_manager: FetchManager):
        self.session = session
        self.fetch_manager = fetch_manager

    def create_fetch_task(self, urls: List[str]) -> Task:
        if not urls:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No URLs provided")
        task = Task(
            type="fetch",
            status="pending",
            payload={"urls": urls},
            result_summary={},
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def run_fetch_task(self, task: Task) -> List[FetchedQuestion]:
        try:
            results = self.fetch_manager.fetch_urls(task.payload["urls"])
            self._store_results(task.id, results)
            task.status = "succeeded"
            task.result_summary = {"count": len(results)}
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
            return results
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.updated_at = datetime.now(timezone.utc)
            self.session.add(task)
            self.session.commit()
            raise

    def _store_results(self, task_id: int, results: List[FetchedQuestion]) -> None:
        statement = select(FetchResult).where(FetchResult.task_id == task_id)
        existing = self.session.exec(statement).all()
        for item in existing:
            self.session.delete(item)
        for question in results:
            self.session.add(FetchResult(task_id=task_id, data=question.model_dump()))
        self.session.commit()

    def list_results(self, task_id: int) -> List[FetchedQuestion]:
        statement = select(FetchResult).where(FetchResult.task_id == task_id)
        rows = self.session.exec(statement).all()
        if not rows:
            task = self.session.get(Task, task_id)
            if not task:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return [FetchedQuestion(**row.data) for row in rows]
