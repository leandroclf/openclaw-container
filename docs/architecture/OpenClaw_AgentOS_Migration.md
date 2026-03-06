# OpenClaw Agent OS Migration (Scheduler Cognitivo + Fila + Supervisão)
**Versão:** 2026-03-05.1  
**Objetivo:** transformar a arquitetura atual do OpenClaw em um **“Sistema Operacional de Agentes (Agent OS)”** com **scheduler cognitivo**, **fila de trabalho**, **supervisão autônoma** e **governança por política**, mantendo **infra mínima** (host único, Docker/WSL2, sem novos serviços obrigatórios no início).

> Este documento é feito para ser **executável**: inclui inventário, desenho de contratos, plano incremental, testes, observabilidade, rollback e um **prompt pronto** para enviar ao Codex.

---

## 1) Escopo e definição de sucesso

### 1.1 Escopo
- Manter o runtime atual (WSL2 Ubuntu 24.04 + Docker) e o container OpenClaw endurecido.
- Evoluir coordenação e comunicação **dentro do stack atual**, adicionando:
  - **Task/Event Canonical Schema**
  - **Máquina de estados (state machine)**
  - **Fila local (SQLite) com leases/TTL**
  - **Supervisor→Planner→Executor** (papéis claros)
  - **Scheduler cognitivo** integrado ao `model_router.py`
  - **Policy gate executável** derivado de `PRODUCTION_CHANGE_POLICY.md`
  - **Envelopes Telegram** (controle) + **artefatos externos** (dados)
- Infra opcional (fases futuras): **OPA** (audit→enforce) e **NATS** (se/quando houver necessidade de async real).

### 1.2 Definição de sucesso (MVP do Agent OS)
O sistema passa a ter, no mínimo:
1) **Uma entidade “Task”** com ID, estado, prioridade, constraints, budgets e critérios de aceite.
2) **Eventos append-only** para cada transição importante (auditável).
3) **Fila local** com:
   - `claim/lease/heartbeat`
   - `retry/backoff`
   - transições de estado consistentes
4) **Supervisor** que coordena, aplica preflight/policy e impõe evidência.
5) **Telegram** apenas como “canal de controle” (sumários curtos), sem falhas por tamanho.
6) Rollout seguro via **Blue/Green**, com gates, e rollback definido.

---

## 2) Inventário do ambiente atual (AS-IS) — o que levantar antes de mexer

### 2.1 Runtime e hardening
- Host: **WSL2 Ubuntu 24.04 + Docker Engine**
- Container principal: `openclaw-secure:latest`, `--restart unless-stopped`
- Hardening: rootfs read-only, cap-drop ALL, no-new-privileges, pids-limit, tmpfs /tmp, etc.
- Gateway: ws://127.0.0.1:18789 (loopback), com auth token
- Canal: Telegram polling com pairing + allowlist

**Ação (inventário):**
- Capturar e versionar:
  - `openclaw --profile prod status`
  - `openclaw --profile prod gateway health`
  - `docker ps` / `docker inspect openclaw`
  - `openclaw.json` efetivo e `.env` placeholders (sem segredos em claro)

### 2.2 ACP / ACPX (estado efetivo informado)
**Base atual relevante:**
- ACP efetivo:
  - `dispatch.enabled=true`
  - `backend=acpx`
  - `defaultAgent=gemini`
  - `allowedAgents=["gemini"]`
  - `maxConcurrentSessions=2`
- ACPX plugin:
  - `permissionMode=approve-reads`
  - `nonInteractivePermissions=deny`
  - `queueOwnerTtlSeconds=15`
  - binário local em runtime

**Ação (inventário):**
- Confirmar e registrar:
  - trechos relevantes do `openclaw.json` (apenas config, sem segredos)
  - versões: `openclaw --version`, sha de imagem docker
  - configuração ACPX: path do binário, permissões, TTL

### 2.3 Cron/autopilot (estado efetivo informado)
- Autopilot sequential delivery cycle
- Autopilot idle watchdog
- Deploy log capture and ...
- Daily autopilot SLA tracker
- Daily summary rotation
- Daily ops state lint

