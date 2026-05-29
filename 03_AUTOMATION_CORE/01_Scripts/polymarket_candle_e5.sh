#!/usr/bin/env bash
# Crypto 5-min candle lane runner -- e5-mother (PRIMARY). Runs EVERY MINUTE so it
# can enter late in each 5-min window. Settles finished windows by price feed +
# places bounded $2 paper bets on strong late momentum. NO REAL MONEY (paper).
set -u
ROOT=/home/ubuntu/AA_MY_DRIVE
DIR=$ROOT/06_DEVELOPMENT
ENV=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
LOG=$DIR/polymarket_agent/logs/candle.log
LOCK=/tmp/pm_candle.lock
mkdir -p "$(dirname "$LOG")"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then exit 0; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT
if [ -f "$ENV" ]; then export $(grep -E "^(ANTHROPIC_API_KEY|PERPLEXITY_API_KEY)=" "$ENV" | xargs) 2>/dev/null || true; fi
cd "$DIR" || exit 1
timeout 90 python3 -m polymarket_agent.main candle >> "$LOG" 2>&1
