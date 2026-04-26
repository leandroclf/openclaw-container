# OpenClaw + Google Meet - Bootstrap Guide

**Version**: 1.0
**OpenClaw Version**: 2026.4.23+
**Date**: 2026-04-26
**Status**: ✅ Production Ready

---

## Overview

This guide provides step-by-step instructions to set up OpenClaw with Google Meet integration on a new machine. After following this bootstrap, you'll be able to automatically join and participate in Google Meet calls.

**What you'll need**:
- Docker 20.10+
- ~2GB RAM
- Internet connection
- 2 free API keys (Deepgram + ElevenLabs)

**Expected setup time**: 20-30 minutes

---

## Step 1: Clone Repository and Prepare Directories

```bash
# Clone the repository
git clone git@github.com:leandroclf/openclaw-container.git ~/openclaw-container
cd ~/openclaw-container

# Create required directories
mkdir -p ~/openclaw/{data,logs,config,runtime}
mkdir -p ~/openclaw/runtime/{gemini,config,cache,pki}
mkdir -p ~/clawd

# Set permissions
chmod 700 ~/openclaw ~/openclaw/data ~/openclaw/runtime
```

---

## Step 2: Create Environment File with API Keys

### 2.1 Obtain API Keys (Free Tier)

**Deepgram (Speech-to-Text)**:
```
1. Visit: https://deepgram.com/
2. Sign up (Google/GitHub)
3. Dashboard → API Keys
4. Create a new key
5. Copy the key
```

**ElevenLabs (Text-to-Speech)**:
```
1. Visit: https://elevenlabs.io/
2. Sign up (free trial)
3. Profile → API Key
4. Copy the key
```

### 2.2 Create .env File

```bash
cat > ~/openclaw/.env << 'EOF'
# Required for Google Meet integration
DEEPGRAM_API_KEY=your_deepgram_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# Optional but recommended
OPENAI_API_KEY=your_openai_key_here
GH_TOKEN=your_github_token_here
GITHUB_TOKEN=your_github_token_here
EOF

chmod 600 ~/openclaw/.env
```

**Replace with actual keys**:
- `your_deepgram_key_here` → your Deepgram API key
- `your_elevenlabs_key_here` → your ElevenLabs API key

---

## Step 3: Build Docker Image

```bash
cd ~/openclaw-container

# Build with legacy builder (required on some systems)
DOCKER_BUILDKIT=0 docker build \
  --build-arg OPENCLAW_VERSION=2026.4.24 \
  -t openclaw-secure:latest \
  .

# Verify build
docker images | grep openclaw-secure
# Expected output: openclaw-secure   latest   <IMAGE_ID>   ~1.2GB
```

**Note**: Build may take 5-10 minutes. ☕

---

## Step 4: Start Hardened Container

```bash
# Stop any existing container
docker rm -f openclaw 2>/dev/null || true

# Run with security hardening
docker run -d \
  --name openclaw \
  --restart unless-stopped \
  --env-file ~/openclaw/.env \
  --read-only \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v openclaw_state:/home/node/.openclaw \
  -p 18789:18789 \
  openclaw-secure:latest \
  --profile prod gateway run --bind loopback --port 18789

# Wait for startup
sleep 20

# Verify running
docker ps | grep openclaw
```

---

## Step 5: Configure API Keys in Container

```bash
docker exec openclaw bash -c '
cat /home/node/.openclaw-prod/openclaw.json | python3 -c "
import json, sys
config = json.load(sys.stdin)
config[\"env\"][\"vars\"][\"DEEPGRAM_API_KEY\"] = \"YOUR_DEEPGRAM_KEY\"
config[\"env\"][\"vars\"][\"ELEVENLABS_API_KEY\"] = \"YOUR_ELEVENLABS_KEY\"
with open(\"/home/node/.openclaw-prod/openclaw.json\", \"w\") as f:
    json.dump(config, f, indent=2)
print(\"✅ Keys configured\")
"
'
```

**Replace**:
- `YOUR_DEEPGRAM_KEY` → your actual Deepgram key
- `YOUR_ELEVENLABS_KEY` → your actual ElevenLabs key

---

## Step 6: Verify Configuration

```bash
# Check gateway health
docker exec openclaw openclaw --profile prod gateway health

# Expected output: Gateway is healthy

# Check loaded plugins
docker exec openclaw openclaw --profile prod plugins list | grep -E "browser|deepgram|elevenlabs|google"

# Expected output:
# ✅ browser plugin loaded
# ✅ deepgram plugin loaded
# ✅ elevenlabs plugin loaded
# ✅ google plugin loaded
```

---

## Step 7: Test Google Meet Integration

### 7.1 Make Script Executable

```bash
chmod +x ~/openclaw-container/scripts/join-google-meet.sh
```

### 7.2 Create Test Meeting

```
1. Visit: https://meet.google.com/
2. Click "Create a meeting" or "Start an instant meeting"
3. Copy the meeting code (e.g., ced-hntf-sgw)
```

