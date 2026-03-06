#!/usr/bin/env python3
"""Agent OS control-plane primitives for OpenClaw."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


ROOT_DIR = Path(__file__).resolve().parents[1]
CONTROL_PLANE_DIR = ROOT_DIR / "control-plane"
SCHEMAS_DIR = CONTROL_PLANE_DIR / "schemas"
CONFIG_DIR = CONTROL_PLANE_DIR / "config"
POLICIES_DIR = CONTROL_PLANE_DIR / "policies"
CONTROL_SCRIPTS_DIR = CONTROL_PLANE_DIR / "scripts"
STATE_DIR = CONTROL_PLANE_DIR / "state"
ARTIFACTS_DIR = CONTROL_PLANE_DIR / "artifacts"
DEFAULT_DB_PATH = STATE_DIR / "agentos.db"
DEFAULT_EVENTS_DIR = ARTIFACTS_DIR / "events"
DEFAULT_TASKS_DIR = ARTIFACTS_DIR / "tasks"
DEFAULT_REPORTS_DIR = ARTIFACTS_DIR / "reports"
OBJECTIVES_PATH = ROOT_DIR / "ops" / "model-routing" / "objectives.json"
SUPERVISOR_CONFIG_PATH = CONFIG_DIR / "supervisor.json"
PREFLIGHT_POLICY_PATH = POLICIES_DIR / "production_preflight_policy.json"

TASK_STATUSES = {
    "queued",
    "claimed",
    "running",
    "blocked",
    "needs_human",
    "failed",
    "succeeded",
    "canceled",
}
BLOCKER_TYPES = {"HARD_BLOCKER", "SOFT_BLOCKER", "HUMAN_BLOCKER"}
SENSITIVE_KINDS = {"ops_deploy", "runtime_change", "policy_change", "routing_change", "auth_change"}
CODE_TASK_KINDS = {"code_impl", "code_review", "debug_ci"}
EVENT_TYPES = {
    "task.created",
    "task.claimed",
    "task.progress",
    "task.blocked",
    "task.failed",
    "task.retry_scheduled",
    "task.needs_human",
    "task.completed",
    "task.handoff",
}
ACCEPTANCE_ALIASES = {
    "test": ("test:",),
    "tests": ("test:",),
    "commit": ("commit:",),
    "pr": ("pr:",),
    "pr_or_pr_update": ("pr:",),
    "ci": ("ci:pass",),
    "ci_pass": ("ci:pass",),
}


class ValidationError(ValueError):
    """Raised when a schema-like validation fails."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_bool_env(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValidationError(f"invalid boolean env for {name}: {raw}")


def read_schema(name: str) -> dict[str, Any]:
    return load_json(SCHEMAS_DIR / name)


def load_supervisor_settings(path: Path = SUPERVISOR_CONFIG_PATH) -> dict[str, Any]:
    settings = {"version": "2026-03-05.1", "safeMode": True, "defaultLeaseSeconds": 30, "heartbeatSeconds": 10}
    if path.exists():
        settings.update(load_json(path))
    env_override = parse_bool_env("AGENTOS_SAFE_MODE")
    if env_override is not None:
        settings["safeMode"] = env_override
    return settings


def load_preflight_policy(path: Path = PREFLIGHT_POLICY_PATH) -> dict[str, Any]:
    if path.exists():
        return load_json(path)
    return {
        "version": "2026-03-05.1",
        "forbiddenWaveCombos": ["infra+policy", "infra+routing", "infra+auth", "auth+multi-provider"],
    }


def _require(payload: dict[str, Any], fields: list[str], prefix: str = "") -> None:
    missing = []
    for field in fields:
        if field not in payload:
            missing.append(f"{prefix}{field}")
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


def validate_task(task: dict[str, Any]) -> None:
    read_schema("task.schema.json")
    _require(
        task,
        [
            "schemaVersion",
            "taskId",
            "correlationId",
            "kind",
            "title",
            "workflow",
            "executionMode",
            "priority",
            "source",
            "routing",
            "constraints",
            "budget",
            "acceptance",
            "state",
            "timestamps",
        ],
    )
    if task["executionMode"] not in {"AUTO", "HUMAN"}:
        raise ValidationError("executionMode must be AUTO or HUMAN")
    if task["priority"] not in {"low", "medium", "high", "critical"}:
        raise ValidationError("priority must be low|medium|high|critical")
    state = task["state"]
    if state.get("status") not in TASK_STATUSES:
        raise ValidationError("state.status is invalid")
    if not isinstance(state.get("attempts"), int) or state["attempts"] < 0:
        raise ValidationError("state.attempts must be a non-negative integer")
    next_run_at = state.get("nextRunAt")
    if next_run_at is not None and not isinstance(next_run_at, str):
        raise ValidationError("state.nextRunAt must be a string or null")
    routing = task["routing"]
    _require(routing, ["objective", "requestedAgent", "effectiveAgent", "executionStrategy"], "routing.")
    if routing["executionStrategy"] not in {"single", "speculative", "consensus"}:
        raise ValidationError("routing.executionStrategy is invalid")
    constraints = task["constraints"]
    _require(
        constraints,
        ["allowWrites", "allowNetwork", "destructiveOps", "productionImpact"],
        "constraints.",
    )
    budget = task["budget"]
    if not isinstance(budget.get("maxRetries"), int) or budget["maxRetries"] < 0:
        raise ValidationError("budget.maxRetries must be a non-negative integer")
    acceptance = task["acceptance"]
    if not isinstance(acceptance.get("required"), list):
        raise ValidationError("acceptance.required must be a list")
    if not isinstance(acceptance.get("ciMustPass"), bool):
        raise ValidationError("acceptance.ciMustPass must be a boolean")
    if "preflight" in task:
        preflight = task["preflight"]
        if not isinstance(preflight, dict):
            raise ValidationError("preflight must be an object")
        if "changeWave" in preflight:
            _require(preflight["changeWave"], ["infra", "policy", "routing", "auth"], "preflight.changeWave.")


def validate_event(event: dict[str, Any]) -> None:
    read_schema("event.schema.json")
    _require(
        event,
        [
            "eventVersion",
            "eventType",
            "eventId",
            "createdAt",
            "correlationId",
            "taskId",
            "source",
            "routing",
            "payload",
            "evidenceRefs",
        ],
    )
    if not isinstance(event["evidenceRefs"], list):
        raise ValidationError("evidenceRefs must be a list")
    if event["eventType"] not in EVENT_TYPES and not event["eventType"].startswith("supervisor."):
        raise ValidationError(f"unsupported eventType: {event['eventType']}")


