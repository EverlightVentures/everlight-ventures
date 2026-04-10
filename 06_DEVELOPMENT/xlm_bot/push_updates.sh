#!/bin/bash
# Push config + new scripts to Oracle and restart bot
# Run this when Oracle SSH is back online

SSH_KEY="$HOME/.ssh/oracle_key.pem"
ORACLE_HOST="${ORACLE_HOST:-129.159.38.250}"
ORACLE_USER="${ORACLE_USER:-opc}"
ORACLE="${ORACLE_USER}@${ORACLE_HOST}"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 $ORACLE"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "Testing connection to $ORACLE..."
if ! $SSH_CMD "echo ok" 2>/dev/null; then
    echo "Oracle not reachable. Try again later."
    exit 1
fi

echo "Uploading config + scripts..."
$SCP_CMD "$BOT_DIR/main.py" "$ORACLE:~/xlm-bot/main.py"
$SCP_CMD "$BOT_DIR/config.yaml" "$ORACLE:~/xlm-bot/config.yaml"
$SCP_CMD "$BOT_DIR/ai/claude_advisor.py" "$ORACLE:~/xlm-bot/ai/claude_advisor.py"
$SCP_CMD "$BOT_DIR/ai/prompts.py" "$ORACLE:~/xlm-bot/ai/prompts.py"
$SCP_CMD "$BOT_DIR/alerts/slack_reports.py" "$ORACLE:~/xlm-bot/alerts/slack_reports.py"
$SCP_CMD "$BOT_DIR/vendor/gdocs_bridge.py" "$ORACLE:~/xlm-bot/vendor/gdocs_bridge.py"
$SCP_CMD "$BOT_DIR/vendor/report_template.py" "$ORACLE:~/xlm-bot/vendor/report_template.py"
$SCP_CMD "$BOT_DIR/feature_store.py" "$ORACLE:~/xlm-bot/feature_store.py"
$SCP_CMD "$BOT_DIR/house_money.py" "$ORACLE:~/xlm-bot/house_money.py"
$SCP_CMD "$BOT_DIR/export_metrics.py" "$ORACLE:~/xlm-bot/export_metrics.py"
$SCP_CMD "$BOT_DIR/push_metrics_supabase.py" "$ORACLE:~/xlm-bot/push_metrics_supabase.py"
$SCP_CMD "$BOT_DIR/trading_watchtower_sync.py" "$ORACLE:~/xlm-bot/trading_watchtower_sync.py"
$SCP_CMD "$BOT_DIR/circuit_breaker.sh" "$ORACLE:~/xlm-bot/circuit_breaker.sh"
$SCP_CMD "$BOT_DIR/error_detector.sh" "$ORACLE:~/xlm-bot/error_detector.sh"
$SCP_CMD "$BOT_DIR/watchdog.sh" "$ORACLE:~/xlm-bot/watchdog.sh"
$SCP_CMD "$BOT_DIR/slack_standup.sh" "$ORACLE:~/xlm-bot/slack_standup.sh"
$SCP_CMD "$BOT_DIR/memory_guard.sh" "$ORACLE:~/xlm-bot/memory_guard.sh"

echo "Setting permissions..."
$SSH_CMD "chmod +x ~/xlm-bot/*.sh"

echo "Setting up optimized cron (watchtower-first, staggered)..."
$SSH_CMD 'cat > /tmp/xlm_cron << "CRON"
# XLM Bot cron jobs -- live telemetry and self-healing
# Trading watchtower + metrics + Supabase push (every minute)
* * * * * cd /home/opc/xlm-bot && flock -xn /tmp/xlm_watchtower.lock env WATCHTOWER_PUSH_SUPABASE=1 /home/opc/xlm-bot/venv/bin/python trading_watchtower_sync.py >> /home/opc/xlm-bot/logs/trading_watchtower_sync.log 2>&1
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
$SSH_CMD "sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws xlm-watchtower.timer && free -m | head -2"

echo ""
echo "Done! Changes deployed:"
echo "  Bot controls:"
echo "  - deterministic freshness gates and safer AI defaults"
echo "  - feature store + trade labels enabled in the live bot"
echo "  Telemetry:"
echo "  - Supabase metrics push + public dashboard/watchtower feed"
echo "  - trading_watchtower_sync.py every minute with webhook support"
echo "  Reliability:"
echo "  - memory_guard.sh, watchdog.sh, circuit_breaker.sh"
echo "  - staggered cron + house_money.py automation"