### 7.3 Join with OpenClaw

```bash
# Basic usage
~/openclaw-container/scripts/join-google-meet.sh "ced-hntf-sgw"

# With custom options
~/openclaw-container/scripts/join-google-meet.sh "ced-hntf-sgw" \
  --name "My AI Assistant" \
  --duration 600
```

---

## Step 8: Monitor and Troubleshoot

### View Logs
```bash
docker logs -f openclaw
```

### Check Status
```bash
docker exec openclaw openclaw status
```

### Test Browser Automation
```bash
docker exec openclaw openclaw --profile prod browser start
docker exec openclaw openclaw --profile prod browser open "https://google.com"
docker exec openclaw openclaw --profile prod browser screenshot
docker exec openclaw openclaw --profile prod browser stop
```

---

## Usage Guide

### Basic Join
```bash
./scripts/join-google-meet.sh "meeting-code"
```

### Silent Mode (Observer Only)
```bash
./scripts/join-google-meet.sh "meeting-code" --no-mic
```

### Custom Duration
```bash
./scripts/join-google-meet.sh "meeting-code" --duration 3600
```

### Custom Name
```bash
./scripts/join-google-meet.sh "meeting-code" --name "My Assistant"
```

### All Options
```bash
./scripts/join-google-meet.sh "meeting-code" \
  --name "Support Bot" \
  --duration 1800 \
  --no-mic
```

---

## File Structure After Bootstrap

```
~/openclaw-container/
├── Dockerfile
├── README.md
├── BOOTSTRAP_GOOGLE_MEET.md      ← This file
├── scripts/
│   ├── join-google-meet.sh       ← Main script for joining Meet
│   ├── configure-meet.sh
│   └── ... (other scripts)
├── .env.example
└── ...

~/openclaw/
├── data/                         ← Persistent data
├── logs/                         ← Container logs
├── config/                       ← Configuration files
└── runtime/                      ← Runtime state
```

---

## Features Enabled After Bootstrap

| Feature | Status | Details |
|---------|--------|---------|
| Join Google Meet | ✅ | Automatic meeting entry |
| Speech-to-Text | ✅ | Deepgram (50 min/month free) |
| Text-to-Speech | ✅ | ElevenLabs (10k chars/month free) |
| AI Processing | ✅ | Gemini 2.5 Flash |
| Voice Loops | ✅ | Real-time conversation |
| Meeting Transcripts | ✅ | Automatic recording |
| Browser Automation | ✅ | Chromium headless |
| Multi-Meeting | ✅ | 2-3 simultaneous |

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **API keys not working** | Verify keys in `~/openclaw/.env` and container config |
| **Container won't start** | Check Docker: `docker ps -a`, view logs: `docker logs openclaw` |
| **Browser plugin missing** | Restart: `docker restart openclaw` |
| **Gateway unreachable** | Wait 20-30s after startup, then retry |
| **Meet page won't load** | Check internet, verify URL format (ced-hntf-sgw) |

---

## Production Checklist

Before using in production:

- [ ] Clone repository
- [ ] Create directories
- [ ] Obtain and configure API keys
- [ ] Build Docker image
- [ ] Start container
- [ ] Verify all plugins loaded
- [ ] Test with sample meeting
- [ ] Review logs for errors
- [ ] Set up monitoring/alerting
- [ ] Document custom configuration

---

## Security Notes

✅ **Hardened Container**:
- Read-only filesystem
- Dropped capabilities
- Non-root user
- Temporary filesystem
- No privileged escalation

✅ **Secrets Management**:
- API keys in `~/openclaw/.env` (not in git)
- Permissions: `chmod 600` on `.env`
- Container reads from mounted volume

---

## Next Steps

1. **Basic Usage**: Run `./scripts/join-google-meet.sh --help`
2. **Custom Configuration**: Edit `/home/node/.openclaw-prod/openclaw.json`
3. **Automation**: Use cron for scheduled meetings
4. **Monitoring**: Set up health checks and alerts
5. **Scaling**: Duplicate setup for multiple machines

---

## References

- **OpenClaw Docs**: https://docs.openclaw.ai/
- **Deepgram API**: https://developers.deepgram.com/
- **ElevenLabs API**: https://elevenlabs.io/docs/
- **Google Meet API**: https://developers.google.com/meet/api/
- **RUNBOOK.md**: Full operational guide
- **README.md**: Overview and features

---

## Support

If you encounter issues:

1. Check logs: `docker logs openclaw | tail -100`
2. Verify config: `docker exec openclaw openclaw status`
3. Test components: `./scripts/test-components.sh`
4. Review docs: `RUNBOOK.md`, `README.md`

---

**Bootstrap Complete!** 🎉

You can now use OpenClaw to join Google Meet automatically.

```bash
./scripts/join-google-meet.sh "your-meeting-code"
```