def validate_preflight(payload: dict[str, Any]) -> None:
    read_schema("preflight.schema.json")
    _require(payload, ["preflight"])
    preflight = payload["preflight"]
    _require(
        preflight,
        [
            "dockerContextChecked",
            "singleContextSession",
            "blueHealthy",
            "isParallelCandidate",
            "reusedProdVolumes",
            "reusedProdWorkspace",
            "usedProdTelegramTokenOnCandidate",
            "changeWave",
            "allowedToProceed",
        ],
        "preflight.",
    )
    _require(preflight["changeWave"], ["infra", "policy", "routing", "auth"], "preflight.changeWave.")


def default_task(
    *,
    kind: str,
    title: str,
    workflow: str,
    execution_mode: str,
    priority: str,
    source: dict[str, Any],
    routing: dict[str, Any],
    constraints: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
    acceptance: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    issue_id: str | None = None,
    repo: str | None = None,
    branch: str | None = None,
) -> dict[str, Any]:
    created_at = now_iso()
    task = {
        "schemaVersion": "2026-03-05.1",
        "taskId": str(uuid.uuid4()),
        "correlationId": str(uuid.uuid4()),
        "kind": kind,
        "title": title,
        "workflow": workflow,
        "executionMode": execution_mode,
        "priority": priority,
        "source": source,
        "routing": routing,
        "constraints": constraints
        or {
            "allowWrites": True,
            "allowNetwork": True,
            "destructiveOps": False,
            "productionImpact": False,
        },
        "budget": budget or {"maxRetries": 3, "maxCost": 0, "maxDurationSeconds": 0},
        "acceptance": acceptance or {"required": [], "ciMustPass": False},
        "state": {
            "status": "queued",
            "attempts": 0,
            "leaseOwner": None,
            "leaseUntil": None,
            "nextRunAt": None,
            "lastBlockerType": None,
            "lastBlockerReason": None,
        },
        "timestamps": {"createdAt": created_at, "updatedAt": created_at},
    }
    if preflight:
        task["preflight"] = preflight
    if issue_id:
        task["issueId"] = issue_id
    if repo:
        task["repo"] = repo
    if branch:
        task["branch"] = branch
    validate_task(task)
    return task


def default_event(
    *,
    event_type: str,
    task: dict[str, Any],
    payload: dict[str, Any],
    evidence_refs: list[str] | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    event = {
        "eventVersion": "2026-03-05.1",
        "eventType": event_type,
        "eventId": str(uuid.uuid4()),
        "createdAt": now_iso(),
        "correlationId": task["correlationId"],
        "taskId": task["taskId"],
        "source": task.get("source", {}),
        "routing": task.get("routing", {}),
        "payload": payload,
        "evidenceRefs": evidence_refs or [],
    }
    if role:
        event["role"] = role
    validate_event(event)
    return event


def open_db(db_path: Path) -> sqlite3.Connection:
    ensure_dir(db_path.parent)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version TEXT PRIMARY KEY,
      applied_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
      task_id TEXT PRIMARY KEY,
      correlation_id TEXT NOT NULL,
      status TEXT NOT NULL,
      priority TEXT NOT NULL,
      kind TEXT NOT NULL,
      objective TEXT NOT NULL,
      requested_agent TEXT NOT NULL,
      effective_agent TEXT NOT NULL,
      repo TEXT,
      branch TEXT,
      attempts INTEGER NOT NULL DEFAULT 0,
      max_retries INTEGER NOT NULL DEFAULT 0,
      lease_owner TEXT,
      lease_until TEXT,
      next_run_at TEXT,
      last_blocker_type TEXT,
      last_blocker_reason TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      task_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
      event_id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      correlation_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      created_at TEXT NOT NULL,
      event_json TEXT NOT NULL,
      FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
      artifact_id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      kind TEXT NOT NULL,
      path TEXT NOT NULL,
      created_at TEXT NOT NULL,
      metadata_json TEXT NOT NULL,
      FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_lease_until ON tasks(lease_until)",
    "CREATE INDEX IF NOT EXISTS idx_events_task_created ON events(task_id, created_at)",
]


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    columns = {row["name"] for row in rows}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    conn = open_db(db_path)
    try:
        for statement in DDL_STATEMENTS:
            conn.execute(statement)
        ensure_column(conn, "tasks", "next_run_at", "TEXT")
        ensure_column(conn, "tasks", "last_blocker_type", "TEXT")
        ensure_column(conn, "tasks", "last_blocker_reason", "TEXT")
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, applied_at)
            VALUES (?, ?)
            """,
            ("2026-03-05.2", now_iso()),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _persist_task_snapshot(task: dict[str, Any]) -> Path:
    ensure_dir(DEFAULT_TASKS_DIR)
    path = DEFAULT_TASKS_DIR / f"{task['taskId']}.json"
    dump_json(path, task)
    return path


def _append_event_jsonl(event: dict[str, Any]) -> Path:
    ensure_dir(DEFAULT_EVENTS_DIR)
    daily = DEFAULT_EVENTS_DIR / f"{event['createdAt'][:10]}.jsonl"
    with daily.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")
    return daily


def _upsert_task(conn: sqlite3.Connection, task: dict[str, Any]) -> None:
    validate_task(task)
    conn.execute(
        """
        INSERT INTO tasks (
          task_id, correlation_id, status, priority, kind, objective,
          requested_agent, effective_agent, repo, branch, attempts, max_retries,
          lease_owner, lease_until, next_run_at, last_blocker_type, last_blocker_reason,
          created_at, updated_at, task_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
          status=excluded.status,
          priority=excluded.priority,
          kind=excluded.kind,
          objective=excluded.objective,
          requested_agent=excluded.requested_agent,
          effective_agent=excluded.effective_agent,
          repo=excluded.repo,
          branch=excluded.branch,
          attempts=excluded.attempts,
          max_retries=excluded.max_retries,
          lease_owner=excluded.lease_owner,
          lease_until=excluded.lease_until,
          next_run_at=excluded.next_run_at,
          last_blocker_type=excluded.last_blocker_type,
          last_blocker_reason=excluded.last_blocker_reason,
          updated_at=excluded.updated_at,
          task_json=excluded.task_json
        """,
        (
            task["taskId"],
            task["correlationId"],
            task["state"]["status"],
            task["priority"],
            task["kind"],
            task["routing"]["objective"],
            task["routing"]["requestedAgent"],
            task["routing"]["effectiveAgent"],
            task.get("repo"),
            task.get("branch"),
            task["state"]["attempts"],
            task["budget"]["maxRetries"],
            task["state"].get("leaseOwner"),
            task["state"].get("leaseUntil"),
            task["state"].get("nextRunAt"),
            task["state"].get("lastBlockerType"),
            task["state"].get("lastBlockerReason"),
            task["timestamps"]["createdAt"],
            task["timestamps"]["updatedAt"],
            json.dumps(task, ensure_ascii=True),
        ),
    )


def _insert_event(conn: sqlite3.Connection, event: dict[str, Any]) -> None:
    validate_event(event)
    conn.execute(
        """
        INSERT INTO events (event_id, task_id, correlation_id, event_type, created_at, event_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event["eventId"],
            event["taskId"],
            event["correlationId"],
            event["eventType"],
            event["createdAt"],
            json.dumps(event, ensure_ascii=True),
        ),
    )


