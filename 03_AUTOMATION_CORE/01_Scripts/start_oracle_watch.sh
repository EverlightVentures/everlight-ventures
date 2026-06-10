#!/usr/bin/env bash
# start_oracle_watch.sh -- launches oracle_reachability_watch.py as a
# managed background process. Idempotent: kills any existing instance
# before starting a new one. Designed to be called from:
#   - ~/.termux/boot/start_oracle_watch.sh (auto-start on phone boot)
#   - manual invocation: bash start_oracle_watch.sh
#   - cron once-a-minute keepalive: */1 * * * * .../start_oracle_watch.sh keepalive
#
# Author: Henrik Strand (Iron Stack S1)

set -euo pipefail

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
WATCH_PY="$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/oracle_reachability_watch.py"
PID_FILE="$WORKSPACE/_logs/.oracle_watch.pid"
LOG_FILE="$WORKSPACE/_logs/oracle_reachability_watch.log"

mode="${1:-start}"

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

start_watch() {
    if is_running; then
        echo "oracle_reachability_watch already running (PID $(cat "$PID_FILE"))"
        return 0
    fi
    nohup python3 "$WATCH_PY" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "oracle_reachability_watch started (PID $(cat "$PID_FILE"))"
}

stop_watch() {
    if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        kill -TERM "$pid" 2>/dev/null || true
        rm -f "$PID_FILE"
        echo "oracle_reachability_watch stopped"
    fi
}

case "$mode" in
    start) start_watch ;;
    stop) stop_watch ;;
    restart) stop_watch; sleep 1; start_watch ;;
    status)
        if is_running; then
            echo "RUNNING (PID $(cat "$PID_FILE"))"
            exit 0
        else
            echo "NOT RUNNING"
            exit 1
        fi
        ;;
    keepalive)
        # Cron-friendly: only start if not running, no output if running
        if ! is_running; then
            start_watch
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|keepalive}"
        exit 2
        ;;
esac
