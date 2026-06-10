#!/usr/bin/env bash
# tn_deal_engine.sh -- daily Tennessee deal-engine launcher with HOST HIERARCHY.
# Rich's doctrine: "if the Oracle's on we use Oracle, if not, it falls back to the phone."
# Order: e5-mother (the always-on AI host) when reachable -> phone (workspace SOT) fallback.
# The engine (tn_deal_tracker.py) is read/track only -- it never sends email (send is
# halt-gated + branded_mailer). Safe to cron.
set -uo pipefail

WS="/mnt/sdcard/AA_MY_DRIVE"
ENGINE_REL="01_BUSINESSES/Everlight_Ventures/Wholesale/scripts/tn_deal_tracker.py"
LOG="$WS/_logs/tn_deal_engine.log"
mkdir -p "$WS/_logs"
ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }

# e5-mother reachable? (mirror of deploy_to_oracle.sh e5_up gate)
e5_up() {
  curl -s -m 4 -o /dev/null "http://e5-mother:1111/health" 2>/dev/null && return 0
  ssh -o ConnectTimeout=4 -o BatchMode=yes e5-mother true 2>/dev/null && return 0
  return 1
}

run_phone() {
  echo "[$(ts)] HOST=phone -- running $ENGINE_REL" >> "$LOG"
  cd "$WS" && python3 "$ENGINE_REL" --enrich 15 >> "$LOG" 2>&1
  # Hermes people-search pass -- frugal: only fires the real browser executor when a
  # browser-use cloud key (free tier) or e5 Chromium is configured. No executor = no-op.
  if [ -n "${BROWSER_USE_API_KEY:-}" ] || [ "${HERMES_E5_CHROMIUM:-}" = "1" ]; then
    python3 "$WS/01_BUSINESSES/Everlight_Ventures/Wholesale/skip_trace/hermes_harness.py" --run --limit 15 >> "$LOG" 2>&1
  fi
}

run_e5() {
  # Requires the wholesale tree synced to e5 (~/AA_MY_DRIVE). Falls back to phone on any failure.
  echo "[$(ts)] HOST=e5-mother -- attempting remote run" >> "$LOG"
  ssh -o ConnectTimeout=6 -o BatchMode=yes e5-mother \
    "test -f ~/AA_MY_DRIVE/$ENGINE_REL && cd ~/AA_MY_DRIVE && python3 $ENGINE_REL --enrich 15" >> "$LOG" 2>&1
}

if e5_up; then
  if ! run_e5; then
    echo "[$(ts)] e5 run failed/absent -- falling back to phone" >> "$LOG"
    run_phone
  fi
else
  echo "[$(ts)] e5-mother unreachable -- using phone" >> "$LOG"
  run_phone
fi
echo "[$(ts)] done." >> "$LOG"
