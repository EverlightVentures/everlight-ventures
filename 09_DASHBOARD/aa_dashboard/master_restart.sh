#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/aa_dashboard"
VENV_DIR="${VENV_DIR:-/tmp/aa_dashboard_venv}"
PY="${PYTHON:-python3}"
PORT="${PORT:-8765}"

cd "$APP_DIR"

pkill -f "uvicorn.*app:app" 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true

sleep 0.5

if [ ! -d "$VENV_DIR" ]; then
  "$PY" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install -r requirements.txt

exec uvicorn app:app --host 0.0.0.0 --port "$PORT" --reload