**Ação (inventário):**
- Listar cron names + intervalos + outputs
- Identificar quais crons enviam payload no Telegram e onde geram logs/artefatos

### 2.4 Workspace artifacts (Control Plane atual)
Você já possui um “control plane” via artefatos (ex.: status, progress, snapshots).  
**Ação (inventário):**
- Enumerar artefatos existentes e seus locais:
  - `deploy-status.json`
  - `product-code-progress.json`
  - `handoff-master.json`
  - `workspace-state.json` (ou equivalente)
  - logs diários
- Definir quais artefatos são:
  - **estado canônico**
  - **cache**
  - **derivados** (gerados e descartáveis)

### 2.5 Gaps operacionais já conhecidos
- Telegram: erro de “message too long” já ocorreu em evidência.
- `openclaw doctor --fix` ainda acusa erro legado (mas operação estável).
- ACP `allowedAgents=["gemini"]` limita multi-agent real (por enquanto).

---

## 3) Desenho do Agent OS: entidades, contratos e máquina de estados

### 3.1 Conceito central: Task como entidade de sistema
Uma task é uma unidade de trabalho que pode ser:
- criada por usuário (Telegram), cron/autopilot, ou por outro agente (derivada).
- enfileirada, reivindicada (claim), executada, bloqueada, reexecutada, concluída.

**Requisitos de Task:**
- ID único e estável (`taskId`)
- correlação ponta-a-ponta (`correlationId`) para rastrear workflow
- estado atual + histórico via eventos
- prioridade e orçamento (custo/tempo/retries)
- constraints (writes/network/destructive/prodImpact)
- critérios de aceite e evidências necessárias

### 3.2 Papéis: Supervisor → Planner → Executor (separação de responsabilidades)
**Supervisor (kernel / coordenador):**
- Observa fila + eventos + saúde do sistema
- Aplica policy/preflight
- Decide roteamento (objective, modelo, requested/effective agent, estratégia)
- Abre tasks derivadas (ex.: “corrigir CI”, “rodar preflight”, “coletar evidência”)
- Impõe gates (test/health/evidência) antes de concluir

**Planner (decompositor):**
- Quebra uma Task grande em subtasks menores
- Define acceptance criteria e evidências por etapa
- Define prioridade de subtasks

**Executor (worker):**
- Executa ação concreta (codar, rodar testes, pesquisar, operar)
- Reporta progresso e produz evidências

> Nota: na fase inicial, Planner/Executor podem ser “roles” dentro do mesmo agente efetivo (Gemini), mas **o contrato já prepara** para multi-agent real quando `allowedAgents` expandir.

### 3.3 Scheduler cognitivo
Função: converter contexto + kind + constraints em:
- `objective` (já existe: coding_quality, reasoning_quality, research_depth, cost_optimized, etc.)
- `requestedAgent` (ex.: codex) e `effectiveAgent` (respeita allowedAgents atual)
- `executionStrategy` (single/speculative/consensus)
- budget (retries/custo/tempo)

#### 3.3.1 Mapping por tipo (kind → objective)
Tabela inicial:
- `code_impl`, `code_review`, `debug_ci` → `coding_quality`
- `architecture`, `planning` → `reasoning_quality`
- `research` → `research_depth`
- `ops_watchdog`, `daily_summary`, `heartbeat` → `cost_optimized`
- `default_chat` → `balanced_default`
- `image_request` → `image_creator`
- `video_request` → `video_creator`

#### 3.3.2 requestedAgent vs effectiveAgent
Como `allowedAgents=["gemini"]` hoje, separar:
- `routing.requestedAgent="codex"` (quando apropriado)
- `routing.effectiveAgent="gemini"` (até abrir allowedAgents)
- `routing.reason="allowedAgents restricts ACP to gemini"`

### 3.4 Máquina de estados (state machine)
Estados recomendados (mínimo):
- `queued`
- `claimed` (opcional explícito; pode ser “running” com lease)
- `running`
- `blocked`
- `needs_human`
- `failed`
- `succeeded`
- `canceled`

