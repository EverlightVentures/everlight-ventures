#!/bin/bash
# Memory Guard + CPU Keepalive for Oracle Cloud
# Cron: 1-56/5 * * * * flock -xn /tmp/xlm_memguard.lock /home/opc/xlm-bot/memory_guard.sh
#
# 1. Monitors RAM -- if >97% used, kills lowest-priority process
# 2. Clears page cache when memory is tight
# 3. Maintains minimum CPU usage to prevent Oracle free-tier reclamation
#    (Oracle reclaims if CPU < 10% for 7 days)
# 4. Coordinates with watchdog.sh via lockfiles to prevent restart fights

BOT_DIR="/home/opc/xlm-bot"
LOG="$BOT_DIR/logs/watchdog.log"
# Source secrets from central .env if not already set
_ENV_FILE="${EVERLIGHT_ENV:-/home/opc/xlm-bot/secrets/runtime.env}"
[ -f "$_ENV_FILE" ] || _ENV_FILE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
[ -f "$_ENV_FILE" ] && set -a && . "$_ENV_FILE" && set +a 2>/dev/null

SLACK_WEBHOOK="${SLACK_WEBHOOK_ALERTS:-}"

MEM_CRITICAL=97   # % - start killing non-essential processes (503MB max)
MEM_WARNING=93    # % - clear caches
SWAP_CRITICAL=85  # % - swap too full

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] MEM_GUARD: $1" >> "$LOG"; }

slack() {
    curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        -d "{\"text\": \"$1\"}" >/dev/null 2>&1
}

# Get memory percentage
MEM_PCT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')
SWAP_PCT=$(free | awk '/Swap:/ {if ($2>0) printf "%.0f", $3/$2*100; else print 0}')
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')

# 1. Critical memory -- kill non-essential processes
if [ "$MEM_PCT" -ge "$MEM_CRITICAL" ]; then
    log "CRITICAL: Memory ${MEM_PCT}% (${MEM_AVAIL}MB available)"

    # Kill dashboard first (least important, can restart)
    DASH_PID=$(pgrep -f "streamlit" | head -1)
    if [ -n "$DASH_PID" ]; then
        log "Killing streamlit dashboard (PID $DASH_PID) to free memory"
        kill "$DASH_PID" 2>/dev/null
        sudo systemctl stop xlm-dashboard
        # Write lockfile so watchdog.sh does NOT restart dashboard
        date +%s > /tmp/xlm_memkill_dashboard
        slack "[MEM_GUARD] Killed dashboard to free memory (${MEM_PCT}% used, ${MEM_AVAIL}MB free). Bot still running."
    fi

    # Clear caches
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1

    # If still critical after killing dashboard, kill WS feed
    sleep 2
    MEM_PCT2=$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')
    if [ "$MEM_PCT2" -ge "$MEM_CRITICAL" ]; then
        WS_PID=$(pgrep -f "live_ws" | head -1)
        if [ -n "$WS_PID" ]; then
            log "Killing WS feed (PID $WS_PID) -- memory still critical"
            kill "$WS_PID" 2>/dev/null
            sudo systemctl stop xlm-ws
            date +%s > /tmp/xlm_memkill_ws
            slack "[MEM_GUARD] Also killed WS feed. Memory still ${MEM_PCT2}%. Bot running standalone."
        fi
    fi

# 2. Warning level -- just clear caches
elif [ "$MEM_PCT" -ge "$MEM_WARNING" ]; then
    log "WARNING: Memory ${MEM_PCT}% -- clearing caches"
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1
fi

# 3. Swap check
if [ "$SWAP_PCT" -ge "$SWAP_CRITICAL" ]; then
    log "WARNING: Swap ${SWAP_PCT}% used"
fi

# 3b. Disk guard -- trim logs when disk is high
DISK_PCT=$(df /home 2>/dev/null | tail -1 | awk '{gsub(/%/,""); print $5}')
DISK_PCT=${DISK_PCT:-0}
if [ "$DISK_PCT" -ge 88 ]; then
    log "DISK CRITICAL: ${DISK_PCT}% -- running emergency log trim"
    bash /home/opc/xlm-bot/log_rotate.sh 2>/dev/null &
    slack "[MEM_GUARD] Disk ${DISK_PCT}% critical -- emergency log trim triggered."
elif [ "$DISK_PCT" -ge 82 ]; then
    log "DISK WARNING: ${DISK_PCT}% -- scheduling log trim"
    bash /home/opc/xlm-bot/log_rotate.sh 2>/dev/null &
fi

# 4. CPU keepalive -- prevent Oracle reclamation
# SKIP keepalive when memory is tight (saves kernel buffers)
if [ "$MEM_PCT" -lt "$MEM_WARNING" ]; then
    # Standard keepalive: 2s CPU spike
    timeout 3 openssl speed aes-256-cbc > /dev/null 2>&1 &
else
    # Lightweight keepalive when memory is tight (no extra allocation)
    for i in $(seq 1 500000); do :; done &
fi

# 5. Protect bot from OOM killer (belt + suspenders with systemd)
BOT_PID=$(pgrep -f "python.*main.py" | head -1)
if [ -n "$BOT_PID" ]; then
    echo -900 | sudo tee /proc/$BOT_PID/oom_score_adj > /dev/null 2>&1
fi

# 6. Auto-restart services if memory is OK and they're stopped
# Respects lockfiles from step 1 (prevents restart fights with watchdog)
if [ "$MEM_PCT" -lt "$MEM_WARNING" ]; then
    DASH_STATUS=$(systemctl is-active xlm-dashboard 2>/dev/null)
    if [ "$DASH_STATUS" != "active" ]; then
        # Only restart if we did not kill it recently (10 min cooldown)
        MEMKILL_TS=$(cat /tmp/xlm_memkill_dashboard 2>/dev/null || echo 0)
        AGE=$(( $(date +%s) - ${MEMKILL_TS:-0} ))
        if [ "$AGE" -ge 600 ]; then
            log "Memory OK (${MEM_PCT}%) -- restarting dashboard"
            sudo systemctl start xlm-dashboard
            rm -f /tmp/xlm_memkill_dashboard
        fi
    fi

    WS_STATUS=$(systemctl is-active xlm-ws 2>/dev/null)
    if [ "$WS_STATUS" != "active" ]; then
        MEMKILL_TS=$(cat /tmp/xlm_memkill_ws 2>/dev/null || echo 0)
        AGE=$(( $(date +%s) - ${MEMKILL_TS:-0} ))
        if [ "$AGE" -ge 600 ]; then
            log "Memory OK (${MEM_PCT}%) -- restarting WS feed"
            sudo systemctl start xlm-ws
            rm -f /tmp/xlm_memkill_ws
        fi
    fi
fi
