from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.chat.access import allowed_access_levels
from backend.app.config.settings import Settings
from backend.app.domain.services.vector_store import VectorSearchResult
from backend.app.infrastructure.database.models import Document, TestClarifyingQuestion, User
from backend.app.infrastructure.documents.cleaning import clean_pages
from backend.app.infrastructure.documents.parsers import DocumentParser
from backend.app.infrastructure.embeddings.providers import create_embedding_provider
from backend.app.infrastructure.retrieval.hybrid import HybridRetriever
from backend.app.infrastructure.vectorstores.factory import create_vector_store


def requirement_text(document: Document) -> str:
    if document.document_type == "link":
        raise ValueError("Web links are not supported as requirement documents yet.")
    pages = DocumentParser().parse(Path(document.path))
    cleaned = clean_pages([page.text for page in pages])
    text = "\n\n".join(part for part in cleaned if part.strip())
    if not text.strip():
        raise ValueError("No readable text could be extracted from this document.")
    return text


async def gather_context(
    settings: Settings,
    session: AsyncSession,
    text: str,
    user: User,
    category: str | None,
    exclude_document_name: str,
) -> list[VectorSearchResult]:
    embeddings = create_embedding_provider(settings.embeddings)
    vector_store = create_vector_store(settings.vector_store)
    query_vector = embeddings.embed_query(text)
    role_name = user.role.name if user.role else "user"
    retriever = HybridRetriever(settings, session, vector_store)
    top_k = settings.test_generation.context_top_k
    results = await retriever.retrieve(
        text,
        query_vector,
        top_k=top_k * 2,
        allowed_levels=allowed_access_levels(role_name),
        category=category,
    )
    # The requirement doc itself is indexed like any other KB document, so
    # exclude it from its own supplementary context.
    return [item for item in results if item.chunk.document_name != exclude_document_name][:top_k]


def format_context(results: list[VectorSearchResult]) -> str:
    if not results:
        return "(no related knowledge base content found)"
    return "\n\n".join(f"[{item.chunk.document_name}] {item.chunk.text}" for item in results)


def format_qa(qa_pairs: list[TestClarifyingQuestion]) -> str:
    if not qa_pairs:
        return "(none yet)"
    lines = []
    for question in qa_pairs:
        answer = question.answer if question.status == "answered" else "(skipped by user)"
        lines.append(f"Q: {question.question}\nA: {answer}")
    return "\n\n".join(lines)
