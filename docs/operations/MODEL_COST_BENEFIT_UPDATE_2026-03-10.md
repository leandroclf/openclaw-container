# Model Cost-Benefit Update - 2026-03-10

## Goal

Refresh OpenClaw routing so low-cost tasks prefer the best current
price-performance options from Gemini and OpenAI without weakening coding
fallback quality.

## Official pricing inputs used

### OpenAI

- `GPT-5 mini`
  - input `$0.250 / 1M`
  - output `$2.000 / 1M`
- `GPT-4.1 mini`
  - input `$0.80 / 1M`
  - output `$3.20 / 1M`
- `GPT-4.1 nano`
  - input `$0.20 / 1M`
  - output `$0.80 / 1M`

### Gemini

- `Gemini 2.5 Pro`
  - input `$1.25 / 1M` up to 200k prompts
  - output `$10.00 / 1M` up to 200k prompts
- `Gemini 2.5 Flash`
  - input `$0.30 / 1M`
  - output `$2.50 / 1M`
- `Gemini 2.5 Flash-Lite`
  - input `$0.10 / 1M`
  - output `$0.40 / 1M`
- `Gemini 3.1 Flash-Lite Preview`
  - input `$0.25 / 1M`
  - output `$1.50 / 1M`

## Runtime constraint found locally

Current OpenClaw `models list` exposes these supported production choices now:

- `google-gemini-cli/gemini-2.5-flash`
- `google-gemini-cli/gemini-2.5-pro`
- `openai/gpt-4.1-mini`
- `openai/gpt-4.1-nano`
- `openai/gpt-4o-mini`
- `openai-codex/gpt-5.3-codex`

It does not currently expose:

- `google-gemini-cli/gemini-2.5-flash-lite`
- `google-gemini-cli/gemini-3.1-flash-lite-preview`
- `openai/gpt-5-mini`

Those models were added only to the router catalog so the policy is ready as
soon as the provider layer starts exposing them.

## Routing decisions applied

- Keep `gemini-2.5-flash` as the daily balanced primary.
- Prefer cheaper OpenAI API models in routing:
  - `gpt-4.1-nano` for `cost_optimized` subagents
  - `gpt-4.1-mini` as a stronger low-cost coding subagent
- Increase fallback depth from `2` to `3` for quality-sensitive objectives.
- Preserve `openai-codex/gpt-5.3-codex` as enforced rescue fallback.

## Practical result

- Routine cron/ops work shifts toward cheaper models.
- Balanced day mode keeps large-context Gemini Flash first.
- Coding still retains Codex fallback when quality is needed.
- The router is future-ready for `GPT-5 mini` and Gemini Flash-Lite once
  OpenClaw exposes them in `models list`.
