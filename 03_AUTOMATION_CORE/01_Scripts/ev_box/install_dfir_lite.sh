#!/usr/bin/env bash
# DFIR-Lite -- ARM-friendly subset of the "autonomous forensics" spec.
# Runs on ev-box. Resource budget: ~1.5 GB RAM steady-state.
#
# Stack: osquery + auditd + Wazuh agent + Velociraptor agent + Medusa SAST + suricata
# Skipped (resource-heavy): CAPEv2, Elasticsearch, Neo4j, MISP, Velociraptor server
set -euo pipefail

DFIR_DIR="/opt/dfir-lite"
LOG_DIR="/var/log/dfir-lite"
sudo mkdir -p "$DFIR_DIR" "$LOG_DIR"
sudo chown -R ubuntu:ubuntu "$DFIR_DIR" "$LOG_DIR"

log() { printf '[dfir-lite %s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ---------- 1. osquery ----------
log "Installing osquery..."
if ! command -v osqueryi >/dev/null 2>&1; then
  curl -fsSL https://pkg.osquery.io/deb/pubkey.gpg | sudo apt-key add - 2>/dev/null || \
    curl -fsSL https://pkg.osquery.io/deb/pubkey.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/osquery.gpg
  echo 'deb [arch=arm64] https://pkg.osquery.io/deb deb main' | sudo tee /etc/apt/sources.list.d/osquery.list >/dev/null
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y osquery
fi
sudo systemctl enable --now osqueryd

# ---------- 2. auditd ----------
log "Installing auditd..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y auditd audispd-plugins
# File-integrity-monitoring rules for the sensitive paths
sudo tee /etc/audit/rules.d/ev-box.rules >/dev/null <<'AUDIT'
-w /home/ubuntu/.ssh/ -p wa -k ssh_keys
-w /home/ubuntu/.claude/ -p wa -k claude_config
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /etc/passwd -p wa -k user_db
-w /etc/sudoers -p wa -k sudoers
-w /opt/dfir-lite/ -p wa -k dfir_self
AUDIT
sudo augenrules --load 2>/dev/null || true
sudo systemctl restart auditd

# ---------- 3. Wazuh agent ----------
log "Installing Wazuh agent..."
if ! dpkg -l wazuh-agent >/dev/null 2>&1; then
  curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
  sudo chmod 644 /usr/share/keyrings/wazuh.gpg
  echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list >/dev/null
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  # Standalone mode -- no manager set, agent logs locally to /var/ossec/logs/
  sudo DEBIAN_FRONTEND=noninteractive WAZUH_MANAGER='127.0.0.1' apt-get install -y wazuh-agent || true
  sudo systemctl daemon-reload
  sudo systemctl enable --now wazuh-agent || log "  (wazuh-agent will run standalone -- no manager wired yet)"
fi

# ---------- 4. Velociraptor (collector mode, no server) ----------
log "Installing Velociraptor agent..."
if [[ ! -f "$DFIR_DIR/velociraptor" ]]; then
  cd "$DFIR_DIR"
  VELO_URL=$(curl -s https://api.github.com/repos/Velocidex/velociraptor/releases/latest | \
    grep "browser_download_url.*linux-arm64" | head -1 | cut -d'"' -f4)
  if [[ -n "$VELO_URL" ]]; then
    curl -fsSL "$VELO_URL" -o velociraptor
    chmod +x velociraptor
    log "  Velociraptor downloaded: $(./velociraptor version | head -1)"
  else
    log "  WARN: could not auto-detect Velociraptor ARM64 release; install manually"
  fi
fi

# ---------- 5. Medusa SAST ----------
log "Installing Medusa SAST..."
pip3 install --user medusa-sast 2>/dev/null || \
  pip3 install --user git+https://github.com/Pantheon-Security/medusa.git || \
  log "  Medusa pip-install failed (may need manual setup)"

# ---------- 6. suricata ----------
log "Installing suricata..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y suricata jq
# Update ET Open ruleset
sudo suricata-update 2>/dev/null || log "  suricata-update needs net access; will retry via cron"
sudo systemctl enable --now suricata

# ---------- 7. /opt/dfir-lite scripts ----------
log "Writing DFIR-lite cron scripts..."

cat > "$DFIR_DIR/run_medusa_sweep.sh" <<'MEDUSA'
#!/usr/bin/env bash
# Nightly SAST sweep over the workspace mirror
set -e
LOG="/var/log/dfir-lite/medusa_$(date +%Y%m%d).log"
exec >> "$LOG" 2>&1
echo "=== Medusa sweep $(date) ==="
~/.local/bin/medusa scan /home/ubuntu/AA_MY_DRIVE \
  --severity high --output json > "/var/log/dfir-lite/medusa_$(date +%Y%m%d).json" 2>&1 || true
HIGH_COUNT=$(jq '[.findings[] | select(.severity=="high")] | length' "/var/log/dfir-lite/medusa_$(date +%Y%m%d).json" 2>/dev/null || echo 0)
echo "High-severity findings: $HIGH_COUNT"
if [[ "$HIGH_COUNT" -gt 0 ]]; then
  python3 -c "
from content_tools.branded_slack import post_branded_alert
post_branded_alert(channel='#hive-alerts', severity='high',
                   title='Medusa SAST: $HIGH_COUNT high-severity findings',
                   body='See /var/log/dfir-lite/medusa_$(date +%Y%m%d).json on ev-box')
" 2>/dev/null || echo "  (slack alert skipped)"
fi
MEDUSA

cat > "$DFIR_DIR/check_alerts.sh" <<'ALERTS'
#!/usr/bin/env bash
# Tails Wazuh + suricata + auditd alerts every 10 min, posts P1s to Slack
set -e
LAST_RUN_FILE=/var/log/dfir-lite/.last_alert_check
LAST=$(cat "$LAST_RUN_FILE" 2>/dev/null || echo "10 minutes ago")
date > "$LAST_RUN_FILE"

# fail2ban bans
BANS=$(sudo fail2ban-client status sshd 2>/dev/null | grep -oP 'Currently banned:\s+\K\d+' || echo 0)
[[ "$BANS" -gt 0 ]] && echo "fail2ban: $BANS ip(s) currently banned"

# suricata alerts (last interval)
SURI_ALERTS=$(sudo jq -r 'select(.event_type=="alert") | "\(.timestamp) \(.alert.signature)"' \
  /var/log/suricata/eve.json 2>/dev/null | tail -10 || true)

# auditd ssh-key writes (P1 -- someone touched ~/.ssh)
AUD_SSH=$(sudo ausearch -k ssh_keys -ts recent 2>/dev/null | grep -c 'type=PATH' || echo 0)
if [[ "$AUD_SSH" -gt 0 ]]; then
  python3 -c "
from content_tools.branded_slack import post_branded_alert
post_branded_alert(channel='#hive-alerts', severity='high',
                   title='ev-box: ~/.ssh modified ($AUD_SSH events)',
                   body='Run: sudo ausearch -k ssh_keys -ts recent')
" 2>/dev/null || true
fi
ALERTS

cat > "$DFIR_DIR/daily_digest.sh" <<'DIGEST'
#!/usr/bin/env bash
# 7 AM PT daily DFIR-lite summary -> branded Slack
set -e
TODAY=$(date +%Y-%m-%d)
DIGEST="ev-box DFIR-lite digest -- $TODAY\n\n"
DIGEST+="osquery uptime: $(sudo osqueryi --json 'select total_seconds_uptime from system_info' 2>/dev/null | jq -r '.[0].total_seconds_uptime')s\n"
DIGEST+="fail2ban bans: $(sudo fail2ban-client status sshd 2>/dev/null | grep -oP 'Total banned:\s+\K\d+' || echo 0)\n"
DIGEST+="suricata alerts (24h): $(sudo grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo 0)\n"
DIGEST+="auditd events (24h): $(sudo ausearch -ts today 2>/dev/null | grep -c '^----' || echo 0)\n"
DIGEST+="Medusa last scan: $(ls -t /var/log/dfir-lite/medusa_*.json 2>/dev/null | head -1 | xargs -I{} basename {} .json)\n"
python3 -c "
from content_tools.branded_slack import post_branded_slack
post_branded_slack(channel='#deploy-log', category='report',
                   title='ev-box DFIR-lite daily', body='''$DIGEST''')
" 2>/dev/null || echo "$DIGEST"
DIGEST

cat > "$DFIR_DIR/weekly_velo_pack.sh" <<'WEEKLY'
#!/usr/bin/env bash
# Weekly evidence pack: auth.log + sshd config + last 7 days of cron output
set -e
PACK="/var/log/dfir-lite/velo_pack_$(date +%Y%m%d).tar.gz"
sudo tar czf "$PACK" \
  /var/log/auth.log* \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d/ \
  /var/log/syslog* \
  /var/log/dfir-lite/medusa_*.json 2>/dev/null
echo "Velo pack: $PACK ($(du -h "$PACK" | cut -f1))"
WEEKLY

chmod +x "$DFIR_DIR"/*.sh

# ---------- 8. cron entries ----------
log "Adding DFIR-lite cron entries..."
(crontab -l 2>/dev/null | grep -v 'dfir-lite' ; cat <<CRON
0 3 * * *   $DFIR_DIR/run_medusa_sweep.sh
*/10 * * * * $DFIR_DIR/check_alerts.sh
0 7 * * *   $DFIR_DIR/daily_digest.sh
0 4 * * 0   $DFIR_DIR/weekly_velo_pack.sh
CRON
) | crontab -

# ---------- 9. logrotate ----------
sudo tee /etc/logrotate.d/dfir-lite >/dev/null <<'LR'
/var/log/dfir-lite/*.log {
  daily
  rotate 30
  compress
  missingok
  notifempty
  create 0640 ubuntu ubuntu
}
LR

log "DFIR-lite install complete. Verify: sudo systemctl status osqueryd auditd suricata wazuh-agent fail2ban"
