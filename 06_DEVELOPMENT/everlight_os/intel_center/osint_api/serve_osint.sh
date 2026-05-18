#!/usr/bin/env bash
# Intel Center OSINT API launcher (port 2301)
# Usage:
#   intel-osint            # foreground, Ctrl+C to stop
#   intel-osint start      # background (nohup)
#   intel-osint stop       # kill the process
#   intel-osint status     # show whether it's running
#   intel-osint logs       # tail the log

set -u
ROOT="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center"
PORT="${IOS_PORT:-2301}"
BIND="${IOS_BIND:-127.0.0.1}"
LOG="$ROOT/cache/osint_api.log"
URL="http://${BIND/0.0.0.0/localhost}:$PORT/"

gold(){ printf "\033[38;5;179m%s\033[0m\n" "$*"; }
dim(){  printf "\033[38;5;245m%s\033[0m\n" "$*"; }

case "${1:-fg}" in
  start)
    if pgrep -f "uvicorn.*osint_api.main.*$PORT" >/dev/null 2>&1; then
      gold "[OSINT] already running -- $URL"; exit 0
    fi
    cd "$ROOT" || exit 1
    mkdir -p "$ROOT/cache"
    nohup python3 -m uvicorn osint_api.main:app --host "$BIND" --port "$PORT" \
      > "$LOG" 2>&1 &
    sleep 1
    pgrep -f "uvicorn.*osint_api.main.*$PORT" >/dev/null 2>&1 \
      && { gold "[OSINT] started -- $URL"; dim "  log: $LOG"; } \
      || { dim "[OSINT] start failed -- check $LOG"; exit 1; }
    ;;
  stop)
    pids=$(pgrep -f "uvicorn.*osint_api.main.*$PORT" 2>/dev/null || true)
    [ -n "$pids" ] && { kill $pids; dim "[OSINT] stopped pid(s): $pids"; } || dim "[OSINT] not running"
    ;;
  status)
    if pgrep -f "uvicorn.*osint_api.main.*$PORT" >/dev/null 2>&1; then
      gold "[OSINT] running -- $URL"
    else
      dim "[OSINT] not running"
    fi
    ;;
  logs)
    tail -n 50 -f "$LOG" 2>/dev/null || dim "no log yet at $LOG"
    ;;
  fg|*)
    cd "$ROOT" || exit 1
    gold "==========================================="
    gold "  ✦  OSINT DESK  ·  EVERLIGHT VENTURES"
    gold "==========================================="
    printf "  URL:    \033[38;5;179m%s\033[0m\n" "$URL"
    dim   "  Stop:   Ctrl+C      Logs:  intel-osint logs"
    dim   "  CLI:    intel investigate <target>"
    gold "==========================================="
    exec python3 -m uvicorn osint_api.main:app --host "$BIND" --port "$PORT"
    ;;
esac
