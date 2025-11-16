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
