#!/usr/bin/env bash
# War Room Watcher - start/stop/status
# Usage:
#   wrw start     # start daemon
#   wrw stop      # stop daemon
#   wrw status    # check if running
#   wrw once      # single scan
#   wrw log       # tail the log
#   wrw reset     # reset state (re-scan all)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WATCHER="$SCRIPT_DIR/war_room_watcher.py"
PID_FILE="/tmp/.war_room_watcher.pid"
LOG_FILE="/mnt/sdcard/AA_MY_DRIVE/_logs/war_room_watcher.log"

case "${1:-start}" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "[WRW] Already running (PID $(cat "$PID_FILE"))"
            exit 0
        fi
        echo "[WRW] Starting war room watcher..."
        nohup python3 -u "$WATCHER" -v >> "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "[WRW] Started (PID $!)"
        echo "[WRW] Log: $LOG_FILE"
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "[WRW] Stopped (PID $PID)"
            else
                echo "[WRW] Process $PID not running"
            fi
            rm -f "$PID_FILE"
        else
            echo "[WRW] No PID file found"
        fi
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "[WRW] Running (PID $(cat "$PID_FILE"))"
        else
            echo "[WRW] Not running"
        fi
        ;;
    once)
        python3 "$WATCHER" --once -v
        ;;
    log)
        tail -f "$LOG_FILE"
        ;;
    reset)
        python3 "$WATCHER" --reset --once -v --no-notify --no-execute
        ;;
    *)
        echo "Usage: wrw {start|stop|status|once|log|reset}"
        exit 1
        ;;
esac
