#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# Deploy XLM Bot to Oracle Cloud -- NATIVE (no Docker)
# Run from your phone/laptop.
#
# Usage:
#   bash deploy-native.sh <server-ip> <ssh-key-path> [user]
#
# Examples:
#   bash deploy-native.sh 129.146.55.123 ~/.ssh/oracle_key.pem
#   bash deploy-native.sh 129.146.55.123 ~/.ssh/oracle_key.pem opc
#
# First time:  uploads code + secrets, installs Python, creates venv, starts bot
# Updates:     uploads code, reinstalls deps if changed, restarts services
# ──────────────────────────────────────────────────────────────────────
set -e

SERVER_IP="${1:?Usage: bash deploy-native.sh <server-ip> <ssh-key-path> [user]}"
SSH_KEY="${2:?Usage: bash deploy-native.sh <server-ip> <ssh-key-path> [user]}"
REMOTE_USER="${3:-opc}"
REMOTE_DIR="xlm-bot"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $REMOTE_USER@$SERVER_IP"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "======================================================="
echo "  XLM Bot Native Deploy to $SERVER_IP"
echo "======================================================="
echo ""

# ── 1. Check if first-time setup needed ──────────────────────────────
echo "[1/6] Checking server state..."
SETUP_DONE=$($SSH_CMD "test -f ~/\$REMOTE_DIR/venv/bin/python && echo yes || echo no" 2>/dev/null || echo "no")

if [ "$SETUP_DONE" = "no" ]; then
    echo "  First-time deploy detected. Running server setup..."
    # Upload setup script first
    $SSH_CMD "mkdir -p ~/$REMOTE_DIR"
    $SCP_CMD "$BOT_DIR/cloud-setup-native.sh" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/"
    $SSH_CMD "cd ~/$REMOTE_DIR && bash cloud-setup-native.sh"
    echo ""
    echo "  OK: Server environment ready"
else
    echo "  OK: Server already set up"
fi

# ── 2. Create remote dirs ────────────────────────────────────────────
echo ""
echo "[2/6] Ensuring remote directories..."
$SSH_CMD "mkdir -p ~/$REMOTE_DIR/{secrets,data,logs,vendor}"

# ── 3. Upload bot code ───────────────────────────────────────────────
echo ""
echo "[3/6] Uploading bot code..."

# Files/dirs to exclude from upload
EXCLUDES=(
    'secrets/' 'data/' 'logs/' 'logs_mr/' 'logs_trend/'
    '.git/' '__pycache__/' '*.pyc' '.env'
    'backtest/' 'tests/' 'venv/'
    'cloud-setup.sh'
)

if command -v rsync &>/dev/null; then
    RSYNC_EXCLUDES=""
    for ex in "${EXCLUDES[@]}"; do
        RSYNC_EXCLUDES="$RSYNC_EXCLUDES --exclude=$ex"
    done
    rsync -avz --delete $RSYNC_EXCLUDES \
        -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
        "$BOT_DIR/" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/"
else
    echo "  (rsync not found, using tar+scp)"
    TAR_FILE="/tmp/xlm-bot-native-deploy.tar.gz"
    TAR_EXCLUDES=""
    for ex in "${EXCLUDES[@]}"; do
        TAR_EXCLUDES="$TAR_EXCLUDES --exclude=$ex"
    done
    tar -czf "$TAR_FILE" $TAR_EXCLUDES -C "$(dirname "$BOT_DIR")" "$(basename "$BOT_DIR")"
    $SCP_CMD "$TAR_FILE" "$REMOTE_USER@$SERVER_IP:/tmp/"
    $SSH_CMD "cd ~ && tar -xzf /tmp/xlm-bot-native-deploy.tar.gz && \
        cp -r xlm_bot/* $REMOTE_DIR/ 2>/dev/null || cp -r xlm_bot/* $REMOTE_DIR/ && \
        rm -rf xlm_bot /tmp/xlm-bot-native-deploy.tar.gz"
    rm -f "$TAR_FILE"
fi
echo "  OK: Code uploaded"

# ── 4. Upload secrets ────────────────────────────────────────────────
echo ""
echo "[4/6] Checking secrets..."
SECRETS_EXIST=$($SSH_CMD "test -f ~/$REMOTE_DIR/secrets/config.json && echo yes || echo no")

if [ "$SECRETS_EXIST" = "no" ]; then
    # Search common locations for Coinbase config
    COINBASE_CONFIG=""
    for p in \
        "$BOT_DIR/secrets/config.json" \
        "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/config.json" \
        "$HOME/.config/coinbase/config.json" \
        "/data/data/com.termux/files/home/.config/coinbase/config.json" \
    ; do
        if [ -f "$p" ]; then
            COINBASE_CONFIG="$p"
            break
        fi
    done

    if [ -n "$COINBASE_CONFIG" ]; then
        echo "  Uploading config from: $COINBASE_CONFIG"
        $SCP_CMD "$COINBASE_CONFIG" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/config.json"
        echo "  OK: Secrets uploaded"
    else
        echo ""
        echo "  WARNING: No Coinbase config.json found locally!"
        echo "  Upload manually:"
        echo "    scp -i $SSH_KEY config.json $REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/"
        echo ""
    fi
else
    echo "  OK: Secrets already on server"
fi

# ── 5. Install/update Python deps ────────────────────────────────────
echo ""
echo "[5/6] Installing Python dependencies..."
$SSH_CMD "cd ~/$REMOTE_DIR && \
    source venv/bin/activate && \
    pip install -q -r requirements.txt && \
    pip install -q streamlit"
echo "  OK: Dependencies installed"

# ── 6. Start/restart services ────────────────────────────────────────
echo ""
echo "[6/6] Starting services..."

# Make runner scripts executable
$SSH_CMD "chmod +x ~/$REMOTE_DIR/run-bot.sh ~/$REMOTE_DIR/run-dashboard.sh ~/$REMOTE_DIR/run-ws.sh 2>/dev/null || true"

# Enable and restart all services
$SSH_CMD "sudo systemctl daemon-reload && \
    sudo systemctl enable xlm-bot xlm-dashboard xlm-ws && \
    sudo systemctl restart xlm-bot xlm-dashboard xlm-ws"

# Wait a moment, then check status
sleep 3
echo ""
echo "  Service status:"
$SSH_CMD "sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws" || true

echo ""
echo "======================================================="
echo "  Deployed!"
echo "======================================================="
echo ""
echo "  Dashboard: http://$SERVER_IP:8502"
echo ""
echo "  SSH in:    ssh -i $SSH_KEY $REMOTE_USER@$SERVER_IP"
echo ""
echo "  Commands:"
echo "    sudo systemctl status xlm-bot          # bot status"
echo "    sudo systemctl status xlm-dashboard    # dashboard status"
echo "    sudo journalctl -u xlm-bot -f          # live bot logs"
echo "    sudo journalctl -u xlm-dashboard -f    # dashboard logs"
echo "    sudo systemctl restart xlm-bot         # restart bot"
echo "    sudo systemctl stop xlm-bot            # stop bot"
echo ""
echo "  Re-deploy after code changes:"
echo "    bash deploy-native.sh $SERVER_IP $SSH_KEY"
echo ""