def _insert_artifact(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    kind: str,
    path: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    artifact_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO artifacts (artifact_id, task_id, kind, path, created_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            task_id,
            kind,
            path,
            now_iso(),
            json.dumps(metadata or {}, ensure_ascii=True),
        ),
    )
    return artifact_id


def emit_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    task: dict[str, Any],
    payload: dict[str, Any],
    evidence_refs: list[str] | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    event = default_event(
        event_type=event_type,
        task=task,
        payload=payload,
        evidence_refs=evidence_refs,
        role=role,
    )
    _insert_event(conn, event)
    daily_path = _append_event_jsonl(event)
    _insert_artifact(conn, task_id=task["taskId"], kind="event_log", path=str(daily_path))
    return event


def enqueue_task(conn: sqlite3.Connection, task: dict[str, Any]) -> dict[str, Any]:
    task["timestamps"]["updatedAt"] = now_iso()
    task["state"]["status"] = "queued"
    _upsert_task(conn, task)
    _persist_task_snapshot(task)
    emit_event(conn, event_type="task.created", task=task, payload={"status": "queued"})
    conn.commit()
    return task


def get_task(conn: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT task_json FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        return None
    return json.loads(row["task_json"])


def list_tasks(conn: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    if status:
        rows = conn.execute(
            "SELECT task_json FROM tasks WHERE status = ? ORDER BY created_at ASC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT task_json FROM tasks ORDER BY created_at ASC").fetchall()
    return [json.loads(row["task_json"]) for row in rows]


def parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_ready_to_run(task: dict[str, Any], current: datetime | None = None) -> bool:
    next_run_at = task["state"].get("nextRunAt")
    if not next_run_at:
        return True
    current = current or now_utc()
    return parse_iso8601(next_run_at) <= current


def is_code_task(task: dict[str, Any]) -> bool:
    return task["kind"] in CODE_TASK_KINDS


def normalize_evidence_refs(evidence_refs: list[str] | None) -> list[str]:
    return [item.strip() for item in (evidence_refs or []) if item and item.strip()]


def acceptance_prefixes(requirement: str) -> tuple[str, ...]:
    return ACCEPTANCE_ALIASES.get(requirement, (f"{requirement}:",))


def validate_completion_evidence(task: dict[str, Any], evidence_refs: list[str]) -> None:
    refs = normalize_evidence_refs(evidence_refs)
    if not refs:
        raise ValidationError("completion requires evidence references")
    missing = []
    requirements = list(task["acceptance"].get("required", []))
    if task["acceptance"].get("ciMustPass"):
        requirements.append("ci")
    for requirement in requirements:
        prefixes = acceptance_prefixes(requirement)
        if not any(any(ref.startswith(prefix) for prefix in prefixes) for ref in refs):
            missing.append(requirement)
    if missing:
        raise ValidationError(f"missing acceptance evidence: {', '.join(sorted(set(missing)))}")
    if is_code_task(task):
        code_requirements = {"test", "commit", "pr_or_pr_update"}
        for requirement in code_requirements:
            prefixes = acceptance_prefixes(requirement)
            if not any(any(ref.startswith(prefix) for prefix in prefixes) for ref in refs):
                raise ValidationError(f"code task completion requires {requirement} evidence")


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 9)


def claim_next_task(
    conn: sqlite3.Connection,
    *,
    worker_id: str,
    kinds_allowed: list[str] | None = None,
    lease_seconds: int = 30,
) -> dict[str, Any] | None:
    rows = list_tasks(conn, status="queued")
    rows = [task for task in rows if is_ready_to_run(task)]
    if kinds_allowed:
        rows = [task for task in rows if task["kind"] in kinds_allowed]
    rows.sort(key=lambda task: (_priority_rank(task["priority"]), task["timestamps"]["createdAt"]))
    if not rows:
        return None
    task = rows[0]
    task["state"]["status"] = "running"
    task["state"]["leaseOwner"] = worker_id
    task["state"]["leaseUntil"] = (now_utc() + timedelta(seconds=lease_seconds)).isoformat().replace("+00:00", "Z")
    task["state"]["nextRunAt"] = None
    task["timestamps"]["updatedAt"] = now_iso()
    _upsert_task(conn, task)
    _persist_task_snapshot(task)
    emit_event(
        conn,
        event_type="task.claimed",
        task=task,
        payload={"workerId": worker_id, "leaseSeconds": lease_seconds},
    )
    conn.commit()
    return task


def heartbeat(conn: sqlite3.Connection, *, task_id: str, worker_id: str, lease_seconds: int = 30) -> dict[str, Any]:
    task = get_task(conn, task_id)
    if task is None:
        raise KeyError(f"Unknown task_id: {task_id}")
    if task["state"].get("leaseOwner") != worker_id:
        raise ValidationError("lease owner mismatch")
    task["state"]["leaseUntil"] = (now_utc() + timedelta(seconds=lease_seconds)).isoformat().replace("+00:00", "Z")
    task["timestamps"]["updatedAt"] = now_iso()
    _upsert_task(conn, task)
    _persist_task_snapshot(task)
    emit_event(conn, event_type="task.progress", task=task, payload={"workerId": worker_id, "heartbeat": True})
    conn.commit()
    return task


def expire_leases(conn: sqlite3.Connection) -> int:
    expired = 0
    rows = list_tasks(conn, status="running")
    current = now_utc()
    for task in rows:
        lease_until = task["state"].get("leaseUntil")
        if not lease_until:
            continue
        lease_dt = datetime.fromisoformat(lease_until.replace("Z", "+00:00"))
        if lease_dt > current:
            continue
        task["state"]["status"] = "queued"
        task["state"]["leaseOwner"] = None
        task["state"]["leaseUntil"] = None
        task["state"]["nextRunAt"] = now_iso()
        task["timestamps"]["updatedAt"] = now_iso()
        _upsert_task(conn, task)
        _persist_task_snapshot(task)
        emit_event(conn, event_type="task.retry_scheduled", task=task, payload={"reason": "lease_expired"})
        expired += 1
    conn.commit()
    return expired


def complete_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    worker_id: str,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    task = get_task(conn, task_id)
    if task is None:
        raise KeyError(f"Unknown task_id: {task_id}")
    if task["state"].get("leaseOwner") not in {None, worker_id}:
        raise ValidationError("lease owner mismatch")
    refs = normalize_evidence_refs(evidence_refs)
    Executor().validate_completion(task, refs)
    task["state"]["status"] = "succeeded"
    task["state"]["leaseOwner"] = None
    task["state"]["leaseUntil"] = None
    task["state"]["nextRunAt"] = None
    task["timestamps"]["updatedAt"] = now_iso()
    _upsert_task(conn, task)
    task_path = _persist_task_snapshot(task)
    if str(task_path) not in refs:
        refs.append(str(task_path))
    emit_event(
        conn,
        event_type="task.completed",
        task=task,
        payload={"workerId": worker_id},
        evidence_refs=refs,
        role="executor",
    )
    for ref in refs:
        _insert_artifact(conn, task_id=task["taskId"], kind="evidence", path=ref)
    conn.commit()
    return task


def fail_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    worker_id: str,
    reason: str,
    retryable: bool = True,
    backoff_seconds: int = 30,
    role: str | None = None,
) -> dict[str, Any]:
    task = get_task(conn, task_id)
    if task is None:
        raise KeyError(f"Unknown task_id: {task_id}")
    task["state"]["attempts"] += 1
    task["timestamps"]["updatedAt"] = now_iso()
    max_retries = task["budget"]["maxRetries"]
    if retryable and task["state"]["attempts"] <= max_retries:
        task["state"]["status"] = "queued"
        next_run_at = (now_utc() + timedelta(seconds=backoff_seconds)).isoformat().replace("+00:00", "Z")
        task["state"]["nextRunAt"] = next_run_at
        payload = {"workerId": worker_id, "reason": reason, "retryInSeconds": backoff_seconds, "nextRunAt": next_run_at}
        event_type = "task.retry_scheduled"
    elif retryable:
        task["state"]["status"] = "needs_human"
        task["state"]["lastBlockerType"] = "HUMAN_BLOCKER"
        task["state"]["lastBlockerReason"] = reason
        payload = {"workerId": worker_id, "reason": reason, "maxRetriesReached": True}
        event_type = "task.needs_human"
    else:
        task["state"]["status"] = "failed"
        task["state"]["lastBlockerType"] = "HARD_BLOCKER"
        task["state"]["lastBlockerReason"] = reason
        payload = {"workerId": worker_id, "reason": reason}
        event_type = "task.failed"
    task["state"]["leaseOwner"] = None
    task["state"]["leaseUntil"] = None
    if event_type != "task.retry_scheduled":
        task["state"]["nextRunAt"] = None
    _upsert_task(conn, task)
    _persist_task_snapshot(task)
    emit_event(conn, event_type=event_type, task=task, payload=payload, role=role)
    conn.commit()
    return task


