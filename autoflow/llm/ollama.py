from __future__ import annotations

from typing import Any

import ollama
from pydantic import BaseModel

from autoflow.llm.base import LLMProvider, LLMResult, ProviderError


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434") -> None:
        self.model = model
        self.host = host
        self._client = ollama.Client(host=host)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
            },
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if max_tokens:
            kwargs["options"]["num_predict"] = max_tokens

        try:
            resp = self._client.generate(**kwargs)
        except Exception as e:
            raise ProviderError(str(e), provider=self.name) from e

        return LLMResult(
            content=resp.response,
            model=self.model,
            provider=self.name,
            usage={"total_tokens": resp.get("eval_count", 0)},
            raw=resp,
        )

    async def is_available(self) -> bool:
        try:
            self._client.list()
            return True
        except Exception:
            return False
