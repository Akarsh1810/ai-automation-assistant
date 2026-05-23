# AutoFlow — AI Workflow Automation Assistant

Turn natural language into automated, multi-step workflows. Orchestrate LLM calls, web searches, file operations, and code execution — all with persistent state, error recovery, and swappable AI backends.

## Features

- **Natural Language → Workflow** — Describe what you want, AutoFlow plans the steps
- **Multi-Step Orchestration** — DAG-based pipeline with dependency resolution
- **Persistent State** — SQLite-backed pause/resume across sessions
- **Prompt Engineering** — Chain-of-thought planning with structured Pydantic validation
- **LLM Provider Abstraction** — Swap between Ollama (local) and OpenAI-compatible APIs (Groq, OpenRouter, etc.)
- **Pluggable Tools** — Web search, file I/O, code execution, shell commands
- **Rich CLI** — Beautiful terminal output with Typer + Rich

## Screenshots

| | | |
|---|---|---|
| ![CLI Help](docs/screenshots/01-help.svg) | ![Run Workflow](docs/screenshots/03-run.svg) | ![Verbose Output](docs/screenshots/04-run-verbose.svg) |
| **CLI Overview** — 6 commands | **NL → Workflow** — single command | **Verbose mode** — per-step details |
| ![Run History](docs/screenshots/05-list-runs.svg) | ![Inspect Run](docs/screenshots/06-show.svg) | ![Failed Run](docs/screenshots/07-failed.svg) |
| **Persistent state** — all runs tracked | **Debug** — step outputs visible | **Error recovery** — resume support |

[View full gallery →](docs/screenshots.md)

## Quick Start

```bash
# Install
pip install -e .

# Check available providers
autoflow check

# Run a workflow from natural language
autoflow run "Research quantum computing 2026, summarize into quantum.md"

# Run from saved workflow file
autoflow run-file examples/research.json

# List past runs
autoflow list-runs

# Inspect a specific run
autoflow show <run-id>

# Resume a failed run
autoflow resume <run-id>
```

## How It Works

```
User Input ──→ NLPlanner ──→ Structured Plan ──→ Pipeline Engine ──→ Output
                   │                                  │
              Prompt engineering                  DAG executor
              Pydantic validation                 SQLite state
              Chain-of-thought                    Retry logic
```

1. **Planner** — LLM decomposes natural language into a validated `WorkflowPlan` (DAG of steps)
2. **Engine** — Topologically sorts steps, executes with dependency tracking
3. **State** — Every step result is persisted to SQLite; crashes don't lose progress
4. **Tools** — Each step type maps to a tool (web search, file write, code exec, etc.)

## Architecture

```
autoflow/
├── core/              Engine, DAG resolver, state machine, data models
├── llm/               Provider abstraction (Ollama, OpenAI-compatible)
├── planner/           NL → structured workflow with prompt engineering
├── tools/             Plugin system: web_search, file_ops, code_exec, llm_call
├── schemas/           Pydantic v2 validation models
├── cli/               Typer-based command line interface
└── config.py          Configuration from env vars
```

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `AUTOFLOW_LLM_PROVIDER` | `ollama` | `ollama` or `openai_compat` |
| `AUTOFLOW_LLM_MODEL` | `llama3.2` | Model name |
| `AUTOFLOW_API_BASE` | `https://api.groq.com/openai/v1` | API base URL |
| `AUTOFLOW_API_KEY` | `` | API key (for OpenAI-compatible) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server |

## Profile Relevance

| Skill | Demonstrated By |
|---|---|
| LLM API Integration | Multi-provider abstraction with OpenAI-compatible + Ollama |
| Multi-Step Orchestration | DAG pipeline with topological sort + dependency resolution |
| Persistent State Handling | SQLite-backed pause/resume with crash recovery |
| Prompt Engineering | Chain-of-thought planner, structured Pydantic output validation |
| Tool/API Design | Plugin tool architecture, CLI design, configurable providers |

## License

MIT
