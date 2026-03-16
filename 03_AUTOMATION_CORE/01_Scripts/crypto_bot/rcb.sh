#!/bin/bash
# rcb - Restart CDE_BOT
# Stops all running instances and restarts bot + dashboard (safe, no global pkill)

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot"
VENV="/tmp/crypto_bot_venv"
BOT_PID_FILE="$BOT_DIR/data/bot.pid"
DASH_PID_FILE="$BOT_DIR/data/dashboard.pid"

echo "Stopping existing bot (via cb)..."
cd "$BOT_DIR" || exit 1
bash "$BOT_DIR/cb" stop >/dev/null 2>&1 || true

echo "Stopping existing dashboard..."
if [ -f "$DASH_PID_FILE" ]; then
  PID="$(cat "$DASH_PID_FILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && ps -p "$PID" >/dev/null 2>&1; then
    kill -TERM "$PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$DASH_PID_FILE" 2>/dev/null || true
fi

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
bash "$BOT_DIR/cb" start >/dev/null 2>&1 || true

echo "Starting dashboard..."
nohup "$VENV/bin/python" -m streamlit run dashboard.py --server.port 8501 --server.headless true --server.address 0.0.0.0 > logs/dashboard.log 2>&1 &
echo $! > "$DASH_PID_FILE"

sleep 2
echo ""
echo "Bot PID: $(cat "$BOT_PID_FILE" 2>/dev/null || echo '?')"
echo "Dashboard PID: $(cat "$DASH_PID_FILE" 2>/dev/null || echo '?')"
echo "Dashboard: http://localhost:8501 (or http://<LAN-IP>:8501)"
echo ""
echo "Logs:"
echo "  tail -f $BOT_DIR/logs/bot_$(date +%Y%m%d).log"
echo "  tail -f $BOT_DIR/logs/bot_console.log"
echo "  tail -f $BOT_DIR/logs/dashboard.log"
