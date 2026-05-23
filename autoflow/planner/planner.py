from __future__ import annotations

import json
import re
from typing import Any

from autoflow.core.models import Step, StepConfig, StepType, WorkflowPlan
from autoflow.llm.base import LLMProvider

PLANNER_SYSTEM_PROMPT = """You are an AI workflow planner. Given a request, output ONLY a JSON object with a plan.

Valid "type" values: "llm_call", "web_search", "file_read", "file_write", "code_exec", "shell"

Example output for "Search for AI news and save to file":
{
  "title": "Search and Save",
  "description": "Search web and save",
  "steps": [
    {
      "label": "Search web",
      "config": {"type": "web_search", "params": {"query": "AI news"}, "depends_on": []}
    },
    {
      "label": "Save to file",
      "config": {"type": "file_write", "params": {"path": "./result.md", "content": "result"},
      "depends_on": ["step_1"]}
    }
  ]
}

Rules:
- Each step_id is auto-assigned as step_1, step_2, etc. Use these in depends_on.
- Use {{step_N.output}} to reference a previous step's output.
- Return ONLY the JSON object. No markdown, no explanation."""

PLANNER_USER_TEMPLATE = """Create a workflow plan for this task:
"{user_request}"

Return ONLY the JSON object."""


class NLPlanner:
    def __init__(self, llm: LLMProvider, max_steps: int = 10) -> None:
        self.llm = llm
        self.max_steps = max_steps

    async def plan(self, user_request: str) -> WorkflowPlan:
        prompt = PLANNER_USER_TEMPLATE.format(user_request=user_request)
        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_prompt=PLANNER_SYSTEM_PROMPT,
                temperature=0.2,
            )
            raw = self._clean_json(result.content)
            data = json.loads(raw)
            if "steps" in data and len(data["steps"]) > 0:
                data["steps"] = data["steps"][: self.max_steps]
                return self._build_plan(data)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        return self._fallback_plan(user_request)

    def _clean_json(self, text: str) -> str:
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        return text

    def _build_plan(self, data: dict[str, Any]) -> WorkflowPlan:
        steps = []
        for i, sd in enumerate(data.get("steps", [])):
            config_data = sd.get("config", {})
            step_type_str = config_data.get("type", "llm_call")
            try:
                step_type = StepType(step_type_str)
            except ValueError:
                step_type = StepType.LLM_CALL
            step = Step(
                label=sd.get("label", f"Step {i + 1}"),
                config=StepConfig(
                    type=step_type,
                    params=config_data.get("params", {}),
                    depends_on=config_data.get("depends_on", []),
                    retry_count=config_data.get("retry_count", 3),
                ),
            )
            step.id = f"step_{i + 1}"
            steps.append(step)

        return WorkflowPlan(
            title=data.get("title", "Untitled Workflow"),
            description=data.get("description", ""),
            steps=steps,
        )

    def _fallback_plan(self, user_request: str) -> WorkflowPlan:
        req_lower = user_request.lower()
        steps: list[Step] = []
        idx = 0

        has_search = any(w in req_lower for w in ["search", "find", "research", "look up", "google", "fetch"])
        has_code = any(w in req_lower for w in ["code", "script", "function", "implement", "program", "write a python"])
        has_file_write = any(w in req_lower for w in ["save", "write to", "store", "create file"])
        has_file_read = any(w in req_lower for w in ["read", "load file", "open file"])
        shell_kw = ["shell", "terminal", "command", "run ", "execute"]
        has_shell = any(w in req_lower for w in shell_kw)
        llm_kw = ["summarize", "explain", "analyze", "describe", "translate"]
        llm_kw += ["rewrite", "tell me", "write about", "say", "draft", "compose"]
        has_llm = any(w in req_lower for w in llm_kw)

        if has_search:
            idx += 1
            steps.append(
                Step(
                    id=f"step_{idx}",
                    label="Search the web",
                    config=StepConfig(type=StepType.WEB_SEARCH, params={"query": user_request}),
                )
            )

        if has_code:
            idx += 1
            deps = [f"step_{i + 1}" for i, s in enumerate(steps)]
            steps.append(
                Step(
                    id=f"step_{idx}",
                    label="Generate code",
                    config=StepConfig(
                        type=StepType.LLM_CALL,
                        params={
                            "prompt": (
                                f"Generate code for: {user_request}"
                                if not deps
                                else (
                                    f"Generate code for: {user_request}\n"
                                    f"Use previous output: {{{{step_{idx - 1}.output}}}}"
                                )
                            ),
                            "temperature": 0.2,
                        },
                        depends_on=deps,
                    ),
                )
            )

        has_llm = has_llm or (not has_search and not has_code and not has_file_read and not has_shell)
        if has_llm:
            idx += 1
            deps = [f"step_{i + 1}" for i, s in enumerate(steps)]
            steps.append(
                Step(
                    id=f"step_{idx}",
                    label="Process with LLM",
                    config=StepConfig(
                        type=StepType.LLM_CALL,
                        params={
                            "prompt": (
                                user_request
                                if not deps
                                else f"Based on previous results: {{{{step_{idx - 1}.output}}}}\n\nTask: {user_request}"
                            )
                        },
                        depends_on=deps,
                    ),
                )
            )

        if has_file_write:
            idx += 1
            deps = [f"step_{i + 1}" for i, s in enumerate(steps)]
            patterns = [
                r'(?:save|write|store|create)\s+(?:it\s+)?(?:to|as|in)\s+["\']?([a-zA-Z0-9_.\-/\\]+)',
                r'(?:save|write|store|create)\s+["\']?([a-zA-Z0-9_.\-/\\]+)["\']?',
            ]
            filename = "output.txt"
            for pat in patterns:
                fm = re.search(pat, user_request, re.IGNORECASE)
                if fm:
                    filename = fm.group(1).strip()
                    break
            steps.append(
                Step(
                    id=f"step_{idx}",
                    label="Save to file",
                    config=StepConfig(
                        type=StepType.FILE_WRITE,
                        params={"path": f"./{filename}", "content": f"{{{{step_{idx - 1}.output}}}}"},
                        depends_on=deps,
                    ),
                )
            )

        if has_shell:
            idx += 1
            deps = [f"step_{i + 1}" for i, s in enumerate(steps)]
            steps.append(
                Step(
                    id=f"step_{idx}",
                    label="Run shell command",
                    config=StepConfig(
                        type=StepType.SHELL,
                        params={"command": user_request.replace("run", "").replace("execute", "").strip()},
                        depends_on=deps,
                    ),
                )
            )

        if not steps:
            idx += 1
            steps.append(
                Step(
                    id="step_1",
                    label="Process request",
                    config=StepConfig(type=StepType.LLM_CALL, params={"prompt": user_request}),
                )
            )

        return WorkflowPlan(
            title="Auto-generated Plan",
            description=f"Fallback plan for: {user_request}",
            steps=steps,
        )
