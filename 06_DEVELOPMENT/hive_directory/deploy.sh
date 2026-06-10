#!/usr/bin/env bash
# Deploy hive_directory to Oracle E5 (163.192.19.196) and start systemd service on :8503.
#
# Usage:
#   ./deploy.sh              (rsync + build + restart)
#   ./deploy.sh --fresh      (first-time install; creates systemd unit + opens firewall)
#
# Target: oracle-e5 (SSH alias in /root/.ssh/config, user=opc)
set -euo pipefail

SSH_HOST="${SSH_HOST:-oracle-e5}"
SSH_OPTS="-F /root/.ssh/config -o StrictHostKeyChecking=no -o ConnectTimeout=10"
REMOTE_BASE="${REMOTE_BASE:-/home/opc/hive_directory}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
FRESH=0
if [[ "${1:-}" == "--fresh" ]]; then FRESH=1; fi

echo "[deploy] local:  $LOCAL_DIR"
echo "[deploy] remote: $SSH_HOST:$REMOTE_BASE  (fresh=$FRESH)"

# Probe SSH
ssh $SSH_OPTS "$SSH_HOST" "echo ok" >/dev/null
echo "[deploy] SSH ok"

# Ensure remote dirs
ssh $SSH_OPTS "$SSH_HOST" "mkdir -p '$REMOTE_BASE' /home/opc/hive_logs"

# Rsync source (skip node_modules, dist, __pycache__, .git)
echo "[deploy] syncing source..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude 'dist' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  -e "ssh $SSH_OPTS" \
  "$LOCAL_DIR/" "$SSH_HOST:$REMOTE_BASE/"

# Install deps + build on remote
echo "[deploy] remote install + build..."
ssh $SSH_OPTS "$SSH_HOST" bash -s <<REMOTE
set -euo pipefail
cd "$REMOTE_BASE"
# Python deps
if command -v pip3 >/dev/null; then
  pip3 install --user -q -r requirements.txt
else
  python3 -m pip install --user -q -r requirements.txt
fi
# Node deps + build (prefer npm ci for reproducibility, fall back to npm install)
if [ -f package-lock.json ]; then
  npm ci --silent || npm install --silent
else
  npm install --silent
fi
npm run build
echo "[remote] build ok, dist/ present: \$(ls -la dist | head -5)"
REMOTE

# Systemd unit install on fresh deploy
if [[ $FRESH -eq 1 ]]; then
  echo "[deploy] installing systemd unit..."
  ssh $SSH_OPTS "$SSH_HOST" "sudo cp '$REMOTE_BASE/hive-directory.service' /etc/systemd/system/hive-directory.service && sudo systemctl daemon-reload && sudo systemctl enable hive-directory"
  echo "[deploy] opening firewall for 8503..."
  ssh $SSH_OPTS "$SSH_HOST" "sudo firewall-cmd --permanent --zone=public --add-port=8503/tcp 2>/dev/null || true; sudo firewall-cmd --reload 2>/dev/null || true"
fi

# Restart service
echo "[deploy] restarting hive-directory.service..."
ssh $SSH_OPTS "$SSH_HOST" "sudo systemctl restart hive-directory && sleep 2 && sudo systemctl is-active hive-directory"

# Smoke test
echo "[deploy] smoke test on :8503..."
sleep 2
ssh $SSH_OPTS "$SSH_HOST" "curl -s -o /dev/null -w 'healthz: %{http_code}\n' http://127.0.0.1:8503/healthz; curl -s http://127.0.0.1:8503/api/team | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"team count: {len(d)}\")'"

echo "[deploy] done. Public: http://163.192.19.196:8503/"
