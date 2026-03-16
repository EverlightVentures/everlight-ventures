#!/bin/bash
# ============================================================
#  CODE-SERVER STARTUP SCRIPT
#  Optimized for PRoot/Termux on Samsung Galaxy Z Fold + DeX
# ============================================================

# Configuration
PORT=8080
LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs"
LOG_FILE="$LOG_DIR/code-server_$(date +%Y-%m-%d_%H%M).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Kill any existing code-server
pkill -f "code-server" 2>/dev/null
sleep 1

# Fix for PRoot network interface errors
export UV_THREADPOOL_SIZE=4
export NODE_OPTIONS="--max-old-space-size=512"

# Disable problematic features in PRoot
export VSCODE_SKIP_PRELAUNCH=1

echo "Starting code-server..."
echo "  Port: $PORT"
echo "  Log: $LOG_FILE"
echo "  Password: everlight"
echo ""
echo "Access via: http://localhost:$PORT"
echo "Or in DeX: http://127.0.0.1:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo "=============================================="

# Start code-server with stability flags
code-server \
    --bind-addr 0.0.0.0:$PORT \
    --auth password \
    --disable-telemetry \
    --disable-update-check \
    --user-data-dir /root/.local/share/code-server \
    2>&1 | tee "$LOG_FILE"
