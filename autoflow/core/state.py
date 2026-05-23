from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from autoflow.core.models import StepStatus, WorkflowPlan, WorkflowRun


class _ThreadLocal(threading.local):
    conn: sqlite3.Connection | None = None


class StateManager:
    _instance: StateManager | None = None
    _lock = threading.Lock()

    def __init__(self, db_path: str | Path = "~/.autoflow/state.db") -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = _ThreadLocal()

    @classmethod
    def get_instance(cls, db_path: str | Path = "~/.autoflow/state.db") -> StateManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._init_tables()
        return self._local.conn

    def _init_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id TEXT PRIMARY KEY,
                plan_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                current_step_id TEXT,
                error TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS step_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                output TEXT,
                error TEXT,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_step_results_run ON step_results(run_id);
        """)
        self._conn.commit()

    def save_run(self, run: WorkflowRun) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO workflow_runs "
            "(id, plan_json, status, error, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                run.id,
                run.plan.model_dump_json(),
                run.status.value,
                run.error,
                run.started_at.isoformat() if run.started_at else None,
                run.completed_at.isoformat() if run.completed_at else None,
            ),
        )
        self._save_step_results(run)
        self._conn.commit()

    def _save_step_results(self, run: WorkflowRun) -> None:
        self._conn.execute("DELETE FROM step_results WHERE run_id = ?", (run.id,))
        cols = "(run_id, step_id, status, output, error, started_at, completed_at)"
        vals = "VALUES (?, ?, ?, ?, ?, ?, ?)"
        sql = f"INSERT INTO step_results {cols} {vals}"
        for step in run.plan.steps:
            self._conn.execute(
                sql,
                (
                    run.id,
                    step.id,
                    step.status.value,
                    json.dumps({"output": step.output}) if step.output is not None else None,
                    step.error,
                    step.started_at.isoformat() if step.started_at else None,
                    step.completed_at.isoformat() if step.completed_at else None,
                ),
            )
        self._conn.commit()

    def load_run(self, run_id: str) -> WorkflowRun | None:
        row = self._conn.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None

        plan = WorkflowPlan.model_validate_json(row["plan_json"])
        cursor = self._conn.execute("SELECT * FROM step_results WHERE run_id = ?", (run_id,))
        for srow in cursor.fetchall():
            for step in plan.steps:
                if step.id == srow["step_id"]:
                    step.status = type(step.status)(srow["status"])
                    step.error = srow["error"]
                    if srow["output"]:
                        data = json.loads(srow["output"])
                        step.output = data.get("output")
                    break

        if plan.steps:
            status_val = type(plan.steps[0].status)(row["status"])
        else:
            status_val = StepStatus.PENDING
        return WorkflowRun(
            id=row["id"],
            plan=plan,
            status=status_val,
            error=row["error"],
        )

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        sql = (
            "SELECT id, status, error, started_at, completed_at, created_at "
            "FROM workflow_runs ORDER BY created_at DESC LIMIT ?"
        )
        rows = self._conn.execute(sql, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def delete_run(self, run_id: str) -> bool:
        self._conn.execute("DELETE FROM step_results WHERE run_id = ?", (run_id,))
        cur = self._conn.execute("DELETE FROM workflow_runs WHERE id = ?", (run_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
