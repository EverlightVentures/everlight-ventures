#!/usr/bin/env bash
# INSTALL_HIVE_CRONS.sh
#
# Bulk-install systemd timers for the 12 highest-leverage cron jobs that
# previously lived on the phone crontab. Generates the unit files inline,
# ships to Oracle, fixes perms + SELinux contexts, enables, verifies.
#
# Run from phone:
#   bash /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wealth_OS/03_Engines/oracle_systemd/INSTALL_HIVE_CRONS.sh
#
# Idempotent. Safe to re-run.

set -euo pipefail

ORACLE_HOST="${ORACLE_HOST:-163.192.19.196}"
ORACLE_USER="${ORACLE_USER:-opc}"
SSH_KEY="${SSH_KEY:-/root/.ssh/oracle_key.pem}"
STAGE_DIR="/tmp/hive_units_$$"
mkdir -p "$STAGE_DIR"

# -----------------------------------------------------------------
# Unit definitions: name | script_path | args | OnCalendar OR OnUnitActiveSec
# -----------------------------------------------------------------
# Naming: {component}-{cadence-or-stage}.timer -- prefix avoids collision
# with anything else on Oracle.
# -----------------------------------------------------------------

write_unit() {
  local name="$1"
  local desc="$2"
  local exec="$3"
  local cadence="$4"  # either "calendar:..." or "active:..."

  cat > "$STAGE_DIR/${name}.service" <<SERVICE
[Unit]
Description=${desc}
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=opc
Group=opc
WorkingDirectory=/home/opc
EnvironmentFile=/etc/default/rex-negotiator
Environment=PYTHONUNBUFFERED=1
ExecStart=${exec}
StandardOutput=journal
StandardError=journal
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
SERVICE

  if [[ "$cadence" == calendar:* ]]; then
    local oncal="${cadence#calendar:}"
    cat > "$STAGE_DIR/${name}.timer" <<TIMER
[Unit]
Description=${desc} schedule
Requires=${name}.service

[Timer]
OnCalendar=${oncal}
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
TIMER
  else
    local active="${cadence#active:}"
    cat > "$STAGE_DIR/${name}.timer" <<TIMER
[Unit]
Description=${desc} loop
Requires=${name}.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=${active}
AccuracySec=15s
Persistent=true

[Install]
WantedBy=timers.target
TIMER
  fi
}

# -----------------------------------------------------------------
# 12 jobs. Scripts are ALL referenced as absolute paths on Oracle.
# Stage 1: monitoring + sync
write_unit hive-health   "Hive health monitor"        "/usr/bin/python3 /home/opc/03_AUTOMATION_CORE/01_Scripts/hive_health_monitor.py --fix --quiet"  "active:5min"
write_unit hive-sync     "Hive master sync"           "/usr/bin/python3 /home/opc/03_AUTOMATION_CORE/01_Scripts/hive_master_sync.py --quick"            "active:10min"
write_unit hourly-pulse  "Hourly status pulse"        "/usr/bin/python3 /home/opc/03_AUTOMATION_CORE/01_Scripts/hourly_status_pulse.py"                 "active:1h"

# Stage 2: outreach + reply detection (rex-negotiator already deployed, skip)
write_unit rex-belfort   "Rex Belfort 7-touch sequence" "/usr/bin/python3 /home/opc/wholesale_agent/rex_belfort_sequence.py"   "active:1h"
write_unit rex-recycler  "Rex lead recycler weekly"     "/usr/bin/python3 /home/opc/wholesale_agent/rex_lead_recycler.py"     "calendar:Sun *-*-* 23:00:00"

