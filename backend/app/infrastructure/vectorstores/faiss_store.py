from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from backend.app.domain.entities.document import DocumentChunk
from backend.app.domain.services.vector_store import VectorSearchResult, VectorStore


class FaissVectorStore(VectorStore):
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.path / "chunks.json"
        self.index_path = self.path / "index.faiss"
        self._chunks: list[DocumentChunk] = []
        self._index = None
        self._load()

    def _load(self) -> None:
        if self.metadata_path.exists():
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            self._chunks = [DocumentChunk(**item) for item in raw]
        if self.index_path.exists():
            import faiss

            self._index = faiss.read_index(str(self.index_path))

    def add_documents(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        import faiss

        matrix = np.asarray(embeddings, dtype="float32")
        if self._index is None:
            self._index = faiss.IndexFlatIP(matrix.shape[1])
        self._index.add(matrix)
        self._chunks.extend(chunks)
        faiss.write_index(self._index, str(self.index_path))
        self.metadata_path.write_text(
            json.dumps([chunk.__dict__ for chunk in self._chunks], indent=2),
            encoding="utf-8",
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[VectorSearchResult]:
        if self._index is None or not self._chunks:
            return []
        query = np.asarray([query_embedding], dtype="float32")
        scores, indices = self._index.search(query, top_k)
        results: list[VectorSearchResult] = []
        for score, index in zip(scores[0], indices[0], strict=False):
            if index < 0:
                continue
            chunk = self._chunks[int(index)]
            if filters:
                allowed = True
                for key, value in filters.items():
                    current = str(chunk.metadata.get(key))
                    if isinstance(value, list):
                        allowed = current in {str(item) for item in value}
                    else:
                        allowed = current == str(value)
                    if not allowed:
                        break
                if not allowed:
                    continue
            results.append(VectorSearchResult(chunk, float(score)))
        return results

    def delete_document(self, document_name: str) -> None:
        import faiss

        if self._index is None or not self._chunks:
            return

        keep_indices = []
        keep_chunks = []
        for idx, chunk in enumerate(self._chunks):
            if chunk.document_name != document_name:
                keep_indices.append(idx)
                keep_chunks.append(chunk)

        if not keep_chunks:
            self._chunks = []
            self._index = None
            if self.index_path.exists():
                self.index_path.unlink()
            if self.metadata_path.exists():
                self.metadata_path.unlink()
            return

        vectors = []
        for idx in keep_indices:
            vector = self._index.reconstruct(idx)
            vectors.append(vector)

        matrix = np.asarray(vectors, dtype="float32")
        new_index = faiss.IndexFlatIP(matrix.shape[1])
        new_index.add(matrix)

        self._index = new_index
        self._chunks = keep_chunks

        faiss.write_index(self._index, str(self.index_path))
        self.metadata_path.write_text(
            json.dumps([chunk.__dict__ for chunk in self._chunks], indent=2),
            encoding="utf-8",
        )
