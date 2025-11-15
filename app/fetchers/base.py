from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.models.fetch import FetchedQuestion


class BaseQuestionFetcher(ABC):
    """Abstract base class for question fetchers."""

    def __init__(self, options: Dict[str, Any] | None = None) -> None:
        self.options = options or {}

    @abstractmethod
    def fetch(self, url: str) -> List[FetchedQuestion]:
        """Fetch questions from a URL."""
        raise NotImplementedError
