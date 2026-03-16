#!/bin/bash
# Slack Standup -- Native Canvas redirection
# Cron: 0 */6 * * * /home/opc/xlm-bot/slack_standup.sh

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot"
METRICS="$BOT_DIR/data/metrics.json"
BRIDGE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/slack_canvas_bridge.py"

# Generate fresh metrics first
cd "$BOT_DIR"
python3 export_metrics.py >/dev/null 2>&1

if [ ! -f "$METRICS" ]; then
    echo "[STANDUP] No metrics available."
    exit 1
fi

# Build message from metrics
MSG=$(python3 -c "
import json
m = json.load(open('$METRICS'))
status = 'ALIVE' if m.get('bot_alive') else 'DOWN'
pos = m.get('position_side') or 'flat'
pnl = m.get('pnl_today_usd', 0)
trades = m.get('trades_today', 0)
wins = m.get('wins', 0)
losses = m.get('losses', 0)
wr = m.get('win_rate_pct', 0)
regime = m.get('vol_state', '?')
equity = m.get('equity_start_usd', 0)
usdc = m.get('spot_usdc', 0)
safe = m.get('safe_mode', False)

lines = [
    '*XLM Bot Standup Report*',
    f'Status: {status} | Regime: {regime}',
    f'Equity: ${equity:.2f} | Spot USDC: ${usdc:.2f}',
    f'PnL today: ${pnl:+.2f}',
    f'Trades: {trades} (W:{wins} L:{losses}) | WR: {wr}%',
    f'Position: {pos}',
    f'Safe mode: {safe}',
]
print('\n'.join(lines))
" 2>/dev/null)

# ROUTE THROUGH CANVAS BRIDGE
echo "$MSG" > /tmp/bot_standup.md
python3 "$BRIDGE" /tmp/bot_standup.md xlmbot
