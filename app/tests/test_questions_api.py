from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.api.dependencies import get_session, get_llm_client
from app.services.llm_service import GeneratedQuestionMetadata
from app.db.schemas import Question, QuestionTag  # noqa: F401


TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    engine = create_engine(
        TEST_DATABASE_URL,
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
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create_question(client: TestClient) -> None:
    payload = {
        "type": "T2",
        "source": "mock",
        "year": 2025,
        "month": 10,
        "suite": "A",
        "number": "01",
        "title": "Titre de test",
        "body": "Contenu de test",
        "tags": ["immigration", "ville"],
    }
    response = client.post("/questions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["tags"] == ["immigration", "ville"]


def test_list_questions(client: TestClient) -> None:
    payload = {
        "type": "T3",
        "source": "mock",
        "year": 2024,
        "month": 5,
        "suite": "B",
        "number": "02",
        "title": "Question 2",
        "body": "Texte",
        "tags": [],
    }
    client.post("/questions", json=payload)
    response = client.get("/questions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Question 2"


def test_update_question(client: TestClient) -> None:
    payload = {
        "type": "T3",
        "source": "mock",
        "year": 2024,
        "month": 5,
        "suite": "B",
        "number": "03",
        "title": "Original",
        "body": "Body",
        "tags": ["alpha"],
    }
    created = client.post("/questions", json=payload).json()
    question_id = created["id"]
    update_payload = {
        "title": "Updated",
        "tags": ["beta", "gamma"],
    }
    response = client.put(f"/questions/{question_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["tags"] == ["beta", "gamma"]


def test_delete_question(client: TestClient) -> None:
    payload = {
        "type": "T2",
        "source": "mock",
        "year": 2023,
        "month": 1,
        "suite": "C",
        "number": "04",
        "title": "Delete me",
        "body": "Body",
        "tags": [],
    }
    created = client.post("/questions", json=payload).json()
    response = client.delete(f"/questions/{created['id']}")
    assert response.status_code == 204
    list_resp = client.get("/questions")
    assert list_resp.status_code == 200
    assert list_resp.json() == []


def test_get_question(client: TestClient) -> None:
    payload = {
        "type": "T2",
        "source": "mock",
        "year": 2024,
        "month": 6,
        "suite": "D",
        "number": "05",
        "title": "Lookup",
        "body": "Body",
        "tags": ["tag1"],
    }
    created = client.post("/questions", json=payload).json()
    question_id = created["id"]
    response = client.get(f"/questions/{question_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Lookup"
    assert data["tags"] == ["tag1"]


def test_get_question_not_found(client: TestClient) -> None:
    response = client.get("/questions/999")
    assert response.status_code == 404


def test_create_question_invalid_type(client: TestClient) -> None:
    payload = {
        "type": "T1",
        "source": "mock",
        "year": 2024,
        "month": 5,
        "suite": "E",
        "number": "06",
        "title": "Invalid type",
        "body": "Body",
        "tags": [],
    }
    response = client.post("/questions", json=payload)
    assert response.status_code == 422


def test_create_question_duplicate(client: TestClient) -> None:
    payload = {
        "type": "T2",
        "source": "mock",
        "year": 2024,
        "month": 7,
        "suite": "F",
        "number": "07",
        "title": "Original",
        "body": "Body",
        "tags": [],
    }
    client.post("/questions", json=payload)
    response = client.post("/questions", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_update_question_tags_sync(client: TestClient) -> None:
    payload = {
        "type": "T3",
        "source": "mock",
        "year": 2024,
        "month": 8,
        "suite": "G",
        "number": "08",
        "title": "Tags sync",
        "body": "Body",
        "tags": ["alpha", "beta"],
    }
    created = client.post("/questions", json=payload).json()
    question_id = created["id"]
    update_payload = {
        "tags": ["beta", "gamma", "gamma", "  delta  "],
    }
    response = client.put(f"/questions/{question_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == ["beta", "gamma", "delta"]


def test_question_slug_is_computed_from_fields(client: TestClient) -> None:
    payload = {
        "type": "T2",
        "source": "seikou",
        "year": 2025,
        "month": 10,
        "suite": "1",
        "number": "2",
        "title": "Default",
        "body": "Body",
        "tags": [],
    }
    response = client.post("/questions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "RE202510.T2.P01S02"


def test_generate_question_metadata(client: TestClient) -> None:
    class DummyLLM:
        def generate_metadata(self, *, slug, body, question_type, tags):
            return GeneratedQuestionMetadata(title="新的标题", tags=["教育", "家庭"])

    app.dependency_overrides[get_llm_client] = lambda: DummyLLM()
    payload = {
        "type": "T2",
        "source": "mock",
        "year": 2024,
        "month": 9,
        "suite": "H",
        "number": "09",
        "title": "原始标题",
        "body": "Parlez de votre ville.",
        "tags": ["ville"],
    }
    created = client.post("/questions", json=payload).json()
    response = client.post(f"/questions/{created['id']}/generate-metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "新的标题"
    assert data["tags"] == ["教育", "家庭"]
    assert data["slug"] == created["slug"]
