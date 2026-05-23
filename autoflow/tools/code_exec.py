from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from autoflow.tools.base import Tool, ToolSpec


class CodeExecTool(Tool):
    def __init__(self, workdir: str | None = None) -> None:
        self.workdir = Path(workdir).resolve() if workdir else Path.cwd()

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="code_exec",
            description="Execute Python or shell code",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to execute"},
                    "language": {
                        "type": "string",
                        "description": "Language: python or shell",
                        "enum": ["python", "shell"],
                    },
                },
                "required": ["code", "language"],
            },
        )

    async def run(self, code: str, language: str = "python") -> str:
        if language == "python":
            return await self._exec_python(code)
        elif language == "shell":
            return await self._exec_shell(code)
        return f"Unsupported language: {language}"

    async def _exec_python(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workdir),
            )
            output = result.stdout or ""
            if result.returncode != 0:
                output += f"\nExit code: {result.returncode}\nStderr: {result.stderr}"
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return "Execution timed out (30s)"
        except Exception as e:
            return f"Execution error: {e}"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _exec_shell(self, code: str) -> str:
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workdir),
            )
            output = result.stdout or ""
            if result.returncode != 0:
                output += f"\nExit code: {result.returncode}\nStderr: {result.stderr}"
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return "Execution timed out (30s)"
        except Exception as e:
            return f"Execution error: {e}"


class ShellCommandTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="shell",
            description="Run a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                },
                "required": ["command"],
            },
        )

    async def run(self, command: str) -> str:
        exec_tool = CodeExecTool()
        return await exec_tool.run(command, language="shell")
