#!/usr/bin/env python3
"""Watch the canonical finance ledger export and alert on lifecycle changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import before_agent_reply
from scripts import finance_export_discovery


DEFAULT_CANONICAL_LEDGER = Path.home() / "openclaw" / "data" / "finance" / "ledger.csv"
DEFAULT_STATE_FILE = Path.home() / "openclaw" / "runtime" / "agentos" / "ledger-export-watchdog.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_ledger_export_path(raw_path: str | None) -> Path:
    candidate = (raw_path or "").strip()
    if candidate:
        return Path(candidate).expanduser()
    env_path = os.getenv("OPENCLAW_LEDGER_EXPORT_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_CANONICAL_LEDGER


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_ledger_export(path: Path) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "observedAt": utc_now(),
    }
    if not path.exists():
        return snapshot

    stat = path.stat()
    snapshot.update(
        {
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": sha256_file(path),
        }
    )
    return snapshot


def discover_ledger_export_candidates() -> dict[str, Any]:
    return finance_export_discovery.discover_finance_exports()


def classify_change(previous: dict[str, Any], current: dict[str, Any]) -> str:
    previous_exists = bool(previous.get("exists"))
    current_exists = bool(current.get("exists"))

    if not previous_exists and current_exists:
        return "appeared"
    if previous_exists and not current_exists:
        return "disappeared"
    if not previous_exists and not current_exists:
        return "initial_missing"

    if (
        previous.get("size") != current.get("size")
        or previous.get("mtime") != current.get("mtime")
        or previous.get("sha256") != current.get("sha256")
    ):
        return "updated"

    return "stable"


def build_alert_message(
    change_type: str,
    current: dict[str, Any],
    previous: dict[str, Any],
    *,
    hostname: str,
) -> str:
    path = current.get("path") or previous.get("path") or str(DEFAULT_CANONICAL_LEDGER)
    observed_at = current.get("observedAt") or utc_now()
    lines = [
        f"OpenClaw ledger export {change_type} on {hostname} at {observed_at}.",
        f"Canonical path: {path}",
    ]

    if change_type != "disappeared":
        if current.get("size") is not None:
            lines.append(f"Current size: {current['size']} bytes")
        if current.get("mtime"):
            lines.append(f"Current modified: {current['mtime']}")
        if current.get("sha256"):
            lines.append(f"Current sha256: {str(current['sha256'])[:16]}…")
    else:
        if previous.get("size") is not None:
            lines.append(f"Previous size: {previous['size']} bytes")
        if previous.get("mtime"):
            lines.append(f"Previous modified: {previous['mtime']}")

    if change_type == "appeared":
        lines.append("Trigger: canonical finance export is now present.")
    elif change_type == "updated":
        lines.append("Trigger: canonical finance export content changed.")
    elif change_type == "disappeared":
        lines.append("Trigger: canonical finance export vanished after previously being present.")

    return "\n".join(lines)


def format_telegram_alert(message: str, artifact_ref: str) -> str:
    return before_agent_reply.format_reply(
        message,
        channel="telegram",
        artifact_ref=artifact_ref,
        header="OpenClaw ledger export watchdog",
    )


def docker_available() -> bool:
    completed = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
    return completed.returncode == 0


def send_telegram_alert(
    *,
    alert_target: str,
    message: str,
    container: str,
    profile: str,
    artifact_ref: str,
) -> dict[str, Any]:
    if not alert_target:
        return {"sent": False, "reason": "no_target"}
    if not docker_available():
        return {"sent": False, "reason": "docker_unavailable"}

    formatted = format_telegram_alert(message, artifact_ref)
    completed = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "openclaw",
            "--profile",
            profile,
            "message",
            "send",
            "--channel",
            "telegram",
            "--target",
            alert_target,
            "--message",
            formatted,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "sent": False,
            "reason": "send_failed",
            "stderr": completed.stderr.strip(),
        }
    return {"sent": True, "reason": "ok"}


def persist_state(state_file: Path, payload: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_watchdog(
    *,
    ledger_export: Path,
    state_file: Path,
    alert_target: str,
    container: str,
    profile: str,
    dry_run: bool,
) -> dict[str, Any]:
    previous = load_state(state_file)
    current = snapshot_ledger_export(ledger_export)
    change_type = classify_change(previous, current)
    change_detected = change_type in {"appeared", "updated", "disappeared"}
    discovery = discover_ledger_export_candidates()

    alert_result: dict[str, Any] = {"sent": False, "reason": "stable"}
    if change_detected and not dry_run:
        alert_result = send_telegram_alert(
            alert_target=alert_target,
            message=build_alert_message(
                change_type,
                current,
                previous,
                hostname=socket_hostname(),
            ),
            container=container,
            profile=profile,
            artifact_ref="artifact://ledger-export-watchdog",
        )

    if not dry_run:
        persisted = {
            "observedAt": current["observedAt"],
            "path": current["path"],
            "exists": current["exists"],
            "size": current.get("size"),
            "mtime": current.get("mtime"),
            "sha256": current.get("sha256"),
            "lastChangeType": change_type,
            "lastChangeAt": current["observedAt"] if change_detected or not previous else previous.get("lastChangeAt"),
            "lastAlertAt": current["observedAt"] if alert_result.get("sent") else previous.get("lastAlertAt"),
            "discovery": discovery,
        }
        persist_state(state_file, persisted)

    return {
        "status": "change_detected" if change_detected else "stable",
        "changeType": change_type,
        "ledgerExport": current,
        "discovery": discovery,
        "previousState": previous,
        "alert": alert_result,
        "stateFile": str(state_file),
        "observedAt": current["observedAt"],
        "dryRun": dry_run,
    }


def socket_hostname() -> str:
    try:
        return os.uname().nodename
    except AttributeError:  # pragma: no cover - fallback for non-POSIX platforms
        return os.getenv("HOSTNAME", "unknown-host")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger-export", default=None, help="Optional explicit ledger export path.")
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
        help="State file used to remember the last observed ledger fingerprint.",
    )
    parser.add_argument("--container", default="openclaw")
    parser.add_argument("--profile", default="prod")
    parser.add_argument("--alert-target", default=os.getenv("ALERT_TELEGRAM_TARGET", "").strip())
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ledger_export = resolve_ledger_export_path(args.ledger_export)
    report = run_watchdog(
        ledger_export=ledger_export,
        state_file=Path(args.state_file),
        alert_target=args.alert_target,
        container=args.container,
        profile=args.profile,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
