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
# 5. PULL all cloud state to phone-local mirror
#    Per HARD LAW feedback_cloud_state_mirrors_local_always:
#    Every piece of cloud-only state has a phone mirror within 24h of write.
# ---------------------------------------------------------------------------
log "cloud-state PULL <- $MOTHER_TAILNET"
mkdir -p "$PHONE_WS/_state" \
         "$PHONE_WS/_state/cloud_mirror" \
         "$PHONE_WS/_state/cloud_mirror_secrets" \
         "$PHONE_WS/_state/cloud_mirror/systemd_units" \
         "$PHONE_WS/_state/cloud_mirror/app_dbs" \
         "$PHONE_WS/08_BACKUPS/mother_snapshots"
chmod 700 "$PHONE_WS/_state/cloud_mirror_secrets" 2>/dev/null || true

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

# 5b. ENV files (sensitive -- to cloud_mirror_secrets/, .gitignored)
log "  env-secrets PULL"
rsync $DRY $VERBOSE $RSYNC_SDCARD \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/e5_data/.env" \
  "$PHONE_WS/_state/cloud_mirror_secrets/e5_data.env" 2>&1 | tail -1 | tee -a "$LOG"
rsync $DRY $VERBOSE $RSYNC_SDCARD \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/e5_data/.env.wholesale" \
  "$PHONE_WS/_state/cloud_mirror_secrets/e5_data.env.wholesale" 2>&1 | tail -1 | tee -a "$LOG"

# 5c. /etc/default/ secrets (need sudo to read; use temp staging)
log "  /etc/default + /etc/mcp secrets PULL"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$MOTHER_USER@$MOTHER_TAILNET" \
  "sudo cat /etc/default/rex-negotiator > /tmp/rex-neg.staged 2>/dev/null; \
   sudo cat /etc/default/hive-action-engine > /tmp/hive-ae.staged 2>/dev/null; \
   sudo cat /etc/mcp/dispatcher_relay.env > /tmp/dispatcher_relay.staged 2>/dev/null; \
   sudo cat /etc/mcp/hive_relay.env > /tmp/hive_relay.staged 2>/dev/null; \
   sudo chown ubuntu:ubuntu /tmp/*.staged" 2>/dev/null
for src in rex-neg hive-ae dispatcher_relay hive_relay; do
  rsync $DRY $RSYNC_SDCARD \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
    "$MOTHER_USER@$MOTHER_TAILNET:/tmp/$src.staged" \
    "$PHONE_WS/_state/cloud_mirror_secrets/$src" 2>&1 | tail -1 | tee -a "$LOG"
done
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$MOTHER_USER@$MOTHER_TAILNET" \
  "rm -f /tmp/*.staged" 2>/dev/null

# 5d. /etc/systemd/system/*.{service,timer} unit files (non-sensitive, in workspace mirror)
log "  systemd unit files PULL"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$MOTHER_USER@$MOTHER_TAILNET" \
  "sudo tar czf /tmp/units.tgz -C /etc/systemd/system . 2>/dev/null && sudo chown ubuntu:ubuntu /tmp/units.tgz"
rsync $DRY $RSYNC_SDCARD \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/tmp/units.tgz" \
  "$PHONE_WS/_state/cloud_mirror/systemd_units/units_latest.tgz" 2>&1 | tail -1 | tee -a "$LOG"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$MOTHER_USER@$MOTHER_TAILNET" \
  "rm -f /tmp/units.tgz" 2>/dev/null

# 5e. App state SQLite DBs (non-sensitive)
log "  app-db PULL (hive_dashboard + xlm-bot states)"
for db in "hive_django/db.sqlite3" "hive-ops/django/db.sqlite3" "_logs/cuyahoga_cache.sqlite3"; do
  name=$(echo "$db" | tr / _)
  rsync $DRY $RSYNC_SDCARD \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
    "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/e5_data/$db" \
    "$PHONE_WS/_state/cloud_mirror/app_dbs/$name" 2>&1 | tail -1 | tee -a "$LOG"
done

# 5f. OAuth tokens (sensitive)
log "  OAuth tokens PULL"
rsync $DRY $RSYNC_SDCARD \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$MOTHER_USER@$MOTHER_TAILNET:/home/ubuntu/e5_data/google_tokens.json" \
  "$PHONE_WS/_state/cloud_mirror_secrets/google_tokens.json" 2>&1 | tail -1 | tee -a "$LOG"

# ---------------------------------------------------------------------------
# 6. record handshake
# ---------------------------------------------------------------------------
date -Iseconds > "$PHONE_WS/_state/last_mother_sync.txt"
log "=== sync_to_mother done -- log: $LOG ==="
