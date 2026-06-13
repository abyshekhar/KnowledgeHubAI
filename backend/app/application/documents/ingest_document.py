from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings
from backend.app.infrastructure.database.models import Chunk, Document
from backend.app.infrastructure.documents.chunking import Chunker
from backend.app.infrastructure.documents.cleaning import clean_pages
from backend.app.infrastructure.documents.parsers import DocumentParser, ParsedPage
from backend.app.infrastructure.embeddings.providers import create_embedding_provider
from backend.app.infrastructure.vectorstores.factory import create_vector_store


class IngestDocumentUseCase:
    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self.settings = settings
        self.session = session

    async def execute(self, document: Document) -> None:
        parser = DocumentParser()
        parsed = parser.parse(Path(document.path))
        cleaned_text = clean_pages([page.text for page in parsed])
        cleaned_pages = [
            ParsedPage(text=text, page_number=page.page_number, section=page.section)
            for text, page in zip(cleaned_text, parsed, strict=False)
        ]
        chunks = Chunker(self.settings.chunking).chunk(
            cleaned_pages,
            document.name,
            document.document_type,
        )
        chunks = [
            type(chunk)(
                text=chunk.text,
                document_name=chunk.document_name,
                document_type=chunk.document_type,
                page_number=chunk.page_number,
                section=chunk.section,
                metadata={
                    **chunk.metadata,
                    "access_level": document.access_level,
                    "category": document.category,
                    "uploaded_by": str(document.uploaded_by_id or ""),
                    "uploaded_date": str(document.created_at or ""),
                },
            )
            for chunk in chunks
        ]
        embedding_provider = create_embedding_provider(self.settings.embeddings)
        embeddings = embedding_provider.embed_documents([chunk.text for chunk in chunks])
        vector_store = create_vector_store(self.settings.vector_store)
        vector_store.add_documents(chunks, embeddings)

        for index, chunk in enumerate(chunks):
            self.session.add(
                Chunk(
                    document_id=document.id,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    vector_id=f"{document.id}:{index}",
                    metadata_json=json.dumps(chunk.metadata),
                )
            )
        document.status = "indexed"
        await self.session.commit()
