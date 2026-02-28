# Validation Evidence - 2026-02-28

This document records the post-promotion operational checks executed on
`2026-02-28T01:05:16Z` in WSL (`docker context = default`).

## 1) Runtime stability and health

Command:

```bash
./scripts/healthcheck.sh
```

Result:

```text
Gateway Health
OK (1264ms)
Telegram: ok (@StephenFryBot) (1264ms)
```

Command:

```bash
docker exec openclaw openclaw --profile prod gateway health
```

Result:

```text
Gateway Health
OK (1266ms)
Telegram: ok (@StephenFryBot) (1266ms)
```

Command:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Result:

```text
NAMES           IMAGE                       STATUS
openclaw        openclaw-secure:candidate   Up 25 minutes
openclaw-next   openclaw-secure:candidate   Up About an hour (healthy)
```

## 2) Cron health (WSL host)

Command:

```bash
service cron status
```

Result:

```text
Active: active (running) since Sun 2026-02-22 11:32:11 -03; 5 days ago
```

Command:

```bash
crontab -l
```

Result (OpenClaw block present):

```text
# === OpenClaw container ops ===
*/15 * * * * . /home/leandro/openclaw/config/alerts.env && /home/leandro/openclaw-container/scripts/healthcheck_notify.sh >> /home/leandro/openclaw/logs/healthcheck.log 2>&1
0 3 * * 0 /home/leandro/openclaw-container/scripts/backup.sh >> /home/leandro/openclaw/logs/backup.log 2>&1
30 3 * * * /home/leandro/openclaw-container/scripts/update.sh >> /home/leandro/openclaw/logs/update.log 2>&1
45 3 * * * /home/leandro/openclaw-container/scripts/model_router.py --objective balanced_default --probe --apply >> /home/leandro/openclaw/logs/model-router.log 2>&1
5 8 * * 1-5 /home/leandro/openclaw-container/scripts/model_router.py --objective coding_quality --probe --apply >> /home/leandro/openclaw/logs/model-router.log 2>&1
5 20 * * * /home/leandro/openclaw-container/scripts/model_router.py --objective cost_optimized --probe --apply >> /home/leandro/openclaw/logs/model-router.log 2>&1
15 4 * * * /home/leandro/openclaw-container/scripts/prune_logs.sh >> /home/leandro/openclaw/logs/prune.log 2>&1
# === /OpenClaw container ops ===
```

## 3) Telegram delivery protection ("message is too long")

Observed once at startup delivery recovery:

```text
[telegram] message failed: ... (400: Bad Request: message is too long)
```

Mitigation applied:

```bash
docker exec openclaw openclaw --profile prod cron edit b84edcee-6a7a-4e72-8937-5048ca1af7db --no-deliver
```

Verification:

```bash
docker exec openclaw openclaw --profile prod cron list --json
```

Watchdog job delivery now:

```json
{
  "id": "b84edcee-6a7a-4e72-8937-5048ca1af7db",
  "name": "Autopilot idle watchdog",
  "delivery": {
    "mode": "none",
    "bestEffort": true
  },
  "lastDeliveryStatus": "unknown"
}
```

No new "message is too long" events in recent logs:

```bash
docker logs --since 15m openclaw | rg -i "message is too long|message failed|delivery failed"
```

Result: no matches.

## 4) Hardening evidence

Command:

```bash
docker inspect openclaw --format 'image={{.Config.Image}} restart={{.HostConfig.RestartPolicy.Name}} readonly={{.HostConfig.ReadonlyRootfs}} capdrop={{json .HostConfig.CapDrop}} tmpfs={{json .HostConfig.Tmpfs}} pids={{.HostConfig.PidsLimit}} security={{json .HostConfig.SecurityOpt}}'
```

Result:

```text
image=openclaw-secure:candidate restart=unless-stopped readonly=true capdrop=["ALL"] tmpfs={"/tmp":"rw,noexec,nosuid,size=256m"} pids=512 security=["no-new-privileges"]
```

Command:

```bash
docker exec openclaw python --version
```

Result:

```text
Python 3.11.2
```
