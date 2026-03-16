#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/tmp/crypto_bot_venv/bin/python"
APP="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/dashboard.py"
PID_FILE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/data/dashboard.pid"
LOG_FILE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/logs/dashboard.log"

if [ ! -x "$VENV_PY" ]; then
  echo "Venv not found at $VENV_PY"
  echo "Create it with: python3 -m venv /tmp/crypto_bot_venv"
  exit 1
fi

# Ensure single instance for this app only.
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && ps -p "$PID" >/dev/null 2>&1; then
    kill -TERM "$PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE" 2>/dev/null || true
fi

nohup "$VENV_PY" -m streamlit run "$APP" --server.port 8501 --server.headless true --server.address 0.0.0.0 \
  >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Dashboard started (PID: $(cat "$PID_FILE")) on http://localhost:8501"
