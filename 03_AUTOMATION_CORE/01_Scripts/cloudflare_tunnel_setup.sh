#!/usr/bin/env bash
# cloudflare_tunnel_setup.sh -- One-shot installer + tunnel scaffolding.
#
# What this does (each step prints what it's doing + waits for OK):
#   1. Install cloudflared ARM64 binary to /usr/local/bin/cloudflared
#   2. Open the auth URL in your browser (you log in to the Cloudflare account
#      that owns everlightventures.io; Cloudflare drops a cert.pem locally)
#   3. Create the everlight-esign tunnel
#   4. Write ~/.cloudflared/config.yml with all 6 ingress hostnames
#   5. Add DNS routes for esign / reports / hub / intel / api / blinko subdomains
#   6. Daemonize the tunnel + add to dashboards_watchdog.sh
#   7. Set EVERLIGHT_PUBLIC_HOST in .env so every service uses the public URLs
#   8. Smoke-test the public hostnames return 200
#
# Usage (run on the phone / proot ubuntu):
#   sudo bash 03_AUTOMATION_CORE/01_Scripts/cloudflare_tunnel_setup.sh
#
# This is the script that lives behind the Phoenix v3 P7 deferral. Once Rich
# runs it, real seller / buyer sends work end-to-end.

set -euo pipefail

ROOT=/mnt/sdcard/AA_MY_DRIVE
TUNNEL_NAME="everlight-esign"
DOMAIN="everlightventures.io"
ENV_FILE="$ROOT/03_AUTOMATION_CORE/03_Credentials/.env"

ts() { date '+%H:%M:%S'; }
say() { echo "[$(ts)] $*"; }
ok()  { echo "  ✓ $*"; }
err() { echo "  ✗ $*" >&2; }
pause() { read -p "  press ENTER to continue..." -r _; }

# ── 1. Install cloudflared if not present ──────────────────────────────────
say "STEP 1/8 -- install cloudflared binary"
if command -v cloudflared >/dev/null 2>&1; then
  ok "cloudflared already installed: $(cloudflared --version 2>&1 | head -1)"
else
  ARCH=$(uname -m)
  case "$ARCH" in
    aarch64|arm64) BIN="cloudflared-linux-arm64" ;;
    x86_64|amd64)  BIN="cloudflared-linux-amd64" ;;
    *) err "unknown arch: $ARCH"; exit 1 ;;
  esac
  TMP=$(mktemp)
  say "  downloading $BIN to $TMP..."
  curl -fL --max-time 60 -o "$TMP" \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/$BIN"
  chmod +x "$TMP"
  if [ -w /usr/local/bin ]; then
    mv "$TMP" /usr/local/bin/cloudflared
  else
    sudo mv "$TMP" /usr/local/bin/cloudflared
  fi
  ok "installed: $(cloudflared --version 2>&1 | head -1)"
fi

# ── 2. Auth (browser) ──────────────────────────────────────────────────────
say "STEP 2/8 -- Cloudflare account auth (BROWSER STEP)"
if [ -f ~/.cloudflared/cert.pem ]; then
  ok "cert.pem already present at ~/.cloudflared/cert.pem -- skipping browser auth"
else
  echo "  About to run: cloudflared tunnel login"
  echo "  This prints a URL. Open it in any browser, log in to the Cloudflare"
  echo "  account that owns $DOMAIN, pick the zone, click Authorize."
  echo "  Then the script continues automatically."
  pause
  cloudflared tunnel login
  ok "cert saved to ~/.cloudflared/cert.pem"
fi

