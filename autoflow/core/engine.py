from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from rich.console import Console

from autoflow.config import Config
from autoflow.core.models import Step, StepStatus, StepType, WorkflowPlan, WorkflowRun
from autoflow.core.state import StateManager
from autoflow.llm import LLMProvider, create_provider
from autoflow.tools.base import ToolRegistry

console = Console()


class PipelineEngine:
    def __init__(
        self,
        config: Config | None = None,
        llm_provider: LLMProvider | None = None,
        state_manager: StateManager | None = None,
    ) -> None:
        self.config = config or Config.from_env()
        self.llm = llm_provider or create_provider(self.config)
        self.state = state_manager or StateManager.get_instance(str(self.config.state_db_path))
        self.tools = ToolRegistry()
        self._step_handlers: dict[StepType, Callable[..., Any]] = {}

    def register_handler(self, step_type: StepType, handler: Callable[..., Any]) -> None:
        self._step_handlers[step_type] = handler

    async def execute(self, plan: WorkflowPlan) -> WorkflowRun:
        run = WorkflowRun(plan=plan, status=StepStatus.RUNNING, started_at=datetime.utcnow())
        self.state.save_run(run)

        steps = plan.topological_sort()
        completed: dict[str, dict[str, Any]] = {}

        for step in steps:
            if run.status == StepStatus.FAILED:
                break

            deps_ok = all(
                completed.get(dep, {}).get("status") == StepStatus.COMPLETED for dep in step.config.depends_on
            )
            if not deps_ok:
                step.status = StepStatus.BLOCKED
                continue

            step.status = StepStatus.RUNNING
            step.started_at = datetime.utcnow()
            self.state.save_run(run)

            resolved_params = self._resolve_params(step.config.params, completed)

            for attempt in range(step.config.retry_count):
                try:
                    output = await self._execute_step(step, resolved_params)
                    step.status = StepStatus.COMPLETED
                    step.output = output
                    step.completed_at = datetime.utcnow()
                    completed[step.id] = {"status": StepStatus.COMPLETED, "output": output}
                    console.print(f"  [green]✓[/green] {step.label}")
                    break
                except Exception as e:
                    step.error = str(e)
                    if attempt < step.config.retry_count - 1:
                        retry_msg = f"retry {attempt + 1}/{step.config.retry_count}"
                        msg = f"  [yellow]⚠[/yellow] {step.label} failed ({retry_msg}): {e}"
                        console.print(msg)
                        await asyncio.sleep(step.config.retry_delay_seconds * (2**attempt))
                    else:
                        step.status = StepStatus.FAILED
                        step.completed_at = datetime.utcnow()
                        completed[step.id] = {"status": StepStatus.FAILED, "error": str(e)}
                        console.print(f"  [red]✗[/red] {step.label}: {e}")

            self.state.save_run(run)

        failed = any(s.status == StepStatus.FAILED for s in plan.steps)
        run.status = StepStatus.FAILED if failed else StepStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        if failed:
            run.error = "One or more steps failed"
        self.state.save_run(run)
        return run

    async def _execute_step(self, step: Step, params: dict[str, Any]) -> Any:
        handler = self._step_handlers.get(step.config.type)
        if handler:
            result = handler(**params)
            if asyncio.iscoroutine(result):
                return await result
            return result
        msg = f"No handler registered for step type: {step.config.type}"
        raise ValueError(msg)

    def _resolve_params(self, params: dict[str, Any], completed: dict[str, dict[str, Any]]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                ref = value[2:-2].strip().split(".")
                if ref[0] in completed:
                    resolved[key] = completed[ref[0]].get("output")
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    async def resume(self, run_id: str) -> WorkflowRun | None:
        run = self.state.load_run(run_id)
        if run is None:
            console.print(f"[red]Run {run_id} not found[/red]")
            return None

        console.print(f"[blue]Resuming run {run_id}...[/blue]")
        return await self.execute(run.plan)

    async def run_nl(self, prompt: str) -> WorkflowRun:
        from autoflow.planner.planner import NLPlanner

        planner = NLPlanner(self.llm)
        plan = await planner.plan(prompt)
        console.print(f"[bold]Plan:[/bold] {plan.title}")
        console.print(f"[dim]{plan.description}[/dim]\n")
        return await self.execute(plan)
