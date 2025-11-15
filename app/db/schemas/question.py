from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Question(SQLModel, table=True):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint(
            "source", "year", "month", "suite", "number", name="uq_question_identity"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    source: str
    year: int
    month: int
    suite: Optional[str] = Field(default=None)
    number: Optional[str] = Field(default=None)
    title: str
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuestionTag(SQLModel, table=True):
    __tablename__ = "question_tags"
    __table_args__ = (
        UniqueConstraint("question_id", "tag", name="uq_question_tag"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="questions.id", index=True)
    tag: str = Field(max_length=255)
