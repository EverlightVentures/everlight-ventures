#!/bin/bash
set -euo pipefail
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$BOT_DIR/venv"
PORT="${XLM_DASH_PORT:-8502}"
CHAT_PORT="${XLM_CHAT_PORT:-8504}"
CHAT_HOST="${XLM_CHAT_HOST:-0.0.0.0}"

cd "$BOT_DIR"
source "$VENV/bin/activate"
if [ -f "$BOT_DIR/secrets/runtime.env" ]; then
    set -a
    # Load dashboard/chat provider keys for the child processes we spawn here.
    source "$BOT_DIR/secrets/runtime.env"
    set +a
fi

echo "[$(date)] Dashboard starting on port $PORT"

start_chat_api() {
    "$VENV/bin/python3" -c "
from claude_chat_api import start_chat_server
start_chat_server(port=${CHAT_PORT}, host='${CHAT_HOST}')
import time
while True:
    time.sleep(3600)
" &
    CHAT_PID=$!
}

stop_chat_api() {
    if [ -n \"${CHAT_PID:-}\" ]; then
        kill \"$CHAT_PID\" 2>/dev/null || true
    fi
}

start_chat_api
trap stop_chat_api EXIT

while true; do
    XLM_DASH_EXCHANGE_READ=1 PYTHONFAULTHANDLER=1 \
        "$VENV/bin/streamlit" run dashboard.py \
        --server.port "$PORT" \
        --server.address 0.0.0.0 \
        --server.headless true \
        --server.fileWatcherType poll
    sleep 2
done
