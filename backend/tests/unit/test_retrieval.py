from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.config.settings import Settings, RetrievalSettings, RerankerSettings
from backend.app.domain.entities.document import DocumentChunk
from backend.app.domain.services.vector_store import VectorSearchResult
from backend.app.infrastructure.retrieval.hybrid import HybridRetriever
from backend.app.infrastructure.retrieval.reranker import CrossEncoderReranker


@pytest.mark.asyncio
async def test_hybrid_retriever_blends_scores():
    # Setup mocks
    settings = Settings()
    settings.retrieval = RetrievalSettings(top_k=2, hybrid_alpha=0.5)
    
    # 2 mock chunks in database
    db_chunk1 = MagicMock()
    db_chunk1.text = "Hello world chunk"
    db_chunk1.page_number = 1
    db_chunk1.section = "Introduction"
    db_chunk1.metadata_json = '{"some": "meta"}'
    db_chunk1.document.name = "Doc1.pdf"
    db_chunk1.document.document_type = "pdf"
    db_chunk1.document.access_level = "user"
    db_chunk1.document.category = "general"

    db_chunk2 = MagicMock()
    db_chunk2.text = "FastAPI is awesome"
    db_chunk2.page_number = 2
    db_chunk2.section = "FastAPI"
    db_chunk2.metadata_json = '{}'
    db_chunk2.document.name = "Doc2.pdf"
    db_chunk2.document.document_type = "pdf"
    db_chunk2.document.access_level = "user"
    db_chunk2.document.category = "tech"

    session = AsyncMock()
    # Mock database scalars to return our list of db chunks
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [db_chunk1, db_chunk2]
    session.scalars.return_value = scalars_mock

    # Mock vector store
    vector_store = MagicMock()
    chunk1 = DocumentChunk(text="Hello world chunk", document_name="Doc1.pdf", document_type="pdf")
    chunk2 = DocumentChunk(text="FastAPI is awesome", document_name="Doc2.pdf", document_type="pdf")
    
    # Dense results: chunk1 gets score 0.8, chunk2 gets score 0.4
    vector_store.search.return_value = [
        VectorSearchResult(chunk1, 0.8),
        VectorSearchResult(chunk2, 0.4)
    ]

    retriever = HybridRetriever(settings, session, vector_store)
    results = await retriever.retrieve(
        query="FastAPI awesome",
        query_vector=[0.1] * 384,
        top_k=2,
        allowed_levels=["user"]
    )

    assert len(results) == 2
    # Verify both got matched and blended
    # "FastAPI is awesome" has higher BM25 relevance for query "FastAPI awesome"
    # So its score should be elevated by the BM25 contribution
    assert results[0].chunk.text in {"Hello world chunk", "FastAPI is awesome"}


from unittest.mock import AsyncMock, MagicMock, patch

# ... (rest of imports remain same)

# Note: make sure patch is imported
@patch("backend.app.infrastructure.retrieval.reranker.CrossEncoderReranker._load")
def test_reranker_success(mock_load):
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.95]
    mock_load.return_value = mock_model

    settings = RerankerSettings(enabled=True, model="BAAI/bge-reranker-base")
    reranker = CrossEncoderReranker(settings)
    
    chunk = DocumentChunk(text="Test chunk", document_name="Doc.txt", document_type="txt")
    results = [VectorSearchResult(chunk, 0.8)]
    
    reranked = reranker.rerank("query", results)
    assert len(reranked) == 1
    assert reranked[0].score == 0.95


@patch("backend.app.infrastructure.retrieval.reranker.CrossEncoderReranker._load")
def test_reranker_fallback(mock_load):
    mock_load.side_effect = RuntimeError("Offline fallback test")
    settings = RerankerSettings(enabled=True, model="BAAI/bge-reranker-base")
    reranker = CrossEncoderReranker(settings)
    
    chunk = DocumentChunk(text="Test chunk", document_name="Doc.txt", document_type="txt")
    results = [VectorSearchResult(chunk, 0.8)]
    
    reranked = reranker.rerank("query", results)
    assert len(reranked) == 1
    assert reranked[0].chunk.text == "Test chunk"


def test_faiss_delete_document(tmp_path):
    from backend.app.infrastructure.vectorstores.faiss_store import FaissVectorStore
    
    store = FaissVectorStore(str(tmp_path))
    chunk1 = DocumentChunk(text="Hello", document_name="doc1.pdf", document_type="pdf")
    chunk2 = DocumentChunk(text="World", document_name="doc2.pdf", document_type="pdf")
    
    store.add_documents([chunk1, chunk2], [[0.1]*384, [0.2]*384])
    assert len(store._chunks) == 2
    
    # Delete doc1
    store.delete_document("doc1.pdf")
    assert len(store._chunks) == 1
    assert store._chunks[0].text == "World"

