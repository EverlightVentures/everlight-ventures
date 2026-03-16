#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/master_dashboard"
VENV_DIR="${VENV_DIR:-/tmp/master_dashboard_venv}"

cd "$APP_DIR"
source "$VENV_DIR/bin/activate"

# Install analytics deps only when needed
pip install -q -r requirements-analytics.txt 2>/dev/null

streamlit run analytics_streamlit.py --server.port 8777 --server.address 0.0.0.0
