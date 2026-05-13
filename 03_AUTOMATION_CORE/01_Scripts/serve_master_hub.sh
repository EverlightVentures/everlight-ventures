#!/usr/bin/env bash
# serve_master_hub.sh -- the :2000 master hub.
# Serves /mnt/sdcard/AA_MY_DRIVE/_DASHBOARDS/index.html as the entry point
# to every local dashboard.

set -u

PORT="${HUB_PORT:-2000}"
ROOT="/mnt/sdcard/AA_MY_DRIVE/_DASHBOARDS"
PIDFILE="/tmp/serve_master_hub.pid"
LOGFILE="/tmp/serve_master_hub.log"
BIND="${HUB_BIND:-127.0.0.1}"

cmd="${1:-start}"

is_running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

start() {
  if is_running; then
    echo "already running pid=$(cat "$PIDFILE")  http://$BIND:$PORT/"
    return 0
  fi
  cd "$ROOT" || { echo "ROOT $ROOT missing"; exit 1; }
  nohup python3 -c "
import http.server
class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-cache, no-store, must-revalidate, max-age=0')
        super().end_headers()
    def log_message(self, fmt, *a):
        if '200' in fmt % a: return
        super().log_message(fmt, *a)
http.server.test(HandlerClass=NoCache, port=$PORT, bind='$BIND')
" > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 0.4
  echo "started pid=$(cat "$PIDFILE")  http://$BIND:$PORT/"
}

stop() {
  is_running || { echo "not running"; rm -f "$PIDFILE"; return 0; }
  pid="$(cat "$PIDFILE")"
  kill "$pid" 2>/dev/null; sleep 0.3; kill -9 "$pid" 2>/dev/null
  rm -f "$PIDFILE"; echo "stopped (was $pid)"
}

status() {
  if is_running; then
    echo "running pid=$(cat "$PIDFILE")  http://$BIND:$PORT/"
  else
    echo "not running"
  fi
}

case "$cmd" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    tail -50 "$LOGFILE" 2>/dev/null || echo "no log" ;;
  *) echo "usage: $0 {start|stop|restart|status|logs}"; exit 1 ;;
esac
