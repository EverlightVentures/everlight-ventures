#!/bin/bash
# rcb - Restart Crypto Bot
# Stops all running instances and restarts bot + dashboard

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot"
VENV="/tmp/crypto_bot_venv"

echo "Stopping existing processes..."
pkill -f "python.*bot.py" 2>/dev/null
pkill -f "streamlit.*dashboard" 2>/dev/null
sleep 1

cd "$BOT_DIR" || exit 1

# Ensure venv exists
if [ ! -d "$VENV" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q streamlit plotly requests pyjwt cryptography streamlit-autorefresh
else
    source "$VENV/bin/activate"
fi

echo "Starting bot..."
nohup python bot.py > logs/bot_console.log 2>&1 &
sleep 2

echo "Starting dashboard..."
nohup streamlit run dashboard.py --server.port 8501 --server.headless true > logs/dashboard.log 2>&1 &

sleep 2
echo ""
echo "Bot PID: $(pgrep -f 'python.*bot.py')"
echo "Dashboard: http://localhost:8501"
echo ""
echo "Logs:"
echo "  tail -f $BOT_DIR/logs/bot_$(date +%Y%m%d).log"
echo "  tail -f $BOT_DIR/logs/bot_console.log"
