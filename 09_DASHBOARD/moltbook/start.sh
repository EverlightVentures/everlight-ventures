#!/usr/bin/env bash
# Moltbook launcher -- nohup'd local HTTP server on port 1112.
# Default binds 127.0.0.1 (local only).
# Override:
#   MOLTBOOK_BIND=0.0.0.0 bash start.sh   # tailnet/lan-visible
#   MOLTBOOK_PORT=2400 bash start.sh      # different port
#   MOLTBOOK_VERBOSE=1 bash start.sh      # log every request

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/_moltbook.log"
PID_FILE="$HERE/_moltbook.pid"

# If already running, don't start a second one
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Moltbook already running (PID $(cat "$PID_FILE"))"
  echo "  -> http://${MOLTBOOK_BIND:-127.0.0.1}:${MOLTBOOK_PORT:-2401}"
  exit 0
fi

cd "$HERE"
nohup python3 serve.py >> "$LOG" 2>&1 &
echo $! > "$PID_FILE"
sleep 1

if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Moltbook launched -- PID $(cat "$PID_FILE")"
  echo "  -> http://${MOLTBOOK_BIND:-127.0.0.1}:${MOLTBOOK_PORT:-2401}"
  echo "  -> log: $LOG"
else
  echo "Moltbook failed to start. tail of log:"
  tail -20 "$LOG"
  exit 1
fi
