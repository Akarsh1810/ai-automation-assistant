from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepType(str, Enum):
    LLM_CALL = "llm_call"
    WEB_SEARCH = "web_search"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    CODE_EXEC = "code_exec"
    SHELL = "shell"
    HTTP_REQUEST = "http_request"
    CONDITIONAL = "conditional"
    HUMAN_APPROVAL = "human_approval"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class StepConfig(BaseModel):
    type: StepType
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float | None = None
    condition: str | None = None


class Step(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    label: str
    config: StepConfig
    status: StepStatus = StepStatus.PENDING
    output: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkflowPlan(BaseModel):
    title: str
    description: str = ""
    steps: list[Step]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def validate_dag(self) -> None:
        step_ids = {s.id for s in self.steps}
        for step in self.steps:
            for dep in step.config.depends_on:
                if dep not in step_ids:
                    msg = f"Step '{step.label}' depends on unknown step id '{dep}'"
                    raise ValueError(msg)

    def topological_sort(self) -> list[Step]:
        self.validate_dag()

        visited: set[str] = set()
        sorted_steps: list[Step] = []
        step_map = {s.id: s for s in self.steps}

        def dfs(step_id: str, path: set[str]) -> None:
            if step_id in path:
                msg = f"Circular dependency detected involving step '{step_id}'"
                raise ValueError(msg)
            if step_id in visited:
                return
            path.add(step_id)
            step = step_map[step_id]
            for dep in step.config.depends_on:
                dfs(dep, path)
            path.remove(step_id)
            visited.add(step_id)
            sorted_steps.append(step)

        for step in self.steps:
            if step.id not in visited:
                dfs(step.id, set())

        return sorted_steps


class WorkflowRun(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    plan: WorkflowPlan
    status: StepStatus = StepStatus.PENDING
    step_results: dict[str, dict[str, Any]] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
