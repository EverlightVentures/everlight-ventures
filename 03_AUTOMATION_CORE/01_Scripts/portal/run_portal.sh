#!/usr/bin/env bash
# Everlight Portal -- run script
# Usage: ./run_portal.sh [port]
# Default port: 8800 (set PORTAL_PORT env to override)
# Bind: 127.0.0.1 only (network-binding doctrine -- loopback, private)
#
# Background mode: ./run_portal.sh &
# Check running: curl -s http://127.0.0.1:8800/ | head -5
# Stop: kill $(cat portal.pid) or just kill the process

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORTAL_PY="$SCRIPT_DIR/portal_server.py"
PID_FILE="$SCRIPT_DIR/portal.pid"
LOG_FILE="$SCRIPT_DIR/portal.log"

# Port override from arg or env
if [ -n "$1" ]; then
  export PORTAL_PORT="$1"
fi
: "${PORTAL_PORT:=8800}"

# Check Python3
if ! command -v python3 &>/dev/null; then
  echo "[portal] ERROR: python3 not found in PATH"
  exit 1
fi

# Check PyYAML (required; stdlib fallback not implemented for full YAML)
if ! python3 -c "import yaml" 2>/dev/null; then
  echo "[portal] WARNING: PyYAML not found. Attempting to install..."
  pip3 install pyyaml 2>/dev/null || {
    echo "[portal] ERROR: Could not install PyYAML. Run: pip3 install pyyaml"
    exit 1
  }
fi

# Check if already running on this port
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[portal] Already running (PID $OLD_PID) at http://127.0.0.1:${PORTAL_PORT}/"
    exit 0
  else
    rm -f "$PID_FILE"
  fi
fi

echo "[portal] Starting Everlight Portal on http://127.0.0.1:${PORTAL_PORT}/"
echo "[portal] Log: $LOG_FILE"

# Launch in background if called from a terminal interactively; otherwise foreground
if [ -t 1 ]; then
  # Interactive terminal -- give the user the option to run foreground
  echo "[portal] Running FOREGROUND (Ctrl+C to stop). To background: $0 &"
  cd "$SCRIPT_DIR"
  exec python3 "$PORTAL_PY"
else
  # Non-interactive (e.g. called from cron, another script)
  cd "$SCRIPT_DIR"
  nohup python3 "$PORTAL_PY" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "[portal] Started in background (PID $(cat "$PID_FILE"))"
  echo "[portal] Verify: curl -s http://127.0.0.1:${PORTAL_PORT}/ | head -3"
fi
