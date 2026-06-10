#!/bin/bash
#
# Crypto Bot Watchdog - Keeps the bot running 24/7
#
# This script monitors the bot and restarts it if it crashes.
# Run this in the background: nohup ./watchdog.sh &
#

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot"
PID_FILE="$BOT_DIR/data/bot.pid"
LOG_FILE="$BOT_DIR/logs/watchdog.log"
CHECK_INTERVAL=60  # Check every 60 seconds
MAX_RESTARTS=5     # Max restarts per hour before giving up
RESTART_COOLDOWN=300  # Wait 5 min between restart attempts

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
    return 1  # Not running
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
    ./cb start

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

while true; do
    sleep $CHECK_INTERVAL

    if ! check_bot; then
        log "Bot stopped unexpectedly!"

        # Wait before restart (avoid rapid restart loops)
        log "Waiting ${RESTART_COOLDOWN}s before restart..."
        sleep $RESTART_COOLDOWN

        restart_bot
    fi
done
