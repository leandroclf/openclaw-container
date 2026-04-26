#!/bin/bash

#
# OpenClaw Google Meet - Quick Configuration
#
# Configura Deepgram + ElevenLabs na instância existente
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check if container is running
if ! docker ps | grep -q openclaw; then
    log_error "Container 'openclaw' não está rodando"
    log_info "Inicie com: docker start openclaw"
    exit 1
fi

log_success "Container openclaw detectado"

# Get API keys
echo ""
log_info "Obter 2 API keys gratuitas (leva 2 minutos):"
echo ""

log_info "1️⃣  Deepgram (Speech-to-Text)"
echo "   Acesse: https://deepgram.com/"
echo "   - Sign Up (Google/GitHub)"
echo "   - Dashboard → API Keys → Create Key"
echo ""
read -p "   Cole sua DEEPGRAM_API_KEY: " DEEPGRAM_KEY

if [[ -z "$DEEPGRAM_KEY" ]]; then
    log_error "Chave Deepgram não pode estar vazia"
    exit 1
fi

echo ""
log_info "2️⃣  ElevenLabs (Text-to-Speech)"
echo "   Acesse: https://elevenlabs.io/"
echo "   - Sign Up (free trial)"
echo "   - Profile → API Key"
echo ""
read -p "   Cole sua ELEVENLABS_API_KEY: " ELEVENLABS_KEY

if [[ -z "$ELEVENLABS_KEY" ]]; then
    log_error "Chave ElevenLabs não pode estar vazia"
    exit 1
fi

# Configure keys in container
echo ""
log_info "Configurando chaves no container..."

docker exec openclaw python3 << EOF
import json
import os

config_path = "/home/node/.openclaw-prod/openclaw.json"

# Load existing config
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {"env": {"vars": {}}}
except json.JSONDecodeError:
    config = {"env": {"vars": {}}}

# Ensure structure exists
if 'env' not in config:
    config['env'] = {}
if 'vars' not in config['env']:
    config['env']['vars'] = {}

# Add API keys
config['env']['vars']['DEEPGRAM_API_KEY'] = "$DEEPGRAM_KEY"
config['env']['vars']['ELEVENLABS_API_KEY'] = "$ELEVENLABS_KEY"

# Save config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Chaves configuradas com sucesso")
EOF

log_success "Chaves salvass no container"

# Verify configuration
echo ""
log_info "Verificando configuração..."

docker exec openclaw python3 << 'EOF'
import json

config_path = "/home/node/.openclaw-prod/openclaw.json"
with open(config_path, 'r') as f:
    config = json.load(f)

has_deepgram = 'DEEPGRAM_API_KEY' in config.get('env', {}).get('vars', {})
has_elevenlabs = 'ELEVENLABS_API_KEY' in config.get('env', {}).get('vars', {})

print(f"Deepgram configurado: {'✅' if has_deepgram else '❌'}")
print(f"ElevenLabs configurado: {'✅' if has_elevenlabs else '❌'}")
EOF

echo ""
log_success "✅ Google Meet pronto para usar!"

echo ""
echo "════════════════════════════════════════════════════════"
echo "📋 Próximas ações:"
echo "════════════════════════════════════════════════════════"
echo ""
echo "1️⃣  Criar uma reunião Google Meet:"
echo "   https://meet.google.com/"
echo "   → Create a meeting → Copy the code (ex: abc-defg-hij)"
echo ""
echo "2️⃣  Entrar na reunião com o OpenClaw:"
echo "   docker exec openclaw python3 /scripts/meet-agent.py \"abc-defg-hij\""
echo ""
echo "3️⃣  Ver logs em tempo real:"
echo "   docker logs -f openclaw"
echo ""
echo "4️⃣  Opções adicionais:"
echo "   --no-mic     : Assistente silencioso (apenas observa)"
echo "   --duration N : Duração em segundos (default: 300, max: 3600)"
echo "   --name TEXT  : Nome do agente na reunião"
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo "Exemplo com opções:"
echo "  docker exec openclaw python3 /scripts/meet-agent.py \"abc-defg-hij\" \\"
echo "    --name \"My AI Assistant\" \\"
echo "    --duration 1800"
echo ""
