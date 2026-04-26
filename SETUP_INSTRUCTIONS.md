# OpenClaw Container - Setup Instructions

**Versão OpenClaw**: 2026.4.23+
**Última Atualização**: 26 de Abril, 2026
**Status**: ✅ Production Ready with Google Meet Integration

---

## Quick Start (5 minutos)

```bash
# 1. Clone o repositório
git clone git@github.com:leandroclf/openclaw-container.git
cd openclaw-container

# 2. Build do container
docker build -t openclaw-secure:latest .

# 3. Rodar o container
docker run -d \
  --name openclaw \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --read-only \
  -e DEEPGRAM_API_KEY="your_deepgram_key" \
  -e ELEVENLABS_API_KEY="your_elevenlabs_key" \
  -v openclaw_state:/home/node/.openclaw \
  -p 18789:18789 \
  openclaw-secure:latest

# 4. Verificar status
docker exec openclaw openclaw status
```

---

## Pré-requisitos

### Sistema
- Docker 20.10+
- Linux kernel 5.10+ (ou WSL2 no Windows)
- 2GB RAM mínimo, 4GB recomendado
- 500MB disk space

### APIs Externas (Free Tier)
- **Deepgram**: https://deepgram.com/ (free tier: 50 minutos/mês)
- **ElevenLabs**: https://elevenlabs.io/ (free tier: 10k caracteres/mês)
- **Google Gemini**: https://ai.google.dev/ (free tier: 60 req/min)

---

## Configuração Detalhada

### Passo 1: Build do Container

```bash
# Build com cache busting (sempre rebuild)
docker build \
  --no-cache \
  -t openclaw-secure:latest \
  --build-arg OPENCLAW_VERSION=2026.4.24 \
  .

# Verificar tamanho
docker images | grep openclaw
# Esperado: ~1.2GB
```

### Passo 2: Preparar Variáveis de Ambiente

```bash
# Crie um arquivo .env
cat > .env << 'EOF'
DEEPGRAM_API_KEY=your_deepgram_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
OPENAI_API_KEY=your_openai_key_here
GITHUB_TOKEN=your_gh_token_here
EOF

# Não commitar .env (add to .gitignore)
echo ".env" >> .gitignore
```

### Passo 3: Rodar o Container

```bash
# Opção A: Produção (Recomendado)
docker run -d \
  --name openclaw \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /run \
  --tmpfs /home/node/.openclaw/tmp \
  -e DEEPGRAM_API_KEY="$DEEPGRAM_API_KEY" \
  -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  -v openclaw_state:/home/node/.openclaw \
  -p 18789:18789 \
  openclaw-secure:latest

# Opção B: Desenvolvimento (com acesso de escrita)
docker run -d \
  --name openclaw-dev \
  -e DEEPGRAM_API_KEY="$DEEPGRAM_API_KEY" \
  -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  -v ./openclaw-data:/home/node/.openclaw \
  -v /tmp/openclaw:/tmp \
  -p 18789:18789 \
  openclaw-secure:latest
```

### Passo 4: Verificar Setup

```bash
# Aguardar 10-15 segundos para inicialização
sleep 15

# Verificar status
docker exec openclaw openclaw status

# Esperado:
# - Gateway: reachable
# - Plugins: 61/102 loaded
# - Browser: enabled

# Verificar plugins de voz
docker exec openclaw openclaw --profile prod plugins list | \
  grep -E "deepgram|elevenlabs|browser|google"
```

---

## Configuração para Google Meet

### Passo 1: Obter API Keys

Siga o guia em `GOOGLE_MEET_SETUP.md` STEP 2 para obter as chaves.

### Passo 2: Configurar Chaves

```bash
# Opção A: Variáveis de ambiente (runtime)
docker exec openclaw bash -c '
export DEEPGRAM_API_KEY="your_key"
export ELEVENLABS_API_KEY="your_key"
'

# Opção B: Arquivo de configuração (persistente)
docker exec openclaw python3 << 'EOF'
import json
config_path = "/home/node/.openclaw-prod/openclaw.json"
with open(config_path, 'r') as f:
    config = json.load(f)
config['env']['vars']['DEEPGRAM_API_KEY'] = "your_key"
config['env']['vars']['ELEVENLABS_API_KEY'] = "your_key"
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print("✅ Chaves configuradas")
EOF
```

