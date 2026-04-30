#!/usr/bin/env bash
# sdcard_sync_to_drive.sh
# ──────────────────────
# Pushes the entire phone workspace to encrypted Drive on schedule.
# Only delta (changed files) goes up after the initial sync.
#
# Excludes regenerable junk (.git, node_modules, venv, .cache, large
# binaries that don't need backup) to fit comfortably in 15GB free Drive.
#
# Recovery: pulled back via rclone copy from drive_everlight_crypt.
#
# Cron entry (recommend hourly):
#   0 * * * * /usr/bin/env bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/sdcard_sync_to_drive.sh >> /mnt/sdcard/AA_MY_DRIVE/_logs/sdcard_sync.log 2>&1
set -euo pipefail

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/sdcard_sync.log
SOURCE=/mnt/sdcard/AA_MY_DRIVE
DEST_REMOTE=drive_everlight_crypt:phone_workspace
EXCLUDE_FILE=/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/.rclone_sdcard_exclude

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

# Build exclude list (regenerable / huge stuff that wastes Drive quota)
cat > "$EXCLUDE_FILE" <<'EOF'
.git/**
**/node_modules/**
**/__pycache__/**
**/.next/**
**/dist/**
**/build/**
**/venv/**
**/.venv/**
**/.cache/**
**/.tmp/**
**/_logs/oracle_watchdog.log
**/_logs/*.log
.DS_Store
**/.idea/**
**/.vscode/**
**/storybook-static/**
**/coverage/**
**/.pytest_cache/**
**/*.pyc
**/*.tmp
**/*.lock
**/yarn.lock
**/package-lock.json
**/pnpm-lock.yaml
**/Cargo.lock
**/go.sum
EOF

if ! command -v rclone >/dev/null 2>&1; then
    log "FAIL: rclone not installed"
    exit 1
fi

if ! rclone listremotes 2>/dev/null | grep -q "drive_everlight_crypt:"; then
    log "FAIL: drive_everlight_crypt remote not configured"
    exit 1
fi

log "═══════════════════════════════════════════════════════════════"
log "  SDCARD → DRIVE encrypted sync starting"
log "═══════════════════════════════════════════════════════════════"
log "Source: $SOURCE"
log "Dest:   $DEST_REMOTE (encrypted)"

# Use sync = makes destination match source (deletes Drive files no longer on phone)
# If you want pure additive (never delete), use 'copy' instead of 'sync'
rclone sync "$SOURCE" "$DEST_REMOTE" \
    --exclude-from "$EXCLUDE_FILE" \
    --transfers 4 \
    --checkers 8 \
    --tpslimit 10 \
    --tpslimit-burst 20 \
    --stats-one-line \
    --stats 30s \
    --log-level INFO \
    2>&1 | tee -a "$LOG" | tail -10

# Summary
SIZE=$(rclone size "$DEST_REMOTE" 2>&1 | grep "Total size" | head -1)
log "  ✓ Sync done: $SIZE"
log "═══════════════════════════════════════════════════════════════"
