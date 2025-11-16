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


def _create_question(client: TestClient) -> int:
    payload = {
        "type": "T2",
        "source": "mock",
        "year": 2024,
        "month": 7,
        "suite": "A",
        "number": "01",
        "title": "Sample",
        "body": "Body",
        "tags": [],
    }
    response = client.post("/questions", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_update_session(client: TestClient) -> None:
    question_id = _create_question(client)
    resp = client.post("/sessions", json={"question_id": question_id})
    assert resp.status_code == 201
    session_data = resp.json()
    assert session_data["question_id"] == question_id

    update_resp = client.put(
        f"/sessions/{session_data['id']}",
        json={"status": "in_progress", "user_answer_draft": "Bonjour"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "in_progress"
    assert updated["user_answer_draft"] == "Bonjour"


def test_create_answer_group_and_answer(client: TestClient) -> None:
    question_id = _create_question(client)
    group_resp = client.post(
        "/answer-groups",
        json={"question_id": question_id, "title": "Group 1"},
    )
    assert group_resp.status_code == 201
    group = group_resp.json()
    assert group["question_id"] == question_id

    answer_resp = client.post(
        "/answers",
        json={
            "answer_group_id": group["id"],
            "title": "Answer title",
            "text": "Contenu",
        },
    )
    assert answer_resp.status_code == 201
    answer = answer_resp.json()
    assert answer["answer_group_id"] == group["id"]

    fetched_group = client.get(f"/answer-groups/{group['id']}")
    assert fetched_group.status_code == 200
    fetched_answer = client.get(f"/answers/{answer['id']}")
    assert fetched_answer.status_code == 200
