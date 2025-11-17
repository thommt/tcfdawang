from typing import List

from fastapi import APIRouter, Depends

from app.api.dependencies import get_session
from app.models.paragraph import ParagraphRead
from app.services.paragraph_service import ParagraphService


def get_paragraph_service(db=Depends(get_session)) -> ParagraphService:
    return ParagraphService(db)


router = APIRouter(prefix="/answers", tags=["paragraphs"])


@router.get("/{answer_id}/paragraphs", response_model=List[ParagraphRead])
def list_paragraphs(answer_id: int, service: ParagraphService = Depends(get_paragraph_service)) -> List[ParagraphRead]:
    return service.list_by_answer(answer_id)


__all__ = ["router"]
