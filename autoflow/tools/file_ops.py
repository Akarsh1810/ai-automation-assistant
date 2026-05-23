from __future__ import annotations

from pathlib import Path

from autoflow.tools.base import Tool, ToolSpec


class FileReadTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_read",
            description="Read contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                },
                "required": ["path"],
            },
        )

    async def run(self, path: str) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"File not found: {path}"
        return p.read_text(encoding="utf-8")


class FileWriteTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="file_write",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        )

    async def run(self, path: str, content: str) -> str:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"
