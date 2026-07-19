from __future__ import annotations

import hashlib
import math

from backend.app.config.settings import EmbeddingSettings


class EmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: EmbeddingSettings) -> None:
        self.settings = settings
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.settings.model)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._load().encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class DeterministicOfflineEmbeddingProvider(EmbeddingProvider):
    """Small fallback used for tests or air-gapped demos before model download."""

    def embed_query(self, text: str) -> list[float]:
        values = [0.0] * 384
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % len(values)
            values[index] += 1.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


_providers: dict[tuple[str, str], EmbeddingProvider] = {}


def create_embedding_provider(settings: EmbeddingSettings) -> EmbeddingProvider:
    # Cached as a singleton per (provider, model): HuggingFaceEmbeddingProvider
    # lazy-loads a SentenceTransformer model, which is far too expensive to
    # re-instantiate (and thus reload from disk) on every request.
    key = (settings.provider, settings.model)
    cached = _providers.get(key)
    if cached is not None:
        return cached

    provider: EmbeddingProvider
    if settings.provider == "deterministic":
        provider = DeterministicOfflineEmbeddingProvider()
    else:
        provider = HuggingFaceEmbeddingProvider(settings)

    _providers[key] = provider
    return provider

