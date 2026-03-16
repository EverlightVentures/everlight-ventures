#!/bin/bash
# rxd - Restart XLM PERP bot + dashboard

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
VENV="/tmp/xlm_bot_venv"

echo "Stopping existing processes..."
pkill -f "python.*xlm_bot/main.py" 2>/dev/null
pkill -f "streamlit.*xlm_bot/dashboard.py" 2>/dev/null
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

echo "Starting XLM PERP dry run..."
nohup python main.py --paper > logs/xpb_console.log 2>&1 &
sleep 2

echo "Starting dashboard..."
nohup streamlit run dashboard.py --server.port 8502 --server.headless true > logs/dashboard.log 2>&1 &

sleep 2
echo ""
echo "Bot PID: $(pgrep -f 'python.*xlm_bot/main.py')"
echo "Dashboard: http://localhost:8502"
echo ""
echo "Logs:"
echo "  tail -f $BOT_DIR/logs/xpb_console.log"
echo "  tail -f $BOT_DIR/logs/dashboard.log"
