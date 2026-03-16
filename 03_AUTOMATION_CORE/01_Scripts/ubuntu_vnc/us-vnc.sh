#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-1}"
GEOMETRY="${GEOMETRY:-1280x720}"
DEPTH="${DEPTH:-24}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VNC_PORT="${VNC_PORT:-$((5900 + DISPLAY_NUM))}"
VNC_SERVER="${VNC_SERVER:-/usr/bin/vncserver}"
NOVNC_PROXY="${NOVNC_PROXY:-/usr/share/novnc/utils/novnc_proxy}"
LOG_DIR="${LOG_DIR:-/mnt/sdcard/AA_MY_DRIVE/_logs/ubuntu_vnc}"
X_LOCK="/tmp/.X${DISPLAY_NUM}-lock"
X_SOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"

log() {
  printf '[us-vnc] %s\n' "$*"
}

check_deps() {
  command -v bash >/dev/null 2>&1 || { echo "bash is required"; exit 1; }
  command -v "$VNC_SERVER" >/dev/null 2>&1 || { echo "vncserver not found at $VNC_SERVER"; exit 1; }
  command -v "$NOVNC_PROXY" >/dev/null 2>&1 || { echo "novnc_proxy not found at $NOVNC_PROXY"; exit 1; }
}

check_port() {
  local port="$1"
  if command -v timeout >/dev/null 2>&1; then
    timeout 2 bash -c "</dev/tcp/127.0.0.1/${port}" >/dev/null 2>&1
  else
    bash -c "</dev/tcp/127.0.0.1/${port}" >/dev/null 2>&1
  fi
}

kill_conflicts() {
  log "Stopping conflicting VNC/noVNC processes..."
  "$VNC_SERVER" -kill ":${DISPLAY_NUM}" >/dev/null 2>&1 || true
  pkill -f "Xtigervnc.*:${DISPLAY_NUM}" >/dev/null 2>&1 || true
  pkill -f "Xvnc.*:${DISPLAY_NUM}" >/dev/null 2>&1 || true
  pkill -f "novnc_proxy.*${NOVNC_PORT}" >/dev/null 2>&1 || true
  pkill -f "websockify.*${NOVNC_PORT}" >/dev/null 2>&1 || true
  rm -f "$X_LOCK" "$X_SOCKET" >/dev/null 2>&1 || true
}

start_vnc() {
  log "Starting TigerVNC on :${DISPLAY_NUM} (port ${VNC_PORT})..."
  "$VNC_SERVER" ":${DISPLAY_NUM}" -geometry "$GEOMETRY" -depth "$DEPTH" -localhost no
}

start_novnc_bg() {
  mkdir -p "$LOG_DIR"
  log "Starting noVNC on 0.0.0.0:${NOVNC_PORT} -> 127.0.0.1:${VNC_PORT}..."
  nohup "$NOVNC_PROXY" \
    --vnc "127.0.0.1:${VNC_PORT}" \
    --listen "0.0.0.0:${NOVNC_PORT}" \
    >>"$LOG_DIR/novnc.log" 2>&1 &
  sleep 1
}

start_interactive() {
  check_deps
  mkdir -p "$LOG_DIR"
  kill_conflicts
  start_vnc
  start_novnc_bg

  if check_port "$VNC_PORT" && check_port "$NOVNC_PORT"; then
    local ip=""
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    log "READY"
    log "Local URL: http://127.0.0.1:${NOVNC_PORT}/vnc.html"
    if [ -n "$ip" ]; then
      log "LAN URL:   http://${ip}:${NOVNC_PORT}/vnc.html"
    fi
  else
    log "Startup check failed. See $LOG_DIR/novnc.log"
    exit 1
  fi
}

run_service() {
  check_deps
  mkdir -p "$LOG_DIR"
  kill_conflicts
  start_vnc
  log "Running noVNC foreground mode for systemd..."
  exec "$NOVNC_PROXY" --vnc "127.0.0.1:${VNC_PORT}" --listen "0.0.0.0:${NOVNC_PORT}"
}

stop_all() {
  log "Stopping noVNC and VNC..."
  pkill -f "novnc_proxy.*${NOVNC_PORT}" >/dev/null 2>&1 || true
  pkill -f "websockify.*${NOVNC_PORT}" >/dev/null 2>&1 || true
  "$VNC_SERVER" -kill ":${DISPLAY_NUM}" >/dev/null 2>&1 || true
  pkill -f "Xtigervnc.*:${DISPLAY_NUM}" >/dev/null 2>&1 || true
  pkill -f "Xvnc.*:${DISPLAY_NUM}" >/dev/null 2>&1 || true
  rm -f "$X_LOCK" "$X_SOCKET" >/dev/null 2>&1 || true
}

status_all() {
  if check_port "$VNC_PORT"; then
    log "VNC port ${VNC_PORT}: OPEN"
  else
    log "VNC port ${VNC_PORT}: CLOSED"
  fi

  if check_port "$NOVNC_PORT"; then
    log "noVNC port ${NOVNC_PORT}: OPEN"
  else
    log "noVNC port ${NOVNC_PORT}: CLOSED"
  fi
}

usage() {
  cat <<EOF
Usage: $0 [start|stop|restart|status|service]
  start    Start VNC + noVNC in background (for alias 'us')
  stop     Stop VNC + noVNC
  restart  Restart both
  status   Show current port status
  service  Start for systemd (noVNC in foreground)
EOF
}

case "${1:-start}" in
  start)
    start_interactive
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    start_interactive
    ;;
  status)
    status_all
    ;;
  service)
    run_service
    ;;
  *)
    usage
    exit 1
    ;;
esac
