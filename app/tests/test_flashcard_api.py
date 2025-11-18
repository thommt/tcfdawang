from typing import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.db.schemas import Question, AnswerGroup, Answer, Paragraph, Sentence, SentenceChunk, FlashcardProgress
from app.main import app
from app.api.dependencies import get_session
from app.services.flashcard_service import FlashcardService
from app.models.flashcard import FlashcardProgressCreate


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


def _seed_chunk(session: Session) -> SentenceChunk:
    sentence = _seed_sentence(session)
    chunk = SentenceChunk(
        sentence_id=sentence.id,
        order_index=1,
        text="Bonjour",
        translation_en="Hello",
        translation_zh="你好",
        chunk_type="expression",
        extra={},
    )
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    return chunk


def _answer_id_from_sentence(session: Session, sentence: Sentence) -> int:
    paragraph = session.get(Paragraph, sentence.paragraph_id)
    assert paragraph is not None
    return paragraph.answer_id


def _create_due_card(session: Session, entity_type: str, entity_id: int) -> int:
    service = FlashcardService(session)
    created = service.get_or_create(
        FlashcardProgressCreate(entity_type=entity_type, entity_id=entity_id)
    )
    record = session.get(FlashcardProgress, created.id)
    assert record is not None
    record.due_at = datetime.now(timezone.utc) - timedelta(days=1)
    session.add(record)
    session.commit()
    return record.id


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

    list_resp = client.get("/flashcards", params={"mode": "manual", "entity_type": "sentence"})
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


def test_chunk_flashcard_payload(client: TestClient, session: Session) -> None:
    chunk = _seed_chunk(session)
    create_resp = client.post(
        "/flashcards",
        json={"entity_type": "chunk", "entity_id": chunk.id},
    )
    assert create_resp.status_code == 201
    list_resp = client.get("/flashcards", params={"mode": "manual", "entity_type": "chunk"})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["card"]["entity_type"] == "chunk"
    chunk_payload = data[0]["chunk"]
    assert chunk_payload["text"] == "Bonjour"
    assert chunk_payload["sentence"]["text"] == "Bonjour tout le monde"


def test_guided_mode_prioritizes_chunks(client: TestClient, session: Session) -> None:
    sentence = _seed_sentence(session)
    chunk_a = SentenceChunk(
        sentence_id=sentence.id,
        order_index=1,
        text="Bonjour",
        translation_en="Hello",
        translation_zh="你好",
        chunk_type="expression",
        extra={},
    )
    chunk_b = SentenceChunk(
        sentence_id=sentence.id,
        order_index=2,
        text="tout le monde",
        translation_en="everyone",
        translation_zh="大家",
        chunk_type="expression",
        extra={},
    )
    session.add(chunk_a)
    session.add(chunk_b)
    session.commit()
    session.refresh(chunk_a)
    session.refresh(chunk_b)
    _create_due_card(session, "chunk", chunk_a.id)
    _create_due_card(session, "chunk", chunk_b.id)
    _create_due_card(session, "sentence", sentence.id)

    resp = client.get("/flashcards")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["card"]["entity_type"] == "chunk"
    assert data[0]["chunk"]["order_index"] == 1
    assert data[1]["chunk"]["order_index"] == 2


def test_guided_mode_returns_sentence_when_chunks_done(client: TestClient, session: Session) -> None:
    sentence = _seed_sentence(session)
    chunk = SentenceChunk(
        sentence_id=sentence.id,
        order_index=1,
        text="Bonjour",
        translation_en="Hello",
        translation_zh="你好",
        chunk_type="expression",
        extra={},
    )
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    chunk_card_id = _create_due_card(session, "chunk", chunk.id)
    # 模拟已完成 chunk 复习：将 due_at 调整到未来
    record = session.get(FlashcardProgress, chunk_card_id)
    record.due_at = datetime.now(timezone.utc) + timedelta(days=3)
    session.add(record)
    session.commit()
    _create_due_card(session, "sentence", sentence.id)

    resp = client.get("/flashcards")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["card"]["entity_type"] == "sentence"


def test_flashcards_can_filter_by_answer_in_manual_mode(client: TestClient, session: Session) -> None:
    sentence_a = _seed_sentence(session)
    sentence_b = _seed_sentence(session)
    for sentence in (sentence_a, sentence_b):
        client.post(
            "/flashcards",
            json={"entity_type": "sentence", "entity_id": sentence.id},
        )
    answer_a_id = _answer_id_from_sentence(session, sentence_a)
    resp = client.get(
        "/flashcards",
        params={"mode": "manual", "entity_type": "sentence", "answer_id": answer_a_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["card"]["entity_id"] == sentence_a.id


def test_flashcards_chunk_filter_by_answer(client: TestClient, session: Session) -> None:
    sentence = _seed_sentence(session)
    paragraph = session.get(Paragraph, sentence.paragraph_id)
    assert paragraph is not None
    answer_id = paragraph.answer_id
    chunk_a = SentenceChunk(
        sentence_id=sentence.id,
        order_index=1,
        text="Bonjour",
        translation_en="Hello",
        translation_zh="你好",
        chunk_type="expression",
        extra={},
    )
    session.add(chunk_a)
    session.commit()
    session.refresh(chunk_a)
    chunk_b = _seed_chunk(session)
    for chunk in (chunk_a, chunk_b):
        client.post(
            "/flashcards",
            json={"entity_type": "chunk", "entity_id": chunk.id},
        )
    resp = client.get(
        "/flashcards",
        params={"mode": "manual", "entity_type": "chunk", "answer_id": answer_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["chunk"]["id"] == chunk_a.id
