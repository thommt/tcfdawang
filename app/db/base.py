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
