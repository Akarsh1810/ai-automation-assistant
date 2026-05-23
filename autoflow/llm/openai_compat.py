from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel

from autoflow.llm.base import LLMProvider, LLMResult, ProviderError


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compat"

    def __init__(
        self,
        model: str = "llama3.2-3b-preview",
        api_base: str = "https://api.groq.com/openai/v1",
        api_key: str = "",
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResult:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens

        if schema:
            body["response_format"] = {
                "type": "json_object",
            }

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        f"{self.api_base}/chat/completions",
                        json=body,
                        headers=headers,
                    )
                    if resp.status_code == 429 and attempt < self.max_retries - 1:
                        import asyncio

                        await asyncio.sleep(2**attempt)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.HTTPStatusError as e:
                last_error = ProviderError(
                    f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                    provider=self.name,
                    status_code=e.response.status_code,
                )
                if attempt < self.max_retries - 1:
                    import asyncio

                    await asyncio.sleep(2**attempt)
                    continue
                raise last_error from e
            except Exception as e:
                last_error = ProviderError(str(e), provider=self.name)
                if attempt < self.max_retries - 1:
                    import asyncio

                    await asyncio.sleep(2**attempt)
                    continue
                raise last_error from e

            choice = data["choices"][0]
            content = choice["message"]["content"]

            if schema and content:
                try:
                    parsed = json.loads(content)
                    content = schema(**parsed).model_dump_json()
                except (json.JSONDecodeError, ValueError):
                    pass

            return LLMResult(
                content=content,
                model=data["model"] or self.model,
                provider=self.name,
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
                raw=data,
            )

        if last_error:
            raise ProviderError(f"Max retries exceeded: {last_error}", provider=self.name)
        raise ProviderError("Unknown error", provider=self.name)

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.api_base}/models")
                return resp.status_code == 200
        except Exception:
            return False
