#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/master_dashboard"
VENV_DIR="${VENV_DIR:-/tmp/master_dashboard_venv}"
PY="${PYTHON:-python3}"
PORT="${PORT:-8765}"

cd "$APP_DIR"

pkill -f "uvicorn.*app:app" 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true

sleep 0.5

if [ ! -d "$VENV_DIR" ]; then
  "$PY" -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  pip install -q -r requirements.txt
else
  source "$VENV_DIR/bin/activate"
  # Only reinstall if requirements changed
  if [ requirements.txt -nt "$VENV_DIR/.installed" ] 2>/dev/null; then
    pip install -q -r requirements.txt
  fi
fi
touch "$VENV_DIR/.installed"

exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
