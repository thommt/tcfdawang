from fastapi import APIRouter, Depends

from app.api.dependencies import get_session, get_llm_client
from app.models.fetch_task import TaskRead
from app.services.task_service import TaskService


def get_task_service(db=Depends(get_session), llm_client=Depends(get_llm_client)) -> TaskService:
    return TaskService(db, llm_client)


router = APIRouter(prefix="/sentences", tags=["sentences"])


@router.post("/{sentence_id}/tasks/split-phrases", response_model=TaskRead, status_code=201)
def run_split_phrase_task(sentence_id: int, service: TaskService = Depends(get_task_service)) -> TaskRead:
    return service.run_sentence_split_task(sentence_id)


__all__ = ["router"]
