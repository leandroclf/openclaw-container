#!/bin/bash

#
# OpenClaw + Google Meet - Automated Deployment
#
# Uso:
#   ./scripts/deploy.sh              # Interactive mode
#   ./scripts/deploy.sh --auto       # Auto mode (reuse existing keys)
#   ./scripts/deploy.sh --clean      # Remove everything and rebuild
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OPENCLAW_VERSION="${OPENCLAW_VERSION:-2026.4.24}"
CONTAINER_NAME="openclaw"
IMAGE_NAME="openclaw-secure:latest"
VOLUME_NAME="openclaw_state"
ENV_FILE="${HOME}/.openclaw.env"
MAX_RETRIES=30
RETRY_DELAY=2

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker não instalado. Instale via: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker ps &> /dev/null; then
        log_error "Docker daemon não está rodando. Inicie com: systemctl start docker"
        exit 1
    fi

    log_success "Docker disponível"
}

get_api_keys() {
    if [[ -f "$ENV_FILE" ]]; then
        log_warn "Arquivo $ENV_FILE já existe"
        read -p "Usar chaves existentes? (s/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            source "$ENV_FILE"
            return
        fi
    fi

    log_info "Você precisa de 2 API keys gratuitas (leva 2 min):"
    echo ""

    # Deepgram
    log_info "1. Deepgram (Speech-to-Text)"
    echo "   - Acesse: https://deepgram.com/"
    echo "   - Sign Up (Google/GitHub)"
    echo "   - Dashboard → API Keys → Create Key"
    echo ""
    read -p "   Cole sua DEEPGRAM_API_KEY: " DEEPGRAM_API_KEY

    if [[ -z "$DEEPGRAM_API_KEY" ]]; then
        log_error "Deepgram key não pode estar vazia"
        exit 1
    fi

    echo ""

    # ElevenLabs
    log_info "2. ElevenLabs (Text-to-Speech)"
    echo "   - Acesse: https://elevenlabs.io/"
    echo "   - Sign Up (free trial)"
    echo "   - Profile → API Key"
    echo ""
    read -p "   Cole sua ELEVENLABS_API_KEY: " ELEVENLABS_API_KEY

    if [[ -z "$ELEVENLABS_API_KEY" ]]; then
        log_error "ElevenLabs key não pode estar vazia"
        exit 1
    fi

    # Save to env file
    cat > "$ENV_FILE" << EOF
DEEPGRAM_API_KEY=$DEEPGRAM_API_KEY
ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY
EOF
    chmod 600 "$ENV_FILE"

    log_success "Chaves salvas em $ENV_FILE"
}

build_image() {
    if docker images | grep -q "openclaw-secure.*latest"; then
        read -p "Imagem já existe. Rebuildar? (s/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            log_success "Usando imagem existente"
            return
        fi
    fi

    log_info "Building Docker image (pode levar 5-10 min)..."

    DOCKER_BUILDKIT=0 docker build \
        --build-arg OPENCLAW_VERSION="$OPENCLAW_VERSION" \
        -t "$IMAGE_NAME" \
        . || {
        log_error "Build falhou"
        exit 1
    }

    log_success "Image built: $IMAGE_NAME"
}

create_volume() {
    if docker volume ls | grep -q "openclaw_state"; then
        log_warn "Volume $VOLUME_NAME já existe"
    else
        docker volume create "$VOLUME_NAME"
        log_success "Volume criado: $VOLUME_NAME"
    fi
}

stop_container() {
    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_info "Parando container $CONTAINER_NAME..."
        docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    fi

    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        docker rm "$CONTAINER_NAME" > /dev/null 2>&1
        log_success "Container removido"
    fi
}

start_container() {
    log_info "Iniciando container $CONTAINER_NAME..."

    # Load env vars
    source "$ENV_FILE"

    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        --cap-drop=ALL \
        --cap-add=NET_BIND_SERVICE \
        --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,size=256m \
        --tmpfs /run \
        --tmpfs /home/node/.openclaw/tmp \
        -e DEEPGRAM_API_KEY="$DEEPGRAM_API_KEY" \
        -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
        -v "$VOLUME_NAME:/home/node/.openclaw" \
        -p 18789:18789 \
        "$IMAGE_NAME" \
        --profile prod gateway run --bind loopback --port 18789 || {
        log_error "Falha ao iniciar container"
        exit 1
    }

    log_success "Container iniciado"
}

