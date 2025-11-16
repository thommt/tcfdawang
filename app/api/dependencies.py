import os
from collections.abc import Generator
from pathlib import Path

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db.base import get_engine
from app.fetchers.manager import FetchManager
from app.services.llm_service import QuestionLLMClient


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for request scope."""
    engine = get_engine()
    with Session(engine) as session:
        yield session


def get_fetch_manager() -> FetchManager:
    config_path = Path("config/fetchers.yaml")
    return FetchManager(config_path=config_path)


def get_llm_client() -> QuestionLLMClient:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="未配置 OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL") or None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return QuestionLLMClient(api_key=api_key, model=model, base_url=base_url)
