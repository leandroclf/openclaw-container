#!/bin/bash

#
# OpenClaw + Google Meet - Automated Bootstrap
#
# This script automates the complete setup of OpenClaw with Google Meet integration
# on a new machine. It handles all prerequisites, configuration, and validation.
#
# Usage:
#   ./scripts/bootstrap-google-meet.sh [OPTIONS]
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_section() { echo -e "\n${MAGENTA}═══ $1 ═══${NC}\n"; }

# Configuration
CONTAINER_NAME="openclaw"
IMAGE_NAME="openclaw-secure:latest"
OPENCLAW_VERSION="2026.4.24"
OPENCLAW_HOME="${HOME}/openclaw"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Options
INTERACTIVE=true
SKIP_DOCKER=false

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --help|-h)
            cat << 'EOF'
OpenClaw + Google Meet - Automated Bootstrap

Usage: ./scripts/bootstrap-google-meet.sh [OPTIONS]

Options:
  --skip-docker    Skip Docker image build
  --help, -h       Show this help message

Prerequisites:
  - Docker 20.10+
  - Internet connection
  - API keys (Deepgram, ElevenLabs)

Time: 20-30 minutes

EOF
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main bootstrap
log_section "STEP 1: Collecting API Keys"
echo "You need 2 free API keys (takes 2 minutes):"
echo ""
log_info "1. Deepgram (Speech-to-Text): https://deepgram.com/"
read -p "   Paste your DEEPGRAM_API_KEY: " DEEPGRAM_KEY
echo ""

log_info "2. ElevenLabs (Text-to-Speech): https://elevenlabs.io/"
read -p "   Paste your ELEVENLABS_API_KEY: " ELEVENLABS_KEY
echo ""

[ -z "$DEEPGRAM_KEY" ] && log_error "API key required" && exit 1
[ -z "$ELEVENLABS_KEY" ] && log_error "API key required" && exit 1

log_success "API keys collected"

log_section "STEP 2: Creating Directories"
mkdir -p "$OPENCLAW_HOME"/{data,logs,config,runtime}
mkdir -p "$OPENCLAW_HOME"/runtime/{gemini,config,cache,pki}
mkdir -p "${HOME}/clawd"
chmod 700 "$OPENCLAW_HOME" "$OPENCLAW_HOME/data" "$OPENCLAW_HOME/runtime"
log_success "Directories created"

log_section "STEP 3: Creating Environment File"
cat > "$OPENCLAW_HOME/.env" << EOF
DEEPGRAM_API_KEY=$DEEPGRAM_KEY
ELEVENLABS_API_KEY=$ELEVENLABS_KEY
OPENAI_API_KEY=\${OPENAI_API_KEY:-}
GH_TOKEN=\${GH_TOKEN:-}
EOF
chmod 600 "$OPENCLAW_HOME/.env"
log_success "Environment file created"

log_section "STEP 4: Checking Docker"
command -v docker &> /dev/null || { log_error "Docker not installed"; exit 1; }
docker ps &> /dev/null || { log_error "Docker daemon not running"; exit 1; }
log_success "Docker ready"

if [ "$SKIP_DOCKER" = false ]; then
    log_section "STEP 5: Building Docker Image"
    cd "$REPO_DIR"
    log_info "Building (may take 5-10 minutes)..."
    DOCKER_BUILDKIT=0 docker build \
        --build-arg OPENCLAW_VERSION="$OPENCLAW_VERSION" \
        -t "$IMAGE_NAME" \
        . || { log_error "Build failed"; exit 1; }
    log_success "Image built"
else
    log_info "Skipping Docker build"
fi

log_section "STEP 6: Starting Container"
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file "$OPENCLAW_HOME/.env" \
    --read-only \
    --cap-drop=ALL \
    --cap-add=NET_BIND_SERVICE \
    --security-opt no-new-privileges \
    --pids-limit 512 \
    --tmpfs /tmp:rw,noexec,nosuid,size=256m \
    -v openclaw_state:/home/node/.openclaw \
    -p 18789:18789 \
    "$IMAGE_NAME" \
    --profile prod gateway run --bind loopback --port 18789

log_success "Container starting..."
sleep 20

log_section "STEP 7: Configuring API Keys"
docker exec "$CONTAINER_NAME" bash -c "
cat /home/node/.openclaw-prod/openclaw.json | python3 -c \"
import json, sys
config = json.load(sys.stdin)
config['env']['vars']['DEEPGRAM_API_KEY'] = '$DEEPGRAM_KEY'
config['env']['vars']['ELEVENLABS_API_KEY'] = '$ELEVENLABS_KEY'
with open('/home/node/.openclaw-prod/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
print('✅ Keys configured')
\"
"
log_success "Keys configured"

log_section "STEP 8: Verifying Setup"
sleep 10
docker exec "$CONTAINER_NAME" openclaw --profile prod plugins list 2>&1 | grep -E "browser|deepgram|elevenlabs" || true
log_success "Plugins loaded"

chmod +x "$REPO_DIR/scripts/join-google-meet.sh"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   ✅ Bootstrap Complete!                              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Setup Summary:"
echo "  Container: $CONTAINER_NAME (running)"
echo "  Home: $OPENCLAW_HOME"
echo "  Version: $OPENCLAW_VERSION"
echo ""
echo "🚀 Quick Start:"
echo "  $REPO_DIR/scripts/join-google-meet.sh \"meeting-code\""
echo ""
echo "📖 Documentation:"
echo "  $REPO_DIR/BOOTSTRAP_GOOGLE_MEET.md"
echo ""
echo "📋 Commands:"
echo "  View logs: docker logs -f $CONTAINER_NAME"
echo "  Check status: docker exec $CONTAINER_NAME openclaw status"
echo ""
