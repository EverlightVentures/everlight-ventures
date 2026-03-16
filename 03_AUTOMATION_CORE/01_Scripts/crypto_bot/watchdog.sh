#!/bin/bash
#
# Crypto Bot Watchdog - Keeps the bot running 24/7
#
# This script monitors the bot and restarts it if it crashes.
# Run this in the background: nohup ./watchdog.sh &
#

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot"
PID_FILE="$BOT_DIR/data/bot.pid"
DB_PID_FILE="$BOT_DIR/data/dashboard.pid"
LOG_FILE="$BOT_DIR/logs/watchdog.log"
DB_LOG_FILE="$BOT_DIR/logs/dashboard.log"
VENV_PY="/tmp/crypto_bot_venv/bin/python"
CHECK_INTERVAL=60  # Check every 60 seconds
MAX_RESTARTS=5     # Max restarts per hour before giving up
RESTART_COOLDOWN=300  # Wait 5 min between restart attempts
DASHBOARD_PORT=8501

# Track restarts
RESTART_COUNT=0
LAST_RESTART_HOUR=$(date +%H)

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        fi
    fi
    # Fallback: bot might have been started without pid file. Recover it.
    for CAND in $(pgrep -f "python3 bot.py" 2>/dev/null || true) $(pgrep -f "python3 .*crypto_bot/bot.py" 2>/dev/null || true); do
        if ! ps -p "$CAND" > /dev/null 2>&1; then
            continue
        fi
        for FD in /proc/"$CAND"/fd/*; do
            TGT="$(readlink "$FD" 2>/dev/null || true)"
            if [ "$TGT" = "$BOT_DIR/logs/bot_console.log" ]; then
                echo "$CAND" > "$PID_FILE"
                return 0
            fi
        done
    done
    return 1  # Not running
}

check_dashboard() {
    if [ -f "$DB_PID_FILE" ]; then
        PID=$(cat "$DB_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    PID=$(pgrep -fo "streamlit run .*crypto_bot/dashboard.py" 2>/dev/null || true)
    if [ -n "${PID:-}" ] && ps -p "$PID" > /dev/null 2>&1; then
        echo "$PID" > "$DB_PID_FILE"
        return 0
    fi
    return 1
}

start_dashboard() {
    cd "$BOT_DIR" || return 1
    if [ ! -x "$VENV_PY" ]; then
        log "WARN: venv python not found at $VENV_PY (dashboard start skipped)"
        return 1
    fi
    log "Starting dashboard on :$DASHBOARD_PORT ..."
    nohup "$VENV_PY" -m streamlit run "$BOT_DIR/dashboard.py" \
        --server.port "$DASHBOARD_PORT" --server.headless true --server.address 0.0.0.0 \
        >> "$DB_LOG_FILE" 2>&1 &
    echo $! > "$DB_PID_FILE"
    return 0
}

restart_bot() {
    # Check restart limits
    CURRENT_HOUR=$(date +%H)
    if [ "$CURRENT_HOUR" != "$LAST_RESTART_HOUR" ]; then
        RESTART_COUNT=0
        LAST_RESTART_HOUR=$CURRENT_HOUR
    fi

    if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
        log "ERROR: Max restarts ($MAX_RESTARTS) reached this hour. Giving up."
        log "Manual intervention required. Run 'cb start' to restart."
        return 1
    fi

    RESTART_COUNT=$((RESTART_COUNT + 1))
    log "Attempting restart #$RESTART_COUNT..."

    cd "$BOT_DIR"
    bash "$BOT_DIR/cb" start

    sleep 5

    if check_bot; then
        log "Bot restarted successfully"
        return 0
    else
        log "Restart failed"
        return 1
    fi
}

# Main watchdog loop
log "Watchdog started"
log "Check interval: ${CHECK_INTERVAL}s"
log "Max restarts per hour: $MAX_RESTARTS"

# Initial start if not running
if ! check_bot; then
    log "Bot not running, starting..."
    restart_bot
fi

# Initial dashboard start if not running
if ! check_dashboard; then
    log "Dashboard not running, starting..."
    start_dashboard
fi

while true; do
    sleep $CHECK_INTERVAL

    if ! check_bot; then
        log "Bot stopped unexpectedly!"

        # Wait before restart (avoid rapid restart loops)
        log "Waiting ${RESTART_COOLDOWN}s before restart..."
        sleep $RESTART_COOLDOWN

        restart_bot
    fi

    if ! check_dashboard; then
        log "Dashboard stopped unexpectedly!"
        start_dashboard
    fi
done