Transições principais:
- `queued → running` (claim + lease)
- `running → blocked` (hard/soft/human blockers)
- `running → failed` (erro fatal ou sem retries)
- `running → queued` (retry com backoff)
- `running → succeeded` (com evidência obrigatória)
- `blocked → running` (quando desbloqueado)
- `failed → queued` (retry manual ou automático)
- qualquer → `canceled` (cancelamento)

---

## 4) Canonical Task/Event Schema (v1) e exemplos

### 4.1 Task Schema (campos mínimos)
Campos (recomendado):
- `schemaVersion` (ex.: `2026-03-05.1`)
- `taskId`, `correlationId`, `issueId` (opcional)
- `kind`, `title`, `workflow`, `executionMode`, `priority`
- `source` (channel/session/message/user)
- `routing` (objective, requestedAgent, effectiveAgent, reason, executionStrategy)
- `repo`, `branch`
- `constraints` (allowWrites, allowNetwork, destructiveOps, productionImpact)
- `budget` (maxRetries, maxCost, maxDurationSeconds)
- `acceptance` (required[], ciMustPass)
- `state` (status, attempts, leaseOwner, leaseUntil)
- `timestamps` (createdAt, updatedAt)

### 4.2 Event Schema (append-only)
Campos (recomendado):
- `eventVersion`, `eventType`, `eventId`, `createdAt`
- `correlationId`, `taskId`
- `source` (channel/session/message/user)
- `routing` (objective, requestedAgent, effectiveAgent, reason)
- `payload` (pequeno)
- `evidenceRefs[]` (paths/urls curtas)

EventTypes:
- `task.created`
- `task.claimed`
- `task.progress`
- `task.blocked` (+ `blockerType`: HARD_BLOCKER|SOFT_BLOCKER|HUMAN_BLOCKER)
- `task.failed`
- `task.retry_scheduled`
- `task.needs_human`
- `task.completed`
- `task.handoff`

### 4.3 Exemplo de evento: task.dispatch.request (compatível com seu modelo)
```json
{
  "eventVersion": "2026-03-05.1",
  "eventType": "task.dispatch.request",
  "eventId": "uuid",
  "createdAt": "2026-03-05T22:10:00Z",
  "correlationId": "corr-uuid",
  "source": {
    "channel": "telegram",
    "sessionKey": "agent:main:main",
    "messageId": "tg:123456",
    "userId": "343551192"
  },
  "routing": {
    "objective": "coding_quality",
    "requestedAgent": "codex",
    "effectiveAgent": "gemini",
    "reason": "allowedAgents restricts ACP to gemini",
    "executionStrategy": "single"
  },
  "payload": {
    "taskId": "ISSUE-001-step-03",
    "title": "Implement value endpoint normalization",
    "kind": "code_impl",
    "repo": "projects/lf-openalex-enrichment-mvp",
    "branch": "feature/issue-001-value-endpoint"
  },
  "evidenceRefs": []
}
```

---

## 5) Fila de trabalho local (SQLite) — design e operações

### 5.1 Por que SQLite primeiro
- Zero novos serviços
- Sem alterar topologia docker
- Persistente em volume já montado (workspace/runtime)
- Permite leases, retries, auditoria e reconstrução

### 5.2 Tabelas mínimas (DDL conceitual)
**tasks**
- task_id (PK)
- status
- priority
- kind
- objective
- requested_agent
- effective_agent
- repo, branch
- attempts, max_retries
- lease_owner, lease_until
- created_at, updated_at
- task_json

**events**
- event_id (PK)
- task_id
- correlation_id
- event_type
- created_at
- event_json

**artifacts**
- artifact_id (PK)
- task_id
- kind (log|diff|report|summary|evidence)
- path
- created_at

### 5.3 Leases/TTL e compatibilidade com ACPX
- ACPX: `queueOwnerTtlSeconds=15` (curto)
- Fila local: lease padrão 30s; heartbeat a cada 10–15s
- Se lease expirar: task volta para `queued` (work stealing)

