from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.main import app
from app.api.dependencies import get_session, get_llm_client
from app.db.schemas import Answer, AnswerGroup, Question, Paragraph, Sentence, LLMConversation
from app.services.llm_service import LLMError


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
        def structure_answer(self, **kwargs):
            return {
                "paragraphs": [
                    {
                        "role": "body",
                        "summary": "LLM summary",
                        "sentences": [
                            {
                                "text": "Salut",
                                "translation": "Hi",
                                "translation_zh": "你好",
                                "difficulty": "B1",
                            }
                        ],
                    }
                ]
            }

        def translate_sentences(self, **kwargs):
            return {
                "translations": [
                    {
                        "sentence_index": 1,
                        "translation_en": "Hi",
                        "translation_zh": "你好",
                        "difficulty": "B1",
                    }
                ]
            }

        def chunk_sentence(self, **kwargs):
            return {
                "chunks": [
                    {
                        "chunk_index": 1,
                        "text": "Bonjour",
                        "translation_en": "Hello",
                        "translation_zh": "你好",
                    }
                ]
            }

        def build_chunk_lexemes(self, **kwargs):
            return {
                "lexemes": [
                    {
                        "chunk_index": 1,
                        "headword": "bonjour",
                        "sense_label": "问候",
                        "gloss": "to greet someone",
                        "translation_zh": "你好",
                        "translation_en": "hello",
                        "pos_tags": "noun",
                        "difficulty": "A2",
                    }
                ]
            }

        def assess_phrase_split_quality(self, **kwargs):
            return {"is_valid": True, "issues": []}

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_llm_client] = lambda: DummyLLM()
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
    sent = Sentence(paragraph_id=para.id, order_index=1, text="Bonjour", translation_en="Hello")
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


def test_run_structure_task(client: TestClient, session: Session) -> None:
    answer_id = _create_answer(session)
    response = client.post(f"/answers/{answer_id}/tasks/structure")
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "succeeded"

    paragraphs = session.exec(
        select(Paragraph).where(Paragraph.answer_id == answer_id).order_by(Paragraph.order_index)
    ).all()
    assert len(paragraphs) == 1
    assert paragraphs[0].role_label == "opening"
    assert paragraphs[0].summary == "LLM summary"

    sentences = session.exec(
        select(Sentence).where(Sentence.paragraph_id == paragraphs[0].id).order_by(Sentence.order_index)
    ).all()
    assert len(sentences) == 1
    assert sentences[0].text == "Salut"
    assert sentences[0].translation_en == "Hi"
    assert sentences[0].translation_zh == "你好"
    assert sentences[0].difficulty == "B1"


def test_structure_task_failure_keeps_previous_paragraphs(client: TestClient, session: Session) -> None:
    answer_id = _create_answer(session)

    class FailingLLM:
        def structure_answer(self, **kwargs):
            raise LLMError("failed to call LLM")

    app.dependency_overrides[get_llm_client] = lambda: FailingLLM()
    response = client.post(f"/answers/{answer_id}/tasks/structure")
    assert response.status_code == 502

    paragraphs = session.exec(
        select(Paragraph).where(Paragraph.answer_id == answer_id).order_by(Paragraph.order_index)
    ).all()
    assert len(paragraphs) == 1
    assert paragraphs[0].summary == "Summary"


def test_sentence_translation_task(client: TestClient, session: Session) -> None:
    answer_id = _create_answer(session)
    response = client.post(f"/answers/{answer_id}/tasks/translate-sentences")
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "succeeded"
    sentence = session.exec(select(Sentence)).first()
    assert sentence is not None
    assert sentence.translation_en == "Hi"
    assert sentence.translation_zh == "你好"
    assert sentence.difficulty == "B1"


def test_sentence_split_task(client: TestClient, session: Session) -> None:
    answer_id = _create_answer(session)
    sentence = session.exec(select(Sentence)).first()
    response = client.post(f"/sentences/{sentence.id}/tasks/chunks")
    assert response.status_code == 201
    response = client.post(f"/sentences/{sentence.id}/tasks/chunk-lexemes")
    assert response.status_code == 201
    from app.db.schemas import SentenceChunk, ChunkLexeme, Lexeme  # local import to avoid circular

    chunks = session.exec(select(SentenceChunk).where(SentenceChunk.sentence_id == sentence.id)).all()
    assert len(chunks) == 1
    links = session.exec(select(ChunkLexeme).where(ChunkLexeme.chunk_id == chunks[0].id)).all()
    assert len(links) == 1
    lexeme = session.exec(select(Lexeme).where(Lexeme.id == links[0].lexeme_id)).first()
    assert lexeme.headword == "bonjour"
    assert lexeme.translation_zh == "你好"


def test_split_task_records_llm_conversation(client: TestClient, session: Session) -> None:
    answer_id = _create_answer(session)
    sentence = session.exec(select(Sentence)).first()
    resp = client.post(f"/sentences/{sentence.id}/tasks/chunks")
    assert resp.status_code == 201
    resp = client.post(f"/sentences/{sentence.id}/tasks/chunk-lexemes")
    assert resp.status_code == 201
    conversation = session.exec(select(LLMConversation).order_by(LLMConversation.created_at.desc())).first()
    assert conversation is not None
    assert conversation.purpose == "chunk_lexeme"
    assert conversation.result.get("lexemes")
    messages = conversation.messages
    assert "lexeme_prompt" in messages
