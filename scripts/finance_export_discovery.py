#!/usr/bin/env python3
"""Discover likely finance export locations for OpenClaw."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CANONICAL_LEDGER = Path.home() / "openclaw" / "data" / "finance" / "ledger.csv"
DEFAULT_SEARCH_ROOTS = (
    Path.home() / "openclaw" / "data" / "finance",
    Path.home() / "openclaw" / "data",
    Path.home() / "openclaw",
    Path.home() / "OneDrive",
    Path.home() / "OneDrive" / "Documents",
    Path.home() / "OneDrive" / "Downloads",
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "finance",
    Path.home() / "Finance",
    Path.home() / "clawd",
    Path.home() / "openclaw-workspace",
    Path("/mnt/c/Users") / Path.home().name / "Downloads",
    Path("/mnt/c/Users") / Path.home().name / "Documents",
    Path("/mnt/c/Users") / Path.home().name / "Desktop",
    Path("/mnt/c/Users") / Path.home().name / "OneDrive",
    Path("/mnt/c/Users") / Path.home().name / "OneDrive" / "Documents",
    Path("/mnt/c/Users") / Path.home().name / "OneDrive" / "Downloads",
    Path("/mnt/c/Users") / "Public" / "Downloads",
)
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".json", ".ndjson", ".csv.gz", ".tsv.gz"}
NAME_KEYWORDS = ("ledger", "finance", "revenue", "billing", "stripe", "bookkeeping", "cashflow", "transactions")
PATH_KEYWORDS = ("finance", "billing", "accounting", "ledger", "revenue", "bookkeeping", "cashflow")
SKIP_DIRS = {
    ".git",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "tmp",
    "runtime",
    "venv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_search_roots(extra_roots: Iterable[str | Path] | None = None) -> list[Path]:
    roots: list[Path] = []
    raw_env = os.getenv("OPENCLAW_LEDGER_EXPORT_SEARCH_PATHS", "").strip()
    raw_roots: list[str | Path]
    if extra_roots is not None:
        raw_roots = list(extra_roots)
    elif raw_env:
        raw_roots = [item for item in raw_env.split(os.pathsep) if item.strip()]
    else:
        raw_roots = list(DEFAULT_SEARCH_ROOTS)

    seen: set[str] = set()
    for item in raw_roots:
        path = Path(item).expanduser()
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        roots.append(path)
    return roots


def normalize_suffix(path: Path) -> str:
    suffix = "".join(path.suffixes).lower()
    if suffix:
        return suffix
    return path.suffix.lower()


def has_keyword(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def is_candidate_file(path: Path) -> bool:
    suffix = normalize_suffix(path)
    if suffix not in SUPPORTED_SUFFIXES:
        return False
    name_hits = has_keyword(path.name, NAME_KEYWORDS)
    path_hits = has_keyword(str(path.parent), PATH_KEYWORDS)
    return bool(name_hits or path_hits)


def score_candidate(path: Path, *, stat_result: os.stat_result, now: datetime) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    suffix = normalize_suffix(path)
    name = path.name.lower()
    parent_text = str(path.parent).lower()

    if path.resolve(strict=False) == DEFAULT_CANONICAL_LEDGER.resolve(strict=False):
        score += 100
        reasons.append("canonical finance export path")

    if suffix in SUPPORTED_SUFFIXES:
        score += 35
        reasons.append(f"supported format {suffix}")

    name_hits = has_keyword(name, NAME_KEYWORDS)
    if name_hits:
        score += 20 + (5 * min(len(name_hits), 3))
        reasons.append("name matches " + ", ".join(name_hits[:3]))

    path_hits = has_keyword(parent_text, PATH_KEYWORDS)
    if path_hits:
        score += 10 + (3 * min(len(path_hits), 3))
        reasons.append("path matches " + ", ".join(path_hits[:3]))

    if stat_result.st_size == 0:
        score -= 15
        reasons.append("empty file")

    age_hours = max(0.0, (now.timestamp() - stat_result.st_mtime) / 3600.0)
    if age_hours <= 24:
        score += 20
        reasons.append("updated in the last 24h")
    elif age_hours <= 72:
        score += 15
        reasons.append("updated in the last 3 days")
    elif age_hours <= 24 * 14:
        score += 10
        reasons.append("updated in the last 2 weeks")
    elif age_hours <= 24 * 60:
        score += 4
        reasons.append("updated in the last 2 months")
    else:
        score += 1
        reasons.append("older snapshot")

    if path.is_symlink():
        score += 3
        reasons.append("symlink drop-in")

    return score, reasons


def discover_finance_exports(
    search_roots: Iterable[str | Path] | None = None,
    *,
    max_depth: int = 2,
    limit: int = 8,
) -> dict[str, Any]:
    roots = parse_search_roots(search_roots)
    now = datetime.now(timezone.utc)
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists() or not root.is_dir():
            continue

        root = root.resolve(strict=False)
        for current_dir, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current_dir)
            try:
                relative_parts = current_path.relative_to(root).parts if current_path != root else ()
            except ValueError:
                relative_parts = ()
            if len(relative_parts) >= max_depth:
                dirnames[:] = []
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in SKIP_DIRS and not dirname.startswith(".")
            ]

            for filename in filenames:
                path = current_path / filename
                resolved = str(path.resolve(strict=False))
                if resolved in seen:
                    continue
                if not is_candidate_file(path):
                    continue
                try:
                    stat_result = path.stat()
                except OSError:
                    continue
                score, reasons = score_candidate(path, stat_result=stat_result, now=now)
                seen.add(resolved)
                candidates.append(
                    {
                        "path": str(path),
                        "score": score,
                        "reasons": reasons,
                        "size": stat_result.st_size,
                        "mtime": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat(),
                        "mtimeEpoch": stat_result.st_mtime,
                        "suffix": normalize_suffix(path),
                    }
                )

    candidates.sort(
        key=lambda item: (
            -int(item.get("score", 0)),
            -float(item.get("mtimeEpoch", 0.0) or 0.0),
            item.get("path", ""),
        )
    )
    limited = candidates[:limit]
    recommended = dict(limited[0]) if limited else None
    return {
        "observedAt": now.isoformat(),
        "searchRoots": [str(root) for root in roots],
        "maxDepth": max_depth,
        "limit": limit,
        "candidateCount": len(candidates),
        "candidates": limited,
        "recommendedSource": recommended,
    }


def render_human_report(report: dict[str, Any]) -> str:
    recommended = report.get("recommendedSource") or {}
    lines = []
    if recommended.get("path"):
        lines.append(f"Suggested finance export source: {recommended.get('path')}")
        lines.append(
            f"Score: {recommended.get('score', 0)} | reasons: {', '.join(recommended.get('reasons', [])[:4]) or 'n/a'}"
        )
    else:
        lines.append("No likely finance export discovered.")

    lines.append(f"Search roots: {', '.join(report.get('searchRoots', [])) or 'n/a'}")
    lines.append(f"Candidates: {report.get('candidateCount', 0)}")

    for item in report.get("candidates", [])[:5]:
        lines.append(
            f"- {item.get('path', 'n/a')} | score={item.get('score', 0)} | {', '.join(item.get('reasons', [])[:3]) or 'n/a'}"
        )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", dest="roots", help="Extra search root (repeatable).")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--human", action="store_true", help="Render a human-readable summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = discover_finance_exports(args.roots, max_depth=args.max_depth, limit=args.limit)
    if args.human:
        print(render_human_report(report))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
