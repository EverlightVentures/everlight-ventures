#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/master_dashboard"
VENV_DIR="${VENV_DIR:-/tmp/master_dashboard_venv}"
PY="${PYTHON:-python3}"

cd "$APP_DIR"

if [ ! -d "$VENV_DIR" ]; then
  "$PY" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install -r requirements.txt

exec python app.py
