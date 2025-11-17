from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.api.dependencies import get_session
from app.db.schemas import Answer, AnswerGroup, Question, Paragraph, Sentence


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


def _create_answer(session: Session) -> int:
    question = Question(
        type="T2",
        source="seikou",
        year=2024,
        month=9,
        suite="1",
        number="1",
        title="Question",
        body="Body",
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    group = AnswerGroup(question_id=question.id, title="Group")
    session.add(group)
    session.commit()
    session.refresh(group)
    answer = Answer(answer_group_id=group.id, title="Answer", text="Texte", status="active")
    session.add(answer)
    session.commit()
    session.refresh(answer)
    para = Paragraph(answer_id=answer.id, order_index=1, role_label="intro", summary="Summary")
    session.add(para)
    session.commit()
    session.refresh(para)
    sent = Sentence(paragraph_id=para.id, order_index=1, text="Bonjour", translation="Hello")
    session.add(sent)
    session.commit()
    return answer.id


def test_list_paragraphs(client: TestClient, session: Session) -> None:
    answer_id = _create_answer(session)
    response = client.get(f"/answers/{answer_id}/paragraphs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["role_label"] == "intro"
    assert len(data[0]["sentences"]) == 1
