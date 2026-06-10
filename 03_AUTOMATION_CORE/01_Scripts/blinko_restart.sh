#!/bin/bash
# Safe restart of the phone BlinkoLite servers (:1111 + :2700) onto the canonical
# _state brain DB.
#
# WHY THIS EXISTS: `pkill -f blinko_lite.py` matches ANY command line containing
# that string -- including the shell running the command -- and on 2026-06-03 it
# killed a live interactive shell mid-run. This helper lives in its own file
# (its args are "bash .../blinko_restart.sh", which do NOT contain the pattern)
# and matches server PIDs precisely with `blinko_lite\.py$`, so it can never kill
# its own caller. NEVER reintroduce `pkill -f blinko_lite.py` anywhere.
set -u
ROOT=/mnt/sdcard/AA_MY_DRIVE
PY="$ROOT/06_DEVELOPMENT/everlight_os/blinko/blinko_lite.py"
LOG="$ROOT/_logs/blinko_lite.log"

# 1. stop existing servers by EXACT match (cmdline ending in blinko_lite.py).
pids=$(pgrep -f 'blinko_lite\.py$' || true)
if [ -n "$pids" ]; then
  echo "stopping blinko_lite pid(s): $pids"
  kill $pids 2>/dev/null || true
  sleep 2
  for p in $pids; do kill -0 "$p" 2>/dev/null && kill -9 "$p" 2>/dev/null || true; done
fi

# 2. start :1111 and :2700 fresh (DB default is now _state/blinko_lite.db).
setsid nohup python3 "$PY" >> "$LOG" 2>&1 < /dev/null &
BLINKO_PORT=2700 setsid nohup python3 "$PY" >> "$LOG" 2>&1 < /dev/null &
sleep 3

# 3. verify both answer health.
ok=0
for port in 1111 2700; do
  if curl -s -m4 "http://127.0.0.1:$port/health" | grep -q '"ok"'; then
    echo ":$port UP"; ok=$((ok + 1))
  else
    echo ":$port DOWN"
  fi
done
if [ "$ok" -eq 2 ]; then
  echo "blinko restart OK (both serving $ROOT/_state/blinko_lite.db)"
else
  echo "blinko restart INCOMPLETE ($ok/2 up)"; exit 1
fi
