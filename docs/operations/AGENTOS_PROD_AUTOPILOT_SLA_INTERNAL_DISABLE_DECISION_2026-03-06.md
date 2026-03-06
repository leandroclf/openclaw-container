# Agent OS Prod Autopilot SLA - Internal Disable Decision - 2026-03-06

## Context

The planned safe rollout for the `Daily autopilot SLA tracker` originally kept the internal OpenClaw cron enabled until the first scheduled host-side run could be compared.

During validation, an additional manual run of the internal job was executed to assess whether the internal path was still operational enough to justify waiting for the nightly schedule.

## Internal job evidence

Job:

- `Daily autopilot SLA tracker`
- job id: `f6db438a-7aaa-4f5d-86bf-e1c7c8cc1a19`

Manual run result:

- status: functionally degraded for the intended task
- summary: the agent stated it could not read or write the required files

Observed via:

- `docker exec openclaw openclaw --profile prod cron runs --id f6db438a-7aaa-4f5d-86bf-e1c7c8cc1a19 --limit 2`

Relevant evidence:

```text
Lamento, mas não consigo executar esta tarefa. O pedido exige a leitura e atualização de arquivos no sistema de arquivos (`autopilot-sla.json`, `autopilot-sla.md`, `autopilot-cycle-history.json`), e eu não tenho acesso a ferramentas que me permitam interagir diretamente com o sistema de arquivos...
```

## Host-side replacement evidence

Manual deterministic runner:

- `/home/leandro/openclaw-container/control-plane/scripts/prod_autopilot_sla_cycle.sh`

Validated successfully with:

- pre/post `Gateway Health OK`
- `autopilot-sla.json` updated
- `autopilot-sla.md` updated
- dashboard sync completed

## Decision

The internal OpenClaw cron was disabled immediately instead of waiting for the next nightly cycle.

Reason:

- the internal path was already proven unreliable for the required file operations
- the host-side deterministic replacement already produced the expected artifacts successfully
- keeping both paths active would preserve a broken runtime lane without adding confidence

## Operational action applied

Disabled:

- `docker exec openclaw openclaw --profile prod cron disable f6db438a-7aaa-4f5d-86bf-e1c7c8cc1a19`

Current ownership:

- host-side `prod-autopilot-sla` cron block owns SLA generation
- internal OpenClaw cron no longer owns this workflow

## Production safety

Post-change validation:

- `docker exec openclaw openclaw --profile prod gateway health`
- Result: `Gateway Health OK`, `Telegram ok`

## Conclusion

Disabling the internal `Daily autopilot SLA tracker` before the first scheduled host-side run was the lower-risk option because the internal implementation was already functionally degraded while the host-side deterministic runner was working.
