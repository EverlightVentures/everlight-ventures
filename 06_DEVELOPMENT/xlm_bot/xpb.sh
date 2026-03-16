#!/bin/bash
# xpb - Restart XLM PERP Bot (dry run)
# Stops all running instances and starts a fresh paper run

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
VENV="/tmp/xlm_bot_venv"

echo "Stopping existing processes..."
pkill -f "python.*xlm_bot/main.py" 2>/dev/null
sleep 1

cd "$BOT_DIR" || exit 1

# Ensure venv exists
if [ ! -d "$VENV" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q -r "$BOT_DIR/requirements.txt"
else
    source "$VENV/bin/activate"
    pip install -q -r "$BOT_DIR/requirements.txt"
fi

echo "Starting XLM PERP dry run (loop every 60s)..."
nohup /bin/sh -c "while true; do python main.py --paper; sleep 60; done" > logs/xpb_console.log 2>&1 &

sleep 2
echo ""
echo "xpb PID: $(pgrep -f 'python.*xlm_bot/main.py')"
echo ""
echo "Logs:"
echo "  tail -f $BOT_DIR/logs/xpb_console.log"
