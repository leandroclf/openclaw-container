# Test Strategy for Safe Evolution (Production Online)

This strategy exists to guarantee no regression while OpenClaw production stays
online.

## Test layers

1. Unit tests (`tests/unit`)
- Validate deterministic logic in scripts.
- Current focus: `scripts/model_router.py` scoring and fallback policies.

2. Regression contract tests (`tests/regression`)
- Validate mandatory docs and operational guardrails are present.
- Prevent accidental removal of critical no-downtime controls.
- Validate compose blue/green templates and promotion checklist contracts.

3. Integration tests (`tests/integration`)
- Validate runtime guardrails directly from Docker inspect.
- Optional Blue/Green isolation checks if `openclaw-next` is running.

## Execution commands

Quick gate (safe, no runtime dependency except python):

```bash
./scripts/test_gate.sh
```

Full gate with Docker runtime checks:

```bash
./scripts/test_gate.sh --with-integration
```

## Promotion policy

Before promoting any candidate:
1. Run `./scripts/test_gate.sh --with-integration`.
2. Run functional smoke on `openclaw-next`.
3. Keep soak window results in change notes.
4. Promote only if all critical gates pass.

## Future extensions (recommended)

- Add policy tests for OPA bundles when policy layer is introduced.
- Add Promptfoo evaluation gates for model quality regression.
- Add automated baseline vs candidate diff report (health/latency/error rates).
