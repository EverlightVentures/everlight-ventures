#!/usr/bin/env bash
# install_open_webui.sh -- Auto-runs on AceMagician PC the moment it's online.
#
# Why here: Open WebUI's native extensions can't load from the phone's sdcard
# (Android security policy). AceMagician is the right host -- Arch Linux,
# native filesystem, more RAM. Exposed back to the phone via tailnet.
#
# Queued: 2026-05-13 by Phoenix v3 P8.
# Will be executed by device_update_runner.sh on next reachability tick.

set -euo pipefail

PORT=2800
DATA_DIR="$HOME/open_webui_data"
LOG=/tmp/open_webui_install.log

ts() { date '+%H:%M:%S'; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

say "STEP 1/4 -- check Python 3.11 or 3.12 availability"
PY=""
for cand in python3.12 python3.11; do
  if command -v "$cand" >/dev/null 2>&1; then
    PY=$(command -v "$cand")
    say "  using $PY ($($PY --version))"
    break
  fi
done
if [ -z "$PY" ]; then
  say "  no python 3.11/3.12 found, installing 3.12 via pacman..."
  sudo pacman -Sy --noconfirm python312 2>&1 | tail -5 | tee -a "$LOG" || {
    say "  pacman python312 unavailable, falling back to uv"
    if ! command -v uv >/dev/null 2>&1; then
      curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    uv python install 3.12
    PY=$(uv python find 3.12)
  }
fi

say "STEP 2/4 -- pip install open-webui (~3-5 min on PC)"
"$PY" -m pip install --user --upgrade open-webui 2>&1 | tail -5 | tee -a "$LOG"

# Bind policy: 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md
# AceMagician runs on the tailnet. Default 127.0.0.1; set EV_BIND=0.0.0.0
# only after confirming Tailscale ACLs are restricting access.
WEBUI_BIND="${EV_BIND:-127.0.0.1}"
say "STEP 3/4 -- launch on $PORT (HOST=$WEBUI_BIND)"
mkdir -p "$DATA_DIR"
pkill -f "open-webui serve" 2>/dev/null || true
sleep 1

DATA_DIR="$DATA_DIR" \
WEBUI_AUTH=true \
WEBUI_NAME="Everlight Ultra Mind" \
PORT="$PORT" \
HOST="$WEBUI_BIND" \
nohup "$PY" -m open_webui serve --port "$PORT" --host "$WEBUI_BIND" \
  > /tmp/svc_open_webui.log 2>&1 &

say "  spawned, waiting for first-time DB init..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w "%{http_code}" -m 2 "http://127.0.0.1:$PORT/" | grep -qE "200|302|307|404"; then
    say "  Open WebUI live at http://127.0.0.1:$PORT/"
    say "  From phone: http://acemagician:$PORT/  or  http://100.93.253.49:$PORT/"
    break
  fi
  sleep 5
done

say "STEP 4/4 -- ensure restart on boot (systemd user unit)"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/open-webui.service" <<UNIT
[Unit]
Description=Open WebUI (Everlight Ultra Mind chat surface)
After=network-online.target

[Service]
Type=simple
Environment=DATA_DIR=$DATA_DIR
Environment=WEBUI_AUTH=true
Environment=WEBUI_NAME=Everlight Ultra Mind
Environment=PORT=$PORT
Environment=HOST=$WEBUI_BIND
ExecStart=$PY -m open_webui serve --port $PORT --host $WEBUI_BIND
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now open-webui.service 2>/dev/null || true
loginctl enable-linger "$USER" 2>/dev/null || true

say "DONE. Open WebUI installed + auto-restart enabled."
echo
echo "Reach from phone:"
echo "  http://acemagician:$PORT/    (preferred -- tailnet hostname)"
echo "  http://100.93.253.49:$PORT/  (fallback -- raw tailnet IP)"
echo
echo "First-run setup: visit one of the URLs above, create admin account."
echo "Then add API keys: Settings → Connections (use values from .env)"
