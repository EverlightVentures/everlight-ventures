#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# Oracle Linux 9 Native Setup (no Docker) for XLM Bot
# Run this ONCE on the server after SSH-ing in.
# Usage: bash cloud-setup-native.sh
# ──────────────────────────────────────────────────────────────────────
set -e

BOT_DIR="$HOME/xlm-bot"
VENV="$BOT_DIR/venv"

echo "======================================================="
echo "  XLM Bot -- Oracle Linux 9 Native Setup"
echo "======================================================="
echo ""

# ── 1. Add swap (safety net for 1GB RAM) ─────────────────────────────
echo "[1/7] Setting up swap..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 1G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 status=progress
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
    echo "  OK: 1GB swap created"
else
    echo "  OK: swap already exists"
fi
free -h | grep -i swap

# ── 2. Install Python 3.11 ───────────────────────────────────────────
echo ""
echo "[2/7] Installing Python 3.11..."
sudo dnf install -y python3.11 python3.11-pip python3.11-devel gcc 2>/dev/null || {
    echo "  Trying alternative install method..."
    sudo dnf install -y python3 python3-pip python3-devel gcc
}

# Verify
PY_CMD=""
for cmd in python3.11 python3; do
    if command -v "$cmd" &>/dev/null; then
        PY_CMD="$cmd"
        break
    fi
done

if [ -z "$PY_CMD" ]; then
    echo "ERROR: No Python 3 found after install"
    exit 1
fi

echo "  OK: $($PY_CMD --version)"

# ── 3. Create bot directory ───────────────────────────────────────────
echo ""
echo "[3/7] Creating directory structure..."
mkdir -p "$BOT_DIR"/{secrets,data,logs}
echo "  OK: $BOT_DIR created"

# ── 4. Create virtual environment ────────────────────────────────────
echo ""
echo "[4/7] Creating Python virtual environment..."
if [ ! -d "$VENV" ]; then
    $PY_CMD -m venv "$VENV"
    echo "  OK: venv created at $VENV"
else
    echo "  OK: venv already exists"
fi

# Upgrade pip
"$VENV/bin/pip" install -q --upgrade pip

# ── 5. Install requirements ──────────────────────────────────────────
echo ""
echo "[5/7] Installing Python packages..."
if [ -f "$BOT_DIR/requirements.txt" ]; then
    "$VENV/bin/pip" install -r "$BOT_DIR/requirements.txt"
    "$VENV/bin/pip" install streamlit
    echo "  OK: all packages installed"
else
    echo "  SKIP: requirements.txt not found yet (will install after code upload)"
fi

# ── 6. Open firewall port ────────────────────────────────────────────
echo ""
echo "[6/7] Opening firewall port 8502..."
if command -v firewall-cmd &>/dev/null; then
    sudo firewall-cmd --permanent --add-port=8502/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
    echo "  OK: firewall port 8502 opened"
else
    sudo iptables -I INPUT -p tcp --dport 8502 -j ACCEPT 2>/dev/null || true
    echo "  OK: iptables port 8502 opened"
fi

# ── 7. Create systemd services ───────────────────────────────────────
echo ""
echo "[7/7] Creating systemd services..."

# Bot service
sudo tee /etc/systemd/system/xlm-bot.service > /dev/null << SVCEOF
[Unit]
Description=XLM Perp Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment=IDLE_SLEEP=30
Environment=IN_TRADE_SLEEP=5
Environment=COINBASE_CONFIG_PATH=$BOT_DIR/secrets/config.json
Environment=CRYPTO_BOT_DIR=$BOT_DIR
Environment=TZ=America/Los_Angeles
ExecStart=$BOT_DIR/run-bot.sh
Restart=always
RestartSec=5
StandardOutput=append:$BOT_DIR/logs/xpb_service.log
StandardError=append:$BOT_DIR/logs/xpb_service.log

[Install]
WantedBy=multi-user.target
SVCEOF

# Dashboard service
sudo tee /etc/systemd/system/xlm-dashboard.service > /dev/null << SVCEOF
[Unit]
Description=XLM Bot Dashboard (Streamlit)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment=COINBASE_CONFIG_PATH=$BOT_DIR/secrets/config.json
Environment=CRYPTO_BOT_DIR=$BOT_DIR
Environment=TZ=America/Los_Angeles
Environment=XLM_DASH_EXCHANGE_READ=1
ExecStart=$BOT_DIR/run-dashboard.sh
Restart=always
RestartSec=5
StandardOutput=append:$BOT_DIR/logs/dashboard_service.log
StandardError=append:$BOT_DIR/logs/dashboard_service.log

