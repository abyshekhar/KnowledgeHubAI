from backend.app.config.settings import ChunkingSettings
from backend.app.infrastructure.documents.chunking import Chunker
from backend.app.infrastructure.documents.parsers import ParsedPage


def test_recursive_chunking_preserves_metadata():
    chunker = Chunker(ChunkingSettings(chunk_size=10, chunk_overlap=2))
    chunks = chunker.chunk([ParsedPage("abcdefghij12345", page_number=2)], "Policy.pdf", "pdf")

    assert chunks
    assert chunks[0].document_name == "Policy.pdf"
    assert chunks[0].metadata["page_number"] == 2

