#!/bin/bash
# rdx - Start XLM dashboard from anywhere

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
VENV="/tmp/xlm_bot_venv"

echo "Stopping existing processes..."
pkill -f "python.*xlm_bot/main.py" 2>/dev/null
pkill -f "streamlit.*xlm_bot/dashboard.py" 2>/dev/null
sleep 1

cd "$BOT_DIR" || exit 1

if [ ! -d "$VENV" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q -r "$BOT_DIR/requirements.txt" || true
    pip install -q streamlit || true
else
    source "$VENV/bin/activate"
    python - <<'PY' >/dev/null 2>&1 || MISSING=1
import streamlit
PY
    if [ "${MISSING:-0}" = "1" ]; then
        pip install -q -r "$BOT_DIR/requirements.txt" || true
        pip install -q streamlit || true
    fi
fi

echo "Starting XLM bot (live)..."
nohup /bin/sh -c "while true; do python main.py --live --i-understand-live; sleep 60; done" > logs/xpb_console.log 2>&1 &
sleep 2

echo "Starting dashboard on :8502..."
nohup streamlit run dashboard.py --server.port 8502 --server.headless true > logs/dashboard.log 2>&1 &

sleep 2
echo ""
echo "Bot PID: $(pgrep -f 'python.*xlm_bot/main.py')"
echo "Dashboard: http://localhost:8502"
