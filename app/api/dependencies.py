from collections.abc import Generator

from pathlib import Path
from collections.abc import Generator

from sqlmodel import Session

from app.db.base import get_engine
from app.fetchers.manager import FetchManager


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for request scope."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


def get_fetch_manager() -> FetchManager:
    config_path = Path("config/fetchers.yaml")
    return FetchManager(config_path=config_path)
