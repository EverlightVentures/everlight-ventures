#!/usr/bin/env bash
# Intel Center -- Dashboard launcher (Everlight Ventures, port 2300)
# Usage:
#   intel               # rebuild data + serve on http://localhost:2300 (foreground)
#   intel rebuild       # regenerate data.js from SQLite (no server)
#   intel pages         # regenerate the multi-page HTML from gen_pages.py
#   intel stop          # kill the running server on 2300
#   intel open          # open the URL in the default browser
#   intel status        # show whether the server is up
#
# Env overrides:
#   IC_PORT   default 2300
#   IC_BIND   default 127.0.0.1 (set 0.0.0.0 to reach from tailnet)

set -u

ROOT="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center"
DASH="$ROOT/09_Dashboard"
PORT="${IC_PORT:-2300}"
BIND="${IC_BIND:-127.0.0.1}"
URL="http://${BIND/0.0.0.0/localhost}:$PORT/09_Dashboard/index.html"

gold()   { printf "\033[38;5;179m%s\033[0m\n" "$*"; }
dim()    { printf "\033[38;5;245m%s\033[0m\n" "$*"; }
banner() {
  gold "==========================================="
  gold "  ✦  INTEL CENTER  ·  EVERLIGHT VENTURES"
  gold "==========================================="
  printf "  URL:    \033[38;5;179m%s\033[0m\n" "$URL"
  dim   "  Stop:   Ctrl+C   |   Rebuild data:  intel rebuild"
  dim   "  Pages:  intel pages   Open:  intel open   Status: intel status"
  gold "==========================================="
}

try_open() {
  local url="$1"
  command -v termux-open-url >/dev/null 2>&1 && termux-open-url "$url" 2>/dev/null && return 0
  command -v xdg-open        >/dev/null 2>&1 && xdg-open        "$url" 2>/dev/null && return 0
  command -v open            >/dev/null 2>&1 && open            "$url" 2>/dev/null && return 0
  command -v am              >/dev/null 2>&1 && am start -a android.intent.action.VIEW -d "$url" >/dev/null 2>&1 && return 0
  return 1
}

case "${1:-serve}" in
  rebuild)
    python3 "$DASH/scripts/rebuild_data.py"
    exit $?
    ;;

  pages)
    python3 "$DASH/scripts/gen_pages.py"
    exit $?
    ;;

  stop)
    pids=$(pgrep -f "http.server[[:space:]]*$PORT" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      kill $pids 2>/dev/null && dim "[INTEL] stopped pid(s): $pids"
    else
      dim "[INTEL] no server running on port $PORT"
    fi
    exit 0
    ;;

  open)
    if try_open "$URL"; then dim "[INTEL] opened $URL"
    else echo "$URL"; fi
    exit 0
    ;;

  status)
    if pgrep -f "http.server[[:space:]]*$PORT" >/dev/null 2>&1; then
      gold "[INTEL] running -- $URL"
    else
      dim  "[INTEL] not running"
    fi
    exit 0
    ;;

  help|-h|--help)
    sed -n '2,15p' "$0"
    exit 0
    ;;
esac

# default: serve
if pgrep -f "http.server[[:space:]]*$PORT" >/dev/null 2>&1; then
  dim "[INTEL] server already running -- opening URL"
  try_open "$URL" || echo "$URL"
  exit 0
fi

# Refresh data layer first (non-fatal if it fails)
if python3 "$DASH/scripts/rebuild_data.py" 2>/dev/null; then
  dim "[INTEL] data layer refreshed"
else
  dim "[INTEL] (rebuild skipped or failed -- serving existing data.js)"
fi

banner
echo ""

# Open browser ~1.2s after the server boots
( sleep 1.2 && try_open "$URL" >/dev/null 2>&1 ) &

cd "$ROOT" || { echo "[INTEL] 06_DEVELOPMENT/everlight_os/intel_center missing: $ROOT"; exit 1; }
exec python3 -m http.server "$PORT" --bind "$BIND"
