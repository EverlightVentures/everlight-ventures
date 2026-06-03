#!/usr/bin/env bash
set -u
DIR=/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT
LOG=$DIR/kalshi_agent/logs/candle.log
LOCK=/tmp/kalshi_candle_phone.lock
mkdir -p "$(dirname "$LOG")"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then exit 0; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT
unset ANTHROPIC_API_KEY PERPLEXITY_API_KEY 2>/dev/null || true
cd "$DIR" && timeout 90 python3 -m kalshi_agent.main candle >> "$LOG" 2>&1
