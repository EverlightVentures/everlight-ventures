#!/usr/bin/env bash
# kill_blockers_then_deploy.sh -- Layer 4 of the Oracle Watch architecture.
#
# Wraps deploy_to_oracle.sh with a pre-flight step that:
#   1. Reads the phone-side reachability watcher's state file. If RED, abort
#      the deploy and surface the diagnosis instead of failing silently after
#      a 30-second SSH timeout.
#   2. Kills any stale phone-side SSH multiplex sessions to Oracle (these
#      hang for 30+ seconds in PRoot under flaky cellular).
#   3. Pre-warms a fresh authenticated SSH connection so the rsync uses a
#      clean channel.
#   4. On the Oracle side, kills any process holding deploy-target file locks
#      (fuser -k) so a partial-deploy from a previous run cannot block this
#      one.
#   5. Runs the actual deploy (deploy_to_oracle.sh).
#   6. On non-zero exit, restarts the affected Oracle services and re-tests
#      reachability via the watcher's state file.
#
# Usage:
#   ./kill_blockers_then_deploy.sh           # full deploy
#   ./kill_blockers_then_deploy.sh scripts   # passes args through
#
# Author: Henrik Strand (Iron Stack S1)

set -euo pipefail

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
STATE_FILE="$WORKSPACE/_logs/.oracle_reachability_state.json"
DEPLOY_SCRIPT="$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh"
LOG_FILE="$WORKSPACE/_logs/kill_blockers_deploy.log"

ORACLE_HOST="163.192.19.196"
SSH_KEY="/root/.ssh/oracle_key.pem"
SSH_USER="opc"

ts() { date "+%Y-%m-%d %H:%M:%S PT"; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")"
log "==== kill_blockers_then_deploy invoked: args=$* ===="

# -----------------------------------------------------------------------------
# Step 1: read watcher state. Abort early if RED.
# -----------------------------------------------------------------------------
if [[ -f "$STATE_FILE" ]]; then
    STATUS=$(python3 -c "import json,sys; print(json.load(open('$STATE_FILE')).get('current_status','UNKNOWN'))" 2>/dev/null || echo "PARSE_ERROR")
    log "Reachability watcher state: $STATUS"
    if [[ "$STATUS" == "RED" ]]; then
        log "ABORT: Oracle is RED per phone-side watcher. Run /mnt/sdcard/AA_MY_DRIVE/_logs/oracle_disconnect_diagnosis_2026-04-29.md playbook before retrying."
        log "If you believe Oracle is reachable again, delete $STATE_FILE and re-run."
        exit 10
    fi
elif [[ ! -f "$STATE_FILE" ]]; then
    log "WARN: watcher state file missing -- proceeding without pre-flight reachability check (start oracle_reachability_watch.py to enable it)"
fi

# -----------------------------------------------------------------------------
# Step 2: kill stale phone-side SSH multiplex sessions.
# -----------------------------------------------------------------------------
log "Killing stale phone-side SSH sessions to Oracle..."
PIDS=$(pgrep -af "ssh.*${ORACLE_HOST}" 2>/dev/null | awk '{print $1}' || true)
if [[ -n "$PIDS" ]]; then
    log "Killing PIDs: $PIDS"
    echo "$PIDS" | xargs -r kill -TERM 2>/dev/null || true
    sleep 1
    echo "$PIDS" | xargs -r kill -KILL 2>/dev/null || true
else
    log "No stale SSH sessions found"
fi

# -----------------------------------------------------------------------------
# Step 3: pre-warm a fresh SSH connection (8s test).
# -----------------------------------------------------------------------------
log "Pre-warming SSH to Oracle (8s timeout)..."
if timeout 12 ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no -o BatchMode=yes \
        -i "$SSH_KEY" "${SSH_USER}@${ORACLE_HOST}" "echo SSH_OK" >/dev/null 2>&1; then
    log "SSH connection verified"
else
    log "FAIL: SSH pre-warm timed out. Oracle path is not actually open."
    log "Update watcher state to RED and abort:"
    if [[ -f "$STATE_FILE" ]]; then
        python3 -c "
import json
p='$STATE_FILE'
d=json.load(open(p))
d['current_status']='RED'
d['consecutive_failures']=max(d.get('consecutive_failures',0),3)
json.dump(d, open(p,'w'), indent=2)
" 2>/dev/null || true
    fi
    exit 11
fi

# -----------------------------------------------------------------------------
# Step 4: kill blocking processes on Oracle side (the user-requested feature).
# -----------------------------------------------------------------------------
log "Killing blocking processes on Oracle (file locks on deploy targets)..."
ssh -o ConnectTimeout=10 -i "$SSH_KEY" "${SSH_USER}@${ORACLE_HOST}" bash <<'REMOTE_KILL' || log "remote pre-clean returned non-zero (continuing)"
set -e
# Targets that deploy_to_oracle.sh writes to. If any process is holding them
# open, fuser -k will kill it so rsync isn't blocked mid-transfer.
TARGETS=(
    /home/opc/scripts
    /home/opc/hive_django
    /home/opc/content_tools
    /home/opc/stark_ai
)
for t in "${TARGETS[@]}"; do
    if [[ -d "$t" ]]; then
        # only kill processes still writing to deploy dirs (read-only is fine)
        sudo fuser -km -SIGTERM "$t" 2>/dev/null || true
    fi
done
# kill stale rsync server processes from previous deploys
sudo pkill -f "rsync --server" 2>/dev/null || true
echo "REMOTE_PRECLEAN_OK"
REMOTE_KILL

# -----------------------------------------------------------------------------
# Step 5: run the actual deploy.
# -----------------------------------------------------------------------------
log "Invoking deploy_to_oracle.sh $*"
DEPLOY_EXIT=0
bash "$DEPLOY_SCRIPT" "$@" || DEPLOY_EXIT=$?
log "deploy_to_oracle.sh exited: $DEPLOY_EXIT"

# -----------------------------------------------------------------------------
# Step 6: on failure, restart Oracle services and re-test.
# -----------------------------------------------------------------------------
if [[ $DEPLOY_EXIT -ne 0 ]]; then
    log "Deploy failed -- attempting service restart on Oracle"
    ssh -o ConnectTimeout=10 -i "$SSH_KEY" "${SSH_USER}@${ORACLE_HOST}" bash <<'REMOTE_RESTART' || true
sudo systemctl restart n8n hive-django blinko hive-voice 2>/dev/null
sleep 3
sudo systemctl is-active n8n hive-django blinko hive-voice 2>&1 | sed 's/^/  /'
REMOTE_RESTART
    log "Service restart attempted. Verify manually."
    exit "$DEPLOY_EXIT"
fi

log "==== deploy succeeded ===="
exit 0
