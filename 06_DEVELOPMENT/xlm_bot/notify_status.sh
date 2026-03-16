#!/bin/bash
# Updates Termux notification with live bot status every 30s
# Keeps Termux visible as a foreground service to prevent Android killing it
BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"

# Clean up notification on exit
trap 'termux-notification-remove xlm-bot 2>/dev/null' EXIT

while true; do
    # Re-acquire wake-lock every cycle (belt and suspenders)
    termux-wake-lock 2>/dev/null

    STATUS=$(python3 -c "
import json
from datetime import datetime, timezone
try:
    with open('$BOT_DIR/data/state.json') as f:
        s = json.load(f)
    with open('$BOT_DIR/logs/dashboard_snapshot.json') as f:
        snap = json.load(f)
    op = s.get('open_position') or {}
    if op:
        d = op.get('direction','?').upper()
        entry = op.get('entry_price', 0)
        mark = snap.get('mark_price') or snap.get('price') or 0
        pnl = snap.get('pnl_usd_live')
        pnl_str = f'\${pnl:+.2f}' if pnl is not None else '?'
        # Time in trade
        try:
            et = datetime.fromisoformat(op.get('entry_time',''))
            mins = (datetime.now(timezone.utc) - et).total_seconds() / 60
            time_str = f'{mins:.0f}m'
        except:
            time_str = '?'
        print(f'{d} @ \${entry:.5f} | Mark \${mark:.5f} | {pnl_str} | {time_str}')
    else:
        usdc = (s.get('last_spot_cash_map') or {}).get('USDC', 0)
        pnl_today = s.get('pnl_today_usd', 0)
        print(f'IDLE | USDC \${usdc:.2f} (3.5%) | PnL \${pnl_today:+.2f}')
except Exception as e:
    print(f'Bot status unknown: {e}')
" 2>/dev/null)

    # Check if bot process is alive
    BOT_ALIVE=$(pgrep -f "python.*main.py.*--live" 2>/dev/null | head -1)
    if [ -z "$BOT_ALIVE" ]; then
        STATUS="BOT DOWN! $STATUS"
    fi

    termux-notification \
      --id xlm-bot \
      --title "XLM Bot${BOT_ALIVE:+ Active}${BOT_ALIVE:-  DOWN}" \
      --content "$STATUS" \
      --ongoing \
      --priority high \
      --alert-once 2>/dev/null

    sleep 30
done
