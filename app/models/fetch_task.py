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
    result_summary: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FetchResponse(BaseModel):
    task: TaskRead
    results: List[FetchedQuestion]
