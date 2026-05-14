#!/usr/bin/env bash
# sync_helper.sh -- PC side. The "acknowledger."
#
# Invoked by:
#   - adb_sync_trigger.sh when the phone connects over USB/ADB
#   - the phone's sync_finisher.sh over SSH (belt + suspenders)
#   - manually
#
# What it does (the PC "does something to acknowledge + help transfer"):
#   1. Ensures the PC's Syncthing systemd service is running
#   2. Blocks PC sleep/suspend for a transfer window (so a 30 GB pull can
#      actually finish instead of dying when the PC dozes)
#   3. Drops an ack file the phone side can see
#   4. Logs PC-side pull progress
#
# Idempotent + single-instance. Safe to call repeatedly -- each call
# refreshes the sleep-inhibit window.

set -u

WS="$HOME/AA_MY_DRIVE"
LOG="$HOME/sync_helper.log"
ACK="$WS/_logs/.sync_pc_ack"
INHIBIT_PID_FILE=/tmp/sync_helper_inhibit.pid
ST_SERVICE="syncthing-everlight.service"
INHIBIT_WINDOW=3600   # block sleep for 1h per call; phone re-calls to refresh

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; echo "[$(ts)] $*"; }

log "=== sync_helper invoked ==="

# ---- 1. ensure PC Syncthing service is up ----
if systemctl --user is-active "$ST_SERVICE" >/dev/null 2>&1; then
  log "PC Syncthing service: active"
else
  log "PC Syncthing service down -- starting"
  systemctl --user start "$ST_SERVICE" 2>&1 | tail -1 | sed 's/^/  /' >> "$LOG"
  sleep 4
fi

# ---- 2. block PC sleep for the transfer window ----
# Kill any stale inhibitor, start a fresh one in the background.
if [ -f "$INHIBIT_PID_FILE" ]; then
  oldpid=$(cat "$INHIBIT_PID_FILE" 2>/dev/null || true)
  [ -n "$oldpid" ] && kill "$oldpid" 2>/dev/null || true
fi
setsid systemd-inhibit --what=sleep:idle \
  --who="everlight-sync" --why="phone<->PC Syncthing catch-up" \
  sleep "$INHIBIT_WINDOW" >/dev/null 2>&1 &
echo $! > "$INHIBIT_PID_FILE"
log "sleep/idle inhibited for ${INHIBIT_WINDOW}s (pid $(cat "$INHIBIT_PID_FILE"))"

# ---- 3. drop the ack file (phone can see this via Syncthing once it lands) ----
mkdir -p "$(dirname "$ACK")"
{
  echo "pc_ack_at=$(ts)"
  echo "pc_host=$(hostname)"
  echo "syncthing=$(systemctl --user is-active "$ST_SERVICE" 2>/dev/null)"
  echo "inhibit_window_s=$INHIBIT_WINDOW"
} > "$ACK"
log "ack file written: $ACK"

# ---- 4. log PC-side pull progress (one snapshot; phone polls the rest) ----
if [ -d "$WS" ]; then
  SIZE=$(du -sh "$WS" 2>/dev/null | cut -f1)
  FILES=$(find "$WS" -type f 2>/dev/null | wc -l)
  log "PC workspace: $SIZE / $FILES files"
fi

log "=== sync_helper done -- PC acknowledged, awake, pulling ==="
echo "ACK:$(hostname):$(ts)"   # <-- this line is what the phone captures over SSH
