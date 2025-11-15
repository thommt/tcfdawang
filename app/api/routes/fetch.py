from typing import List

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_session
from app.api.dependencies import get_fetch_manager
from app.models.fetch_task import FetchRequest, FetchResponse, TaskRead
from app.services.fetch_service import FetchTaskService


router = APIRouter(prefix="/fetch", tags=["fetch"])


def get_fetch_service(
    session=Depends(get_session),
    fetch_manager=Depends(get_fetch_manager),
) -> FetchTaskService:
    return FetchTaskService(session, fetch_manager)


@router.post("", response_model=FetchResponse, status_code=status.HTTP_201_CREATED)
def fetch_questions(
    payload: FetchRequest,
    service: FetchTaskService = Depends(get_fetch_service),
) -> FetchResponse:
    task = service.create_fetch_task(payload.urls)
    results = service.run_fetch_task(task)
    task_read = TaskRead.model_validate(task)
    return FetchResponse(task=task_read, results=results)


@router.get("/results", response_model=List[dict])
def fetch_results(
    task_id: int,
    service: FetchTaskService = Depends(get_fetch_service),
) -> List[dict]:
    results = service.list_results(task_id)
    return [item.model_dump() for item in results]
