from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class LexemeRead(BaseModel):
    id: int
    headword: str
    sense_label: Optional[str] = None
    gloss: Optional[str] = None
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    pos_tags: Optional[str] = None
    difficulty: Optional[str] = None
    hash: str
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChunkLexemeRead(BaseModel):
    id: int
    chunk_id: int
    lexeme_id: int
    order_index: int
    role: Optional[str] = None
    lexeme: LexemeRead

    model_config = ConfigDict(from_attributes=True)


class SentenceChunkRead(BaseModel):
    id: int
    sentence_id: int
    order_index: int
    text: str
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    chunk_type: Optional[str] = None
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    lexemes: List[ChunkLexemeRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
