from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.fetchers.base import BaseQuestionFetcher
from app.models.fetch import FetchedQuestion

RE_TACHE = re.compile(r"^(?:t(?:â|a)che)\s*(\d+)", re.IGNORECASE)
RE_PARTIE = re.compile(r"^partie\s*(\d+)", re.IGNORECASE)
RE_SUJET = re.compile(r"^sujet\s*(\d+)", re.IGNORECASE)
RE_MONTH_YEAR = re.compile(
    r"\b(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\b\s+(\d{4})",
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


class SeikouFetcher(BaseQuestionFetcher):
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    def fetch(self, url: str) -> List[FetchedQuestion]:
        html = self._get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        month, year = self._extract_month_year(soup)
        article = self._guess_article_body(soup)
        questions = self._parse_article(article)
        source_alias = self.options.get("source_name") or (urlparse(url).hostname or "unknown")
        result: List[FetchedQuestion] = []
        for item in questions:
            slug = self._build_slug(year, month, item["tache"], item["partie"], item["sujet"])
            slug = self._build_slug(year, month, item["tache"], item["partie"], item["sujet"])
            result.append(
                FetchedQuestion(
                    type=f"T{item['tache']}",
                    source=source_alias,
                    year=year,
                    month=month,
                    suite=str(item["partie"]),
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
                month_name = m.group(1).lower()
                year = int(m.group(2))
                month = MONTHS.get(month_name, 1)
                return month, year
        raise ValueError("Unable to determine month/year for page")

    def _guess_article_body(self, soup: BeautifulSoup):
        selectors = [
            "article .entry-content",
            "div.entry-content",
            "main article",
            "article",
            "main",
            "div#content",
            "div.site-main",
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                return node
        return soup.body or soup

    def _parse_article(self, article: BeautifulSoup) -> List[dict]:
        state = {"tache": None, "partie": None, "sujet": None, "buffer": []}
        results = []
        for element in article.find_all(["h1", "h2", "h3", "h4", "p", "li", "div"]):
            text = element.get_text(" ", strip=True)
            if not text:
                continue
            if element.name == "div" and element.find_all(["p", "div", "section"], recursive=False):
                continue
            tache = RE_TACHE.match(text)
            partie = RE_PARTIE.match(text)
            sujet = RE_SUJET.match(text)
            if tache:
                self._flush(state, results)
                state.update({"tache": int(tache.group(1)), "partie": None, "sujet": None, "buffer": []})
                continue
            if partie:
                self._flush(state, results)
                state.update({"partie": int(partie.group(1)), "sujet": None, "buffer": []})
                continue
            if sujet:
                self._flush(state, results)
                state.update({"sujet": int(sujet.group(1)), "buffer": []})
                continue
            if state["tache"] and state["partie"] and state["sujet"]:
                state["buffer"].append(text)
        self._flush(state, results)
        return results

    def _flush(self, state, results):
        if state["tache"] and state["partie"] and state["sujet"] and state["buffer"]:
            body = "\n".join(state["buffer"]).strip()
            results.append({
                "tache": state["tache"],
                "partie": state["partie"],
                "sujet": state["sujet"],
                "body": body,
            })
            state["buffer"] = []

    def _build_slug(self, year, month, tache, partie, sujet) -> str:
        return f"RE{year:04d}{month:02d}.T{int(tache)}.P{int(partie):02d}S{int(sujet):02d}"
