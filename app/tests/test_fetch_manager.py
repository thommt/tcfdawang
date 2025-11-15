from pathlib import Path
from typing import Generator

import pytest

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.fetchers.manager import FetchManager
from app.models.fetch import FetchedQuestion
from app.models.question import QuestionCreate
from app.services.question_service import QuestionService
from app.db.schemas import Question, QuestionTag  # noqa: F401


SAMPLE_HTML = """
<html>
  <head>
    <title>Octobre 2025 - Expression Orale</title>
  </head>
  <body>
    <h1>Octobre 2025 - Expression Orale</h1>
    <article class="entry-content">
      <h2>Tâche 3</h2>
      <h3>Partie 1</h3>
      <p>Sujet 1</p>
      <p>Vous discutez avec votre ami de l'environnement.</p>
      <p>Expliquez votre opinion et proposez des solutions.</p>
    </article>
  </body>
</html>
"""


class DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:  # pragma: no cover - simple stub
        return


OPAL_HTML = """
<html>
  <head>
    <title>Expression Orale SEPTEMBRE 2025</title>
  </head>
  <body>
    <h1>Expression Orale SEPTEMBRE 2025</h1>
    <section>
      <h2>TÂCHE 2</h2>
      <h3>COMBINAISON 1</h3>
      <p>Sujet 1</p>
      <p>Expliquez l'importance de l'apprentissage.</p>
      <p>Donnez des exemples personnels.</p>
    </section>
    <section>
      <h2>TÂCHE 3</h2>
      <h3>COMBINAISON 2</h3>
      <p>Sujet 1</p>
      <p>Débattez avec un ami sur la technologie.</p>
    </section>
  </body>
</html>
"""


@pytest.fixture()
def fetch_config(tmp_path: Path) -> Path:
    config_text = """
fetchers:
  - name: seikou
    domains: ["reussir-tcfcanada.com"]
    fetcher: app.fetchers.seikou:SeikouFetcher
    options:
      source_name: "reussir-tcfcanada"
  - name: tanpaku
    domains: ["tcf.opal-ca.net"]
    fetcher: app.fetchers.tanpaku:TanpakuFetcher
    options:
      source_name: "opal-ca"
"""
    path = tmp_path / "fetchers.yaml"
    path.write_text(config_text, encoding="utf-8")
    return path


@pytest.fixture()
def fetch_manager(fetch_config: Path) -> FetchManager:
    return FetchManager(config_path=fetch_config)


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


def test_fetch_manager_parses_questions(
    fetch_manager: FetchManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, headers=None, timeout=30):
        assert "octobre-2025" in url
        return DummyResponse(SAMPLE_HTML)

    monkeypatch.setattr("app.fetchers.seikou.requests.get", fake_get)
    url = "https://reussir-tcfcanada.com/octobre-2025-expression-orale/"
    results = fetch_manager.fetch_urls([url])
    assert len(results) == 1
    question = results[0]
    assert isinstance(question, FetchedQuestion)
    assert question.type == "T3"
    assert question.suite == "1"
    assert question.number == "1"
    assert question.year == 2025
    assert question.month == 10
    assert question.title.startswith("Sujet 1")
    assert "environnement" in question.body
    assert question.slug == "202510.T3.P1S1"
    assert question.source_url == url


def test_fetch_manager_unknown_domain(fetch_manager: FetchManager) -> None:
    url = "https://example.com/test"
    with pytest.raises(ValueError):
        fetch_manager.fetch_urls([url])


def test_fetched_question_can_be_saved(
    fetch_manager: FetchManager, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, headers=None, timeout=30):
        return DummyResponse(SAMPLE_HTML)

    monkeypatch.setattr("app.fetchers.seikou.requests.get", fake_get)
    url = "https://reussir-tcfcanada.com/octobre-2025-expression-orale/"
    question = fetch_manager.fetch_urls([url])[0]
    service = QuestionService(session)
    payload = QuestionCreate(
        type=question.type,
        source=question.source,
        year=question.year,
        month=question.month,
        suite=question.suite,
        number=question.number,
        title=question.title,
        body=question.body,
        tags=question.tags,
    )
    created = service.create_question(payload)
    assert created.title == question.title
    db_question = session.get(Question, created.id)
    assert db_question is not None
    assert db_question.suite == question.suite
    assert db_question.number == question.number


def test_tanpaku_fetcher_parses_combinaisons(
    fetch_manager: FetchManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, headers=None, timeout=30):
        assert "opal" in url
        return DummyResponse(OPAL_HTML)

    monkeypatch.setattr("app.fetchers.tanpaku.requests.get", fake_get)
    url = "https://tcf.opal-ca.net/expression-orale-SEPTEMBRE-2025/"
    questions = fetch_manager.fetch_urls([url])
    assert len(questions) == 2
    t2, t3 = questions
    assert t2.type == "T2"
    assert t2.suite == "1"
    assert t2.number == "1"
    assert t2.month == 9
    assert "apprentissage" in t2.body
    assert t3.type == "T3"
    assert t3.suite == "2"
    assert t3.number == "1"
