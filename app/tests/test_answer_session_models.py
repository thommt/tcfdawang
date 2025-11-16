from typing import Generator

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.db.schemas import Question, AnswerGroup, Answer, Session as SessionSchema


def create_in_memory_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_answer_group_and_session_models():
    engine = create_in_memory_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        question = Question(
            type="T3",
            source="mock",
            year=2024,
            month=10,
            suite="A",
            number="01",
            title="Sample",
            body="Body",
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        answer_group = AnswerGroup(question_id=question.id, title="Group", slug="S1")
        db.add(answer_group)
        db.commit()
        db.refresh(answer_group)

        answer = Answer(answer_group_id=answer_group.id, title="Answer", text="...", status="active")
        db.add(answer)
        db.commit()
        db.refresh(answer)

        session = SessionSchema(
            question_id=question.id,
            answer_id=answer.id,
            session_type="first",
            status="draft",
        )
        db.add(session)
        db.commit()

        stored_group = db.exec(select(AnswerGroup)).first()
        stored_answer = db.exec(select(Answer)).first()
        stored_session = db.exec(select(SessionSchema)).first()

        assert stored_group is not None
        assert stored_answer is not None
        assert stored_session is not None
        assert stored_group.question_id == question.id
        assert stored_answer.answer_group_id == stored_group.id
        assert stored_session.answer_id == stored_answer.id
