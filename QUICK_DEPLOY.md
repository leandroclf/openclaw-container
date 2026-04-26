# OpenClaw + Google Meet - Deployment Rápido

**Objetivo**: Subir OpenClaw em Docker e participar de reuniões Google Meet como assistente de IA.

**Tempo Estimado**: 15-20 minutos (primeira vez) | 2 minutos (próximas vezes)

---

## Pré-requisitos Verificados

```bash
# Sistema
docker --version              # Docker 20.10+
docker-compose --version      # 1.29+

# Você precisa de:
# ✅ Docker instalado e rodando
# ✅ Conta Google (para o Google Meet)
# ✅ Acesso à internet (APIs Deepgram + ElevenLabs)
```

---

## FASE 1: Build do Container (5 min)

### 1.1 Clonar repositório
```bash
cd ~/workspace
git clone git@github.com:leandroclf/openclaw-container.git
cd openclaw-container
```

### 1.2 Build da imagem
```bash
# Build com versão específica (2026.4.24 = latest stable)
DOCKER_BUILDKIT=0 docker build \
  --build-arg OPENCLAW_VERSION=2026.4.24 \
  -t openclaw-secure:latest \
  .

# ⏱️ Isto pode levar 5-10 minutos
# ☕ Aproveita para anotar as API keys (próximo passo)
```

**Verificar build**:
```bash
docker images | grep openclaw
# Esperado: openclaw-secure   latest   <IMAGE_ID>   ~1.2GB
```

---

## FASE 2: Obter API Keys Gratuitas (3 min)

### 2.1 Deepgram (Speech-to-Text)

```bash
# 1. Acesse: https://deepgram.com/
# 2. Sign Up (com Google/GitHub)
# 3. Dashboard → API Keys
# 4. Click em "Create Key"
# 5. Copy a chave

# Será algo como:
DEEPGRAM_API_KEY="8cfd9559f0330df0b4039c50e3a6cc54590932d4"
```

**Free Tier**: 50 minutos/mês (suficiente para testes)

### 2.2 ElevenLabs (Text-to-Speech)

```bash
# 1. Acesse: https://elevenlabs.io/
# 2. Sign Up (free trial)
# 3. Profile → API Key (icone no canto superior direito)
# 4. Copy a chave

# Será algo como:
ELEVENLABS_API_KEY="sk_72749c6b234561eeb02ea5a718f175046f2edc7bab4912ff"
```

**Free Tier**: 10.000 caracteres/mês (suficiente para testes)

---

## FASE 3: Rodar Container (3 min)

### 3.1 Preparar variáveis de ambiente

```bash
# Salvar as chaves
cat > /tmp/openclaw.env << 'EOF'
DEEPGRAM_API_KEY=YOUR_DEEPGRAM_KEY_HERE
ELEVENLABS_API_KEY=YOUR_ELEVENLABS_KEY_HERE
EOF
```

**Substitua**:
- `YOUR_DEEPGRAM_KEY_HERE` → chave do Deepgram
- `YOUR_ELEVENLABS_KEY_HERE` → chave do ElevenLabs

### 3.2 Rodar container

```bash
# Remover container antigo (se existir)
docker rm -f openclaw 2>/dev/null || true

# Rodar novo container
docker run -d \
  --name openclaw \
  --restart unless-stopped \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --tmpfs /run \
  --tmpfs /home/node/.openclaw/tmp \
  --env-file /tmp/openclaw.env \
  -v openclaw_state:/home/node/.openclaw \
  -p 18789:18789 \
  openclaw-secure:latest \
  --profile prod gateway run --bind loopback --port 18789

# ⏱️ Aguardar 10-15 segundos para inicializar
sleep 15
```

### 3.3 Verificar status

```bash
# Health check
docker exec openclaw openclaw --profile prod gateway health

# Esperado: "Gateway is healthy" ou código 200

# Se erro 1006: é normal nos primeiros 10s, aguarde mais um pouco
```

---

## FASE 4: Configurar API Keys no Container (2 min)

### 4.1 Adicionar chaves à configuração

```bash
# Substitua as chaves REAIS aqui
docker exec openclaw python3 << 'EOF'
import json

config_path = "/home/node/.openclaw-prod/openclaw.json"

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {"env": {"vars": {}}}

# Adicionar as chaves (SUBSTITUA PELOS VALORES REAIS)
config['env'] = config.get('env', {})
config['env']['vars'] = config['env'].get('vars', {})
config['env']['vars']['DEEPGRAM_API_KEY'] = "YOUR_DEEPGRAM_KEY"
config['env']['vars']['ELEVENLABS_API_KEY'] = "YOUR_ELEVENLABS_KEY"

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Chaves configuradas com sucesso")
EOF
```

### 4.2 Verificar plugins carregados

```bash
docker exec openclaw openclaw --profile prod plugins list | grep -E "browser|deepgram|elevenlabs|gemini"

# Esperado:
# ✅ browser plugin loaded
# ✅ deepgram plugin loaded
# ✅ elevenlabs plugin loaded
# ✅ gemini plugin loaded
```

---

## FASE 5: Testar com Google Meet Real (5 min)

### 5.1 Criar reunião de teste

```bash
# Acesse: https://meet.google.com/
# Clique: "Create a meeting" ou "Start an instant meeting"
# Você receberá um código como: abc-defg-hij

# COPIE O CÓDIGO
MEET_CODE="abc-defg-hij"
```

