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
LOCAL_SHARED_ENV="$(cd "$BOT_DIR/../.." && pwd)/03_AUTOMATION_CORE/03_Credentials/.env"
GOOGLE_CLIENT_SECRET_LOCAL="$BOT_DIR/secrets/google_client_secret.json"
GOOGLE_CLIENT_SECRET_FALLBACK="$BOT_DIR/../../08_BACKUPS/Credentials_Plaintext_Backup/client_secret_864189495801-pssn6fg438ahieth9vqih41a188smghu.apps.googleusercontent.com.json"

SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no $REMOTE_USER@$SERVER_IP"
SCP_CMD="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "======================================================="
echo "  XLM Bot Native Deploy to $SERVER_IP"
echo "======================================================="
echo ""

# ── 1. Check if first-time setup needed ──────────────────────────────
echo "[1/6] Checking server state..."
SETUP_DONE=$($SSH_CMD "test -f ~/$REMOTE_DIR/venv/bin/python && echo yes || echo no" 2>/dev/null || echo "no")
RECONFIGURE_NEEDED=$($SSH_CMD "test -f /etc/systemd/system/xlm-watchtower.timer && test -f /etc/systemd/system/xlm-liqfeed.service && sudo systemctl cat xlm-bot 2>/dev/null | grep -q 'GDOCS_QUEUE_DIR=' && echo no || echo yes" 2>/dev/null || echo "yes")

if [ "$SETUP_DONE" = "no" ] || [ "${FORCE_RECONFIGURE:-0}" = "1" ] || [ "$RECONFIGURE_NEEDED" = "yes" ]; then
    if [ "$SETUP_DONE" = "no" ]; then
        echo "  First-time deploy detected. Running server setup..."
    else
        echo "  Existing deploy needs service refresh. Re-running server setup..."
    fi
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
    'run-bot.sh' 'run-dashboard.sh' 'run-ws.sh'
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

# data/ is excluded to protect runtime state; upload required Python module(s) explicitly.
$SSH_CMD "mkdir -p ~/$REMOTE_DIR/data"
if [ -f "$BOT_DIR/data/candles.py" ]; then
    $SCP_CMD "$BOT_DIR/data/candles.py" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/data/candles.py"
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

if [ -f "$GOOGLE_CLIENT_SECRET_LOCAL" ]; then
    echo "  Uploading Google Docs client secret"
    $SCP_CMD "$GOOGLE_CLIENT_SECRET_LOCAL" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/google_client_secret.json"
    $SSH_CMD "chmod 600 ~/$REMOTE_DIR/secrets/google_client_secret.json"
    echo "  OK: Google client secret uploaded"
elif [ -f "$GOOGLE_CLIENT_SECRET_FALLBACK" ]; then
    echo "  Uploading Google Docs client secret"
    $SCP_CMD "$GOOGLE_CLIENT_SECRET_FALLBACK" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/google_client_secret.json"
    $SSH_CMD "chmod 600 ~/$REMOTE_DIR/secrets/google_client_secret.json"
    echo "  OK: Google client secret uploaded"
fi

RUNTIME_ENV_TMP="$(mktemp)"
python3 - "$LOCAL_SHARED_ENV" > "$RUNTIME_ENV_TMP" <<'PY'
import json
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
values = {}
if env_path.exists():
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

lines = []
supabase_url = values.get("SUPABASE_URL", "").strip()
if supabase_url:
    lines.append(f"SUPABASE_URL={supabase_url}")

access_token = values.get("SUPABASE_ACCESS_TOKEN", "").strip()
if access_token:
    try:
        import requests

        resp = requests.get(
            "https://api.supabase.com/v1/projects/jdqqmsmwmbsnlnstyavl/api-keys?reveal=true",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        for item in payload:
            if (item.get("name") or item.get("type")) == "service_role":
                key = (item.get("api_key") or item.get("apiKey") or item.get("key") or "").strip()
                if key:
                    lines.append(f"SUPABASE_SERVICE_ROLE_KEY={key}")
                break
    except Exception:
        pass

if lines:
    print("\n".join(lines))
PY

if [ -s "$RUNTIME_ENV_TMP" ]; then
    printf '\nXLM_REPORT_PUBLIC_BASE_URL=http://%s:8502/?report_id=\n' "$SERVER_IP" >> "$RUNTIME_ENV_TMP"
fi

if [ -s "$RUNTIME_ENV_TMP" ]; then
    echo "  Uploading runtime integration env"
    $SCP_CMD "$RUNTIME_ENV_TMP" "$REMOTE_USER@$SERVER_IP:~/$REMOTE_DIR/secrets/runtime.env"
    $SSH_CMD "chmod 600 ~/$REMOTE_DIR/secrets/runtime.env"
    echo "  OK: Runtime env uploaded"
    if ! grep -q '^SUPABASE_SERVICE_ROLE_KEY=' "$RUNTIME_ENV_TMP"; then
        echo "  WARNING: Runtime env did not include SUPABASE_SERVICE_ROLE_KEY"
    fi
else
    echo "  SKIP: No runtime integration env available"
fi
rm -f "$RUNTIME_ENV_TMP"

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
$SSH_CMD "chmod +x ~/$REMOTE_DIR/run-bot.sh ~/$REMOTE_DIR/run-dashboard.sh ~/$REMOTE_DIR/run-ws.sh ~/$REMOTE_DIR/liquidation_feed_runner.py 2>/dev/null || true"

# Enable and restart all services
$SSH_CMD "sudo systemctl daemon-reload && \
    sudo systemctl enable xlm-bot xlm-dashboard xlm-ws xlm-liqfeed xlm-watchtower.timer && \
    sudo systemctl restart xlm-bot xlm-dashboard xlm-ws xlm-liqfeed && \
    sudo systemctl restart xlm-watchtower.timer && \
    sudo systemctl start xlm-watchtower.service"

# Wait a moment, then check status
sleep 3
echo ""
echo "  Service status:"
$SSH_CMD "sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws xlm-liqfeed xlm-watchtower.timer && sudo systemctl --no-pager --full status xlm-watchtower.service | sed -n '1,18p'" || true

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
