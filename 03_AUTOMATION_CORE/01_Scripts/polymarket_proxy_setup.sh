#!/usr/bin/env bash
# Set up a non-US HTTPS egress proxy on a fresh EU VPS (Ubuntu/Debian) so the
# Polymarket bot's order POSTs exit from a German IP (bypassing the US geoblock).
#
# Uses tinyproxy in CONNECT-tunnel mode: for HTTPS it pipes ENCRYPTED bytes only
# -- it never decrypts, so it CANNOT see API creds or order contents (TLS stays
# end-to-end). The VPS just provides the non-US exit IP.
#
# Run ON THE VPS (as root):  bash polymarket_proxy_setup.sh <ALLOWED_SRC_IP>
# Then on the bot host set:   egress.proxy_url: "http://<VPS_IP>:8888"
set -euo pipefail
PORT="${PORT:-8888}"
ALLOW_SRC="${1:-0.0.0.0/0}"   # ideally the bot host's public IP; default open (lock down!)

apt-get update -y
apt-get install -y tinyproxy

cat > /etc/tinyproxy/tinyproxy.conf <<EOF
User tinyproxy
Group tinyproxy
Port ${PORT}
Timeout 600
# CONNECT tunnel for HTTPS to Polymarket (encrypted passthrough, no decryption)
ConnectPort 443
# allow only the bot host (lock this down to your bot's IP for security)
Allow ${ALLOW_SRC}
Allow 127.0.0.1
# no content logging
LogLevel Critical
DisableViaHeader Yes
EOF

systemctl enable tinyproxy
systemctl restart tinyproxy
echo "tinyproxy up on :${PORT} -- CONNECT 443 allowed from ${ALLOW_SRC}"
echo "test from bot host:  curl -x http://<VPS_IP>:${PORT} https://clob.polymarket.com/  -I"
echo "then set egress.proxy_url: http://<VPS_IP>:${PORT} in config.yaml"
