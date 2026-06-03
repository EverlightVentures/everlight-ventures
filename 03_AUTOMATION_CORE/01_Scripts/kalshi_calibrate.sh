#!/usr/bin/env bash
# Polymarket PAPER calibration runner. Runs one full paper cycle:
# scan real markets -> gather signals -> predict (Claude) -> risk -> paper-bet
# -> SETTLE resolved bets -> accumulate calibration data (Brier/win-rate).
#
# NO REAL MONEY: paper mode uses fake fills. This runs the 20-trade calibration
# gate that must clear (Brier<0.25, win>52%) before any live cutover.
#
# Interim home = phone (runs when awake). Proper home = e5-mother 24/7
# (deploy via deploy_to_oracle.sh polymarket once tailnet is reachable).
set -u
DIR="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT"
LOG="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/kalshi_agent/logs/calibrate.log"
LOCK="/tmp/kalshi_calibrate.lock"
mkdir -p "$(dirname "$LOG")"

# HOST OWNERSHIP (fixed 2026-06-02 after a 4-day split-brain gap):
# The OLD logic SSH-pinged e5 and SKIPPED if e5 merely *answered* -- assuming e5
# ran the cycle. But e5 never had this cron installed, so every "e5 is up" skip
# meant NOBODY ran it -> 4 days, 0 paper trades. (And from the phone proot the
# SSH check itself hangs ~50s on a tailnet timeout.) So: the phone OWNS the value
# lane directly, lock-protected against self-overlap. Coordinated phone<->e5
# failover is reinstated ONLY once e5 runs this cron AND writes a freshness
# heartbeat we can verify (a reachable SSH echo != "the cycle actually ran").
# TODO(e5): re-enable defer when an e5 calibrate_heartbeat file is fresh (<35m).

# single-instance lock (skip if a run is in flight)
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "$(date -u +%FT%TZ) skip: already running" >> "$LOG"; exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# Use the .env keys (loader prefers the file), not any stale ambient key.
unset ANTHROPIC_API_KEY PERPLEXITY_API_KEY 2>/dev/null || true

cd "$DIR" || exit 1
echo "$(date -u +%FT%TZ) === paper calibration cycle ===" >> "$LOG"
timeout 300 python3 -m kalshi_agent.main paper >> "$LOG" 2>&1
echo "$(date -u +%FT%TZ) cycle done (exit $?)" >> "$LOG"
