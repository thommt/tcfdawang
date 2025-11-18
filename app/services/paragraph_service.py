from __future__ import annotations

from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import (
    Paragraph as ParagraphSchema,
    Sentence as SentenceSchema,
    Answer as AnswerSchema,
    Lexeme as LexemeSchema,
    SentenceChunk as SentenceChunkSchema,
    ChunkLexeme as ChunkLexemeSchema,
)
from app.models.paragraph import ParagraphRead, SentenceRead
from app.models.lexeme import SentenceChunkRead, ChunkLexemeRead, LexemeRead


class ParagraphService:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    def list_by_answer(self, answer_id: int) -> List[ParagraphRead]:
        answer = self.session.get(AnswerSchema, answer_id)
        if not answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        statement = (
            select(ParagraphSchema)
            .where(ParagraphSchema.answer_id == answer_id)
            .order_by(ParagraphSchema.order_index)
        )
        paragraphs = self.session.exec(statement).all()
        return [self._to_paragraph_read(paragraph) for paragraph in paragraphs]

    def _to_paragraph_read(self, paragraph: ParagraphSchema) -> ParagraphRead:
        sentences = (
            self.session.exec(
                select(SentenceSchema)
                .where(SentenceSchema.paragraph_id == paragraph.id)
                .order_by(SentenceSchema.order_index)
            ).all()
        )
        sentence_ids = [sentence.id for sentence in sentences]
        chunk_map: dict[int, list[SentenceChunkRead]] = {sid: [] for sid in sentence_ids if sid is not None}
        chunk_id_map: dict[int, SentenceChunkRead] = {}
        if sentence_ids:
            chunk_rows = self.session.exec(
                select(SentenceChunkSchema)
                .where(SentenceChunkSchema.sentence_id.in_(sentence_ids))
                .order_by(SentenceChunkSchema.order_index)
            ).all()
            for chunk in chunk_rows:
                chunk_data = chunk.model_dump()
                chunk_data["lexemes"] = []
                chunk_read = SentenceChunkRead(**chunk_data)
                chunk_map.setdefault(chunk.sentence_id, []).append(chunk_read)
                chunk_id_map[chunk.id] = chunk_read
            chunk_ids = [chunk.id for chunk in chunk_rows]
            if chunk_ids:
                lexeme_rows = self.session.exec(
                    select(ChunkLexemeSchema, LexemeSchema)
                    .join(LexemeSchema, LexemeSchema.id == ChunkLexemeSchema.lexeme_id)
                    .where(ChunkLexemeSchema.chunk_id.in_(chunk_ids))
                    .order_by(ChunkLexemeSchema.order_index)
                ).all()
                for association, lexeme in lexeme_rows:
                    chunk_read = chunk_id_map.get(association.chunk_id)
                    if not chunk_read:
                        continue
                    lexeme_read = LexemeRead.model_validate(lexeme)
                    assoc_data = association.model_dump()
                    assoc_data["lexeme"] = lexeme_read
                    chunk_lexeme = ChunkLexemeRead(**assoc_data)
                    chunk_read.lexemes.append(chunk_lexeme)
        sentence_reads = []
        for sentence in sentences:
            sentence_data = sentence.model_dump()
            sentence_data["chunks"] = chunk_map.get(sentence.id, [])
            sentence_reads.append(SentenceRead.model_validate(sentence_data))
        data = paragraph.model_dump()
        data["sentences"] = sentence_reads
        return ParagraphRead.model_validate(data)
