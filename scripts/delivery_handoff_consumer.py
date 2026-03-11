#!/usr/bin/env python3
"""Evaluate delivery handoff readiness without mutating product repositories."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

FRESHNESS_LIMIT = timedelta(minutes=45)


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    request_path = bridge_dir / "delivery-execution-request.json"
    state_path = bridge_dir / "delivery-handoff-state.json"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    state = load_json(state_path) if state_path.exists() else {
        "updatedAt": None,
        "lastEvaluatedRequestId": None,
        "lastActivatedRequestId": None,
        "status": "empty",
        "notes": [],
    }

    if not request_path.exists():
        state.update(
            {
                "updatedAt": now.isoformat().replace("+00:00", "Z"),
                "status": "no_request",
                "notes": ["No delivery handoff request artifact present."],
            }
        )
        save_json(state_path, state)
        print("[DELIVERY_CONSUMER_NO_REQUEST]")
        return

    request = load_json(request_path)
    request_id = request.get("requestId")
    created_at = parse_timestamp(request.get("createdAt"))
    request_status = request.get("status")
    repo_readiness = request.get("repoReadiness", {})
    task = request.get("task", {})

    notes: list[str] = []
    if created_at is None or (now - created_at) > FRESHNESS_LIMIT:
        notes.append("Request is stale.")
    if request_status != "pending_internal_consumption":
        notes.append(f"Unexpected request status: {request_status}")
    if not repo_readiness.get("canExecuteMutations"):
        notes.append(f"Repo not ready for execution: {repo_readiness.get('denyReason', 'unknown')}")
    acceptance = task.get("acceptance", {})
    required = acceptance.get("required", [])
    if task.get("kind") == "code_impl":
        for item in ("test", "commit", "pr_or_pr_update"):
            if item not in required:
                notes.append(f"Missing code acceptance requirement: {item}")
        if not acceptance.get("ciMustPass", False):
            notes.append("Code execution handoff requires ciMustPass=true.")
    if state.get("lastActivatedRequestId") == request_id:
        notes.append("Request already activated previously.")

    ready = not notes
    state.update(
        {
            "updatedAt": now.isoformat().replace("+00:00", "Z"),
            "lastEvaluatedRequestId": request_id,
            "status": "ready" if ready else "blocked",
            "notes": notes or ["Request is eligible for future activation."],
        }
    )

    if args.activate and ready:
        state["lastActivatedRequestId"] = request_id
        state["status"] = "activated"
        state["notes"] = [
            "Activation flag used. This consumer records readiness only; no internal trigger is executed here.",
        ]
        save_json(state_path, state)
        print(f"[DELIVERY_CONSUMER_ACTIVATED] requestId={request_id}")
        return

    save_json(state_path, state)
    if ready:
        print(f"[DELIVERY_CONSUMER_READY] requestId={request_id}")
    else:
        print(f"[DELIVERY_CONSUMER_BLOCKED] requestId={request_id}")


if __name__ == "__main__":
    main()
