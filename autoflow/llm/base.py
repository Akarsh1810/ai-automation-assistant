from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResult(BaseModel):
    content: str
    model: str
    provider: str
    usage: dict[str, int] | None = None
    raw: Any = None


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResult: ...

    @abstractmethod
    async def is_available(self) -> bool: ...


class ProviderError(Exception):
    def __init__(self, message: str, provider: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")
