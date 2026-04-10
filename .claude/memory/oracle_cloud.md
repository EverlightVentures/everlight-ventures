# Oracle Cloud Deployment -- XLM Bot Production

**Status as of Feb 27, 2026: BOT IS DEPLOYED ON ORACLE CLOUD. LOCAL PHONE PROCESS IS INTENTIONALLY INACTIVE.**

## Runtime Ownership
- `runtime_owner = oracle_cloud`
- `local_process = inactive_expected` (NOT a bug, NOT a crash)
- Oracle Cloud is the ONLY production environment
- Phone/Termux is dev/backup only -- DO NOT restart local xpb/xdr/xws

## Infrastructure
- **VM**: Ampere A1 ARM64, free tier (4 OCPU / 24GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Runtime**: Docker + docker-compose, `restart: always`
- **Bot dir on VM**: `~/xlm_bot/`
- **Public IP**: 129.159.38.250
- **Dashboard**: `http://129.159.38.250:8502`
- **Heartbeat**: `~/xlm_bot/data/.heartbeat` -- should be <60s old

## Daily Health Check (required)
```bash
# SSH into Oracle VM
ssh ubuntu@129.159.38.250

# Check Docker container status
docker ps  # should show "healthy"

# Check recent logs
docker compose -f ~/xlm_bot/docker-compose.yml logs --tail=50 xlm-bot

# Check heartbeat age
docker compose exec xlm-bot python3 -c "
import time; from pathlib import Path
hb = Path('data/.heartbeat')
age = time.time() - float(hb.read_text())
print(f'Heartbeat age: {age:.0f}s - {\"OK\" if age < 60 else \"STALE\"}')"
```

## Source of Truth Files (on Oracle VM)
- `~/xlm_bot/data/state.json` -- live position state
- `~/xlm_bot/logs/trades.csv` -- trade history
- `~/xlm_bot/logs/xpb_console.log` -- bot cycles
- `~/xlm_bot/logs/ai_debug.log` -- Claude Opus decisions
- `~/xlm_bot/data/ai_insight.json` -- latest AI directive

## Escalation: Bot Unreachable
1. SSH to Oracle VM -- if unreachable, check Oracle Cloud Console
2. `docker compose logs xlm-bot` -- look for crash reason
3. `docker compose up -d` -- restart if down
4. Check `secrets/config.json` and `.env` are intact
5. If position open on Coinbase: manage manually via Coinbase app

## Update Bot Code
```bash
rsync -avz /mnt/sdcard/AA_MY_DRIVE/xlm_bot/ ubuntu@ORACLE_IP:~/xlm_bot/
docker compose build && docker compose up -d
```

## AI Executive Mode Details (overflow from MEMORY.md)
- **Cache TTL**: 300s (5 min). Opus takes ~10-25s per call + 30s cycle.
- **Timing**: Opus responds in ~10-25s. Result available by next 30s cycle.
- **Debug log**: `logs/ai_debug.log` -- tracks FIRE/CLI/DONE events with timing
- **run_live.sh**: Bot runner script that unsets CLAUDECODE before starting loop

## Dashboard Theme Classes
- `.card`, `.intel-card`, `.intel-title`, `.intel-event`, `.feed-mini`
- `.pill`, `.pill.ok`, `.pill.danger`
- `.label`, `.metric`, `.ok`, `.danger`, `.green`, `.red`, `.muted`, `.kpi`
- `.side-kv`, `.side-v`, `.side-title`, `.side-divider`

## Situational Awareness (include in every daily report)
Bot location: **Oracle Cloud** | Local: **inactive (expected)** | Check: SSH + docker ps
