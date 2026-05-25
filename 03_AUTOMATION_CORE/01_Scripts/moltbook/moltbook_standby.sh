#!/bin/bash
# ---------------------------------------------------------------------------
# Phone HOT-STANDBY for the Lucrex moltbook engagement loop.
#
# Failover doctrine (reference_infrastructure_hierarchy +
# feedback_offline_first_bidirectional_sync):
#   e5-mother = PRIMARY always-on executor.  Phone = STANDBY.
#     - mother UP   -> stand down immediately (mother owns it; no double-post).
#     - mother DOWN -> run the engagement cycle locally so Lucrex never goes
#                      dark just because mother/tailscale dropped.
#
# This is the piece the 2026-05-24 migration was missing: it disabled the
# phone crons and left "mother unreachable -> wait" as the only behaviour,
# turning mother into a new SPOF.  The standby gate restores the failover.
#
# Double-post safety in the brief failover/recovery overlap is handled by:
#   1. _lucrex_already_replied_after() -- re-reads the live thread first.
#   2. server-side isRead state -- shared across both hosts via the API.
#
# Usage (from cron):  moltbook_standby.sh once | proactive | post
# ---------------------------------------------------------------------------
set -uo pipefail

WS="/mnt/sdcard/AA_MY_DRIVE"
E5="e5-mother"                       # ssh alias (key+user in ~/.ssh/config)
MODE="${1:-once}"
ENGINE="$WS/03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py"
LOG="$WS/_logs/moltbook/standby.log"
SSH="ssh -o ConnectTimeout=6 -o BatchMode=yes"

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

# --- mother reachable? -> she owns engagement; phone stands down ------------
if timeout 10 $SSH "$E5" "echo ok" >/dev/null 2>&1; then
  exit 0
fi

# --- mother down -> phone takes over (best-effort failover) -----------------
case "$MODE" in
  once)      ARGS="--once" ;;
  proactive) ARGS="--proactive --max-posts 1" ;;
  post)      ARGS="--post --max-posts 1" ;;
  *)         ARGS="--once" ;;
esac

cd "$WS" || exit 0
log "mother DOWN -> phone failover: $ARGS"
# env -u ANTHROPIC_API_KEY forces the engine's file-first .env key load
# (a stale shell key once masked a rotation and burned the daemon 17h).
env -u ANTHROPIC_API_KEY /usr/bin/python3 "$ENGINE" $ARGS \
  >> "$WS/_logs/lucrex_engage_cron.log" 2>&1
log "failover cycle ($MODE) done rc=$?"
