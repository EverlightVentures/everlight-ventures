#!/usr/bin/env bash
# sync_conflict_resolver.sh
#
# Resolves Syncthing + .claude/ sync conflict files by archiving the conflicted
# versions to 08_BACKUPS/sync_conflicts_archive_<YYYY-MM-DD>/ and leaving the
# canonical workspace tree intact.
#
# Triggers (any of):
#   1. AceMagician udev rule on Z Fold 7 USB plug-in
#      (see install_acemagician_triggers.sh)
#   2. AceMagician hourly cron when phone visible on tailnet
#   3. Phone Termux boot script when AceMagician reachable
#   4. Manual: `bash sync_conflict_resolver.sh [--dry-run]`
#
# Safety:
#   - Reversible: never deletes, only MOVES to dated archive folder
#   - Skips the dashboard sqlite3 conflict (needs row-count comparison, manual)
#   - Logs every action with timestamps
#   - Posts summary to Slack #deploy-log via branded_slack if available
#
# Saved: 2026-05-15 -- in response to Rich's "write a script that auto-runs
# when I plug my phone into the AceMagician"
set -euo pipefail

# --- Locate workspace --------------------------------------------------------
# Workspace lives on sdcard on phone, mounted differently on PC.
# Auto-detect: try phone path first, then PC paths.
# 2026-08-06: /AA_MY_DRIVE is now the canonical PC tree and must be probed
# BEFORE the legacy /home/richgee one, which is being retired.
if [ -d "/mnt/sdcard/AA_MY_DRIVE" ]; then
    WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
elif [ -d "/AA_MY_DRIVE" ]; then
    WORKSPACE="/AA_MY_DRIVE"
elif [ -d "/home/richgee/AA_MY_DRIVE" ]; then
    WORKSPACE="/home/richgee/AA_MY_DRIVE"   # legacy, retired 2026-08-06
elif [ -d "$HOME/AA_MY_DRIVE" ]; then
    WORKSPACE="$HOME/AA_MY_DRIVE"
else
    echo "ERROR: workspace not found at known paths"
    exit 1
fi

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
fi

TODAY=$(date +%Y-%m-%d)
ARCHIVE_ROOT="$WORKSPACE/08_BACKUPS/sync_conflicts_archive_$TODAY"
LOG="$WORKSPACE/_logs/sync_conflict_resolver.log"
mkdir -p "$ARCHIVE_ROOT" "$(dirname "$LOG")"

log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S %Z')
    echo "[$ts] $*" | tee -a "$LOG"
}

log "===== sync_conflict_resolver START (host=$(hostname), workspace=$WORKSPACE, dry_run=$DRY_RUN) ====="

# --- Phase 1: Syncthing-style .sync-conflict-* files ------------------------
# Pattern: anywhere in workspace, files containing ".sync-conflict-" in name
# Skip: dashboard sqlite3 (manual row-count check)
# Skip: anything inside an existing archive dir
SYNCTHING_COUNT=0
SYNCTHING_BYTES=0
SKIPPED_DB=0

while IFS= read -r -d '' conflict_path; do
    rel_path="${conflict_path#$WORKSPACE/}"

    # Skip if already inside an archive
    case "$rel_path" in
        08_BACKUPS/*) continue ;;
        _sync_conflicts_quarantine_*) continue ;;
        .git/*) continue ;;
        */node_modules/*) continue ;;
    esac

    # Defer the dashboard sqlite3 -- needs manual row-count compare
    case "$rel_path" in
        *hive_dashboard/db.sync-conflict-*.sqlite3)
            log "SKIP (manual): $rel_path  -- dashboard sqlite needs row-count compare before archiving"
            SKIPPED_DB=$((SKIPPED_DB+1))
            continue
            ;;
    esac

    size=$(stat -c%s "$conflict_path" 2>/dev/null || echo 0)
    target_dir="$ARCHIVE_ROOT/$(dirname "$rel_path")"
    target_path="$ARCHIVE_ROOT/$rel_path"

    if [ "$DRY_RUN" = "1" ]; then
        log "DRY: would archive: $rel_path  ->  08_BACKUPS/sync_conflicts_archive_$TODAY/$rel_path ($size bytes)"
    else
        mkdir -p "$target_dir"
        mv "$conflict_path" "$target_path"
        log "ARCHIVED: $rel_path  ($size bytes)"
    fi
    SYNCTHING_COUNT=$((SYNCTHING_COUNT+1))
    SYNCTHING_BYTES=$((SYNCTHING_BYTES+size))
done < <(find "$WORKSPACE" -type f -name "*sync-conflict-*" -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/08_BACKUPS/*" -print0 2>/dev/null)

# --- Phase 2: .claude/.sync_conflicts/ timestamped directories --------------
DOT_COUNT=0
DOT_BYTES=0
DOT_CONFLICT_ROOT="$WORKSPACE/.claude/.sync_conflicts"
if [ -d "$DOT_CONFLICT_ROOT" ]; then
    for subdir in "$DOT_CONFLICT_ROOT"/*/; do
        [ -d "$subdir" ] || continue
        name=$(basename "$subdir")
        target="$ARCHIVE_ROOT/.claude/.sync_conflicts/$name"
        size=$(du -sb "$subdir" 2>/dev/null | awk '{print $1}')
        if [ "$DRY_RUN" = "1" ]; then
            log "DRY: would archive directory: .claude/.sync_conflicts/$name ($size bytes)"
        else
            mkdir -p "$(dirname "$target")"
            mv "$subdir" "$target"
            log "ARCHIVED dir: .claude/.sync_conflicts/$name  ($size bytes)"
        fi
        DOT_COUNT=$((DOT_COUNT+1))
        DOT_BYTES=$((DOT_BYTES+size))
    done
