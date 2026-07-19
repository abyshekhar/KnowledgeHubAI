from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, model: str | None = None) -> str:
        raise NotImplementedError

    async def check_health(self) -> bool:
        """Whether the underlying model runtime is reachable. Providers that
        have nothing to ping (e.g. an in-process model) can leave this as-is."""
        return True

    async def list_models(self) -> list[str]:
        """Locally available model names, if the provider supports more than
        one. Providers without a concept of multiple models return []."""
        return []