### 5.4 Retry/backoff e DLQ simples
- `attempts < max_retries`: requeue com backoff (ex.: 30s, 2min, 5min…)
- `attempts == max_retries`: `needs_human` + evento com reason + evidência

---

## 6) Política e preflight: tornar PRODUCTION_CHANGE_POLICY executável

### 6.1 O que deve ser “sensível”
Kinds que exigem preflight:
- `ops_deploy`
- `runtime_change`
- `policy_change`
- `routing_change`
- `auth_change`

### 6.2 Preflight steps (derivado literalmente da policy)
Checklist mínimo:
1) `docker context ls` + `docker context show`
2) Garantir “single context session”
3) Se toca produção (Blue):
   - `docker ps --filter name=openclaw`
   - `docker exec openclaw openclaw --profile prod gateway health`
   - `docker exec openclaw openclaw --profile prod status`
   - `tail -n 120 ~/openclaw/logs/openclaw-$(date +%F).log`
4) Se validação paralela (Green):
   - nunca parar/remover openclaw Blue
   - nunca reutilizar `~/openclaw/*` nem `~/clawd`
   - nunca usar token Telegram de produção no candidate
   - bind apenas loopback
5) Bloquear “waves” no mesmo ciclo:
   - infra + policy
   - infra + routing
   - infra + auth
   - auth de múltiplos providers ao mesmo tempo

### 6.3 Preflight output canônico (exemplo)
```json
{
  "preflight": {
    "dockerContextChecked": true,
    "singleContextSession": true,
    "blueHealthy": true,
    "isParallelCandidate": false,
    "reusedProdVolumes": false,
    "reusedProdWorkspace": false,
    "usedProdTelegramTokenOnCandidate": false,
    "changeWave": { "infra": false, "policy": true, "routing": true, "auth": false },
    "allowedToProceed": false,
    "denyReason": "policy+routing in same wave"
  }
}
```

---

## 7) Telegram envelope (controle) + evidências (dados)

### 7.1 Regras operacionais
- alvo ≤ 2800 chars; limite duro ≤ 3500
- JSON bruto grande: proibido
- logs/stacktrace: no máximo 3–5 linhas relevantes + caminho do artefato completo
- mensagens longas → chunking `part 1/2`

### 7.2 Template (normal)
```
[AgentOS][ISSUE-001][code_impl][part 1/1]

Status:
- repo: lf-openalex-enrichment-mvp
- branch: feature/issue-001-value-endpoint
- fase: testes locais
- objective: coding_quality

Resultado:
- code: ok
- tests: ok
- commit: 1234abc
- pr: <url>

Evidências:
- logs: artifacts/evidence/ISSUE-001-step-03/test_gate.log

Riscos:
- nenhum bloqueio crítico
```

### 7.3 Template (incidente)
```
[AgentOS][CI][lf-openalex-enrichment-mvp][part 1/1]

Resumo:
- 2 falhas consecutivas detectadas
- owner AUTO: devops-ci-cd-specialist
- run: <url>

Causa raiz (curta):
- setup-python cache mal configurado

Ação:
- correção aplicada
- aguardando CI verde

Evidências:
- artifacts/evidence/ci/2026-03-05/ci_failures.log
```

---

## 8) Plano incremental de implementação (SQLite + OPA + opcional NATS)

### Fase 0 — Inventário + contratos (sem mudar comportamento)
- Criar diretório `control-plane/`
- Adicionar schemas Task/Event/Preflight
- Criar `agentos.db` e scripts utilitários
- Instrumentar crons para emitirem eventos (sem alterar lógica)

**Saída:** auditoria/telemetria básica e base para fila.

### Fase 1 — Fila local (SQLite) + leases
- Implementar Queue API
- Migrar 1–2 fluxos de baixo risco para fila (ex.: `daily_ops_state_lint`, `daily_summary_rotation`)
- Garantir retries/backoff e `needs_human`

**Saída:** work queue funcional sem NATS.

