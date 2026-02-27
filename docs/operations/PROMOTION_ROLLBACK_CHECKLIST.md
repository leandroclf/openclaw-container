# Promotion and Rollback Checklist (Blue/Green)

Use this checklist for every candidate promotion.

## 1) Pre-promotion baseline (Blue)

- [ ] Confirm Docker context:
  - `docker context ls`
  - `docker context show`
- [ ] Confirm Blue container is running:
  - `docker ps --filter name=openclaw`
- [ ] Confirm Blue gateway health:
  - `docker exec openclaw openclaw --profile prod gateway health`
- [ ] Confirm Blue status:
  - `docker exec openclaw openclaw --profile prod status`
- [ ] Save latest Blue logs:
  - `tail -n 200 ~/openclaw/logs/openclaw-$(date +%F).log`

## 2) Candidate validation (Green)

- [ ] Green uses isolated dirs (`~/openclaw-next`, `~/clawd-next`).
- [ ] Green does not reuse production Telegram token.
- [ ] Green health is OK:
  - `docker exec openclaw-next openclaw --profile prod gateway health`
- [ ] Green status is OK:
  - `docker exec openclaw-next openclaw --profile prod status`
- [ ] Test gates passed:
  - `./scripts/test_gate.sh --with-integration`
- [ ] Soak window completed with no critical errors.

## 3) Promotion decision gate

Promote only if all are true:
- [ ] No critical regression in Green logs.
- [ ] Functional test checklist completed.
- [ ] Rollback commands prepared and reviewed.

## 4) Promotion execution (manual cutover)

Record timestamp and operator before actions.

1. Stop Blue:
   - `docker stop openclaw`
2. Promote Green image/runtime to production command path
   (either rename strategy or restart production with approved artifact).
3. Validate production checks immediately:
   - `docker ps --filter name=openclaw`
   - `docker exec openclaw openclaw --profile prod gateway health`
   - `docker exec openclaw openclaw --profile prod status`

## 5) Rollback execution (if regression detected)

1. Stop promoted runtime.
2. Start previous known-good Blue runtime.
3. Re-run health/status checks.
4. Confirm Telegram channel response.
5. Log incident details in change notes.

## 6) Post-change record

Store this block in your change journal:

```text
Date/Time:
Operator:
Docker context:
Blue baseline: PASS/FAIL
Green validation: PASS/FAIL
Promoted artifact:
Rollback executed: YES/NO
Final status:
```
