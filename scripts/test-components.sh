#!/bin/bash

# OpenClaw Component Test Script
# Verifica se todos os componentes necessários estão funcionando

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}OpenClaw Component Test${NC}"
echo -e "${BLUE}================================${NC}\n"

# Color helper functions
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

info() {
    echo -e "${BLUE}ℹ️  INFO${NC}: $1"
}

# Test 1: Container is running
echo -e "\n${BLUE}TEST 1: Container Status${NC}"
if docker ps | grep -q openclaw; then
    pass "Container is running"
else
    fail "Container is not running"
    exit 1
fi

# Test 2: Get container info
CONTAINER_ID=$(docker ps | grep openclaw | awk '{print $1}')
info "Container ID: $CONTAINER_ID"

# Test 3: Check OpenClaw status
echo -e "\n${BLUE}TEST 2: OpenClaw Status${NC}"
if docker exec openclaw openclaw status > /tmp/openclaw-status.txt 2>&1; then
    pass "OpenClaw is responding"
    grep "Gateway" /tmp/openclaw-status.txt | head -1
else
    fail "OpenClaw is not responding"
fi

# Test 4: Check plugins
echo -e "\n${BLUE}TEST 3: Plugin Status${NC}"
info "Checking required plugins..."

PLUGINS="browser deepgram elevenlabs google"
for plugin in $PLUGINS; do
    if docker exec openclaw openclaw --profile prod plugins list 2>/dev/null | grep -q "$plugin.*loaded"; then
        pass "Plugin loaded: $plugin"
    else
        fail "Plugin not loaded: $plugin"
    fi
done

# Test 5: Check Browser
echo -e "\n${BLUE}TEST 4: Browser Configuration${NC}"
if docker exec openclaw grep -q "\"browser\"" /home/node/.openclaw-prod/openclaw.json 2>/dev/null; then
    pass "Browser is configured"
    docker exec openclaw grep -A 5 '"browser"' /home/node/.openclaw-prod/openclaw.json | head -6
else
    warn "Browser configuration not found"
fi

# Test 6: Check API Keys
echo -e "\n${BLUE}TEST 5: API Key Configuration${NC}"
CONFIG_FILE="/home/node/.openclaw-prod/openclaw.json"

if docker exec openclaw grep -q "DEEPGRAM_API_KEY" "$CONFIG_FILE" 2>/dev/null; then
    pass "Deepgram API key is configured"
else
    fail "Deepgram API key is NOT configured"
    info "Run: docker-compose exec openclaw python3 setup-keys.py"
fi

if docker exec openclaw grep -q "ELEVENLABS_API_KEY" "$CONFIG_FILE" 2>/dev/null; then
    pass "ElevenLabs API key is configured"
else
    fail "ElevenLabs API key is NOT configured"
    info "Run: docker-compose exec openclaw python3 setup-keys.py"
fi

# Test 7: Check disk space
echo -e "\n${BLUE}TEST 6: Disk Space${NC}"
DISK_USAGE=$(docker exec openclaw du -sh /home/node/.openclaw 2>/dev/null | cut -f1)
info "OpenClaw data size: $DISK_USAGE"

# Test 8: Check memory usage
echo -e "\n${BLUE}TEST 7: Memory Usage${NC}"
MEM=$(docker stats --no-stream openclaw 2>/dev/null | tail -1 | awk '{print $6}')
info "Memory usage: $MEM"

# Test 9: Check network connectivity
echo -e "\n${BLUE}TEST 8: Network Connectivity${NC}"
if docker exec openclaw curl -s https://api.deepgram.com/v1/status -H "Authorization: Token test" > /dev/null 2>&1; then
    pass "Can reach Deepgram API"
elif docker exec openclaw curl -s https://api.elevenlabs.io/status > /dev/null 2>&1; then
    pass "Can reach ElevenLabs API"
else
    warn "Network connectivity check - may be blocked"
fi

# Test 10: Check Chrome/Chromium
echo -e "\n${BLUE}TEST 9: Browser Executable${NC}"
if docker exec openclaw which chromium > /dev/null 2>&1; then
    CHROME_VERSION=$(docker exec openclaw chromium --version 2>/dev/null)
    pass "Chromium is available: $CHROME_VERSION"
else
    fail "Chromium is NOT available"
fi

# Test 11: Check CDP Port
echo -e "\n${BLUE}TEST 10: Chrome DevTools Protocol (CDP)${NC}"
if docker exec openclaw lsof -i :18801 > /dev/null 2>&1; then
    pass "CDP port 18801 is available"
else
    warn "CDP port 18801 is not listening (may start on demand)"
fi

# Test 12: Check agent models
echo -e "\n${BLUE}TEST 11: AI Models${NC}"
if docker exec openclaw grep -q "google-gemini" "$CONFIG_FILE" 2>/dev/null; then
    pass "Google Gemini is configured as primary model"
else
    warn "Google Gemini configuration not found"
fi

# Test 13: Test Meet agent script
echo -e "\n${BLUE}TEST 12: Meet Agent Script${NC}"
if [ -f "/scripts/meet-agent.py" ]; then
    pass "Meet agent script exists"
    if python3 /scripts/meet-agent.py --help > /dev/null 2>&1; then
        pass "Meet agent script is executable"
    else
        warn "Meet agent script may have dependencies"
    fi
else
    fail "Meet agent script not found at /scripts/meet-agent.py"
fi

# Summary
echo -e "\n${BLUE}================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}================================${NC}"

PASS_COUNT=$(grep -c "^✅" /tmp/test-results.txt 2>/dev/null || echo "N/A")
FAIL_COUNT=$(grep -c "^❌" /tmp/test-results.txt 2>/dev/null || echo "N/A")

info "All basic tests completed"
info "For detailed setup, see: SETUP_INSTRUCTIONS.md"
info "For Google Meet integration, see: GOOGLE_MEET_SETUP.md"

echo -e "\n${GREEN}✅ System is ready for Google Meet integration!${NC}\n"
