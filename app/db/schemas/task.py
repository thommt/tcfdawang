from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    result_summary: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FetchResult(SQLModel, table=True):
    __tablename__ = "fetch_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    data: dict = Field(sa_column=Column(JSON, nullable=False))
