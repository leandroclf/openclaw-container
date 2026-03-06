# Idle Watchdog Manual Activation Gate - 2026-03-06

## Purpose

Provide a single manual entrypoint for future executor cutover while keeping the
default state blocked.

## Script

```bash
/home/leandro/openclaw-container/control-plane/scripts/manual_idle_watchdog_cutover_activate.sh \
  --confirm-cutover
```

## Guardrails

The script always performs, in order:

1. Docker context verification
2. `gateway health` before activation
3. `idle_watchdog_cutover_readiness.py`
4. hard stop unless readiness returns `GO`
5. execution bridge activation with:
   - `--activate`
   - `--internal-watchdog-primary false`
6. `gateway health` after activation

## Current Expected Result

- exit non-zero
- message:
  - `Cutover activation blocked by readiness gate.`

This is correct until the internal `Autopilot idle watchdog` is no longer the
primary executor.
