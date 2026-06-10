#!/usr/bin/env bash
# serve_open_webui.sh -- launcher for Open WebUI on :2800
#
# Storage doctrine (split because Android sdcard is mounted noexec):
#   - Package code:  /root/open_webui_pkgs/      (proot Linux fs, .so files load)
#   - User data:     /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/open_webui_data/
#                    (sdcard, visible to VimWiki, Termux, AceMagician sync)
#   - Launchers:     /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/
#                    (this file, on sdcard)
#
# Same pattern Rich's Emacs uses (~/.emacs.d on /root, org files on sdcard).
# See feedback_no_venvs_on_root_filesystem.md for the doctrine + nuance.

set -u

ROOT_WS=/mnt/sdcard/AA_MY_DRIVE
PKG_DIR=/root/open_webui_pkgs
DATA_DIR="$ROOT_WS/06_DEVELOPMENT/open_webui_data"
PORT="${OPEN_WEBUI_PORT:-2800}"
LOG="/tmp/svc_2800.log"

PY312=$(ls /root/.local/share/uv/python/cpython-3.12*/bin/python3.12 2>/dev/null | head -1)
if [ -z "$PY312" ]; then
  echo "FATAL: no Python 3.12 found. Run: uv python install 3.12" >&2
  exit 1
fi

mkdir -p "$DATA_DIR"

# Inherit Everlight credentials (per system-wide .env doctrine)
if [ -f "$ROOT_WS/03_AUTOMATION_CORE/03_Credentials/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_WS/03_AUTOMATION_CORE/03_Credentials/.env"
  set +a
fi

export DATA_DIR
export WEBUI_AUTH=true
export WEBUI_NAME="Everlight Ultra Mind"
export PORT="$PORT"
export HOST=127.0.0.1
export PYTHONPATH="$PKG_DIR"

cd "$PKG_DIR" || exit 1

exec "$PY312" -m uvicorn open_webui.main:app \
  --host 127.0.0.1 \
  --port "$PORT" \
  --log-level info \
  >> "$LOG" 2>&1
