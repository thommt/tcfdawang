from __future__ import annotations

from typing import List

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import Paragraph as ParagraphSchema, Sentence as SentenceSchema, Answer as AnswerSchema
from app.models.paragraph import ParagraphRead, SentenceRead


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
        data = paragraph.model_dump()
        data["sentences"] = [SentenceRead.model_validate(sentence) for sentence in sentences]
        return ParagraphRead.model_validate(data)
