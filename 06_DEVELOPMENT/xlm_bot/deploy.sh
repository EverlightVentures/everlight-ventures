#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# Deploy XLM Bot to Oracle Cloud (run from your phone/laptop)
#
# Usage:
#   bash deploy.sh <server-ip> <ssh-key-path>
#
# Example:
#   bash deploy.sh 129.146.55.123 ~/.ssh/oracle_key.pem
#
# First time:  uploads code + secrets, builds Docker, starts bot
# Updates:     uploads code, rebuilds Docker, restarts bot
# ──────────────────────────────────────────────────────────────────────
set -e

SERVER_IP="${1:?Usage: bash deploy.sh <server-ip> <ssh-key-path>}"
SSH_KEY="${2:?Usage: bash deploy.sh <server-ip> <ssh-key-path>}"
REMOTE_USER="${3:-opc}"  # opc = Oracle Linux, ubuntu = Ubuntu
REMOTE_DIR="xlm-bot"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $REMOTE_USER@$SERVER_IP"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "═══════════════════════════════════════════════"
echo "  Deploying XLM Bot to $SERVER_IP"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. Create remote dirs ───────────────────────────────────────────
echo "[1/5] Creating remote directories..."
$SSH_CMD "mkdir -p ~/$REMOTE_DIR/{secrets,data,logs}"

# ── 2. Upload bot code (exclude secrets, data, logs, git) ───────────
echo "[2/5] Uploading bot code..."
# Use rsync if available, fall back to scp
if command -v rsync &>/dev/null; then
    rsync -avz --delete \
        --exclude='secrets/' \
        --exclude='data/' \
        --exclude='logs/' \
        --exclude='.git/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='backtest/' \
        --exclude='tests/' \
        -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
        "$BOT_DIR/" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/"
else
    echo "  (rsync not found, using scp — slower but works)"
    # Create a temp tarball excluding unwanted dirs
    TAR_FILE="/tmp/xlm-bot-deploy.tar.gz"
    tar -czf "$TAR_FILE" \
        --exclude='secrets' \
        --exclude='data' \
        --exclude='logs' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='backtest' \
        --exclude='tests' \
        -C "$(dirname "$BOT_DIR")" "$(basename "$BOT_DIR")"
    $SCP_CMD "$TAR_FILE" "$REMOTE_USER@$SERVER_IP:/tmp/"
    $SSH_CMD "cd ~ && tar -xzf /tmp/xlm-bot-deploy.tar.gz && rsync -a xlm_bot/ $REMOTE_DIR/ && rm -rf xlm_bot /tmp/xlm-bot-deploy.tar.gz" 2>/dev/null || \
    $SSH_CMD "cd ~ && tar -xzf /tmp/xlm-bot-deploy.tar.gz --strip-components=0 -C $REMOTE_DIR/ && rm /tmp/xlm-bot-deploy.tar.gz"
    rm -f "$TAR_FILE"
fi

# ── 3. Upload secrets (only if not already there) ───────────────────
echo "[3/5] Checking secrets..."
SECRETS_EXIST=$($SSH_CMD "test -f ~/$REMOTE_DIR/secrets/config.json && echo yes || echo no")
if [ "$SECRETS_EXIST" = "no" ]; then
    # Look for Coinbase config in common places
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
        echo "  Uploading Coinbase config from: $COINBASE_CONFIG"
        $SCP_CMD "$COINBASE_CONFIG" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/config.json"
    else
        echo ""
        echo "  ⚠  No Coinbase config.json found locally!"
        echo "  Upload manually:"
        echo "    scp -i $SSH_KEY config.json $REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/"
        echo ""
    fi
else
    echo "  ✓ Secrets already on server"
fi

# ── 4. Create .env if missing ───────────────────────────────────────
echo "[4/5] Setting up environment..."
$SSH_CMD "test -f ~/$REMOTE_DIR/.env || cat > ~/$REMOTE_DIR/.env << 'EOF'
COINBASE_CONFIG_PATH=/app/secrets/config.json
CRYPTO_BOT_DIR=/app
TZ=America/Los_Angeles
SLACK_WEBHOOK_URL=
EOF"

# ── 5. Build and launch ─────────────────────────────────────────────
echo "[5/5] Building and starting bot..."
$SSH_CMD "cd ~/$REMOTE_DIR && docker compose up -d --build"

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✓ Deployed!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Dashboard: http://$SERVER_IP:8502"
echo ""
echo "  Useful commands (SSH in first):"
echo "    docker compose logs -f          # live logs"
echo "    docker compose restart          # restart bot"
echo "    docker compose down             # stop everything"
echo "    docker compose up -d --build    # rebuild + restart"
echo ""
echo "  Re-deploy after code changes:"
echo "    bash deploy.sh $SERVER_IP $SSH_KEY"
echo ""
