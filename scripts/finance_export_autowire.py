#!/usr/bin/env python3
"""Autowire a discovered finance export into the canonical OpenClaw path.

The workflow is intentionally idempotent:
- discover a likely finance export source
- wire it into the canonical drop-in path when a candidate exists
- publish the weekly finance/legal capture against the canonical export
- refresh the ledger watchdog state so the autonomy snapshot stays current
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
WORKSPACE_ROOT = Path(os.getenv("OPENCLAW_WORKSPACE_ROOT", str(Path.home() / "openclaw-workspace"))).expanduser()
CANONICAL_LEDGER = Path.home() / "openclaw" / "data" / "finance" / "ledger.csv"
STATE_FILE = Path.home() / "openclaw" / "runtime" / "agentos" / "finance-export-autowire.json"
INSTALL_DROPIN_SCRIPT = ROOT_DIR / "scripts" / "install_finance_export_dropin.sh"
LEDGER_WATCHDOG_SCRIPT = ROOT_DIR / "scripts" / "ledger_export_watchdog.py"
WEEKLY_CAPTURE_WORKFLOW = WORKSPACE_ROOT / "tools" / "weekly_blocker_capture_workflow.py"

from scripts import finance_export_discovery


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def persist_state(state_file: Path, payload: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve(strict=False) == right.expanduser().resolve(strict=False)


def discover_finance_export(max_depth: int, limit: int) -> dict[str, Any]:
    return finance_export_discovery.discover_finance_exports(max_depth=max_depth, limit=limit)


def resolve_candidate(report: dict[str, Any]) -> Path | None:
    candidate = report.get("recommendedSource")
    if not isinstance(candidate, dict):
        return None
    raw_path = str(candidate.get("path") or "").strip()
    if not raw_path:
        return None
    return Path(raw_path).expanduser()


def install_dropin(source: Path) -> dict[str, Any]:
    rc = run([str(INSTALL_DROPIN_SCRIPT), str(source)], cwd=ROOT_DIR)
    return {
        "returncode": rc.returncode,
        "stdout": rc.stdout.strip(),
        "stderr": rc.stderr.strip(),
    }


def run_weekly_capture(ledger_export: Path) -> dict[str, Any]:
    rc = run(
        [sys.executable, str(WEEKLY_CAPTURE_WORKFLOW), "--ledger-export", str(ledger_export)],
        cwd=WORKSPACE_ROOT,
    )
    commit_match = re.search(r"^commit:\s+(\S+)$", rc.stdout, flags=re.MULTILINE)
    return {
        "returncode": rc.returncode,
        "stdout": rc.stdout.strip(),
        "stderr": rc.stderr.strip(),
        "commit": commit_match.group(1) if commit_match else None,
    }


def run_watchdog(ledger_export: Path) -> dict[str, Any]:
    rc = run([sys.executable, str(LEDGER_WATCHDOG_SCRIPT), "--ledger-export", str(ledger_export)], cwd=ROOT_DIR)
    payload: dict[str, Any] = {}
    if rc.stdout.strip():
        try:
            parsed = json.loads(rc.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = {"rawOutput": rc.stdout.strip()}
    payload.setdefault("returncode", rc.returncode)
    if rc.stderr.strip():
        payload.setdefault("stderr", rc.stderr.strip())
    return payload


def ensure_publish_state(state_file: Path, payload: dict[str, Any]) -> None:
    persist_state(state_file, payload)


def build_report(
    *,
    discovery: dict[str, Any],
    candidate: Path | None,
    install_result: dict[str, Any] | None,
    capture_result: dict[str, Any] | None,
    watchdog_result: dict[str, Any],
    dry_run: bool,
    action: str,
) -> dict[str, Any]:
    candidate_record = discovery.get("recommendedSource") if isinstance(discovery.get("recommendedSource"), dict) else None
    report: dict[str, Any] = {
        "observedAt": utc_now(),
        "status": action,
        "dryRun": dry_run,
        "canonicalLedger": str(CANONICAL_LEDGER),
        "candidateCount": discovery.get("candidateCount", 0),
        "recommendedSource": candidate_record,
        "searchRoots": discovery.get("searchRoots", []),
        "actions": [],
        "install": install_result,
        "capture": capture_result,
        "watchdog": watchdog_result,
    }
    if candidate is not None:
        report["candidatePath"] = str(candidate)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=3, help="Discovery depth for local finance export search.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum number of discovered candidates to retain.")
    parser.add_argument("--dry-run", action="store_true", help="Only discover and report; do not wire or publish.")
    parser.add_argument("--state-file", default=str(STATE_FILE), help="Runtime state file for the autowire snapshot.")
    args = parser.parse_args(argv)

    state_file = Path(args.state_file).expanduser()
    discovery = discover_finance_export(max_depth=args.max_depth, limit=args.limit)
    candidate = resolve_candidate(discovery)

    install_result: dict[str, Any] | None = None
    capture_result: dict[str, Any] | None = None
    action = "waiting_for_source"

    if candidate is not None:
        action = "candidate_discovered"
        if not args.dry_run:
            if not same_path(candidate, CANONICAL_LEDGER):
                install_result = install_dropin(candidate)
                if install_result.get("returncode", 1) != 0:
                    report = build_report(
                        discovery=discovery,
                        candidate=candidate,
                        install_result=install_result,
                        capture_result=None,
                        watchdog_result={"status": "install_failed"},
                        dry_run=args.dry_run,
                        action="install_failed",
                    )
                    ensure_publish_state(state_file, report)
                    print(json.dumps(report, indent=2, ensure_ascii=True))
                    return int(install_result.get("returncode", 1) or 1)
                action = "dropin_wired"
            else:
                action = "already_canonical"

            capture_result = run_weekly_capture(CANONICAL_LEDGER)
            if capture_result.get("returncode", 1) != 0:
                report = build_report(
                    discovery=discovery,
                    candidate=candidate,
                    install_result=install_result,
                    capture_result=capture_result,
                    watchdog_result={"status": "capture_failed"},
                    dry_run=args.dry_run,
                    action="capture_failed",
                )
                ensure_publish_state(state_file, report)
                print(json.dumps(report, indent=2, ensure_ascii=True))
                return int(capture_result.get("returncode", 1) or 1)

            watchdog_result = run_watchdog(CANONICAL_LEDGER)
            action = "wired_and_published"
        else:
            watchdog_result = {"status": "dry_run"}
            action = "dry_run_candidate"
    else:
        watchdog_result = run_watchdog(CANONICAL_LEDGER)
        if args.dry_run:
            action = "dry_run"

    report = build_report(
        discovery=discovery,
        candidate=candidate,
        install_result=install_result,
        capture_result=capture_result,
        watchdog_result=watchdog_result,
        dry_run=args.dry_run,
        action=action,
    )
    report["stateFile"] = str(state_file)
    report["actions"] = [action]
    ensure_publish_state(state_file, report)

    print(f"Agente: workflow-runner")
    print(f"Skill: n/a (execução direta)")
    print(f"Workflow: finance export autowire")
    print(f"status: {action}")
    print(f"candidateCount: {report.get('candidateCount', 0)}")
    if candidate is not None:
        print(f"candidate: {candidate}")
    print(f"canonicalLedger: {CANONICAL_LEDGER}")
    print(f"stateFile: {state_file}")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
