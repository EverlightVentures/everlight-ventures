# XLM Bot -- Cloud Deployment

## Production: Oracle Cloud
- **IP:** 163.192.19.196
- **User:** opc
- **SSH:** `ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196`
- **OS:** Oracle Linux 9.7 (x86_64), 1 OCPU, ~950MB RAM
- **Python:** 3.9 (system), venv at ~/xlm-bot/venv/
- **Bot dir:** /home/opc/xlm-bot/
- **Dashboard:** http://163.192.19.196:8502 (port 8502)

## Services (systemd)
| Service | Command | Description |
|---------|---------|-------------|
| xlm-bot | `sudo systemctl status xlm-bot` | Main trading loop (30s idle, 5s in trade) |
| xlm-dashboard | `sudo systemctl status xlm-dashboard` | Streamlit dashboard on :8502 |
| xlm-ws | `sudo systemctl status xlm-ws` | WebSocket price feed |

## Common Commands
```bash
# SSH in
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196

# Service management
sudo systemctl restart xlm-bot
sudo systemctl stop xlm-bot
sudo systemctl status xlm-bot xlm-dashboard xlm-ws

# Live logs
sudo journalctl -u xlm-bot -f
sudo journalctl -u xlm-dashboard -f

# Check state
cat ~/xlm-bot/data/state.json | python3 -m json.tool
cat ~/xlm-bot/data/metrics.json | python3 -m json.tool

# Quick health
python3 ~/xlm-bot/export_metrics.py
```

## Re-deploy After Code Changes
```bash
# From phone/laptop (uploads code, installs deps, restarts services)
bash /mnt/sdcard/AA_MY_DRIVE/xlm_bot/deploy-native.sh 163.192.19.196 ~/.ssh/oracle_key.pem
```

## Local Environment
- **Path:** /mnt/sdcard/AA_MY_DRIVE/xlm_bot/
- **Status:** Development only, NOT running live
- **Oracle is production** -- all live trading happens there

## Monitoring
- **Metrics cron:** export_metrics.py runs every minute on Oracle
- **Health monitor:** `bash 03_AUTOMATION_CORE/01_Scripts/cloud_monitor.sh --once`
- **Synced data:** _logs/sync/xlm_bot_oracle/ (state, metrics, trades)
- **Slack alerts:** Automatic if bot goes down (heartbeat stale >180s)

## Config Changes on Oracle
Edit config directly on the server:
```bash
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196
nano ~/xlm-bot/secrets/config.yaml
sudo systemctl restart xlm-bot
```

## Key Files on Oracle
```
~/xlm-bot/
  main.py              # Bot entry point (one cycle per run)
  export_metrics.py    # Metrics exporter (cron)
  run-bot.sh           # Bot loop runner
  run-dashboard.sh     # Dashboard runner
  run-ws.sh            # WS feed runner
  secrets/config.json  # Coinbase API credentials
  secrets/config.yaml  # Bot configuration
  data/state.json      # Current bot state
  data/metrics.json    # Exported metrics
  logs/trades.csv      # Trade history
  .heartbeat           # Updated each cycle
```
