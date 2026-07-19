from __future__ import annotations

from backend.app.config.settings import VectorStoreSettings
from backend.app.domain.services.vector_store import VectorStore
from backend.app.infrastructure.vectorstores.faiss_store import FaissVectorStore
from backend.app.infrastructure.vectorstores.qdrant_store import QdrantVectorStore

_stores: dict[tuple[str, str], VectorStore] = {}


def create_vector_store(settings: VectorStoreSettings) -> VectorStore:
    # Cached as a singleton per (provider, path): FaissVectorStore loads its
    # full index + chunk metadata from disk in __init__, which is expensive to
    # repeat on every request. Reusing the instance also means add/delete
    # calls mutate the same in-memory index that queries read from.
    key = (settings.provider, settings.path)
    cached = _stores.get(key)
    if cached is not None:
        return cached

    if settings.provider == "faiss":
        store: VectorStore = FaissVectorStore(settings.path)
    elif settings.provider == "qdrant":
        store = QdrantVectorStore()
    else:
        raise ValueError(f"Unsupported vector store provider: {settings.provider}")

    _stores[key] = store
    return store

