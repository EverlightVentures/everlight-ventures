#!/usr/bin/env bash
# =============================================================================
# THE CROWN -- Alley Kingz daily art daemon
# -----------------------------------------------------------------------------
# Paints the MAX free-Leonardo allotment EVERY day, no matter what, and ships it
# to the live game (alley-kingz.pages.dev). Built as a self-healing DAEMON LOOP
# -- not a crontab entry -- because crond is NOT installed on this phone
# (start_hive.sh's `crond || cron` fails silently); the watchdog daemons that DO
# work here are all nohup loops. The Crown copies that proven pattern.
#
# Behaviour:
#   * Leonardo's free quota resets at 00:00 UTC, so the daily counter keys on the
#     UTC date. The loop re-checks every CROWN_SHORT seconds, so it auto-catches-up
#     the first time the phone is awake after a reset -- surviving phone sleep.
#   * Idempotent: art_factory.py skips already-painted assets; we only deploy when
#     something new was actually painted, and never paint past CROWN_DAILY_MAX/day.
#   * Correct deploy: cf_pages_direct_upload.py --project alley-kingz (NOT
#     deploy_to_oracle.sh, which targets the XLM/Oracle box, not the game).
#
# Tunables (env): CROWN_DAILY_MAX (soft daily cap), CROWN_BATCH (per-pass),
#                 CROWN_SHORT (sleep while productive), CROWN_LONG (sleep when idle).
# Start:  nohup bash ak_crown_daemon.sh >/dev/null 2>&1 &
# Singleton-guarded so start_hive.sh can call it on every boot safely.
# =============================================================================
set -uo pipefail
ROOT=/mnt/sdcard/AA_MY_DRIVE
ENVF=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
ART=$ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/art
GAME=$ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game
DEPLOY=$ROOT/03_AUTOMATION_CORE/01_Scripts/deploy/cf_pages_direct_upload.py
LOG=$ROOT/_logs/ak_crown_daemon.log
STATE=$ROOT/_state/ak_crown_state.json
LOCK=$ROOT/_state/ak_crown.lock

DAILY_MAX=${CROWN_DAILY_MAX:-60}     # soft cap; real limiter is Leonardo quota (handled gracefully)
BATCH=${CROWN_BATCH:-12}             # images per drain pass
SHORT=${CROWN_SHORT:-1200}           # 20 min between passes while there is work
LONG=${CROWN_LONG:-3600}             # 1 h backoff when quota hit / nothing to paint

mkdir -p "$ROOT/_logs" "$ROOT/_state"
log(){ echo "[$(date '+%F %T %Z')] $*" >> "$LOG"; }

# ---- singleton guard: if a live Crown is already looping, exit quietly ----
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

count_png(){ find "$GAME/assets" -name '*.png' ! -size 0 2>/dev/null | wc -l | tr -d ' '; }  # REAL art only -- 0-byte stubs never count as "made"
utc_day(){ date -u +%F; }

# painted-today counter persisted across restarts (resets on UTC day rollover)
painted_today(){ python3 - "$STATE" "$(utc_day)" <<'PY' 2>/dev/null || echo 0
import json,sys
try: s=json.load(open(sys.argv[1]))
except Exception: s={}
print(s.get('painted',0) if s.get('date')==sys.argv[2] else 0)
PY
}
set_painted(){ python3 - "$STATE" "$(utc_day)" "$1" <<'PY' 2>/dev/null
import json,sys
json.dump({'date':sys.argv[2],'painted':int(sys.argv[3])}, open(sys.argv[1],'w'))
PY
}

log "CROWN daemon up (pid $$) DAILY_MAX=$DAILY_MAX BATCH=$BATCH SHORT=${SHORT}s LONG=${LONG}s"
while true; do
  export LEONARDO_API_KEY=$(grep -m1 '^LEONARDO_API_KEY=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
  done=$(painted_today)
  if [ "$done" -ge "$DAILY_MAX" ]; then
    log "daily max reached ($done/$DAILY_MAX) -- idling until UTC reset"
    sleep "$LONG"; continue
  fi
  lim=$(( DAILY_MAX - done )); [ "$lim" -gt "$BATCH" ] && lim=$BATCH
  before=$(count_png)
  ( cd "$ART" && python3 art_factory.py --limit "$lim" >> "$LOG" 2>&1 )
  after=$(count_png); made=$(( after - before ))
  if [ "$made" -gt 0 ]; then
    set_painted $(( done + made ))
    log "painted +$made (today $(painted_today)/$DAILY_MAX, total pngs $after) -- deploying to alley-kingz.pages.dev"
    # shellcheck disable=SC1090
    set -a; . "$ENVF" 2>/dev/null; set +a
    ( cd "$GAME" && python3 "$DEPLOY" --dir . --project alley-kingz --branch main >> "$LOG" 2>&1 ) \
      && log "deploy OK" || log "deploy FAILED (art saved locally, will re-ship next pass)"
    sleep "$SHORT"
  else
    log "nothing painted this pass (quota hit or set complete) -- backing off ${LONG}s"
    sleep "$LONG"
  fi
done
