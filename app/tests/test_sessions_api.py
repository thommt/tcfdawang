from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.main import app
from app.api.dependencies import get_session, get_llm_client
from app.db.schemas import (
    AnswerGroup,
    Answer,
    Paragraph,
    Sentence,
    SentenceChunk,
    Lexeme,
    ChunkLexeme,
    FlashcardProgress,
)


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
            return {"feedback": "很好", "score": 4}

        def structure_answer(self, **kwargs):
            return {
                "paragraphs": [
                    {
                        "role": "intro",
                        "summary": "summary",
                        "sentences": [{"text": "Bonjour", "translation": "Hello"}],
                    }
                ]
            }

        def compose_answer(self, **kwargs):
            return {"title": "自动标题", "text": "Réponse standard"}

        def compare_answer(self, **kwargs):
            return {"decision": "new_group", "matched_answer_group_id": None, "reason": "差异较大", "differences": []}

        def highlight_gaps(self, **kwargs):
            return {
                "coverage_score": 0.5,
                "missing_points": ["缺少示例"],
                "grammar_notes": ["动词一致"],
                "suggestions": ["添加结论"],
            }

        def refine_answer(self, **kwargs):
            return {"text": "Réponse enrichie", "notes": ["加入更多细节"]}

    app.dependency_overrides[get_llm_client] = lambda: DummyLLM()
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


def test_run_eval_task(client: TestClient) -> None:
    question_id = _create_question(client)
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Je pense que..."},
    )
    session_id = session_resp.json()["id"]
    task_resp = client.post(f"/sessions/{session_id}/tasks/eval")
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert task["type"] == "eval"
    assert task["status"] == "succeeded"
    assert task["result_summary"]["score"] == 4
    assert "saved_at" in task["result_summary"]
    session_data = client.get(f"/sessions/{session_id}").json()
    last_eval = session_data["progress_state"]["last_eval"]
    assert last_eval["score"] == 4
    assert "saved_at" in last_eval


def test_run_compose_task(client: TestClient) -> None:
    class DummyLLM:
        def evaluate_answer(self, **kwargs):
            return {"feedback": "很好", "score": 4}

        def compose_answer(self, **kwargs):
            return {"title": "标题", "text": "Mon texte"}

        def compare_answer(self, **kwargs):
            return {"decision": "new_group", "matched_answer_group_id": None, "reason": "全新主旨", "differences": []}

    app.dependency_overrides[get_llm_client] = lambda: DummyLLM()
    question_id = _create_question(client)
    session_resp = client.post("/sessions", json={"question_id": question_id}).json()
    task_resp = client.post(f"/sessions/{session_resp['id']}/tasks/compose")
    assert task_resp.status_code == 201
    data = task_resp.json()
    assert data["type"] == "compose"
    assert data["result_summary"]["text"] == "Mon texte"
    assert "saved_at" in data["result_summary"]
    session_data = client.get(f"/sessions/{session_resp['id']}").json()
    last_compose = session_data["progress_state"]["last_compose"]
    assert last_compose["text"] == "Mon texte"
    assert "saved_at" in last_compose


def test_compare_task(client: TestClient) -> None:
    question_id = _create_question(client)
    group_resp = client.post(
        "/answer-groups",
        json={"question_id": question_id, "title": "Group 1"},
    ).json()
    client.post(
        "/answers",
        json={
            "answer_group_id": group_resp["id"],
            "title": "Answer title",
            "text": "Contenu",
        },
    )
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Je pense que..."},
    )
    session_id = session_resp.json()["id"]
    task_resp = client.post(f"/sessions/{session_id}/tasks/compare")
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert task["type"] == "compare"
    assert task["status"] == "succeeded"
    summary = task["result_summary"]
    assert summary["decision"] in {"new_group", "reuse"}
    assert "saved_at" in summary


def test_gap_highlight_and_refine(client: TestClient) -> None:
    question_id = _create_question(client)
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Je pense que..."},
    )
    session_id = session_resp.json()["id"]
    highlight_resp = client.post(f"/sessions/{session_id}/tasks/gap-highlight")
    assert highlight_resp.status_code == 201
    highlight = highlight_resp.json()
    assert highlight["type"] == "gap_highlight"
    assert highlight["result_summary"]["coverage_score"] == 0.5
    refine_resp = client.post(f"/sessions/{session_id}/tasks/refine")
    assert refine_resp.status_code == 201
    refine = refine_resp.json()
    assert refine["type"] == "refine_answer"
    assert refine["result_summary"]["text"] == "Réponse enrichie"


