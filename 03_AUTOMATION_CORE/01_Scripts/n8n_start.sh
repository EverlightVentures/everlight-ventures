#!/bin/bash
# n8n Start Script -- loads env and launches n8n
# Used by watchdog and manual starts

BASE="/mnt/sdcard/AA_MY_DRIVE"
ENV_FILE="$BASE/03_AUTOMATION_CORE/03_Credentials/.env"
N8N_LOG="$BASE/_logs/n8n.log"
N8N_DATA="$BASE/06_DEVELOPMENT/everlight_os/n8n/data"

mkdir -p "$(dirname "$N8N_LOG")"
mkdir -p "$N8N_DATA"

# Load environment
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# n8n config
export N8N_PORT=5678
export N8N_HOST=0.0.0.0
export GENERIC_TIMEZONE=America/Los_Angeles
export N8N_USER_FOLDER="$N8N_DATA"
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_HIRING_BANNER_ENABLED=false
export N8N_METRICS=true
export EXECUTIONS_DATA_SAVE_ON_ERROR=all
export EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
export EXECUTIONS_DATA_MAX_AGE=168
export N8N_BASIC_AUTH_ACTIVE=true
export N8N_BASIC_AUTH_USER=admin
export N8N_BASIC_AUTH_PASSWORD=everlight_n8n_2026
export WEBHOOK_URL=http://localhost:5678

echo "[$(date '+%Y-%m-%d %H:%M:%S PT')] Starting n8n on port $N8N_PORT..." >> "$N8N_LOG"

# Start n8n in background, logging to file
nohup n8n start >> "$N8N_LOG" 2>&1 &

echo "[$(date '+%Y-%m-%d %H:%M:%S PT')] n8n launched (PID $!)" >> "$N8N_LOG"
echo "n8n started (PID $!)"
