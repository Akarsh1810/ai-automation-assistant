from __future__ import annotations

from autoflow.llm.base import LLMProvider
from autoflow.tools.base import Tool, ToolSpec


class LLMCallTool(Tool):
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="llm_call",
            description="Make an LLM call with a prompt",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The prompt to send"},
                    "system_prompt": {"type": "string", "description": "Optional system prompt"},
                    "temperature": {"type": "number", "description": "Temperature (0-2)"},
                },
                "required": ["prompt"],
            },
        )

    async def run(self, prompt: str, system_prompt: str | None = None, temperature: float = 0.7) -> str:
        result = await self._provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        return result.content
