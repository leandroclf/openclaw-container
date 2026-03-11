#!/usr/bin/env python3
"""Consume delivery execution result artifacts and reconcile Agent OS task state."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import agentos

FRESHNESS_LIMIT = timedelta(hours=6)


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def archive_processed_artifacts(bridge_dir: Path, request_id: str) -> None:
    history_dir = bridge_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "delivery-execution-request.json",
        "delivery-execution-request.md",
        "delivery-handoff-state.json",
        "delivery-execution-intent.json",
        "delivery-execution-intent.md",
        "delivery-execution-state.json",
        "delivery-execution-result.json",
        "delivery-execution-agent-output.json",
    ]:
        source = bridge_dir / name
        if not source.exists():
            continue
        target = history_dir / f"{request_id}-{name}"
        shutil.move(str(source), str(target))


def build_evidence_refs(result: dict, result_path: Path) -> list[str]:
    refs = [f"report:{result_path}"]
    for item in result.get("tests", []):
        refs.append(f"test:{item}")
    commit_sha = result.get("commit")
    if commit_sha:
        refs.append(f"commit:{commit_sha}")
    pr_url = result.get("pr")
    if pr_url:
        refs.append(f"pr:{pr_url}")
    ci_status = str(result.get("ciStatus") or "").strip().lower()
    if ci_status in {"pass", "passed", "success", "succeeded"}:
        refs.append("ci:pass")
    return refs


def reconcile_success(conn, request: dict, result: dict, result_path: Path) -> dict[str, str]:
    task_id = request["task"]["taskId"]
    task = agentos.get_task(conn, task_id)
    if task is None:
        raise KeyError(f"unknown task id in request: {task_id}")
    evidence_refs = build_evidence_refs(result, result_path)
    agentos.complete_task(conn, task_id=task_id, worker_id="delivery-result-reconcile", evidence_refs=evidence_refs)
    parent_id = task["source"].get("parentTaskId")
    if parent_id:
        agentos.complete_task(
            conn,
            task_id=parent_id,
            worker_id="delivery-result-reconcile",
            evidence_refs=[f"report:{result_path}"],
        )
    return {"taskId": task_id, "parentTaskId": parent_id or ""}


def reconcile_blocked(conn, request: dict, result: dict) -> dict[str, str]:
    task_id = request["task"]["taskId"]
    blocker_type = result.get("blockerType") or "HARD_BLOCKER"
    if blocker_type not in agentos.BLOCKER_TYPES:
        blocker_type = "SOFT_BLOCKER"
    blocker_reason = result.get("blockerReason") or "delivery_execution_blocked"
    agentos.block_task(
        conn,
        task_id=task_id,
        worker_id="delivery-result-reconcile",
        blocker_type=blocker_type,
        reason=blocker_reason,
        role="executor",
    )
    return {"taskId": task_id, "blockerType": blocker_type, "blockerReason": blocker_reason}


def reconcile_failed(conn, request: dict, result: dict) -> dict[str, str]:
    task_id = request["task"]["taskId"]
    reason = result.get("blockerReason") or "delivery_execution_failed"
    agentos.fail_task(
        conn,
        task_id=task_id,
        worker_id="delivery-result-reconcile",
        reason=reason,
        retryable=False,
        role="executor",
    )
    return {"taskId": task_id, "reason": reason}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--bridge-dir", required=True)
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    request_path = bridge_dir / "delivery-execution-request.json"
    result_path = bridge_dir / "delivery-execution-result.json"
    state_path = bridge_dir / "delivery-result-state.json"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    state = load_json(state_path) if state_path.exists() else {
        "updatedAt": None,
        "lastRequestId": None,
        "lastResultUpdatedAt": None,
        "status": "empty",
        "notes": [],
    }

    if not request_path.exists() or not result_path.exists():
        state.update(
            {
                "updatedAt": now.isoformat().replace("+00:00", "Z"),
                "status": "no_result",
                "notes": ["Request/result artifact missing for reconciliation."],
            }
        )
        save_json(state_path, state)
        print("[DELIVERY_RECONCILE_NO_RESULT]")
        return

    request = load_json(request_path)
    result = load_json(result_path)
    request_id = request.get("requestId")
    result_updated_at = parse_timestamp(result.get("updatedAt"))
    notes: list[str] = []

    if result.get("requestId") != request_id:
        notes.append("Result requestId does not match current request.")
    if result_updated_at is None or (now - result_updated_at) > FRESHNESS_LIMIT:
        notes.append("Result artifact is stale.")
    if state.get("lastRequestId") == request_id and state.get("lastResultUpdatedAt") == result.get("updatedAt"):
        notes.append("Result already reconciled.")

    if notes:
        state.update(
            {
                "updatedAt": now.isoformat().replace("+00:00", "Z"),
                "lastRequestId": request_id,
                "lastResultUpdatedAt": result.get("updatedAt"),
                "status": "blocked",
                "notes": notes,
            }
        )
        save_json(state_path, state)
        print(f"[DELIVERY_RECONCILE_BLOCKED] requestId={request_id}")
        return

    agentos.init_db(db_path)
    conn = agentos.open_db(db_path)
    try:
        outcome = result.get("status")
        details: dict[str, str]
        if outcome in {"succeeded", "completed"}:
            details = reconcile_success(conn, request, result, result_path)
            status = "succeeded"
        elif outcome == "blocked":
            details = reconcile_blocked(conn, request, result)
            status = "blocked"
        else:
            details = reconcile_failed(conn, request, result)
            status = "failed"
    finally:
        conn.close()

    state.update(
        {
            "updatedAt": now.isoformat().replace("+00:00", "Z"),
            "lastRequestId": request_id,
            "lastResultUpdatedAt": result.get("updatedAt"),
            "status": status,
            "notes": [f"Reconciled delivery result: {status}"],
            "details": details,
        }
    )
    save_json(state_path, state)
    archive_processed_artifacts(bridge_dir, request_id)
    print(f"[DELIVERY_RECONCILE_{status.upper()}] requestId={request_id}")


if __name__ == "__main__":
    main()