### Passo 3: Usar o Meet Agent

```bash
# Ver guia completo
cat GOOGLE_MEET_SETUP.md

# Executar agente em uma reunião
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij"
```

---

## Troubleshooting

### Container não inicia

```bash
# Verificar logs
docker logs openclaw

# Verificar recursos
docker stats openclaw

# Se out of memory:
docker update --memory 4g openclaw
docker restart openclaw
```

### Browser não funciona

```bash
# Verificar Chromium
docker exec openclaw which chromium

# Verificar CDP port
docker exec openclaw lsof -i :18801

# Reiniciar browser
docker exec openclaw pkill chromium
docker exec openclaw openclaw --profile prod browser start
```

### Plugins não carregam

```bash
# Verificar plugins list
docker exec openclaw openclaw plugins list

# Reiniciar container
docker restart openclaw

# Verificar logs
docker logs openclaw | tail -50
```

---

## Segurança

### Security Checklist

✅ Read-only filesystem (em produção)
✅ Dropped capabilities (CAP_DROP=ALL)
✅ Non-root user (node:node)
✅ No NOPASSWD sudo (removido)
✅ Limited tmpfs (não persistente)
✅ Signed base image
✅ Regular updates (2026.4.24+)

### Audit

```bash
# Verificar configuração de segurança
docker exec openclaw openclaw security audit

# Redact PII from logs
docker exec openclaw openclaw config set logging.redact-pii true

# Limitar logs a 7 dias
docker exec openclaw openclaw config set logging.retention-days 7
```

---

## Performance

### Recomendações

| Cenário | CPU | RAM | Disco |
|---------|-----|-----|-------|
| Single agent | 1 core | 2GB | 500MB |
| Multiple meetings (2-3) | 2 cores | 4GB | 1GB |
| Production cluster | 4+ cores | 8GB+ | 10GB+ |

### Otimização

```bash
# Limpar logs antigos
docker exec openclaw find /home/node/.openclaw -name "*.log" -mtime +7 -delete

# Compact database
docker exec openclaw sqlite3 /home/node/.openclaw/memory-search.db "VACUUM;"

# Cache optimization
docker exec openclaw openclaw config set cache.ttl-minutes 60
```

---

## Atualizações

### Atualizar OpenClaw

```bash
# Verificar versão disponível
docker exec openclaw openclaw update check

# Atualizar (safe)
docker exec openclaw openclaw update --confirm

# Ou rebuildar container
docker build --build-arg OPENCLAW_VERSION=2026.4.25 -t openclaw-secure:latest .
```

---

## Volumes

### Dados Persistentes

```bash
# Criar volume
docker volume create openclaw_state

# Backup
docker run --rm \
  -v openclaw_state:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/openclaw-backup.tar.gz -C /data .

# Restore
docker run --rm \
  -v openclaw_state:/data \
  -v $(pwd):/backup \
  busybox tar xzf /backup/openclaw-backup.tar.gz -C /data
```

---

## Docker Compose

Para facilitar, use este `docker-compose.yml`:

```yaml
version: '3.8'

services:
  openclaw:
    image: openclaw-secure:latest
    build:
      context: .
      args:
        OPENCLAW_VERSION: 2026.4.24
    container_name: openclaw
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
      - /run
      - /home/node/.openclaw/tmp
    environment:
      DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY}
      ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - openclaw_state:/home/node/.openclaw
    ports:
      - "18789:18789"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "openclaw", "status"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  openclaw_state:
```

**Uso**:
```bash
# Build e run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Próximos Passos

1. ✅ Build container
2. ✅ Configurar variáveis de ambiente
3. ✅ Obter API keys (Deepgram, ElevenLabs)
4. ✅ Rodar container
5. ⏭️ Ler `GOOGLE_MEET_SETUP.md` para integração
6. ⏭️ Testar com reunião real

---

## Suporte

- **Documentação**: `/docs/`
- **Issues**: GitHub Issues
- **Logs**: `docker logs openclaw`
- **Status**: `docker exec openclaw openclaw status`

---

**Versão**: 1.2
**Data**: 2026-04-26
**Autor**: OpenClaw Team
