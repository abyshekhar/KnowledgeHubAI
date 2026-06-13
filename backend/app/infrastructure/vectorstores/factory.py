from __future__ import annotations

from backend.app.config.settings import VectorStoreSettings
from backend.app.domain.services.vector_store import VectorStore
from backend.app.infrastructure.vectorstores.faiss_store import FaissVectorStore
from backend.app.infrastructure.vectorstores.qdrant_store import QdrantVectorStore


def create_vector_store(settings: VectorStoreSettings) -> VectorStore:
    if settings.provider == "faiss":
        return FaissVectorStore(settings.path)
    if settings.provider == "qdrant":
        return QdrantVectorStore()
    raise ValueError(f"Unsupported vector store provider: {settings.provider}")

