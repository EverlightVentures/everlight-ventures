#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/tmp/crypto_bot_venv/bin/python"
APP="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/dashboard.py"

if [ ! -x "$VENV_PY" ]; then
  echo "Venv not found at $VENV_PY"
  echo "Create it with: python3 -m venv /tmp/crypto_bot_venv"
  exit 1
fi

# Ensure single instance on port 8501 (aggressive)
pkill -9 -f "streamlit run .*crypto_bot/dashboard.py" 2>/dev/null || true
pkill -9 -f "streamlit" 2>/dev/null || true

# Kill anything still listening on 8501
ps -ef | awk '/streamlit/ {print $2}' | xargs -r kill -9 || true
ps -ef | awk '/8501/ {print $2}' | xargs -r kill -9 || true

# Bind policy: 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md
BIND_HOST="${EV_BIND:-127.0.0.1}"
exec "$VENV_PY" -m streamlit run "$APP" --server.port 8501 --server.headless true --server.address "$BIND_HOST"
