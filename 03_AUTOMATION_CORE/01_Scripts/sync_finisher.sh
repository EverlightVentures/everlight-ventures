#!/usr/bin/env bash
# sync_finisher.sh -- PHONE side. Auto-resumes + drives the phone->PC Syncthing
# transfer to 100% completion, then exits.
#
# What it does:
#   1. Single-instance lock (safe to call from cron every few minutes)
#   2. Ensures the phone's Syncthing is running (via the watchdog launcher)
#   3. Waits for the AceMagician PC to be reachable over the tailnet
#   4. SSHes into the PC and runs sync_helper.sh -- the PC "acknowledges" by
#      waking its Syncthing + blocking sleep for the transfer window
#   5. Polls the phone's Syncthing API for the PC's completion %
#   6. Logs progress; when the PC hits 100% it flips the phone folder to
#      sendreceive (true bidirectional) and exits clean
#
# Triggers (so it "auto-starts when the phone connects"):
#   - cron */5  -- checks conditions, runs if there's pending work
#   - Termux:Boot -- kicks once on phone power-on
#   - manual:  bash sync_finisher.sh
#
# Idempotent. Self-limiting (6h hard cap). Logs to _logs/sync_finisher.log

set -u

ROOT=/mnt/sdcard/AA_MY_DRIVE
LOG="$ROOT/_logs/sync_finisher.log"
LOCK=/tmp/sync_finisher.lock
ST_HOME=/root/.config/syncthing_everlight
ST_API="http://127.0.0.1:8384"
WATCHDOG="$ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh"

PC_IP=100.93.253.49
PC_USER=richgee
PC_KEY=/root/.ssh/phone_to_arch
PC_DEVICE_ID="JATQVWX-SWCIMSZ-3COXWKG-NSYQJY5-IRARMOF-46PDJQL-I7XQDJ4-NAS6QQC"
FOLDER_ID="everlight-workspace"

POLL_SECONDS=60          # how often to re-check progress
MAX_RUNTIME_SECONDS=21600 # 6h hard cap, then exit regardless
PC_ACK_REFRESH=5         # re-run the PC helper every N poll cycles (keeps PC awake)

mkdir -p "$(dirname "$LOG")"
ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

# ---- single instance ----
if [ -f "$LOCK" ]; then
  oldpid=$(cat "$LOCK" 2>/dev/null || true)
  if [ -n "$oldpid" ] && kill -0 "$oldpid" 2>/dev/null; then
    # already running -- quiet exit (this is normal under cron)
    exit 0
  fi
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "=== sync_finisher start (pid $$) ==="

# ---- 1. ensure phone Syncthing is up (reuse the proven watchdog launcher) ----
if ! curl -s -o /dev/null -m 4 "$ST_API/rest/noauth/health" 2>/dev/null; then
  log "phone Syncthing down -- invoking watchdog to launch it"
  bash "$WATCHDOG" --quiet 2>/dev/null || true
  sleep 8
fi
if ! curl -s -o /dev/null -m 4 "$ST_API/rest/noauth/health" 2>/dev/null; then
  log "phone Syncthing still down after watchdog -- direct launch"
  rm -f "$ST_HOME/syncthing.lock" 2>/dev/null
  nohup syncthing serve --home="$ST_HOME" --no-browser > /tmp/syncthing_phone.log 2>&1 &
  sleep 10
fi

APIKEY=$(grep -oP '<apikey>\K[^<]+' "$ST_HOME/config.xml" 2>/dev/null | head -1)
if [ -z "$APIKEY" ]; then
  log "FATAL: could not read Syncthing API key -- abort"
  exit 1
fi
log "phone Syncthing healthy, API key loaded"

# ---- helper: PC reachable? ----
pc_reachable() {
  timeout 10 ssh -i "$PC_KEY" -o ConnectTimeout=6 -o StrictHostKeyChecking=no \
    "$PC_USER@$PC_IP" "echo ok" 2>/dev/null | grep -q ok
}

# ---- helper: PC completion % of our folder (from phone's API view) ----
pc_completion() {
  curl -s -H "X-API-Key: $APIKEY" \
    "$ST_API/rest/db/completion?folder=$FOLDER_ID&device=$PC_DEVICE_ID" 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('completion',0):.1f} {d.get('needBytes',0)} {d.get('needItems',0)}\")" 2>/dev/null \
    || echo "0 0 0"
}

# ---- helper: trigger the PC-side acknowledger ----
trigger_pc_helper() {
  timeout 30 ssh -i "$PC_KEY" -o ConnectTimeout=8 "$PC_USER@$PC_IP" \
    "bash ~/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/sync_helper.sh" 2>&1 | tail -2
}

# ---- 2. main loop ----
START=$(date +%s)
cycle=0
while true; do
  elapsed=$(( $(date +%s) - START ))
  if [ "$elapsed" -ge "$MAX_RUNTIME_SECONDS" ]; then
    log "6h cap reached -- exiting (sync continues in background via Syncthing)"
    break
  fi

  if ! pc_reachable; then
    log "PC not reachable yet -- waiting (Syncthing will catch up when it wakes)"
    sleep "$POLL_SECONDS"
    cycle=$((cycle+1))
    continue
  fi

  # PC is up: every PC_ACK_REFRESH cycles, (re)trigger the PC helper to keep it awake
  if [ $(( cycle % PC_ACK_REFRESH )) -eq 0 ]; then
    ack=$(trigger_pc_helper)
    log "PC helper triggered -- ack: ${ack:-<none>}"
  fi

  read -r comp needbytes needitems <<< "$(pc_completion)"
  log "PC completion: ${comp}%  (needs ${needitems} items / ${needbytes} bytes)"

  # done?  completion 100 and nothing left to send
  if [ "${comp%.*}" -ge 100 ] && [ "${needbytes:-1}" -eq 0 ]; then
    log "=== PC is fully caught up (100%) ==="
    # flip phone folder to sendreceive for true bidirectional from here on
    CFG="$ST_HOME/config.xml"
    if grep -q 'id="'"$FOLDER_ID"'"[^>]*type="sendonly"' "$CFG"; then
      sed -i 's/\(<folder id="'"$FOLDER_ID"'"[^>]*\)type="sendonly"/\1type="sendreceive"/' "$CFG"
      log "flipped phone folder sendonly -> sendreceive (bidirectional now live)"
      # graceful restart so the new mode loads
      curl -s -X POST -H "X-API-Key: $APIKEY" "$ST_API/rest/system/restart" >/dev/null 2>&1 || true
      log "Syncthing restart requested to apply sendreceive"
    fi
    log "=== sync_finisher DONE ==="
    break
  fi

  sleep "$POLL_SECONDS"
  cycle=$((cycle+1))
done
