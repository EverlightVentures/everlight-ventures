#!/bin/bash
# Push config + new scripts to Oracle and restart bot
# Run this when Oracle SSH is back online

SSH_KEY="$HOME/.ssh/oracle_key.pem"
ORACLE="opc@163.192.19.196"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 $ORACLE"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "Testing connection..."
if ! $SSH_CMD "echo ok" 2>/dev/null; then
    echo "Oracle not reachable. Try again later."
    exit 1
fi

echo "Uploading config + scripts..."
$SCP_CMD "$BOT_DIR/config.yaml" "$ORACLE:~/xlm-bot/config.yaml"
$SCP_CMD "$BOT_DIR/house_money.py" "$ORACLE:~/xlm-bot/house_money.py"
$SCP_CMD "$BOT_DIR/export_metrics.py" "$ORACLE:~/xlm-bot/export_metrics.py"
$SCP_CMD "$BOT_DIR/circuit_breaker.sh" "$ORACLE:~/xlm-bot/circuit_breaker.sh"
$SCP_CMD "$BOT_DIR/error_detector.sh" "$ORACLE:~/xlm-bot/error_detector.sh"
$SCP_CMD "$BOT_DIR/watchdog.sh" "$ORACLE:~/xlm-bot/watchdog.sh"
$SCP_CMD "$BOT_DIR/slack_standup.sh" "$ORACLE:~/xlm-bot/slack_standup.sh"
$SCP_CMD "$BOT_DIR/memory_guard.sh" "$ORACLE:~/xlm-bot/memory_guard.sh"

echo "Setting permissions..."
$SSH_CMD "chmod +x ~/xlm-bot/*.sh"

echo "Setting up optimized cron (RAM-efficient, staggered)..."
$SSH_CMD 'cat > /tmp/xlm_cron << "CRON"
# XLM Bot cron jobs -- staggered to avoid RAM spikes
# Metrics exporter (lightweight, every 2 min)
*/2 * * * * cd /home/opc/xlm-bot && /home/opc/xlm-bot/venv/bin/python export_metrics.py > /dev/null 2>&1
# Memory guard + CPU keepalive (every 5 min, offset by 1)
1-56/5 * * * * /home/opc/xlm-bot/memory_guard.sh > /dev/null 2>&1
# Watchdog - zombie detection + service health (every 5 min, offset by 2)
2-57/5 * * * * /home/opc/xlm-bot/watchdog.sh > /dev/null 2>&1
# Circuit breaker (every 10 min, offset by 3)
3-53/10 * * * * /home/opc/xlm-bot/circuit_breaker.sh > /dev/null 2>&1
# Error pattern detector (every 3 hours)
0 */3 * * * /home/opc/xlm-bot/error_detector.sh > /dev/null 2>&1
# Slack standup (every 6 hours)
0 */6 * * * /home/opc/xlm-bot/slack_standup.sh > /dev/null 2>&1
# House money check (every 30 min)
15,45 * * * * cd /home/opc/xlm-bot && /home/opc/xlm-bot/venv/bin/python house_money.py > /dev/null 2>&1
CRON
crontab /tmp/xlm_cron && rm /tmp/xlm_cron && echo "Cron installed" && crontab -l'

echo ""
echo "Restarting bot with new config..."
$SSH_CMD "sudo systemctl restart xlm-bot"

echo "Waiting 5s..."
sleep 5

echo "Checking status..."
$SSH_CMD "sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws && free -m | head -2"

echo ""
echo "Done! Changes deployed:"
echo "  Strategy: swing-optimized for 4x leverage"
echo "  - daily_profit_target: \$50 -> \$500"
echo "  - TP targets widened (TP1:0.30 TP2:0.60 TP3:1.00)"
echo "  - trend_tp_atr: 1.40 -> 2.00"
echo "  - time_stop: 4 -> 8 bars (2hr), trend: 12 -> 24 bars (6hr)"
echo "  - trend entry profiles: TPs raised 1.5-2x"
echo "  - expansion profit locks widened"
echo "  Reliability:"
echo "  - memory_guard.sh (prevents OOM, kills dashboard before bot)"
echo "  - CPU keepalive (prevents Oracle reclamation)"
echo "  - staggered cron (no RAM spikes)"
echo "  - house_money.py (sweep initial capital at 2x equity)"
