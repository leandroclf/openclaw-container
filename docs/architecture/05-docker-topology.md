# Docker Topology (Single Host)

This topology keeps all services on one host with internal Docker networking
and minimal externally exposed surfaces.

## Logical communication diagram

```text
                           +----------------------+
                           |  Grafana             |
                           +----------+-----------+
                                      |
                           +----------v-----------+
                           | OTel Collector       |
                           +-----+-----------+----+
                                 |           |
                                 |           |
+----------------+        +------v---+   +---v----------------+
| Telegram User  +------->+ OpenClaw +--->+ NATS JetStream     |
+----------------+        | Gateway  |    +---+----------------+
                          +--+----+--+        |
                             |    |           |
                             |    |           v
                             |    |      +----+----------------+
                             |    +----->+ Prefect Worker/Jobs |
                             |           +---------------------+
                             |
                             +-----> Redis Stack (semantic cache)
                             +-----> OPA (policy decisions)
                             +-----> Vault (secrets)
                             +-----> memory-lancedb (semantic memory)

OpenClaw and all support services communicate on internal Docker networks.
```

## Network model

- `oc_core` (internal): OpenClaw, NATS, Redis, OPA, Vault, Prefect.
- `oc_obs` (internal): OTel, Loki, Prometheus, Grafana.
- No public bind by default for support services.
- Admin UIs should be loopback-only when enabled.

## Volume model

Current OpenClaw volumes (already in production):
- `~/openclaw/data` -> `/home/node/.openclaw-prod`
- `~/openclaw/runtime` -> `/home/node/.openclaw`
- `~/openclaw/logs` -> `/tmp/openclaw`
- `~/clawd` -> `/home/node/clawd`

Planned additional persistent volumes:
- NATS JetStream store
- Vault Raft data
- Redis data (AOF/RDB as configured)
- Prefect metadata DB
- Loki/Prometheus/Grafana state

## Secrets strategy

- Source of truth: Vault.
- Bootstrap only: minimal env file on host for startup and Vault auth bootstrap.
- Never commit raw secrets in repo.
- Mask token-like values in logs and reports.

## Performance guardrails

- Set per-service memory and CPU limits to protect OpenClaw.
- Apply log retention policies to avoid disk growth.
- Monitor:
  - gateway response time
  - provider error rates (`rate_limit`, timeout)
  - queue depth
  - memory pressure and swap usage

## Deployment profiles (recommended)

- `core`: OpenClaw + required runtime deps only
- `obs`: telemetry stack
- `security`: Vault + OPA + runtime isolation config
- `eval`: Promptfoo jobs and datasets

Deploy in sequence: `core` -> `obs` -> `security` -> `eval`.
