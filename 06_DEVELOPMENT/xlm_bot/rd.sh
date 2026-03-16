#!/bin/bash
# rd - Restart XLM PERP dashboard only

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
VENV="/tmp/xlm_bot_venv"
PORT=8503

echo "Stopping existing dashboard on port $PORT..."
lsof -ti :$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

cd "$BOT_DIR" || exit 1

# Ensure venv exists
if [ ! -d "$VENV" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q -r "$BOT_DIR/requirements.txt"
    pip install -q streamlit
else
    source "$VENV/bin/activate"
    pip install -q -r "$BOT_DIR/requirements.txt"
    pip install -q streamlit
fi

echo "Starting dashboard on port $PORT..."
nohup streamlit run dashboard.py --server.port $PORT --server.headless true > logs/dashboard.log 2>&1 &

sleep 2
echo ""
echo "Dashboard: http://localhost:$PORT"
echo ""
echo "Logs:"
echo "  tail -f $BOT_DIR/logs/dashboard.log"
