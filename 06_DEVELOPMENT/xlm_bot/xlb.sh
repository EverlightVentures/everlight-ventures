#!/bin/bash
# xlb - Restart XLM PERP Bot (live + watchdog)
#
# Runs main.py in a supervisor loop:
# - Faster cadence while in a position (reduce liquidation/stop exposure).
# - Slower cadence when flat.
#
# NOTE: Live trading requires `--i-understand-live`.

set -u

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
VENV="/tmp/xlm_bot_venv"

IDLE_SLEEP="${IDLE_SLEEP:-30}"
IN_TRADE_SLEEP="${IN_TRADE_SLEEP:-5}"

echo "Stopping existing bot processes..."
pkill -f "python.*xlm_bot/main.py" 2>/dev/null
sleep 1

cd "$BOT_DIR" || exit 1

if [ ! -d "$VENV" ]; then
  echo "Creating venv..."
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install -q -r "$BOT_DIR/requirements.txt"

echo "Starting XLM PERP LIVE watchdog loop..."
nohup /bin/sh -c "
  cd \"$BOT_DIR\" || exit 1
  while true; do
    python main.py --live --i-understand-live
    S=\$(python -c \"import json; from pathlib import Path; p=Path('data/state.json'); s=json.loads(p.read_text()) if p.exists() else {}; print($IN_TRADE_SLEEP if s.get('open_position') else $IDLE_SLEEP)\")
    sleep \"\$S\"
  done
" > logs/xlb_console.log 2>&1 &

sleep 2
echo ""
echo "xlb PID: $(pgrep -f 'python.*xlm_bot/main.py' | head -n 1)"
echo ""
echo "Logs:"
echo "  tail -f $BOT_DIR/logs/xlb_console.log"
