#!/usr/bin/env bash
# stop_all.sh -- Kill the MCP server fleet started by start_all.sh.

set -u

PIDDIR="${MCP_PIDDIR:-/tmp/mcp_pids}"
ts() { date '+%Y-%m-%d %H:%M:%S'; }

if [ ! -d "$PIDDIR" ]; then
  echo "[$(ts)] no $PIDDIR -- nothing to stop"
  exit 0
fi

shopt -s nullglob
for pidfile in "$PIDDIR"/*.pid; do
  name="$(basename "$pidfile" .pid)"
  pid="$(cat "$pidfile" 2>/dev/null || echo "")"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    sleep 0.3
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null
      echo "[$(ts)] KILL $name pid=$pid (force)"
    else
      echo "[$(ts)] STOP $name pid=$pid"
    fi
  else
    echo "[$(ts)] DEAD $name -- stale pidfile, removing"
  fi
  rm -f "$pidfile"
done

# Belt + suspenders: kill anything matching the pattern that escaped pid tracking
pkill -f "mcp_servers/.*/server.py" 2>/dev/null && echo "[$(ts)] pkill swept stragglers"
echo "[$(ts)] stop_all.sh -- done"
