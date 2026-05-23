"""Generate SVG screenshots of AutoFlow CLI for documentation.

Usage:
    source .venv/bin/activate
    python scripts/generate_screenshots.py
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autoflow.config import Config
from autoflow.core.engine import PipelineEngine
from autoflow.core.models import StepStatus
from autoflow.core.state import StateManager
from autoflow.llm import create_provider
from autoflow.tools import register_default_tools

OUTPUT_DIR = Path("docs/screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 100
HEIGHT = 30

def make_console(title: str) -> Console:
    return Console(record=True, width=100, force_terminal=True, color_system="truecolor")

def save_svg(console: Console, name: str):
    path = OUTPUT_DIR / f"{name}.svg"
    console.save_svg(str(path), title="AutoFlow CLI")
    print(f"  Saved: {path}")

def screenshot_help():
    console = make_console("help")
    console.print(Panel("[bold cyan]AutoFlow[/bold cyan] — AI Workflow Automation Assistant\nTurn natural language into automated multi-step pipelines.", border_style="blue"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Command")
    table.add_column("Description")
    table.add_row("[green]run[/green]", "Run workflow from NL prompt")
    table.add_row("[green]run-file[/green]", "Run workflow from saved plan")
    table.add_row("[green]resume[/green]", "Resume failed workflow")
    table.add_row("[green]list-runs[/green]", "Show run history")
    table.add_row("[green]show[/green]", "Inspect run details")
    table.add_row("[green]check[/green]", "Verify LLM provider")
    console.print(table)
    save_svg(console, "01-help")

def screenshot_check():
    console = make_console("check")
    console.print("[bold]Checking LLM providers...[/bold]\n")
    console.print("  [bold]Ollama (localhost:11434):[/bold] [green]✓ Available[/green]")
    console.print("  [bold]Groq (free tier):[/bold] [yellow]✗ Not available[/yellow]")
    console.print("\n[dim]Set AUTOFLOW_LLM_PROVIDER=ollama or openai_compat[/dim]")
    console.print("[dim]Set AUTOFLOW_API_KEY for OpenAI-compatible providers[/dim]")
    save_svg(console, "02-check")

def screenshot_run():
    console = make_console("run")
    prompt = "Research Python async frameworks, summarize top 3, save to async-frameworks.md"

    console.print(Panel(
        f"[bold]Input:[/bold] {prompt}",
        title="[bold blue]AutoFlow[/bold blue]",
        border_style="blue"
    ))

    console.print("\n[bold]Plan:[/bold] Research & Report")
    console.print("[dim]Search web, summarize with LLM, save to file[/dim]\n")

    steps_data = [
        ("Search the web", StepStatus.COMPLETED, None),
        ("Summarize results", StepStatus.COMPLETED, None),
        ("Save to file", StepStatus.COMPLETED, None),
    ]

    for label, status, err in steps_data:
        icon = "[green]✓[/green]" if status == StepStatus.COMPLETED else "[red]✗[/red]"
        console.print(f"  {icon} {label}")

    console.print(f"\n{'='*50}")
    console.print("[bold green]Status:[/bold green] COMPLETED")
    console.print("[bold]Steps:[/bold] 3/3 completed")
    console.print("\n[dim]Run ID: a1b2c3d4e5f6  |  autoflow show a1b2c3d4e5f6[/dim]")
    save_svg(console, "03-run")

def screenshot_run_verbose():
    console = make_console("run-verbose")
    prompt = "Say hello from AutoFlow and save to hello.txt"

    console.print(Panel(
        f"[bold]Input:[/bold] {prompt}",
        title="[bold blue]AutoFlow[/bold blue]",
        border_style="blue"
    ))

    console.print("\n[bold]Plan:[/bold] Auto-generated Plan")
    console.print("[dim]Fallback plan for: Say hello from AutoFlow and save to hello.txt[/dim]\n")

    console.print("  [green]✓[/green] Process with LLM")
    console.print("  [green]✓[/green] Save to file")

    console.print(f"\n{'='*50}")
    console.print("[bold green]Status:[/bold green] COMPLETED")
    console.print("[bold]Steps:[/bold] 2/2 completed\n")

    tree_lines = [
        "Step Details",
        "├── [green]● Process with LLM (completed)[/green]",
        "│   └── Output: AutoFlow says hello! This is a demonstration",
        "│       of the AI Workflow Automation Assistant...",
        "└── [green]● Save to file (completed)[/green]",
        "    └── Output: Written 321 bytes to ./hello.txt",
    ]
    for line in tree_lines:
        console.print(line)

    console.print("\n[dim]Run ID: b2c3d4e5f6a7  |  autoflow show b2c3d4e5f6a7[/dim]")
    save_svg(console, "04-run-verbose")

def screenshot_list_runs():
    console = make_console("list-runs")
    table = Table(title="[bold]Recent Workflow Runs[/bold]")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Created")
    table.add_column("Error")

    runs = [
        ("a1b2c3d4e5f6", "completed", "2026-05-23 14:30:00", "-"),
        ("b2c3d4e5f6a7", "completed", "2026-05-23 14:28:00", "-"),
        ("c3d4e5f6a7b8", "failed", "2026-05-23 14:25:00", "One or more steps failed"),
        ("d4e5f6a7b8c9", "completed", "2026-05-23 14:20:00", "-"),
    ]

    for rid, status, created, error in runs:
        style = {
            "completed": "green",
            "failed": "red",
            "running": "yellow",
        }.get(status, "white")
        table.add_row(rid, f"[{style}]{status}[/{style}]", created, error)

    console.print(table)
    save_svg(console, "05-list-runs")

def screenshot_show():
    console = make_console("show")
    console.print("[bold]Run ID:[/bold] a1b2c3d4e5f6")
    console.print("[bold]Workflow:[/bold] Research & Report")
    console.print("[bold]Status:[/bold] [green]completed[/green]\n")

    console.print("[bold]Steps[/bold]")
    console.print("├── [green]● Search the web (completed)[/green]")
    console.print("│   └── Output: Found 5 relevant results about")
    console.print("│       Python async frameworks including FastAPI,")
    console.print("│       Sanic, and Quart...")
    console.print("├── [green]● Summarize results (completed)[/green]")
    console.print("│   └── Output: Top 3 Python async frameworks:")
    console.print("│       1. FastAPI - high performance, modern")
    console.print("│       2. Sanic - async-first web server")
    console.print("│       3. Quart - Flask-compatible async")
    console.print("└── [green]● Save to file (completed)[/green]")
    console.print("    └── Output: Written 2048 bytes to ./async-frameworks.md")
    save_svg(console, "06-show")

def screenshot_failed():
    console = make_console("failed")
    console.print("[bold]Run ID:[/bold] c3d4e5f6a7b8")
    console.print("[bold]Workflow:[/bold] Code Generator")
    console.print("[bold]Status:[/bold] [red]failed[/red]\n")

    console.print("[bold]Steps[/bold]")
    console.print("├── [red]● Write Python function (failed)[/red]")
    console.print("│   └── [red]Error: Model 'llama3.2' not found[/red]")
    console.print("├── [red dim]● Test the function (blocked)[/red dim]")
    console.print("└── [red dim]● Save to file (blocked)[/red dim]")
    console.print("\n⏭  [bold]Resume:[/bold] [cyan]autoflow resume c3d4e5f6a7b8[/cyan]")
    save_svg(console, "07-failed")

def screenshot_workflow_file():
    console = make_console("workflow-file")
    syntax = Syntax(
        json.dumps({
            "title": "AI Research & Report",
            "description": "Research a topic and save to markdown",
            "steps": [
                {
                    "label": "Search web",
                    "config": {
                        "type": "web_search",
                        "params": {"query": "AI advancements 2026"},
                        "depends_on": []
                    }
                },
                {
                    "label": "Summarize",
                    "config": {
                        "type": "llm_call",
                        "params": {
                            "prompt": "Summarize: {{step_1.output}}",
                            "temperature": 0.3
                        },
                        "depends_on": ["step_1"]
                    }
                },
                {
                    "label": "Save report",
                    "config": {
                        "type": "file_write",
                        "params": {
                            "path": "./report.md",
                            "content": "{{step_2.output}}"
                        },
                        "depends_on": ["step_2"]
                    }
                }
            ]
        }, indent=2),
        "json",
        theme="monokai",
        line_numbers=True
    )
    console.print(Panel(syntax, title="[bold]Workflow Plan File[/bold] (research.json)", border_style="green"))
    console.print("\n[dim]Run with: autoflow run-file research.json[/dim]")
    save_svg(console, "08-workflow-file")


if __name__ == "__main__":
    print("Generating screenshots...\n")
    screenshot_help()
    screenshot_check()
    screenshot_run()
    screenshot_run_verbose()
    screenshot_list_runs()
    screenshot_show()
    screenshot_failed()
    screenshot_workflow_file()
    print(f"\nDone! {len(list(OUTPUT_DIR.glob('*.svg')))} screenshots saved to {OUTPUT_DIR}")
