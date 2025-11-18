from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.api.dependencies import get_session
from app.db.schemas import LLMConversation


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


def test_list_conversations(client: TestClient, session: Session) -> None:
    conversation = LLMConversation(purpose="structure", messages={"input": "test"}, result={"output": "ok"})
    session.add(conversation)
    session.commit()

    resp = client.get("/llm-conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["purpose"] == "structure"

