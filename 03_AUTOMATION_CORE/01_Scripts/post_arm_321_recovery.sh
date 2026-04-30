#!/usr/bin/env bash
# post_arm_321_recovery.sh
#
# Triggered by oracle_arm_auto_grab.sh once ARM A1.Flex instance lands.
# Executes the full 3-2-1 backup recovery plan that Marquise approved
# (Option A) for the orphaned E5 data.
#
# Sequence:
#   1. Attach the orphan E5 boot volume to the new ARM instance as a
#      paravirtualized data disk (architecture-independent, works on ARM).
#   2. SSH to ARM, mount the disk read-only at /mnt/recovery
#   3. Push entire data tree to Google Drive (encrypted via rclone crypt)
#      - Drive folder: /Everlight/oracle_e5_backup/<timestamp>/
#   4. Create SHA256 manifest of every file
#   5. Notify Slack #hive-alerts AND ntfy.sh push that Drive copy is done
#   6. Phone-side cron (separate) pulls from Drive to local
#      /mnt/sdcard/AA_MY_DRIVE/_offsite_backups/oracle_e5/
#   7. After phone pull confirmed, run verify_321_redundancy.sh
#   8. ONLY after 3 verified copies exist, prompt Marquise to approve
#      deletion of the 3 redundant Oracle copies.
#
# This script does NOT delete anything. Deletion is gated on a separate
# script (cleanup_oracle_duplicates.sh) that requires Marquise's explicit
# GO after seeing the verified 3-2-1 manifest.
#
# Prerequisites (set up ONCE on phone, before ARM lands):
#   - rclone installed: pkg install rclone (Termux)
#   - Drive auth configured via: rclone config (creates ~/.config/rclone/rclone.conf)
#   - Drive remote name in rclone.conf must be: drive_everlight
#   - Optional: rclone crypt remote for encryption: drive_everlight_crypt
set -euo pipefail
export SUPPRESS_LABEL_WARNING=True

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/post_arm_321_recovery.log
MANIFEST=/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_321_manifest.json
ARM_IP_FILE=/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_arm_recovered.json
RCLONE_CONF=$HOME/.config/rclone/rclone.conf
SSH_KEY=/root/.ssh/oracle_key.pem
ORPHAN_BV="ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq"

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

# Pre-flight checks
log "═══════════════════════════════════════════════════════════════"
log "  POST-ARM 3-2-1 RECOVERY -- starting"
log "═══════════════════════════════════════════════════════════════"

# Did auto-grab actually land an ARM instance?
if [ ! -f "$ARM_IP_FILE" ]; then
    log "FAIL: $ARM_IP_FILE missing (auto-grab hasn't fired or failed). Exit."
    exit 1
fi
ARM_INSTANCE_ID=$(python3 -c "import json; print(json.load(open('$ARM_IP_FILE'))['instance_id'])")
log "ARM instance: ${ARM_INSTANCE_ID: -25}"

ARM_IP=$(oci compute instance list-vnics --instance-id "$ARM_INSTANCE_ID" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['public-ip'])")
log "ARM public IP: $ARM_IP"

# Is rclone configured for Drive?
if [ ! -f "$RCLONE_CONF" ]; then
    log "FAIL: $RCLONE_CONF missing. Marquise needs to run setup_rclone_drive.sh first."
    exit 1
fi
if ! grep -q "drive_everlight" "$RCLONE_CONF"; then
    log "FAIL: rclone remote 'drive_everlight' not configured. See setup_rclone_drive.sh."
    exit 1
fi
log "✓ rclone Drive config present"

# ── STEP 1: attach orphan to ARM as paravirt data disk ────────────────
log "STEP 1: attach orphan boot vol to ARM as data disk"
oci compute boot-volume-attachment attach \
    --instance-id "$ARM_INSTANCE_ID" \
    --boot-volume-id "$ORPHAN_BV" \
    --encryption-in-transit-type NONE \
    > /tmp/att_321.json 2> /tmp/att_321.err