wait_for_health() {
    log_info "Aguardando inicialização (até 60 segundos)..."

    for i in $(seq 1 $MAX_RETRIES); do
        if docker exec "$CONTAINER_NAME" openclaw --profile prod gateway health &> /dev/null; then
            log_success "Container saudável"
            return 0
        fi

        # Show progress
        printf "\r   Tentativa %d/%d..." "$i" "$MAX_RETRIES"
        sleep $RETRY_DELAY
    done

    echo ""
    log_warn "Container ainda não está pronto. Tente: docker logs openclaw"
    return 1
}

configure_keys() {
    log_info "Configurando API keys no container..."

    source "$ENV_FILE"

    docker exec "$CONTAINER_NAME" python3 << EOF
import json
import os

config_path = "/home/node/.openclaw-prod/openclaw.json"

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except:
    config = {"env": {"vars": {}}}

if 'env' not in config:
    config['env'] = {}
if 'vars' not in config['env']:
    config['env']['vars'] = {}

config['env']['vars']['DEEPGRAM_API_KEY'] = "$DEEPGRAM_API_KEY"
config['env']['vars']['ELEVENLABS_API_KEY'] = "$ELEVENLABS_API_KEY"

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Chaves configuradas")
EOF

    log_success "Chaves configuradas no container"
}

verify_plugins() {
    log_info "Verificando plugins..."

    plugins=$(docker exec "$CONTAINER_NAME" openclaw --profile prod plugins list 2>&1 || echo "")

    # Check for key plugins
    if echo "$plugins" | grep -q "browser"; then
        log_success "Plugin browser ✓"
    fi

    if echo "$plugins" | grep -q "deepgram"; then
        log_success "Plugin deepgram ✓"
    fi

    if echo "$plugins" | grep -q "elevenlabs"; then
        log_success "Plugin elevenlabs ✓"
    fi
}

test_meet() {
    echo ""
    read -p "Testar com Google Meet agora? (s/n) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        return
    fi

    log_info "Siga os passos:"
    echo "  1. Acesse: https://meet.google.com/"
    echo "  2. Clique em 'Start an instant meeting'"
    echo "  3. Copie o código (ex: abc-defg-hij)"
    echo ""

    read -p "Cole o código da reunião: " MEET_CODE

    if [[ -z "$MEET_CODE" ]]; then
        log_warn "Teste cancelado"
        return
    fi

    log_info "Iniciando agent na reunião..."
    docker exec "$CONTAINER_NAME" python3 /scripts/meet-agent.py "$MEET_CODE" \
        --name "OpenClaw Assistant" \
        --duration 60

    log_success "Teste concluído. Verifique os logs: docker logs openclaw"
}

print_summary() {
    echo ""
    echo "════════════════════════════════════════════════════════"
    log_success "OpenClaw está pronto para Google Meet!"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "📋 Próximas ações:"
    echo ""
    echo "  1. Usar em reunião:"
    echo "     docker exec openclaw python3 /scripts/meet-agent.py <MEET_CODE>"
    echo ""
    echo "  2. Ver status:"
    echo "     docker exec openclaw openclaw status"
    echo ""
    echo "  3. Ver logs:"
    echo "     docker logs openclaw -f"
    echo ""
    echo "  4. Parar container:"
    echo "     docker stop openclaw"
    echo ""
    echo "  5. Mais opções:"
    echo "     cat QUICK_DEPLOY.md"
    echo ""
    echo "════════════════════════════════════════════════════════"
}

clean_all() {
    log_warn "Limpando tudo..."

    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    docker rmi "$IMAGE_NAME" 2>/dev/null || true
    docker volume rm "$VOLUME_NAME" 2>/dev/null || true

    log_success "Limpeza concluída"
}

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║   OpenClaw + Google Meet - Automated Deployment       ║"
    echo "║   Version: $OPENCLAW_VERSION                             ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""

    # Parse arguments
    if [[ "$1" == "--clean" ]]; then
        clean_all
        exit 0
    fi

    AUTO_MODE=false
    if [[ "$1" == "--auto" ]]; then
        AUTO_MODE=true
    fi

    # Execute steps
    check_docker

    if [[ "$AUTO_MODE" == true ]]; then
        log_info "Modo automático (reusando chaves existentes)"
    fi

    get_api_keys
    build_image
    create_volume
    stop_container
    start_container
    wait_for_health && configure_keys
    verify_plugins

    print_summary

    if [[ "$AUTO_MODE" == false ]]; then
        test_meet
    fi
}

main "$@"
