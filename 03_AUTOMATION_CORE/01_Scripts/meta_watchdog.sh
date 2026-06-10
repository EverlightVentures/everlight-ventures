#!/usr/bin/env bash
# meta_watchdog.sh -- the watchdog of watchdogs (Constitutional Amendment XII).
#
# Watches the three layers below it:
#   1. dashboards_watchdog (in-proot, cron */1) -- heartbeat at _logs/dashboards_watchdog.heartbeat
#   2. mcp_watchdog        (in-proot, cron */1) -- heartbeat at _logs/mcp_watchdog.heartbeat
#   3. dashboards_keepalive (Termux-side daemon) -- PID at /data/data/com.termux/files/home/.termux/boot/dashboards_keepalive.pid
#
# If any heartbeat is older than STALE_THRESHOLD or any PID is dead, fires the
# corresponding restart action and (on second-strike) posts a fail-loud Slack
# alert via branded_slack so it_triage / Rich sees the failure within 15 min.
#
# Per HARD LAW feedback_fail_loud_with_it_auto_repair: closed loop, ends in
# ✓ or operator escalation.
#
# Cron (every 5 min):
#   */5 * * * * bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/meta_watchdog.sh --quiet

set -u

ROOT=/mnt/sdcard/AA_MY_DRIVE
LOG=$ROOT/_logs/meta_watchdog.log
STATE=$ROOT/_logs/meta_watchdog_state.json
STALE_THRESHOLD_SECONDS=600   # 10 min -- 2x the dashboards cron interval

QUIET=0
for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
  esac
done

mkdir -p "$(dirname "$LOG")" 2>/dev/null

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() {
  echo "[$(ts)] $*" >> "$LOG"
  if [ "$QUIET" -eq 0 ]; then echo "$*"; fi
}

