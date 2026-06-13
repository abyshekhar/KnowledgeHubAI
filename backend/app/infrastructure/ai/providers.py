from __future__ import annotations

import httpx

from backend.app.config.settings import LLMSettings
from backend.app.domain.services.llm_provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.base_url}/api/generate",
                json={
                    "model": self.settings.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": self.settings.temperature},
                },
            )
            response.raise_for_status()
            return response.json().get("response", "")


class TransformersProvider(LLMProvider):
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def generate(self, prompt: str) -> str:
        raise RuntimeError(
            "TransformersProvider is configured but not loaded. "
            "Install a local text-generation model adapter for this deployment."
        )


def create_llm_provider(settings: LLMSettings) -> LLMProvider:
    if settings.provider == "ollama":
        return OllamaProvider(settings)
    if settings.provider == "transformers":
        return TransformersProvider(settings)
    raise ValueError(f"Unsupported LLM provider: {settings.provider}")

