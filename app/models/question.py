from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class QuestionBase(BaseModel):
    type: str = Field(pattern=r"^T[23]$")
    source: str
    year: int
    month: int
    suite: Optional[str] = None
    number: Optional[str] = None
    title: str
    body: str


class QuestionCreate(QuestionBase):
    tags: List[str] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionRead(QuestionBase):
    id: int
    slug: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