def block_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    worker_id: str,
    blocker_type: str,
    reason: str,
    role: str | None = None,
) -> dict[str, Any]:
    if blocker_type not in BLOCKER_TYPES:
        raise ValidationError("invalid blocker_type")
    task = get_task(conn, task_id)
    if task is None:
        raise KeyError(f"Unknown task_id: {task_id}")
    task["state"]["status"] = "needs_human" if blocker_type == "HUMAN_BLOCKER" else "blocked"
    task["state"]["leaseOwner"] = None
    task["state"]["leaseUntil"] = None
    task["state"]["nextRunAt"] = None
    task["state"]["lastBlockerType"] = blocker_type
    task["state"]["lastBlockerReason"] = reason
    task["timestamps"]["updatedAt"] = now_iso()
    _upsert_task(conn, task)
    _persist_task_snapshot(task)
    emit_event(
        conn,
        event_type="task.blocked",
        task=task,
        payload={"workerId": worker_id, "blockerType": blocker_type, "reason": reason},
        role=role,
    )
    conn.commit()
    return task


def handoff_task(
    conn: sqlite3.Connection,
    *,
    task: dict[str, Any],
    from_role: str,
    to_role: str,
    reason: str,
    derived_task: dict[str, Any] | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "fromRole": from_role,
        "toRole": to_role,
        "reason": reason,
    }
    if derived_task is not None:
        payload["derivedTaskId"] = derived_task["taskId"]
        payload["derivedTaskKind"] = derived_task["kind"]
    event = emit_event(
        conn,
        event_type="task.handoff",
        task=task,
        payload=payload,
        evidence_refs=evidence_refs,
        role=from_role,
    )
    conn.commit()
    return event


@dataclass
class RoutingDecision:
    objective: str
    requested_agent: str
    effective_agent: str
    reason: str
    execution_strategy: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "requestedAgent": self.requested_agent,
            "effectiveAgent": self.effective_agent,
            "reason": self.reason,
            "executionStrategy": self.execution_strategy,
        }


@dataclass
class RoutingPlan:
    decision: RoutingDecision
    model_router_command: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective": self.decision.objective,
            "requestedAgent": self.decision.requested_agent,
            "effectiveAgent": self.decision.effective_agent,
            "reason": self.decision.reason,
            "executionStrategy": self.decision.execution_strategy,
            "modelRouterCommand": self.model_router_command,
        }


def resolve_routing(
    *,
    kind: str,
    allowed_agents: list[str],
    requested_agent: str | None = None,
    routing_rules_path: Path = CONFIG_DIR / "routing_rules.json",
) -> RoutingDecision:
    rules = load_json(routing_rules_path)
    objective = rules.get("kindToObjective", {}).get(kind, rules.get("defaultObjective", "balanced_default"))
    default_requested = rules.get("requestedAgentDefaults", {}).get(kind, "gemini")
    requested = requested_agent or default_requested
    effective = requested if requested in allowed_agents else (allowed_agents[0] if allowed_agents else requested)
    reason = "requested agent allowed"
    if effective != requested:
        reason = f"allowedAgents restricts execution to {effective}"
    return RoutingDecision(
        objective=objective,
        requested_agent=requested,
        effective_agent=effective,
        reason=reason,
        execution_strategy=rules.get("defaultExecutionStrategy", "single"),
    )


