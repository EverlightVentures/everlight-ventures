#!/usr/bin/env bash
# Kalshi edge hunter -- scans allowed (crypto) markets, LOGS what it would trade.
# Dry-run (no --live) until the exposure guard is added + edges proven, then small-live.
set -u
DIR=/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT
LOG=$DIR/kalshi_agent/logs/hunt.log
LOCK=/tmp/kalshi_hunt.lock
mkdir -p "$(dirname "$LOG")"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then exit 0; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT
cd "$DIR" && echo "--- hunt $(date -u +%FT%TZ) ---" >> "$LOG"
timeout 120 python3 -m kalshi_agent.hunt_kalshi >> "$LOG" 2>&1
