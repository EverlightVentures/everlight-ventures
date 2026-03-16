#!/usr/bin/env bash
# BlinkoLite Watchdog - keeps BlinkoLite alive with auto-restart on crash.
#
# Usage:
#   ./blinko_watchdog.sh         # Run in foreground
#   ./blinko_watchdog.sh &       # Run in background
#   nohup ./blinko_watchdog.sh & # Survive terminal close
#
# Checks every 15 seconds. If BlinkoLite is down, restarts it.
# Logs to _logs/blinko_watchdog.log

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BLINKO_SCRIPT="${SCRIPT_DIR}/blinko_lite.py"
PID_FILE="/tmp/blinko_lite.pid"
WATCHDOG_PID_FILE="/tmp/blinko_watchdog.pid"
LOG_FILE="/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_watchdog.log"
CHECK_INTERVAL=15
MAX_RESTARTS_PER_HOUR=10

# Track restarts
restart_count=0
restart_window_start=$(date +%s)

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

is_running() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    # Also check by port
    if python3 -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://localhost:1111/health', timeout=3)
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
        return 0
    fi
    return 1
}

start_blinko() {
    log "Starting BlinkoLite..."
    nohup python3 "$BLINKO_SCRIPT" >> "$LOG_FILE" 2>&1 &
    sleep 2

    if is_running; then
        pid=$(cat "$PID_FILE" 2>/dev/null)
        log "BlinkoLite started (PID: ${pid})"
        return 0
    else
        log "ERROR: BlinkoLite failed to start"
        return 1
    fi
}

stop_blinko() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ]; then
            log "Stopping BlinkoLite (PID: ${pid})..."
            kill "$pid" 2>/dev/null
            sleep 1
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    # Kill any orphaned processes on port 1111
    pkill -f "blinko_lite.py" 2>/dev/null
}

cleanup() {
    log "Watchdog shutting down..."
    rm -f "$WATCHDOG_PID_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Write watchdog PID
echo $$ > "$WATCHDOG_PID_FILE"
log "Watchdog started (PID: $$, interval: ${CHECK_INTERVAL}s)"

# Initial start
if ! is_running; then
    start_blinko
fi

# Main watchdog loop
while true; do
    sleep "$CHECK_INTERVAL"

    # Reset restart counter every hour
    now=$(date +%s)
    elapsed=$(( now - restart_window_start ))
    if [ "$elapsed" -ge 3600 ]; then
        restart_count=0
        restart_window_start=$now
    fi

    if ! is_running; then
        restart_count=$(( restart_count + 1 ))

        if [ "$restart_count" -gt "$MAX_RESTARTS_PER_HOUR" ]; then
            log "ERROR: Hit max restarts ($MAX_RESTARTS_PER_HOUR/hr). Backing off 5 min..."
            sleep 300
            restart_count=0
            restart_window_start=$(date +%s)
        fi

        log "BlinkoLite is DOWN (restart #${restart_count}). Restarting..."
        stop_blinko
        sleep 1
        start_blinko
    fi
done
