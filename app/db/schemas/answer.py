from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class AnswerGroup(SQLModel, table=True):
    __tablename__ = "answer_groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="questions.id", index=True)
    slug: Optional[str] = Field(default=None, index=True)
    title: str
    descriptor: Optional[str] = None
    dialogue_profile: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Answer(SQLModel, table=True):
    __tablename__ = "answers"

    id: Optional[int] = Field(default=None, primary_key=True)
    answer_group_id: int = Field(foreign_key="answer_groups.id", index=True)
    version_index: int = Field(default=1)
    status: str = Field(default="draft", index=True)
    title: str
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="questions.id", index=True)
    answer_id: Optional[int] = Field(default=None, foreign_key="answers.id")
    session_type: str = Field(default="first", index=True)
    status: str = Field(default="draft", index=True)
    user_answer_draft: Optional[str] = None
    progress_state: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
