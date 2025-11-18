from typing import List, Optional

from fastapi import APIRouter, Depends

from app.api.dependencies import get_session
from app.models.flashcard import FlashcardProgressRead, FlashcardProgressCreate, FlashcardProgressUpdate
from app.services.flashcard_service import FlashcardService


def get_flashcard_service(db=Depends(get_session)) -> FlashcardService:
    return FlashcardService(db)


router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("", response_model=List[FlashcardProgressRead])
def list_flashcards(
    entity_type: Optional[str] = None,
    due_only: bool = True,
    limit: int = 50,
    service: FlashcardService = Depends(get_flashcard_service),
) -> List[FlashcardProgressRead]:
    if due_only:
        return service.list_due(entity_type=entity_type, limit=limit)
    raise NotImplementedError("Listing all flashcards is not supported yet")


@router.post("", response_model=FlashcardProgressRead, status_code=201)
def create_flashcard(
    payload: FlashcardProgressCreate,
    service: FlashcardService = Depends(get_flashcard_service),
) -> FlashcardProgressRead:
    return service.get_or_create(payload)


@router.patch("/{card_id}", response_model=FlashcardProgressRead)
def update_flashcard(
    card_id: int,
    payload: FlashcardProgressUpdate,
    service: FlashcardService = Depends(get_flashcard_service),
) -> FlashcardProgressRead:
    return service.update(card_id, payload)


@router.post("/{card_id}/review", response_model=FlashcardProgressRead)
def record_review(
    card_id: int,
    score: int,
    service: FlashcardService = Depends(get_flashcard_service),
) -> FlashcardProgressRead:
    return service.record_review(card_id, score)


__all__ = ["router"]
