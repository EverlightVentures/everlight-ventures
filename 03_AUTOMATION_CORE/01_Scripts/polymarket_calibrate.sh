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
LOG="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/polymarket_agent/logs/calibrate.log"
LOCK="/tmp/polymarket_calibrate.lock"
mkdir -p "$(dirname "$LOG")"

# ACTIVE-PASSIVE FAILOVER: e5-mother is the primary mother hub. The phone runs
# this ONLY when e5 is unreachable. If e5 answers, it owns the cycle -> skip
# (prevents double-running / paper-state divergence across hosts).
# Generous timeout: e5 tailnet SSH handshake can take >8s under load. Only treat
# e5 as DOWN after a real failure -- a false-failover would fork the ledger.
# Retry twice before declaring e5 down.
e5_up() {
  for _ in 1 2; do
    if timeout 25 ssh -o ConnectTimeout=18 -o StrictHostKeyChecking=no \
         -i /root/.ssh/github_deploy e5-mother "echo up" >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  return 1
}
if e5_up; then
  echo "$(date -u +%FT%TZ) skip: e5 (primary) is up, it owns the cycle" >> "$LOG"; exit 0
fi
echo "$(date -u +%FT%TZ) e5 DOWN (2 tries) -> phone failover taking the cycle" >> "$LOG"

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
timeout 300 python3 -m polymarket_agent.main paper >> "$LOG" 2>&1
echo "$(date -u +%FT%TZ) cycle done (exit $?)" >> "$LOG"
