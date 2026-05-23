# Screenshots

Visual walkthrough of AutoFlow CLI in action.

---

## 1. CLI Help

```
autoflow --help
```

![CLI Help](screenshots/01-help.svg)

Shows all 6 commands with descriptions.

---

## 2. Provider Check

```
autoflow check
```

![Provider Check](screenshots/02-check.svg)

Verifies which LLM providers are available (Ollama local vs cloud APIs).

---

## 3. Running a Workflow

```
autoflow run "Research Python async frameworks, summarize top 3, save to async-frameworks.md"
```

![Workflow Run](screenshots/03-run.svg)

Natural language → planned → executed in a single command.

---

## 4. Verbose Output

```
autoflow run "Say hello from AutoFlow and save to hello.txt" -v
```

![Verbose Run](screenshots/04-run-verbose.svg)

The `-v` flag shows per-step output details.

---

## 5. Run History

```
autoflow list-runs
```

![Run History](screenshots/05-list-runs.svg)

All past runs stored in SQLite with status and timestamps.

---

## 6. Run Inspection

```
autoflow show <run-id>
```

![Run Details](screenshots/06-show.svg)

Per-step outputs, errors, and timing for any past run.

---

## 7. Failed Run

```
autoflow show <failed-run-id>
```

![Failed Run](screenshots/07-failed.svg)

Shows which step failed, why, and how to resume.

---

## 8. Workflow Plan File

```json
// research.json — define reusable pipelines
```

![Workflow File](screenshots/08-workflow-file.svg)

Declarative workflow templates with DAG dependencies and parameter templating.
