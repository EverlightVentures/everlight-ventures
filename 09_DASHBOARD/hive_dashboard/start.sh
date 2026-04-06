#!/bin/bash
# Hive Mind Dashboard -- Start Script
# Runs on port 8504

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Load credentials
ENV_FILE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo "[HIVE] Loaded env from $ENV_FILE"
fi

echo "[HIVE] Collecting static files..."
python3 manage.py collectstatic --noinput -q 2>&1

echo "[HIVE] Importing latest sessions..."
python3 manage.py import_sessions 2>&1

BIND_HOST="127.0.0.1"
if [ "${HIVE_BIND_ALL:-0}" = "1" ]; then
    BIND_HOST="0.0.0.0"
fi

echo "[HIVE] Starting dashboard on ${BIND_HOST}:8504..."
python3 manage.py runserver "${BIND_HOST}:8504"
