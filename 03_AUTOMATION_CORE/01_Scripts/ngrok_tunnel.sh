#!/usr/bin/env bash
# ngrok_tunnel.sh -- expose XLM bot dashboard via ngrok tunnel
# Run this ON the Oracle Cloud VM: bash ~/ngrok_tunnel.sh
#
# Prerequisites:
#   - ngrok account (free): https://dashboard.ngrok.com
#   - Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
#
# Usage:
#   bash ngrok_tunnel.sh              # start tunnel (interactive, shows URL)
#   bash ngrok_tunnel.sh --authtoken YOUR_TOKEN  # first-time setup
#   bash ngrok_tunnel.sh --background # start detached, writes URL to ~/ngrok_url.txt
#   bash ngrok_tunnel.sh --basic-auth "user:pass"  # require login to access dashboard
#   bash ngrok_tunnel.sh --background --basic-auth "admin:secret"  # both

set -e

DASHBOARD_PORT=8502
NGROK_BIN="$HOME/ngrok"
NGROK_URL_FILE="$HOME/ngrok_url.txt"
BASIC_AUTH=""

# Parse flags (order-independent)
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --basic-auth)
            BASIC_AUTH="$2"
            shift 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done
set -- "${ARGS[@]}"

install_ngrok() {
    echo "Detecting architecture..."
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64)
            NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz"
            ;;
        x86_64)
            NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
            ;;
        *)
            echo "ERROR: Unknown architecture: $ARCH"
            exit 1
            ;;
    esac

    echo "Downloading ngrok for $ARCH..."
    wget -q "$NGROK_URL" -O /tmp/ngrok.tgz
    tar -xzf /tmp/ngrok.tgz -C "$HOME"
    chmod +x "$NGROK_BIN"
    rm /tmp/ngrok.tgz
    echo "ngrok installed at $NGROK_BIN"
}

# Install ngrok if not present
if [ ! -x "$NGROK_BIN" ]; then
    echo "ngrok not found, installing..."
    install_ngrok
else
    echo "ngrok found at $NGROK_BIN"
fi

# Handle --authtoken flag (first-time setup)
if [ "$1" = "--authtoken" ]; then
    if [ -z "$2" ]; then
        echo "Usage: $0 --authtoken YOUR_NGROK_TOKEN"
        echo "Get your token: https://dashboard.ngrok.com/get-started/your-authtoken"
        exit 1
    fi
    "$NGROK_BIN" config add-authtoken "$2"
    echo "Authtoken saved. Run: bash $0"
    exit 0
fi

# Check authtoken is configured
if ! "$NGROK_BIN" config check 2>/dev/null | grep -q authtoken; then
    echo ""
    echo "====================================================="
    echo "  ngrok authtoken not set."
    echo "  1. Sign up free: https://dashboard.ngrok.com"
    echo "  2. Copy your authtoken"
    echo "  3. Run: bash $0 --authtoken YOUR_TOKEN"
    echo "====================================================="
    exit 1
fi

# Check dashboard is actually running
echo "Checking dashboard on port $DASHBOARD_PORT..."
if ! curl -s --max-time 3 http://127.0.0.1:$DASHBOARD_PORT > /dev/null 2>&1; then
    echo "WARNING: Dashboard not responding on port $DASHBOARD_PORT!"
    echo "Trying to restart Docker container..."
    cd ~/xlm_bot 2>/dev/null && docker compose restart xlm-bot 2>/dev/null || \
        sudo systemctl restart xlm-bot 2>/dev/null || \
        echo "  Could not restart container. Check manually: docker ps"
    echo "Waiting 10s for dashboard to come up..."
    sleep 10
    if ! curl -s --max-time 5 http://127.0.0.1:$DASHBOARD_PORT > /dev/null 2>&1; then
        echo "ERROR: Dashboard still not responding. ngrok tunnel will fail."
        echo "Debug: docker logs xlm-bot --tail 30"
        exit 1
    fi
fi

echo "Dashboard is UP on port $DASHBOARD_PORT"

# Build ngrok command args
NGROK_ARGS=("http" "$DASHBOARD_PORT")
if [ -n "$BASIC_AUTH" ]; then
    NGROK_ARGS+=("--basic-auth" "$BASIC_AUTH")
    echo "Basic auth ENABLED (login required to access dashboard)"
fi

# Start ngrok tunnel
if [ "$1" = "--background" ]; then
    echo "Starting ngrok in background..."
    nohup "$NGROK_BIN" "${NGROK_ARGS[@]}" --log=stdout > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!
    echo "ngrok PID: $NGROK_PID"

    # Wait for tunnel URL to appear
    echo "Waiting for tunnel URL..."
    for i in $(seq 1 15); do
        sleep 1
        URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
              python3 -c "import sys,json; t=json.load(sys.stdin); print(t['tunnels'][0]['public_url'])" 2>/dev/null || echo "")
        if [ -n "$URL" ]; then
            echo ""
            echo "====================================================="
            echo "  DASHBOARD URL:  $URL"
            echo "====================================================="
            echo "$URL" > "$NGROK_URL_FILE"
            echo "URL saved to: $NGROK_URL_FILE"
            echo "ngrok dashboard: http://127.0.0.1:4040"
            echo ""
            echo "To stop tunnel: kill $NGROK_PID"
            exit 0
        fi
    done
    echo "ngrok running but couldn't fetch URL. Check: cat /tmp/ngrok.log"
else
    # Interactive mode -- ctrl+c to stop
    echo ""
    echo "Starting ngrok tunnel to localhost:$DASHBOARD_PORT ..."
    echo "(Press Ctrl+C to stop)"
    echo ""
    "$NGROK_BIN" "${NGROK_ARGS[@]}"
fi
