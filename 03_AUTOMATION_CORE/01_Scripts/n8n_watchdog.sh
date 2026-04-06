#!/bin/bash
# n8n Watchdog -- keeps n8n alive 24/7
# Run via cron every 2 minutes:
# */2 * * * * bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/n8n_watchdog.sh

LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/n8n_watchdog.log"
N8N_LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/n8n.log"
N8N_START="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/n8n_start.sh"
SLACK_WEBHOOK="https://hooks.slack.com/services/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"
PORT=5678
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S PT')

mkdir -p "$(dirname "$LOG")"

log() {
    echo "[$TIMESTAMP] $1" >> "$LOG"
    echo "[$TIMESTAMP] $1"
}

slack_alert() {
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"$1\"}" > /dev/null 2>&1
    fi
}

# Check if n8n is responding
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/healthz" 2>/dev/null | grep -q "200"; then
    # n8n is healthy
    exit 0
fi

# n8n is not responding -- check if process exists
N8N_PID=$(pgrep -f "n8n start" | head -1)

if [ -n "$N8N_PID" ]; then
    log "n8n process $N8N_PID exists but not responding on port $PORT"
    # Give it 10 more seconds
    sleep 10
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/healthz" 2>/dev/null | grep -q "200"; then
        log "n8n recovered after 10s wait"
        exit 0
    fi
    log "n8n still unresponsive -- killing and restarting"
    kill "$N8N_PID" 2>/dev/null
    sleep 2
    kill -9 "$N8N_PID" 2>/dev/null
    sleep 1
else
    log "n8n is not running"
fi

# Capture last errors before restart
LAST_ERRORS=""
if [ -f "$N8N_LOG" ]; then
    LAST_ERRORS=$(tail -30 "$N8N_LOG" | grep -i "error\|fail\|crash\|exception" | tail -5)
fi

# Start n8n
log "Starting n8n via $N8N_START"
bash "$N8N_START" &
sleep 5

# Verify it came up
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/healthz" 2>/dev/null | grep -q "200"; then
    log "n8n restarted successfully"
    slack_alert "[n8n Watchdog] n8n was down and has been restarted. Status: HEALTHY"
else
    # Check if process at least started
    NEW_PID=$(pgrep -f "n8n start" | head -1)
    if [ -n "$NEW_PID" ]; then
        log "n8n process started (PID $NEW_PID) but not yet responding -- may still be booting"
        slack_alert "[n8n Watchdog] n8n restarted (PID $NEW_PID), still booting. Will check again in 2 min."
    else
        log "CRITICAL: n8n failed to start"
        ERROR_MSG="[n8n Watchdog] CRITICAL: n8n failed to start."
        if [ -n "$LAST_ERRORS" ]; then
            ERROR_MSG="$ERROR_MSG Last errors: $LAST_ERRORS"
        fi
        slack_alert "$ERROR_MSG"
    fi
fi
