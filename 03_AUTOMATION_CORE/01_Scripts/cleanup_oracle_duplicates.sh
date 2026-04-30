#!/usr/bin/env bash
# cleanup_oracle_duplicates.sh
# ────────────────────────────
# Deletes the 3 redundant Oracle copies of the E5 data, keeping ONE
# (the orphan boot volume) as production access.
#
# Pre-requisites (HARD GATE):
#   - verify_321_redundancy.sh must exit 0 (all 3 copies confirmed)
#   - Marquise must explicitly run this script with --i-have-verified
#     (won't run by accident)
#   - Frees ~140GB of Oracle Always Free storage cap
#
# What gets DELETED:
#   - E5_FRESH_xxxxxx (Boot Volume)             — fresh clone from backup
#   - EMERGENCY_BACKUP_E5_20260429_181430       — backup snapshot #1
#   - EMERGENCY_BACKUP_E5_20260429_201615       — backup snapshot #2
#
# What gets KEPT:
#   - xlm-bot-core-e5-2c16g (Boot Volume)       — the orphan (production)
#   - All Always Free working volumes for live VMs
set -euo pipefail
export SUPPRESS_LABEL_WARNING=True

# Hard gate: require explicit flag
if [ "${1:-}" != "--i-have-verified" ]; then
    cat <<'EOF'
═══════════════════════════════════════════════════════════════
  cleanup_oracle_duplicates.sh -- HARD GATE
═══════════════════════════════════════════════════════════════

This script deletes 3 of 4 Oracle backup copies of the E5 data.

PREREQUISITES:
  1. ARM A1.Flex captured (auto-grab fired successfully)
  2. Drive copy pushed (post_arm_321_recovery.sh ran)
  3. Phone copy pulled (phone_pull_321_from_drive.sh ran)
  4. verify_321_redundancy.sh exited 0

To run for real:
  bash cleanup_oracle_duplicates.sh --i-have-verified

EOF
    exit 2
fi

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_cleanup.log
mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

log "═══════════════════════════════════════════════════════════════"
log "  ORACLE DUPLICATE CLEANUP -- starting"
log "═══════════════════════════════════════════════════════════════"

# Run verification one more time as belt-and-suspenders
log "Running final verify_321_redundancy.sh..."
if ! bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/verify_321_redundancy.sh > /tmp/final_verify.log 2>&1; then
    log "  FAIL: verification did not pass. Aborting cleanup."
    cat /tmp/final_verify.log >> "$LOG"
    exit 1
fi
log "  ✓ verification passed"

TENANCY=$(grep "^tenancy" /root/.oci/config | cut -d= -f2 | tr -d ' ')
AD="kNfe:US-SANJOSE-1-AD-1"
ORPHAN="ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq"

# 1. Find FRESH clone(s) and delete
log "STEP 1: delete E5_FRESH_xxxxxx clones"
oci bv boot-volume list -c "$TENANCY" --availability-domain "$AD" --all 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for v in d.get('data',[]):
    if v.get('display-name','').startswith('E5_FRESH_') and v.get('lifecycle-state')=='AVAILABLE':
        print(v['id'])
" | while read -r FRESH_ID; do
    log "  deleting fresh clone: ${FRESH_ID: -25}"
    oci bv boot-volume delete --boot-volume-id "$FRESH_ID" --force 2>&1 | tee -a "$LOG"
done

# 2. Delete the 2 backup snapshots
log "STEP 2: delete backup snapshots EMERGENCY_BACKUP_E5_*"
oci bv boot-volume-backup list -c "$TENANCY" --boot-volume-id "$ORPHAN" --all 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
for b in d.get('data',[]):
    if b.get('display-name','').startswith('EMERGENCY_BACKUP_E5_'):
        print(b['id'])
" | while read -r BACKUP_ID; do
    log "  deleting backup: ${BACKUP_ID: -25}"
    oci bv boot-volume-backup delete --boot-volume-backup-id "$BACKUP_ID" --force 2>&1 | tee -a "$LOG"
done

# 3. Verify orphan still exists
log "STEP 3: verify orphan still alive"
ORPHAN_STATE=$(oci bv boot-volume get --boot-volume-id "$ORPHAN" 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["lifecycle-state"])' 2>/dev/null || echo "GONE")
log "  orphan state: $ORPHAN_STATE"
if [ "$ORPHAN_STATE" != "AVAILABLE" ]; then
    log "  CRITICAL: orphan no longer AVAILABLE. We may have deleted the wrong thing!"
    log "  CHECK Drive + phone copies are intact before doing anything else."
    exit 1
fi

# 4. Storage cap check
log "STEP 4: storage cap check"
TOTAL=$(oci bv boot-volume list -c "$TENANCY" --availability-domain "$AD" --all 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
total=sum(v.get('size-in-gbs',0) for v in d.get('data',[]) if v.get('lifecycle-state')!='TERMINATED')
print(total)
" 2>/dev/null)
log "  current Oracle storage: ${TOTAL}GB / 200GB cap"

# 5. Slack notify
log "STEP 5: Slack notify"
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
        title="3-2-1 Cleanup Complete",
        summary="Oracle duplicate copies deleted. Orphan + Drive + phone now hold the only redundancy. Real 3-2-1 architecture in place.",
        agent_name="Iron Stack",
        agent_title="DevOps",
    )
    print("Slack notified")
except Exception as e:
    print(f"slack err: {e}")
PYEOF

log "═══════════════════════════════════════════════════════════════"
log "  ORACLE DUPLICATE CLEANUP -- DONE"
log "═══════════════════════════════════════════════════════════════"
log "  3-2-1 architecture now active:"
log "    Copy 1: Oracle orphan (production access)"
log "    Copy 2: Google Drive (encrypted offsite)"
log "    Copy 3: Phone local /mnt/sdcard/_offsite_backups/"
log ""
log "  Storage freed: ~141GB of 200GB cap"
log "  Future ARM redeploy can clone fresh boot vols without hitting cap"
