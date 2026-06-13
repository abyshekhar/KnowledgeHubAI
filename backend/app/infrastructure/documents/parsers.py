from __future__ import annotations

from pathlib import Path

import fitz
from docx import Document as DocxDocument
from markdown_it import MarkdownIt


class ParsedPage:
    def __init__(self, text: str, page_number: int | None = None, section: str | None = None) -> None:
        self.text = text
        self.page_number = page_number
        self.section = section


class DocumentParser:
    def parse(self, path: Path) -> list[ParsedPage]:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(path)
        if suffix == ".docx":
            return self._parse_docx(path)
        if suffix == ".md":
            return self._parse_markdown(path)
        if suffix == ".txt":
            return [ParsedPage(path.read_text(encoding="utf-8", errors="ignore"))]
        raise ValueError(f"Unsupported document type: {suffix}")

    def _parse_pdf(self, path: Path) -> list[ParsedPage]:
        doc = fitz.open(path)
        return [ParsedPage(page.get_text(), page_number=index + 1) for index, page in enumerate(doc)]

    def _parse_docx(self, path: Path) -> list[ParsedPage]:
        doc = DocxDocument(path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        return [ParsedPage(text)]

    def _parse_markdown(self, path: Path) -> list[ParsedPage]:
        markdown = path.read_text(encoding="utf-8", errors="ignore")
        tokens = MarkdownIt().parse(markdown)
        headings = [token.content for token in tokens if token.type == "inline" and token.content]
        section = headings[0] if headings else None
        return [ParsedPage(markdown, section=section)]

