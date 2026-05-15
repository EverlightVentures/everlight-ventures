#!/usr/bin/env bash
# dashboards_watchdog.sh -- Self-healing watchdog for the 2100-band local dashboards.
#
# Pattern (per Rich's spec): for each port, curl health. If down → pkill anything
# on that port → restart the canonical launcher. Idempotent. Safe to run from
# cron, boot, or interactive shell.
#
# Usage:
#   bash dashboards_watchdog.sh           # one cycle, exit
#   bash dashboards_watchdog.sh --status  # print health table only, no fix
#   bash dashboards_watchdog.sh --quiet   # no stdout, only log file
#
# Cron line (every 1 min):
#   * * * * * bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh --quiet

set -u

ROOT=/mnt/sdcard/AA_MY_DRIVE
LOG=$ROOT/_logs/dashboards_watchdog.log
mkdir -p "$(dirname "$LOG")"

QUIET=0
STATUS_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
    --status|-s) STATUS_ONLY=1 ;;
  esac
done

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() {
  echo "[$(ts)] $*" >> "$LOG"
  if [ "$QUIET" -eq 0 ]; then echo "$*"; fi
}

# Service definitions: PORT|HEALTH_PATH|LAUNCH_COMMAND|HUMAN_NAME
# Each launch command runs in a subshell so it can cd before exec
SERVICES=(
  "2000|/|cd $ROOT && nohup bash 03_AUTOMATION_CORE/01_Scripts/serve_master_hub.sh start > /tmp/svc_2000.log 2>&1|Master Hub"
  "2200|/|cd $ROOT && nohup bash 03_AUTOMATION_CORE/01_Scripts/serve_local_reports.sh start > /tmp/svc_2200.log 2>&1|Reports Hub"
  "2300|/|cd $ROOT/Everlight_Intel_Center/09_Dashboard && nohup python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/serve_helpers/everlight_themed_server.py 2300 . 'Intel Center' > /tmp/svc_2300.log 2>&1 &|Intel Static"
  "2301|/healthz|cd $ROOT/Everlight_Intel_Center && nohup python3 -m uvicorn osint_api.main:app --host 127.0.0.1 --port 2301 > /tmp/svc_2301.log 2>&1 &|Intel FastAPI"
  "2302|/healthz|cd $ROOT/Everlight_Intel_Center && nohup python3 -m uvicorn osint_api.esign_server:app --host 127.0.0.1 --port 2302 > /tmp/svc_2302.log 2>&1 &|E-Sign + Signatures"
  "2400|/|cd $ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/Alley_Kingz/prototype && nohup python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/serve_helpers/everlight_themed_server.py 2400 . 'Apps -- Alley Kingz' > /tmp/svc_2400.log 2>&1 &|Apps"
  "2401|/api/health|cd $ROOT/09_DASHBOARD/moltbook && nohup python3 serve.py > /tmp/svc_2401.log 2>&1 &|Moltbook -- audit notebook"
  "2500|/|cd $ROOT/05_PERSONAL/02_Training/MMA_Notebook/Fight_Camp_OS && nohup python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/serve_helpers/everlight_themed_server.py 2500 . 'MMA Fight Camp' > /tmp/svc_2500.log 2>&1 &|Health (MMA)"
  "2700|/health|cd $ROOT && BLINKO_PORT=2700 nohup python3 06_DEVELOPMENT/everlight_os/blinko/blinko_lite.py > /tmp/svc_2700.log 2>&1 &|Blinko RAG"
  "2701|/healthz|cd $ROOT && BLINKO_URL=http://127.0.0.1:2700 nohup python3 -m uvicorn 06_DEVELOPMENT.mcp_servers.http_bridge:app --host 127.0.0.1 --port 2701 > /tmp/svc_2701.log 2>&1 &|MCP HTTP Bridge"
)

# Pids of stale processes bound to a port we want
pids_on_port() {
  # Best effort: try ss first, fallback to lsof, fallback to fuser, fallback to ps grep
  local port=$1
  ss -tlnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $7}' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
}