### Fase 2 — Supervisor + Scheduler cognitivo
- Implementar Supervisor loop:
  - cria tasks derivadas
  - aplica preflight para tasks sensíveis
  - exige evidência para completion
- Integrar mapping `kind→objective` com `model_router.py`

**Saída:** autonomia orquestrada com governança.

### Fase 3 — OPA (opcional, recomendado) em audit mode
- Transformar preflight e gates em políticas avaliáveis por OPA
- Começar com **audit** (não bloqueia), depois **enforce** após estabilidade

**Saída:** governança computável.

### Fase 4 — NATS (opcional, somente se houver necessidade real)
Critérios para adotar NATS:
- múltiplos workers/containers
- necessidade de async desacoplado
- reprocessamento e backpressure mais sofisticados

Começar com:
- espelhamento de `events` para stream (JetStream)
- 1 worker externo não crítico consumindo tasks

---

## 9) Observabilidade mínima (sem stack grande)
Requisitos mínimos:
- `correlationId` e `taskId` em:
  - logs
  - eventos
  - envelopes Telegram
- Métricas (mesmo que via log parsing inicial):
  - throughput por kind
  - taxa de sucesso/falha
  - tempo médio por kind
  - top blockers/reasons
  - retries por kind

Artefatos sugeridos:
- `artifacts/reports/daily_agentos_report.md`
- `artifacts/reports/failure_clusters.json`

---

## 10) Plano de testes (unit + integração) e gates

### 10.1 Testes unitários
- Validação de schema Task/Event/Preflight
- Queue leasing:
  - claim → heartbeat → expire → reclaim
- Retry/backoff:
  - falha retryable requeue
  - max_retries → needs_human
- Telegram envelope:
  - chunking garantido
  - nunca envia JSON grande

### 10.2 Testes de integração (ambiente candidate Green)
- Supervisor loop não cria loops infinitos de tasks
- Preflight bloqueia waves proibidas
- Gate de evidência:
  - tasks sensíveis não finalizam sem artefato/test_gate/health
- Crons instrumentados:
  - emitem eventos e salvam artefatos

### 10.3 Gate de promoção
Antes de promover Green:
- `openclaw gateway health` e `openclaw status`
- `test_gate.sh --with-integration` quando aplicável
- soak window com monitoramento de fila e eventos
- zero regressões de Telegram delivery

---

## 11) Procedimentos de rollback (operacional e de código)

### 11.1 Rollback operacional (Blue/Green)
- Manter Blue intacto durante validação
- Se Green falhar:
  - desligar Green
  - preservar artifacts para pós-mortem
  - continuar com Blue

### 11.2 Safe mode (recomendado implementar)
Um toggle (config/env) para:
- desativar Supervisor
- manter emissão de eventos
- manter fila em modo “observe-only”

Isso permite reverter autonomia sem perder telemetria.

### 11.3 Rollback de migrations do SQLite
- Versionar schema
- Manter script `cp_migrate_db.py`
- Backups:
  - `agentos.db.bak` por dia

---

## 12) Mudanças de configuração do ACP (multi-agent real) — roteiro seguro

### Etapa A — sem mexer em allowedAgents
- Construir Agent OS (fila + supervisor + policy) com effectiveAgent fixo (gemini)
- Ganhos: coordenação, evidência, envelopes, gates e menos retrabalho

### Etapa B — abrir `allowedAgents=["gemini","codex"]`
- Adicionar policy de roteamento:
  - kinds que podem usar codex
  - budgets mais restritos
- Manter `executionStrategy="single"` inicialmente

### Etapa C — expandir providers (opcional)
- Apenas após estabilidade:
  - adicionar novos providers
  - evitar mudança “auth multi-provider” no mesmo wave

---

## 13) Prompt pronto para enviar ao Codex (copiar e colar)

