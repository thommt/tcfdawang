from typing import List

from fastapi import APIRouter, Depends

from app.api.dependencies import get_session, get_llm_client
from app.models.paragraph import ParagraphRead
from app.models.fetch_task import TaskRead
from app.services.paragraph_service import ParagraphService
from app.services.task_service import TaskService


def get_paragraph_service(db=Depends(get_session)) -> ParagraphService:
    return ParagraphService(db)

def get_task_service(
    db=Depends(get_session), llm_client=Depends(get_llm_client)
) -> TaskService:
    return TaskService(db, llm_client)

router = APIRouter(prefix="/answers", tags=["paragraphs"])


@router.get("/{answer_id}/paragraphs", response_model=List[ParagraphRead])
def list_paragraphs(answer_id: int, service: ParagraphService = Depends(get_paragraph_service)) -> List[ParagraphRead]:
    return service.list_by_answer(answer_id)


@router.post("/{answer_id}/tasks/structure", response_model=TaskRead, status_code=201)
def run_structure_task(
    answer_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_structure_task_for_answer(answer_id)


@router.post("/{answer_id}/tasks/translate-sentences", response_model=TaskRead, status_code=201)
def run_sentence_translation_task(
    answer_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_sentence_translation_for_answer(answer_id)


__all__ = ["router"]
