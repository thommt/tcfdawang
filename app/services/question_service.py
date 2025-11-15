from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.schemas.question import Question, QuestionTag
from app.models.question import QuestionCreate, QuestionRead, QuestionUpdate


class QuestionService:
    def __init__(self, session: Session):
        self.session = session

    def list_questions(self) -> List[QuestionRead]:
        statement = select(Question)
        questions = self.session.exec(statement).all()
        return [self._to_read_model(question) for question in questions]

    def create_question(self, data: QuestionCreate) -> QuestionRead:
        question = Question(
            type=data.type,
            source=data.source,
            year=data.year,
            month=data.month,
            suite=data.suite,
            number=data.number,
            title=data.title,
            body=data.body,
        )
        self.session.add(question)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question with same source/year/month/suite/number already exists",
            ) from exc
        self.session.refresh(question)
        self._sync_tags(question.id, data.tags)
        return self._to_read_model(question)

    def get_question(self, question_id: int) -> QuestionRead:
        question = self._get_question_entity(question_id)
        return self._to_read_model(question)

    def update_question(self, question_id: int, data: QuestionUpdate) -> QuestionRead:
        question = self._get_question_entity(question_id)
        update_data = data.model_dump(exclude_unset=True, exclude={"tags"})
        for key, value in update_data.items():
            setattr(question, key, value)
        question.updated_at = datetime.now(timezone.utc)
        self.session.add(question)
        if data.tags is not None:
            self._sync_tags(question_id, data.tags)
        self.session.commit()
        self.session.refresh(question)
        return self._to_read_model(question)

    def delete_question(self, question_id: int) -> None:
        question = self._get_question_entity(question_id)
        self.session.delete(question)
        self.session.commit()

    def _get_question_entity(self, question_id: int) -> Question:
        question = self.session.get(Question, question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return question

    def _sync_tags(self, question_id: int, tags: List[str]) -> None:
        incoming = tags or []
        normalized: List[str] = []
        for tag in incoming:
            cleaned = tag.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        existing = self.session.exec(
            select(QuestionTag).where(QuestionTag.question_id == question_id)
        ).all()
        existing_tags = {tag.tag for tag in existing}
        # Remove tags not in new set
        for tag in existing:
            if tag.tag not in normalized:
                self.session.delete(tag)
        # Add new tags
        for tag in normalized:
            if tag not in existing_tags:
                self.session.add(QuestionTag(question_id=question_id, tag=tag))
        self.session.commit()

    def _get_tags(self, question_id: int) -> List[str]:
        statement = (
            select(QuestionTag.tag)
            .where(QuestionTag.question_id == question_id)
            .order_by(QuestionTag.id)
        )
        return list(self.session.exec(statement))

    def _to_read_model(self, question: Question) -> QuestionRead:
        tags = self._get_tags(question.id)
        data = question.model_dump()
        data["tags"] = tags
        return QuestionRead(**data)