def build_model_router_command(
    *,
    objective: str,
    container: str = "openclaw",
    profile: str = "prod",
    probe: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "model_router.py"),
        "--objective",
        objective,
        "--container",
        container,
        "--profile",
        profile,
        "--json",
    ]
    if probe:
        command.append("--probe")
    return command


def resolve_routing_plan(
    *,
    kind: str,
    allowed_agents: list[str],
    requested_agent: str | None = None,
    container: str = "openclaw",
    profile: str = "prod",
    probe: bool = False,
) -> RoutingPlan:
    decision = resolve_routing(
        kind=kind,
        allowed_agents=allowed_agents,
        requested_agent=requested_agent,
    )
    command = build_model_router_command(
        objective=decision.objective,
        container=container,
        profile=profile,
        probe=probe,
    )
    return RoutingPlan(decision=decision, model_router_command=command)


def split_telegram_message(
    text: str,
    *,
    hard_limit: int = 3500,
    target_limit: int = 2800,
    header: str | None = None,
) -> list[str]:
    if hard_limit <= 0 or target_limit <= 0:
        raise ValidationError("limits must be positive")
    if target_limit > hard_limit:
        target_limit = hard_limit
    normalized = text.strip()
    if not normalized:
        return [header] if header else [""]
    chunks: list[str] = []
    lines = normalized.splitlines()
    current = []
    current_len = 0
    for line in lines:
        line_len = len(line) + (1 if current else 0)
        if current and current_len + line_len > target_limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
            continue
        if not current and len(line) > hard_limit:
            for idx in range(0, len(line), target_limit):
                chunks.append(line[idx : idx + target_limit])
            current = []
            current_len = 0
            continue
        current.append(line)
        current_len += line_len
    if current:
        chunks.append("\n".join(current))
    if not header:
        return chunks
    total = len(chunks)
    output = []
    for idx, chunk in enumerate(chunks, start=1):
        output.append(f"{header}[part {idx}/{total}]\n\n{chunk}".strip())
    return output


def sanitize_telegram_text(text: str, artifact_ref: str | None = None) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    stripped = normalized.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        compact = stripped.replace("\n", "")
        if len(compact) > 1200:
            ref = artifact_ref or "artifact://telegram-payload"
            return f"Large JSON payload omitted. See {ref}."
    lines = normalized.splitlines()
    traceback_start = next((idx for idx, line in enumerate(lines) if line.startswith("Traceback")), None)
    if traceback_start is not None:
        excerpt = lines[traceback_start : traceback_start + 5]
        ref = artifact_ref or "artifact://stacktrace"
        return "\n".join(excerpt + [f"... truncated; see {ref}"])
    filtered = []
    log_pattern = re.compile(r"^(INFO|DEBUG|WARNING|ERROR|TRACE|[0-9]{4}-[0-9]{2}-[0-9]{2}T)")
    log_count = 0
    for line in lines:
        if log_pattern.match(line):
            log_count += 1
            if log_count > 5:
                continue
        filtered.append(line)
    if log_count > 5:
        ref = artifact_ref or "artifact://logs"
        filtered.append(f"... truncated log lines; see {ref}")
    return "\n".join(filtered)


def prepare_telegram_envelope(
    text: str,
    *,
    header: str | None = None,
    artifact_ref: str | None = None,
    hard_limit: int = 3500,
    target_limit: int = 2800,
) -> list[str]:
    sanitized = sanitize_telegram_text(text, artifact_ref=artifact_ref)
    return split_telegram_message(
        sanitized,
        hard_limit=hard_limit,
        target_limit=target_limit,
        header=header,
    )


