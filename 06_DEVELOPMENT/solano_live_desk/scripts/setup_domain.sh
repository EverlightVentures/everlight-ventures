#!/usr/bin/env bash
# One-time Cloudflare Tunnel setup so the dashboard lives at a memorable URL:
#   https://survival.everlightventures.io  (no IP, no tailscale needed)
# Run this ON e5. The login step (#1) opens a URL you approve in a browser once.
set -euo pipefail
CF="$HOME/.local/bin/cloudflared"
DOMAIN="survival.everlightventures.io"
NAME="solano"

echo "[1/5] Cloudflare login (approve the URL it prints, pick everlightventures.io)..."
"$CF" tunnel login

echo "[2/5] Create tunnel '$NAME'..."
"$CF" tunnel create "$NAME" 2>/dev/null || true
TID="$("$CF" tunnel list | awk -v n="$NAME" '$2==n{print $1}')"

echo "[3/5] Route DNS $DOMAIN -> tunnel..."
"$CF" tunnel route dns "$NAME" "$DOMAIN"

echo "[4/5] Write config (tunnel -> localhost:2600)..."
mkdir -p "$HOME/.cloudflared"
cat > "$HOME/.cloudflared/config.yml" <<CFG
tunnel: $TID
credentials-file: $HOME/.cloudflared/$TID.json
ingress:
  - hostname: $DOMAIN
    service: http://127.0.0.1:2600
  - service: http_status:404
CFG

echo "[5/5] Install + start the tunnel service (always-on)..."
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/solano-tunnel.service" <<UNIT
[Unit]
Description=Cloudflare tunnel for Solano Live Desk
After=network-online.target
[Service]
ExecStart=%h/.local/bin/cloudflared tunnel run $NAME
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now solano-tunnel.service

echo "DONE -> https://$DOMAIN  (give DNS a minute)."
echo "LOCK IT DOWN: Cloudflare dashboard -> Zero Trust -> Access -> Applications ->"
echo "  add '$DOMAIN' with an email-OTP policy for your address, so only you + agents get in."
