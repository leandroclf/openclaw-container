# OpenClaw + Google Meet Integration
## Complete Bootstrap Guide - v1.0.0

**Release Date**: 2026-04-26
**OpenClaw Version**: 2026.4.23+
**Status**: ✅ Production Ready

---

## 📋 What's Included

### Scripts
- ✅ `scripts/bootstrap-google-meet.sh` - Automated complete setup
- ✅ `scripts/join-google-meet.sh` - Join Google Meet meetings
- ✅ `scripts/configure-meet.sh` - Configure API keys

### Documentation
- ✅ `BOOTSTRAP_GOOGLE_MEET.md` - Step-by-step setup guide
- ✅ `GOOGLE_MEET_BOOTSTRAP_v1.0.0.md` - This file
- ✅ `GOOGLE_MEET_INTEGRATION.md` - Technical architecture
- ✅ `GOOGLE_MEET_SETUP.md` - Quick setup reference

### Features
- ✅ Automatic Google Meet joining via browser automation
- ✅ Speech-to-Text (Deepgram STT)
- ✅ Text-to-Speech (ElevenLabs TTS)
- ✅ AI Processing (Gemini 2.5 Flash)
- ✅ Meeting transcripts and recording
- ✅ Voice loops for real-time conversation
- ✅ Multi-meeting support (2-3 simultaneous)

---

## 🚀 Quick Start (Automated)

### Option 1: Interactive Bootstrap (Recommended)

```bash
# Clone repository
git clone git@github.com:leandroclf/openclaw-container.git
cd openclaw-container

# Run bootstrap (prompts for API keys)
./scripts/bootstrap-google-meet.sh
```

**What it does**:
1. Prompts for Deepgram + ElevenLabs keys
2. Creates directories and configuration
3. Builds Docker image (5-10 min)
4. Starts hardened container
5. Configures plugins and API keys
6. Verifies installation
7. Ready to use! 🎉

### Option 2: Skip Docker Build

```bash
./scripts/bootstrap-google-meet.sh --skip-docker
```

Use if Docker image already exists on your machine.

---

## 📖 Manual Setup (Step-by-Step)

If you prefer to set up manually, follow `BOOTSTRAP_GOOGLE_MEET.md`:

```bash
# 1. Clone & prepare directories
git clone git@github.com:leandroclf/openclaw-container.git ~/openclaw-container
mkdir -p ~/openclaw/{data,logs,config,runtime}

# 2. Create environment file with API keys
cat > ~/openclaw/.env << 'EOF'
DEEPGRAM_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
EOF

# 3. Build Docker image
cd ~/openclaw-container
DOCKER_BUILDKIT=0 docker build -t openclaw-secure:latest .

# 4. Start container
docker run -d \
  --name openclaw \
  --env-file ~/openclaw/.env \
  --read-only --cap-drop=ALL \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v openclaw_state:/home/node/.openclaw \
  -p 18789:18789 \
  openclaw-secure:latest \
  --profile prod gateway run --bind loopback --port 18789

# 5. Configure keys in container
# (See BOOTSTRAP_GOOGLE_MEET.md for details)

# 6. Test
./scripts/join-google-meet.sh "meeting-code"
```

---

## 💡 How to Use

### Basic Join
```bash
./scripts/join-google-meet.sh "meeting-code"
```

### With Custom Name
```bash
./scripts/join-google-meet.sh "meeting-code" --name "My Assistant"
```

### Silent Mode (Observer Only)
```bash
./scripts/join-google-meet.sh "meeting-code" --no-mic
```

### Custom Duration (30 minutes)
```bash
./scripts/join-google-meet.sh "meeting-code" --duration 1800
```

### Help
```bash
./scripts/join-google-meet.sh --help
```

---

## 🔧 Configuration

### API Keys

**Deepgram** (Speech-to-Text):
- Free: 50 minutes/month
- URL: https://deepgram.com/
- Setup time: 1 minute

**ElevenLabs** (Text-to-Speech):
- Free: 10,000 characters/month
- URL: https://elevenlabs.io/
- Setup time: 1 minute

### Container Configuration

All configuration is in:
```
~/openclaw/.env              # Environment variables
~/openclaw/data/             # Persistent data
~/.openclaw-prod/            # Runtime configuration (in container)
```

---

## 📊 Features & Capabilities

| Feature | Status | Notes |
|---------|--------|-------|
| **Join Google Meet** | ✅ | Automatic entry |
| **Speech-to-Text** | ✅ | Deepgram (50 min/month) |
| **Text-to-Speech** | ✅ | ElevenLabs (10k chars/month) |
| **AI Processing** | ✅ | Gemini 2.5 Flash |
| **Voice Loops** | ✅ | Real-time conversation |
| **Transcripts** | ✅ | Automatic recording |
| **Multi-Meeting** | ✅ | 2-3 simultaneous |
| **Browser Automation** | ✅ | Chromium headless |