### 5.2 Executar agente na reunião

```bash
# Usar o meet-agent script
docker exec openclaw python3 /scripts/meet-agent.py "$MEET_CODE" \
  --name "OpenClaw Assistant" \
  --duration 60

# ⏱️ O agente vai:
# 1. Abrir o navegador headless
# 2. Navegar para meet.google.com/abc-defg-hij
# 3. Tentar clicar em "Join"
# 4. Ouvir a reunião
# 5. Responder automaticamente
```

### 5.3 Verificar resultado

```bash
# Screenshots foram criadas?
docker exec openclaw ls -lah /tmp/meet-*.png

# Ver logs
docker logs openclaw | tail -20

# Você deve ver mensagens como:
# [INFO] Browser opened Meet link
# [INFO] Joining meeting...
# [INFO] Deepgram listening...
# [INFO] Processing audio...
```

---

## FASE 6: Usar em Reuniões Reais (Contínuo)

### 6.1 Cenário 1: Assistente Silencioso (Chat apenas)

```bash
# Use quando quiser que o agente observe mas não fale
docker exec openclaw python3 /scripts/meet-agent.py "seu-codigo-meet" \
  --no-mic \
  --name "Silent Assistant" \
  --duration 1800  # 30 minutos
```

**Bom para**: Monitorar discussões, coletar insights

### 6.2 Cenário 2: Assistente com Áudio

```bash
# Use para interação em tempo real
docker exec openclaw python3 /scripts/meet-agent.py "seu-codigo-meet" \
  --name "Voice Assistant" \
  --duration 3600  # 1 hora
```

**Bom para**: Q&A, brainstorming, technical support

### 6.3 Cenário 3: Múltiplas Reuniões (em paralelo)

```bash
# Terminal 1
docker exec openclaw python3 /scripts/meet-agent.py "code-1" --duration 1800

# Terminal 2 (simultaneamente)
docker exec openclaw python3 /scripts/meet-agent.py "code-2" --duration 1800
```

---

## Features da Nova Versão (2026.4.24)

### ✅ Já incluído
- **Browser Automation** (headless Chromium)
- **Speech-to-Text** via Deepgram
- **Text-to-Speech** via ElevenLabs
- **Model Routing** (Gemini Flash por padrão, fallback para Claude)
- **Meeting Transcripts** (saved automatically)
- **Voice Loops** (realtime conversation)

### 🚀 Próximas Features (roadmap)
- [ ] Chat message sending
- [ ] Screen sharing support
- [ ] Multi-participant detection
- [ ] Real-time translation
- [ ] Action items extraction
- [ ] Meeting summary generation

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| **"Browser timeout"** | Aumentar wait time ou reiniciar container: `docker restart openclaw` |
| **"API key invalid"** | Verificar chaves no config: `docker exec openclaw cat /home/node/.openclaw-prod/openclaw.json \| grep -A2 DEEPGRAM` |
| **"Gateway not healthy"** | Aguardar 20s após start, ou: `docker logs openclaw` para ver erro |
| **Container not starting** | Check resources: `docker stats` e aumentar RAM se needed |
| **No audio being picked up** | Verificar Deepgram status: `curl https://api.deepgram.com/v1/status -H "Authorization: Token $DEEPGRAM_KEY"` |

---

## Checklist de Deploy

- [ ] Docker instalado e rodando (`docker ps`)
- [ ] Repositório clonado (`cd openclaw-container`)
- [ ] Build completo (`docker images | grep openclaw`)
- [ ] API keys obtidas (Deepgram + ElevenLabs)
- [ ] Container rodando (`docker ps | grep openclaw`)
- [ ] Plugins carregados (`docker exec openclaw openclaw --profile prod plugins list`)
- [ ] Testado com reunião real (Google Meet test)
- [ ] Pronto para produção ✅

---

## Monitoramento & Manutenção

### Verificar saúde do sistema
```bash
# Status geral
docker exec openclaw openclaw status

# Usar recursos
docker stats openclaw

# Ver logs em tempo real
docker logs -f openclaw
```

### Backup diário
```bash
# Criar snapshot
docker exec openclaw openclaw backup create

# Limpar logs antigos (>7 dias)
docker exec openclaw find /home/node/.openclaw -name "*.log" -mtime +7 -delete
```

### Atualizar OpenClaw
```bash
# Verificar versão disponível
docker exec openclaw openclaw update check

# Atualizar (safe)
docker exec openclaw openclaw update --confirm
```

---

## Próximos Passos

1. ✅ **Setup Completo**: Container rodando + Google Meet integrado
2. ⏭️ **Customização**: Adjust model routing, add custom instructions
3. ⏭️ **Escalabilidade**: Múltiplas reuniões simultâneas
4. ⏭️ **Automação**: Schedule reuniões automáticas com `cron`

---

## Referências Rápidas

- **Documentação Completa**: `GOOGLE_MEET_INTEGRATION.md`
- **Setup Detalhado**: `SETUP_INSTRUCTIONS.md`
- **Google Meet Guide**: `GOOGLE_MEET_SETUP.md`
- **Operações**: `README.md` seção "Operations guide"

---

**Status**: ✅ Production Ready | **Versão**: 2026.4.24 | **Data**: 2026-04-26
