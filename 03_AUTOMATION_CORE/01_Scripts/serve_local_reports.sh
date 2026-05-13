#!/usr/bin/env bash
# serve_local_reports.sh -- local replacement for the dead 163.192.19.196:8504/reports
# Bound to :8504 so the existing hardcoded URLs in publish_gdoc / branded_slack / etc.
# all just work locally. No-cache headers so report edits show up on refresh.
#
# Usage:
#   bash serve_local_reports.sh start   # spawn in background
#   bash serve_local_reports.sh stop
#   bash serve_local_reports.sh status
#   bash serve_local_reports.sh logs

set -u

PORT="${REPORTS_PORT:-2200}"
ROOT="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD"   # serves /reports/ under this
PIDFILE="/tmp/serve_local_reports.pid"
LOGFILE="/tmp/serve_local_reports.log"
BIND="${REPORTS_BIND:-127.0.0.1}"

cmd="${1:-start}"

is_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

start() {
  if is_running; then
    echo "already running (pid=$(cat "$PIDFILE")) on http://$BIND:$PORT/reports/"
    return 0
  fi
  THEMED="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/serve_helpers/everlight_themed_server.py"
  cd "$ROOT" || { echo "ROOT $ROOT missing"; exit 1; }
  EV_BIND="$BIND" nohup python3 "$THEMED" "$PORT" "$ROOT" "Reports Hub" > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 0.5
  echo "started pid=$(cat "$PIDFILE")"
  echo "  reports root: $ROOT"
  echo "  url:          http://$BIND:$PORT/reports/"
  echo "  log:          $LOGFILE"
}

stop() {
  if ! is_running; then
    echo "not running"
    rm -f "$PIDFILE"
    return 0
  fi
  pid="$(cat "$PIDFILE")"
  kill "$pid" 2>/dev/null && sleep 0.3
  kill -9 "$pid" 2>/dev/null
  rm -f "$PIDFILE"
  echo "stopped (pid was $pid)"
}

status() {
  if is_running; then
    echo "running pid=$(cat "$PIDFILE") -- http://$BIND:$PORT/reports/"
    ls -1t "$ROOT/reports/" | head -5 | sed 's/^/  recent: /'
  else
    echo "not running"
  fi
}

case "$cmd" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    tail -50 "$LOGFILE" 2>/dev/null || echo "no log yet" ;;
  *) echo "usage: $0 {start|stop|restart|status|logs}"; exit 1 ;;
esac
