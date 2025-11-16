from typing import Generator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.api.dependencies import get_session, get_fetch_manager
from app.models.fetch import FetchedQuestion
from app.fetchers.base import BaseQuestionFetcher


class DummyFetcher(BaseQuestionFetcher):
    def __init__(self, options=None) -> None:
        super().__init__(options)
        self.data: List[FetchedQuestion] = [
            FetchedQuestion(
                type="T3",
                source="dummy",
                year=2025,
                month=11,
                suite="1",
                number="1",
                title="RE202511.T3.P01S01",
                body="Sample body",
                tags=[],
                slug="RE202511.T3.P01S01",
                source_url="https://example/test",
                source_name="dummy",
            )
        ]

    def fetch(self, url: str) -> List[FetchedQuestion]:
        return self.data


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_session():
        yield session

    def override_fetch_manager():
        class DummyManager:
            def fetch_urls(self, urls):
                fetcher = DummyFetcher()
                return fetcher.fetch(urls[0])

        return DummyManager()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_fetch_manager] = override_fetch_manager
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_fetch_api_creates_task_and_results(client: TestClient) -> None:
    response = client.post("/questions/fetch", json={"urls": ["https://example/test"]})
    assert response.status_code == 201
    data = response.json()
    assert data["task"]["status"] == "succeeded"
    assert data["task"]["result_summary"]["count"] == 1
    assert data["results"][0]["slug"] == "RE202511.T3.P01S01"

    task_id = data["task"]["id"]
    resp = client.get(f"/questions/fetch/results?task_id={task_id}")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "RE202511.T3.P01S01"
    assert results[0]["slug"] == "RE202511.T3.P01S01"


def test_fetch_api_returns_error_on_failure(client: TestClient) -> None:
    class FailingManager:
        def fetch_urls(self, urls):
            raise ValueError("No fetcher configured")

    app.dependency_overrides[get_fetch_manager] = lambda: FailingManager()
    response = client.post("/questions/fetch", json={"urls": ["https://unknown"]})
    assert response.status_code == 400
    assert "No fetcher" in response.json()["detail"]


def test_fetch_import_results(client: TestClient) -> None:
    fetch_resp = client.post("/questions/fetch", json={"urls": ["https://example/test"]})
    task_id = fetch_resp.json()["task"]["id"]
    import_resp = client.post("/questions/fetch/import", json={"task_id": task_id})
    assert import_resp.status_code == 201
    data = import_resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "RE202511.T3.P01S01"
    assert data[0]["slug"] == "DU202511.T3.P01S01"
