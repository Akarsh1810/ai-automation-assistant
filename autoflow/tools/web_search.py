from __future__ import annotations

from autoflow.tools.base import Tool, ToolSpec


class WebSearchTool(Tool):
    def __init__(self, max_results: int = 5) -> None:
        self.max_results = max_results

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_search",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        )

    async def run(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for i, r in enumerate(ddgs.text(query, max_results=self.max_results)):
                    results.append(f"{i + 1}. {r['title']}\n   {r['href']}\n   {r['body']}")
            if not results:
                return "No results found."
            return "\n\n".join(results)
        except ImportError:
            return "Web search requires duckduckgo_search: pip install duckduckgo_search"
        except Exception as e:
            return f"Search failed: {e}"
