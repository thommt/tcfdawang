from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, Field, ConfigDict

from app.models.fetch_task import TaskRead


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
    answers: List['AnswerRead'] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)


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


class SessionFinalizePayload(BaseModel):
    answer_group_id: Optional[int] = None
    group_title: Optional[str] = None
    group_descriptor: Optional[str] = None
    dialogue_profile: Optional[dict] = None
    answer_title: str
    answer_text: str


class LLMConversationRead(BaseModel):
    id: int
    session_id: Optional[int] = None
    task_id: Optional[int] = None
    purpose: str
    messages: dict
    result: dict
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerHistoryRead(BaseModel):
    answer: AnswerRead
    group: AnswerGroupRead
    sessions: List[SessionRead] = Field(default_factory=list)
    tasks: List[TaskRead] = Field(default_factory=list)
    conversations: List[LLMConversationRead] = Field(default_factory=list)
    review_notes_history: List[dict] = Field(default_factory=list)


class SessionHistoryRead(BaseModel):
    session: SessionRead
    tasks: List[TaskRead] = Field(default_factory=list)
    conversations: List[LLMConversationRead] = Field(default_factory=list)
