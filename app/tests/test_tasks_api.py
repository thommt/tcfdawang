from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.api.dependencies import get_session, get_llm_client
from app.db.schemas import Task, Session as SessionSchema, Question, AnswerGroup, Answer


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

    class DummyLLM:
        def evaluate_answer(self, **kwargs):
            return {"feedback": "好", "score": 4}

        def compose_answer(self, **kwargs):
            return {"title": "标题", "text": "内容"}

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_llm_client] = lambda: DummyLLM()
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _create_question(session: Session, idx: int = 0) -> int:
    question = Question(
        type="T2",
        source="seikou",
        year=2024,
        month=9,
        suite=str(idx + 1),
        number=str(idx + 1),
        title=f"Question {idx}",
        body="Body",
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    sess = SessionSchema(question_id=question.id, session_type="first", status="draft")
    session.add(sess)
    session.commit()
    session.refresh(sess)
    return sess.id


def _create_answer(session: Session, idx: int = 0) -> int:
    question = Question(
        type="T2",
        source="seikou",
        year=2024,
        month=10,
        suite=str(idx + 1),
        number=str(idx + 1),
        title=f"Answer question {idx}",
        body="Body",
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    group = AnswerGroup(question_id=question.id, title=f"Group {idx}")
    session.add(group)
    session.commit()
    session.refresh(group)
    answer = Answer(answer_group_id=group.id, title=f"Answer {idx}", text="Texte", status="active")
    session.add(answer)
    session.commit()
    session.refresh(answer)
    return answer.id


def test_list_tasks(client: TestClient, session: Session) -> None:
    session_id = _create_question(session)
    task = Task(type="eval", status="succeeded", payload={"session_id": session_id}, session_id=session_id)
    session.add(task)
    session.commit()
    resp = client.get("/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["session_id"] == session_id


def test_filter_tasks_by_session(client: TestClient, session: Session) -> None:
    s1 = _create_question(session, idx=0)
    s2 = _create_question(session, idx=1)
    tasks = [
        Task(type="eval", status="pending", session_id=s1, payload={"session_id": s1}),
        Task(type="compose", status="succeeded", session_id=s2, payload={"session_id": s2}),
    ]
    session.add_all(tasks)
    session.commit()
    resp = client.get(f"/tasks?session_id={s1}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "eval"


def test_filter_tasks_by_answer(client: TestClient, session: Session) -> None:
    answer_one = _create_answer(session, idx=0)
    answer_two = _create_answer(session, idx=1)
    tasks = [
        Task(type="structure", status="failed", answer_id=answer_one, payload={"answer_id": answer_one}),
        Task(type="structure", status="succeeded", answer_id=answer_two, payload={"answer_id": answer_two}),
    ]
    session.add_all(tasks)
    session.commit()
    resp = client.get(f"/tasks?task_type=structure&answer_id={answer_one}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["answer_id"] == answer_one


def test_get_task_detail(client: TestClient, session: Session) -> None:
    session_id = _create_question(session)
    task = Task(type="eval", status="pending", session_id=session_id, payload={"session_id": session_id})
    session.add(task)
    session.commit()
    session.refresh(task)
    resp = client.get(f"/tasks/{task.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task.id


def test_retry_task(client: TestClient, session: Session) -> None:
    session_id = _create_question(session)
    resp = client.post(f"/sessions/{session_id}/tasks/eval")
    assert resp.status_code == 201
    task_id = resp.json()["id"]
    retry_resp = client.post(f"/tasks/{task_id}/retry")
    assert retry_resp.status_code == 201
    assert retry_resp.json()["type"] == "eval"


def test_cancel_task(client: TestClient, session: Session) -> None:
    session_id = _create_question(session)
    task = Task(type="eval", status="pending", session_id=session_id, payload={"session_id": session_id})
    session.add(task)
    session.commit()
    session.refresh(task)
    cancel_resp = client.post(f"/tasks/{task.id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "canceled"
