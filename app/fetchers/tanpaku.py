from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseQuestionFetcher
from app.models.fetch import FetchedQuestion


RE_TACHE = re.compile(r"t(?:â|a)che\s*(\d+)", re.IGNORECASE)
RE_COMBINAISON = re.compile(r"combinaison\s*(\d+)", re.IGNORECASE)
RE_SUJET = re.compile(r"sujet\s*(\d+)", re.IGNORECASE)
RE_MONTH_YEAR = re.compile(
    r"(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})",
    re.IGNORECASE,
)

MONTHS = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}


class TanpakuFetcher(BaseQuestionFetcher):
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    def fetch(self, url: str) -> List[FetchedQuestion]:
        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        month, year = self._extract_month_year(soup)
        sections = soup.find_all(["section", "article", "div"])
        questions: List[dict] = []
        for section in sections:
            questions.extend(self._parse_section(section))
        source_alias = self.options.get("source_name") or (urlparse(url).hostname or "unknown")
        result: List[FetchedQuestion] = []
        for item in questions:
            slug = self._build_slug(year, month, item["tache"], item["combinaison"], item["sujet"])
            result.append(
                FetchedQuestion(
                    type=f"T{item['tache']}",
                    source=source_alias,
                    year=year,
                    month=month,
                    suite=item["combinaison"],
                    number=str(item["sujet"]),
                    title=slug,
                    body=item["body"],
                    tags=[],
                    slug=slug,
                    source_url=url,
                    source_name=source_alias,
                )
            )
        return result

    def _get_html(self, url: str) -> str:
        headers = {"User-Agent": self.USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text

    def _extract_month_year(self, soup: BeautifulSoup) -> Tuple[int, int]:
        candidates = []
        for selector in ["h1", "title"]:
            tag = soup.find(selector)
            if tag and tag.get_text(strip=True):
                candidates.append(tag.get_text(" ", strip=True))
        for text in candidates:
            m = RE_MONTH_YEAR.search(text)
            if m:
                month = MONTHS.get(m.group(1).lower(), 1)
                year = int(m.group(2))
                return month, year
        raise ValueError("Unable to determine month/year for page")

    def _parse_section(self, section) -> List[dict]:
        current_tache = None
        current_combinaison = None
        results: List[dict] = []
        buffer: List[str] = []
        current_sujet = None
        for element in section.find_all(["h1", "h2", "h3", "p", "li"]):
            text = element.get_text(" ", strip=True)
            if not text:
                continue
            if (match := RE_TACHE.search(text)):
                current_tache = int(match.group(1))
                continue
            if (match := RE_COMBINAISON.search(text)):
                current_combinaison = match.group(1)
                continue
            if (match := RE_SUJET.search(text)):
                if current_tache and current_combinaison and buffer and current_sujet:
                    results.append(
                        {
                            "tache": current_tache,
                            "combinaison": current_combinaison,
                            "sujet": current_sujet,
                            "body": "\n".join(buffer).strip(),
                        }
                    )
                current_sujet = int(match.group(1))
                buffer = []
                continue
            if current_tache and current_combinaison and current_sujet:
                buffer.append(text)
        if current_tache and current_combinaison and current_sujet and buffer:
            results.append(
                {
                    "tache": current_tache,
                    "combinaison": current_combinaison,
                    "sujet": current_sujet,
                    "body": "\n".join(buffer).strip(),
                }
            )
        return results

    def _build_slug(self, year, month, tache, combinaison, sujet) -> str:
        comb = int(combinaison)
        return f"OP{year:04d}{month:02d}.T{int(tache)}.P{comb:02d}S{int(sujet):02d}"
