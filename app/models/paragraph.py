from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.models.lexeme import SentenceChunkRead


class SentenceRead(BaseModel):
    id: int
    paragraph_id: int
    order_index: int
    text: str
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    difficulty: Optional[str] = None
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    chunks: List[SentenceChunkRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ParagraphRead(BaseModel):
    id: int
    answer_id: int
    order_index: int
    role_label: Optional[str] = None
    summary: Optional[str] = None
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    sentences: List[SentenceRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