def run_shell(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def execute_preflight(
    *,
    change_wave: dict[str, bool],
    touches_production: bool,
    is_parallel_candidate: bool,
    reused_prod_volumes: bool,
    reused_prod_workspace: bool,
    used_prod_telegram_token_on_candidate: bool,
    candidate_bind_loopback: bool = True,
    auth_multi_provider: bool = False,
    docker_runner: Callable[[list[str]], tuple[int, str, str]] = run_shell,
    shell_runner: Callable[[list[str]], tuple[int, str, str]] = run_shell,
    policy_path: Path = PREFLIGHT_POLICY_PATH,
) -> dict[str, Any]:
    for key in ("infra", "policy", "routing", "auth"):
        if key not in change_wave:
            raise ValidationError(f"missing changeWave.{key}")

    result = {
        "preflight": {
            "dockerContextChecked": False,
            "singleContextSession": False,
            "blueHealthy": not touches_production,
            "isParallelCandidate": is_parallel_candidate,
            "reusedProdVolumes": reused_prod_volumes,
            "reusedProdWorkspace": reused_prod_workspace,
            "usedProdTelegramTokenOnCandidate": used_prod_telegram_token_on_candidate,
            "candidateBindLoopback": candidate_bind_loopback,
            "authMultiProvider": auth_multi_provider,
            "changeWave": change_wave,
            "allowedToProceed": True,
            "denyReason": "",
        }
    }
    policy = load_preflight_policy(policy_path)

    rc_ls, _, _ = docker_runner(["docker", "context", "ls"])
    rc_show, stdout_show, _ = docker_runner(["docker", "context", "show"])
    result["preflight"]["dockerContextChecked"] = rc_ls == 0 and rc_show == 0
    result["preflight"]["singleContextSession"] = bool(stdout_show.strip()) if rc_show == 0 else False

    if touches_production:
        checks = [
            ["docker", "ps", "--filter", "name=openclaw"],
            ["docker", "exec", "openclaw", "openclaw", "--profile", "prod", "gateway", "health"],
            ["docker", "exec", "openclaw", "openclaw", "--profile", "prod", "status"],
        ]
        blue_healthy = True
        for command in checks:
            rc, _, _ = docker_runner(command)
            if rc != 0:
                blue_healthy = False
                break
        if blue_healthy:
            rc_tail, _, _ = shell_runner(
                [
                    "bash",
                    "-lc",
                    "tail -n 120 ~/openclaw/logs/openclaw-$(date +%F).log >/dev/null",
                ]
            )
            blue_healthy = rc_tail == 0
        result["preflight"]["blueHealthy"] = blue_healthy

    deny_reasons = []
    if not result["preflight"]["dockerContextChecked"]:
        deny_reasons.append("docker_context_check_failed")
    if not result["preflight"]["singleContextSession"]:
        deny_reasons.append("single_context_session_required")
    if touches_production and not result["preflight"]["blueHealthy"]:
        deny_reasons.append("blue_not_healthy")
    if is_parallel_candidate and reused_prod_volumes:
        deny_reasons.append("candidate_reuses_prod_volumes")
    if is_parallel_candidate and reused_prod_workspace:
        deny_reasons.append("candidate_reuses_prod_workspace")
    if is_parallel_candidate and used_prod_telegram_token_on_candidate:
        deny_reasons.append("candidate_uses_prod_telegram_token")
    if is_parallel_candidate and not candidate_bind_loopback:
        deny_reasons.append("candidate_bind_not_loopback")
    if auth_multi_provider:
        deny_reasons.append("auth+multi-provider")
    for combo in policy.get("forbiddenWaveCombos", []):
        parts = combo.split("+")
        if combo == "auth+multi-provider":
            continue
        if all(change_wave.get(part, False) for part in parts):
            deny_reasons.append(combo)

    if deny_reasons:
        result["preflight"]["allowedToProceed"] = False
        result["preflight"]["denyReason"] = ",".join(deny_reasons)

    validate_preflight(result)
    return result


class Planner:
    role = "planner"

    def derive_task(self, task: dict[str, Any], *, kind: str, title: str) -> dict[str, Any]:
        derived = default_task(
            kind=kind,
            title=title,
            workflow=task["workflow"],
            execution_mode=task["executionMode"],
            priority=task["priority"],
            source={**task["source"], "parentTaskId": task["taskId"]},
            routing=dict(task["routing"]),
            issue_id=task.get("issueId"),
            repo=task.get("repo"),
            branch=task.get("branch"),
        )
        derived["correlationId"] = task["correlationId"]
        validate_task(derived)
        return derived


class Executor:
    role = "executor"

    def validate_completion(self, task: dict[str, Any], evidence_refs: list[str]) -> None:
        validate_completion_evidence(task, evidence_refs)


def persist_report(
    conn: sqlite3.Connection,
    *,
    task: dict[str, Any],
    name: str,
    payload: dict[str, Any],
    kind: str = "report",
) -> str:
    ensure_dir(DEFAULT_REPORTS_DIR)
    path = DEFAULT_REPORTS_DIR / f"{task['taskId']}-{name}.json"
    dump_json(path, payload)
    _insert_artifact(conn, task_id=task["taskId"], kind=kind, path=str(path))
    return str(path)


@dataclass
class SupervisorResult:
    action: str
    reason: str
    derived_tasks: list[dict[str, Any]]
    blocked_tasks: list[str]
    escalated_tasks: list[str]
    observed_counts: dict[str, int]


class Supervisor:
    def __init__(
        self,
        *,
        safe_mode: bool | None = None,
        max_derived_tasks_per_root: int = 5,
        docker_runner: Callable[[list[str]], tuple[int, str, str]] = run_shell,
        shell_runner: Callable[[list[str]], tuple[int, str, str]] = run_shell,
    ):
        settings = load_supervisor_settings()
        self.safe_mode = settings["safeMode"] if safe_mode is None else safe_mode
        self.max_derived_tasks_per_root = max_derived_tasks_per_root
        self.docker_runner = docker_runner
        self.shell_runner = shell_runner
        self.planner = Planner()

    def should_apply_preflight(self, task: dict[str, Any]) -> bool:
        return task["kind"] in SENSITIVE_KINDS

    def derive_follow_up(self, task: dict[str, Any], title: str, kind: str) -> dict[str, Any]:
        return self.planner.derive_task(task, kind=kind, title=title)

    def preflight_request(self, task: dict[str, Any]) -> dict[str, Any]:
        request = dict(task.get("preflight", {}))
        change_wave = dict(request.get("changeWave", {}))
        for key in ("infra", "policy", "routing", "auth"):
            change_wave.setdefault(key, False)
        inferred_key = {
            "ops_deploy": "infra",
            "runtime_change": "infra",
            "policy_change": "policy",
            "routing_change": "routing",
            "auth_change": "auth",
        }.get(task["kind"])
        if inferred_key:
            change_wave[inferred_key] = True
        request["changeWave"] = change_wave
        request.setdefault("touchesProduction", bool(task["constraints"].get("productionImpact")))
        request.setdefault("isParallelCandidate", False)
        request.setdefault("reusedProdVolumes", False)
        request.setdefault("reusedProdWorkspace", False)
        request.setdefault("usedProdTelegramTokenOnCandidate", False)
        request.setdefault("candidateBindLoopback", True)
        request.setdefault("authMultiProvider", False)
        return request

    def cycle(self, conn: sqlite3.Connection, tasks: list[dict[str, Any]] | None = None) -> SupervisorResult:
        tasks = tasks or list_tasks(conn)
        queued = [task for task in tasks if task["state"]["status"] == "queued"]
        blocked = [task for task in tasks if task["state"]["status"] == "blocked"]
        failed = [task for task in tasks if task["state"]["status"] == "failed"]
        if not queued:
            return SupervisorResult(
                action="noop",
                reason="no queued tasks",
                derived_tasks=[],
                blocked_tasks=[],
                escalated_tasks=[],
                observed_counts={"queued": 0, "blocked": len(blocked), "failed": len(failed)},
            )

        sensitive = [task for task in queued if self.should_apply_preflight(task)]
        if self.safe_mode:
            for task in sensitive[: self.max_derived_tasks_per_root]:
                emit_event(
                    conn,
                    event_type="task.progress",
                    task=task,
                    payload={"mode": "safe", "observation": "sensitive task observed by supervisor"},
                    role="supervisor",
                )
            conn.commit()
            return SupervisorResult(
                action="observe_only",
                reason="safe mode enabled",
                derived_tasks=sensitive[: self.max_derived_tasks_per_root],
                blocked_tasks=[],
                escalated_tasks=[],
                observed_counts={"queued": len(queued), "blocked": len(blocked), "failed": len(failed)},
            )

        derived = []
        blocked_ids: list[str] = []
        escalated_ids: list[str] = []
        for task in sensitive[: self.max_derived_tasks_per_root]:
            request = self.preflight_request(task)
            result = execute_preflight(
                change_wave=request["changeWave"],
                touches_production=request["touchesProduction"],
                is_parallel_candidate=request["isParallelCandidate"],
                reused_prod_volumes=request["reusedProdVolumes"],
                reused_prod_workspace=request["reusedProdWorkspace"],
                used_prod_telegram_token_on_candidate=request["usedProdTelegramTokenOnCandidate"],
                candidate_bind_loopback=request["candidateBindLoopback"],
                auth_multi_provider=request["authMultiProvider"],
                docker_runner=self.docker_runner,
                shell_runner=self.shell_runner,
            )
            report_ref = persist_report(conn, task=task, name="preflight", payload=result, kind="preflight_report")
            if not result["preflight"]["allowedToProceed"]:
                block_task(
                    conn,
                    task_id=task["taskId"],
                    worker_id="supervisor",
                    blocker_type="HARD_BLOCKER",
                    reason=result["preflight"]["denyReason"],
                    role="supervisor",
                )
                blocked_ids.append(task["taskId"])
                continue
            derived_task = self.derive_follow_up(task, f"Plan execution for {task['title']}", "planning")
            enqueue_task(conn, derived_task)
            handoff_task(
                conn,
                task=task,
                from_role="supervisor",
                to_role=self.planner.role,
                reason="preflight_passed",
                derived_task=derived_task,
                evidence_refs=[report_ref],
            )
            block_task(
                conn,
                task_id=task["taskId"],
                worker_id="supervisor",
                blocker_type="SOFT_BLOCKER",
                reason=f"awaiting_planner:{derived_task['taskId']}",
                role="supervisor",
            )
            derived.append(derived_task)
            blocked_ids.append(task["taskId"])
        for task in failed[: self.max_derived_tasks_per_root]:
            block_task(
                conn,
                task_id=task["taskId"],
                worker_id="supervisor",
                blocker_type="HUMAN_BLOCKER",
                reason="failed_task_requires_human_follow_up",
                role="supervisor",
            )
            escalated_ids.append(task["taskId"])
        return SupervisorResult(
            action="processed_sensitive_queue",
            reason="supervisor cycle executed",
            derived_tasks=derived,
            blocked_tasks=blocked_ids,
            escalated_tasks=escalated_ids,
            observed_counts={"queued": len(queued), "blocked": len(blocked), "failed": len(failed)},
        )


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent OS control-plane utilities.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_db_parser = sub.add_parser("init-db", help="Initialize local Agent OS SQLite database")
    init_db_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))

    enqueue_parser = sub.add_parser("enqueue-demo", help="Enqueue a demo task")
    enqueue_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    enqueue_parser.add_argument("--kind", default="default_chat")
    enqueue_parser.add_argument("--title", required=True)
    enqueue_parser.add_argument("--workflow", default="operate-and-grow")
    enqueue_parser.add_argument("--execution-mode", default="AUTO")
    enqueue_parser.add_argument("--priority", default="medium")
    enqueue_parser.add_argument("--requested-agent", default=None)
    enqueue_parser.add_argument("--allowed-agents", default="gemini")
    enqueue_parser.add_argument("--touches-production", action="store_true")
    enqueue_parser.add_argument("--parallel-candidate", action="store_true")
    enqueue_parser.add_argument("--reused-prod-volumes", action="store_true")
    enqueue_parser.add_argument("--reused-prod-workspace", action="store_true")
    enqueue_parser.add_argument("--used-prod-telegram-token", action="store_true")
    enqueue_parser.add_argument("--candidate-bind-not-loopback", action="store_true")
    enqueue_parser.add_argument("--auth-multi-provider", action="store_true")
    enqueue_parser.add_argument("--infra", action="store_true")
    enqueue_parser.add_argument("--policy", action="store_true")
    enqueue_parser.add_argument("--routing", action="store_true")
    enqueue_parser.add_argument("--auth", action="store_true")

    claim_parser = sub.add_parser("claim-next", help="Claim next task from the queue")
    claim_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    claim_parser.add_argument("--worker-id", required=True)
    claim_parser.add_argument("--lease-seconds", type=int, default=30)
    claim_parser.add_argument("--kinds-allowed", default="")

    heartbeat_parser = sub.add_parser("heartbeat", help="Renew task lease")
    heartbeat_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    heartbeat_parser.add_argument("--task-id", required=True)
    heartbeat_parser.add_argument("--worker-id", required=True)
    heartbeat_parser.add_argument("--lease-seconds", type=int, default=30)

    complete_parser = sub.add_parser("complete", help="Mark task as succeeded")
    complete_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    complete_parser.add_argument("--task-id", required=True)
    complete_parser.add_argument("--worker-id", required=True)
    complete_parser.add_argument("--evidence-ref", action="append", default=[])

    fail_parser = sub.add_parser("fail", help="Fail or retry a task")
    fail_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    fail_parser.add_argument("--task-id", required=True)
    fail_parser.add_argument("--worker-id", required=True)
    fail_parser.add_argument("--reason", required=True)
    fail_parser.add_argument("--no-retry", action="store_true")

    block_parser = sub.add_parser("block", help="Block a task")
    block_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    block_parser.add_argument("--task-id", required=True)
    block_parser.add_argument("--worker-id", required=True)
    block_parser.add_argument("--blocker-type", required=True)
    block_parser.add_argument("--reason", required=True)

    list_parser = sub.add_parser("list", help="List tasks")
    list_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    list_parser.add_argument("--status", default=None)

    expire_parser = sub.add_parser("expire-leases", help="Requeue tasks with expired leases")
    expire_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))

    route_parser = sub.add_parser("route", help="Resolve routing for a task kind")
    route_parser.add_argument("--kind", required=True)
    route_parser.add_argument("--requested-agent", default=None)
    route_parser.add_argument("--allowed-agents", default="gemini")
    route_parser.add_argument("--container", default="openclaw")
    route_parser.add_argument("--profile", default="prod")
    route_parser.add_argument("--probe", action="store_true")

    envelope_parser = sub.add_parser("envelope", help="Chunk a Telegram message")
    envelope_parser.add_argument("--header", default="[AgentOS]")
    envelope_parser.add_argument("--file", default=None)
    envelope_parser.add_argument("--artifact-ref", default=None)

    preflight_parser = sub.add_parser("preflight", help="Run executable production preflight")
    preflight_parser.add_argument("--touches-production", action="store_true")
    preflight_parser.add_argument("--parallel-candidate", action="store_true")
    preflight_parser.add_argument("--reused-prod-volumes", action="store_true")
    preflight_parser.add_argument("--reused-prod-workspace", action="store_true")
    preflight_parser.add_argument("--used-prod-telegram-token", action="store_true")
    preflight_parser.add_argument("--candidate-bind-not-loopback", action="store_true")
    preflight_parser.add_argument("--auth-multi-provider", action="store_true")
    preflight_parser.add_argument("--infra", action="store_true")
    preflight_parser.add_argument("--policy", action="store_true")
    preflight_parser.add_argument("--routing", action="store_true")
    preflight_parser.add_argument("--auth", action="store_true")

    supervisor_parser = sub.add_parser("supervisor-cycle", help="Run one supervisor cycle against queued tasks")
    supervisor_parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    mode_group = supervisor_parser.add_mutually_exclusive_group()
    mode_group.add_argument("--safe-mode", action="store_true")
    mode_group.add_argument("--unsafe-mode", action="store_true")

    sub.add_parser("validate-schemas", help="Validate control-plane schemas and local policy files")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-db":
        path = init_db(Path(args.db))
        _print_json({"db": str(path), "initialized": True})
        return 0

    if args.command == "route":
        allowed_agents = [item for item in args.allowed_agents.split(",") if item]
        plan = resolve_routing_plan(
            kind=args.kind,
            allowed_agents=allowed_agents,
            requested_agent=args.requested_agent,
            container=args.container,
            profile=args.profile,
            probe=args.probe,
        )
        _print_json(plan.as_dict())
        return 0

    if args.command == "envelope":
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        _print_json({"parts": prepare_telegram_envelope(text, header=args.header, artifact_ref=args.artifact_ref)})
        return 0

    if args.command == "preflight":
        result = execute_preflight(
            change_wave={
                "infra": args.infra,
                "policy": args.policy,
                "routing": args.routing,
                "auth": args.auth,
            },
            touches_production=args.touches_production,
            is_parallel_candidate=args.parallel_candidate,
            reused_prod_volumes=args.reused_prod_volumes,
            reused_prod_workspace=args.reused_prod_workspace,
            used_prod_telegram_token_on_candidate=args.used_prod_telegram_token,
            candidate_bind_loopback=not args.candidate_bind_not_loopback,
            auth_multi_provider=args.auth_multi_provider,
        )
        _print_json(result)
        return 0 if result["preflight"]["allowedToProceed"] else 1

    if args.command == "validate-schemas":
        read_schema("task.schema.json")
        read_schema("event.schema.json")
        read_schema("preflight.schema.json")
        load_preflight_policy()
        load_supervisor_settings()
        _print_json({"valid": True, "schemas": 3, "policy": str(PREFLIGHT_POLICY_PATH), "supervisorConfig": str(SUPERVISOR_CONFIG_PATH)})
        return 0

    db_path = Path(getattr(args, "db", DEFAULT_DB_PATH))
    init_db(db_path)
    conn = open_db(db_path)
    try:
        if args.command == "enqueue-demo":
            allowed_agents = [item for item in args.allowed_agents.split(",") if item]
            decision = resolve_routing(
                kind=args.kind,
                allowed_agents=allowed_agents,
                requested_agent=args.requested_agent,
            )
            task = default_task(
                kind=args.kind,
                title=args.title,
                workflow=args.workflow,
                execution_mode=args.execution_mode,
                priority=args.priority,
                source={"channel": "manual"},
                routing=decision.as_dict(),
                preflight={
                    "touchesProduction": args.touches_production,
                    "isParallelCandidate": args.parallel_candidate,
                    "reusedProdVolumes": args.reused_prod_volumes,
                    "reusedProdWorkspace": args.reused_prod_workspace,
                    "usedProdTelegramTokenOnCandidate": args.used_prod_telegram_token,
                    "candidateBindLoopback": not args.candidate_bind_not_loopback,
                    "authMultiProvider": args.auth_multi_provider,
                    "changeWave": {
                        "infra": args.infra,
                        "policy": args.policy,
                        "routing": args.routing,
                        "auth": args.auth,
                    },
                }
                if any(
                    [
                        args.touches_production,
                        args.parallel_candidate,
                        args.reused_prod_volumes,
                        args.reused_prod_workspace,
                        args.used_prod_telegram_token,
                        args.candidate_bind_not_loopback,
                        args.auth_multi_provider,
                        args.infra,
                        args.policy,
                        args.routing,
                        args.auth,
                        args.kind in SENSITIVE_KINDS,
                    ]
                )
                else None,
            )
            _print_json(enqueue_task(conn, task))
            return 0

        if args.command == "claim-next":
            kinds_allowed = [item for item in args.kinds_allowed.split(",") if item]
            claimed = claim_next_task(
                conn,
                worker_id=args.worker_id,
                kinds_allowed=kinds_allowed or None,
                lease_seconds=args.lease_seconds,
            )
            _print_json({"task": claimed})
            return 0 if claimed else 1

        if args.command == "heartbeat":
            _print_json(
                heartbeat(
                    conn,
                    task_id=args.task_id,
                    worker_id=args.worker_id,
                    lease_seconds=args.lease_seconds,
                )
            )
            return 0

        if args.command == "complete":
            _print_json(
                complete_task(
                    conn,
                    task_id=args.task_id,
                    worker_id=args.worker_id,
                    evidence_refs=args.evidence_ref,
                )
            )
            return 0

        if args.command == "fail":
            _print_json(
                fail_task(
                    conn,
                    task_id=args.task_id,
                    worker_id=args.worker_id,
                    reason=args.reason,
                    retryable=not args.no_retry,
                )
            )
            return 0

        if args.command == "block":
            _print_json(
                block_task(
                    conn,
                    task_id=args.task_id,
                    worker_id=args.worker_id,
                    blocker_type=args.blocker_type,
                    reason=args.reason,
                )
            )
            return 0

        if args.command == "list":
            _print_json({"tasks": list_tasks(conn, status=args.status)})
            return 0

        if args.command == "expire-leases":
            _print_json({"expired": expire_leases(conn)})
            return 0

        if args.command == "supervisor-cycle":
            safe_mode = None
            if args.safe_mode:
                safe_mode = True
            elif args.unsafe_mode:
                safe_mode = False
            supervisor = Supervisor(safe_mode=safe_mode)
            result = supervisor.cycle(conn)
            _print_json(
                {
                    "action": result.action,
                    "reason": result.reason,
                    "derivedTasks": result.derived_tasks,
                    "blockedTasks": result.blocked_tasks,
                    "escalatedTasks": result.escalated_tasks,
                    "observedCounts": result.observed_counts,
                }
            )
            return 0
    finally:
        conn.close()

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
