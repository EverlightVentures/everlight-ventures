#!/usr/bin/env bash
set -e

BOT_DIR="/app"
CONFIG="${XLM_CONFIG_FILE:-config.yaml}"
VENV_PYTHON="python3"

echo "=== XLM Bot Docker Entrypoint ==="
echo "Config: $CONFIG"
echo "Coinbase config: $COINBASE_CONFIG_PATH"
echo "CRYPTO_BOT_DIR: $CRYPTO_BOT_DIR"

# Verify secrets exist
if [ ! -f "$COINBASE_CONFIG_PATH" ]; then
    echo "ERROR: Coinbase config not found at $COINBASE_CONFIG_PATH"
    echo "Mount your config.json via: -v /path/to/config.json:/app/secrets/config.json"
    exit 1
fi

cd "$BOT_DIR"

# Start dashboard in background
echo "Starting dashboard on port 8502..."
$VENV_PYTHON -m streamlit run dashboard.py \
    --server.port=8502 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    > logs/dashboard.log 2>&1 &
DASH_PID=$!
echo "Dashboard PID: $DASH_PID"

# Start websocket feed in background
echo "Starting websocket feed..."
$VENV_PYTHON live_ws.py > logs/live_ws.log 2>&1 &
WS_PID=$!
echo "WS PID: $WS_PID"

# Resource + heartbeat watchdog (background, requires SLACK_WEBHOOK_URL)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
  (
    while true; do
      sleep 120
      MEM_PCT=$(free 2>/dev/null | awk '/^Mem:/{printf "%.0f", $3/$2*100}' || echo 0)
      HB_AGE=$(python3 -c "
import time, os
hb = '/app/.heartbeat'
print(int(time.time() - os.stat(hb).st_mtime) if os.path.exists(hb) else 9999)
" 2>/dev/null || echo 9999)
      if [ "$MEM_PCT" -gt 85 ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
          -H 'Content-type: application/json' \
          --data "{\"text\":\":warning: Oracle VM memory at ${MEM_PCT}% -- bot may crash soon\"}" \
          > /dev/null 2>&1
      fi
      if [ "$HB_AGE" -gt 180 ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
          -H 'Content-type: application/json' \
          --data "{\"text\":\":red_circle: Bot heartbeat stale ${HB_AGE}s -- may be dead. Check Oracle VM.\"}" \
          > /dev/null 2>&1
      fi
    done
  ) &
  WATCHDOG_PID=$!
  echo "Resource watchdog PID: $WATCHDOG_PID"
fi

# Bot loop (foreground) — matches xpb-fg behavior
echo "Starting bot loop..."
while true; do
    $VENV_PYTHON main.py --config "$CONFIG" --live --i-understand-live 2>&1 | tee -a logs/xpb_console.log

    # Read sleep time from state
    SLEEP=30
    if [ -f data/state.json ]; then
        HAS_POS=$(python3 -c "
import json
s = json.load(open('data/state.json'))
print('yes' if s.get('open_position') else 'no')
" 2>/dev/null || echo "no")
        if [ "$HAS_POS" = "yes" ]; then
            SLEEP=5
        fi
    fi

    sleep "$SLEEP"
done
