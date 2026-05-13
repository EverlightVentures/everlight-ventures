#!/usr/bin/env bash
# serve_themed.sh -- launch the Everlight branded HTTP server on any port.
# Drop-in replacement for `python3 -m http.server <port>`.
#
# Usage:
#   serve_themed.sh start <port> <root_dir> [<label>]
#   serve_themed.sh stop <port>
#   serve_themed.sh status <port>
#   serve_themed.sh restart <port> <root_dir> [<label>]
#
# pidfile: /tmp/themed_<port>.pid
# logfile: /tmp/themed_<port>.log

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HANDLER="$SCRIPT_DIR/everlight_themed_server.py"

cmd="${1:-help}"
port="${2:-}"
root="${3:-}"
label="${4:-}"

PIDFILE="/tmp/themed_${port}.pid"
LOGFILE="/tmp/themed_${port}.log"

is_running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

start() {
  [ -z "$port" ] && { echo "usage: $0 start <port> <root> [label]"; exit 1; }
  [ -z "$root" ] && { echo "usage: $0 start <port> <root> [label]"; exit 1; }
  if is_running; then
    echo "already running pid=$(cat "$PIDFILE")  http://127.0.0.1:$port/"
    return 0
  fi
  EV_PAGE_LABEL="${label:-Everlight Local}" \
    nohup python3 "$HANDLER" "$port" "$root" "${label:-Everlight Local}" \
    > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 0.4
  echo "started pid=$(cat "$PIDFILE")  http://127.0.0.1:$port/"
}

stop() {
  [ -z "$port" ] && { echo "usage: $0 stop <port>"; exit 1; }
  is_running || { echo "not running on :$port"; rm -f "$PIDFILE"; return 0; }
  pid="$(cat "$PIDFILE")"
  kill "$pid" 2>/dev/null; sleep 0.2; kill -9 "$pid" 2>/dev/null
  rm -f "$PIDFILE"
  echo "stopped (was $pid)"
}

status() {
  [ -z "$port" ] && { echo "usage: $0 status <port>"; exit 1; }
  if is_running; then
    echo "running pid=$(cat "$PIDFILE")  http://127.0.0.1:$port/"
  else
    echo "not running on :$port"
  fi
}

case "$cmd" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  *) echo "usage: $0 {start|stop|restart|status} <port> [<root> [<label>]]"; exit 1 ;;
esac