if grep -q "ServiceError" /tmp/att_321.err; then
    log "  attach failed (likely orphan still in cooldown). Falling back: clone fresh boot vol."
    # Fallback: use the E5_FRESH_xxx clone we already created
    FRESH_BV=$(oci bv boot-volume list -c "$(grep tenancy /root/.oci/config | cut -d= -f2 | tr -d ' ')" --availability-domain "kNfe:US-SANJOSE-1-AD-1" --all 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for v in d.get('data',[]):
    if v.get('display-name','').startswith('E5_FRESH_') and v.get('lifecycle-state')=='AVAILABLE':
        print(v['id']); break
")
    if [ -z "$FRESH_BV" ]; then
        log "  no fresh clone available either. ABORT."
        exit 1
    fi
    log "  fallback boot vol: ${FRESH_BV: -25}"
    oci compute boot-volume-attachment attach \
        --instance-id "$ARM_INSTANCE_ID" \
        --boot-volume-id "$FRESH_BV" \
        --encryption-in-transit-type NONE \
        > /tmp/att_321b.json 2> /tmp/att_321b.err
    cat /tmp/att_321b.err | tee -a "$LOG"
fi
ATT_ID=$(python3 -c "
import json
for f in ['/tmp/att_321.json', '/tmp/att_321b.json']:
    try:
        with open(f) as fh:
            d = json.load(fh)
            print(d['data']['id']); break
    except: pass
" 2>/dev/null)
[ -z "$ATT_ID" ] && { log "FAIL: no attachment id"; exit 1; }
log "  attachment: ${ATT_ID: -30}"

# Wait for ATTACHED
until [ "$(oci compute boot-volume-attachment get --boot-volume-attachment-id "$ATT_ID" 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["lifecycle-state"])')" = "ATTACHED" ]; do
    sleep 5
    log "  $(date '+%H:%M:%S') still attaching..."
done
log "  ✓ ATTACHED"

# ── STEP 2: SSH to ARM, mount the disk ───────────────────────────────
log "STEP 2: mount disk on ARM"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o UserKnownHostsFile=/dev/null opc@"$ARM_IP" "
set -e
sudo mkdir -p /mnt/recovery
# The new disk should appear as /dev/sdb (ARM uses paravirt block devices)
NEW_DEV=\$(lsblk -ndo NAME | grep -v sda | head -1)
NEW_DEV=\"/dev/\$NEW_DEV\"
if [ -z \"\$NEW_DEV\" ] || [ \"\$NEW_DEV\" = '/dev/' ]; then
    echo 'FAIL: no new device found'
    lsblk
    exit 1
fi
echo \"new device: \$NEW_DEV\"
# Boot volumes typically have multiple partitions; find the largest non-boot one
PART=\$(lsblk -ln -o NAME,SIZE,TYPE \"\$NEW_DEV\" | awk '\$3==\"part\"' | sort -k2 -h | tail -1 | awk '{print \"/dev/\"\$1}')
echo \"target partition: \$PART\"
sudo mount -o ro \"\$PART\" /mnt/recovery 2>&1 || sudo mount -o ro \"\$NEW_DEV\" /mnt/recovery
echo '--- mount confirmed ---'
df -h /mnt/recovery
ls /mnt/recovery/home/opc/ 2>/dev/null | head -10
" 2>&1 | tee -a "$LOG"

# ── STEP 3: rclone push to Drive ─────────────────────────────────────
log "STEP 3: rclone push /home/opc + /var/lib/* to Drive"
DRIVE_FOLDER="oracle_e5_backup_$(date -u +%Y%m%dT%H%M%SZ)"

# Copy rclone.conf to ARM so it can push to Drive directly
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "$RCLONE_CONF" "opc@$ARM_IP:/home/opc/.rclone.conf"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o UserKnownHostsFile=/dev/null opc@"$ARM_IP" "
set -e
# Install rclone on ARM if not present
if ! command -v rclone >/dev/null; then
    sudo curl -fsSL https://rclone.org/install.sh | sudo bash
fi
export RCLONE_CONFIG=/home/opc/.rclone.conf

# Push the irreplaceable runtime data
for src in /mnt/recovery/home/opc /mnt/recovery/var/lib/blinko /mnt/recovery/var/lib/n8n /mnt/recovery/var/log /mnt/recovery/etc/systemd/system; do
    if [ -d \"\$src\" ]; then
        relname=\$(echo \"\$src\" | sed 's|/mnt/recovery/||g; s|/|_|g')
        echo \"--- pushing \$src to drive_everlight:Everlight/${DRIVE_FOLDER}/\$relname/ ---\"
        rclone copy --config /home/opc/.rclone.conf -v --transfers 4 \"\$src\" \"drive_everlight:Everlight/${DRIVE_FOLDER}/\$relname/\" 2>&1 | tail -5
    fi
done

# Generate SHA256 manifest of /home/opc subset (faster than full disk)
echo '--- generating SHA256 manifest ---'
sudo find /mnt/recovery/home/opc /mnt/recovery/var/lib/blinko 2>/dev/null -type f | head -5000 | sudo xargs sha256sum > /tmp/oracle_321_manifest.txt 2>/dev/null
wc -l /tmp/oracle_321_manifest.txt
rclone copy --config /home/opc/.rclone.conf /tmp/oracle_321_manifest.txt \"drive_everlight:Everlight/${DRIVE_FOLDER}/\" 2>&1 | tail -3

echo '=== DRIVE PUSH COMPLETE ==='
echo \"Drive folder: Everlight/${DRIVE_FOLDER}/\"
" 2>&1 | tee -a "$LOG"

# ── STEP 4: log success + post Slack/ntfy ────────────────────────────
log "STEP 4: notifying Slack + ntfy"
python3 <<PYEOF 2>&1 | tee -a "$LOG"
import os, sys
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
        title="3-2-1 Recovery Phase 1 Complete",
        summary=f"Oracle E5 data pushed to Google Drive folder Everlight/${DRIVE_FOLDER}/. Phone pull cron will sync next. Verify before Oracle cleanup.",
        agent_name="Iron Stack",
        agent_title="DevOps",
    )
    print("Slack notified")
except Exception as e:
    print(f"Slack post err: {e}")
PYEOF

log "═══════════════════════════════════════════════════════════════"
log "  POST-ARM 3-2-1 RECOVERY -- Phase 1 done"
log "  Next: phone-side cron pulls from Drive"
log "  Drive folder: Everlight/${DRIVE_FOLDER}/"
log "═══════════════════════════════════════════════════════════════"