[Install]
WantedBy=multi-user.target
SVCEOF

# WebSocket feed service
sudo tee /etc/systemd/system/xlm-ws.service > /dev/null << SVCEOF
[Unit]
Description=XLM Bot WebSocket Feed
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment=TZ=America/Los_Angeles
ExecStart=$BOT_DIR/run-ws.sh
Restart=always
RestartSec=5
StandardOutput=append:$BOT_DIR/logs/ws_service.log
StandardError=append:$BOT_DIR/logs/ws_service.log

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
echo "  OK: 3 systemd services created"

# ── Create runner scripts (server-native, no hardcoded phone paths) ──
cat > "$BOT_DIR/run-bot.sh" << 'RUNEOF'
#!/bin/bash
set -euo pipefail
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$BOT_DIR/venv"
CONFIG="${XLM_CONFIG_FILE:-config.yaml}"
IDLE_SLEEP="${IDLE_SLEEP:-30}"
IN_TRADE_SLEEP="${IN_TRADE_SLEEP:-5}"

cd "$BOT_DIR"
source "$VENV/bin/activate"

# Detect paper vs live
is_paper=$("$VENV/bin/python" -c "
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('$CONFIG').read_text()) if Path('$CONFIG').exists() else {}
print('true' if bool(cfg.get('paper', True)) else 'false')
")

if [ "$is_paper" = "true" ]; then
    CMD=("$VENV/bin/python" main.py --config "$CONFIG" --paper)
else
    CMD=("$VENV/bin/python" main.py --config "$CONFIG" --live --i-understand-live)
fi

echo "[$(date)] Bot starting (paper=$is_paper, config=$CONFIG)"

while true; do
    if ! "${CMD[@]}"; then
        rc=$?
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] bot exited code $rc; retrying" >&2
    fi
    S=$("$VENV/bin/python" -c "
import json
from pathlib import Path
p = Path('data/state.json')
try:
    s = json.loads(p.read_text()) if p.exists() else {}
except Exception:
    s = {}
print($IN_TRADE_SLEEP if s.get('open_position') else $IDLE_SLEEP)
")
    sleep "$S"
done
RUNEOF
chmod +x "$BOT_DIR/run-bot.sh"

cat > "$BOT_DIR/run-dashboard.sh" << 'RUNEOF'
#!/bin/bash
set -euo pipefail
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$BOT_DIR/venv"
PORT="${XLM_DASH_PORT:-8502}"

cd "$BOT_DIR"
source "$VENV/bin/activate"

echo "[$(date)] Dashboard starting on port $PORT"

while true; do
    XLM_DASH_EXCHANGE_READ=1 PYTHONFAULTHANDLER=1 \
        "$VENV/bin/streamlit" run dashboard.py \
        --server.port "$PORT" \
        --server.address 0.0.0.0 \
        --server.headless true \
        --server.fileWatcherType poll
    sleep 2
done
RUNEOF
chmod +x "$BOT_DIR/run-dashboard.sh"

cat > "$BOT_DIR/run-ws.sh" << 'RUNEOF'
#!/bin/bash
set -euo pipefail
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$BOT_DIR/venv"

cd "$BOT_DIR"
source "$VENV/bin/activate"

echo "[$(date)] WebSocket feed starting"

while true; do
    "$VENV/bin/python" live_ws.py --product XLM-USD
    sleep 2
done
RUNEOF
chmod +x "$BOT_DIR/run-ws.sh"

echo ""
echo "======================================================="
echo "  Setup complete!"
echo "======================================================="
echo ""
echo "  Bot directory: $BOT_DIR"
echo "  Python: $($PY_CMD --version)"
echo "  Venv: $VENV"
echo "  Swap: $(free -h | grep -i swap | awk '{print $2}')"
echo ""
echo "  Next: upload your bot code + secrets, then run:"
echo "    sudo systemctl enable --now xlm-bot xlm-dashboard xlm-ws"
echo ""
echo "  Manage:"
echo "    sudo systemctl status xlm-bot        # check status"
echo "    sudo journalctl -u xlm-bot -f        # live logs"
echo "    sudo systemctl restart xlm-bot       # restart"
echo "    sudo systemctl stop xlm-bot          # stop"
echo ""
