from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

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


def test_create_and_list_flashcards(client: TestClient) -> None:
    create_resp = client.post(
        "/flashcards",
        json={"entity_type": "sentence", "entity_id": 1},
    )
    assert create_resp.status_code == 201
    card = create_resp.json()
    assert card["entity_type"] == "sentence"
    assert card["entity_id"] == 1

    list_resp = client.get("/flashcards?entity_type=sentence")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1


def test_record_review(client: TestClient) -> None:
    create_resp = client.post(
        "/flashcards",
        json={"entity_type": "sentence", "entity_id": 2},
    )
    card_id = create_resp.json()["id"]
    review_resp = client.post(f"/flashcards/{card_id}/review", params={"score": 4})
    assert review_resp.status_code == 200
    card = review_resp.json()
    assert card["streak"] == 1
