#!/usr/bin/env python3
"""Policy-based model routing for OpenClaw."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT_DIR / "ops" / "model-routing" / "model_catalog.json"
DEFAULT_OBJECTIVES = ROOT_DIR / "ops" / "model-routing" / "objectives.json"
DEFAULT_REPORT = ROOT_DIR / "ops" / "model-routing" / "last-recommendation.json"

PROVIDER_SCORE_ADJUST = {
    "ok": 0.0,
    "expiring": -6.0,
    "expired": -20.0,
    "missing": -35.0,
}

PROBE_SCORE_ADJUST = {
    "ok": 4.0,
    "unknown": -8.0,
    "rate_limit": -15.0,
    "auth": -35.0,
}

SCORING_FIELDS = {
    "coding",
    "reasoning",
    "research",
    "image",
    "video",
    "latency",
    "cost_efficiency",
}


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_command(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "(no stderr)"
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{stderr}")
    return result.stdout


def parse_json_payload(raw_output: str) -> dict[str, Any]:
    payload = raw_output.strip()
    start = payload.find("{")
    if start == -1:
        raise RuntimeError("No JSON object found in command output.")
    payload = payload[start:]
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON payload: {exc}") from exc


def get_models_status(
    container: str,
    profile: str,
    probe: bool,
    probe_timeout_ms: int,
    probe_max_tokens: int,
) -> dict[str, Any]:
    cmd = [
        "docker",
        "exec",
        container,
        "openclaw",
        "--profile",
        profile,
        "models",
        "status",
        "--json",
    ]
    if probe:
        cmd.extend(
            [
                "--probe",
                "--probe-timeout",
                str(probe_timeout_ms),
                "--probe-max-tokens",
                str(probe_max_tokens),
            ]
        )
    return parse_json_payload(run_command(cmd))


def build_provider_status_map(status: dict[str, Any]) -> dict[str, str]:
    provider_status: dict[str, str] = {}
    providers = status.get("auth", {}).get("oauth", {}).get("providers", [])
    for item in providers:
        provider = item.get("provider")
        if not provider:
            continue
        provider_status[provider] = item.get("status", "unknown")
    return provider_status


def build_probe_status_map(status: dict[str, Any]) -> dict[str, str]:
    probe_status: dict[str, str] = {}
    results = status.get("auth", {}).get("probes", {}).get("results", [])
    for item in results:
        model = item.get("model")
        if not model:
            continue
        probe_status[model] = item.get("status", "unknown")
    return probe_status


def score_model(
    model_key: str,
    model_cfg: dict[str, Any],
    objective_cfg: dict[str, Any],
    provider_state: str,
    probe_state: str | None,
) -> tuple[float, dict[str, Any]]:
    weights = objective_cfg.get("weights", {})
    raw_scores = model_cfg.get("scores", {})
    base_score = 0.0
    for field, weight in weights.items():
        if field not in SCORING_FIELDS:
            continue
        base_score += float(weight) * float(raw_scores.get(field, 0.0))

    provider_penalty = PROVIDER_SCORE_ADJUST.get(provider_state, -10.0)
    probe_penalty = 0.0
    if probe_state is not None:
        probe_penalty = PROBE_SCORE_ADJUST.get(probe_state, -12.0)

    final_score = base_score + provider_penalty + probe_penalty
    return final_score, {
        "model": model_key,
        "provider": model_cfg.get("provider"),
        "baseScore": round(base_score, 3),
        "providerState": provider_state,
        "probeState": probe_state,
        "finalScore": round(final_score, 3),
    }


def filter_by_modalities(
    candidates: list[tuple[str, dict[str, Any]]], required_modalities: list[str]
) -> list[tuple[str, dict[str, Any]]]:
    filtered: list[tuple[str, dict[str, Any]]] = []
    for model_key, model_cfg in candidates:
        modalities = model_cfg.get("modalities", {})
        if all(bool(modalities.get(modality)) for modality in required_modalities):
            filtered.append((model_key, model_cfg))
    return filtered


def apply_openclaw_routing(
    container: str,
    profile: str,
    primary: str,
    fallbacks: list[str],
) -> None:
    run_command(
        [
            "docker",
            "exec",
            container,
            "openclaw",
            "--profile",
            profile,
            "config",
            "set",
            "agents.defaults.model.primary",
            primary,
        ]
    )
    run_command(
        [
            "docker",
            "exec",
            container,
            "openclaw",
            "--profile",
            profile,
            "config",
            "set",
            "agents.defaults.model.fallbacks",
            json.dumps(fallbacks),
        ]
    )


def render_callbacks(callbacks: list[str], container: str, profile: str) -> list[str]:
    rendered = []
    for command in callbacks:
        rendered.append(command.format(container=container, profile=profile))
    return rendered


def enforce_required_fallbacks(
    *,
    scored_models: list[str],
    primary: str,
    fallbacks: list[str],
    required_models: list[str],
    position: str,
) -> tuple[list[str], list[str], list[str]]:
    updated = list(fallbacks)
    enforced: list[str] = []
    notes: list[str] = []

    for model in unique_preserve_order(required_models):
        if model == primary:
            notes.append(f"required fallback model '{model}' is already primary.")
            continue
        if model not in scored_models:
            notes.append(f"required fallback model '{model}' is not available in current candidates.")
            continue
        if model in updated:
            continue

        if position == "front":
            updated.insert(0, model)
        else:
            updated.append(model)
        enforced.append(model)

    return unique_preserve_order(updated), enforced, notes


def run_callbacks(callbacks: list[str]) -> None:
    for command in callbacks:
        result = subprocess.run(command, shell=True, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Callback failed ({result.returncode}): {command}\n"
                f"{result.stderr.strip() or '(no stderr)'}"
            )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Policy-based model router for OpenClaw.")
    parser.add_argument("--objective", help="Objective name from ops/model-routing/objectives.json")
    parser.add_argument("--list-objectives", action="store_true", help="List available objectives and exit")
    parser.add_argument("--apply", action="store_true", help="Apply selected routing to OpenClaw config")
    parser.add_argument(
        "--run-callbacks",
        action="store_true",
        help="Run callback commands declared for objective after apply",
    )
    parser.add_argument("--probe", action="store_true", help="Run live auth/model probe before ranking")
    parser.add_argument("--probe-timeout-ms", type=int, default=12000, help="Probe timeout per model")
    parser.add_argument("--probe-max-tokens", type=int, default=64, help="Probe max tokens")
    parser.add_argument("--profile", default="prod", help="OpenClaw profile (default: prod)")
    parser.add_argument("--container", default="openclaw", help="Container name (default: openclaw)")
    parser.add_argument(
        "--fallback-count",
        type=int,
        default=None,
        help="Override fallback count for this run",
    )
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Catalog JSON path")
    parser.add_argument("--objectives", default=str(DEFAULT_OBJECTIVES), help="Objectives JSON path")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Output report JSON path")
    parser.add_argument("--json", action="store_true", help="Print result JSON to stdout")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    catalog = load_json(Path(args.catalog))
    objective_payload = load_json(Path(args.objectives))
    objectives = objective_payload.get("objectives", {})
    constraints = objective_payload.get("constraints", {})

    if args.list_objectives:
        for name, cfg in sorted(objectives.items()):
            print(f"{name}: {cfg.get('description', '')}")
        return 0

    if not args.objective:
        parser.error("--objective is required (or use --list-objectives)")

    if args.objective not in objectives:
        available = ", ".join(sorted(objectives.keys()))
        raise SystemExit(f"Unknown objective '{args.objective}'. Available: {available}")

    objective_cfg = objectives[args.objective]
    status = get_models_status(
        container=args.container,
        profile=args.profile,
        probe=args.probe,
        probe_timeout_ms=args.probe_timeout_ms,
        probe_max_tokens=args.probe_max_tokens,
    )

    available_models = set(status.get("allowed", []))
    model_catalog = catalog.get("models", {})
    provider_state_map = build_provider_status_map(status)
    probe_state_map = build_probe_status_map(status)

    candidates = [(m, cfg) for m, cfg in model_catalog.items() if m in available_models]
    required_modalities = objective_cfg.get("requiredModalities", ["text"])
    candidates = filter_by_modalities(candidates, required_modalities)

    if not candidates:
        raise SystemExit(
            f"No candidate models found for objective '{args.objective}' with required "
            f"modalities {required_modalities}."
        )

    scored: list[dict[str, Any]] = []
    for model_key, model_cfg in candidates:
        provider = str(model_cfg.get("provider", ""))
        provider_state = provider_state_map.get(provider, "unknown")
        probe_state = probe_state_map.get(model_key)
        final_score, item = score_model(
            model_key=model_key,
            model_cfg=model_cfg,
            objective_cfg=objective_cfg,
            provider_state=provider_state,
            probe_state=probe_state,
        )
        item["finalScore"] = round(final_score, 3)
        scored.append(item)

    scored.sort(key=lambda row: row["finalScore"], reverse=True)
    fallback_count = args.fallback_count or int(objective_cfg.get("fallbackCount", 3))
    primary = scored[0]["model"]
    fallbacks = [row["model"] for row in scored[1 : 1 + fallback_count]]
    required_models = []
    required_models.extend(constraints.get("ensureFallbackModels", []))
    required_models.extend(objective_cfg.get("ensureFallbackModels", []))
    ensure_position = str(
        objective_cfg.get("ensureFallbackPosition", constraints.get("ensureFallbackPosition", "append"))
    ).lower()
    if ensure_position not in {"append", "front"}:
        ensure_position = "append"
    scored_models = [row["model"] for row in scored]
    fallbacks, enforced_models, enforcement_notes = enforce_required_fallbacks(
        scored_models=scored_models,
        primary=primary,
        fallbacks=fallbacks,
        required_models=required_models,
        position=ensure_position,
    )
    callbacks = render_callbacks(objective_cfg.get("callbacks", []), args.container, args.profile)

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "objective": args.objective,
        "description": objective_cfg.get("description", ""),
        "requiredModalities": required_modalities,
        "primary": primary,
        "fallbacks": fallbacks,
        "enforcedFallbackModels": enforced_models,
        "enforcementNotes": enforcement_notes,
        "applied": bool(args.apply),
        "probeUsed": bool(args.probe),
        "scoredModels": scored,
        "callbacks": callbacks,
    }

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.apply:
        apply_openclaw_routing(args.container, args.profile, primary, fallbacks)
        if args.run_callbacks and callbacks:
            run_callbacks(callbacks)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Objective: {args.objective}")
    print(f"Primary : {primary}")
    print(f"Fallbacks ({len(fallbacks)}): {', '.join(fallbacks) if fallbacks else '-'}")
    if enforced_models:
        print(f"Enforced fallback models: {', '.join(enforced_models)}")
    if enforcement_notes:
        for note in enforcement_notes:
            print(f"Note: {note}")
    print("")
    print("Ranking:")
    for idx, item in enumerate(scored, start=1):
        probe_state = item.get("probeState") or "-"
        print(
            f"{idx:>2}. {item['model']:<40} score={item['finalScore']:<8} "
            f"provider={item['providerState']:<8} probe={probe_state}"
        )
    print("")
    print(f"Report: {args.report}")
    if callbacks:
        print("Callbacks:")
        for command in callbacks:
            print(f"  - {command}")
    if args.apply:
        print("Routing applied to OpenClaw config.")
    else:
        print("Dry run only. Use --apply to persist routing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
