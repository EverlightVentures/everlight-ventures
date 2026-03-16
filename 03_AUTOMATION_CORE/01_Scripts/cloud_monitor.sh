#!/bin/bash
# Cloud Health Monitor -- pulls Oracle bot data + checks health
#
# Usage:
#   bash cloud_monitor.sh --once          # single check (for cron)
#   bash cloud_monitor.sh                 # loop every 5 min
#   bash cloud_monitor.sh --status        # print status and exit

ORACLE_IP="163.192.19.196"
ORACLE_USER="opc"
SSH_KEY="$HOME/.ssh/oracle_key.pem"
REMOTE_DIR="xlm-bot"
LOCAL_SYNC="/mnt/sdcard/AA_MY_DRIVE/_logs/sync/xlm_bot_oracle"
SLACK_WEBHOOK=""

# Load webhook from env if available
[ -n "$SLACK_WEBHOOK_URL" ] && SLACK_WEBHOOK="$SLACK_WEBHOOK_URL"

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 $ORACLE_USER@$ORACLE_IP"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

HEARTBEAT_MAX_AGE=180

mkdir -p "$LOCAL_SYNC"

send_slack() {
    local msg="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"$msg\"}" >/dev/null 2>&1
    fi
    echo "[ALERT] $msg"
}

do_sync() {
    echo "[$(date '+%H:%M:%S PT')] Syncing from Oracle..."

    $SCP_CMD "$ORACLE_USER@$ORACLE_IP:~/$REMOTE_DIR/data/state.json" "$LOCAL_SYNC/" 2>/dev/null
    $SCP_CMD "$ORACLE_USER@$ORACLE_IP:~/$REMOTE_DIR/data/metrics.json" "$LOCAL_SYNC/" 2>/dev/null
    $SCP_CMD "$ORACLE_USER@$ORACLE_IP:~/$REMOTE_DIR/logs/trades.csv" "$LOCAL_SYNC/" 2>/dev/null
    $SCP_CMD "$ORACLE_USER@$ORACLE_IP:~/$REMOTE_DIR/.heartbeat" "$LOCAL_SYNC/" 2>/dev/null

    SVC_STATUS=$($SSH_CMD "sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws 2>/dev/null" 2>/dev/null)
    echo "$SVC_STATUS" > "$LOCAL_SYNC/service_status.txt"

    echo "  Services: $SVC_STATUS"
}

check_health() {
    local alert_needed=false
    local alert_msg=""

    if [ -f "$LOCAL_SYNC/metrics.json" ]; then
        local bot_alive=$(python3 -c "import json; m=json.load(open('$LOCAL_SYNC/metrics.json')); print(m.get('bot_alive', False))" 2>/dev/null)
        local hb_age=$(python3 -c "import json; m=json.load(open('$LOCAL_SYNC/metrics.json')); print(m.get('heartbeat_age_s', -1))" 2>/dev/null)

        if [ "$bot_alive" = "False" ]; then
            alert_needed=true
            alert_msg="XLM Bot heartbeat stale (${hb_age}s). Bot may be down!"
        fi

        python3 -c "
import json
m = json.load(open('$LOCAL_SYNC/metrics.json'))
print(f\"  Bot alive: {m.get('bot_alive')}\")
print(f\"  Heartbeat age: {m.get('heartbeat_age_s')}s\")
print(f\"  PnL today: \${m.get('pnl_today_usd', 0):.2f}\")
print(f\"  Trades: {m.get('trades_today', 0)} (W:{m.get('wins',0)} L:{m.get('losses',0)})\")
print(f\"  Regime: {m.get('vol_state')}\")
print(f\"  Position: {m.get('position_side') or 'flat'}\")
" 2>/dev/null
    else
        echo "  No metrics.json yet -- waiting for first cron run on Oracle"
    fi

    if [ -f "$LOCAL_SYNC/service_status.txt" ]; then
        if grep -q "inactive\|failed" "$LOCAL_SYNC/service_status.txt"; then
            alert_needed=true
            alert_msg="XLM Bot service down on Oracle! $(cat "$LOCAL_SYNC/service_status.txt")"
        fi
    fi

    if [ "$alert_needed" = true ]; then
        send_slack "$alert_msg"
    else
        echo "  Health: OK"
    fi
}

print_status() {
    if [ -f "$LOCAL_SYNC/metrics.json" ]; then
        python3 -c "
import json
m = json.load(open('$LOCAL_SYNC/metrics.json'))
print('=== XLM Bot Oracle Status ===')
print(f\"Session: {m.get('session_id')}\")
print(f\"Bot alive: {m.get('bot_alive')} (heartbeat {m.get('heartbeat_age_s')}s)\")
print(f\"Equity start: \${m.get('equity_start_usd', 0):.2f}\")
print(f\"PnL today: \${m.get('pnl_today_usd', 0):.2f}\")
print(f\"Trades: {m.get('trades_today', 0)} | Win rate: {m.get('win_rate_pct', 0)}%\")
print(f\"Regime: {m.get('vol_state')} | Recovery: {m.get('recovery_mode')}\")
print(f\"Position: {m.get('position_side') or 'flat'}\")
print(f\"Overnight: {m.get('overnight_ok')}\")
print(f\"Spot USDC: \${m.get('spot_usdc', 0):.2f}\")
print(f\"Safe mode: {m.get('safe_mode')}\")
print(f\"Generated: {m.get('generated_at')}\")
" 2>/dev/null
    else
        echo "No cached metrics. Run: bash cloud_monitor.sh --once"
    fi
}

case "${1:-loop}" in
    --once)
        do_sync
        check_health
        ;;
    --status)
        print_status
        ;;
    *)
        echo "Cloud monitor running (Ctrl+C to stop)..."
        while true; do
            do_sync
            check_health
            echo ""
            sleep 300
        done
        ;;
esac
