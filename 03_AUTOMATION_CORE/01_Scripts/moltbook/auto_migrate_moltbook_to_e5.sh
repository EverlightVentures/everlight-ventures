#!/bin/bash
# ---------------------------------------------------------------------------
# Auto-migration guard for the moltbook engagement loop (phone cron, every
# 30 min). Idempotent + self-healing. Three outcomes:
#
#   1. mother unreachable        -> silent exit (wait for tailscale/mother).
#   2. migrated + engine present -> CODE-ONLY re-sync (dev->prod mirror, like
#                                   xlm-bot auto-deploy). NEVER touches mother's
#                                   runtime _state (seen-set/dm_pending) -- that
#                                   would clobber prod and cause double-replies.
#   3. not migrated (or mother wiped) -> FULL migration via
#                                   deploy_moltbook_to_e5.sh, then disable the
#                                   phone engage crons + write sentinel + alert.
#
# Wired 2026-05-24 per operator: "add a small phone cron that auto runs that
# migration." See [[reference_infrastructure_hierarchy]] + punchlist C#31.
# ---------------------------------------------------------------------------
set -uo pipefail

WS="/mnt/sdcard/AA_MY_DRIVE"
E5="e5-mother"                       # ssh alias (key+user in ~/.ssh/config)
REMOTE_WS="/home/ubuntu/AA_MY_DRIVE"
SENTINEL="$WS/_state/moltbook/.migrated_to_e5"
LOG="$WS/_logs/moltbook/auto_migrate.log"
DEPLOY="$WS/03_AUTOMATION_CORE/01_Scripts/moltbook/deploy_moltbook_to_e5.sh"
REMOTE_ENGINE="$REMOTE_WS/03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py"
SSH="ssh -o ConnectTimeout=8 -o BatchMode=yes"

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

# 1. reachable?
if ! timeout 14 $SSH "$E5" "echo ok" >/dev/null 2>&1; then
  log "mother unreachable; waiting"
  exit 0
fi

remote_has_engine=0
timeout 14 $SSH "$E5" "test -f $REMOTE_ENGINE" >/dev/null 2>&1 && remote_has_engine=1

# 3. needs full migration
if [ ! -f "$SENTINEL" ] || [ "$remote_has_engine" -eq 0 ]; then
  log "full migration needed (sentinel=$( [ -f "$SENTINEL" ] && echo yes || echo no ), engine=$remote_has_engine)"
  if bash "$DEPLOY" >> "$LOG" 2>&1; then
    # disable phone engage crons (idempotent -- comment any live ones)
    crontab -l 2>/dev/null | sed -E 's#^([^#].*lucrex_engage\.py.*)#\# [migrated-to-e5] \1#' | crontab -
    printf '{"migrated_utc":"%s","target":"%s:%s","by":"auto_migrate"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$E5" "$REMOTE_WS" > "$SENTINEL"
    log "full migration OK; phone engage crons disabled; sentinel written"
  else
    log "full migration FAILED; will retry next run"
  fi
  exit 0
fi

# 2. already migrated -> keep mother's CODE fresh (no state, no --delete on state)
RSYNC="rsync -az -e \"$SSH\""
changed=0
for p in \
  "03_AUTOMATION_CORE/01_Scripts/moltbook/" \
  "03_AUTOMATION_CORE/01_Scripts/content_tools/" \
  "03_AUTOMATION_CORE/01_Scripts/blinko_queue_drain.py"; do
  # --exclude state dirs that may sit under moltbook/ -- code only
  out=$(rsync -az -i --exclude='__pycache__' -e "$SSH" \
        "$WS/$p" "$E5:$REMOTE_WS/$p" 2>>"$LOG")
  [ -n "$out" ] && changed=1
done
[ "$changed" -eq 1 ] && log "code re-sync pushed updates to mother" || true

# 2b. cron drift self-heal: if mother is missing a current cron (e.g. the
# --post broadcast cron added after migration), re-run the full deploy. It is
# idempotent and reinstalls the complete cron set. Cheap grep, runs only when
# a known-expected cron line is absent on mother.
if ! timeout 14 $SSH "$E5" "crontab -l 2>/dev/null | grep -q 'lucrex_engage.py --post'"; then
  log "mother crontab missing --post cron -> re-running deploy to reinstall cron set"
  bash "$DEPLOY" >> "$LOG" 2>&1 && log "cron drift healed via deploy" || log "deploy re-run failed"
fi
exit 0
