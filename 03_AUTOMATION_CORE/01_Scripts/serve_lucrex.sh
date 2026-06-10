#!/usr/bin/env bash
# serve_lucrex.sh -- local home for the Lucrex Command Center (Next.js, 2700 band).
# Rehomed 2026-05-24 from the dead Oracle mother (129.159.38.250:8080/lucrex/).
# Private by default per Network Binding Doctrine: binds 127.0.0.1 unless EV_BIND set.
#
# REALITY (2026-05-24): the phone's proot CANNOT run npm/pnpm install -- they SIGSEGV
# (node itself works fine). And lucrex-os has API routes (blinko/django/trading proxies)
# so it is NOT statically exportable -- it needs a node runtime at request time.
# Therefore:
#   * BUILD happens on e5-mother (real Linux) via `build-remote`, artifacts rsync back.
#   * SERVE happens locally with `next start` (pure node -- works on the phone).
#   * Until artifacts exist, a branded placeholder keeps :2700 live + honest.
#
# Usage:
#   bash serve_lucrex.sh start         # next start from artifacts, else placeholder
#   bash serve_lucrex.sh build-remote  # build on e5-mother, pull node_modules + .next back
#   bash serve_lucrex.sh placeholder   # serve the branded "build pending" page
#   bash serve_lucrex.sh sync | stop | status | logs

set -u

PORT="${LUCREX_PORT:-2702}"   # 2700 = local blinko_lite, 2701 = MCP bridge; Lucrex sits at 2702 in-band
BIND="${EV_BIND:-${LUCREX_BIND:-127.0.0.1}}"
APP_SRC="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/lucrex-os"          # editable source (sdcard)
RUN_DIR="${LUCREX_RUN_DIR:-/root/.cache/lucrex-run}"                # native fs (symlinks work)
PLACEHOLDER="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/serve_helpers/lucrex_placeholder"
PIDFILE="/tmp/serve_lucrex.pid"
LOGFILE="/tmp/serve_lucrex.log"

# e5-mother coords (build host). Sourced from the mesh keystone if present.
MESH="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/mesh/hive_hosts.env"
[ -f "$MESH" ] && source "$MESH" 2>/dev/null
E5_HOST="${HIVE_PROD_HOST:-e5-mother}"
E5_USER="${HIVE_PROD_USER:-ubuntu}"
E5_PORT="${HIVE_PROD_SSH_PORT:-2222}"
E5_KEY="${HIVE_SSH_KEY:-/root/.ssh/github_deploy}"
E5_REMOTE="/home/${E5_USER}/lucrex-os"

cmd="${1:-start}"

is_running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

e5_up() {
  getent hosts "$E5_HOST" >/dev/null 2>&1 || [[ "$E5_HOST" =~ ^[0-9.]+$ ]] || return 1
  ssh -o ConnectTimeout=6 -o BatchMode=yes -p "$E5_PORT" -i "$E5_KEY" "$E5_USER@$E5_HOST" true 2>/dev/null
}

sync_src() {
  [ -d "$APP_SRC" ] || { echo "APP_SRC $APP_SRC missing"; exit 1; }
  mkdir -p "$RUN_DIR"
  # vfat-style sdcard perms cannot be preserved onto native fs -> force sane perms.
  rsync -rltD --delete --no-perms --no-owner --no-group --chmod=ugo=rwX \
    --exclude 'node_modules' --exclude '.next' --exclude '.git' \
    "$APP_SRC/" "$RUN_DIR/"
}

# Build on e5-mother, pull node_modules + .next back to the phone's run dir.
build_remote() {
  if ! e5_up; then
    echo "e5-mother ($E5_HOST) unreachable -- cannot build remotely right now."
    echo "When the tailnet is up, re-run: bash $0 build-remote"
    return 1
  fi
  echo "syncing source to e5-mother..."
  rsync -rltz --delete --exclude node_modules --exclude .next --exclude .git \
    -e "ssh -o ConnectTimeout=10 -p $E5_PORT -i $E5_KEY" \
    "$APP_SRC/" "$E5_USER@$E5_HOST:$E5_REMOTE/"
  echo "installing + building on e5-mother..."
  ssh -o ConnectTimeout=10 -p "$E5_PORT" -i "$E5_KEY" "$E5_USER@$E5_HOST" \
    "cd $E5_REMOTE && (npm install --no-audit --no-fund || corepack pnpm install) && npm run build" || {
      echo "remote build FAILED"; return 1; }
  echo "pulling artifacts back to $RUN_DIR..."
  mkdir -p "$RUN_DIR"
  rsync -rltz -e "ssh -o ConnectTimeout=10 -p $E5_PORT -i $E5_KEY" \
    "$E5_USER@$E5_HOST:$E5_REMOTE/node_modules/" "$RUN_DIR/node_modules/"
  rsync -rltz -e "ssh -o ConnectTimeout=10 -p $E5_PORT -i $E5_KEY" \
    "$E5_USER@$E5_HOST:$E5_REMOTE/.next/" "$RUN_DIR/.next/"
  echo "artifacts pulled. run: bash $0 start"
}

launch_node() {   # next start from prebuilt .next (pure node, no install)
  cd "$RUN_DIR" || return 1
  HOSTNAME="$BIND" PORT="$PORT" nohup npm run start > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"; sleep 1
  echo "started pid=$(cat "$PIDFILE") mode=next-start  http://$BIND:$PORT/"
}

launch_placeholder() {   # branded "build pending" page, pure python, no node
  cd "$PLACEHOLDER" || { echo "placeholder dir missing"; exit 1; }
  nohup python3 -m http.server "$PORT" --bind "$BIND" --directory "$PLACEHOLDER" > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"; sleep 0.5
  echo "started pid=$(cat "$PIDFILE") mode=placeholder  http://$BIND:$PORT/  (full app pending build-remote)"
}

start() {
  if is_running; then echo "already running (pid=$(cat "$PIDFILE")) on http://$BIND:$PORT/"; return 0; fi
  sync_src
  if [ -d "$RUN_DIR/.next" ] && [ -d "$RUN_DIR/node_modules/next" ]; then
    launch_node
  else
    echo "no build artifacts in $RUN_DIR -- serving placeholder."
    echo "to go live: bash $0 build-remote   (builds on e5-mother)"
    launch_placeholder
  fi
}

stop() {
  if ! is_running; then echo "not running"; rm -f "$PIDFILE"; return 0; fi
  pid="$(cat "$PIDFILE")"
  kill -- "-$(ps -o pgid= "$pid" 2>/dev/null | tr -d ' ')" 2>/dev/null || kill "$pid" 2>/dev/null
  sleep 0.5; kill -9 "$pid" 2>/dev/null; rm -f "$PIDFILE"
  echo "stopped (pid was $pid)"
}

status() {
  if is_running; then
    echo "running pid=$(cat "$PIDFILE") -- http://$BIND:$PORT/"
    [ -d "$RUN_DIR/.next" ] && echo "  mode: full app (next start)" || echo "  mode: placeholder (build pending)"
  else echo "not running"; fi
}

case "$cmd" in
  start)        start ;;
  build-remote) build_remote ;;
  placeholder)  stop 2>/dev/null; launch_placeholder ;;
  sync)         sync_src; echo "synced $APP_SRC -> $RUN_DIR" ;;
  stop)         stop ;;
  restart)      stop; start ;;
  status)       status ;;
  logs)         tail -50 "$LOGFILE" 2>/dev/null || echo "no log yet" ;;
  *) echo "usage: $0 {start|build-remote|placeholder|sync|stop|restart|status|logs}"; exit 1 ;;
esac
