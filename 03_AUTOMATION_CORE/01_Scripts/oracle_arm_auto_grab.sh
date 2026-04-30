#!/usr/bin/env bash
# oracle_arm_auto_grab.sh
#
# Polls Oracle every 15 min. The moment ARM A1.Flex capacity opens
# in us-sanjose-1, grabs the slot, launches the recovery instance
# from the FRESH cloned E5 boot volume, and writes a marker file
# so subsequent runs no-op.
#
# Idempotent: safe to run from cron every 15 min indefinitely.
# Logs to: /mnt/sdcard/AA_MY_DRIVE/_logs/oracle_arm_auto_grab.log
set -euo pipefail
export SUPPRESS_LABEL_WARNING=True

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_arm_auto_grab.log
MARKER=/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_arm_grabbed.marker
SUCCESS_MSG=/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_arm_recovered.json

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# If we already grabbed, no-op
if [ -f "$MARKER" ]; then
    log "marker exists, skipping (instance already grabbed: $(cat $MARKER))"
    exit 0
fi

TENANCY=$(grep "^tenancy" /root/.oci/config | cut -d= -f2 | tr -d ' ')
AD="kNfe:US-SANJOSE-1-AD-1"
ARM_IMG_ID="ocid1.image.oc1.us-sanjose-1.aaaaaaaai7u6drx4yrgnyc4yelox5m4zhxw5viqjjxhducb4kizfoqybnceq"

# Get subnet ID from running Xlm-bot
SUBNET=$(oci compute instance list-vnics --instance-id "ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['subnet-id'])" 2>/dev/null)
if [ -z "$SUBNET" ]; then
    log "FAIL: cannot get subnet (Xlm-bot lookup failed)"
    exit 1
fi

PUBKEY=$(ssh-keygen -y -f /root/.ssh/oracle_key.pem 2>/dev/null)
echo "{\"ssh_authorized_keys\": \"$PUBKEY\"}" > /tmp/auto_md.json

# Try shape sizes from biggest to smallest -- prefer 4 OCPU 24GB
TRIED=0
GRABBED=""
for OCPUS in 4 2 1; do
    MEM=$((OCPUS * 6))
    [ $OCPUS -eq 1 ] && MEM=6
    log "trying VM.Standard.A1.Flex ${OCPUS} OCPU / ${MEM}GB"
    echo "{\"ocpus\": $OCPUS, \"memoryInGBs\": $MEM}" > /tmp/auto_shape.json
    OUT=$(oci compute instance launch \
        --availability-domain "$AD" \
        --compartment-id "$TENANCY" \
        --shape "VM.Standard.A1.Flex" \
        --shape-config file:///tmp/auto_shape.json \
        --image-id "$ARM_IMG_ID" \
        --display-name "hive-arm-$(date +%H%M%S)" \
        --subnet-id "$SUBNET" \
        --metadata file:///tmp/auto_md.json \
        --assign-public-ip true 2>&1)
    TRIED=$((TRIED+1))

    if echo "$OUT" | grep -q "Out of host capacity"; then
        log "  ${OCPUS}c capacity full, trying smaller"
        continue
    fi

    NEW_ID=$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "")
    if [ -n "$NEW_ID" ]; then
        log "  ✓ GRABBED ${OCPUS}c instance: ${NEW_ID: -25}"
        GRABBED="$NEW_ID"
        echo "{\"instance_id\":\"$NEW_ID\",\"shape_ocpus\":$OCPUS,\"shape_mem\":$MEM,\"grabbed_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$SUCCESS_MSG"
        echo "$NEW_ID" > "$MARKER"
        break
    fi

    log "  ${OCPUS}c failed (not capacity): $(echo "$OUT" | head -3)"
done

if [ -z "$GRABBED" ]; then
    log "all sizes failed -- will retry next cron cycle"
    exit 0
fi

log "=== Recovery instance LAUNCHED. Triggering post-recovery sequence ==="

# Wait for RUNNING + IP
until [ "$(oci compute instance get --instance-id "$GRABBED" 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["lifecycle-state"])' 2>/dev/null)" = "RUNNING" ]; do
    log "  waiting for state=RUNNING..."
    sleep 15
done

NEW_IP=$(oci compute instance list-vnics --instance-id "$GRABBED" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['public-ip'])" 2>/dev/null)
log "  ARM instance IP: $NEW_IP"

# Wait for SSH responsive (ARM stock Oracle Linux boots fast, ~60s)
until timeout 10 ssh -i /root/.ssh/oracle_key.pem -o StrictHostKeyChecking=no -o ConnectTimeout=8 -o UserKnownHostsFile=/dev/null opc@"$NEW_IP" "echo ARM_UP" 2>&1 | grep -q ARM_UP; do
    log "  waiting for ARM SSH..."
    sleep 15
done
log "  ✓ ARM SSH RESPONSIVE"

# Send recovery alert to Slack
python3 << PYEOF >> "$LOG" 2>&1 || log "(slack post failed, non-fatal)"
import sys, os
from pathlib import Path
ENV = Path('/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env')
for line in ENV.read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        k, _, v = line.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
sys.path.insert(0, '/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools')
from branded_slack import post_branded_alert
post_branded_alert(
    channel="#hive-alerts",
    severity="info",
    title="Oracle ARM Recovery Instance UP",
    summary=f"Auto-grabbed VM.Standard.A1.Flex at $NEW_IP. SSH responsive. Next: attach E5 boot volume + restore Hive backend.",
    agent_name="Iron Stack",
    agent_title="DevOps",
)
print("Slack notified")
PYEOF

log "=== Phase 1 COMPLETE: ARM is up. Now firing 3-2-1 recovery. ==="
log "    new IP: $NEW_IP"

# Phase 2: 3-2-1 backup recovery (Marquise approved Option A)
log "Phase 2: launching post_arm_321_recovery.sh in background"
nohup bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/post_arm_321_recovery.sh \
    >> /mnt/sdcard/AA_MY_DRIVE/_logs/post_arm_321_recovery.log 2>&1 &
log "    backgrounded as PID $!"

log "=== oracle_arm_auto_grab DONE. 3-2-1 recovery handing off. ==="
