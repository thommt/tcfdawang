from collections.abc import Generator

from sqlmodel import Session

from app.db.base import get_engine


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for request scope."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
