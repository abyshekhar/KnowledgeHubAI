from __future__ import annotations

import re
import unicodedata
from collections import Counter


def clean_pages(pages: list[str]) -> list[str]:
    normalized = [_normalize(page) for page in pages]
    repeated = _repeated_lines(normalized)
    cleaned: list[str] = []
    for page in normalized:
        lines = []
        for line in page.splitlines():
            stripped = line.strip()
            if not stripped or stripped in repeated or re.fullmatch(r"\d+", stripped):
                continue
            lines.append(stripped)
        cleaned.append("\n".join(lines))
    return cleaned


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _repeated_lines(pages: list[str]) -> set[str]:
    counter: Counter[str] = Counter()
    for page in pages:
        counter.update({line.strip() for line in page.splitlines() if line.strip()})
    threshold = max(3, len(pages) // 2)
    return {line for line, count in counter.items() if count >= threshold and len(line) < 120}

