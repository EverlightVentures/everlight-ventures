#!/usr/bin/env bash
# mcp_watchdog.sh -- Self-healing watchdog for the 6 MCP HTTP servers.
#
# Pattern (mirrors dashboards_watchdog.sh): for each port, curl-check. If down,
# pkill stale -> fire start_mcp.sh -> sleep -> re-check. On second failure,
# write to IT repair queue + post fail-loud Slack alert.
#
# Per HARD LAW feedback_voice_register_by_recipient is not relevant here.
# Per HARD LAW feedback_fail_loud_with_it_auto_repair: failures must reach
# #hive-alerts via branded_slack so it_triage.py can auto-repair.
#
# Skipped: n8n :3103 (parked since 2026-04-24 per CLAUDE.md).
#
# Usage:
#   bash mcp_watchdog.sh           # one cycle, exit
#   bash mcp_watchdog.sh --status  # health table only, no fix
#   bash mcp_watchdog.sh --quiet   # no stdout, log only
#
# Cron (every 1 min):
#   * * * * * bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/mcp_watchdog.sh --quiet

set -u

ROOT=/mnt/sdcard/AA_MY_DRIVE
LOG=$ROOT/_logs/mcp_watchdog.log
QUEUE=$ROOT/_logs/it_repair_queue.jsonl
mkdir -p "$(dirname "$LOG")" "$(dirname "$QUEUE")" 2>/dev/null

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

# Source credentials so start_mcp.sh and Slack alerts have what they need.
if [ -f "$ROOT/03_AUTOMATION_CORE/03_Credentials/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/03_AUTOMATION_CORE/03_Credentials/.env" 2>/dev/null || true
  set +a
fi

# MCP service definitions: PORT|NAME|HEALTH_PATH|REQUIRES_SECRET
# n8n (3103) intentionally excluded -- parked per CLAUDE.md doctrine 2026-04-24.
SERVICES=(
  "3101|blinko-memory|/mcp|no"
  "3102|market-intel|/mcp|no"
  "3104|broker-os|/mcp|no"
  "3105|supabase|/mcp|SUPABASE_ACCESS_TOKEN"
  # DISABLED 2026-05-19: stripe rk_live_ key returns 401 (invalid/revoked). MCP
  # never binds 3106 -> watchdog re-enqueued every minute -> 871 escalations/day
  # of pure noise. Payments are not live pre-Deal-1 so the MCP is not needed.
  # RE-ENABLE when Rich rotates the Stripe RAK (dashboard.stripe.com/apikeys) and
  # checkout goes live. Root-cause + fix logged in cf/security session 2026-05-19.
  # "3106|stripe|/mcp|STRIPE_SECRET_KEY"
  "3107|resend|/mcp|RESEND_API_KEY"
)

# Health check: 000 = down (connection refused). Anything 200-499 = alive.
# MCP endpoints return 406/405 on simple GETs; that still counts as alive.
probe() {
  local port=$1
  local path=$2
  local rc
  rc=$(curl -s -o /dev/null -w "%{http_code}" -m 3 "http://127.0.0.1:$port$path" 2>/dev/null)
  echo "${rc:-000}"
}

is_alive() {
  local rc=$1
  case "$rc" in
    200|201|202|204|301|302|400|401|403|404|405|406|409) return 0 ;;
    *) return 1 ;;
  esac
}

pids_on_port() {
  local port=$1
  ss -tlnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $7}' | \
    grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
}

restart_one() {
  local port=$1; local name=$2
  log "RESTART :$port ($name) -- pkill stale + start_mcp.sh"
  for pid in $(pids_on_port "$port"); do
    log "  pkill pid=$pid on :$port"
    kill "$pid" 2>/dev/null && sleep 0.4
    kill -9 "$pid" 2>/dev/null
  done
  pkill -f "mcp-proxy.*--port $port" 2>/dev/null
  sleep 0.3
  nohup bash "$ROOT/03_AUTOMATION_CORE/01_Scripts/start_mcp.sh" "$name" \
    >> "/tmp/mcp_${name}.log" 2>&1 &
  sleep 2
}

