from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class Lexeme(SQLModel, table=True):
    __tablename__ = "lexemes"
    __table_args__ = (UniqueConstraint("hash", name="ux_lexemes_hash"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    headword: str = Field(index=True)
    sense_label: Optional[str] = Field(default=None)
    gloss: Optional[str] = Field(default=None)
    translation_en: Optional[str] = Field(default=None)
    translation_zh: Optional[str] = Field(default=None)
    pos_tags: Optional[str] = Field(default=None)
    difficulty: Optional[str] = Field(default=None)
    hash: str = Field(index=True)
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SentenceChunk(SQLModel, table=True):
    __tablename__ = "sentence_chunks"
    __table_args__ = (UniqueConstraint("sentence_id", "order_index", name="ux_sentence_chunk_order"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    sentence_id: int = Field(foreign_key="sentences.id", index=True)
    order_index: int = Field(default=1)
    text: str
    translation_en: Optional[str] = Field(default=None)
    translation_zh: Optional[str] = Field(default=None)
    chunk_type: Optional[str] = Field(default=None)
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChunkLexeme(SQLModel, table=True):
    __tablename__ = "chunk_lexemes"
    __table_args__ = (UniqueConstraint("chunk_id", "lexeme_id", "order_index", name="ux_chunk_lexeme_unique"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    chunk_id: int = Field(foreign_key="sentence_chunks.id", index=True)
    lexeme_id: int = Field(foreign_key="lexemes.id", index=True)
    order_index: int = Field(default=1)
    role: Optional[str] = Field(default=None)
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
