# Next Step - Idle Watchdog Execution Bridge - 2026-03-06

## Goal

Define the next implementation target after the current watchdog observe/policy/bridge/consumer scaffolds.

## Target

Build the **execution bridge** for idle watchdog handoff, but keep it disabled at first.

## What the execution bridge must do

1. read `watchdog-handoff-request.json`
2. validate consumer state
3. refuse execution if:
   - request is stale
   - request already activated
   - internal watchdog is still marked as primary executor
4. if explicitly enabled in a future phase:
   - mark the request as activated
   - record execution ownership transfer
   - trigger the chosen executor path exactly once

## What it must not do in the first cut

- no cron installation
- no automatic activation
- no disabling of the internal watchdog
- no Telegram side effects

## Recommended implementation order

1. create execution bridge script with `--dry-run` default
2. persist executor state transition only
3. add unit-level checks for:
   - stale request
   - duplicate activation
   - internal-primary guard
4. document activation gate

## Why this is the correct next step

At this point, the missing piece is no longer observation or policy. It is execution ownership transfer. That is the only missing contract before reducing the internal watchdog.
