from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class LiveTurn(SQLModel, table=True):
    __tablename__ = "live_turns"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", index=True)
    turn_index: int = Field(index=True)
    candidate_query: str = Field(default="")
    examiner_reply: Optional[str] = Field(default=None)
    candidate_followup: Optional[str] = Field(default=None)
    meta: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
