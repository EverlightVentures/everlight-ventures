#!/usr/bin/env bash
# One-shot deploy of the Wealth Intel monthly cron to Oracle E5.
# Run this from the phone. Requires SSH access via oracle-mcp-tunnel host alias.

set -euo pipefail

ORACLE_HOST="${ORACLE_HOST:-163.192.19.196}"
ORACLE_USER="${ORACLE_USER:-opc}"
SSH_KEY="${SSH_KEY:-/root/.ssh/oracle_key.pem}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> shipping runner to Oracle"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new \
  "$HERE/wealth_intel_runner.py" \
  "$ORACLE_USER@$ORACLE_HOST:/home/opc/wealth_intel_runner.py"
ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "chmod +x /home/opc/wealth_intel_runner.py"

echo "==> shipping systemd units to Oracle (staging in opc home)"
scp -i "$SSH_KEY" \
  "$HERE/wealth-intel.service" \
  "$HERE/wealth-intel.timer" \
  "$ORACLE_USER@$ORACLE_HOST:/home/opc/"

echo "==> installing units (sudo)"
ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" bash -se <<'REMOTE'
set -euo pipefail
sudo mv /home/opc/wealth-intel.service /etc/systemd/system/
sudo mv /home/opc/wealth-intel.timer   /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/wealth-intel.service /etc/systemd/system/wealth-intel.timer
sudo chown root:root /etc/systemd/system/wealth-intel.service /etc/systemd/system/wealth-intel.timer
# SELinux relabel: files mv'd from a user home keep user_home_t and systemd will refuse to read them.
sudo restorecon -v /etc/systemd/system/wealth-intel.service /etc/systemd/system/wealth-intel.timer
sudo systemctl daemon-reload
sudo systemctl enable --now wealth-intel.timer
echo "--- timer status ---"
systemctl list-timers wealth-intel.timer --no-pager
REMOTE

echo
echo "Wealth Intel cron is now Oracle-resident. Fires 1st of each month at 7:17 AM PT."
echo "Logs: /home/opc/_logs/wealth_intel.log"
echo "Snapshot state: /home/opc/_state/wealth_intel_last.json"
