#!/usr/bin/env bash
set -euo pipefail

# ---------------- DEBUG MODE ----------------
DEBUG="${DEBUG:-0}"

if [[ "$DEBUG" == "1" ]]; then
  # Print commands + line numbers as they run
  export PS4='+(${BASH_SOURCE}:${LINENO}) '
  set -x
fi

debug_shell() {
  local msg="${1:-Dropped into debug shell.}"
  echo
  echo "🛠 DEBUG: $msg"
  echo "PWD: $PWD"
  echo "LOG: $LOG_FILE"
  echo "PIDFILE: $PID_FILE"
  echo "Tip: tail -n 200 -f \"$LOG_FILE\""
  echo
  bash --noprofile --norc -i
}


# ─────────────────────────────────────────────────────────────
# 🌿 Mountain Gardens POS Launcher
# - Always runs from .venv
# - start/stop/restart/status/logs
# - writes PID_FILE + logs
# - optional: auto-open browser
# ─────────────────────────────────────────────────────────────

APP_NAME="Mountain Gardens POS"
APP_DIR="/home/mgn/Projects/Mountain Gardens Nursery POS"
VENV_DIR="$APP_DIR/.venv"
PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"
URL="http://${HOST}:${PORT}"

LOG_DIR="$APP_DIR/logs"
LOG_FILE="$LOG_DIR/pos.log"
PID_FILE="$APP_DIR/.pos.pid"

# Colors (no-fail if terminal doesn't support)
RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; BLU=$'\033[34m'; MAG=$'\033[35m'; CYN=$'\033[36m'; DIM=$'\033[2m'; RST=$'\033[0m'

# ---- Auto-open logs on failure (launcher errors) ----
open_log_viewer() {
  local LOG_FILE="$1"

  # Prefer kwrite (since that's what you ended up liking)
  if command -v kwrite >/dev/null 2>&1; then
    kwrite "$LOG_FILE" >/dev/null 2>&1 &
    return
  fi

  # Prefer kitty if available (new OS window tailing logs)
  if command -v kitty >/dev/null 2>&1; then
    kitty --title "MGN POS Log" sh -lc "echo '=== $LOG_FILE ==='; tail -n 300 -f '$LOG_FILE'"
    return
  fi

  # GNOME Terminal fallback
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="MGN POS Log" -- bash -lc "echo '=== $LOG_FILE ==='; tail -n 300 -f '$LOG_FILE'"
    return
  fi

  # Terminal fallback
  tail -n 200 "$LOG_FILE"
}

on_fail() {
  # Avoid the trap causing a loop if the viewer fails
  set +e
  echo "❌ START_POS failed (line $1). Opening log: $LOG_FILE"
  [ -f "$LOG_FILE" ] || touch "$LOG_FILE" 2>/dev/null || true
  open_log_viewer "$LOG_FILE"
}
trap 'on_fail $LINENO' ERR



banner() {
  echo "${GRN}"
  echo "  🌿  Mountain Gardens POS"
  echo "  ─────────────────────────"
  echo "${RST}"
}

die() { echo "${RED}✖ $*${RST}" >&2; exit 1; }
ok()  { echo "${GRN}✔ $*${RST}"; }
info(){ echo "${CYN}➜ $*${RST}"; }
warn(){ echo "${YLW}⚠ $*${RST}"; }

ensure_dirs() {
  mkdir -p "$LOG_DIR"
}

ensure_venv() {
  if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found. Install it: sudo apt install -y python3 python3-venv"
  fi

  if [ ! -x "$PY" ]; then
    info "Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi

  # Upgrade pip quietly (won't fail script if network issues)
  "$PY" -m pip install -U pip >/dev/null 2>&1 || true
}

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

status() {
  banner
  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    ok "$APP_NAME is running (PID_FILE $pid) at $URL"
  else
    warn "$APP_NAME is not running"
  fi
}

stop() {
  banner
  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    info "Stopping PID_FILE $pid ..."
    kill "$pid" >/dev/null 2>&1 || true

    # wait up to ~3s
    for _ in {1..30}; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        sleep 0.1
      else
        break
      fi
    done

    if kill -0 "$pid" >/dev/null 2>&1; then
      warn "Did not stop gracefully; killing hard..."
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi

    rm -f "$PID_FILE"
    ok "Stopped"
  else
    warn "Not running"
  fi
}

tail_logs() {
  banner
  if [ ! -f "$LOG_FILE" ]; then
    warn "No log file yet: $LOG_FILE"
    exit 0
  fi
  info "Tailing logs: $LOG_FILE"
  tail -n 200 -f "$LOG_FILE"
}

open_browser() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
}

start() {
  banner
  ensure_dirs
  ensure_venv

  cd "$APP_DIR"

  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    warn "Already running (PID_FILE $pid). Use: ./START_POS.sh restart"
    exit 0
  fi

  # Optional auto-install requirements if file exists (safe / non-fatal)
  if [ -f "$APP_DIR/requirements.txt" ]; then
    info "Installing requirements (if needed)..."
    "$PY" -m pip install -r "$APP_DIR/requirements.txt" >/dev/null 2>&1 || true
  fi

  info "Starting on $URL"
  info "Logging to $LOG_FILE"

  # Start in background, record PID_FILE, write logs
  # Using exec in a subshell ensures PID_FILE file points to python process.
  (
    exec "$PY" "$APP_DIR/MGN_APP.py"
  ) >>"$LOG_FILE" 2>&1 &

  echo $! > "$PID_FILE"

  # Small warmup
  sleep 0.4

  if is_running; then
    ok "Started (PID_FILE $(cat "$PID_FILE"))"
    info "Open: $URL"
  else
    warn "It may have failed to start. Check logs:"
    echo "  $LOG_FILE"
    exit 1
  fi
}

restart() {
  stop || true
  start
}

help_msg() {
  cat <<EOF
${APP_NAME} launcher

Usage:
  ./START_POS.sh start        Start POS (default)
  ./START_POS.sh stop         Stop POS
  ./START_POS.sh restart      Restart POS
  ./START_POS.sh status       Show status
  ./START_POS.sh logs         Tail logs

Env overrides:
  HOST=127.0.0.1 PORT=5000

Tip:
  To compile-check with venv python:
    ./.venv/bin/python -m py_compile POS_CORE.py
EOF
}

cmd="${1:-start}"

case "$cmd" in
  start)   start ;;
  stop)    stop ;;
  restart) restart ;;
  status)  status ;;
  logs)    tail_logs ;;
  help|-h|--help) help_msg ;;
  *)
    warn "Unknown command: $cmd"
    help_msg
    exit 2
    ;;
esac
