from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.db.schemas import Question, AnswerGroup, Answer, Paragraph, Sentence
from app.main import app
from app.api.dependencies import get_session


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _seed_sentence(session: Session) -> Sentence:
    question = Question(type="T2", source="spec", year=2024, month=1, title="Demo Q", body="Body")
    session.add(question)
    session.commit()
    session.refresh(question)
    group = AnswerGroup(question_id=question.id, title="Group Title")
    session.add(group)
    session.commit()
    session.refresh(group)
    answer = Answer(answer_group_id=group.id, title="Answer", text="Texte")
    session.add(answer)
    session.commit()
    session.refresh(answer)
    paragraph = Paragraph(answer_id=answer.id, order_index=1, role_label="body", summary="sum")
    session.add(paragraph)
    session.commit()
    session.refresh(paragraph)
    sentence = Sentence(
        paragraph_id=paragraph.id,
        order_index=1,
        text="Bonjour tout le monde",
        translation_en="Hello everyone",
        translation_zh="大家好",
        difficulty="B1",
    )
    session.add(sentence)
    session.commit()
    session.refresh(sentence)
    return sentence


def test_create_and_list_flashcards(client: TestClient, session: Session) -> None:
    sentence = _seed_sentence(session)
    create_resp = client.post(
        "/flashcards",
        json={"entity_type": "sentence", "entity_id": sentence.id},
    )
    assert create_resp.status_code == 201
    card = create_resp.json()
    assert card["entity_type"] == "sentence"
    assert card["entity_id"] == sentence.id

    list_resp = client.get("/flashcards?entity_type=sentence")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["card"]["entity_id"] == sentence.id
    assert data[0]["sentence"]["text"] == "Bonjour tout le monde"


def test_record_review(client: TestClient, session: Session) -> None:
    sentence = _seed_sentence(session)
    create_resp = client.post(
        "/flashcards",
        json={"entity_type": "sentence", "entity_id": sentence.id},
    )
    card_id = create_resp.json()["id"]
    review_resp = client.post(f"/flashcards/{card_id}/review", params={"score": 4})
    assert review_resp.status_code == 200
    card = review_resp.json()
    assert card["streak"] == 1
