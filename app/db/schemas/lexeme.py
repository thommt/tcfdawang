from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class Lexeme(SQLModel, table=True):
    __tablename__ = "lexemes"
    __table_args__ = (UniqueConstraint("hash", name="ux_lexemes_hash"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    lemma: str = Field(index=True)
    sense_label: Optional[str] = Field(default=None)
    gloss: Optional[str] = Field(default=None)
    translation_en: Optional[str] = Field(default=None)
    translation_zh: Optional[str] = Field(default=None)
    pos_tags: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    complexity_level: Optional[str] = Field(default=None)
    hash: str = Field(index=True)
    is_manual: bool = Field(default=False)
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SentenceLexeme(SQLModel, table=True):
    __tablename__ = "sentence_lexemes"
    __table_args__ = (UniqueConstraint("sentence_id", "lexeme_id", "order_index", name="ux_sentence_lexeme_unique"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    sentence_id: int = Field(foreign_key="sentences.id", index=True)
    lexeme_id: int = Field(foreign_key="lexemes.id", index=True)
    order_index: int = Field(default=1)
    context_note: Optional[str] = Field(default=None)
    translation_override: Optional[str] = Field(default=None)
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
