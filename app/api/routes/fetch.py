from typing import List

from fastapi import APIRouter, Depends, status, HTTPException

from app.api.dependencies import get_session, get_fetch_manager
from app.models.fetch_task import FetchRequest, FetchResponse, TaskRead, FetchImportRequest
from app.models.question import QuestionRead

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
    try:
        results = service.run_fetch_task(task)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    task_read = TaskRead.model_validate(task)
    return FetchResponse(task=task_read, results=results)


@router.get("/results", response_model=List[dict])
def fetch_results(
    task_id: int,
    service: FetchTaskService = Depends(get_fetch_service),
) -> List[dict]:
    results = service.list_results(task_id)
    return [item.model_dump() for item in results]


@router.post("/import", response_model=List[QuestionRead], status_code=status.HTTP_201_CREATED)
def import_fetch_results(
    payload: FetchImportRequest,
    service: FetchTaskService = Depends(get_fetch_service),
) -> List[QuestionRead]:
    try:
        return service.import_results(payload.task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
