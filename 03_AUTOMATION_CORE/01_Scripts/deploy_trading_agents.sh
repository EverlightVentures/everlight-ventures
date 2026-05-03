#!/bin/bash
# deploy_trading_agents.sh -- one-shot deploy of the Everlight TradingAgents fork to Oracle.
# Standalone from deploy_to_oracle.sh (which is XLM-bot-specific). Idempotent: re-run safely.
#
# Usage:
#   bash deploy_trading_agents.sh              # rsync code + install/upgrade systemd timer
#   bash deploy_trading_agents.sh code-only    # rsync code only, do not touch systemd
#   bash deploy_trading_agents.sh smoke        # rsync + run one --no-execute SPY cycle, no systemd
#
# Requires:
#   /root/.ssh/oracle_key.pem (existing Oracle key) reachable
#   $ORACLE_VM env var or default opc@163.192.19.196
#
# What it does NOT do:
#   - install python deps (run on Oracle: cd /home/opc/trading_agents && python3 -m venv .venv && .venv/bin/pip install -e . -r everlight/requirements.txt)
#   - flip LIVE_TRADING (you do that explicitly in /home/opc/trading_agents/.env after paper P&L proves out)

set -euo pipefail

KEY="${ORACLE_KEY:-/root/.ssh/oracle_key.pem}"
ORACLE_VM="${ORACLE_VM:-opc@163.192.19.196}"
LOCAL="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/trading_agents"
REMOTE="/home/opc/trading_agents"
MODE="${1:-all}"

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }
log() { echo "[$(ts)] $*"; }

if [[ ! -f "$KEY" ]]; then
    log "ERROR: SSH key not found at $KEY"
    exit 1
fi

log "Syncing $LOCAL -> $ORACLE_VM:$REMOTE"
rsync -az --delete \
    --exclude='.venv/' \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='logs/' \
    --exclude='.pytest_cache/' \
    --exclude='node_modules/' \
    --exclude='.env' \
    -e "ssh -o ConnectTimeout=10 -i $KEY" \
    "$LOCAL/" "$ORACLE_VM:$REMOTE/"
log "Code synced."

ssh -o ConnectTimeout=10 -i "$KEY" "$ORACLE_VM" "mkdir -p $REMOTE/logs"

if [[ "$MODE" == "code-only" ]]; then
    log "code-only mode; skipping systemd + smoke."
    exit 0
fi

if [[ "$MODE" == "smoke" ]]; then
    log "Running one --no-execute SPY cycle (research only, no broker)..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$ORACLE_VM" \
        "cd $REMOTE && .venv/bin/python -m everlight.run --ticker SPY --no-execute" || {
        log "Smoke run failed (likely missing deps; install with: cd $REMOTE && python3 -m venv .venv && .venv/bin/pip install -e . -r everlight/requirements.txt)"
        exit 2
    }
    log "Smoke OK."
    exit 0
fi

log "Installing systemd unit + timer..."
ssh -o ConnectTimeout=10 -i "$KEY" "$ORACLE_VM" "sudo cp $REMOTE/everlight/systemd/trading-agents.service /etc/systemd/system/ && sudo cp $REMOTE/everlight/systemd/trading-agents.timer /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now trading-agents.timer"
log "Timer enabled. Status:"
ssh -o ConnectTimeout=10 -i "$KEY" "$ORACLE_VM" "systemctl status trading-agents.timer --no-pager | head -15"
