# Model Routing Strategy (v1)

This folder defines a policy-based model router for OpenClaw.

Goal: choose `primary + fallbacks` per objective with quality first and
cost-benefit as fallback.

## What this solves

- Consistent model selection by objective (`coding`, `reasoning`, `research`,
  `image`, `video`, `cost`).
- Live availability-aware routing using current auth/probe state from OpenClaw.
- Versioned policy in git (`catalog + objective weights`).

## Files

- `model_catalog.json`: model capability and scoring inputs.
- `objectives.json`: objective weights, required modalities, callbacks.
- `last-recommendation.json`: generated output (created by script).

## Script

Use `scripts/model_router.py`.

List objectives:

```bash
./scripts/model_router.py --list-objectives
```

Dry run (no config changes):

```bash
./scripts/model_router.py --objective balanced_default
```

Dry run with live probe:

```bash
./scripts/model_router.py --objective coding_quality --probe
```

Apply routing to OpenClaw config:

```bash
./scripts/model_router.py --objective coding_quality --apply
```

Apply and run objective callbacks:

```bash
./scripts/model_router.py --objective coding_quality --apply --run-callbacks
```

## Operational rule

1. Keep `balanced_default` for daily operations.
2. Switch objective before heavy workloads:
   - `coding_quality` for deep implementation/debug.
   - `reasoning_quality` for architecture/strategy decisions.
   - `research_depth` for web/data synthesis.
   - `cost_optimized` for background jobs and cron.
3. Re-run with `--probe` when provider instability/rate-limit appears.
4. Global constraint in `objectives.json` guarantees at least one OpenAI chain
   fallback (`openai-codex/gpt-5.3-codex`) in every routing decision when the
   model is available.

## Governance

- Refresh `model_catalog.json` monthly.
- Sources to refresh scores:
  - SWE-bench / LiveCodeBench / LiveBench
  - GenEval
  - VBench / VBench-2.0
  - Official provider pricing pages
- Keep score changes in commit history with a short rationale.
