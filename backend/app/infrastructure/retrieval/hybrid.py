from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings
from backend.app.domain.entities.document import DocumentChunk
from backend.app.domain.services.vector_store import VectorSearchResult, VectorStore
from backend.app.infrastructure.database.models import Chunk, Document


class HybridRetriever:
    def __init__(self, settings: Settings, session: AsyncSession, vector_store: VectorStore) -> None:
        self.settings = settings
        self.session = session
        self.vector_store = vector_store

    def _tokenize(self, text: str) -> list[str]:
        # Simple whitespace tokenization for keyword match
        return [word.strip(",.?!()[]{}'\"").lower() for word in text.split() if word.strip()]

    async def retrieve(
        self,
        query: str,
        query_vector: list[float],
        top_k: int,
        allowed_levels: list[str],
        category: str | None = None,
    ) -> list[VectorSearchResult]:
        # 1. Dense vector search
        dense_filters = {"access_level": allowed_levels}
        if category and category.lower() != "all":
            dense_filters["category"] = category

        dense_results = self.vector_store.search(
            query_vector,
            top_k=top_k * 2,  # Retrieve more candidates for blending
            filters=dense_filters,
        )

        # 2. Sparse BM25 keyword search
        # Query chunks with access control filter directly in SQL
        stmt = (
            select(Chunk)
            .join(Chunk.document)
            .where(Document.access_level.in_(allowed_levels))
        )
        if category and category.lower() != "all":
            stmt = stmt.where(Document.category == category)
        stmt = stmt.options(selectinload(Chunk.document))

        result = await self.session.scalars(stmt)
        db_chunks = result.all()

        if not db_chunks:
            return dense_results[:top_k]

        # Convert DB chunks to domain chunks
        all_chunks: list[DocumentChunk] = []
        for db_chunk in db_chunks:
            try:
                metadata = json.loads(db_chunk.metadata_json)
            except Exception:
                metadata = {}
            doc = db_chunk.document
            all_chunks.append(
                DocumentChunk(
                    text=db_chunk.text,
                    document_name=doc.name,
                    document_type=doc.document_type,
                    page_number=db_chunk.page_number,
                    section=db_chunk.section,
                    metadata={
                        **metadata,
                        "access_level": doc.access_level,
                        "category": doc.category,
                    },
                )
            )

        from rank_bm25 import BM25Okapi

        # Tokenize corpus for BM25
        tokenized_corpus = [self._tokenize(chunk.text) for chunk in all_chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        query_tokens = self._tokenize(query)
        bm25_scores = bm25.get_scores(query_tokens)

        # Max score for BM25 normalization
        max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 0.0
        if max_bm25 == 0.0:
            max_bm25 = 1.0

        # Create maps for fast lookup
        dense_map = {res.chunk.text: res.score for res in dense_results}
        
        # Deduplicate and build quick lookup map
        chunk_map: dict[str, DocumentChunk] = {}
        for chunk in all_chunks:
            if chunk.text not in chunk_map:
                chunk_map[chunk.text] = chunk

        # Calculate hybrid scores
        hybrid_candidates: dict[str, float] = {}

        # Add all dense candidates
        for res in dense_results:
            text = res.chunk.text
            dense_score = res.score
            # Find BM25 score
            sparse_score = 0.0
            if text in chunk_map:
                try:
                    idx = all_chunks.index(chunk_map[text])
                    sparse_score = float(bm25_scores[idx]) / max_bm25
                except ValueError:
                    pass

            score = (
                self.settings.retrieval.hybrid_alpha * dense_score
                + (1.0 - self.settings.retrieval.hybrid_alpha) * sparse_score
            )
            hybrid_candidates[text] = score

        # Add top BM25 candidates that weren't in dense search
        sorted_bm25_indices = sorted(
            range(len(bm25_scores)), key=lambda k: bm25_scores[k], reverse=True
        )[: top_k * 2]

        for idx in sorted_bm25_indices:
            chunk = all_chunks[idx]
            text = chunk.text
            if text not in hybrid_candidates:
                sparse_score = float(bm25_scores[idx]) / max_bm25
                dense_score = dense_map.get(text, 0.0)
                score = (
                    self.settings.retrieval.hybrid_alpha * dense_score
                    + (1.0 - self.settings.retrieval.hybrid_alpha) * sparse_score
                )
                hybrid_candidates[text] = score

        # Sort and return top_k
        sorted_results = sorted(hybrid_candidates.items(), key=lambda item: item[1], reverse=True)
        
        final_results: list[VectorSearchResult] = []
        for text, score in sorted_results[:top_k]:
            chunk = chunk_map.get(text)
            if chunk:
                final_results.append(VectorSearchResult(chunk, score))

        return final_results
