#!/bin/bash
# Hive Mind Dashboard -- Start Script
# Runs on port 8504

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "[HIVE] Importing latest sessions..."
python3 manage.py import_sessions 2>&1

echo "[HIVE] Starting dashboard on port 8504..."
python3 manage.py runserver 0.0.0.0:8504
