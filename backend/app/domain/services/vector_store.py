from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.domain.entities.document import DocumentChunk


class VectorSearchResult:
    def __init__(self, chunk: DocumentChunk, score: float) -> None:
        self.chunk = chunk
        self.score = score


class VectorStore(ABC):
    @abstractmethod
    def add_documents(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[VectorSearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, document_name: str) -> None:
        raise NotImplementedError

