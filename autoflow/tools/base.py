from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class Tool(ABC):
    @property
    @abstractmethod
    def spec(self) -> ToolSpec: ...

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]
