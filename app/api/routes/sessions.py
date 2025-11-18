from typing import List

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_session, get_llm_client
from app.models.answer import (
    AnswerCreate,
    AnswerRead,
    AnswerGroupCreate,
    AnswerGroupRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
    SessionFinalizePayload,
    AnswerHistoryRead,
    SessionHistoryRead,
)
from app.models.fetch_task import TaskRead
from app.services.session_service import SessionService
from app.services.task_service import TaskService


def get_session_service(db=Depends(get_session)) -> SessionService:
    return SessionService(db)


def get_task_service(
    db=Depends(get_session), llm_client=Depends(get_llm_client)
) -> TaskService:
    return TaskService(db, llm_client)


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


@sessions_router.post("/{session_id}/tasks/eval", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def run_eval_task(
    session_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_eval_task(session_id)


@sessions_router.post("/{session_id}/tasks/compose", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def run_compose_task(
    session_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_compose_task(session_id)


@sessions_router.post("/{session_id}/tasks/compare", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def run_compare_task(
    session_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_answer_compare_task(session_id)


@sessions_router.post("/{session_id}/finalize", response_model=SessionRead)
def finalize_session(
    session_id: int,
    payload: SessionFinalizePayload,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    return service.finalize_session(session_id, payload)


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


@answer_group_router.get("/by-question/{question_id}", response_model=List[AnswerGroupRead])
def list_answer_groups(question_id: int, service: SessionService = Depends(get_session_service)) -> List[AnswerGroupRead]:
    return service.list_answer_groups(question_id)


@answer_group_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_answer_group(group_id: int, service: SessionService = Depends(get_session_service)) -> None:
    service.delete_answer_group(group_id)


answers_router = APIRouter(prefix="/answers", tags=["answers"])


@answers_router.post("", response_model=AnswerRead, status_code=status.HTTP_201_CREATED)
def create_answer(payload: AnswerCreate, service: SessionService = Depends(get_session_service)) -> AnswerRead:
    return service.create_answer(payload)


@answers_router.get("/{answer_id}", response_model=AnswerRead)
def get_answer(answer_id: int, service: SessionService = Depends(get_session_service)) -> AnswerRead:
    return service.get_answer(answer_id)


@answers_router.get("/{answer_id}/history", response_model=AnswerHistoryRead)
def get_answer_history(answer_id: int, service: SessionService = Depends(get_session_service)) -> AnswerHistoryRead:
    return service.get_answer_history(answer_id)


@answers_router.post("/{answer_id}/sessions", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_review_session(answer_id: int, service: SessionService = Depends(get_session_service)) -> SessionRead:
    return service.create_review_session(answer_id)


@answers_router.delete("/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_answer(answer_id: int, service: SessionService = Depends(get_session_service)) -> None:
    service.delete_answer(answer_id)


@sessions_router.get("/{session_id}/history", response_model=SessionHistoryRead)
def get_session_history(
    session_id: int, service: SessionService = Depends(get_session_service)
) -> SessionHistoryRead:
    return service.get_session_history(session_id)


__all__ = ["sessions_router", "answer_group_router", "answers_router"]
