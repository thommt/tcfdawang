# 抓题脚本原型（仅供参考）

> 下方代码为最初的 `fetch.py` 脚本，用于解析 reussir-tcfcanada.com 等站点的 TCF 题目。该脚本不属于正式项目，仅供后续实现 Web 抓取功能时参考思路（解析层级、提取 slug 等）。请勿直接引用到生产代码中。

```python
import re
import json
import sys
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import unicodedata
import argparse
import csv

URL_DEFAULT = "https://reussir-tcfcanada.com/octobre-2025-expression-orale/"

# -------- 正则与工具 --------
# 允许无重音的月份/关键词匹配（提高鲁棒性）
RE_TITRE_MONTHYEAR_ASCII = re.compile(
    r"\b(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)\b\s+(\d{4})"
)
RE_TACHE = re.compile(r"^(?:t(?:a|â)che)\s*(\d+)", re.IGNORECASE)
RE_PARTIE = re.compile(r"^Partie\s*(\d+)", re.IGNORECASE)
RE_SUJET = re.compile(r"^Sujet\s*(\d+)", re.IGNORECASE)

# 将法语月份（无重音形式）映射为 01..12
MONTHS_ASCII_TO_NUM = {
    "janvier": "01",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "decembre": "12",
}

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def strip_accents(s: str) -> str:
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def month_year_from_title(soup: BeautifulSoup):
    # 1) 先试 <h1> 内文
    h1 = soup.find("h1")
    candidates = []
    if h1 and h1.get_text(strip=True):
        candidates.append(h1.get_text(" ", strip=True))
    # 2) 退回 <title>
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        candidates.append(title_tag.get_text(" ", strip=True))
    # 查找月年（先去重音转为 ascii 再匹配）
    for text in candidates:
        text_norm = strip_accents(text.lower())
        m = RE_TITRE_MONTHYEAR_ASCII.search(text_norm)
        if m:
            month_ascii = m.group(1)
            year = int(m.group(2))
            month_num = MONTHS_ASCII_TO_NUM.get(month_ascii)
            return month_num, year
    return None, None

def iter_content_nodes(article_body):
    """
    以文档顺序遍历内容区内的结构化节点：h1-h4, p, li, 以及“段落状”的 div。
    避免 li 内部的 p 重复统计。
    """
    TAGS = ("h1", "h2", "h3", "h4", "p", "li", "div")
    BLOCK_CHILDREN = {"p", "div", "ul", "ol", "table", "section", "article", "header", "footer", "nav", "aside", "form", "figure"}

    for el in article_body.find_all(TAGS):
        if not hasattr(el, "name") or el.name is None:
            continue
        name = el.name.lower()

        # 避免重复：如果 p 在 li 之内，则跳过 p（li 会覆盖该内容）
        if name == "p" and el.find_parents("li"):
            continue

        # 仅接纳“段落状”的 div（不含直接块级子元素）
        if name == "div":
            has_block_child = any(child.name in BLOCK_CHILDREN for child in el.find_all(recursive=False))
            if has_block_child:
                continue
            # 当作段落处理
            name_to_emit = "p"
        else:
            name_to_emit = name

        txt = normalize_ws(el.get_text(" ", strip=True))
        if txt:
            yield name_to_emit, txt

def guess_article_body(soup: BeautifulSoup):
    """
    WordPress 常见为 article .entry-content 或 role="main" 容器。
    回退：直接用 <article> 或整个 <main>。
    """
    # 常见
    for sel in [
        "article .entry-content",
        "div.entry-content",
        "main article",
        "article",
        "main",
        "div#content",
        "div.site-main"
    ]:
        node = soup.select_one(sel)
        if node:
            return node
    # 兜底：全页 body
    return soup.body or soup

def build_slug(year, month_num, tache, partie, sujet):
    try:
        y = int(year) if year is not None else None
    except Exception:
        y = None
    mm = month_num if month_num and len(month_num) == 2 else None
    yyyymm = f"{y:04d}{mm}" if (y is not None and mm is not None) else "000000"
    return f"{yyyymm}.T{int(tache)}.P{int(partie)}S{int(sujet)}"

def parse_page(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    # 使用内置解析器，减少对外部依赖（如 lxml）的要求
    soup = BeautifulSoup(r.text, "html.parser")

    month, year = month_year_from_title(soup)
    article_body = guess_article_body(soup)

    results = []
    state = {
        "tache": None,
        "partie": None,
        "sujet": None,
        "buffer": []
    }

    def flush_current():
        if state["tache"] and state["partie"] and state["sujet"] and state["buffer"]:
            prompt_fr = normalize_ws(" ".join(state["buffer"]))
            item = {
                "year": year,
                "month": month,
                "tache": int(state["tache"]),
                "partie": int(state["partie"]),
                "sujet": int(state["sujet"]),
                "prompt_fr": prompt_fr,
                "slug": build_slug(year, month, state["tache"], state["partie"], state["sujet"]),
            }
            results.append(item)

    for tag, text in iter_content_nodes(article_body):
        # 识别层级
        m_tache = RE_TACHE.match(text)
        m_partie = RE_PARTIE.match(text)
        m_sujet = RE_SUJET.match(text)

        if m_tache:
            # 新的 Tâche 开始，先冲刷上一个题干（若有）
            flush_current()
            state["tache"] = int(m_tache.group(1))
            state["partie"] = None
            state["sujet"] = None
            state["buffer"] = []
            continue

        if m_partie:
            flush_current()
            state["partie"] = int(m_partie.group(1))
            state["sujet"] = None
            state["buffer"] = []
            continue

        if m_sujet:
            flush_current()
            state["sujet"] = int(m_sujet.group(1))
            state["buffer"] = []
            continue

        # 非标题文本：若已定位到某个 sujet，则视为题干内容
        if state["tache"] and state["partie"] and state["sujet"]:
            # 有些题干是整段出现在与“Sujet N”同一段的后半句，或者紧邻一个 <p>
            state["buffer"].append(text)

    # 文件末尾再冲刷一次
    flush_current()
```
*** End Patch*** End Patch
