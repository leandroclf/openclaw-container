#!/usr/bin/env python3
"""Assess whether the idle watchdog cutover preconditions are satisfied."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

FRESHNESS_LIMIT = timedelta(minutes=30)
TARGET_JOB = "Autopilot idle watchdog"


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_json(cmd: list[str]) -> object:
    return json.loads(subprocess.check_output(cmd, text=True))


def run_text(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def render_markdown(report: dict) -> str:
    lines = [
        "# Idle Watchdog Cutover Readiness",
        "",
        f"generatedAt: `{report['generatedAt']}`",
        f"status: `{report['status']}`",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        lines.append(f"- {check['name']}: `{check['status']}` - {check['detail']}")
    lines.extend(
        [
            "",
            "## Summary",
            f"- internalWatchdogActive: `{report['internalWatchdogActive']}`",
            f"- requestId: `{report['requestId']}`",
            f"- requestFresh: `{report['requestFresh']}`",
            f"- consumerReady: `{report['consumerReady']}`",
            f"- executionBridgeStatus: `{report['executionBridgeStatus']}`",
            "",
            "## Decision",
            f"- {report['decision']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else bridge_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    request_path = bridge_dir / "watchdog-handoff-request.json"
    consumer_state_path = bridge_dir / "watchdog-handoff-state.json"
    execution_state_path = bridge_dir / "watchdog-execution-state.json"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    checks: list[dict[str, str]] = []

    if not request_path.exists():
        raise SystemExit("[NO_GO] handoff request missing")
    if not consumer_state_path.exists():
        raise SystemExit("[NO_GO] consumer state missing")
    if not execution_state_path.exists():
        raise SystemExit("[NO_GO] execution state missing")

    request = load_json(request_path)
    consumer_state = load_json(consumer_state_path)
    execution_state = load_json(execution_state_path)

    request_id = request.get("requestId")
    created_at = parse_timestamp(request.get("createdAt"))
    request_fresh = created_at is not None and (now - created_at) <= FRESHNESS_LIMIT
    checks.append(
        {
            "name": "request_fresh",
            "status": "PASS" if request_fresh else "FAIL",
            "detail": "request age within 30 minutes" if request_fresh else "request stale",
        }
    )

    consumer_ready = consumer_state.get("status") == "ready"
    checks.append(
        {
            "name": "consumer_ready",
            "status": "PASS" if consumer_ready else "FAIL",
            "detail": f"consumer status={consumer_state.get('status')}",
        }
    )

    execution_status = execution_state.get("status", "unknown")
    execution_prepared = execution_state.get("lastPreparedRequestId") == request_id
    checks.append(
        {
            "name": "execution_bridge_prepared",
            "status": "PASS" if execution_prepared else "FAIL",
            "detail": f"execution status={execution_status}",
        }
    )

    cron_response = run_json(
        ["docker", "exec", "openclaw", "openclaw", "--profile", "prod", "cron", "list", "--json"]
    )
    cron_jobs = cron_response["jobs"] if isinstance(cron_response, dict) else cron_response
    internal_watchdog_active = any(job.get("name") == TARGET_JOB for job in cron_jobs)
    checks.append(
        {
            "name": "internal_watchdog_primary",
            "status": "FAIL" if internal_watchdog_active else "PASS",
            "detail": "internal watchdog still enabled" if internal_watchdog_active else "internal watchdog disabled",
        }
    )

    health = run_text(["docker", "exec", "openclaw", "openclaw", "--profile", "prod", "gateway", "health"])
    health_ok = "Gateway Health\nOK" in health or "Gateway Health\r\nOK" in health
    checks.append(
        {
            "name": "gateway_health",
            "status": "PASS" if health_ok else "FAIL",
            "detail": "gateway healthy" if health_ok else "gateway health failed",
        }
    )

    decision = "GO" if all(check["status"] == "PASS" for check in checks) else "NO_GO"
    report = {
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "status": decision,
        "requestId": request_id,
        "requestFresh": request_fresh,
        "consumerReady": consumer_ready,
        "executionBridgeStatus": execution_status,
        "internalWatchdogActive": internal_watchdog_active,
        "checks": checks,
        "decision": "Cutover may proceed." if decision == "GO" else "Do not cut over. Resolve failed checks first.",
    }

    json_path = output_dir / "watchdog-cutover-readiness.json"
    md_path = output_dir / "watchdog-cutover-readiness.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"[{decision}] requestId={request_id}")
    print(f"readiness_json={json_path}")
    print(f"readiness_md={md_path}")


if __name__ == "__main__":
    main()
