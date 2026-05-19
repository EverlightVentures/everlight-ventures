#!/usr/bin/env bash
# Hive Directory launcher. Runs FastAPI on :8503 and Vite dev on :5174.
set -euo pipefail
cd "$(dirname "$0")"

# Python deps (idempotent)
pip install --quiet -r requirements.txt || true

# Bind policy: 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md
BIND_HOST="${EV_BIND:-127.0.0.1}"
# Backend (background)
uvicorn api:app --host "$BIND_HOST" --port 8503 &
API_PID=$!
trap "kill $API_PID 2>/dev/null || true" EXIT INT TERM

# Frontend dev
if [ ! -d node_modules ]; then
  npm install --silent
fi
npm run dev