queue_repair() {
  local port=$1; local name=$2; local reason=$3
  python3 -c "
import json, pathlib
from datetime import datetime, timezone
entry = {
    'ts': datetime.now(timezone.utc).isoformat(),
    'service': '$name',
    'port': $port,
    'failure_reason': '$reason',
    'auto_repair_target': '$name',
    'attempt_count': 1,
    'status': 'pending',
}
p = pathlib.Path('$QUEUE')
p.parent.mkdir(parents=True, exist_ok=True)
with p.open('a') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null || log "  WARN failed to write IT repair queue entry"
}

post_fail_loud_alert() {
  local port=$1; local name=$2; local reason=$3
  # Best-effort Slack alert via branded_slack. Non-blocking on failure.
  python3 -c "
import sys
sys.path.insert(0, '$ROOT/03_AUTOMATION_CORE/01_Scripts/content_tools')
try:
    from branded_slack import post_branded_alert
    post_branded_alert(
        severity='warn',
        title='MCP $name failed to start',
        detail='Port :$port stayed down after auto-restart. Reason: $reason. it_triage.py will attempt repair.',
        agent='MCP Watchdog',
        meta={'auto_repair_target': '$name', 'port': $port, 'reason': '$reason'},
        channel_env='SLACK_WEBHOOK_ALERTS',
    )
except Exception as e:
    print(f'alert post failed: {e}', file=sys.stderr)
" >> "$LOG" 2>&1 || log "  WARN Slack alert failed (post_branded_alert)"
}

ALIVE=0; DEAD=0; RESTARTED=0; QUEUED=0
TABLE=""
for svc in "${SERVICES[@]}"; do
  IFS='|' read -r port name healthpath secret_var <<< "$svc"

  # Preflight: if MCP requires a secret and it isn't set, fail loud immediately.
  if [ "$secret_var" != "no" ]; then
    if [ -z "${!secret_var:-}" ]; then
      TABLE+=$(printf "  :%-4s %-15s NO_SECRET (%s missing)\n" "$port" "$name" "$secret_var")
      TABLE+=$'\n'
      DEAD=$((DEAD+1))
      if [ "$STATUS_ONLY" -eq 0 ]; then
        log "  :$port ($name) skipped -- $secret_var missing in env"
        queue_repair "$port" "$name" "secret_missing:$secret_var"
        post_fail_loud_alert "$port" "$name" "secret_missing:$secret_var"
        QUEUED=$((QUEUED+1))
      fi
      continue
    fi
  fi

  rc=$(probe "$port" "$healthpath")
  if is_alive "$rc"; then
    TABLE+=$(printf "  :%-4s %-15s UP (HTTP %s)\n" "$port" "$name" "$rc")
    TABLE+=$'\n'
    ALIVE=$((ALIVE+1))
    continue
  fi

  TABLE+=$(printf "  :%-4s %-15s DOWN (HTTP %s)\n" "$port" "$name" "$rc")
  TABLE+=$'\n'
  DEAD=$((DEAD+1))

  if [ "$STATUS_ONLY" -eq 1 ]; then continue; fi

  restart_one "$port" "$name"
  rc2=$(probe "$port" "$healthpath")
  if is_alive "$rc2"; then
    RESTARTED=$((RESTARTED+1))
    log "  ✓ :$port ($name) back UP (HTTP $rc2)"
  else
    log "  ✗ :$port ($name) STILL DOWN after restart (HTTP $rc2) -- queueing for IT triage"
    queue_repair "$port" "$name" "restart_failed_http_$rc2"
    post_fail_loud_alert "$port" "$name" "restart_failed_http_$rc2"
    QUEUED=$((QUEUED+1))
  fi
done

if [ "$STATUS_ONLY" -eq 1 ]; then
  echo "$TABLE"
  echo "  $ALIVE up, $DEAD down (status only)"
else
  log "Cycle done -- $ALIVE up, $DEAD down, $RESTARTED restarted, $QUEUED queued for IT"
  if [ "$QUIET" -eq 0 ]; then
    echo "$TABLE"
    echo "  $ALIVE up, $DEAD down, $RESTARTED restarted, $QUEUED queued for IT triage"
  fi
fi

# Heartbeat
echo "$(ts) alive=$ALIVE down=$DEAD restarted=$RESTARTED queued=$QUEUED" \
  > "$ROOT/_logs/mcp_watchdog.heartbeat"
