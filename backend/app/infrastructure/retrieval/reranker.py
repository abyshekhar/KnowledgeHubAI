from __future__ import annotations

import logging
from backend.app.config.settings import RerankerSettings
from backend.app.domain.services.vector_store import VectorSearchResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(self, settings: RerankerSettings) -> None:
        self.settings = settings
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.settings.model)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[VectorSearchResult],
    ) -> list[VectorSearchResult]:
        if not results:
            return []
        if not self.settings.enabled:
            return results

        try:
            model = self._load()
            pairs = [[query, res.chunk.text] for res in results]
            scores = model.predict(pairs)
            
            reranked = []
            for res, score in zip(results, scores, strict=False):
                reranked.append(VectorSearchResult(res.chunk, float(score)))
            
            return sorted(reranked, key=lambda x: x.score, reverse=True)
        except Exception as e:
            logger.warning("Reranking failed (fallback to original results): %s", e)
            return results
