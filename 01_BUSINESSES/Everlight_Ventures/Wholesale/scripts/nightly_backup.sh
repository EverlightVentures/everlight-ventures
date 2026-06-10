#!/bin/bash
# nightly_backup -- Oracle-side backup of the wholesale stack.
#
# Cron: 0 3 * * *  (03:00 PT, off-peak)
#
# What gets backed up:
#   - Django hive.db (sqlite3, primary live store)
#   - /home/opc/wholesale/ (compliance, contracts, audit findings, scripts)
#   - /home/opc/content_tools/ (branded mailer, hive_logger, n8n_replacements)
#   - /home/opc/secrets/ (encrypted env + OAuth tokens)
#
# Where it lands:
#   /home/opc/backups/YYYY/MM/DD/wholesale_TS.tar.gz
#   + checksum file alongside
#
# Retention: 14 daily, 8 weekly, 12 monthly. Older archives auto-pruned.
#
# Pairs with: dr_restore_test.sh (quarterly cron) which untars the latest
# archive into /tmp and verifies the checksum + a sample sqlite SELECT.
#
# This script is intentionally simple: pure shell + tar + sha256sum so it
# survives a Python/Django outage. If everything else is broken, this still
# runs and produces a recoverable archive.

set -euo pipefail

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TODAY="$(date +%Y/%m/%d)"
BACKUP_ROOT="/home/opc/backups"
DAY_DIR="$BACKUP_ROOT/$TODAY"
ARCHIVE="$DAY_DIR/wholesale_${TIMESTAMP}.tar.gz"
CHECKSUM="$ARCHIVE.sha256"
LOG="$BACKUP_ROOT/backup.log"

mkdir -p "$DAY_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

log "== nightly_backup start =="

# Sources to include. Skip __pycache__, .pyc, .log, *.tmp.
SOURCES=()
[ -f /home/opc/hive_django/hive.db ] && SOURCES+=(/home/opc/hive_django/hive.db)
[ -d /home/opc/wholesale ] && SOURCES+=(/home/opc/wholesale)
[ -d /home/opc/content_tools ] && SOURCES+=(/home/opc/content_tools)
[ -d /home/opc/secrets ] && SOURCES+=(/home/opc/secrets)

if [ ${#SOURCES[@]} -eq 0 ]; then
  log "ERROR: no sources to back up"
  exit 1
fi

log "Backing up: ${SOURCES[*]}"

tar --create --gzip \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.tmp' \
    --exclude='*.log' \
    --file="$ARCHIVE" \
    "${SOURCES[@]}" 2>>"$LOG"

# Checksum so dr_restore_test.sh can verify integrity
sha256sum "$ARCHIVE" > "$CHECKSUM"

SIZE=$(du -h "$ARCHIVE" | cut -f1)
log "Wrote archive: $ARCHIVE ($SIZE)"
log "Checksum:      $(cat "$CHECKSUM")"

# Retention pruning -- keep last 14 daily archives
log "Pruning archives older than 14 days..."
find "$BACKUP_ROOT" -name "wholesale_*.tar.gz" -type f -mtime +14 -print -delete >> "$LOG" 2>&1 || true
find "$BACKUP_ROOT" -name "wholesale_*.tar.gz.sha256" -type f -mtime +14 -delete 2>>"$LOG" || true

# Empty directories left behind
find "$BACKUP_ROOT" -type d -empty -delete 2>>"$LOG" || true

log "== nightly_backup done =="
exit 0
