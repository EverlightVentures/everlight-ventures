#!/bin/bash
# =============================================================================
# setup_ngrok.sh -- Install ngrok and expose Nextcloud on port 8080
# Run INSIDE PRoot-Ubuntu after Nextcloud is running.
#
# Requirements:
#   1. Sign up at https://ngrok.com (free tier is fine)
#   2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
#   3. Set NGROK_AUTHTOKEN below or export it before running this script
# =============================================================================

NGROK_AUTHTOKEN="${NGROK_AUTHTOKEN:-}"   # set env var or paste token here
NGROK_PORT=8080
NC_WEB_DIR="/var/www/nextcloud"
LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud"
NGROK_LOG="$LOG_DIR/ngrok.log"
NGROK_BIN="/usr/local/bin/ngrok"

mkdir -p "$LOG_DIR"

# ---- Install ngrok if missing -----------------------------------------------
if [ ! -f "$NGROK_BIN" ]; then
    echo "Installing ngrok (ARM64)..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        NGROK_PKG="ngrok-v3-stable-linux-arm64.tgz"
    else
        NGROK_PKG="ngrok-v3-stable-linux-amd64.tgz"
    fi
    wget -q -O /tmp/ngrok.tgz \
        "https://bin.equinox.io/c/bNyj1mQVY4c/${NGROK_PKG}"
    tar -xzf /tmp/ngrok.tgz -C /usr/local/bin/
    chmod +x "$NGROK_BIN"
    rm /tmp/ngrok.tgz
    echo "  [OK] ngrok installed at $NGROK_BIN"
fi

# ---- Authenticate -----------------------------------------------------------
if [ -z "$NGROK_AUTHTOKEN" ]; then
    echo ""
    echo "Paste your ngrok authtoken (from https://dashboard.ngrok.com):"
    read -r NGROK_AUTHTOKEN
fi

ngrok config add-authtoken "$NGROK_AUTHTOKEN"

# ---- Kill existing ngrok ----------------------------------------------------
pkill -x ngrok 2>/dev/null || true
sleep 1

# ---- Start ngrok in background ----------------------------------------------
echo "Starting ngrok tunnel on port $NGROK_PORT..."
nohup ngrok http "$NGROK_PORT" \
    --log=stdout \
    --log-format=json \
    > "$NGROK_LOG" 2>&1 &

sleep 3

# ---- Get public URL ---------------------------------------------------------
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys,json; t=json.load(sys.stdin)['tunnels']; \
                  print(t[0]['public_url'])" 2>/dev/null || echo "")

if [ -n "$NGROK_URL" ]; then
    echo ""
    echo "  ngrok tunnel: $NGROK_URL"
    echo ""
    echo "  Adding $NGROK_URL to Nextcloud trusted_domains..."
    DOMAIN=$(echo "$NGROK_URL" | sed 's|https://||' | sed 's|http://||')
    if [ -d "$NC_WEB_DIR" ]; then
        cd "$NC_WEB_DIR"
        php occ config:system:set trusted_domains 4 --value="$DOMAIN"
        php occ config:system:set overwrite.cli.url --value="$NGROK_URL"
        echo "  [OK] Trusted domain updated."
    fi
    echo ""
    echo "  Remote URL: $NGROK_URL"
    echo "  Log:        $NGROK_LOG"
    echo "  Status UI:  http://localhost:4040"
else
    echo "  ngrok started but could not retrieve URL yet."
    echo "  Check: http://localhost:4040 or $NGROK_LOG"
fi

echo ""
echo "NOTE: Free ngrok URLs rotate on restart."
echo "      Add the new URL to Nextcloud trusted_domains each time,"
echo "      or upgrade to a paid ngrok plan for a static domain."
