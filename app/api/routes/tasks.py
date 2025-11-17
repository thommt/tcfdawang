from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_session
from app.models.fetch_task import TaskRead
from app.services.task_query_service import TaskQueryService


def get_task_query_service(db=Depends(get_session)) -> TaskQueryService:
    return TaskQueryService(db)


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskRead])
def list_tasks(
    session_id: Optional[int] = None,
    question_id: Optional[int] = None,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    service: TaskQueryService = Depends(get_task_query_service),
) -> List[TaskRead]:
    return service.list_tasks(session_id=session_id, question_id=question_id, task_type=task_type, status=status)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, service: TaskQueryService = Depends(get_task_query_service)) -> TaskRead:
    try:
        return service.get_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


__all__ = ["router"]