def test_finalize_session_creates_answer(client: TestClient, session: Session) -> None:
    question_id = _create_question(client)
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Bonjour"},
    ).json()
    finalize_payload = {
        "group_title": "家庭题",
        "answer_title": "答案版本1",
        "answer_text": "Ceci est une réponse.",
    }
    finalize_resp = client.post(f"/sessions/{session_resp['id']}/finalize", json=finalize_payload)
    assert finalize_resp.status_code == 200
    data = finalize_resp.json()
    assert data["status"] == "completed"
    groups = session.exec(select(AnswerGroup)).all()
    assert len(groups) == 1
    answers = session.exec(select(Answer)).all()
    assert len(answers) == 1

    second_session = client.post("/sessions", json={"question_id": question_id}).json()
    reuse_payload = {
        "answer_group_id": groups[0].id,
        "answer_title": "答案版本2",
        "answer_text": "Deuxième réponse.",
    }
    resp = client.post(f"/sessions/{second_session['id']}/finalize", json=reuse_payload)
    assert resp.status_code == 200
    answers = session.exec(select(Answer).where(Answer.answer_group_id == groups[0].id)).all()
    assert len(answers) == 2

    list_resp = client.get(f"/answer-groups/by-question/{question_id}")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert len(data[0]["answers"]) == 2


