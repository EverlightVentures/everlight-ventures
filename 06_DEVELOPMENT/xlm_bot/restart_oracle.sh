#!/bin/bash
# restart_oracle.sh -- Diagnose and restart XLM bot on Oracle Cloud
# Run from phone/laptop: bash restart_oracle.sh
#
# What it does:
#   1. SSHs into Oracle VM
#   2. Checks if bot processes are running (systemctl)
#   3. Checks disk space and memory
#   4. Restarts the bot if down
#   5. Restarts the dashboard if down
#   6. Prints status summary

set -euo pipefail

SSH_KEY="${HOME}/.ssh/oracle_key.pem"
ORACLE_IP="${ORACLE_HOST:-163.192.19.196}"
ORACLE_USER="${ORACLE_USER:-opc}"
ORACLE="${ORACLE_USER}@${ORACLE_IP}"
BOT_DIR="/home/opc/xlm-bot"

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o GSSAPIAuthentication=no -o AddressFamily=inet"
SSH_CMD="ssh $SSH_OPTS $ORACLE"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

echo "================================================="
echo "  XLM Bot Oracle Diagnostic + Restart"
echo "  Target: ${ORACLE_IP}"
echo "  Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "================================================="
echo ""

# ---- Step 0: Test SSH connectivity ----
echo "[1/6] Testing SSH connection..."
if ! $SSH_CMD "echo ok" 2>/dev/null; then
    fail "Cannot reach Oracle VM at ${ORACLE_IP}"
    echo ""
    echo "Possible causes:"
    echo "  - VM is stopped (check OCI console)"
    echo "  - Firewall/security list blocking SSH"
    echo "  - SSH key mismatch"
    echo ""
    echo "Manual check:"
    echo "  oci compute instance get --instance-id ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq --query 'data.\"lifecycle-state\"' --raw-output"
    exit 1
fi
info "SSH connection OK"

# ---- Step 1: Check processes ----
echo ""
echo "[2/6] Checking bot processes..."
$SSH_CMD "
echo '--- systemd services ---'
for svc in xlm-bot xlm-dashboard xlm-ws xlm-liqfeed; do
    status=\$(sudo systemctl is-active \$svc 2>/dev/null || echo 'inactive')
    printf '  %-20s %s\n' \"\$svc\" \"\$status\"
done

echo ''
echo '--- xlm-watchtower timer ---'
timer_status=\$(sudo systemctl is-active xlm-watchtower.timer 2>/dev/null || echo 'inactive')
printf '  %-20s %s\n' 'xlm-watchtower.timer' \"\$timer_status\"

echo ''
echo '--- python processes ---'
pgrep -af python | grep -E '(main\.py|dashboard\.py|live_ws\.py|watchtower)' || echo '  No bot python processes found'
"

# ---- Step 2: Check disk space ----
echo ""
echo "[3/6] Checking disk space..."
$SSH_CMD "
echo '--- disk usage ---'
df -h / | tail -1 | awk '{printf \"  Used: %s / %s (%s)\\n\", \$3, \$2, \$5}'

echo ''
echo '--- bot logs size ---'
du -sh ${BOT_DIR}/logs/ 2>/dev/null || echo '  logs dir not found'
"

