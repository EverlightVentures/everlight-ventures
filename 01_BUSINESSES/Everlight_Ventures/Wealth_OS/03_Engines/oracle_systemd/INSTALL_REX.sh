#!/usr/bin/env bash
# Deploy Rex Negotiator as a systemd timer on Oracle E5.
# Mirror of INSTALL.sh for the Wealth Intel cron, with the SELinux + perm fixes baked in.

set -euo pipefail

ORACLE_HOST="${ORACLE_HOST:-163.192.19.196}"
ORACLE_USER="${ORACLE_USER:-opc}"
SSH_KEY="${SSH_KEY:-/root/.ssh/oracle_key.pem}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Verify rex_negotiator.py exists on Oracle"
ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" \
  "test -f /home/opc/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/rex_negotiator.py && echo present || echo MISSING"

echo "==> Ship systemd units"
scp -i "$SSH_KEY" "$HERE/rex-negotiator.service" "$HERE/rex-negotiator.timer" \
  "$ORACLE_USER@$ORACLE_HOST:/home/opc/"

echo "==> Install (sudo) with SELinux relabel"
ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" bash -se <<'REMOTE'
set -euo pipefail

mkdir -p /home/opc/_logs

sudo mv /home/opc/rex-negotiator.service /etc/systemd/system/
sudo mv /home/opc/rex-negotiator.timer   /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/rex-negotiator.service /etc/systemd/system/rex-negotiator.timer
sudo chown root:root /etc/systemd/system/rex-negotiator.service /etc/systemd/system/rex-negotiator.timer
sudo restorecon -v /etc/systemd/system/rex-negotiator.service /etc/systemd/system/rex-negotiator.timer

sudo systemctl daemon-reload
sudo systemctl enable --now rex-negotiator.timer

echo "--- timer status ---"
systemctl list-timers rex-negotiator.timer --no-pager

echo "--- last 6 lines of rex_negotiator.log (after first fire) ---"
sleep 4
tail -6 /home/opc/_logs/rex_negotiator.log 2>/dev/null || echo "(no log yet)"
REMOTE

echo
echo "Rex Negotiator is now Oracle-resident. Fires every 2 minutes."
echo "Next step (do this manually only after verifying it works for 30 min):"
echo "  crontab -l | grep -v rex_negotiator > /tmp/cron.tmp && crontab /tmp/cron.tmp"
echo "to remove the duplicate phone-side cron line."
