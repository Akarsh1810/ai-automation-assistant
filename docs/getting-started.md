# Getting Started

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) (for free local LLM inference — no API key needed)

## Step 1: Setup Virtual Environment

```bash
cd /Users/apple/akarsh/myprojects/ai-projects/automation-assistant

# Create virtual env (one-time)
python3 -m venv .venv

# Activate it
source .venv/bin/activate
```

## Step 2: Install AutoFlow

```bash
pip install -e ".[dev]"

# Verify
autoflow --help
```

Expected output:
```
 Usage: autoflow [OPTIONS] COMMAND [ARGS]...
 AI Workflow Automation Assistant...
 Commands: run, run-file, resume, list-runs, show, check
```

## Step 3: Verify LLM Provider

```bash
autoflow check
```

Expected output:
```
  Ollama (localhost:11434): ✓ Available
  Groq (free tier): ✗ Not available
```

If Ollama shows ✗, start it: `ollama serve`

## Step 4: Test with a Simple Workflow

```bash
export AUTOFLOW_LLM_MODEL=phi3
autoflow run "Say hello from AutoFlow and save to hello.txt" -v
```

Expected output:
```
  ✓ Process with LLM
  ✓ Save to file
  Status: COMPLETED
  Steps: 2/2 completed
```

Verify the file was created:
```bash
cat hello.txt
```

## Step 5: Test with a Pre-built Workflow File

```bash
autoflow run-file examples/code-gen.json -v
```

This generates, tests, and saves a Python email validator function.

## Step 6: Explore Run History

```bash
autoflow list-runs
autoflow show <run-id-from-above>
```

## Step 7: Cleanup Test Files

```bash
rm -f hello.txt email_validator.py
```

---

## Available Models on This Machine

We have **phi3** installed locally. You can also pull other models:

```bash
ollama pull llama3.2    # 3.8B params, good for structured output
ollama pull phi3         # already installed
```

Set the model via env:
```bash
export AUTOFLOW_LLM_MODEL=phi3
# or
export AUTOFLOW_LLM_MODEL=llama3.2
```

---

## Free Cloud Providers (No Local GPU Needed)

### Groq (free tier)
```bash
export AUTOFLOW_LLM_PROVIDER=openai_compat
export AUTOFLOW_LLM_MODEL=llama3.2-3b-preview
export AUTOFLOW_API_BASE=https://api.groq.com/openai/v1
export AUTOFLOW_API_KEY=gsk_your_key_here    # get at https://console.groq.com
```

### OpenRouter (free models)
```bash
export AUTOFLOW_LLM_PROVIDER=openai_compat
export AUTOFLOW_LLM_MODEL=meta-llama/llama-3.2-3b-instruct:free
export AUTOFLOW_API_BASE=https://openrouter.ai/api/v1
export AUTOFLOW_API_KEY=your_key_here
```

---

## Full CLI Reference

```bash
autoflow run "prompt"          # NL → executed workflow
autoflow run-file plan.json    # Execute saved plan
autoflow resume <run-id>       # Resume failed run
autoflow list-runs             # Show run history
autoflow show <run-id>         # Inspect run details
autoflow check                 # Verify LLM provider
```
