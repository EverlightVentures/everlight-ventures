#!/usr/bin/env bash
# phone_pull_321_from_drive.sh
# ────────────────────────────
# Runs on phone via cron every 1 hour. Pulls latest oracle_e5_backup
# folder from Drive into /mnt/sdcard/AA_MY_DRIVE/_offsite_backups/oracle_e5/
# This is the "1" in the 3-2-1 backup rule (offsite local).
#
# Cron entry:
#   0 * * * * /usr/bin/env bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/phone_pull_321_from_drive.sh >> /mnt/sdcard/AA_MY_DRIVE/_logs/phone_pull_321.log 2>&1
set -euo pipefail

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/phone_pull_321.log
DEST=/mnt/sdcard/AA_MY_DRIVE/_offsite_backups/oracle_e5
mkdir -p "$DEST" "$(dirname "$LOG")"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

if ! command -v rclone >/dev/null 2>&1; then
    log "FAIL: rclone not installed. Run setup_rclone_drive.sh first."
    exit 1
fi

if ! rclone listremotes 2>/dev/null | grep -q "drive_everlight:"; then
    log "FAIL: drive_everlight remote not configured. Run setup_rclone_drive.sh."
    exit 1
fi

log "Starting Drive→phone sync..."

# Find the latest oracle_e5_backup_* folder on Drive
LATEST=$(rclone lsd drive_everlight_crypt:oracle_e5_backups 2>/dev/null | grep -oE 'oracle_e5_backup_[0-9TZ]+' | sort | tail -1)
if [ -z "$LATEST" ]; then
    log "  no oracle_e5_backup_* folder found on Drive yet"
    exit 0
fi
log "  latest Drive backup: $LATEST"

# Sync to phone (only newer files; deletes nothing locally)
rclone copy --transfers 4 --no-update-modtime \
    "drive_everlight_crypt:oracle_e5_backups/$LATEST/" \
    "$DEST/$LATEST/" \
    2>&1 | tee -a "$LOG" | tail -20

# Compute size
SIZE=$(du -sh "$DEST/$LATEST/" 2>/dev/null | cut -f1)
COUNT=$(find "$DEST/$LATEST/" -type f 2>/dev/null | wc -l)
log "  ✓ pulled: $SIZE / $COUNT files"
log "  local path: $DEST/$LATEST/"

# Update the "latest" symlink
ln -sfn "$DEST/$LATEST" "$DEST/latest"
log "  symlink: $DEST/latest -> $LATEST"
