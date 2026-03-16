#!/usr/bin/env bash
# Start XLM Trading Dashboard (Django)
set -e
cd "$(dirname "$0")"

PORT=8503

# Kill any existing process on this port
echo "[dashboard] Cleaning up port $PORT..."
lsof -ti :$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Use python3.13 if available (matches installed packages), else python3
PY=$(command -v python3.13 2>/dev/null || command -v python3)
echo "[dashboard] Using $PY"
echo "[dashboard] Running migrations..."
"$PY" manage.py migrate --run-syncdb 2>/dev/null || true
echo "[dashboard] Collecting static files..."
"$PY" manage.py collectstatic --noinput 2>/dev/null || true
echo "[dashboard] Starting on port $PORT..."
exec "$PY" manage.py runserver 0.0.0.0:$PORT
