#!/bin/bash
# Circuit Breaker v2 -- auto-resetting, never blocks monitoring permanently
# Cron: */10 * * * * flock -xn /tmp/xlm_cb.lock /home/opc/xlm-bot/circuit_breaker.sh
#
# Key changes from v1:
# - Auto-resets after COOLDOWN_MIN (30 min) -- bot resumes trading
# - Tracks trip count: 3 trips in 2 hours = extended lockout (2hr), still auto-resets
# - Clears stale state after VM restart (uptime < 10 min)
# - Never requires manual intervention (but sends escalating alerts)

BOT_DIR="/home/opc/xlm-bot"
LOGS="$BOT_DIR/logs"
DATA="$BOT_DIR/data"
STATE="$DATA/state.json"
CB_STATE="$DATA/.circuit_breaker"
CB_HISTORY="$DATA/.cb_trip_history"
# Source secrets from central .env if not already set
_ENV_FILE="${EVERLIGHT_ENV:-/home/opc/xlm-bot/secrets/runtime.env}"
[ -f "$_ENV_FILE" ] || _ENV_FILE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
[ -f "$_ENV_FILE" ] && set -a && . "$_ENV_FILE" && set +a 2>/dev/null

SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Thresholds
ERROR_WINDOW_MIN=30
MAX_INCIDENTS=5
TRACEBACK_THRESHOLD=3
MAX_RESTARTS=10

# Auto-reset timing
COOLDOWN_MIN=30           # Normal cooldown: resume after 30 min
EXTENDED_COOLDOWN_MIN=120 # Extended: 3 trips in 2hr = 2hr cooldown
MAX_TRIPS_FOR_EXTENDED=3  # Trips within EXTENDED window that trigger long cooldown
TRIP_WINDOW_MIN=120       # Window for counting repeated trips

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $1" >> "$LOGS/watchdog.log"; }

slack() {
    curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        -d "{\"text\": \"$1\"}" >/dev/null 2>&1
}

# Clear stale state after fresh boot (uptime < 10 min)
UPTIME_SEC=$(awk '{print int($1)}' /proc/uptime)
if [ "$UPTIME_SEC" -lt 600 ] && [ -f "$CB_STATE" ]; then
    log "CIRCUIT BREAKER: Cleared stale trip state after fresh start (uptime ${UPTIME_SEC}s)"
    rm -f "$CB_STATE"
fi

