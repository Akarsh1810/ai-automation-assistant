from autoflow.llm.base import LLMProvider
from autoflow.tools.base import Tool, ToolRegistry, ToolSpec
from autoflow.tools.code_exec import CodeExecTool, ShellCommandTool
from autoflow.tools.file_ops import FileReadTool, FileWriteTool
from autoflow.tools.llm_tool import LLMCallTool
from autoflow.tools.web_search import WebSearchTool


def register_default_tools(registry: ToolRegistry, llm_provider: LLMProvider) -> None:
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(WebSearchTool())
    registry.register(LLMCallTool(llm_provider))
    registry.register(CodeExecTool())
    registry.register(ShellCommandTool())


__all__ = [
    "Tool",
    "ToolRegistry",
    "ToolSpec",
    "FileReadTool",
    "FileWriteTool",
    "WebSearchTool",
    "LLMCallTool",
    "CodeExecTool",
    "ShellCommandTool",
    "register_default_tools",
]
