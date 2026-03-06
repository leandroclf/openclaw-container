# Daily Summary Rotation Ownership Decision - 2026-03-06

Decision: keep `daily_summary_rotation` owned by the internal once-daily OpenClaw cron and remove it from the Agent OS `prod-observe` lane.

## Evidence

- Source script:
  - `~/clawd/ops/multiagent/delivery/scripts/daily_summary_rotate.py`
- Rotation only happens when:
  - `daily-summary.md` has at least `180` lines
- Current production file state at analysis time:
  - `lines = 22`
  - `size_bytes = 1009`

## Reasoning

- The script is semanticaily a daily compaction/archival routine.
- Running it every 30 minutes from `prod-observe` does not improve reliability.
- In the current state it only returns `no-rotation-needed`, adding duplicated execution and noise to the production Agent OS lane.
- The internal cron already runs this workflow at a more coherent cadence (`23:10`).

## Operational decision

- Keep internal cron job:
  - `Daily summary rotation`
- Remove `daily_summary_rotation` from:
  - `control-plane/scripts/prod_observe_cycle.sh`

## Expected effect

- `prod-observe` becomes a cleaner observation lane focused on:
  - `daily_ops_state_lint`
  - `product_progress_snapshot`
- duplication is reduced without losing the actual daily rotation behavior
