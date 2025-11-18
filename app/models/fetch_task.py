from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, ConfigDict

from app.models.fetch import FetchedQuestion


class FetchRequest(BaseModel):
    urls: List[str] = Field(min_length=1)


class TaskRead(BaseModel):
    id: int
    type: str
    status: str
    session_id: int | None = None
    answer_id: int | None = None
    payload: dict
    result_summary: dict
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FetchResponse(BaseModel):
    task: TaskRead
    results: List[FetchedQuestion]


class FetchImportRequest(BaseModel):
    task_id: int
