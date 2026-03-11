#!/usr/bin/env python3
"""Build and optionally activate a delivery execution intent from a ready handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
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


def run_json(cmd: list[str]) -> object:
    return json.loads(subprocess.check_output(cmd, text=True))


def run_text(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def resolve_cron_job(profile: str, cron_name: str) -> dict | None:
    payload = run_json(["docker", "exec", "openclaw", "openclaw", "--profile", profile, "cron", "list", "--json"])
    jobs = payload["jobs"] if isinstance(payload, dict) else payload
    for job in jobs:
        if job.get("name") == cron_name:
            return job
    return None


def render_md(intent: dict) -> str:
    lines = [
        "# Delivery Execution Intent",
        "",
        f"requestId: `{intent['requestId']}`",
        f"generatedAt: `{intent['generatedAt']}`",
        f"mode: `{intent['mode']}`",
        f"status: `{intent['status']}`",
        "",
        "## Guards",
        f"- internalDeliveryPrimary: `{intent['guards']['internalDeliveryPrimary']}`",
        f"- consumerReady: `{intent['guards']['consumerReady']}`",
        f"- requestFresh: `{intent['guards']['requestFresh']}`",
        f"- duplicateExecutionPrevented: `{intent['guards']['duplicateExecutionPrevented']}`",
        f"- targetCronEnabled: `{intent['guards']['targetCronEnabled']}`",
        f"- targetCronRunning: `{intent['guards']['targetCronRunning']}`",
        "",
        "## Source Task",
        f"- issueId: `{intent['source']['issueId']}`",
        f"- taskId: `{intent['source']['taskId']}`",
        f"- repo: `{intent['source']['repo']}`",
        f"- branch: `{intent['source']['branch']}`",
        f"- kind: `{intent['source']['kind']}`",
        "",
        "## Execution",
        f"- triggerMethod: {intent['execution'].get('triggerMethod', 'not configured')}",
        f"- sideEffect: {intent['execution'].get('sideEffect', 'none in dry-run mode')}",
    ]
    if intent["execution"].get("jobId"):
        lines.append(f"- cronJobId: `{intent['execution']['jobId']}`")
    if intent["execution"].get("result"):
        lines.append(f"- triggerResult: `{intent['execution']['result']}`")
    if intent.get("notes"):
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in intent["notes"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--profile", default="prod")
    parser.add_argument("--trigger-cron-name", default="Autopilot sequential delivery cycle")
    parser.add_argument("--trigger-cron-id", default=None)
    parser.add_argument("--trigger-timeout-ms", default="900000")
    parser.add_argument(
        "--internal-delivery-primary",
        choices=["true", "false"],
        default="true",
        help="Keep true while the internal delivery cron remains the primary scheduler.",
    )
    parser.add_argument(
        "--allow-disabled-cron",
        action="store_true",
        help="Allow activation even if the target cron is disabled, as long as it still resolves by name.",
    )
    args = parser.parse_args()

    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    request_path = bridge_dir / "delivery-execution-request.json"
    consumer_state_path = bridge_dir / "delivery-handoff-state.json"
    execution_state_path = bridge_dir / "delivery-execution-state.json"
    intent_json_path = bridge_dir / "delivery-execution-intent.json"
    intent_md_path = bridge_dir / "delivery-execution-intent.md"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    internal_primary = args.internal_delivery_primary == "true"

    if not request_path.exists():
        print("[DELIVERY_EXECUTION_NO_REQUEST]")
        return
    if not consumer_state_path.exists():
        print("[DELIVERY_EXECUTION_BLOCKED] consumer state missing")
        return

    request = load_json(request_path)
    consumer_state = load_json(consumer_state_path)
    execution_state = load_json(execution_state_path) if execution_state_path.exists() else {
        "updatedAt": None,
        "lastPreparedRequestId": None,
        "lastExecutedRequestId": None,
        "status": "empty",
        "notes": [],
    }

    request_id = request.get("requestId")
    created_at = parse_timestamp(request.get("createdAt"))
    request_fresh = created_at is not None and (now - created_at) <= FRESHNESS_LIMIT
    consumer_ready = consumer_state.get("status") == "ready"
    duplicate_prevented = execution_state.get("lastExecutedRequestId") != request_id

    target_job = resolve_cron_job(args.profile, args.trigger_cron_name)
    target_enabled = bool(target_job.get("enabled", False)) if target_job else False
    target_running = bool(target_job and target_job.get("state", {}).get("runningAtMs"))
    target_job_id = args.trigger_cron_id or (target_job.get("id") if target_job else None)

    notes: list[str] = []
    if internal_primary:
        notes.append("Internal delivery cron is still the primary scheduler.")
    if not consumer_ready:
        notes.append("Delivery consumer state is not ready.")
    if not request_fresh:
        notes.append("Delivery request is stale.")
    if not duplicate_prevented:
        notes.append("Request was already executed previously.")
    if not target_job_id:
        notes.append(f"Target cron job not found: {args.trigger_cron_name}")
    elif not target_enabled and not args.allow_disabled_cron:
        notes.append("Target cron job is disabled.")
    if target_running:
        notes.append("Target cron job is already running.")

    trigger_method = "none"
    side_effect = "none in dry-run mode"
    trigger_result = None
    trigger_output = None
    if args.activate and not notes:
        trigger_method = f"openclaw cron run {args.trigger_cron_name}"
        side_effect = "trigger host-approved internal sequential delivery cycle"
        try:
            trigger_output = run_text(
                [
                    "docker",
                    "exec",
                    "openclaw",
                    "openclaw",
                    "--profile",
                    args.profile,
                    "cron",
                    "run",
                    target_job_id,
                    "--timeout",
                    args.trigger_timeout_ms,
                ]
            )
            trigger_result = "triggered"
        except subprocess.CalledProcessError as exc:
            trigger_output = (exc.output or "").strip()
            trigger_result = "failed"
            notes.append("Cron trigger failed during delivery execution activation.")

    final_notes = notes
    if not notes:
        if args.activate and trigger_result == "triggered":
            final_notes = ["Delivery execution bridge activated and the internal sequential delivery cycle was triggered."]
        elif args.activate:
            final_notes = ["Delivery execution bridge activation completed."]
        else:
            final_notes = ["Delivery execution bridge is ready for future ownership transfer."]

    intent = {
        "requestId": request_id,
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "mode": "activate" if args.activate else "dry-run",
        "status": "blocked" if notes else ("activated" if args.activate else "ready"),
        "guards": {
            "internalDeliveryPrimary": internal_primary,
            "consumerReady": consumer_ready,
            "requestFresh": request_fresh,
            "duplicateExecutionPrevented": duplicate_prevented,
            "targetCronEnabled": target_enabled,
            "targetCronRunning": target_running,
        },
        "source": {
            "taskId": request["task"].get("taskId"),
            "issueId": request["task"].get("issueId"),
            "repo": request["task"].get("repo"),
            "branch": request["task"].get("branch"),
            "kind": request["task"].get("kind"),
        },
        "execution": {
            "triggerMethod": trigger_method,
            "sideEffect": side_effect,
            "jobId": target_job_id,
            "result": trigger_result,
            "output": trigger_output,
        },
        "notes": final_notes,
    }

    execution_state.update(
        {
            "updatedAt": now.isoformat().replace("+00:00", "Z"),
            "lastPreparedRequestId": request_id,
            "status": intent["status"],
            "notes": intent["notes"],
        }
    )
    if args.activate and not notes:
        execution_state["lastExecutedRequestId"] = request_id
        execution_state["lastTriggerCronJobId"] = target_job_id
        execution_state["lastTriggerResult"] = trigger_result

    save_json(intent_json_path, intent)
    intent_md_path.write_text(render_md(intent), encoding="utf-8")
    save_json(execution_state_path, execution_state)

    if notes:
        print(f"[DELIVERY_EXECUTION_BLOCKED] requestId={request_id}")
    elif args.activate:
        print(f"[DELIVERY_EXECUTION_ACTIVATED] requestId={request_id}")
    else:
        print(f"[DELIVERY_EXECUTION_READY] requestId={request_id}")
    print(f"intent_json={intent_json_path}")
    print(f"intent_md={intent_md_path}")


if __name__ == "__main__":
    main()
