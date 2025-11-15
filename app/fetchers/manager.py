from __future__ import annotations

import importlib
import yaml
from pathlib import Path
from typing import Any, Dict, List, Type
from urllib.parse import urlparse

from app.fetchers.base import BaseQuestionFetcher
from app.models.fetch import FetchedQuestion


class FetchManager:
    def __init__(self, config_path: Path | str) -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Fetcher config not found: {self.config_path}")
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        return data or {}

    def fetch_urls(self, urls: List[str]) -> List[FetchedQuestion]:
        results: List[FetchedQuestion] = []
        for url in urls:
            fetcher_info = self._resolve_fetcher(url)
            fetcher_cls = self._import_fetcher(fetcher_info["fetcher"])
            fetcher = fetcher_cls(fetcher_info.get("options"))
            results.extend(fetcher.fetch(url))
        return results

    def _resolve_fetcher(self, url: str) -> Dict[str, Any]:
        hostname = urlparse(url).hostname or ""
        normalized_host = hostname.lower()
        for entry in self.config.get("fetchers", []):
            domains = [d.lower() for d in entry.get("domains", [])]
            if any(normalized_host.endswith(domain) for domain in domains):
                return entry
        raise ValueError(f"No fetcher configured for domain: {hostname}")

    def _import_fetcher(self, dotted_path: str) -> Type[BaseQuestionFetcher]:
        module_path, class_name = dotted_path.split(":")
        module = importlib.import_module(module_path)
        fetcher_cls = getattr(module, class_name)
        if not issubclass(fetcher_cls, BaseQuestionFetcher):
            raise TypeError(f"{dotted_path} is not a BaseQuestionFetcher")
        return fetcher_cls
