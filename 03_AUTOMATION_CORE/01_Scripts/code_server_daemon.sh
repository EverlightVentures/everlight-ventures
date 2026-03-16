#!/bin/bash
# ============================================================
#  CODE-SERVER DAEMON (Background with Auto-Restart)
# ============================================================

PORT=8080
LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs"
PID_FILE="/tmp/code-server.pid"
RESTART_DELAY=5

# Fix for PRoot network interface errors
export UV_THREADPOOL_SIZE=4
export NODE_OPTIONS="--max-old-space-size=512"
export VSCODE_SKIP_PRELAUNCH=1

start_server() {
    LOG_FILE="$LOG_DIR/code-server_$(date +%Y-%m-%d_%H%M).log"
    mkdir -p "$LOG_DIR"

    code-server \
        --bind-addr 0.0.0.0:$PORT \
        --auth password \
        --disable-telemetry \
        --disable-update-check \
        --user-data-dir /root/.local/share/code-server \
        /mnt/sdcard/AA_MY_DRIVE \
        >> "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    echo "code-server started (PID: $(cat $PID_FILE))"
    echo "Log: $LOG_FILE"
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null
        rm "$PID_FILE"
        echo "code-server stopped"
    fi
    pkill -f "code-server" 2>/dev/null
}

status_server() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "code-server is running (PID: $(cat $PID_FILE))"
        echo "URL: http://localhost:$PORT"
    else
        echo "code-server is not running"
    fi
}

case "$1" in
    start)
        stop_server 2>/dev/null
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        sleep 2
        start_server
        ;;
    status)
        status_server
        ;;
    watch)
        # Auto-restart loop (run in background with nohup)
        echo "Starting code-server in watch mode (auto-restart on crash)..."
        while true; do
            if ! pgrep -f "code-server" > /dev/null; then
                echo "[$(date)] code-server crashed, restarting..."
                start_server
            fi
            sleep $RESTART_DELAY
        done
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|watch}"
        exit 1
        ;;
esac
