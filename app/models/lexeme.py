from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class LexemeRead(BaseModel):
    id: int
    lemma: str
    sense_label: Optional[str] = None
    gloss: Optional[str] = None
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    pos_tags: Optional[str] = None
    notes: Optional[str] = None
    complexity_level: Optional[str] = None
    hash: str
    is_manual: bool
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SentenceLexemeRead(BaseModel):
    id: int
    sentence_id: int
    lexeme_id: int
    order_index: int
    context_note: Optional[str] = None
    translation_override: Optional[str] = None
    lexeme: LexemeRead

    model_config = ConfigDict(from_attributes=True)
