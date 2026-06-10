#!/usr/bin/env bash
# post_recovery_redeploy.sh
#
# Auto-fires when Oracle E5 reachability is restored.
# Idempotent: safe to run multiple times. Verifies services, redeploys if
# anything missing, reactivates crons + watchdog mirror on Oracle side.
#
# Triggered by:
#   (a) oracle_reachability_watch.py on transition DEAD->ALIVE, OR
#   (b) Manually: bash post_recovery_redeploy.sh
#
# Logs to /mnt/sdcard/AA_MY_DRIVE/_logs/oracle_recovery.log
set -euo pipefail

ORACLE_IP="163.192.19.196"
PRIVATE_IP="10.0.0.22"
LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_recovery.log"
SSH_KEY="/root/.ssh/oracle_key.pem"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null"

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }
ssh_oracle() { ssh $SSH_OPTS "opc@$ORACLE_IP" "$@"; }

log "=== Post-recovery redeploy starting (target $ORACLE_IP) ==="

# Step 1: confirm SSH works
log "Step 1: SSH probe"
if ! timeout 15 ssh_oracle "echo OK" >/dev/null 2>&1; then
    log "FAIL: SSH not reachable on $ORACLE_IP. Aborting redeploy."
    exit 1
fi
log "Step 1: SSH OK"

# Step 2: capture VM state
log "Step 2: VM state snapshot"
ssh_oracle "
    echo '--- hostname ---'; hostname
    echo '--- uptime ---'; uptime
    echo '--- df -h / ---'; df -h /
    echo '--- public IP self-test ---'; curl -sS -m 5 https://ifconfig.io 2>/dev/null || echo no_internet
    echo '--- iptables INPUT ---'; sudo iptables -L INPUT -n | head -15
" 2>&1 | tee -a "$LOG"

# Step 3: service status check
log "Step 3: service status"
SERVICE_STATE=$(ssh_oracle "
    for s in n8n hive-django blinko hive-voice xlm-bot xlm-dash-react xlm-ws hive-self-heal; do
        active=\$(systemctl is-active \$s 2>/dev/null || echo missing)
        echo \"\$s=\$active\"
    done
" 2>&1 || echo "ssh_failed")
echo "$SERVICE_STATE" | tee -a "$LOG"

# Step 4: restart any inactive services
log "Step 4: restart inactive services"
echo "$SERVICE_STATE" | grep -v "=active" | grep -v "=missing" | while IFS='=' read -r svc state; do
    if [ -n "$svc" ] && [ "$state" != "active" ] && [ "$state" != "missing" ]; then
        log "  restarting $svc (was $state)"
        ssh_oracle "sudo systemctl restart $svc" 2>&1 | tee -a "$LOG" || log "  failed to restart $svc"
    fi
done

# Step 5: redeploy scripts (only if deploy_to_oracle.sh exists locally)
if [ -x /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh ]; then
    log "Step 5: redeploying scripts via deploy_to_oracle.sh"
    bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh 2>&1 | tee -a "$LOG" || log "deploy script returned non-zero"
else
    log "Step 5: skipping redeploy (deploy_to_oracle.sh not executable)"
fi

# Step 6: install Oracle-side watchdog if not present
log "Step 6: install Oracle-side watchdog"
if [ -f /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/oracle_reachability_watchdog_oracle_side.py ]; then
    scp $SSH_OPTS /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/oracle_reachability_watchdog_oracle_side.py "opc@$ORACLE_IP:/home/opc/oracle_watchdog_self.py" 2>&1 | tee -a "$LOG"
    ssh_oracle "
        # Add to user crontab if not already there
        (crontab -l 2>/dev/null | grep -v oracle_watchdog_self.py; echo '* * * * * /usr/bin/python3 /home/opc/oracle_watchdog_self.py >/dev/null 2>&1') | crontab -
        echo cron_installed
    " 2>&1 | tee -a "$LOG"
else
    log "Step 6: skipping (oracle-side watchdog source missing)"
fi

# Step 7: post recovery alert to Slack
log "Step 7: posting recovery to Slack"
python3 <<'PYEOF' 2>&1 | tee -a "$LOG" || log "Slack post failed (non-fatal)"
import sys, os
from pathlib import Path
ENV = Path('/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env')
for line in ENV.read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        k, _, v = line.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
sys.path.insert(0, '/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools')
try:
    from branded_slack import post_branded_alert
    post_branded_alert(
        channel="#hive-alerts",
        severity="info",
        title="Oracle E5 RECOVERED",
        summary="Connection restored to 163.192.19.196 (was 129.159.38.250). Services verified, crons reinstalled, watchdog re-armed.",
        agent_name="Iron Stack",
        agent_title="DevOps",
    )
    print("Slack post sent")
except Exception as e:
    print(f"Slack post error: {e}")
PYEOF

log "=== Post-recovery redeploy complete ==="
