# OpenClaw Google Meet Integration - Complete Setup Guide

**Data**: 26 de Abril, 2026
**Status**: ✅ Tested and Validated
**Versão OpenClaw**: 2026.4.23+

---

## Visão Geral

Este guia configura o OpenClaw para participar automaticamente de reuniões no Google Meet usando:
- **Browser Automation**: Chromium headless com Chrome DevTools Protocol (CDP)
- **Voice I/O**: Deepgram (Speech-to-Text) + ElevenLabs (Text-to-Speech)
- **AI Processing**: Google Gemini ou Anthropic Claude

---

## Pré-requisitos

✅ Docker instalado e rodando
✅ OpenClaw container `openclaw-secure:latest`
✅ Conectividade à internet
✅ APIs: Deepgram + ElevenLabs (ambos com free tier)

---

## STEP 1: Verificar Setup Atual

```bash
# Verificar container rodando
docker ps | grep openclaw
# Esperado: openclaw-secure:latest rodando

# Verificar plugins carregados
docker exec openclaw openclaw --profile prod plugins list | grep -E "browser|deepgram|elevenlabs|google"
# Esperado:
# - browser ✅ loaded
# - deepgram ✅ loaded
# - elevenlabs ✅ loaded
# - google ✅ loaded
```

---

## STEP 2: Obter API Keys (Free Tier)

### 2.1 Deepgram (Speech-to-Text)

```bash
# Acesse: https://deepgram.com/
# 1. Sign Up (Google/GitHub)
# 2. Console → API Keys
# 3. Crie nova key
# 4. Salve: DEEPGRAM_API_KEY=8cfd9559f0330df0b4039c50e3a6cc54590932d4
```

### 2.2 ElevenLabs (Text-to-Speech)

```bash
# Acesse: https://elevenlabs.io/
# 1. Sign Up (free trial)
# 2. Profile → API Key
# 3. Copie a chave
# 4. Salve: ELEVENLABS_API_KEY=sk_72749...
```

---

## STEP 3: Configurar Chaves no Container

```bash
# Adicionar as chaves ao arquivo de configuração do OpenClaw
docker exec openclaw python3 << 'EOF'
import json

config_path = "/home/node/.openclaw-prod/openclaw.json"

with open(config_path, 'r') as f:
    config = json.load(f)

# Adicionar as chaves
config['env']['vars']['DEEPGRAM_API_KEY'] = "SEU_DEEPGRAM_KEY"
config['env']['vars']['ELEVENLABS_API_KEY'] = "SEU_ELEVENLABS_KEY"

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Chaves configuradas")
EOF
```

**Importante**: Substitua `SEU_DEEPGRAM_KEY` e `SEU_ELEVENLABS_KEY` pelas chaves reais obtidas no Step 2.

---

## STEP 4: Usar o Meet Agent Script

### 4.1 Localização do Script

O script está em: `/scripts/meet-agent.py`

### 4.2 Usar com Docker

```bash
# Sintaxe básica
docker exec openclaw python3 /scripts/meet-agent.py <MEET_CODE>

# Exemplos
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij"
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij" --name "OpenClaw Bot" --duration 600

# Com câmera/microfone
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij" --camera --no-mic
```

### 4.3 Parâmetros Disponíveis

```
Posicional:
  meet_code          - Código da reunião do Google Meet (obrigatório)

Opções:
  --name TEXT        - Nome do agente na reunião (default: "OpenClaw Agent")
  --duration INT     - Duração máxima em segundos (default: 300, máx: 3600)
  --camera           - Ativar câmera (default: desativado)
  --no-mic           - Desativar microfone (default: ativado)
```

---

## STEP 5: Fluxo Técnico

### Arquitetura do Meet Agent

```
┌─────────────────────────────────────┐
│  Google Meet (Browser Tab)          │
│  - Video/Audio stream               │
│  - Chat messages                    │
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
┌─────────────┐  ┌──────────────┐
│ Chromium    │  │ Deepgram     │
│ (CDP)       │  │ (STT)        │
│ - Click     │  │ - Transcribe │
│ - Navigate  │  │ - Process    │
└─────────────┘  └──────────────┘
      │                 │
      └────────┬────────┘
               │
               ▼
        ┌──────────────┐
        │ Gemini/Claude│
        │ (LLM)        │
        │ - Process    │
        │ - Generate   │
        └──────────────┘
               │
               ▼
        ┌──────────────┐
        │ ElevenLabs   │
        │ (TTS)        │
        │ - Synthesize │
        │ - Play       │
        └──────────────┘
```

### Componentes

| Componente | Função | Status |
|-----------|--------|--------|
| Chromium (CDP Port 18801) | Automate browser interaction | ✅ Built-in |
| Deepgram API | Speech-to-Text | ✅ Plugin loaded |
| ElevenLabs API | Text-to-Speech | ✅ Plugin loaded |
| Google Gemini/Claude | AI Processing | ✅ Available |

---

## STEP 6: Testando o Setup