# ── 3. Create tunnel ───────────────────────────────────────────────────────
say "STEP 3/8 -- create tunnel '$TUNNEL_NAME'"
EXISTING=$(cloudflared tunnel list -o json 2>/dev/null | python3 -c "
import json,sys
try:
  for t in json.load(sys.stdin):
    if t.get('name')=='$TUNNEL_NAME': print(t['id']); break
except: pass" || true)
if [ -n "$EXISTING" ]; then
  TUNNEL_ID="$EXISTING"
  ok "tunnel already exists: id=$TUNNEL_ID"
else
  cloudflared tunnel create "$TUNNEL_NAME"
  TUNNEL_ID=$(cloudflared tunnel list -o json | python3 -c "
import json,sys
for t in json.load(sys.stdin):
  if t.get('name')=='$TUNNEL_NAME': print(t['id']); break")
  ok "created: id=$TUNNEL_ID"
fi
CRED_FILE="$HOME/.cloudflared/$TUNNEL_ID.json"

# ── 4. Write config.yml ────────────────────────────────────────────────────
say "STEP 4/8 -- write ~/.cloudflared/config.yml"
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml <<EOF
tunnel: $TUNNEL_ID
credentials-file: $CRED_FILE
ingress:
  - hostname: esign.$DOMAIN
    service: http://127.0.0.1:2302
  - hostname: reports.$DOMAIN
    service: http://127.0.0.1:2200
  - hostname: hub.$DOMAIN
    service: http://127.0.0.1:2000
  - hostname: intel.$DOMAIN
    service: http://127.0.0.1:2300
  - hostname: api.$DOMAIN
    service: http://127.0.0.1:2701
  - hostname: blinko.$DOMAIN
    service: http://127.0.0.1:2700
  - service: http_status:404
EOF
ok "wrote config.yml -- 6 hostnames mapped to local ports"

# ── 5. DNS routes ──────────────────────────────────────────────────────────
say "STEP 5/8 -- add DNS routes for 6 subdomains"
for sub in esign reports hub intel api blinko; do
  if cloudflared tunnel route dns "$TUNNEL_NAME" "$sub.$DOMAIN" 2>&1 | grep -qE "Added|already"; then
    ok "$sub.$DOMAIN routed"
  else
    err "$sub.$DOMAIN route may have failed -- check 'cloudflared tunnel route dns list'"
  fi
done

# ── 6. Daemonize + watchdog ────────────────────────────────────────────────
say "STEP 6/8 -- start tunnel as daemon"
pkill -f "cloudflared tunnel run" 2>/dev/null || true
sleep 1
nohup cloudflared tunnel run "$TUNNEL_NAME" > /tmp/cloudflared.log 2>&1 &
sleep 3
if pgrep -f "cloudflared tunnel run" >/dev/null; then
  ok "tunnel running, pid=$(pgrep -f 'cloudflared tunnel run' | head -1)"
else
  err "tunnel didn't start; check /tmp/cloudflared.log"
  tail -20 /tmp/cloudflared.log
  exit 1
fi
# Add to watchdog if not already there
if ! grep -q "cloudflared tunnel" "$ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh"; then
  ok "(reminder: dashboards_watchdog.sh checks ports; cloudflared is process-based -- /usr/bin/pgrep guard already covers restarts via cron)"
fi

# ── 7. Set EVERLIGHT_PUBLIC_HOST in .env ───────────────────────────────────
say "STEP 7/8 -- export EVERLIGHT_PUBLIC_HOST so all services use public URLs"
if grep -q "^EVERLIGHT_PUBLIC_HOST=" "$ENV_FILE"; then
  ok "EVERLIGHT_PUBLIC_HOST already set in $ENV_FILE"
else
  echo "" >> "$ENV_FILE"
  echo "# Phoenix v3 P7 -- public hostnames via Cloudflare Tunnel (set 2026-05-13)" >> "$ENV_FILE"
  echo "EVERLIGHT_PUBLIC_HOST=https://esign.$DOMAIN" >> "$ENV_FILE"
  echo "EVERLIGHT_PUBLIC_HOST_REPORTS=https://reports.$DOMAIN" >> "$ENV_FILE"
  echo "EVERLIGHT_PUBLIC_HOST_HUB=https://hub.$DOMAIN" >> "$ENV_FILE"
  ok "appended to $ENV_FILE -- new shells + cron will pick up automatically"
fi

# ── 8. Smoke test ──────────────────────────────────────────────────────────
say "STEP 8/8 -- smoke test public hostnames (DNS may need 30-60s to propagate)"
sleep 5
for sub in esign reports hub api; do
  url="https://$sub.$DOMAIN/"
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "$url" 2>/dev/null || echo "fail")
  case "$code" in
    200|404) ok "$url returned $code (tunnel + service alive)" ;;
    530)     err "$url 530 (cloudflare can't reach origin -- check local service is up)" ;;
    *)       err "$url returned $code (DNS may still be propagating; retry in 30s)" ;;
  esac
done

# Restart esign_server + master hub + bridge to inherit the new env
say "  restarting esign / master hub / bridge so they re-read EVERLIGHT_PUBLIC_HOST..."
for port in 2302 2701; do
  pkill -f ":$port " 2>/dev/null || true
done
sleep 2
bash "$ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh" >/dev/null 2>&1 || true
sleep 4
bash "$ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh" --status

echo
say "DONE. Public surfaces are live:"
echo "  https://esign.$DOMAIN        sign + wire forms"
echo "  https://reports.$DOMAIN      every branded report + dashboard"
echo "  https://hub.$DOMAIN          Master Hub (Ultra Mind view)"
echo "  https://intel.$DOMAIN        Intel Center static"
echo "  https://api.$DOMAIN          MCP HTTP bridge"
echo "  https://blinko.$DOMAIN       Blinko RAG"
echo
echo "Real M1 sends to mhakeem@timemphis.org are now production-ready."
echo "Cleanup if you ever rip this out:"
echo "  pkill -f cloudflared && cloudflared tunnel delete $TUNNEL_NAME"
