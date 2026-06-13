from __future__ import annotations

from backend.app.domain.entities.document import DocumentChunk
from backend.app.domain.services.vector_store import VectorSearchResult, VectorStore


class QdrantVectorStore(VectorStore):
    def add_documents(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        raise RuntimeError("Qdrant support requires an external local Qdrant deployment.")

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[VectorSearchResult]:
        raise RuntimeError("Qdrant support requires an external local Qdrant deployment.")