fi

# --- Phase 3: _sync_conflicts_quarantine_* root folders ---------------------
# These were already moved out of working tree on a prior run.
# Re-archive them to today's dated archive for organization.
QUARANTINE_COUNT=0
QUARANTINE_BYTES=0
for q_dir in "$WORKSPACE"/_sync_conflicts_quarantine_*/; do
    [ -d "$q_dir" ] || continue
    name=$(basename "$q_dir")
    target="$ARCHIVE_ROOT/$name"
    size=$(du -sb "$q_dir" 2>/dev/null | awk '{print $1}')
    if [ "$DRY_RUN" = "1" ]; then
        log "DRY: would archive quarantine dir: $name ($size bytes)"
    else
        mv "$q_dir" "$target"
        log "ARCHIVED quarantine dir: $name  ($size bytes)"
    fi
    QUARANTINE_COUNT=$((QUARANTINE_COUNT+1))
    QUARANTINE_BYTES=$((QUARANTINE_BYTES+size))
done

# --- Phase 4: Cleanup empty archive root if nothing moved -------------------
if [ "$DRY_RUN" != "1" ]; then
    if [ ! "$(ls -A "$ARCHIVE_ROOT" 2>/dev/null)" ]; then
        rmdir "$ARCHIVE_ROOT" 2>/dev/null || true
    fi
fi

# --- Summary ----------------------------------------------------------------
TOTAL=$((SYNCTHING_COUNT + DOT_COUNT + QUARANTINE_COUNT))
TOTAL_MB=$(awk -v b=$((SYNCTHING_BYTES + DOT_BYTES + QUARANTINE_BYTES)) 'BEGIN{printf "%.1f", b/1024/1024}')

log "===== SUMMARY (host=$(hostname), dry_run=$DRY_RUN) ====="
log "  Syncthing-style files: $SYNCTHING_COUNT ($(awk -v b=$SYNCTHING_BYTES 'BEGIN{printf "%.1f MB", b/1024/1024}'))"
log "  .claude/.sync_conflicts/ dirs: $DOT_COUNT ($(awk -v b=$DOT_BYTES 'BEGIN{printf "%.1f MB", b/1024/1024}'))"
log "  _sync_conflicts_quarantine_* dirs: $QUARANTINE_COUNT ($(awk -v b=$QUARANTINE_BYTES 'BEGIN{printf "%.1f MB", b/1024/1024}'))"
log "  Skipped (manual): dashboard sqlite3 = $SKIPPED_DB"
log "  TOTAL ARCHIVED: $TOTAL items, ${TOTAL_MB} MB"
log "  Archive root: $ARCHIVE_ROOT"

# --- Slack post (best-effort, fails silently) -------------------------------
if [ "$DRY_RUN" != "1" ] && [ "$TOTAL" -gt 0 ] && [ -f "$WORKSPACE/content_tools/branded_slack.py" ]; then
    cd "$WORKSPACE"
    python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from content_tools.branded_slack import post_branded_slack
    post_branded_slack(
        channel='#deploy-log',
        category='ops',
        title='Sync Conflicts Resolved',
        summary='Auto-resolver archived $TOTAL items (${TOTAL_MB} MB) on $(hostname).',
        body='Archived to 08_BACKUPS/sync_conflicts_archive_$TODAY/. Skipped $SKIPPED_DB dashboard sqlite for manual review.',
    )
    print('Slack posted')
except Exception as e:
    print(f'Slack skipped: {e}')
" 2>&1 | tee -a "$LOG" || true
fi

log "===== sync_conflict_resolver END ====="
exit 0
