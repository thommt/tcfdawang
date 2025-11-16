from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.fetchers.manager import FetchManager
from app.models.fetch import FetchedQuestion
from app.models.question import QuestionCreate, QuestionRead
from app.models.fetch_task import TaskRead
from app.db.schemas import Task
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
            summary = {
                "count": len(results),
                "results": [question.model_dump() for question in results],
                "t2_count": sum(1 for q in results if q.type == "T2"),
                "t3_count": sum(1 for q in results if q.type == "T3"),
            }
            task.status = "succeeded"
            task.result_summary = summary
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

    def list_results(self, task_id: int) -> List[FetchedQuestion]:
        task = self.session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        raw_results = task.result_summary.get("results", [])
        return [FetchedQuestion(**item) for item in raw_results]

    def import_results(self, task_id: int) -> List[QuestionRead]:
        task = self.session.get(Task, task_id)
        if not task:
            raise ValueError("No fetch task found")
        raw_results = task.result_summary.get("results")
        if not raw_results:
            raise ValueError("No fetch results available for this task")
        question_service = QuestionService(self.session)
        created: List[QuestionRead] = []
        for row in raw_results:
            data = FetchedQuestion(**row)
            payload = QuestionCreate(
                type=data.type,
                source=data.source,
                year=data.year,
                month=data.month,
                suite=data.suite,
                number=data.number,
                title=data.title,
                body=data.body,
                tags=data.tags,
            )
            created_question = question_service.upsert_question(payload)
            created.append(created_question)
        return created
