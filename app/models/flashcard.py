from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class FlashcardProgressRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    last_score: Optional[int] = None
    due_at: datetime
    streak: int
    interval_days: int
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlashcardProgressUpdate(BaseModel):
    last_score: Optional[int] = None
    due_at: Optional[datetime] = None
    streak: Optional[int] = None
    interval_days: Optional[int] = None


class FlashcardProgressCreate(BaseModel):
    entity_type: str
    entity_id: int
    last_score: Optional[int] = None
    due_at: Optional[datetime] = None
    streak: Optional[int] = None
    interval_days: Optional[int] = None


class SentenceCardInfo(BaseModel):
    id: int
    paragraph_id: int
    answer_id: Optional[int] = None
    text: str
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    difficulty: Optional[str] = None


class LexemeCardInfo(BaseModel):
    id: int
    lemma: str
    sense_label: Optional[str] = None
    gloss: Optional[str] = None
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    sample_sentence: Optional[str] = None
    sample_sentence_translation: Optional[str] = None


class FlashcardStudyCardRead(BaseModel):
    card: FlashcardProgressRead
    sentence: Optional[SentenceCardInfo] = None
    lexeme: Optional[LexemeCardInfo] = None
