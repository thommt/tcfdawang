from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session as DBSession

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
from app.db.base import get_engine


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


@sessions_router.post("/{session_id}/tasks/gap-highlight", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def run_gap_highlight_task(
    session_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_gap_highlight_task(session_id)


@sessions_router.post("/{session_id}/tasks/refine", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def run_refine_task(
    session_id: int, task_service: TaskService = Depends(get_task_service)
) -> TaskRead:
    return task_service.run_refine_answer_task(session_id)


@sessions_router.post("/{session_id}/finalize", response_model=SessionRead)
def finalize_session(
    session_id: int,
    payload: SessionFinalizePayload,
    service: SessionService = Depends(get_session_service),
    task_service: TaskService = Depends(get_task_service),
) -> SessionRead:
    result = service.finalize_session(session_id, payload)
    if result.answer_id:
        try:
            task_service.run_structure_pipeline_task(result.id, result.answer_id)
        except HTTPException:
            pass
    return result


@sessions_router.post("/{session_id}/live/start", response_model=SessionRead)
def start_live_session(
    session_id: int,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    return service.start_live_session(session_id)


@sessions_router.post("/{session_id}/live/finalize", response_model=SessionRead)
def finalize_live_session(
    session_id: int,
    force: bool = False,
    service: SessionService = Depends(get_session_service),
    task_service: TaskService = Depends(get_task_service),
) -> SessionRead:
    payload = service.prepare_live_finalize_payload(session_id, force=force)
    result = service.finalize_session(session_id, payload)
    service.update_live_status(session_id, "completed")
    if result.answer_id:
        try:
            task_service.run_structure_pipeline_task(result.id, result.answer_id)
        except HTTPException:
            pass
    return result


@sessions_router.websocket("/live/{session_id}/stream")
async def live_session_stream(websocket: WebSocket, session_id: int) -> None:
    await websocket.accept()
    try:
        llm_client = get_llm_client()
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "message": exc.detail})
        await websocket.close(code=4400)
        return
    engine = get_engine()
    with DBSession(engine) as db:
        service = SessionService(db)
        task_service = TaskService(db, llm_client)
        try:
            entity = service._get_session_entity(session_id)
            service._ensure_live_mode(entity, require_active=False)  # type: ignore[attr-defined]
        except HTTPException as exc:
            await websocket.send_json({"type": "error", "message": exc.detail})
            await websocket.close(code=4400)
            return
        try:
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")
                if msg_type == "candidate_turn":
                    text = (message.get("text") or "").strip()
                    followup = (message.get("followup") or "").strip() or None
                    if not text:
                        await websocket.send_json({"type": "error", "message": "请输入问题文本"})
                        continue
                    turn = service.create_live_turn(session_id, text, followup)
                    await websocket.send_json({"type": "ack", "turn": turn.turn_index})
                    try:
                        reply = await run_in_threadpool(task_service.generate_live_reply, session_id, turn.id)
                        result_text = reply.get("text", "")
                        meta = reply.get("meta")
                        service.record_live_reply(turn.id, result_text, meta)
                        await websocket.send_json(
                            {"type": "examiner_reply", "turn": turn.turn_index, "text": result_text}
                        )
                        if turn.turn_index >= 15:
                            await websocket.send_json(
                                {"type": "warning", "message": "已达到 15 轮，请收尾或结束本次练习。"}
                            )
                        elif turn.turn_index >= 12:
                            await websocket.send_json(
                                {"type": "notice", "message": "已经完成 12 轮，可以随时结束或继续。"}
                            )
                    except HTTPException as exc:
                        service.mark_live_turn_error(turn.id, exc.detail if isinstance(exc.detail, str) else str(exc))
                        await websocket.send_json({"type": "error", "message": exc.detail})
                        continue
                elif msg_type == "stop":
                    service.update_live_status(session_id, "stopped")
                    await websocket.send_json({"type": "stopped"})
                else:
                    await websocket.send_json({"type": "error", "message": "未知消息类型"})
        except WebSocketDisconnect:
            service.update_live_status(session_id, "stopped")
        except Exception as exc:  # pragma: no cover
            await websocket.send_json({"type": "error", "message": str(exc)})
            service.update_live_status(session_id, "stopped")
        finally:
            await websocket.close()


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
@sessions_router.post("/{session_id}/complete-learning", response_model=SessionRead)
def complete_learning(
    session_id: int,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    return service.mark_learning_complete(session_id)


@sessions_router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, service: SessionService = Depends(get_session_service)) -> None:
    service.delete_session(session_id)