# ---- Step 3: Check memory ----
echo ""
echo "[4/6] Checking memory..."
$SSH_CMD "
echo '--- memory ---'
free -m | awk '
NR==2 {printf \"  RAM:  %dMB used / %dMB total (%d%% used)\\n\", \$3, \$2, (\$3/\$2)*100}
NR==3 {printf \"  Swap: %dMB used / %dMB total\\n\", \$3, \$2}
'

echo ''
echo '--- top memory consumers ---'
ps aux --sort=-%mem | head -6 | awk 'NR>1 {printf \"  %s %s%% %s\\n\", \$1, \$4, \$11}'
"

# ---- Step 4: Check last activity ----
echo ""
echo "[5/6] Checking last bot activity..."
$SSH_CMD "
echo '--- last heartbeat ---'
if [ -f ${BOT_DIR}/data/.heartbeat ]; then
    HB=\$(cat ${BOT_DIR}/data/.heartbeat 2>/dev/null | tr -d '[:space:]')
    if [ -n \"\$HB\" ] && [ \"\$HB\" -gt 0 ] 2>/dev/null; then
        NOW=\$(date +%s)
        AGE=\$(( NOW - HB ))
        echo \"  Last heartbeat: \${AGE}s ago (\$(date -d @\$HB '+%Y-%m-%d %H:%M:%S %Z'))\"
        if [ \$AGE -gt 300 ]; then
            echo \"  WARNING: Heartbeat is stale (>5 min)\"
        fi
    else
        echo '  Heartbeat file exists but unreadable'
    fi
else
    echo '  No heartbeat file found'
fi

echo ''
echo '--- last live tick ---'
if [ -f ${BOT_DIR}/logs/live_tick.json ]; then
    TICK_AGE=\$(( \$(date +%s) - \$(stat -c %Y ${BOT_DIR}/logs/live_tick.json) ))
    echo \"  live_tick.json last modified: \${TICK_AGE}s ago\"
    if [ \$TICK_AGE -gt 120 ]; then
        echo \"  WARNING: Tick data is stale (>2 min)\"
    fi
else
    echo '  No live_tick.json found'
fi

echo ''
echo '--- last 5 log lines (bot) ---'
sudo journalctl -u xlm-bot --no-pager -n 5 2>/dev/null || echo '  No journal entries'

echo ''
echo '--- last 5 log lines (dashboard) ---'
sudo journalctl -u xlm-dashboard --no-pager -n 5 2>/dev/null || echo '  No journal entries'
"

# ---- Step 5: Restart anything that is down ----
echo ""
echo "[6/6] Restarting down services..."
$SSH_CMD "
RESTARTED=0

for svc in xlm-bot xlm-dashboard xlm-ws xlm-liqfeed; do
    status=\$(sudo systemctl is-active \$svc 2>/dev/null || echo 'inactive')
    if [ \"\$status\" != 'active' ]; then
        echo \"  Restarting \$svc (was: \$status)...\"
        sudo systemctl restart \$svc
        RESTARTED=\$((RESTARTED + 1))
    fi
done

# Watchtower timer
timer_status=\$(sudo systemctl is-active xlm-watchtower.timer 2>/dev/null || echo 'inactive')
if [ \"\$timer_status\" != 'active' ]; then
    echo '  Restarting xlm-watchtower.timer...'
    sudo systemctl restart xlm-watchtower.timer
    RESTARTED=\$((RESTARTED + 1))
fi

if [ \$RESTARTED -eq 0 ]; then
    echo '  All services already running -- no restart needed'
else
    echo \"  Restarted \$RESTARTED service(s). Waiting 5s for startup...\"
    sleep 5

    echo ''
    echo '--- post-restart status ---'
    for svc in xlm-bot xlm-dashboard xlm-ws xlm-liqfeed; do
        status=\$(sudo systemctl is-active \$svc 2>/dev/null || echo 'inactive')
        printf '  %-20s %s\n' \"\$svc\" \"\$status\"
    done
    timer_status=\$(sudo systemctl is-active xlm-watchtower.timer 2>/dev/null || echo 'inactive')
    printf '  %-20s %s\n' 'xlm-watchtower.timer' \"\$timer_status\"
fi
"

echo ""
echo "================================================="
echo "  Diagnostic complete"
echo "================================================="
echo ""
echo "  Dashboard: http://${ORACLE_IP}:8502"
echo "  SSH:       ssh ${SSH_OPTS} ${ORACLE}"
echo ""
echo "  Manual commands:"
echo "    sudo systemctl status xlm-bot"
echo "    sudo journalctl -u xlm-bot -f"
echo "    sudo systemctl restart xlm-bot"
echo "    sudo systemctl restart xlm-dashboard"
echo ""
echo "  Full redeploy (if restart is not enough):"
echo "    bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot/deploy-native.sh ${ORACLE_IP} ${SSH_KEY}"
echo ""
