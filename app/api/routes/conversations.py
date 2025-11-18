from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.dependencies import get_session
from app.db.schemas import LLMConversation
from app.models.answer import LLMConversationRead


router = APIRouter(prefix="/llm-conversations", tags=["llm_conversations"])


@router.get("", response_model=List[LLMConversationRead])
def list_conversations(
    limit: int = 50,
    session_id: Optional[int] = None,
    task_id: Optional[int] = None,
    db: Session = Depends(get_session),
) -> List[LLMConversationRead]:
    statement = select(LLMConversation).order_by(LLMConversation.created_at.desc())
    if session_id is not None:
        statement = statement.where(LLMConversation.session_id == session_id)
    if task_id is not None:
        statement = statement.where(LLMConversation.task_id == task_id)
    if limit:
        statement = statement.limit(limit)
    rows = db.exec(statement).all()
    return [LLMConversationRead.model_validate(row) for row in rows]


__all__ = ["router"]
