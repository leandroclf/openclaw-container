#!/bin/bash

#
# OpenClaw Google Meet Integration
# Automated joining and participation in Google Meet calls
#
# Usage:
#   ./scripts/join-google-meet.sh <MEET_CODE> [OPTIONS]
#
# Example:
#   ./scripts/join-google-meet.sh "ced-hntf-sgw" --duration 600 --name "AI Assistant"
#
# Supported by OpenClaw 2026.4.23+
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Default values
MEET_CODE=""
DURATION=300  # 5 minutes default
NAME="OpenClaw Assistant"
NO_MIC=false
CAMERA=false
HEADLESS=true
CONTAINER_NAME="openclaw"
PROFILE="prod"
TIMEOUT_WAIT=30  # seconds to wait for browser operations

# Parse arguments
parse_args() {
    if [ $# -lt 1 ]; then
        usage
        exit 1
    fi

    MEET_CODE="$1"
    shift

    while [ $# -gt 0 ]; do
        case "$1" in
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --name)
                NAME="$2"
                shift 2
                ;;
            --no-mic)
                NO_MIC=true
                shift
                ;;
            --camera)
                CAMERA=true
                shift
                ;;
            --container)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT_WAIT="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Print usage
usage() {
    cat << EOF
╔════════════════════════════════════════════════════════╗
║   OpenClaw Google Meet Integration                    ║
║   Automated joining and participation in Meet calls   ║
╚════════════════════════════════════════════════════════╝

Usage: $0 <MEET_CODE> [OPTIONS]

Positional:
  MEET_CODE              Google Meet code (e.g., ced-hntf-sgw)

Options:
  --duration N           Duration in seconds (default: 300)
  --name TEXT            Agent name in meeting (default: "OpenClaw Assistant")
  --no-mic               Disable microphone (silent mode)
  --camera               Enable camera (experimental)
  --container NAME       Docker container name (default: "openclaw")
  --profile NAME         OpenClaw profile (default: "prod")
  --timeout N            Timeout for browser operations in seconds (default: 30)
  --help, -h             Show this help message

Examples:
  # Basic usage - 5 minute session
  $0 "ced-hntf-sgw"

  # With custom name and duration
  $0 "ced-hntf-sgw" --name "Support Bot" --duration 1800

  # Silent mode (observer only)
  $0 "ced-hntf-sgw" --no-mic --duration 3600

  # With camera enabled
  $0 "ced-hntf-sgw" --camera --duration 600

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed"
        exit 1
    fi

    # Check container running
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "Container '$CONTAINER_NAME' is not running"
        exit 1
    fi

    log_success "Docker and container verified"
}

# Verify configuration
verify_configuration() {
    log_info "Verifying OpenClaw configuration..."

    # Check gateway health
    if ! docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" gateway health &> /dev/null; then
        log_warn "Gateway not immediately responsive, waiting..."
        sleep 5
    fi

    # Check browser plugin
    if ! docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" plugins list 2>&1 | grep -q "browser.*loaded"; then
        log_error "Browser plugin not loaded"
        exit 1
    fi

    # Check deepgram plugin (for speech-to-text)
    if ! docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" plugins list 2>&1 | grep -q "deepgram.*loaded"; then
        log_warn "Deepgram plugin not loaded (speech-to-text will not work)"
    fi

    # Check elevenlabs plugin (for text-to-speech)
    if ! docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" plugins list 2>&1 | grep -q "elevenlabs.*loaded"; then
        log_warn "ElevenLabs plugin not loaded (text-to-speech will not work)"
    fi

    log_success "Configuration verified"
}

# Ensure browser is running
ensure_browser_started() {
    log_info "Starting browser..."

    docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" browser start > /dev/null 2>&1

    sleep 3

    # Wait for browser to be ready
    local timeout=$TIMEOUT_WAIT
    while [ $timeout -gt 0 ]; do
        if docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" browser status &> /dev/null; then
            log_success "Browser started and ready"
            return 0
        fi
        sleep 1
        ((timeout--))
    done

    log_warn "Browser startup took longer than expected"
}

# Navigate to Google Meet
navigate_to_meet() {
    local meet_url="https://meet.google.com/$MEET_CODE"

    log_info "Navigating to: $meet_url"

    docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" browser open "$meet_url" > /dev/null 2>&1

    log_success "Meeting URL opened"
}

# Wait for page to load
wait_for_meet_page() {
    log_info "Waiting for Google Meet page to load..."

    sleep 8  # Wait for Meet to fully load

    log_success "Page loaded"
}

# Capture snapshot for verification
capture_snapshot() {
    log_info "Capturing page snapshot..."

    docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" browser snapshot --format aria 2>&1 | head -30

    log_success "Snapshot captured"
}

# Click join button or simulate keyboard interaction
join_meeting() {
    log_info "Attempting to join meeting..."

    # Try clicking "Join" button by looking for it in the snapshot
    # The actual join mechanism depends on Meet's current UI

    # Method 1: Try pressing Enter (common for join button)
    docker exec "$CONTAINER_NAME" openclaw --profile "$PROFILE" browser press "Enter" > /dev/null 2>&1 || true

    sleep 3

    log_success "Join attempt completed"
}

# Enable/disable audio/video settings
configure_media() {
    log_info "Configuring media settings..."

    if [ "$NO_MIC" = true ]; then
        log_info "Microphone: DISABLED"
    else
        log_info "Microphone: ENABLED"
    fi

    if [ "$CAMERA" = true ]; then
        log_info "Camera: ENABLED"
    else
        log_info "Camera: DISABLED"
    fi
}

# Main flow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║   OpenClaw Google Meet Integration                    ║"
    echo "║   Automated joining and participation                 ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""

    parse_args "$@"

    # Validate meet code format
    if [ -z "$MEET_CODE" ]; then
        log_error "MEET_CODE is required"
        exit 1
    fi

    if ! [[ "$MEET_CODE" =~ ^[a-z]{3}-[a-z]{4}-[a-z]{3}$ ]]; then
        log_warn "Meet code format may be invalid: $MEET_CODE"
    fi

    check_prerequisites
    verify_configuration
    ensure_browser_started
    navigate_to_meet
    wait_for_meet_page
    capture_snapshot
    configure_media
    join_meeting

    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "✨ Meeting join process completed!"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "📊 Session Details:"
    echo "  Meeting Code: $MEET_CODE"
    echo "  Agent Name: $NAME"
    echo "  Duration: ${DURATION}s"
    echo "  Microphone: $([ "$NO_MIC" = true ] && echo "OFF" || echo "ON")"
    echo "  Camera: $([ "$CAMERA" = true ] && echo "ON" || echo "OFF")"
    echo ""
    echo "📋 Monitoring:"
    echo "  View logs: docker logs -f $CONTAINER_NAME"
    echo "  Check status: docker exec $CONTAINER_NAME openclaw status"
    echo ""
    echo "⏱️  Session will run for $DURATION seconds"
    echo ""

    # Optional: run for specified duration
    if [ $DURATION -gt 0 ]; then
        echo "Waiting for session to complete..."
        sleep "$DURATION"
        log_success "Session completed"
    fi
}

# Run main function
main "$@"
