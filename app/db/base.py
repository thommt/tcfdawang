from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///./app.db"

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
        )
    return _engine


def init_db() -> None:
    """Create tables for initial skeleton."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _ensure_session_columns(engine)
    _ensure_task_columns(engine)
    _ensure_sentence_columns(engine)
    _ensure_flashcard_columns(engine)


def _ensure_session_columns(engine) -> None:
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info('sessions')"))
        columns = {row[1] for row in result}
        if "updated_at" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE sessions ADD COLUMN updated_at TIMESTAMP"
                )
            )


def _ensure_task_columns(engine) -> None:
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info('tasks')"))
        columns = {row[1] for row in result}
        if "session_id" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN session_id INTEGER"))
        if "answer_id" not in columns:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN answer_id INTEGER"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_answer_id ON tasks(answer_id)"))


def _ensure_sentence_columns(engine) -> None:
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info('sentences')"))
        columns = {row[1] for row in result}
        if "translation_en" not in columns:
            conn.execute(text("ALTER TABLE sentences ADD COLUMN translation_en TEXT"))
        if "translation_zh" not in columns:
            conn.execute(text("ALTER TABLE sentences ADD COLUMN translation_zh TEXT"))
        if "difficulty" not in columns:
            conn.execute(text("ALTER TABLE sentences ADD COLUMN difficulty TEXT"))


def _ensure_flashcard_columns(engine) -> None:
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info('flashcard_progress')"))
        columns = {row[1] for row in result}
        if not columns:
            return
        if "interval_days" not in columns:
            conn.execute(text("ALTER TABLE flashcard_progress ADD COLUMN interval_days INTEGER DEFAULT 1"))
