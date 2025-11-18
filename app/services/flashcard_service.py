from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session as DBSession, select

from app.db.schemas import FlashcardProgress
from app.models.flashcard import FlashcardProgressRead, FlashcardProgressCreate, FlashcardProgressUpdate


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

    def list_due(self, *, entity_type: Optional[str] = None, limit: int = 50) -> List[FlashcardProgressRead]:
        now = datetime.now(timezone.utc)
        statement = select(FlashcardProgress).where(FlashcardProgress.due_at <= now).order_by(FlashcardProgress.due_at)
        if entity_type:
            statement = statement.where(FlashcardProgress.entity_type == entity_type)
        if limit:
            statement = statement.limit(limit)
        rows = self.session.exec(statement).all()
        return [FlashcardProgressRead.model_validate(row) for row in rows]

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