# Source secrets for Slack posts.
if [ -f "$ROOT/03_AUTOMATION_CORE/03_Credentials/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/03_AUTOMATION_CORE/03_Credentials/.env" 2>/dev/null || true
  set +a
fi

# Read previous strike count (so we only alert on second-strike, not every cycle).
load_strikes() {
  if [ -f "$STATE" ]; then
    cat "$STATE"
  else
    echo "{}"
  fi
}

save_strikes() {
  echo "$1" > "$STATE"
}

post_alert() {
  local subject=$1; local detail=$2
  python3 -c "
import sys
sys.path.insert(0, '$ROOT/03_AUTOMATION_CORE/01_Scripts/content_tools')
try:
    from branded_slack import post_branded_alert
    post_branded_alert(
        channel='#hive-alerts',
        severity='warn',
        title='$subject',
        detail='$detail',
        agent_name='Meta Watchdog',
    )
except Exception as e:
    print(f'alert failed: {e}', file=sys.stderr)
" >> "$LOG" 2>&1 || log "  WARN slack alert failed"
}

# Returns 0 if heartbeat is fresh, 1 if stale or missing.
heartbeat_fresh() {
  local file=$1
  if [ ! -f "$file" ]; then
    return 1
  fi
  local mtime now age
  mtime=$(stat -c %Y "$file" 2>/dev/null || echo 0)
  now=$(date +%s)
  age=$(( now - mtime ))
  [ "$age" -lt "$STALE_THRESHOLD_SECONDS" ]
}

# Check 1: dashboards_watchdog heartbeat ---------------------------------------
DASH_HB=$ROOT/_logs/dashboards_watchdog.heartbeat
if heartbeat_fresh "$DASH_HB"; then
  log "  ✓ dashboards_watchdog heartbeat fresh"
  DASH_STATUS=ok
else
  log "  ✗ dashboards_watchdog heartbeat stale/missing -- firing one-shot"
  nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh --quiet \
    >> $ROOT/_logs/dashboards_watchdog.log 2>&1 &
  DASH_STATUS=restarted
fi

# Check 2: mcp_watchdog heartbeat ----------------------------------------------
MCP_HB=$ROOT/_logs/mcp_watchdog.heartbeat
if heartbeat_fresh "$MCP_HB"; then
  log "  ✓ mcp_watchdog heartbeat fresh"
  MCP_STATUS=ok
else
  log "  ✗ mcp_watchdog heartbeat stale/missing -- firing one-shot"
  nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/mcp_watchdog.sh --quiet \
    >> $ROOT/_logs/mcp_watchdog.log 2>&1 &
  MCP_STATUS=restarted
fi

# Check 3: dashboards_keepalive PID --------------------------------------------
KA_PID_FILE=/data/data/com.termux/files/home/.termux/boot/dashboards_keepalive.pid
KA_SCRIPT=/data/data/com.termux/files/home/.termux/boot/dashboards_keepalive.sh
KA_STATUS=ok
if [ -f "$KA_PID_FILE" ]; then
  ka_pid=$(cat "$KA_PID_FILE" 2>/dev/null)
  if [ -n "$ka_pid" ] && kill -0 "$ka_pid" 2>/dev/null; then
    log "  ✓ dashboards_keepalive alive (pid=$ka_pid)"
  else
    log "  ✗ dashboards_keepalive pid=$ka_pid is DEAD -- respawning via setsid+nohup"
    # Detached respawn. setsid puts the child in a new process group with no
    # controlling tty, so it survives this cron script exiting.
    nohup setsid /data/data/com.termux/files/usr/bin/bash "$KA_SCRIPT" \
      < /dev/null > /dev/null 2>&1 &
    disown 2>/dev/null
    KA_STATUS=respawned
  fi
else
  log "  ✗ dashboards_keepalive pid file missing -- first-time spawn"
  nohup setsid /data/data/com.termux/files/usr/bin/bash "$KA_SCRIPT" \
    < /dev/null > /dev/null 2>&1 &
  disown 2>/dev/null
  KA_STATUS=spawned
fi

# Strike counting + escalation -------------------------------------------------
# Anything that wasn't ok gets a strike. Two strikes in a row = fail-loud alert.
strikes=$(load_strikes)
new_strikes='{"dashboards_watchdog":0,"mcp_watchdog":0,"dashboards_keepalive":0}'

for service in dashboards_watchdog mcp_watchdog dashboards_keepalive; do
  case "$service" in
    dashboards_watchdog) status=$DASH_STATUS ;;
    mcp_watchdog)        status=$MCP_STATUS ;;
    dashboards_keepalive) status=$KA_STATUS ;;
  esac

  prev=$(echo "$strikes" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$service',0))" 2>/dev/null || echo 0)
  if [ "$status" = "ok" ]; then
    new=0
  else
    new=$((prev + 1))
    # Only alert on TRANSITION to strike 2 (the second consecutive failure).
    # Subsequent strikes 3, 4, ... do not re-alert -- suppresses spam in
    # #hive-alerts when a service is in a persistent failure mode (e.g.,
    # keepalive respawn-from-proot which is structurally unrepairable).
    # Strikes reset to 0 when status returns to ok, at which point a new
    # transition to 2 can re-alert.
    if [ "$new" -eq 2 ]; then
      log "  ALERT $service transitioned to 2 strikes -- posting fail-loud"
      post_alert "Meta watchdog: $service repeatedly failing" \
                 "Service $service failed self-recovery 2 cycles in a row. Status=$status. Manual investigation. Further strikes suppressed until service recovers."
    elif [ "$new" -gt 2 ]; then
      log "  $service strike $new (alert suppressed, still in persistent-failure mode)"
    fi
  fi
  new_strikes=$(echo "$new_strikes" | python3 -c "import json,sys; d=json.load(sys.stdin); d['$service']=$new; print(json.dumps(d))")
done

save_strikes "$new_strikes"

# Heartbeat for the meta-watchdog itself (Constitutional Amendment XII -- the
# watchdog OF watchdogs needs its own pulse for any future tier above it).
echo "$(ts) dash=$DASH_STATUS mcp=$MCP_STATUS keepalive=$KA_STATUS" \
  > $ROOT/_logs/meta_watchdog.heartbeat

log "Cycle done -- dashboards=$DASH_STATUS mcp=$MCP_STATUS keepalive=$KA_STATUS"
