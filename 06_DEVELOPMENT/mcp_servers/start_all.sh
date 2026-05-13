#!/usr/bin/env bash
# start_all.sh -- Spawn the MCP server fleet.
#
# Called by mcp_elect.sh when this node wins the election.
# Spawns servers that exist on disk; logs a skip for stubs not yet built.
# Each server runs in the background; pids tracked in /tmp/mcp_pids/.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDDIR="${MCP_PIDDIR:-/tmp/mcp_pids}"
LOGDIR="${MCP_LOGDIR:-/tmp/mcp_logs}"
mkdir -p "$PIDDIR" "$LOGDIR"

# server_id -> "port:script_path"
# Port band: 2701-2707 (mirrors local-dashboard 2100-band doctrine; 2700 reserved for Blinko RAG)
declare -A FLEET=(
  [broker_os]="2701:$ROOT/broker_os/server.py"
  [blinko_memory]="2702:$ROOT/blinko_memory/server.py"
  [market_intel]="2703:$ROOT/market_intel/server.py"
  [slack]="2704:$ROOT/slack/server.py"
  [gmail]="2705:$ROOT/gmail/server.py"
  [calendar]="2706:$ROOT/calendar/server.py"
  [hive_orchestrator]="2707:$ROOT/hive_orchestrator/server.py"
)

ts() { date '+%Y-%m-%d %H:%M:%S'; }

start_one() {
  local name="$1"; local port="$2"; local script="$3"
  local pidfile="$PIDDIR/$name.pid"
  local logfile="$LOGDIR/$name.log"

  if [ ! -f "$script" ]; then
    echo "[$(ts)] SKIP $name -- script not found ($script)"
    return
  fi
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "[$(ts)] OK   $name -- already running pid=$(cat "$pidfile")"
    return
  fi
  MCP_PORT="$port" nohup python3 "$script" > "$logfile" 2>&1 &
  echo $! > "$pidfile"
  echo "[$(ts)] UP   $name -- port=$port pid=$! script=$script"
}

echo "[$(ts)] mcp_servers/start_all.sh -- starting fleet"
for name in "${!FLEET[@]}"; do
  IFS=':' read -r port script <<< "${FLEET[$name]}"
  start_one "$name" "$port" "$script"
done
echo "[$(ts)] start_all.sh -- done; pids in $PIDDIR, logs in $LOGDIR"
