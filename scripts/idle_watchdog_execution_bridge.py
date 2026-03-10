#!/usr/bin/env python3
"""Build a dry-run execution intent from a ready idle-watchdog handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

FRESHNESS_LIMIT = timedelta(minutes=30)


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


def resolve_cron_job_id(profile: str, cron_name: str) -> str | None:
    payload = run_json(["docker", "exec", "openclaw", "openclaw", "--profile", profile, "cron", "list", "--json"])
    jobs = payload["jobs"] if isinstance(payload, dict) else payload
    for job in jobs:
        if job.get("name") == cron_name and job.get("enabled", True):
            return job.get("id")
    return None


def render_md(intent: dict) -> str:
    lines = [
        "# Idle Watchdog Execution Intent",
        "",
        f"requestId: `{intent['requestId']}`",
        f"generatedAt: `{intent['generatedAt']}`",
        f"mode: `{intent['mode']}`",
        f"status: `{intent['status']}`",
        "",
        "## Guards",
        f"- internalWatchdogPrimary: `{intent['guards']['internalWatchdogPrimary']}`",
        f"- consumerReady: `{intent['guards']['consumerReady']}`",
        f"- requestFresh: `{intent['guards']['requestFresh']}`",
        f"- duplicateExecutionPrevented: `{intent['guards']['duplicateExecutionPrevented']}`",
        "",
        "## Source Summary",
        f"- suggestedAction: `{intent['source']['suggestedAction']}`",
        f"- eligibleAutoTasks: `{intent['source']['eligibleAutoTasks']}`",
        f"- reason: {intent['source']['reason']}",
        "",
        "## Planned Executor Contract",
        "- executorOwner: internal OpenClaw watchdog until ownership transfer is approved",
        f"- triggerMethod: {intent['execution'].get('triggerMethod', 'not configured')}",
        f"- sideEffect: {intent['execution'].get('sideEffect', 'none in dry-run mode')}",
    ]
    if intent["execution"].get("jobId"):
        lines.append(f"- cronJobId: `{intent['execution']['jobId']}`")
    if intent["execution"].get("result"):
        lines.append(f"- triggerResult: `{intent['execution']['result']}`")
    if intent.get("notes"):
        lines.extend(["", "## Notes"])
        lines.extend([f"- {note}" for note in intent["notes"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--profile", default="prod")
    parser.add_argument("--trigger-cron-name")
    parser.add_argument("--trigger-timeout-ms", default="600000")
    parser.add_argument(
        "--internal-watchdog-primary",
        choices=["true", "false"],
        default="true",
        help="Keep true while the internal OpenClaw watchdog is still the sole executor.",
    )
    args = parser.parse_args()

    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    request_path = bridge_dir / "watchdog-handoff-request.json"
    consumer_state_path = bridge_dir / "watchdog-handoff-state.json"
    execution_state_path = bridge_dir / "watchdog-execution-state.json"
    intent_json_path = bridge_dir / "watchdog-execution-intent.json"
    intent_md_path = bridge_dir / "watchdog-execution-intent.md"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    internal_primary = args.internal_watchdog_primary == "true"

    if not request_path.exists():
        print("[EXECUTION_NO_REQUEST]")
        return
    if not consumer_state_path.exists():
        print("[EXECUTION_BLOCKED] consumer state missing")
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

    notes: list[str] = []
    if internal_primary:
        notes.append("Internal watchdog is still the primary executor.")
    if not consumer_ready:
        notes.append("Consumer state is not ready.")
    if not request_fresh:
        notes.append("Request is stale.")
    if not duplicate_prevented:
        notes.append("Request was already executed previously.")

    trigger_method = "none"
    side_effect = "none in dry-run mode"
    trigger_job_id = None
    trigger_result = None
    trigger_output = None

    if args.activate and not notes:
        if not args.trigger_cron_name:
            notes.append("Execution bridge activation requires --trigger-cron-name.")
        else:
            trigger_job_id = resolve_cron_job_id(args.profile, args.trigger_cron_name)
            if not trigger_job_id:
                notes.append(f"Cron job not found or disabled: {args.trigger_cron_name}")
            else:
                trigger_method = f"openclaw cron run {args.trigger_cron_name}"
                side_effect = "trigger host-approved internal delivery cycle"
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
                            trigger_job_id,
                            "--timeout",
                            args.trigger_timeout_ms,
                        ]
                    )
                    trigger_result = "triggered"
                except subprocess.CalledProcessError as exc:
                    trigger_result = "failed"
                    trigger_output = (exc.output or "").strip()
                    notes.append("Cron trigger failed during execution bridge activation.")

    final_notes = notes
    if not notes:
        if args.activate and trigger_result == "triggered":
            final_notes = ["Execution bridge activated and the internal delivery cycle was triggered."]
        elif args.activate:
            final_notes = ["Execution bridge activation completed."]
        else:
            final_notes = ["Execution bridge is ready for a future ownership transfer."]

    intent = {
        "requestId": request_id,
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "mode": "activate" if args.activate else "dry-run",
        "status": "blocked" if notes else ("activated" if args.activate else "ready"),
        "guards": {
            "internalWatchdogPrimary": internal_primary,
            "consumerReady": consumer_ready,
            "requestFresh": request_fresh,
            "duplicateExecutionPrevented": duplicate_prevented,
        },
        "source": {
            "artifact": request["source"].get("artifact"),
            "suggestedAction": request["source"].get("suggestedAction"),
            "eligibleAutoTasks": request["source"].get("eligibleAutoTasks"),
            "reason": request["source"].get("reason"),
        },
        "execution": {
            "triggerMethod": trigger_method,
            "sideEffect": side_effect,
            "jobId": trigger_job_id,
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
        execution_state["lastTriggerCronJobId"] = trigger_job_id
        execution_state["lastTriggerResult"] = trigger_result

    save_json(intent_json_path, intent)
    intent_md_path.write_text(render_md(intent), encoding="utf-8")
    save_json(execution_state_path, execution_state)

    if notes:
        print(f"[EXECUTION_BLOCKED] requestId={request_id}")
    elif args.activate:
        print(f"[EXECUTION_ACTIVATED] requestId={request_id}")
    else:
        print(f"[EXECUTION_READY] requestId={request_id}")
    print(f"intent_json={intent_json_path}")
    print(f"intent_md={intent_md_path}")


if __name__ == "__main__":
    main()
