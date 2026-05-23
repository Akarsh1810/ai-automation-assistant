# Architecture

## Overview

AutoFlow is a modular, event-driven workflow automation engine. It follows a four-layer architecture:

```
┌─────────────────────────────────────────────────┐
│                    CLI Layer                      │
│            (Typer + Rich terminal UI)             │
├─────────────────────────────────────────────────┤
│                 Orchestration Layer               │
│    Planner → Pipeline Engine → State Manager      │
├─────────────────────────────────────────────────┤
│                 Provider Layer                    │
│    LLM Providers (Ollama, OpenAI-compatible)      │
│    Tool Registry (web, file, code, shell)         │
├─────────────────────────────────────────────────┤
│                 Data Layer                        │
│    Pydantic Models → SQLite Persistence           │
└─────────────────────────────────────────────────┘
```

## Core Components

### 1. Data Models (`autoflow/core/models.py`)

The foundation of the system. Key models:

- **`StepType`** — Enum of supported step types (llm_call, web_search, file_ops, etc.)
- **`StepStatus`** — Enum for tracking execution state (pending → running → completed/failed)
- **`StepConfig`** — Configuration for a step (type, params, dependencies, retry policy)
- **`Step`** — Runtime representation of a step with status, output, timing
- **`WorkflowPlan`** — The full plan: title, description, ordered steps with DAG validation
- **`WorkflowRun`** — Execution record wrapping a plan with step results

**DAG Validation** — `WorkflowPlan.validate_dag()` checks:
- All `depends_on` references exist
- No circular dependencies (via DFS cycle detection)
- `topological_sort()` returns steps in valid execution order

### 2. State Persistence (`autoflow/core/state.py`)

SQLite-backed state management with thread-safe singleton:

- `workflow_runs` table — stores run metadata and serialized plan
- `step_results` table — stores per-step status, output, error, timing
- WAL mode for concurrent read performance
- Full save/load/list/delete operations

**Why SQLite?** Zero configuration, file-based, atomic transactions, built into Python. Perfect for a CLI tool.

### 3. Pipeline Engine (`autoflow/core/engine.py`)

The orchestrator that ties everything together:

1. **Topological Sort** — Steps are DAG-sorted before execution
2. **Dependency Resolution** — Each step waits for its `depends_on` to complete
3. **Parameter Templating** — `{{step_id.output}}` references are resolved at runtime
4. **Retry Logic** — Configurable retry count with exponential backoff
5. **State Persistence** — Run state saved after each step (crash-safe)
6. **Resume** — Load a failed run and continue from where it stopped

### 4. LLM Provider Abstraction (`autoflow/llm/`)

Strategy pattern for LLM backends:

```
LLMProvider (ABC)
├── OllamaProvider     — Local inference via Ollama
└── OpenAICompatibleProvider  — Groq, OpenRouter, etc.
```

Each provider implements:
- `generate(prompt, system_prompt, schema, temperature, max_tokens) → LLMResult`
- `is_available() → bool`

The factory `autoflow.llm.create_provider()` selects the right provider based on config.

### 5. Planner (`autoflow/planner/planner.py`)

The prompt engineering centerpiece. Uses **chain-of-thought prompting** to decompose user intent:

**System Prompt** — Defines available step types, JSON output schema, constraints
**User Prompt** — The user's natural language request, wrapped in a template
**Output Cleaning** — Regex removes markdown fences, extracts pure JSON
**Plan Building** — JSON → `WorkflowPlan` with auto-generated step IDs

### 6. Tools (`autoflow/tools/`)

Plugin architecture for executable actions:

```
Tool (ABC)
├── WebSearchTool   — DuckDuckGo search (no API key needed)
├── FileReadTool    — Read file contents
├── FileWriteTool   — Write content to file
├── LLMCallTool    — Make LLM calls
├── CodeExecTool   — Execute Python code
└── ShellCommandTool — Run shell commands
```

Tools are registered in the `ToolRegistry` and mapped to step types in the engine.

## Data Flow

```
User: "Research X, summarize, save to file"
  │
  ▼
┌─────────────────────────────┐
│  NLPlanner.plan()           │
│  • LLM generates JSON plan  │
│  • Validates with Pydantic  │
│  • Returns WorkflowPlan     │
└─────────────────────────────┘
  │
  ▼
┌─────────────────────────────┐
│  PipelineEngine.execute()   │
│  • Load step handlers       │
│  • Save initial state       │
│  • For each step (sorted):  │
│    ├─ Resolve deps          │
│    ├─ Run with retry        │
│    └─ Persist result        │
└─────────────────────────────┘
  │
  ▼
Output + Persisted Run State
```

## Design Decisions

| Decision | Rationale |
|---|---|
| SQLite over Redis/Postgres | Zero deps, portable, good enough for CLI tool |
| Async engine | LLM calls are I/O-bound; async enables parallel step execution in future |
| Pydantic v2 | First-class JSON schema validation, serialization, performance |
| Strategy pattern for LLMs | Swap providers without changing engine code |
| DAG over sequential | Real workflows have branching and parallelizable steps |
| DuckDuckGo search | Free, no API key required for basic web search |
