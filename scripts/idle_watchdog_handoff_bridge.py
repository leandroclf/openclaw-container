#!/usr/bin/env python3
"""Create an idempotent host-side handoff request from idle watchdog artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def compute_request_id(report: dict) -> str:
    tracked_ids = [item.get("id") or item.get("title") or "unknown" for item in report.get("monitored_tasks", [])]
    payload = {
        "observedAt": report.get("observedAt") or report.get("timestamp"),
        "suggestedAction": report.get("suggested_action"),
        "reason": report.get("reason"),
        "tracked": tracked_ids,
        "eligibleAutoTasks": report.get("eligible_auto_tasks"),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def render_md(request: dict) -> str:
    source = request.get("source", {})
    lines = [
        "# Idle Watchdog Handoff Request",
        "",
        f"requestId: `{request['requestId']}`",
        f"createdAt: `{request['createdAt']}`",
        f"status: `{request['status']}`",
        "",
        "## Source",
        f"- channel: `{source.get('channel', 'cron')}`",
        f"- sessionKey: `{source.get('sessionKey', 'n/a')}`",
        f"- messageRef: `{source.get('messageRef', 'n/a')}`",
        f"- dedupKey: `{source.get('dedupKey', 'n/a')}`",
        f"- observedAt: `{request['source']['observedAt']}`",
        f"- suggestedAction: `{request['source']['suggestedAction']}`",
        f"- reason: {request['source']['reason']}",
        f"- eligibleAutoTasks: `{request['source']['eligibleAutoTasks']}`",
        f"- productiveAdvancementDetected: `{request['source']['productiveAdvancementDetected']}`",
        f"- activeBlockersDetected: `{request['source']['activeBlockersDetected']}`",
        "",
        "## Candidate Tasks",
    ]
    tracked = request["source"].get("trackedTasks", [])
    if tracked:
        lines.append("| Task | Repo | Advancement |")
        lines.append("|---|---|---|")
        for item in tracked:
            lines.append(
                "| {task} | `{repo}` | `{adv}` |".format(
                    task=item.get("id", "n/a"),
                    repo=item.get("repoPath", "n/a"),
                    adv=item.get("advancementDetected", False),
                )
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Bridge Contract",
            "- This artifact requests internal consumption only.",
            "- Host-side must not trigger mini-cycle execution directly.",
            "- Internal executor may consume this request in a later phase.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--bridge-dir", required=True)
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).expanduser().resolve()
    bridge_dir = Path(args.bridge_dir).expanduser().resolve()
    bridge_dir.mkdir(parents=True, exist_ok=True)

    source_json = workspace_root / "ops" / "multiagent" / "delivery" / "watchdog-monitor.json"
    report = load_json(source_json)
    observed_at = parse_timestamp(report.get("observedAt") or report.get("timestamp"))
    now = datetime.now(timezone.utc).replace(microsecond=0)

    if observed_at is None or (now - observed_at) > FRESHNESS_LIMIT:
        print("[BRIDGE_BLOCKED] stale watchdog observation")
        return

    if report.get("active_blockers_detected"):
        print("[BRIDGE_SKIPPED] blockers present")
        return

    if report.get("suggested_action") != "TRIGGER_MINI_CYCLE":
        print("[BRIDGE_SKIPPED] no handoff requested")
        return

    request_id = compute_request_id(report)
    request = {
        "requestId": request_id,
        "createdAt": now.isoformat().replace("+00:00", "Z"),
        "status": "pending_internal_consumption",
        "source": {
            "channel": "cron",
            "sessionKey": "cron:idle-watchdog",
            "messageRef": observed_at.isoformat().replace("+00:00", "Z"),
            "dedupKey": request_id,
            "artifact": str(source_json),
            "observedAt": observed_at.isoformat().replace("+00:00", "Z"),
            "suggestedAction": report.get("suggested_action"),
            "reason": report.get("reason"),
            "eligibleAutoTasks": report.get("eligible_auto_tasks", 0),
            "productiveAdvancementDetected": report.get("productive_advancement_detected", False),
            "activeBlockersDetected": report.get("active_blockers_detected", False),
            "trackedTasks": [
                {
                    "id": item.get("id"),
                    "repoPath": item.get("repo_path"),
                    "advancementDetected": item.get("advancement_detected", False),
                }
                for item in report.get("monitored_tasks", [])
            ],
        },
    }

    json_path = bridge_dir / "watchdog-handoff-request.json"
    md_path = bridge_dir / "watchdog-handoff-request.md"
    current = load_json(json_path) if json_path.exists() else {}
    if current.get("requestId") == request_id and current.get("status") == request["status"]:
        print(f"[BRIDGE_NOOP] requestId={request_id}")
        return

    json_path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_md(request), encoding="utf-8")
    print(f"[BRIDGE_READY] requestId={request_id}")
    print(f"handoff_json={json_path}")
    print(f"handoff_md={md_path}")


if __name__ == "__main__":
    main()
