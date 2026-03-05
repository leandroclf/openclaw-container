#!/usr/bin/env python3
"""Validate sensitive runtime config paths use env placeholders."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable

PLACEHOLDER_RE = re.compile(r"^\$\{[A-Z0-9_]+\}$")


@dataclass(frozen=True)
class Rule:
    path: str
    expected: str
    required: bool


RULES: list[Rule] = [
    Rule("gateway.auth.token", "${OPENCLAW_GATEWAY_TOKEN}", True),
    Rule("skills.entries.notion.apiKey", "${NOTION_API_KEY}", True),
    Rule("skills.entries.openai-image-gen.apiKey", "${OPENAI_IMAGE_GEN_API_KEY}", True),
    Rule("skills.entries.openai-whisper-api.apiKey", "${OPENAI_WHISPER_API_KEY}", True),
    Rule("agents.defaults.memorySearch.remote.apiKey", "${OPENAI_API_KEY}", False),
    Rule("env.vars.GH_TOKEN", "${GH_TOKEN}", False),
    Rule("env.vars.GITHUB_TOKEN", "${GITHUB_TOKEN}", False),
]


def get_path(data: Any, path: str) -> tuple[bool, Any]:
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def classify(value: Any) -> str:
    if isinstance(value, str):
        if PLACEHOLDER_RE.match(value):
            return "placeholder"
        if value == "":
            return "empty"
        return "literal"
    if isinstance(value, dict) and {"source", "provider", "id"} <= set(value):
        return "secretref-object"
    return type(value).__name__


def iter_checks(data: dict[str, Any], rules: Iterable[Rule]) -> tuple[list[str], list[str]]:
    ok: list[str] = []
    errors: list[str] = []
    for rule in rules:
        exists, value = get_path(data, rule.path)
        if not exists:
            if rule.required:
                errors.append(f"ERROR  {rule.path}: missing (expected {rule.expected})")
            else:
                ok.append(f"OK     {rule.path}: missing (optional)")
            continue

        kind = classify(value)
        if isinstance(value, str) and value == rule.expected:
            ok.append(f"OK     {rule.path}: placeholder {rule.expected}")
            continue

        if kind == "placeholder":
            errors.append(
                f"ERROR  {rule.path}: unexpected placeholder format (expected {rule.expected})"
            )
        elif kind == "secretref-object":
            errors.append(
                f"ERROR  {rule.path}: SecretRef object detected (expected {rule.expected})"
            )
        elif kind == "literal":
            errors.append(
                f"ERROR  {rule.path}: literal value detected (expected {rule.expected})"
            )
        else:
            errors.append(
                f"ERROR  {rule.path}: unsupported type {kind} (expected {rule.expected})"
            )

    return ok, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/openclaw/data/openclaw.json"),
        help="Path to runtime config json (default: ~/openclaw/data/openclaw.json)",
    )
    args = parser.parse_args()

    try:
        with open(args.config, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print(f"ERROR  config file not found: {args.config}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR  invalid json in {args.config}: {exc}")
        return 2

    if not isinstance(data, dict):
        print(f"ERROR  config root must be an object: {args.config}")
        return 2

    ok, errors = iter_checks(data, RULES)
    for line in ok:
        print(line)
    for line in errors:
        print(line)

    if errors:
        print(f"SUMMARY  failed={len(errors)} ok={len(ok)}")
        return 1
    print(f"SUMMARY  failed=0 ok={len(ok)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
