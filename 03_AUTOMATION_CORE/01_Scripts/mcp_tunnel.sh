#!/usr/bin/env bash
# mcp_tunnel.sh -- supervise the SSH tunnel from phone to Oracle E5 for the MCP fleet.
# Listens on 127.0.0.1:3101-3107 (minus 3104 which is phone-local for broker-os).
# Auto-reconnects on disconnect. Idempotent: if another copy is running, this exits.

set -u

LOG=/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/logs/mcp_tunnel.log
PIDFILE=/tmp/mcp_tunnel.pid
mkdir -p "$(dirname "$LOG")"

# Idempotency guard
if [ -f "$PIDFILE" ]; then
  old="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    echo "$(date -Iseconds) tunnel supervisor already running pid=$old" >>"$LOG"
    exit 0
  fi
fi
echo $$ > "$PIDFILE"

echo "" >>"$LOG"
echo "=== supervisor start $(date -Iseconds) pid=$$ ===" >>"$LOG"

trap 'echo "$(date -Iseconds) supervisor exiting pid=$$" >>"$LOG"; rm -f "$PIDFILE"; exit 0' EXIT INT TERM

while true; do
  # -N no command, -T no tty, -o ExitOnForwardFailure=no tolerates ports already bound
  # (SSH itself dies if *any* LocalForward fails when ExitOnForwardFailure=yes)
  /usr/bin/ssh -F /root/.ssh/config \
      -N -T \
      -o ExitOnForwardFailure=no \
      -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
      oracle-mcp-tunnel \
      >>"$LOG" 2>&1
  rc=$?
  echo "$(date -Iseconds) ssh exited rc=$rc -- reconnecting in 8s" >>"$LOG"
  sleep 8
done
