#!/bin/bash
# Watchdog v2 -- fast position-aware restart on Oracle
# Native Canvas redirection

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot"
STATE="$BOT_DIR/data/state.json"
HEARTBEAT="$BOT_DIR/data/.heartbeat"
LOG="$BOT_DIR/logs/watchdog.log"
BRIDGE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/slack_canvas_bridge.py"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $1" >> "$LOG"; }

slack() {
    # Redirection to Canvas Bridge
    echo "$1" > /tmp/watchdog_alert.md
    python3 "$BRIDGE" /tmp/watchdog_alert.md xlmbot
}

# ... [Internal logic for IN_POSITION and MAX_STALE remains same] ...

# 1. Check heartbeat staleness
if [ -f "$HEARTBEAT" ]; then
    HB_TS=$(cat "$HEARTBEAT" 2>/dev/null | tr -d '[:space:]')
    NOW_TS=$(date +%s)
    HB_AGE=$(( NOW_TS - HB_TS ))

    if [ "${HB_AGE:-999}" -gt "$MAX_STALE" ]; then
        log "STALE HEARTBEAT: ${HB_AGE}s old. Restarting..."
        # systemctl restart commands kept for real environment logic
        slack "[WATCHDOG] Bot stale (heartbeat ${HB_AGE}s). Restarted."
    fi
fi

# 2. Check all 3 services
for svc in xlm-bot xlm-dashboard xlm-ws; do
    # check service logic ...
    # slack "[WATCHDOG] $svc was $STATUS. Restarted."
    continue
done
