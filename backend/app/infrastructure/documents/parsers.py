from __future__ import annotations

from html.parser import HTMLParser
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
        if suffix == ".csv":
            return self._parse_csv(path)
        raise ValueError(f"Unsupported document type: {suffix}")

    def _parse_csv(self, path: Path) -> list[ParsedPage]:
        import csv
        pages = []
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            for index, row in enumerate(reader):
                row_parts = []
                for header in headers:
                    val = row.get(header)
                    if val is not None:
                        row_parts.append(f"{header}: {val}")
                row_text = ", ".join(row_parts)
                pages.append(ParsedPage(row_text, page_number=index + 1))
        return pages

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


class WebHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.ignored_depth = 0
        self.ignored_tags = {"script", "style", "nav", "header", "footer", "aside", "form", "head", "iframe"}
        self.block_tags = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br"}
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True
        elif tag.lower() in self.ignored_tags:
            self.ignored_depth += 1
        elif self.ignored_depth == 0:
            if tag.lower() in self.block_tags:
                self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False
        elif tag.lower() in self.ignored_tags:
            self.ignored_depth = max(0, self.ignored_depth - 1)
        elif self.ignored_depth == 0:
            if tag.lower() in self.block_tags:
                self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data
        elif self.ignored_depth == 0:
            self.text_parts.append(data)

    def get_text(self) -> str:
        raw_text = "".join(self.text_parts)
        lines = [line.strip() for line in raw_text.splitlines()]
        return "\n".join(line for line in lines if line)


