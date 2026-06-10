#!/usr/bin/env bash
# mcp_broker_os_local.sh -- phone-local SSE/HTTP proxy for broker-os MCP.
# Listens on 127.0.0.1:3104. Idempotent; cron reruns this every few minutes.

set -u

LOG=/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/logs/mcp_broker_os.log
PIDFILE=/tmp/mcp_broker_os.pid
mkdir -p "$(dirname "$LOG")"

# Idempotency guard
if [ -f "$PIDFILE" ]; then
  old="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    exit 0
  fi
fi

# If anything else already listens on 3104, bail out
if ss -ltn 2>/dev/null | grep -q '127\.0\.0\.1:3104'; then
  echo "$(date -Iseconds) port 3104 already bound -- nothing to do" >>"$LOG"
  exit 0
fi

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT INT TERM

echo "" >>"$LOG"
echo "=== mcp-proxy broker-os start $(date -Iseconds) pid=$$ ===" >>"$LOG"

export WORKSPACE=/mnt/sdcard/AA_MY_DRIVE
export DJANGO_URL=http://127.0.0.1:8504
export SMTP_HOST=smtp.resend.com
export SMTP_PORT=465
export SMTP_USER=resend
export SMTP_PASS=re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt
export SMTP_FROM=noreply@everlightventures.io

exec /usr/local/bin/mcp-proxy \
  --host 127.0.0.1 --port 3104 \
  --pass-environment \
  -- /usr/bin/python3 /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/broker_os/server.py \
  >>"$LOG" 2>&1