def test_answer_history_endpoint(client: TestClient) -> None:
    question_id = _create_question(client)
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Texte initial"},
    ).json()
    eval_resp = client.post(f"/sessions/{session_resp['id']}/tasks/eval")
    assert eval_resp.status_code == 201

    finalize_payload = {
        "group_title": "历史答案",
        "answer_title": "版本1",
        "answer_text": "Une réponse complète",
    }
    finalize_resp = client.post(f"/sessions/{session_resp['id']}/finalize", json=finalize_payload)
    assert finalize_resp.status_code == 200
    answer_id = finalize_resp.json()["answer_id"]

    structure_resp = client.post(f"/answers/{answer_id}/tasks/structure")
    assert structure_resp.status_code == 201

    history_resp = client.get(f"/answers/{answer_id}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["answer"]["id"] == answer_id
    assert history["group"]["title"] == "历史答案"
    assert len(history["sessions"]) == 1
    assert any(task["type"] == "eval" for task in history["tasks"])
    assert any(conv["purpose"] == "eval" for conv in history["conversations"])


def test_session_history_endpoint(client: TestClient) -> None:
    question_id = _create_question(client)
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Texte initial"},
    ).json()
    eval_resp = client.post(f"/sessions/{session_resp['id']}/tasks/eval")
    assert eval_resp.status_code == 201

    history_resp = client.get(f"/sessions/{session_resp['id']}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["session"]["id"] == session_resp["id"]
    assert len(history["tasks"]) == 1
    assert history["tasks"][0]["type"] == "eval"
    assert any(conv["purpose"] == "eval" for conv in history["conversations"])


def test_create_review_session(client: TestClient, session: Session) -> None:
    question_id = _create_question(client)
    session_resp = client.post(
        "/sessions",
        json={"question_id": question_id, "user_answer_draft": "Bonjour"},
    ).json()
    finalize_payload = {
        "group_title": "复习题",
        "answer_title": "首版答案",
        "answer_text": "Un texte",
    }
    finalize_resp = client.post(f"/sessions/{session_resp['id']}/finalize", json=finalize_payload)
    answer_id = finalize_resp.json()["answer_id"]

    review_resp = client.post(f"/answers/{answer_id}/sessions")
    assert review_resp.status_code == 201


def test_delete_answer_group_cascades(client: TestClient, session: Session) -> None:
    question_id = _create_question(client)
    group = client.post(
        "/answer-groups",
        json={"question_id": question_id, "title": "Group"},
    ).json()
    answer = client.post(
        "/answers",
        json={
            "answer_group_id": group["id"],
            "title": "Answer title",
            "text": "Contenu",
        },
    ).json()
    paragraph = Paragraph(answer_id=answer["id"], order_index=1, role_label="intro", summary="summary", extra={})
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
        extra={},
    )
    session.add(sentence)
    session.commit()
    session.refresh(sentence)
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
    lexeme = Lexeme(
        headword="bonjour",
        lemma="bonjour",
        sense_label="greeting",
        gloss="hello",
        translation_en="hello",
        translation_zh="你好",
        pos_tags="noun",
        difficulty="A1",
        hash="bonjour::greeting::bonjour",
        extra={},
    )
    session.add(lexeme)
    session.commit()
    session.refresh(lexeme)
    link = ChunkLexeme(chunk_id=chunk.id, lexeme_id=lexeme.id, order_index=1, role="root", extra={})
    session.add(link)
    session.commit()
    for entity_type, entity_id in [
        ("sentence", sentence.id),
        ("chunk", chunk.id),
        ("lexeme", lexeme.id),
    ]:
        session.add(
            FlashcardProgress(
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )
    session.commit()
    review_session = client.post(
        "/sessions",
        json={"question_id": question_id, "answer_id": answer["id"]},
    ).json()

    resp = client.delete(f"/answer-groups/{group['id']}")
    assert resp.status_code == 204
    assert client.get(f"/answer-groups/{group['id']}").status_code == 404
    assert session.get(Answer, answer["id"]) is None
    assert session.exec(select(Paragraph).where(Paragraph.answer_id == answer["id"])).all() == []
    assert session.exec(select(Sentence).where(Sentence.paragraph_id == paragraph.id)).all() == []
    assert session.exec(select(SentenceChunk).where(SentenceChunk.sentence_id == sentence.id)).all() == []
    assert session.exec(select(ChunkLexeme).where(ChunkLexeme.chunk_id == chunk.id)).all() == []
    assert session.get(Lexeme, lexeme.id) is None
    assert (
        session.exec(
            select(FlashcardProgress).where(FlashcardProgress.entity_type == "sentence")
        ).all()
        == []
    )
    assert (
        session.exec(
            select(FlashcardProgress).where(FlashcardProgress.entity_type == "chunk")
        ).all()
        == []
    )
    assert (
        session.exec(
            select(FlashcardProgress).where(FlashcardProgress.entity_type == "lexeme")
        ).all()
        == []
    )
    updated_session = client.get(f"/sessions/{review_session['id']}").json()
    assert updated_session["answer_id"] is None


def test_delete_single_answer(client: TestClient, session: Session) -> None:
    question_id = _create_question(client)
    group = client.post(
        "/answer-groups",
        json={"question_id": question_id, "title": "Group"},
    ).json()
    answer = client.post(
        "/answers",
        json={
            "answer_group_id": group["id"],
            "title": "Answer title",
            "text": "Texte",
        },
    ).json()
    paragraph = Paragraph(answer_id=answer["id"], order_index=1, role_label="intro", summary="sum", extra={})
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
        extra={},
    )
    session.add(sentence)
    session.commit()
    session.refresh(sentence)
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
    flashcard = FlashcardProgress(entity_type="sentence", entity_id=sentence.id)
    session.add(flashcard)
    session.commit()
    resp = client.delete(f"/answers/{answer['id']}")
    assert resp.status_code == 204
    assert client.get(f"/answers/{answer['id']}").status_code == 404
    assert client.get(f"/answer-groups/{group['id']}").status_code == 200
    assert session.exec(select(Paragraph).where(Paragraph.answer_id == answer["id"])).all() == []
    assert session.exec(select(Sentence).where(Sentence.paragraph_id == paragraph.id)).all() == []
    assert session.exec(select(SentenceChunk).where(SentenceChunk.sentence_id == sentence.id)).all() == []
    assert session.exec(select(FlashcardProgress).where(FlashcardProgress.entity_type == "sentence")).all() == []


def test_delete_non_latest_answer_fails(client: TestClient, session: Session) -> None:
    question_id = _create_question(client)
    group = client.post(
        "/answer-groups",
        json={"question_id": question_id, "title": "Group"},
    ).json()
    first = client.post(
        "/answers",
        json={
            "answer_group_id": group["id"],
            "title": "V1",
            "text": "Texte",
            "version_index": 1,
        },
    ).json()
    second = client.post(
        "/answers",
        json={
            "answer_group_id": group["id"],
            "title": "V2",
            "text": "Texte2",
            "version_index": 2,
        },
    ).json()
    resp = client.delete(f"/answers/{first['id']}")
    assert resp.status_code == 400
    assert client.get(f"/answers/{first['id']}").status_code == 200
    assert client.delete(f"/answers/{second['id']}").status_code == 204
