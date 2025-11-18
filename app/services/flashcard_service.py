from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import FlashcardProgress, Sentence, Paragraph, Lexeme, SentenceChunk, ChunkLexeme
from app.models.flashcard import (
    FlashcardProgressRead,
    FlashcardProgressCreate,
    FlashcardProgressUpdate,
    FlashcardStudyCardRead,
    SentenceCardInfo,
    LexemeCardInfo,
    ChunkCardInfo,
)


class FlashcardService:
    def __init__(self, session: DBSession) -> None:
        self.session = session

    def get_or_create(self, data: FlashcardProgressCreate) -> FlashcardProgressRead:
        card = self._get_by_entity(data.entity_type, data.entity_id)
        if card:
            return FlashcardProgressRead.model_validate(card)
        due_at = data.due_at or datetime.now(timezone.utc)
        interval = data.interval_days or 1
        entity = FlashcardProgress(
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            last_score=data.last_score,
            due_at=due_at,
            streak=data.streak or 0,
            interval_days=interval,
            extra={},
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return FlashcardProgressRead.model_validate(entity)

    def list_due(self, *, entity_type: Optional[str] = None, limit: int = 50) -> List[FlashcardStudyCardRead]:
        now = datetime.now(timezone.utc)
        statement = select(FlashcardProgress).where(FlashcardProgress.due_at <= now).order_by(FlashcardProgress.due_at)
        if entity_type:
            statement = statement.where(FlashcardProgress.entity_type == entity_type)
        if limit:
            statement = statement.limit(limit)
        rows = self.session.exec(statement).all()
        cards: List[FlashcardStudyCardRead] = []
        for row in rows:
            study_card = self._build_study_card(row)
            cards.append(study_card)
        return cards

    def update(self, card_id: int, data: FlashcardProgressUpdate) -> FlashcardProgressRead:
        card = self.session.get(FlashcardProgress, card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(card, key, value)
        card.updated_at = datetime.now(timezone.utc)
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return FlashcardProgressRead.model_validate(card)

    def record_review(self, card_id: int, score: int) -> FlashcardProgressRead:
        card = self.session.get(FlashcardProgress, card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")
        card.last_score = score
        if score >= 3:
            card.streak += 1
            card.interval_days = min(card.interval_days * 2, 60)
        else:
            card.streak = 0
            card.interval_days = 1
        card.due_at = datetime.now(timezone.utc) + timedelta(days=card.interval_days)
        card.updated_at = datetime.now(timezone.utc)
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return FlashcardProgressRead.model_validate(card)

    def _get_by_entity(self, entity_type: str, entity_id: int) -> Optional[FlashcardProgress]:
        statement = (
            select(FlashcardProgress)
            .where(FlashcardProgress.entity_type == entity_type)
            .where(FlashcardProgress.entity_id == entity_id)
        )
        return self.session.exec(statement).first()

    def _build_study_card(self, entity: FlashcardProgress) -> FlashcardStudyCardRead:
        sentence_info: Optional[SentenceCardInfo] = None
        lexeme_info: Optional[LexemeCardInfo] = None
        chunk_info: Optional[ChunkCardInfo] = None
        if entity.entity_type == "sentence":
            sentence = self.session.get(Sentence, entity.entity_id)
            if sentence:
                paragraph = self.session.get(Paragraph, sentence.paragraph_id)
                sentence_info = SentenceCardInfo(
                    id=sentence.id,
                    paragraph_id=sentence.paragraph_id,
                    answer_id=paragraph.answer_id if paragraph else None,
                    text=sentence.text,
                    translation_en=sentence.translation_en,
                    translation_zh=sentence.translation_zh,
                    difficulty=sentence.difficulty,
                )
        elif entity.entity_type == "chunk":
            chunk = self.session.get(SentenceChunk, entity.entity_id)
            if chunk:
                sentence = self.session.get(Sentence, chunk.sentence_id)
                paragraph = self.session.get(Paragraph, sentence.paragraph_id) if sentence else None
                sentence_context = None
                if sentence:
                    sentence_context = SentenceCardInfo(
                        id=sentence.id,
                        paragraph_id=sentence.paragraph_id,
                        answer_id=paragraph.answer_id if paragraph else None,
                        text=sentence.text,
                        translation_en=sentence.translation_en,
                        translation_zh=sentence.translation_zh,
                        difficulty=sentence.difficulty,
                    )
                chunk_info = ChunkCardInfo(
                    id=chunk.id,
                    sentence_id=chunk.sentence_id,
                    order_index=chunk.order_index,
                    text=chunk.text,
                    translation_en=chunk.translation_en,
                    translation_zh=chunk.translation_zh,
                    chunk_type=chunk.chunk_type,
                    sentence=sentence_context,
                )
        elif entity.entity_type == "lexeme":
            lexeme = self.session.get(Lexeme, entity.entity_id)
            if lexeme:
                sample = self.session.exec(
                    select(ChunkLexeme, SentenceChunk, Sentence)
                    .join(SentenceChunk, SentenceChunk.id == ChunkLexeme.chunk_id)
                    .join(Sentence, Sentence.id == SentenceChunk.sentence_id)
                    .where(ChunkLexeme.lexeme_id == lexeme.id)
                    .order_by(ChunkLexeme.id)
                ).first()
                sample_chunk = sample[1].text if sample else None
                sample_sentence = sample[2].text if sample else None
                sample_translation = sample[2].translation_zh if sample else None
                lexeme_info = LexemeCardInfo(
                    id=lexeme.id,
                    headword=lexeme.headword,
                    sense_label=lexeme.sense_label,
                    gloss=lexeme.gloss,
                    translation_en=lexeme.translation_en,
                    translation_zh=lexeme.translation_zh,
                    sample_chunk=sample_chunk,
                    sample_sentence=sample_sentence,
                    sample_sentence_translation=sample_translation,
                )
        return FlashcardStudyCardRead(
            card=FlashcardProgressRead.model_validate(entity),
            sentence=sentence_info,
            lexeme=lexeme_info,
            chunk=chunk_info,
        )