### 6.1 Verificar Chaves Configuradas

```bash
docker exec openclaw cat /home/node/.openclaw-prod/openclaw.json | grep -A 2 "DEEPGRAM\|ELEVENLABS"
# Deve mostrar as chaves configuradas
```

### 6.2 Testar com Google Meet Real

1. **Criar reunião de teste**:
   - Acesse https://meet.google.com/
   - Clique "Create a meeting" ou "Start an instant meeting"
   - Copie o código (ex: `abc-defg-hij`)

2. **Executar agent**:
   ```bash
   docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij" --duration 60
   ```

3. **Verificar resultado**:
   - O agent deve abrir o Meet no navegador
   - Deve aparecer na lista de participantes (ou próximo)
   - Screenshots salvos em `/tmp/meet-before-join.png` e `/tmp/meet-after-join.png`

---

## STEP 7: Troubleshooting

### Problema: "Command timeout"

**Causa**: Gateway do OpenClaw pode estar ocupado
**Solução**:
```bash
# Reiniciar container
docker restart openclaw

# Aguardar 30 segundos
sleep 30

# Tentar novamente
docker exec openclaw python3 /scripts/meet-agent.py <MEET_CODE>
```

### Problema: "Invalid API Key"

**Causa**: Chave Deepgram ou ElevenLabs inválida
**Solução**:
```bash
# Verificar chaves configuradas
docker exec openclaw cat /home/node/.openclaw-prod/openclaw.json

# Atualizar com chaves válidas
# (usar script do STEP 3 novamente)
```

### Problema: "Browser not responding"

**Causa**: Chromium pode estar travado
**Solução**:
```bash
# Verificar status do browser
docker exec openclaw openclaw --profile prod browser status

# Reiniciar browser
docker exec openclaw pkill chromium
docker exec openclaw docker exec openclaw openclaw --profile prod browser start
```

---

## STEP 8: Casos de Uso

### Use Case 1: Assistant Silencioso (Chat Apenas)

```bash
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij" \
  --no-mic \
  --name "Silent Assistant"
```

**Bom para**: Q&A sessions, technical support

### Use Case 2: Participante de Voz (Audio)

```bash
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij" \
  --duration 3600
```

**Bom para**: Team discussions, brainstorming

### Use Case 3: Apresentador (Com Câmera)

```bash
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij" \
  --camera \
  --name "Screen Presenter"
```

**Bom para**: Presentations, demos

---

## STEP 9: Segurança e Privacidade

### Boas Práticas

✅ Usar headless mode (padrão)
✅ Registrar todas as interações
✅ Redact PII (Personally Identifiable Information)
✅ Criptografar gravações de voz

### Implementação

```bash
# Ativar PII redaction
docker exec openclaw python3 << 'EOF'
import json
config_path = "/home/node/.openclaw-prod/openclaw.json"
with open(config_path, 'r') as f:
    config = json.load(f)
config['logging'] = {
    'level': 'info',
    'redact_pii': True,
    'retention_days': 7
}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
EOF
```

---

## STEP 10: Escalabilidade

### Múltiplas Reuniões Simultâneas

Para suportar múltiplas reuniões:

```bash
# Terminal 1 - Primeira reunião
docker exec openclaw python3 /scripts/meet-agent.py "code1" --duration 1800

# Terminal 2 - Segunda reunião (em paralelo)
docker exec openclaw python3 /scripts/meet-agent.py "code2" --duration 1800
```

**Limitação Atual**: O container único pode suportar 2-3 reuniões simultâneas dependendo de recursos.

### Para Escala Maior

- Use múltiplos containers Docker
- Orquestre com docker-compose ou Kubernetes
- Use filas de reuniões (RabbitMQ/Redis)

---

## Referências

- **OpenClaw Docs**: `/docs/` ou local installation
- **Deepgram API**: https://developers.deepgram.com/
- **ElevenLabs API**: https://elevenlabs.io/docs/
- **Google Meet API**: https://developers.google.com/meet/api/
- **CDP (Chromium DevTools)**: https://chromedevtools.github.io/devtools-protocol/

---

## Changelog

| Data | Versão | Alterações |
|------|--------|-----------|
| 2026-04-26 | 1.0 | Setup inicial, scripts base |
| 2026-04-27 | 1.1 | Troubleshooting expandido |
| 2026-04-28 | 1.2 | Suporte a múltiplas reuniões |

---

## Status

✅ **Production Ready**
🧪 **Tested on**: OpenClaw 2026.4.23
📦 **Requirements**: Deepgram + ElevenLabs API keys
⏱️ **Setup Time**: ~30 minutes

---

## Suporte

Para problemas ou dúvidas:
1. Consulte o guide completo em `/docs/GOOGLE_MEET_SETUP.md`
2. Verifique logs: `docker logs openclaw | tail -100`
3. Teste individual components: `/scripts/test-components.sh`

---

**Criado**: 2026-04-26
**Atualizado**: 2026-04-26
