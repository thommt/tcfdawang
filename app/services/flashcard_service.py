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

    def list_due(
        self,
        *,
        entity_type: Optional[str] = None,
        mode: str = "manual",
        limit: int = 50,
        answer_id: Optional[int] = None,
    ) -> List[FlashcardStudyCardRead]:
        answer_filter = self._build_answer_entity_filter(answer_id) if answer_id else None
        if mode == "guided":
            return self._list_guided(limit=limit, answer_filter=answer_filter)
        now = datetime.now(timezone.utc)
        statement = select(FlashcardProgress).where(FlashcardProgress.due_at <= now).order_by(FlashcardProgress.due_at)
        if entity_type:
            statement = statement.where(FlashcardProgress.entity_type == entity_type)
        if limit:
            statement = statement.limit(limit)
        rows = self.session.exec(statement).all()
        cards: List[FlashcardStudyCardRead] = []
        for row in rows:
            if answer_filter and not self._entity_in_filter(row, answer_filter):
                continue
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

    def _list_guided(self, *, limit: int, answer_filter: Optional[dict[str, set[int]]] = None) -> List[FlashcardStudyCardRead]:
        now = datetime.now(timezone.utc)
        statement = select(FlashcardProgress).where(FlashcardProgress.due_at <= now).order_by(FlashcardProgress.due_at)
        rows = self.session.exec(statement).all()
        if not rows:
            return []
        chunk_map: dict[int, list[FlashcardStudyCardRead]] = {}
        sentence_cards: dict[int, FlashcardStudyCardRead] = {}
        lexeme_cards: list[FlashcardStudyCardRead] = []
        sentence_due_map: dict[int, datetime] = {}
        for row in rows:
            if answer_filter and not self._entity_in_filter(row, answer_filter):
                continue
            card = self._build_study_card(row)
            if row.entity_type == "chunk" and card.chunk:
                chunk_map.setdefault(card.chunk.sentence_id, []).append(card)
                current_due = sentence_due_map.get(card.chunk.sentence_id)
                if current_due is None or card.card.due_at < current_due:
                    sentence_due_map[card.chunk.sentence_id] = card.card.due_at
            elif row.entity_type == "sentence" and card.sentence:
                sentence_cards[card.sentence.id] = card
                current_due = sentence_due_map.get(card.sentence.id)
                if current_due is None or card.card.due_at < current_due:
                    sentence_due_map[card.sentence.id] = card.card.due_at
            elif row.entity_type == "lexeme":
                lexeme_cards.append(card)
        priorities = sorted(sentence_due_map.items(), key=lambda item: item[1])
        results: list[FlashcardStudyCardRead] = []
        for sentence_id, _ in priorities:
            chunk_cards = chunk_map.get(sentence_id, [])
            if chunk_cards:
                chunk_cards.sort(key=lambda item: (item.card.due_at, item.chunk.order_index if item.chunk else 0))
                results.extend(chunk_cards)
                if len(results) >= limit:
                    break
                continue
            sentence_card = sentence_cards.get(sentence_id)
            if sentence_card:
                results.append(sentence_card)
            if len(results) >= limit:
                break
        if not results and lexeme_cards:
            # 当没有句子/Chunk due 时，退化为返回 lexeme 以免界面空白
            return lexeme_cards[:limit]
        return results[:limit]

    def _entity_in_filter(self, entity: FlashcardProgress, answer_filter: dict[str, set[int]]) -> bool:
        if entity.entity_type == "sentence":
            return entity.entity_id in answer_filter["sentence"]
        if entity.entity_type == "chunk":
            return entity.entity_id in answer_filter["chunk"]
        if entity.entity_type == "lexeme":
            return entity.entity_id in answer_filter["lexeme"]
        return False

    def _build_answer_entity_filter(self, answer_id: int) -> dict[str, set[int]]:
        sentence_rows = self.session.exec(
            select(Sentence.id)
            .join(Paragraph, Paragraph.id == Sentence.paragraph_id)
            .where(Paragraph.answer_id == answer_id)
        ).all()
        sentence_ids = {row if isinstance(row, int) else row[0] for row in sentence_rows}
        chunk_ids = set()
        sentence_id_list = list(sentence_ids)
        if sentence_id_list:
            chunk_rows = self.session.exec(
                select(SentenceChunk.id).where(SentenceChunk.sentence_id.in_(sentence_id_list))
            ).all()
            chunk_ids = {row if isinstance(row, int) else row[0] for row in chunk_rows}
        lexeme_ids = set()
        chunk_id_list = list(chunk_ids)
        if chunk_id_list:
            lexeme_rows = self.session.exec(
                select(ChunkLexeme.lexeme_id).where(ChunkLexeme.chunk_id.in_(chunk_id_list))
            ).all()
            lexeme_ids = {
                (row if isinstance(row, int) else row[0])
                for row in lexeme_rows
                if (row if isinstance(row, int) else row[0]) is not None
            }
        return {
            "sentence": sentence_ids,
            "chunk": chunk_ids,
            "lexeme": lexeme_ids,
        }
