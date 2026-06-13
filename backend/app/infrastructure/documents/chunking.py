from __future__ import annotations

from backend.app.config.settings import ChunkingSettings
from backend.app.domain.entities.document import DocumentChunk
from backend.app.infrastructure.documents.parsers import ParsedPage


class Chunker:
    def __init__(self, settings: ChunkingSettings) -> None:
        self.settings = settings

    def chunk(self, pages: list[ParsedPage], document_name: str, document_type: str) -> list[DocumentChunk]:
        if self.settings.strategy == "section":
            return self._section_aware(pages, document_name, document_type)
        return self._recursive(pages, document_name, document_type)

    def _recursive(
        self,
        pages: list[ParsedPage],
        document_name: str,
        document_type: str,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        step = max(1, self.settings.chunk_size - self.settings.chunk_overlap)
        for page in pages:
            text = page.text
            for start in range(0, len(text), step):
                part = text[start : start + self.settings.chunk_size].strip()
                if not part:
                    continue
                chunks.append(
                    DocumentChunk(
                        text=part,
                        document_name=document_name,
                        document_type=document_type,
                        page_number=page.page_number,
                        section=page.section,
                        metadata={
                            "document_name": document_name,
                            "page_number": page.page_number,
                            "section": page.section,
                            "document_type": document_type,
                        },
                    )
                )
        return chunks

    def _section_aware(
        self,
        pages: list[ParsedPage],
        document_name: str,
        document_type: str,
    ) -> list[DocumentChunk]:
        return self._recursive(pages, document_name, document_type)

