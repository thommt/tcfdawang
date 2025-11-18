from __future__ import annotations

from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import (
    Paragraph as ParagraphSchema,
    Sentence as SentenceSchema,
    Answer as AnswerSchema,
    Lexeme as LexemeSchema,
    SentenceLexeme as SentenceLexemeSchema,
)
from app.models.paragraph import ParagraphRead, SentenceRead
from app.models.lexeme import SentenceLexemeRead, LexemeRead


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
        lexeme_map: dict[int, list[SentenceLexemeRead]] = {sid: [] for sid in sentence_ids if sid is not None}
        if sentence_ids:
            rows = self.session.exec(
                select(SentenceLexemeSchema, LexemeSchema)
                .join(LexemeSchema, LexemeSchema.id == SentenceLexemeSchema.lexeme_id)
                .where(SentenceLexemeSchema.sentence_id.in_(sentence_ids))
                .order_by(SentenceLexemeSchema.order_index)
            ).all()
            for association, lexeme in rows:
                lexeme_read = LexemeRead.model_validate(lexeme)
                assoc_data = association.model_dump()
                assoc_data["lexeme"] = lexeme_read
                lexeme_read_entry = SentenceLexemeRead(**assoc_data)
                lexeme_map.setdefault(association.sentence_id, []).append(lexeme_read_entry)
        sentence_reads = []
        for sentence in sentences:
            sentence_data = sentence.model_dump()
            sentence_data["lexemes"] = lexeme_map.get(sentence.id, [])
            sentence_reads.append(SentenceRead.model_validate(sentence_data))
        data = paragraph.model_dump()
        data["sentences"] = sentence_reads
        return ParagraphRead.model_validate(data)