```text
Você é o Codex implementer. Objetivo: evoluir a arquitetura OpenClaw atual para um “Agent Operating System” (Agent OS) com scheduler cognitivo, fila de trabalho e supervisão autônoma, mantendo infra mínima (sem novos serviços obrigatórios no início).

Contexto:
- ACP dispatch.enabled=true, backend=acpx, defaultAgent=gemini, allowedAgents=["gemini"], maxConcurrentSessions=2.
- ACPX: permissionMode=approve-reads, nonInteractivePermissions=deny, queueOwnerTtlSeconds=15.
- Há crons/autopilot ativos (delivery, watchdog, deploy log capture, SLA tracker, summary rotation, ops state lint).
- Há model_router.py + objectives.json + model_catalog.json.
- Há política de produção Blue/Green e preflight derivado de PRODUCTION_CHANGE_POLICY.

Tarefas para implementar (passo a passo, commits pequenos):
1) Criar diretório control-plane/ no workspace com:
   - schemas/task.schema.json, schemas/event.schema.json, schemas/preflight.schema.json.
   - state/agentos.db (SQLite) e scripts para init/migrate/validate.
   - artifacts/{events,tasks,evidence,reports}/ para outputs.
2) Implementar banco SQLite com tabelas: tasks, events, artifacts, incluindo lease/TTL e snapshots JSON.
3) Implementar EventEmitter:
   - valida schema
   - grava em SQLite + JSONL diário (append-only)
   - retorna eventId
4) Implementar Queue API:
   - enqueue_task
   - claim_next_task(worker_id, kinds_allowed, lease_seconds)
   - heartbeat (renova lease)
   - complete_task (com evidências)
   - fail_task (retry/backoff)
   - block_task (HARD/SOFT/HUMAN)
   - needs_human
5) Implementar máquina de estados conforme documento: queued/running/blocked/failed/succeeded/canceled/needs_human.
6) Implementar Scheduler Cognitivo:
   - mapping kind→objective em routing_rules.json
   - integrar com model_router.py para selecionar objective/model/fallback
   - sempre preencher requestedAgent e effectiveAgent (effective respeita acp.allowedAgents; hoje ficará gemini)
   - adicionar executionStrategy (single/speculative/consensus) default single
7) Implementar Telegram Envelope:
   - limite alvo 2800 / duro 3500
   - chunking com header part x/y
   - nunca enviar JSON grande
   - sempre enviar resumo + evidenceRefs (paths curtas)
8) Implementar Preflight executável baseado na política:
   - docker context check (single context)
   - se produção: baseline Blue (ps, health, status, tail log)
   - se paralelo: nunca parar Blue, nunca reutilizar volumes/workspace, nunca usar token Telegram prod, bind loopback
   - bloquear change waves proibidos: infra+policy, infra+routing, infra+auth, auth multi-provider no mesmo ciclo
   - output allow/deny + denyReason
9) Implementar Supervisor loop:
   - observa tasks/events
   - aplica preflight antes de tasks sensíveis (ops_deploy/runtime_change/policy_change/routing_change/auth_change)
   - cria tasks derivadas (ex: corrigir CI, coletar evidência)
   - aplica retry/backoff e escalonamento de objective
   - exige evidências para concluir (test_gate/health/logs/PR conforme acceptance)
10) Instrumentar crons existentes para emitirem eventos e (quando apropriado) enfileirar tasks, sem mudar o comportamento inicialmente.

Inclua:
- testes unit/integration (schema validation, queue lease, preflight deny, telegram chunking, supervisor loop guard contra loops)
- safe mode para desativar Supervisor mantendo eventos
- documentação curta de operação/rollback.

Respeite repo boundaries: não inserir código de produto no workspace. Mudanças pequenas e incrementais.
```

---

## 14) Checklist final de entrega (para validação)
- [ ] `control-plane/` criado com schemas e scripts
- [ ] `agentos.db` criado e versionado com migrations
- [ ] EventEmitter ativo e usado por crons
- [ ] Queue API com leases/retries/backoff
- [ ] Supervisor ativo (com safe mode)
- [ ] Preflight aplicado em tasks sensíveis
- [ ] Telegram envelope implementado e sem “message too long”
- [ ] Testes unit/integration passando
- [ ] Rollout Green validado e promoção segura

---