# Stage 3: broker daily orchestrator (4 different actions)
# Pacific Time times (12:00, 19:00, 01:00, 05:00 PT) = UTC 19:00, 02:00 next day, 08:00, 12:00
write_unit broker-orch-full     "Broker daily orchestrator full"      "/usr/bin/python3 /home/opc/broker_daily_orchestrator.py full"      "calendar:*-*-* 19:00:00"
write_unit broker-orch-outreach "Broker daily orchestrator outreach"  "/usr/bin/python3 /home/opc/broker_daily_orchestrator.py outreach"  "calendar:*-*-* 02:00:00"
write_unit broker-orch-scout    "Broker daily orchestrator scout"     "/usr/bin/python3 /home/opc/broker_daily_orchestrator.py scout"     "calendar:*-*-* 08:00:00"
write_unit broker-orch-match    "Broker daily orchestrator match"     "/usr/bin/python3 /home/opc/broker_daily_orchestrator.py match"     "calendar:*-*-* 12:00:00"

# Stage 4: wholesale pipeline + brief
# 15:00 PT = 22:00 UTC, 20:00 PT = 03:00 UTC next day, 00:00 PT = 07:00 UTC
write_unit wholesale-day        "Wholesale pipeline day stages"      "/usr/bin/python3 /home/opc/03_AUTOMATION_CORE/01_Scripts/wholesale_hive_pipeline.py --stage scout qualify match pitch"  "calendar:*-*-* 22:00:00"
write_unit wholesale-outreach   "Wholesale pipeline outreach"        "/usr/bin/python3 /home/opc/03_AUTOMATION_CORE/01_Scripts/wholesale_hive_pipeline.py --stage outreach"                  "calendar:*-*-* 03:00:00"
write_unit ceo-brief            "CEO daily brief"                    "/usr/bin/python3 /home/opc/ceo_daily_brief.py"                    "calendar:*-*-* 22:00:00"

echo "==> Generated $(ls $STAGE_DIR | wc -l) unit files"

# -----------------------------------------------------------------
# Ship + install on Oracle (root-owned, restorecon for SELinux)
# -----------------------------------------------------------------
echo "==> Shipping units to Oracle"
scp -i "$SSH_KEY" "$STAGE_DIR"/*.service "$STAGE_DIR"/*.timer \
  "$ORACLE_USER@$ORACLE_HOST:/tmp/" 2>&1 | tail -3

echo "==> Install + enable (sudo) with restorecon"
ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" bash -se <<'REMOTE'
set -uo pipefail
cd /tmp
units=$(ls *.service *.timer 2>/dev/null)
for u in $units; do
  sudo mv -f "/tmp/$u" "/etc/systemd/system/$u"
  sudo chmod 644 "/etc/systemd/system/$u"
  sudo chown root:root "/etc/systemd/system/$u"
done
sudo restorecon -v /etc/systemd/system/{hive-,rex-,broker-,wholesale-,ceo-,hourly-}*.{service,timer} 2>&1 | head -20

sudo systemctl daemon-reload

# Enable each timer
enabled=0
failed=0
for t in /etc/systemd/system/hive-*.timer \
         /etc/systemd/system/rex-belfort.timer \
         /etc/systemd/system/rex-recycler.timer \
         /etc/systemd/system/broker-orch-*.timer \
         /etc/systemd/system/wholesale-*.timer \
         /etc/systemd/system/ceo-brief.timer \
         /etc/systemd/system/hourly-*.timer; do
  [ -f "$t" ] || continue
  name=$(basename "$t")
  if sudo systemctl enable --now "$name" 2>&1 | grep -q "Failed"; then
    echo "FAIL $name"
    failed=$((failed+1))
  else
    enabled=$((enabled+1))
  fi
done

echo "--- $enabled enabled, $failed failed ---"
echo
echo "--- LIVE TIMERS (Hive scope) ---"
systemctl list-timers --no-pager 2>&1 | grep -E 'hive-|rex-|broker-|wholesale-|ceo-|hourly-|wealth-|gmail-' | head -20
REMOTE

rm -rf "$STAGE_DIR"
echo
echo "Hive crons are now Oracle-resident. Phone crontab still has the duplicates;"
echo "remove them with: crontab -l | grep -v -E '(broker_daily_orchestrator|rex_belfort_sequence|rex_lead_recycler|wholesale_hive_pipeline|hive_health_monitor|hive_master_sync|hourly_status_pulse|ceo_daily_brief)' | crontab -"
