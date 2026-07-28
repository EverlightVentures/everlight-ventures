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
#   * Engines (art_factory.py failover chain): Leonardo (API credits = PURCHASED,
#     exhausted 2026-06-10, no daily reset) -> CF Workers AI via CF_AI_TOKEN
#     (10k free neurons/day, ~100+ images). Daily counter keys on the UTC date;
#     the loop re-checks every CROWN_SHORT seconds, surviving phone sleep.
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


# ---- ship(): deploy the game to CF Pages -- e5 first (phone radio kills long
# uploads; 5 deploys died 2026-06-11, incl. a mid-deploy "Expired JWT"), local
# direct-upload as fallback. e5 kit at ~/ak_deploy (script + cf.env + game mirror).
ship(){
  if rsync -az --partial --timeout=60 "$GAME"/ e5:~/ak_deploy/game/ 2>>"$LOG" \
     && ssh -o ConnectTimeout=20 e5 'source ~/ak_deploy/cf.env && cd ~/ak_deploy && python3 cf_pages_direct_upload.py --dir game --project alley-kingz --branch main' >>"$LOG" 2>&1; then
    return 0
  fi
  log "e5 ship failed -- trying local direct upload"
  ( cd "$GAME" && python3 "$DEPLOY" --dir . --project alley-kingz --branch main >>"$LOG" 2>&1 )
}

log "CROWN daemon up (pid $$) DAILY_MAX=$DAILY_MAX BATCH=$BATCH SHORT=${SHORT}s LONG=${LONG}s"
while true; do
  export LEONARDO_API_KEY=$(grep -m1 '^LEONARDO_API_KEY=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
  # CF Workers AI fallback engine (Leonardo API credits = purchased, dead since 2026-06-10)
  export CF_AI_TOKEN=$(grep -m1 '^CF_AI_TOKEN=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
  done=$(painted_today)
  if [ "$done" -ge "$DAILY_MAX" ]; then
    # painted art (or code fixes) may still be stranded by a failed deploy --
    # keep retrying the ship even while the painter idles (flaky phone radio
    # killed 5 deploys on 2026-06-11; deploy retry must not wait for tomorrow)
    if [ -f "$ROOT/_state/ak_crown_need_deploy" ]; then
      log "daily max reached but a deploy is pending -- retrying ship"
      set -a; . "$ENVF" 2>/dev/null; set +a
      if ship; then
        rm -f "$ROOT/_state/ak_crown_need_deploy"; log "pending deploy SHIPPED"
      else
        log "pending deploy still failing -- will retry"
      fi
      sleep "$SHORT"; continue
    fi
    log "daily max reached ($done/$DAILY_MAX) -- idling until UTC reset"
    sleep "$LONG"; continue
  fi
  lim=$(( DAILY_MAX - done )); [ "$lim" -gt "$BATCH" ] && lim=$BATCH
  before=$(count_png)
  PASS=$(mktemp /tmp/ak_crown_pass.XXXXXX)
  ( cd "$ART" && python3 art_factory.py --limit "$lim" 2>&1 | tee "$PASS" >> "$LOG" )
  after=$(count_png); made=$(( after - before ))
  if [ "$made" -gt 0 ]; then
    set_painted $(( done + made ))
    log "painted +$made (today $(painted_today)/$DAILY_MAX, total pngs $after) -- deploying to alley-kingz.pages.dev"
    # BUILD LOG (operator visibility law 2026-06-11): publish what got painted to
    # game/updates.json -- ships with this same deploy, feeds the lobby ticker so
    # players see daily growth. Keeps last 60 entries.
    python3 - "$GAME/updates.json" "$PASS" <<'PY' 2>>"$LOG"
import json, sys, datetime
path, passlog = sys.argv[1], sys.argv[2]
ids = [l.split()[1] for l in open(passlog) if l.strip().startswith("PAINTED")]
left = ""
for l in open(passlog):
    if "still need art" in l: left = l.split("|")[-1].strip().split()[0]
try: u = json.load(open(path))
except Exception: u = []
now = datetime.datetime.now().astimezone()
u.insert(0, {"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M %Z"),
             "count": len(ids), "painted": ids, "remaining": left})
json.dump(u[:60], open(path, "w"), indent=1)
PY
    # shellcheck disable=SC1090
    set -a; . "$ENVF" 2>/dev/null; set +a
    if ship; then
      log "deploy OK"; rm -f "$ROOT/_state/ak_crown_need_deploy"
      # 1-line ops ping to #deploy-log (raw chat.postMessage is doctrine-OK for ops pings)
      LEFT=$(grep -oE '[0-9]+ still need art' "$PASS" | grep -oE '^[0-9]+' | head -1)
      IDS=$(grep -oE '^\s*PAINTED \S+' "$PASS" | awk '{print $2}' | head -12 | tr '\n' ' ')
      curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer ${SLACK_BOT_TOKEN:-}" -H "Content-Type: application/json" \
        -d "{\"channel\":\"C0AN4GSTMT5\",\"text\":\"AK art drop: +$made painted ($(painted_today)/$DAILY_MAX today, ${LEFT:-?} left) -> deployed to alleykingz.online. New: ${IDS}\"}" \
        >/dev/null 2>&1 || true
    else
      log "deploy FAILED (art saved locally, will re-ship next pass)"; touch "$ROOT/_state/ak_crown_need_deploy"
    fi
    rm -f "$PASS"
    sleep "$SHORT"
  else
    rm -f "$PASS"
    log "nothing painted this pass (quota hit or set complete) -- backing off ${LONG}s"
    sleep "$LONG"
  fi
done
