#!/usr/bin/env bash
# sync_to_mother.sh -- phone-side push of workspace deltas to e5-mother.
#
# Mirrors the design of claude_sync_acemagician.sh but targets the Oracle
# always-on hub. The doctrine is "phone is workstation SOT; e5-mother is the
# always-on hub that holds the canonical copy for the rest of the family."
#
# Direction: phone /mnt/sdcard/AA_MY_DRIVE/  ->  e5-mother /home/ubuntu/AA_MY_DRIVE/
# Plus:      phone ~/.claude/.../memory/      ->  e5-mother ~/.claude/.../memory/
#
# Idempotent. Safe to run any time. Fired by start_hive.sh on phone boot;
# can also be triggered manually.
#
# Usage:
#   bash sync_to_mother.sh             # auto, conflict-preserving
#   bash sync_to_mother.sh --dry-run   # show what would move, no bytes
#   bash sync_to_mother.sh --verbose

set -uo pipefail

DRY=""
VERBOSE=""
for a in "$@"; do
  case "$a" in
    --dry-run)  DRY="--dry-run" ;;
    --verbose)  VERBOSE="-v" ;;
  esac
done

PHONE_WS="/mnt/sdcard/AA_MY_DRIVE"
MOTHER_TAILNET="100.125.115.95"
MOTHER_USER="ubuntu"
MOTHER_WS="/home/ubuntu/AA_MY_DRIVE"
SSH_KEY="/root/.ssh/github_deploy"

PHONE_MEM="/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"
MOTHER_MEM="/home/ubuntu/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"

TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PHONE_WS/_logs/network_sync"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sync_to_mother_$TS.log"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

SSH_OPT="ssh -i $SSH_KEY -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -o BatchMode=yes"

# ---------------------------------------------------------------------------
# 1. reachability gate -- skip cleanly if e5-mother offline
# ---------------------------------------------------------------------------
log "=== sync_to_mother start  target=$MOTHER_TAILNET dry=${DRY:-no} ==="
if ! $SSH_OPT "$MOTHER_USER@$MOTHER_TAILNET" "echo MOTHER_UP" 2>/dev/null | grep -q MOTHER_UP; then
  log "  e5-mother unreachable on tailnet -- skipping (will retry next boot)"
  exit 0
fi
log "  e5-mother reachable -- proceeding"

# ---------------------------------------------------------------------------
# 2. ensure remote dirs exist
# ---------------------------------------------------------------------------
$SSH_OPT "$MOTHER_USER@$MOTHER_TAILNET" \
  "mkdir -p '$MOTHER_WS' '$MOTHER_MEM'" 2>/dev/null

# ---------------------------------------------------------------------------
# 3. workspace push (one-way, conflict-preserving via --backup)
# ---------------------------------------------------------------------------
QUAR_REMOTE="$MOTHER_WS/_sync_conflicts_quarantine_from_phone_$TS"
log "workspace -> $MOTHER_TAILNET:$MOTHER_WS"

rsync $DRY $VERBOSE -az --update --backup --backup-dir="$QUAR_REMOTE" \
  --exclude '_logs/' \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '08_BACKUPS/_frozen_snapshots/' \
  --exclude '_sync_conflicts_quarantine_*/' \
  --exclude '04_MEDIA_LIBRARY/' \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$PHONE_WS/" "$MOTHER_USER@$MOTHER_TAILNET:$MOTHER_WS/" 2>&1 \
  | tail -8 | tee -a "$LOG"

# ---------------------------------------------------------------------------
# 4. memory push (one-way; doctrine, feedback rules, references)
# ---------------------------------------------------------------------------
log "memory -> $MOTHER_TAILNET:$MOTHER_MEM"
rsync $DRY $VERBOSE -az --update \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$PHONE_MEM/" "$MOTHER_USER@$MOTHER_TAILNET:$MOTHER_MEM/" 2>&1 \
  | tail -3 | tee -a "$LOG"

# ---------------------------------------------------------------------------
# 5. PULL memory data files FROM mother (defense-in-depth, never lose memory)
#    -- Blinko SQLite live DB
#    -- agentmemory knowledge graph
#    -- yesterday's snapshots (in case the live file got corrupted)
# ---------------------------------------------------------------------------
log "memory PULL <- $MOTHER_TAILNET (Blinko DB + agentmemory graph)"
mkdir -p "$PHONE_WS/_state" "$PHONE_WS/08_BACKUPS/mother_snapshots"

# Live files first (latest state)
# sdcard FAT filesystem doesn't support chmod/chown -- strip perms to avoid noise
RSYNC_SDCARD="-rtz --update --no-perms --no-owner --no-group --no-times"

rsync $DRY $VERBOSE $RSYNC_SDCARD \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/e5_data/blinko_lite.db" \
  "$PHONE_WS/_state/blinko_lite.db" 2>&1 | tail -2 | tee -a "$LOG"

rsync $DRY $VERBOSE $RSYNC_SDCARD \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/e5_data/agentmemory_graph.json" \
  "$PHONE_WS/_state/agentmemory_graph.json" 2>&1 | tail -2 | tee -a "$LOG"

# Rolling 14-day snapshots (defense if live file is bad)
rsync $DRY $VERBOSE $RSYNC_SDCARD --delete-excluded \
  --include='blinko_*.db' --include='agentmemory_*.json' --exclude='*' \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/blinko_backups/" \
  "$PHONE_WS/08_BACKUPS/mother_snapshots/" 2>&1 | tail -3 | tee -a "$LOG"

# ---------------------------------------------------------------------------
# 6. record handshake
# ---------------------------------------------------------------------------
date -Iseconds > "$PHONE_WS/_state/last_mother_sync.txt"
log "=== sync_to_mother done -- log: $LOG ==="
