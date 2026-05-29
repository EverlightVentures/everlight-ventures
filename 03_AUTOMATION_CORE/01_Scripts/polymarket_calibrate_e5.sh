#!/usr/bin/env bash
# Polymarket PAPER calibration runner -- e5-mother (PRIMARY / mother hub).
# Self-updates from git each run so it is NOT dependent on a manual rsync from
# the phone (tailnet can flap). Runs one paper cycle: scan short-horizon markets
# -> signals -> Claude predict (both sides + convex lane) -> risk -> paper-bet
# -> settle resolved -> accumulate calibration (Brier/win-rate). NO REAL MONEY.
set -u
ROOT=/home/ubuntu/AA_MY_DRIVE
DIR=$ROOT/06_DEVELOPMENT
ENV=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
LOG=$DIR/polymarket_agent/logs/calibrate.log
LOCK=/tmp/pm_calib.lock
mkdir -p "$(dirname "$LOG")"

if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then exit 0; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

# Self-update code from git (best-effort; mirror may or may not be a git repo).
git -C "$ROOT" pull --ff-only >> "$LOG" 2>&1 || echo "$(date -u +%FT%TZ) git pull skipped" >> "$LOG"

# Keys: loader reads the local .env via paths.py; also export as belt-and-suspenders.
if [ -f "$ENV" ]; then
  export $(grep -E "^(ANTHROPIC_API_KEY|PERPLEXITY_API_KEY)=" "$ENV" | xargs) 2>/dev/null || true
fi

cd "$DIR" || exit 1
echo "$(date -u +%FT%TZ) === e5 paper calibration ===" >> "$LOG"
timeout 300 python3 -m polymarket_agent.main paper >> "$LOG" 2>&1
echo "$(date -u +%FT%TZ) done (exit $?)" >> "$LOG"
