#!/usr/bin/env bash
# hive_dispatcher_supervisor.sh -- keep the FastAPI dispatcher running on :8600.
# Idempotent: cron calls this every few minutes.

set -u

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/dispatcher/supervisor.log
PIDFILE=/tmp/hive_dispatcher.pid
mkdir -p "$(dirname "$LOG")"

# Is anything already listening on 8600?
if ss -ltn 2>/dev/null | grep -q '127\.0\.0\.1:8600'; then
  exit 0
fi

if [ -f "$PIDFILE" ]; then
  old="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    exit 0
  fi
fi

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT INT TERM

echo "" >>"$LOG"
echo "=== dispatcher start $(date -Iseconds) pid=$$ ===" >>"$LOG"

# Load Resend and Slack env from the workspace .env so subprocess workers inherit them
set -a
[ -f /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env ] && \
  . /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env
set +a

exec /usr/bin/python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_dispatcher.py \
  >>"$LOG" 2>&1
