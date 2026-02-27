# Production Change Policy (Zero-Downtime First)

This policy is mandatory for any OpenClaw evolution in this repository.

Goal:
- Keep the current production agent (`openclaw`) online.
- Validate all functional tests in parallel before promotion.
- Guarantee fast rollback with no data loss.

## 1) Hard rules (do not break)

1. Never stop/remove `openclaw` during parallel validation.
2. Never reuse production volumes for candidate environment.
   This includes workspace mount (`~/clawd`).
3. Never run candidate with production Telegram bot token.
4. Never expose candidate gateway on non-loopback interface.
5. Never run commands without explicit Docker context check.
6. Never rotate all provider credentials in the same change wave.
7. Never apply infra + policy + routing + auth changes in one step.

## 2) Environment model

- `Blue` = current production
  - container: `openclaw`
  - port: `18789`
  - data root: `~/openclaw/`
  - workspace: `~/clawd`
- `Green` = candidate
  - container: `openclaw-next`
  - port: `28789`
  - data root: `~/openclaw-next/`
  - workspace: `~/clawd-next`

Keep Blue and Green fully isolated (volumes, env file, logs, runtime state).

## 3) Docker context safety

Before any command:

```bash
docker context ls
docker context show
```

If using Docker Desktop in WSL, explicitly choose context in commands:

```bash
docker --context desktop-linux ps
docker --context default ps
```

Policy:
- Use one context per session.
- Record selected context in change notes.

## 4) Pre-change gate (mandatory)

Run and store outputs:

```bash
docker ps --filter name=openclaw
docker exec openclaw openclaw --profile prod gateway health
docker exec openclaw openclaw --profile prod status
tail -n 120 ~/openclaw/logs/openclaw-$(date +%F).log
```

Proceed only if Blue is healthy.

## 5) Candidate deployment gate (Green)

- Build candidate image tag (do not overwrite production tag in risky changes).
- Start `openclaw-next` with:
  - separate env file (`~/openclaw-next/.env`)
  - separate volumes (`~/openclaw-next/{data,runtime,logs}`)
  - loopback bind and alternate port `28789`

Validate:
- gateway health
- status
- model auth availability
- functional smoke flow
- job/cron behavior (if enabled for candidate)

## 6) Promotion gate

Promote only when all conditions are true:
- Green passed functional test suite.
- No critical errors in Green logs during soak window.
- Rollback command set is prepared and tested.

## 7) Rollback rule

If regression appears after promotion:
1. Stop candidate path.
2. Restore Blue runtime path immediately.
3. Re-check health and Telegram channel response.
4. Log incident and block new rollout until root cause is written.

## 8) Change note template (required)

```text
Date/Time:
Operator:
Docker context:
Change scope:
Blue baseline status:
Green validation status:
Promotion decision:
Rollback required? (Y/N)
Next action:
```

## 9) Forbidden shortcuts

- Direct in-place reconfiguration in production without parallel validation.
- Running destructive cleanup on production volumes.
- Pushing untested policy/routing changes directly to active runtime.
