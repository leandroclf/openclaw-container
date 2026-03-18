# Estrategia avancada de economia de tokens (OpenClaw)

## Objetivo
Reduzir consumo de tokens sem perder qualidade, combinando:
1. roteamento por objetivo,
2. controle de concorrencia/contexto,
3. recursos nativos de economia por provedor.

## O que os docs oficiais recomendam

### OpenAI (Codex/OpenAI API)
- **Prompt Caching**: permite reaproveitar prefixos repetidos e reduzir custo de entrada.
- **Batch API**: para tarefas assincronas, possui desconto de custo e melhor throughput.
- **Controle de saida**: limitar `max_output_tokens` e usar menor verbosidade reduz gasto direto.

### Anthropic (Claude API)
- **Prompt Caching**: leitura de cache mais barata que reprocessar contexto; ha cache de curta e longa duracao.
- **Extended Thinking**: melhora qualidade em problemas dificeis, mas aumenta tokens; usar somente quando necessario.
- **Tool use**: Claude 4+ ja possui melhorias de eficiencia para tool use (nao depende de flag legado).

### Google Gemini
- **Context Caching**: cache explicito para prompts grandes e reaproveitados.
- **Token counting**: contar tokens antes de enviar para controlar budget por fluxo.
- **Thinking budget (Gemini 2.5)**: limitar raciocinio quando a tarefa nao exige profundidade maxima.

### OpenClaw
- **Context pruning e compaction**: configuracoes nativas para reduzir contexto acumulado.
- **Subagents com modelo proprio**: usar modelo mais barato para subagentes reduz burn rate.
- **Callbacks por objetivo**: aplicar politicas dinamicas antes de cargas pesadas.

## Politica aplicada neste repositorio

### 1) Router mais defensivo
- `scripts/model_router.py` agora:
  - filtra modelos em estado invalido de autenticacao (`auth`) e provedores indisponiveis;
  - nao remove automaticamente modelos em `rate_limit` (aplica penalidade e mantem fallback);
  - filtra provedores `missing`/`expired`;
  - aplica tuning de runtime por objetivo (`maxConcurrent`, `subagents`, `contextPruning`).

### 2) Objetivos com guardrails de custo
Arquivo: `ops/model-routing/objectives.json`
- `balanced_default`: usa `gemini-2.5-flash-lite` para subagentes quando disponivel, com concorrencia moderada.
- `coding_quality`: usa `gpt-5-mini` como subagente barato para tarefas de codigo.
- `cost_optimized`: concorrencia minima e contexto mais curto para rotinas/cron, priorizando `gpt-4.1-nano`.

### 3) Cron com prioridade em estabilidade/custo
Arquivo: `cron/cron.example`
- horario comercial volta para `balanced_default`.
- `coding_quality` deve ser acionado manualmente para tarefas criticas.

## Comandos operacionais recomendados

### Modo diario (equilibrado)
```bash
/home/leandro/openclaw-container/scripts/model_router.py --objective balanced_default --probe --apply
```

### Sprint de codificacao critica
```bash
/home/leandro/openclaw-container/scripts/model_router.py --objective coding_quality --probe --apply
```

### Voltar para economia agressiva
```bash
/home/leandro/openclaw-container/scripts/model_router.py --objective cost_optimized --probe --apply
```

### Verificar estado atual
```bash
docker exec openclaw openclaw --profile prod models status --probe
```

## Estrategia de uso para nao estourar cota
1. **Default fixo em balanced_default** com subagentes em `gemini-2.5-flash-lite` quando disponivel.
2. **Ativar coding_quality apenas por janela curta** e manter `gpt-5-mini` como subagente barato.
3. **Retornar para cost_optimized fora do horario de pico** com `gpt-4.1-nano` como cadeia minima.
4. **Manter subagentes em modelo economico** para tarefas paralelas.
5. **Revisar `last-recommendation.json` semanalmente** e reajustar pesos.

## Fontes oficiais
- OpenAI Prompt Caching: https://platform.openai.com/docs/guides/prompt-caching
- OpenAI Batch API: https://platform.openai.com/docs/guides/batch
- OpenAI Pricing: https://platform.openai.com/pricing
- Anthropic Prompt Caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Anthropic Extended Thinking: https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
- Anthropic Tool Use Overview: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- Gemini Context Caching: https://ai.google.dev/gemini-api/docs/caching
- Gemini Token Counting: https://ai.google.dev/gemini-api/docs/tokens
- Gemini Thinking (2.5): https://ai.google.dev/gemini-api/docs/thinking
- OpenClaw Config Reference: https://docs.openclaw.ai/configuration/reference