restart_one() {
  local port=$1; local launch="$2"; local name="$3"
  log "RESTART :$port ($name) -- pkill stale + launch"
  # Kill anything bound to this port
  for pid in $(pids_on_port "$port"); do
    log "  pkill stale pid=$pid on :$port"
    kill "$pid" 2>/dev/null && sleep 0.4
    kill -9 "$pid" 2>/dev/null
  done
  # Belt + suspenders: pkill by command match (catches detached processes)
  pkill -f "port[= ]$port" 2>/dev/null
  pkill -f ":$port" 2>/dev/null
  sleep 0.3
  # Launch
  bash -c "$launch"
  sleep 1.5
}

ALIVE=0
DEAD=0
RESTARTED=0
TABLE=""
for svc in "${SERVICES[@]}"; do
  IFS='|' read -r port healthpath launch name <<< "$svc"
  rc=$(curl -s -o /dev/null -w "%{http_code}" -m 3 "http://127.0.0.1:$port$healthpath" 2>/dev/null)
  status="DOWN"
  if [ "$rc" = "200" ] || [ "$rc" = "404" ]; then
    # 404 still counts as alive (server up, just no root route)
    status="UP"
    ALIVE=$((ALIVE+1))
  else
    DEAD=$((DEAD+1))
  fi
  TABLE+=$(printf "  :%-5s %-22s %s (HTTP %s)\n" "$port" "$name" "$status" "$rc")
  TABLE+=$'\n'

  if [ "$STATUS_ONLY" -eq 1 ]; then continue; fi

  if [ "$status" = "DOWN" ]; then
    restart_one "$port" "$launch" "$name"
    # Re-check after restart
    rc2=$(curl -s -o /dev/null -w "%{http_code}" -m 3 "http://127.0.0.1:$port$healthpath" 2>/dev/null)
    if [ "$rc2" = "200" ] || [ "$rc2" = "404" ]; then
      RESTARTED=$((RESTARTED+1))
      log "  ✓ :$port back UP (HTTP $rc2)"
    else
      log "  ✗ :$port still DOWN after restart (HTTP $rc2)"
    fi
  fi
done

# ------------------------------------------------------------------------------
# Non-port actions -- run every cycle regardless of port-watchdog state.
# Order matters here: each action is fire-and-forget but kept short.
# Per HARD LAW feedback_oracle_only_crons + feedback_offline_first_bidirectional_sync:
# this is NOT a cron host, but the watchdog is the legitimate phone-side
# recurring trigger. Keep actions cheap (sub-second) so they fit the 1-min cycle.
# ------------------------------------------------------------------------------

# Action 1: drain sync_queue if non-empty (ships phone-originated writes upward)
if [ "$STATUS_ONLY" -eq 0 ]; then
  QUEUE_DEPTH=$(python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/sync_queue.py depth 2>/dev/null || echo 0)
  if [ "$QUEUE_DEPTH" != "0" ] && [ -n "$QUEUE_DEPTH" ]; then
    log "  sync_queue depth=$QUEUE_DEPTH -- draining"
    python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/sync_queue.py drain >> "$LOG" 2>&1 &
  fi

  # Action 2: drain agentmemory inbox if any local inbox entries arrived from peers
  if [ -s /tmp/agentmemory_inbox.jsonl ]; then
    log "  agentmemory_inbox has entries -- merging"
    python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/agentmemory_inbox_merger.py drain >> "$LOG" 2>&1 &
  fi
fi

# Print summary
if [ "$STATUS_ONLY" -eq 1 ]; then
  echo "$TABLE"
  echo "  $ALIVE up, $DEAD down (status only, no restart)"
else
  log "Cycle done -- $ALIVE up, $DEAD down, $RESTARTED restarted"
  if [ "$QUIET" -eq 0 ]; then
    echo "$TABLE"
    echo "  $ALIVE up, $DEAD down, $RESTARTED restarted this cycle"
  fi
fi
