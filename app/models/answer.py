from datetime import datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, Field


class AnswerGroupBase(BaseModel):
    question_id: int
    slug: Optional[str] = None
    title: str
    descriptor: Optional[str] = None
    dialogue_profile: dict = Field(default_factory=dict)


class AnswerGroupCreate(AnswerGroupBase):
    pass


class AnswerGroupRead(AnswerGroupBase):
    id: int
    created_at: datetime


class AnswerBase(BaseModel):
    answer_group_id: int
    version_index: int = 1
    status: str = Field(default="draft")
    title: str
    text: str


class AnswerCreate(AnswerBase):
    pass


class AnswerRead(AnswerBase):
    id: int
    created_at: datetime


class AnswerUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    status: Optional[str] = None


class SessionBase(BaseModel):
    question_id: int
    answer_id: Optional[int] = None
    session_type: Literal["first", "review"] = "first"
    status: str = Field(default="draft")
    user_answer_draft: Optional[str] = None
    progress_state: dict = Field(default_factory=dict)


class SessionCreate(SessionBase):
    pass


class SessionRead(SessionBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class SessionUpdate(BaseModel):
    answer_id: Optional[int] = None
    status: Optional[str] = None
    user_answer_draft: Optional[str] = None
    progress_state: Optional[dict] = None