---

## 🔒 Security

✅ **Container Hardening**:
- Read-only filesystem
- Dropped capabilities (CAP_DROP=ALL)
- Non-root user execution
- Temporary filesystem only
- No privilege escalation

✅ **Secrets Management**:
- API keys in `~/.env` (not in git)
- File permissions: 600
- Loaded at container startup

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **API keys don't work** | Regenerate from Deepgram/ElevenLabs dashboards |
| **Container won't start** | Check: `docker logs openclaw` |
| **Browser plugin missing** | Wait 20s, then: `docker restart openclaw` |
| **Gateway unreachable** | Allow 30s startup time |
| **Meet page won't load** | Verify internet, check URL format |

### Debug Commands
```bash
# View logs
docker logs -f openclaw

# Check status
docker exec openclaw openclaw status

# Test browser
docker exec openclaw openclaw --profile prod browser status

# Restart
docker restart openclaw
```

---

## 📁 File Structure

```
~/openclaw-container/
├── scripts/
│   ├── bootstrap-google-meet.sh    ← Start here!
│   ├── join-google-meet.sh         ← Use to join meetings
│   └── configure-meet.sh
├── BOOTSTRAP_GOOGLE_MEET.md        ← Manual setup guide
├── GOOGLE_MEET_BOOTSTRAP_v1.0.0.md ← This file
├── GOOGLE_MEET_INTEGRATION.md      ← Technical details
├── GOOGLE_MEET_SETUP.md            ← Quick reference
├── Dockerfile
├── README.md
└── ...

~/openclaw/
├── .env                 ← API keys (KEEP SECURE!)
├── data/                ← Persistent data
├── logs/                ← Container logs
├── runtime/             ← Runtime state
└── config/              ← Configuration files
```

---

## 💰 Cost Analysis

| Service | Free Tier | Monthly Cost |
|---------|-----------|--------------|
| **Deepgram** | 50 min | $0 |
| **ElevenLabs** | 10k chars | $0 |
| **Google Gemini** | 60 req/min | $0 |
| **Docker (local)** | Unlimited | $0 |
| **Total** | Sufficient for testing | **$0** ✅ |

**Scale-up costs** (if you exceed free tier):
- Deepgram: $0.0043/minute
- ElevenLabs: $0.30/1k characters
- Gemini: $0.075/1M tokens

---

## ✅ Verification Checklist

After bootstrap completes:

- [ ] Container running: `docker ps | grep openclaw`
- [ ] Gateway healthy: `docker exec openclaw openclaw status`
- [ ] Plugins loaded: `docker exec openclaw openclaw plugins list`
- [ ] API keys configured: Check `~/openclaw/.env`
- [ ] Scripts executable: `ls -la scripts/join-google-meet.sh`
- [ ] Test meeting join
- [ ] View logs without errors

---

## 🎯 Next Steps

1. **Run Bootstrap**: `./scripts/bootstrap-google-meet.sh`
2. **Create Test Meeting**: https://meet.google.com/
3. **Join with OpenClaw**: `./scripts/join-google-meet.sh "code"`
4. **Monitor**: `docker logs -f openclaw`
5. **Enjoy!** 🎉

---

## 📚 Documentation Map

| Document | Purpose |
|----------|---------|
| **BOOTSTRAP_GOOGLE_MEET.md** | Step-by-step setup (manual) |
| **GOOGLE_MEET_BOOTSTRAP_v1.0.0.md** | This overview |
| **GOOGLE_MEET_INTEGRATION.md** | Technical architecture |
| **GOOGLE_MEET_SETUP.md** | Quick reference |
| **README.md** | Full project overview |
| **RUNBOOK.md** | Operations guide |

---

## 🤝 Support

### Resources
- **OpenClaw Docs**: https://docs.openclaw.ai/
- **Deepgram API**: https://developers.deepgram.com/
- **ElevenLabs API**: https://elevenlabs.io/docs/

### Debug
1. Check logs: `docker logs openclaw | tail -100`
2. Verify config: `docker exec openclaw openclaw status`
3. Test components: See troubleshooting section
4. Review documentation

---

## 📜 Version History

| Version | Date | Changes |
|---------|------|---------|
| **v1.0.0** | 2026-04-26 | Initial release with Google Meet integration |

---

## 🎊 Summary

You now have:
✅ OpenClaw container running 24/7
✅ Google Meet integration ready
✅ Speech-to-Text enabled
✅ Text-to-Speech enabled
✅ Browser automation working
✅ Production-ready setup

**Time to first meeting**: ~30 minutes
**Cost**: Free (using free API tiers)
**Complexity**: Low (automated bootstrap)

---

**Ready to get started?**

```bash
cd ~/openclaw-container
./scripts/bootstrap-google-meet.sh
```

Let the magic happen! ✨

