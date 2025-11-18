from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class FlashcardProgress(SQLModel, table=True):
    __tablename__ = "flashcard_progress"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="ux_flashcard_entity"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_id: int = Field(index=True)
    last_score: Optional[int] = Field(default=None)
    due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    streak: int = Field(default=0)
    interval_days: int = Field(default=1)
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
