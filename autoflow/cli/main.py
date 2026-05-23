from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from autoflow.config import Config
from autoflow.core.engine import PipelineEngine
from autoflow.core.models import StepStatus, StepType, WorkflowPlan, WorkflowRun
from autoflow.core.state import StateManager
from autoflow.llm import create_provider
from autoflow.tools import register_default_tools

app = typer.Typer(
    name="autoflow",
    help="Turn natural language into automated multi-step pipelines.",
    no_args_is_help=True,
)
console = Console()


def _build_engine(config_path: str | None = None) -> PipelineEngine:
    if config_path:
        config = Config.model_validate_json(Path(config_path).read_text())
    else:
        config = Config.from_env()
    llm = create_provider(config)
    state = StateManager.get_instance(str(config.state_db_path))
    engine = PipelineEngine(config=config, llm_provider=llm, state_manager=state)

    register_default_tools(engine.tools, llm)

    from autoflow.tools.code_exec import CodeExecTool, ShellCommandTool
    from autoflow.tools.file_ops import FileReadTool, FileWriteTool
    from autoflow.tools.llm_tool import LLMCallTool
    from autoflow.tools.web_search import WebSearchTool

    engine.register_handler(StepType.LLM_CALL, LLMCallTool(llm).run)
    engine.register_handler(StepType.WEB_SEARCH, WebSearchTool().run)
    engine.register_handler(StepType.FILE_READ, FileReadTool().run)
    engine.register_handler(StepType.FILE_WRITE, FileWriteTool().run)
    engine.register_handler(StepType.CODE_EXEC, CodeExecTool().run)
    engine.register_handler(StepType.SHELL, ShellCommandTool().run)

    return engine


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Natural language description of the workflow"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed step output"),
) -> None:
    """Run a workflow from a natural language prompt."""
    engine = _build_engine(config)

    async def _run() -> None:
        console.print(Panel(f"[bold]Input:[/bold] {prompt}", title="AutoFlow", border_style="blue"))
        run_result = await engine.run_nl(prompt)
        _show_summary(run_result, verbose)

    asyncio.run(_run())


@app.command()
def run_file(
    workflow_file: str = typer.Argument(..., help="Path to workflow YAML/JSON file"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed step output"),
) -> None:
    """Run a workflow from a saved plan file."""
    engine = _build_engine(config)

    async def _run() -> None:
        path = Path(workflow_file).expanduser().resolve()
        if not path.exists():
            console.print(f"[red]File not found: {path}[/red]")
            raise typer.Exit(1)

        data = json.loads(path.read_text())
        plan = WorkflowPlan.model_validate(data)
        console.print(Panel(f"[bold]Workflow:[/bold] {plan.title}", border_style="blue"))
        run_result = await engine.execute(plan)
        _show_summary(run_result, verbose)

    asyncio.run(_run())


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="Run ID to resume"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Resume a previously interrupted workflow run."""
    engine = _build_engine(config)

    async def _resume() -> None:
        result = await engine.resume(run_id)
        if result:
            _show_summary(result, verbose=True)

    asyncio.run(_resume())


@app.command()
def list_runs(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of runs to show"),
) -> None:
    """List recent workflow runs."""
    state = StateManager.get_instance()
    runs = state.list_runs(limit=limit)
    if not runs:
        console.print("[yellow]No runs found.[/yellow]")
        return

    table = Table(title="Recent Workflow Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Created")
    table.add_column("Error")

    for r in runs:
        status_style = {
            "completed": "green",
            "failed": "red",
            "running": "yellow",
            "pending": "dim",
        }.get(r["status"], "white")
        table.add_row(
            r["id"],
            f"[{status_style}]{r['status']}[/{status_style}]",
            r["created_at"] or "-",
            r["error"] or "-",
        )
    console.print(table)


@app.command()
def show(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
) -> None:
    """Show details of a specific workflow run."""
    state = StateManager.get_instance()
    run = state.load_run(run_id)
    if not run:
        console.print(f"[red]Run {run_id} not found.[/red]")
        return

    console.print(f"[bold]Run ID:[/bold] {run.id}")
    console.print(f"[bold]Workflow:[/bold] {run.plan.title}")
    console.print(f"[bold]Status:[/bold] {run.status.value}")

    tree = Tree("Steps")
    for step in run.plan.steps:
        style = {
            StepStatus.COMPLETED: "green",
            StepStatus.FAILED: "red",
            StepStatus.RUNNING: "yellow",
            StepStatus.PENDING: "dim",
            StepStatus.BLOCKED: "red dim",
        }.get(step.status, "white")
        label = f"[{style}]● {step.label} ({step.status.value})[/{style}]"
        branch = tree.add(label)
        if step.error:
            branch.add(f"[red]Error: {step.error}[/red]")
        if step.output is not None:
            output_str = str(step.output)[:200]
            branch.add(f"[dim]Output: {output_str}[/dim]")

    console.print(tree)


@app.command()
def check() -> None:
    """Check which LLM providers are available."""
    console.print("[bold]Checking LLM providers...[/bold]\n")

    async def _check() -> None:
        from autoflow.llm.ollama import OllamaProvider
        from autoflow.llm.openai_compat import OpenAICompatibleProvider

        providers = [
            ("Ollama (localhost:11434)", OllamaProvider()),
            ("Groq (free tier)", OpenAICompatibleProvider(api_key="dummy")),
        ]

        for name, provider in providers:
            try:
                available = await provider.is_available()
                label_on = "[green]✓ Available[/green]"
                label_off = "[yellow]✗ Not available[/yellow]"
                status = label_on if available else label_off
                console.print(f"  {name}: {status}")
            except Exception as e:
                console.print(f"  {name}: [red]Error: {e}[/red]")

    asyncio.run(_check())

    console.print("\n[dim]Set AUTOFLOW_LLM_PROVIDER=ollama or openai_compat[/dim]")
    console.print("[dim]Set AUTOFLOW_API_KEY for OpenAI-compatible providers[/dim]")


def _show_summary(run_result: WorkflowRun, verbose: bool = False) -> None:
    steps = run_result.plan.steps
    total = len(steps)
    completed = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
    failed = sum(1 for s in steps if s.status == StepStatus.FAILED)

    status_color = "green" if failed == 0 else "red"
    status_val = run_result.status.value.upper()
    console.print(f"\n[bold]{'=' * 50}[/bold]")
    console.print(f"[bold {status_color}]Status:[/bold {status_color}] {status_val}")
    steps_info = f"[bold]Steps:[/bold] {completed}/{total} completed"
    if failed:
        steps_info += f", {failed} failed"
    console.print(steps_info)

    if verbose and run_result.plan.steps:
        tree = Tree("Step Details")
        for step in run_result.plan.steps:
            style = {
                StepStatus.COMPLETED: "green",
                StepStatus.FAILED: "red",
                StepStatus.PENDING: "dim",
                StepStatus.BLOCKED: "red dim",
                StepStatus.RUNNING: "yellow",
            }.get(step.status, "white")
            label = f"[{style}]● {step.label} ({step.status.value})[/{style}]"
            branch = tree.add(label)
            if step.error:
                branch.add(f"[red]Error: {step.error}[/red]")
        console.print(tree)

    if run_result.id:
        console.print(f"\n[dim]Run ID: {run_result.id}  |  autoflow show {run_result.id}[/dim]")


if __name__ == "__main__":
    app()
