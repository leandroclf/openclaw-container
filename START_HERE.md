# 🚀 OpenClaw + Google Meet - Comece Aqui

**Objetivo**: Subir OpenClaw em Docker e participar de reuniões Google Meet como assistente de IA.

**Tempo**: 15 minutos (primeira vez) | 2 minutos (próximas vezes)

---

## Opção A: Deploy Automático (Recomendado ⭐)

Se você quiser automatizar tudo de uma vez:

```bash
cd ~/workspace/openclaw-container
./scripts/deploy.sh
```

**O que acontece**:
1. ✅ Verifica Docker
2. ✅ Pede API keys (Deepgram + ElevenLabs - **GRÁTIS**)
3. ✅ Build da imagem Docker
4. ✅ Inicia container
5. ✅ Configura tudo
6. ✅ Oferece testar com Google Meet real

**Tempo estimado**: 10-15 minutos (5-10 min é o build)

---

## Opção B: Deploy Manual (Passo-a-Passo)

Se preferir controle total, siga: **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)**

---

## Opção C: Deploy Com Docker Compose

Para infraestrutura permanente, use:

```bash
# Crie .env file
cat > .env << 'EOF'
DEEPGRAM_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
EOF

# Up
docker-compose up -d

# Check
docker-compose logs -f
```

---

## Depois do Deploy

### 1️⃣ Usar em uma Reunião Real

```bash
# Pega o código da reunião (ex: abc-defg-hij)
docker exec openclaw python3 /scripts/meet-agent.py "abc-defg-hij"

# Pronto! O agente entra na reunião e começa a ouvir
```

### 2️⃣ Ver Logs

```bash
docker logs -f openclaw
```

### 3️⃣ Parar/Reiniciar

```bash
docker stop openclaw     # Para
docker start openclaw    # Reinicia
docker restart openclaw  # Reinicia
```

---

## Features Disponíveis Agora (v2026.4.24)

| Feature | Status | Descrição |
|---------|--------|-----------|
| **Join Google Meet** | ✅ Live | Entra automaticamente em reuniões |
| **Speech-to-Text** | ✅ Live | Deepgram (50 min/mês free) |
| **Text-to-Speech** | ✅ Live | ElevenLabs (10k chars/mês free) |
| **AI Responses** | ✅ Live | Gemini 2.5 Flash (padrão) ou Claude |
| **Meeting Transcripts** | ✅ Live | Gravado automaticamente |
| **Voice Loops** | ✅ Live | Conversação em tempo real |
| **Browser Automation** | ✅ Live | Chromium headless |
| **Multi-Meeting** | ✅ Live | 2-3 reuniões simultâneas |

---

## API Keys Gratuitas (2 minutos)

### Deepgram (Speech-to-Text)
```
URL: https://deepgram.com/
1. Sign up (Google/GitHub)
2. Dashboard → API Keys
3. Create key
Free tier: 50 min/mês
```

### ElevenLabs (Text-to-Speech)
```
URL: https://elevenlabs.io/
1. Sign up
2. Profile → API Key
3. Copy
Free tier: 10k caracteres/mês
```

**Custo para teste**: $0 (completamente grátis)

---

## Casos de Uso

### 📝 Caso 1: Assistente Silencioso
```bash
# Agente observa sem falar
docker exec openclaw python3 /scripts/meet-agent.py "codigo" --no-mic
```
**Bom para**: Coleta de insights, Q&A

### 🎤 Caso 2: Assistente com Áudio
```bash
# Agente participa da conversa
docker exec openclaw python3 /scripts/meet-agent.py "codigo"
```
**Bom para**: Brainstorming, suporte técnico

### 👥 Caso 3: Múltiplas Reuniões
```bash
# Terminal 1
docker exec openclaw python3 /scripts/meet-agent.py "code-1"

# Terminal 2
docker exec openclaw python3 /scripts/meet-agent.py "code-2"
```
**Bom para**: Escalabilidade

---

## Documentação Completa

Se precisar de detalhes:

| Documento | Conteúdo |
|-----------|----------|
| **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** | Deploy passo-a-passo |
| **[GOOGLE_MEET_SETUP.md](GOOGLE_MEET_SETUP.md)** | Integração Google Meet |
| **[GOOGLE_MEET_INTEGRATION.md](GOOGLE_MEET_INTEGRATION.md)** | Arquitetura técnica |
| **[SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)** | Instalação detalhada |
| **[README.md](README.md)** | Overview completo |

---

## Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Docker não instalado | `curl -fsSL https://get.docker.com \| sh` |
| API key inválida | Regenerar em https://deepgram.com/ ou https://elevenlabs.io/ |
| Container não inicia | `docker logs openclaw` para ver erro |
| Gateway não responde | Aguardar 20s depois do start |
| Agente não fala | Verificar Deepgram + ElevenLabs keys |

---

## Checklist Rápido

- [ ] Docker instalado (`docker ps`)
- [ ] Clone o repositório
- [ ] Obter API keys (Deepgram + ElevenLabs)
- [ ] Executar `./scripts/deploy.sh`
- [ ] Aguardar "✓ OpenClaw pronto para Google Meet!"
- [ ] Testar com reunião real
- [ ] ✅ Pronto!

---

## Próximos Passos

1. **Agora**: Execute `./scripts/deploy.sh`
2. **Depois**: Crie uma reunião Google Meet e teste
3. **Escalabilidade**: Configure múltiplas reuniões com `cron`
4. **Customização**: Ajuste model routing, add custom instructions

---

## ⚡ Quick Reference

```bash
# Deploy rápido
./scripts/deploy.sh

# Usar em reunião
docker exec openclaw python3 /scripts/meet-agent.py "CODE"

# Ver status
docker exec openclaw openclaw status

# Ver logs
docker logs -f openclaw

# Parar
docker stop openclaw

# Deletar tudo e recomeçar
./scripts/deploy.sh --clean
```

---

## Precisa de Ajuda?

1. **Instalação**: Veja `SETUP_INSTRUCTIONS.md`
2. **Google Meet**: Veja `GOOGLE_MEET_SETUP.md`
3. **Arquitetura**: Veja `GOOGLE_MEET_INTEGRATION.md`
4. **Operações**: Veja `README.md`
5. **Logs**: `docker logs openclaw | tail -50`

---

**Status**: ✅ Production Ready
**Versão**: 2026.4.24
**Data**: 2026-04-26

---

## 🎯 Let's Go!

```bash
cd ~/workspace/openclaw-container
./scripts/deploy.sh
```

Your AI assistant is ready to join Google Meet! 🎉
