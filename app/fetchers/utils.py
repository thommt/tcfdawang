from __future__ import annotations

import hashlib


def hash_domain(domain: str) -> str:
    normalized = (domain or "").strip().lower()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def domain_suffixes(hostname: str):
    normalized = (hostname or "").strip().lower()
    if not normalized:
        return []
    parts = normalized.split(".")
    suffixes = [".".join(parts[i:]) for i in range(len(parts))]
    return [suffix for suffix in suffixes if suffix]
