# Target Architecture by Functional Layer

This proposal selects exactly one primary technology per required layer to avoid
responsibility overlap and reduce operational load on a single host.

## Selection table

| Layer | Recommended technology | Why selected for this host | Strengths | Limitations | Alternatives reviewed (not selected) |
|---|---|---|---|---|---|
| Orchestration and task planning | Prefect (self-hosted) | Docker-native orchestration with schedules, retries, and event automations | Simple deployments, strong flow model, good observability hooks | Extra service + metadata DB | Airflow (heavier), Temporal (higher ops complexity) |
| Async messaging and processing | NATS JetStream | High throughput and lightweight persistent messaging on one host | Fast, durable streams, replay, simple clustering path | Requires subject discipline and retention tuning | RabbitMQ (higher footprint), Kafka/Redpanda (overkill here) |
| Semantic memory and retrieval | OpenClaw memory-lancedb plugin | Native OpenClaw integration with minimum glue code | Low friction, keeps cognitive context close to agent runtime | Less ecosystem than standalone vectordb stacks | Qdrant (needs extra integration layer), pgvector (mixed concerns) |
| Auth and secrets management | HashiCorp Vault OSS (Raft) | Mature secrets engine with policy control and audit options | AppRole, rotation support, explicit access boundaries | Operational overhead vs plain env files | Infisical (simpler but less proven in strict enterprise ops), Keycloak (not a secret vault) |
| Sandbox and execution isolation | gVisor (`runsc`) + OpenClaw sandbox | Better syscall isolation while keeping Docker workflow | Better containment for untrusted task execution | Potential compatibility/perf overhead per workload | Docker default runtime only (weaker isolation), Kata (more setup) |
| Technical and cognitive observability | OpenTelemetry Collector + Prometheus + Loki + Grafana | Best open stack for traces/metrics/logs with local hosting | Standardized telemetry, broad ecosystem, dashboard flexibility | Needs initial tuning (retention/cardinality) | ELK stack (higher memory/IO), ad-hoc logs only (low visibility) |
| Validation and policy decisions | OPA (Rego) | Policy-as-code engine decoupled from app logic | Clear governance boundary, testable policies | Rego learning curve | Inline app rules (less auditable), Cedar-based stacks (less adoption in this footprint) |
| Semantic cache and cost optimization | Redis Stack | Fast cache for prompt/result/context deduplication with TTL | Low latency, easy Docker use, mature client support | Requires memory policy tuning (maxmemory/eviction) | In-process cache only (no shared state), Memcached (fewer structures) |
| Critical evaluation (LLM-as-judge) | Promptfoo (CLI jobs) | Pragmatic eval suite for regression and quality gates | Provider-agnostic, CI friendly, red-team support | Needs disciplined test suite maintenance | DeepEval (python-heavy stack), custom scripts only (low repeatability) |
| Human-in-the-loop and governance | OpenClaw pairing + approvals + allowlist | Already in production channel flow with minimal change | Native UX, low extra ops burden, secure gating | Not a full ticketing platform | External ITSM workflows (too heavy for current phase) |

## Cross-layer coherence rules

- NATS is the single async backbone. Do not add another queue/broker.
- Redis is cache only. Do not use Redis as the event bus.
- Lancedb plugin is semantic memory only. Do not mix with policy or cache logic.
- OPA is the policy decision point. Keep authorization rules out of task code when possible.
- Prefect orchestrates; it does not replace OpenClaw cognitive execution.

## Host sizing guidance (single host)

Recommended baseline for all layers active:
- vCPU: 8+
- RAM: 16 GB+
- Storage: SSD with dedicated space for logs, telemetry, and volumes

If memory pressure appears first, reduce retention in Loki/Prometheus before
changing OpenClaw runtime limits.
