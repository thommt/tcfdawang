from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Paragraph(SQLModel, table=True):
    __tablename__ = "paragraphs"

    id: Optional[int] = Field(default=None, primary_key=True)
    answer_id: int = Field(foreign_key="answers.id", index=True)
    order_index: int = Field(default=1)
    role_label: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    extra: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Sentence(SQLModel, table=True):
    __tablename__ = "sentences"

    id: Optional[int] = Field(default=None, primary_key=True)
    paragraph_id: int = Field(foreign_key="paragraphs.id", index=True)
    order_index: int = Field(default=1)
    text: str
    translation: Optional[str] = Field(default=None)
    extra: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
