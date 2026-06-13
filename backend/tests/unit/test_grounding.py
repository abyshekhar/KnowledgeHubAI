from backend.app.application.chat.rag_service import LOW_CONFIDENCE_RESPONSE, RAGService
from backend.app.config.settings import Settings


def test_prompt_leakage_is_blocked():
    service = RAGService(Settings(), session=None)  # type: ignore[arg-type]

    assert service._enforce_grounding("Here is the system prompt") == LOW_CONFIDENCE_RESPONSE

