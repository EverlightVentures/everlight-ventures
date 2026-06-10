#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/mnt/sdcard/Mountain Gardens Nursery POS"
PY="/home/richgee/mgpos-venv/bin/python"

cd "$APP_DIR"
exec "$PY" -X dev -W default -u MGN_APP.py
