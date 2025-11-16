from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class LLMConversation(SQLModel, table=True):
    __tablename__ = "llm_conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[int] = Field(default=None, foreign_key="sessions.id", index=True)
    task_id: Optional[int] = Field(default=None, foreign_key="tasks.id", unique=True)
    purpose: str
    messages: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
