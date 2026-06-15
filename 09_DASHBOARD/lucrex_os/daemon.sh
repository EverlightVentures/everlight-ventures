#!/usr/bin/env bash
# Self-heal loop for LUCREX OS. Singleton-guarded. NOT a cron entry.
# Phone has no crond -- cron entries silently never run. Use this daemon loop.
set -uo pipefail
ROOT="${LUCREX_OS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
OS_DIR="$ROOT/09_DASHBOARD/lucrex_os"
pidfile="/tmp/lucrex_os_daemon.pid"
if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
  echo "daemon already running"; exit 0
fi
echo $$ > "$pidfile"
trap 'rm -f "$pidfile"' EXIT
while true; do
  python3 "$OS_DIR/sync.py" --check >/dev/null 2>&1 || true
  sleep 60
done
