from typing import List

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_session
from app.models.question import QuestionCreate, QuestionRead, QuestionUpdate
from app.services.question_service import QuestionService


router = APIRouter(prefix="/questions", tags=["questions"])


def get_question_service(session=Depends(get_session)) -> QuestionService:
    return QuestionService(session)


@router.get("", response_model=List[QuestionRead])
def list_questions(service: QuestionService = Depends(get_question_service)) -> List[QuestionRead]:
    return service.list_questions()


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate, service: QuestionService = Depends(get_question_service)
) -> QuestionRead:
    return service.create_question(payload)


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(
    question_id: int, service: QuestionService = Depends(get_question_service)
) -> QuestionRead:
    return service.get_question(question_id)


@router.put("/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    service: QuestionService = Depends(get_question_service),
) -> QuestionRead:
    return service.update_question(question_id, payload)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int, service: QuestionService = Depends(get_question_service)
) -> None:
    service.delete_question(question_id)
