from __future__ import annotations

from backend.app.config.settings import ChunkingSettings, load_settings
from backend.app.domain.entities.document import DocumentChunk
from backend.app.infrastructure.documents.parsers import ParsedPage
from backend.app.infrastructure.embeddings.providers import create_embedding_provider


class Chunker:
    def __init__(self, settings: ChunkingSettings) -> None:
        self.settings = settings

    def chunk(self, pages: list[ParsedPage], document_name: str, document_type: str) -> list[DocumentChunk]:
        if self.settings.strategy == "section":
            return self._section_aware(pages, document_name, document_type)
        if self.settings.strategy == "semantic":
            return self._semantic(pages, document_name, document_type)
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
        import re
        chunks: list[DocumentChunk] = []

        for page in pages:
            parts = re.split(r'(^#+\s+.*$)', page.text, flags=re.MULTILINE)
            if len(parts) <= 1:
                chunks.extend(self._recursive([page], document_name, document_type))
                continue

            current_section = page.section or "Introduction"
            first_text = parts[0].strip()
            if first_text:
                temp_page = ParsedPage(text=first_text, page_number=page.page_number, section=current_section)
                chunks.extend(self._recursive([temp_page], document_name, document_type))

            for i in range(1, len(parts), 2):
                heading = parts[i].strip()
                content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                current_section = heading.lstrip('#').strip()
                if content:
                    full_text = f"{heading}\n{content}"
                    temp_page = ParsedPage(text=full_text, page_number=page.page_number, section=current_section)
                    chunks.extend(self._recursive([temp_page], document_name, document_type))

        return chunks

    def _semantic(
        self,
        pages: list[ParsedPage],
        document_name: str,
        document_type: str,
    ) -> list[DocumentChunk]:
        try:
            settings = load_settings()
            embedding_provider = create_embedding_provider(settings.embeddings)
        except Exception:
            return self._recursive(pages, document_name, document_type)

        import re
        chunks: list[DocumentChunk] = []
        similarity_threshold = 0.6

        for page in pages:
            sentences = re.split(r'(?<=[.?!])\s+', page.text)
            sentences = [s.strip() for s in sentences if s.strip()]
            if not sentences:
                continue

            try:
                embeddings = embedding_provider.embed_documents(sentences)
            except Exception:
                page_chunks = self._recursive([page], document_name, document_type)
                chunks.extend(page_chunks)
                continue

            current_group: list[str] = [sentences[0]]
            current_len = len(sentences[0])

            for i in range(1, len(sentences)):
                sentence = sentences[i]
                emb1 = embeddings[i - 1]
                emb2 = embeddings[i]
                dot_product = sum(x * y for x, y in zip(emb1, emb2))
                too_long = current_len + len(sentence) + 1 > self.settings.chunk_size
                dissimilar = dot_product < similarity_threshold

                if too_long or dissimilar:
                    chunk_text = " ".join(current_group)
                    chunks.append(
                        DocumentChunk(
                            text=chunk_text,
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
                    current_group = [sentence]
                    current_len = len(sentence)
                else:
                    current_group.append(sentence)
                    current_len += len(sentence) + 1

            if current_group:
                chunk_text = " ".join(current_group)
                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
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