# Auto-reset check: if breaker is tripped, check if cooldown has elapsed
if [ -f "$CB_STATE" ]; then
    TRIP_TS=$(stat -c %Y "$CB_STATE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    TRIP_AGE_MIN=$(( (NOW - TRIP_TS) / 60 ))

    # Count recent trips to determine cooldown duration
    RECENT_TRIPS=0
    if [ -f "$CB_HISTORY" ]; then
        CUTOFF=$(date -d "$TRIP_WINDOW_MIN minutes ago" +%s 2>/dev/null || echo 0)
        RECENT_TRIPS=$(awk -v cutoff="$CUTOFF" '$1 >= cutoff' "$CB_HISTORY" 2>/dev/null | wc -l)
    fi

    if [ "$RECENT_TRIPS" -ge "$MAX_TRIPS_FOR_EXTENDED" ]; then
        COOLDOWN=$EXTENDED_COOLDOWN_MIN
    else
        COOLDOWN=$COOLDOWN_MIN
    fi

    if [ "$TRIP_AGE_MIN" -ge "$COOLDOWN" ]; then
        REASON=$(cat "$CB_STATE" | cut -d'|' -f2 2>/dev/null || echo "unknown")
        log "CIRCUIT BREAKER: Auto-reset after ${TRIP_AGE_MIN}min cooldown (was: $REASON)"
        slack "[CIRCUIT BREAKER] Auto-reset after ${TRIP_AGE_MIN}min cooldown. Bot resuming. (Was: $REASON)"
        rm -f "$CB_STATE"
        sudo systemctl start xlm-bot 2>/dev/null || true
    else
        REMAINING=$((COOLDOWN - TRIP_AGE_MIN))
        # Log sparingly while waiting (every ~30 min)
        if [ $((TRIP_AGE_MIN % 30)) -lt 10 ]; then
            log "Circuit breaker cooling down: ${REMAINING}min remaining (${RECENT_TRIPS} recent trips)"
        fi
        exit 0
    fi
fi

trip_breaker() {
    local reason="$1"
    log "CIRCUIT BREAKER TRIPPED: $reason"

    # Record trip in history
    echo "$(date +%s)|$reason" >> "$CB_HISTORY"

    # Trim history to last 20 entries
    if [ -f "$CB_HISTORY" ]; then
        tail -20 "$CB_HISTORY" > "${CB_HISTORY}.tmp" && mv "${CB_HISTORY}.tmp" "$CB_HISTORY"
    fi

    # Count recent trips for escalation
    RECENT_TRIPS=0
    if [ -f "$CB_HISTORY" ]; then
        CUTOFF=$(date -d "$TRIP_WINDOW_MIN minutes ago" +%s 2>/dev/null || echo 0)
        RECENT_TRIPS=$(awk -v cutoff="$CUTOFF" -F'|' '$1 >= cutoff' "$CB_HISTORY" 2>/dev/null | wc -l)
    fi

    if [ "$RECENT_TRIPS" -ge "$MAX_TRIPS_FOR_EXTENDED" ]; then
        COOLDOWN=$EXTENDED_COOLDOWN_MIN
    else
        COOLDOWN=$COOLDOWN_MIN
    fi

    echo "$(ts)|$reason" > "$CB_STATE"
    sudo systemctl stop xlm-bot
    slack "[CIRCUIT BREAKER] Bot paused: $reason. Auto-resumes in ${COOLDOWN}min. (Trip #${RECENT_TRIPS} in ${TRIP_WINDOW_MIN}min window)"
    exit 0
}

# === Health Checks ===

# 1. Check incidents.jsonl
if [ -f "$LOGS/incidents.jsonl" ]; then
    CUTOFF=$(date -d "$ERROR_WINDOW_MIN minutes ago" '+%Y-%m-%dT%H:%M' 2>/dev/null || date '+%Y-%m-%dT%H:%M')
    INCIDENT_COUNT=$(awk -v cutoff="$CUTOFF" '
        /"timestamp"/ { if ($0 > cutoff) count++ }
        END { print count+0 }
    ' "$LOGS/incidents.jsonl")

    if [ "$INCIDENT_COUNT" -ge "$MAX_INCIDENTS" ]; then
        trip_breaker "$INCIDENT_COUNT incidents in last ${ERROR_WINDOW_MIN}min"
    fi
fi

# 2. Check decisions.jsonl for safe_mode blocks
if [ -f "$LOGS/decisions.jsonl" ]; then
    SAFE_COUNT=$(tail -100 "$LOGS/decisions.jsonl" | grep -c "safe_mode_block" 2>/dev/null | tail -1 || echo 0)
    SAFE_COUNT=${SAFE_COUNT:-0}
    if [ "$SAFE_COUNT" -ge 10 ] 2>/dev/null; then
        trip_breaker "safe_mode triggered $SAFE_COUNT times in recent decisions"
    fi
fi

# 3. Check for Python tracebacks
TB_COUNT=$(sudo journalctl -u xlm-bot --since "${ERROR_WINDOW_MIN} min ago" --no-pager 2>/dev/null | grep -c "Traceback" 2>/dev/null | tail -1 || echo 0)
TB_COUNT=${TB_COUNT:-0}
if [ "$TB_COUNT" -ge "$TRACEBACK_THRESHOLD" ] 2>/dev/null; then
    trip_breaker "$TB_COUNT Python tracebacks in last ${ERROR_WINDOW_MIN}min"
fi

# 4. Check for restart loop
RESTART_COUNT=$(sudo journalctl -u xlm-bot --since "${ERROR_WINDOW_MIN} min ago" --no-pager 2>/dev/null | grep -c "Started xlm-bot\|Bot starting" 2>/dev/null | tail -1 || echo 0)
RESTART_COUNT=${RESTART_COUNT:-0}
if [ "$RESTART_COUNT" -ge "$MAX_RESTARTS" ] 2>/dev/null; then
    trip_breaker "Restart loop: $RESTART_COUNT restarts in ${ERROR_WINDOW_MIN}min"
fi

# All clear
