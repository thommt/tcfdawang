from typing import List

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_session
from app.models.answer import (
    AnswerCreate,
    AnswerRead,
    AnswerGroupCreate,
    AnswerGroupRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
)
from app.services.session_service import SessionService


def get_session_service(db=Depends(get_session)) -> SessionService:
    return SessionService(db)


sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])


@sessions_router.get("", response_model=List[SessionRead])
def list_sessions(service: SessionService = Depends(get_session_service)) -> List[SessionRead]:
    return service.list_sessions()


@sessions_router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, service: SessionService = Depends(get_session_service)) -> SessionRead:
    return service.create_session(payload)


@sessions_router.get("/{session_id}", response_model=SessionRead)
def get_session(session_id: int, service: SessionService = Depends(get_session_service)) -> SessionRead:
    return service.get_session(session_id)


@sessions_router.put("/{session_id}", response_model=SessionRead)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    return service.update_session(session_id, payload)


answer_group_router = APIRouter(prefix="/answer-groups", tags=["answer-groups"])


@answer_group_router.post("", response_model=AnswerGroupRead, status_code=status.HTTP_201_CREATED)
def create_answer_group(
    payload: AnswerGroupCreate,
    service: SessionService = Depends(get_session_service),
) -> AnswerGroupRead:
    return service.create_answer_group(payload)


@answer_group_router.get("/{group_id}", response_model=AnswerGroupRead)
def get_answer_group(group_id: int, service: SessionService = Depends(get_session_service)) -> AnswerGroupRead:
    return service.get_answer_group(group_id)


answers_router = APIRouter(prefix="/answers", tags=["answers"])


@answers_router.post("", response_model=AnswerRead, status_code=status.HTTP_201_CREATED)
def create_answer(payload: AnswerCreate, service: SessionService = Depends(get_session_service)) -> AnswerRead:
    return service.create_answer(payload)


@answers_router.get("/{answer_id}", response_model=AnswerRead)
def get_answer(answer_id: int, service: SessionService = Depends(get_session_service)) -> AnswerRead:
    return service.get_answer(answer_id)


__all__ = ["sessions_router", "answer_group_router", "answers_router"]
