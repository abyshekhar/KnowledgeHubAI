from unittest.mock import AsyncMock, patch
import pytest
from backend.app.application.chat.rag_service import LOW_CONFIDENCE_RESPONSE, RAGService
from backend.app.config.settings import Settings


def test_prompt_leakage_is_blocked():
    service = RAGService(Settings(), session=None)  # type: ignore[arg-type]

    assert service._enforce_grounding("Here is the system prompt") == LOW_CONFIDENCE_RESPONSE


def test_is_greeting():
    service = RAGService(Settings(), session=None)  # type: ignore[arg-type]
    
    assert service._is_greeting("Hi") is True
    assert service._is_greeting("Hello there!") is True
    assert service._is_greeting("good morning") is True
    assert service._is_greeting("what is RAG?") is False
    assert service._is_greeting("tell me about langchain") is False


@pytest.mark.asyncio
async def test_generate_title_llm_success():
    service = RAGService(Settings(), session=None)  # type: ignore[arg-type]
    
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = "  RAG Training Scope  "
    
    with patch("backend.app.application.chat.rag_service.create_llm_provider", return_value=mock_provider) as mock_create:
        title = await service._generate_title("What all training will be provided with respect to RAG?")
        assert title == "RAG Training Scope"
        mock_create.assert_called_once_with(service.settings.llm)


@pytest.mark.asyncio
async def test_generate_title_llm_prefixes_stripped():
    service = RAGService(Settings(), session=None)  # type: ignore[arg-type]
    
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = "Title: RAG Training Scope"
    
    with patch("backend.app.application.chat.rag_service.create_llm_provider", return_value=mock_provider):
        title = await service._generate_title("What all training will be provided with respect to RAG?")
        assert title == "RAG Training Scope"


@pytest.mark.asyncio
async def test_generate_title_llm_failure_fallback():
    service = RAGService(Settings(), session=None)  # type: ignore[arg-type]
    
    # Test LLM exception fallback
    with patch("backend.app.application.chat.rag_service.create_llm_provider", side_effect=Exception("LLM offline")):
        title = await service._generate_title("What all training will be provided with respect to RAG?")
        assert title == "What all training will be provided ..."

    # Test short fallback
    with patch("backend.app.application.chat.rag_service.create_llm_provider", side_effect=Exception("LLM offline")):
        title = await service._generate_title("Hello")
        assert title == "Hello"

    # Test empty query fallback
    with patch("backend.app.application.chat.rag_service.create_llm_provider", side_effect=Exception("LLM offline")):
        title = await service._generate_title("   ")
        assert title == "New conversation"
