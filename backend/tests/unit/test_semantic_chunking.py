from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.app.config.settings import ChunkingSettings
from backend.app.infrastructure.documents.chunking import Chunker
from backend.app.infrastructure.documents.parsers import ParsedPage


@patch("backend.app.infrastructure.documents.chunking.create_embedding_provider")
@patch("backend.app.infrastructure.documents.chunking.load_settings")
def test_semantic_chunking_groups_sentences(mock_load_settings, mock_create_provider):
    # Setup mocks
    settings_mock = MagicMock()
    mock_load_settings.return_value = settings_mock
    
    # Mock embedding provider to return specific embeddings
    provider_mock = MagicMock()
    # 3 sentences:
    # 1. "FastAPI is a modern web framework."
    # 2. "It is built on top of Starlette." (highly similar/related)
    # 3. "Bananas are delicious yellow fruits." (dissimilar)
    # Let's mock embedding values such that:
    # dot_product(1, 2) is high (e.g. 0.9)
    # dot_product(2, 3) is low (e.g. 0.1)
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [0.9, 0.43, 0.0]
    emb3 = [0.0, 0.0, 1.0]
    provider_mock.embed_documents.return_value = [emb1, emb2, emb3]
    mock_create_provider.return_value = provider_mock

    chunker = Chunker(ChunkingSettings(strategy="semantic", chunk_size=500, chunk_overlap=50))
    page = ParsedPage(
        text="FastAPI is a modern web framework. It is built on top of Starlette. Bananas are delicious yellow fruits.",
        page_number=1,
        section="Intro"
    )

    chunks = chunker.chunk([page], "Python.pdf", "pdf")
    
    # We expect 2 chunks:
    # Chunk 1: "FastAPI is a modern web framework. It is built on top of Starlette."
    # Chunk 2: "Bananas are delicious yellow fruits."
    assert len(chunks) == 2
    assert "Starlette" in chunks[0].text
    assert "Bananas" in chunks[1].text
    assert chunks[0].metadata["page_number"] == 1
    assert chunks[1].metadata["section"] == "Intro"
