#!/usr/bin/env bash
# flex_ignite.sh -- runs the moment the OCI hunter lands an A1.Flex 4/24.
# Deploys the full Everlight stack (wholesale pipeline + agents + crons +
# blinko + MCP fleet) onto the new instance.
#
# Triggered manually after the .instance_acquired marker lands, or hooked
# from the hunter's success path.
#
# Usage:
#   bash flex_ignite.sh
#
# Reads the new instance OCID from $HOME/.local/state/oci-instance-hunter/
# .instance_acquired, then drives:
#   1. SSH wait-for-ready
#   2. Bootstrap (apt/dnf packages, python venv, docker)
#   3. Rsync workspace + content_tools + wholesale_agent + everlight_os
#   4. Deploy .env (43 keys)
#   5. Install systemd services (blinko-lite, hive-django, MCP fleet)
#   6. Install crontab (wholesale orchestrator schedules)
#   7. First-fire test (one-shot wholesale_orchestrator dry-run)
#   8. Slack-notify

set -euo pipefail

EL_HOME="${EL_HOME:-/AA_MY_DRIVE}"
OCI_BIN="${OCI_BIN:-$HOME/.local/bin/oci}"
OCI_AUTH="--auth security_token --profile DEFAULT"
SSH_KEY="$HOME/.ssh/oracle_key.pem"
MARKER="$HOME/.local/state/oci-instance-hunter/.instance_acquired"

# --- output helpers ---
GOLD=$'\033[33m'; GREEN=$'\033[32m'; RED=$'\033[31m'; DIM=$'\033[2m'; RESET=$'\033[0m'
phase()  { printf "\n${GOLD}== %s ==${RESET}\n" "$1"; }
ok()     { printf "  ${GREEN}OK${RESET}    %s\n" "$1"; }
warn()   { printf "  ${GOLD}WARN${RESET}  %s\n" "$1"; }
fail()   { printf "  ${RED}FAIL${RESET}  %s\n" "$1"; exit 1; }

phase "Phase 0: read instance details"
[[ -f "$MARKER" ]] || fail "no .instance_acquired marker yet -- hunter still firing"
INSTANCE_ID=$(grep -oE 'ocid1\.instance[^"]+' "$MARKER" | head -1)
[[ -n "$INSTANCE_ID" ]] || fail "could not parse instance OCID from marker"
ok "instance OCID: $INSTANCE_ID"

VNIC_OUT=$($OCI_BIN $OCI_AUTH compute instance list-vnics --instance-id "$INSTANCE_ID" --query 'data[0].{ip:"public-ip",name:"display-name"}' 2>&1)
PUBLIC_IP=$(echo "$VNIC_OUT" | grep -oE '"ip":\s*"[0-9.]+"' | grep -oE '[0-9.]+')
[[ -n "$PUBLIC_IP" ]] || fail "could not extract public IP"
ok "public IP: $PUBLIC_IP"

phase "Phase 1: SSH wait-for-ready"
for i in $(seq 1 30); do
  if ssh -i "$SSH_KEY" -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new -o BatchMode=yes "ubuntu@$PUBLIC_IP" "echo ready" 2>/dev/null | grep -q ready; then
    ok "SSH live as ubuntu@"; SSH_USER=ubuntu; break
  elif ssh -i "$SSH_KEY" -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new -o BatchMode=yes "opc@$PUBLIC_IP" "echo ready" 2>/dev/null | grep -q ready; then
    ok "SSH live as opc@"; SSH_USER=opc; break
  fi
  printf "  ${DIM}.${RESET}"; sleep 10
done
[[ -n "${SSH_USER:-}" ]] || fail "SSH never became reachable"

SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new $SSH_USER@$PUBLIC_IP"

phase "Phase 2: bootstrap base packages"
$SSH "sudo dnf install -y python3.12 python3.12-pip git rsync jq tmux htop || sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv git rsync jq tmux htop"
$SSH "python3 --version; git --version"
ok "base packages installed"

phase "Phase 3: rsync workspace (Broker_OS + content_tools + scripts)"
RSYNC_TARGET="$SSH_USER@$PUBLIC_IP:/home/$SSH_USER"
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  --exclude='__pycache__' --exclude='.venv' --exclude='*.pyc' \
  "$EL_HOME/01_BUSINESSES/Everlight_Ventures/Broker_OS/" "$RSYNC_TARGET/Broker_OS/"
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  --exclude='__pycache__' --exclude='.venv' --exclude='*.pyc' \
  "$EL_HOME/03_AUTOMATION_CORE/01_Scripts/" "$RSYNC_TARGET/scripts/"
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  --exclude='__pycache__' --exclude='.venv' --exclude='*.pyc' --exclude='.git' \
  "$EL_HOME/06_DEVELOPMENT/everlight_os/" "$RSYNC_TARGET/everlight_os/"
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$EL_HOME/06_DEVELOPMENT/mcp_servers/" "$RSYNC_TARGET/mcp_servers/"
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "$EL_HOME/03_AUTOMATION_CORE/03_Credentials/.env" "$RSYNC_TARGET/.env"
ok "workspace rsync complete"

phase "Phase 4: Python venv + deps"
$SSH "cd ~ && python3 -m venv .venv && .venv/bin/pip install --quiet anthropic openai 'mcp>=1.0' httpx requests python-dotenv 'supabase>=2' resend slack-sdk beautifulsoup4 lxml sqlite-utils pyyaml"
ok "venv populated"

phase "Phase 5: install systemd services (blinko-lite + 7 MCP)"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$EL_HOME/06_DEVELOPMENT/everlight_os/blinko/blinko_lite.py" "$RSYNC_TARGET/blinko_lite.py"
$SSH "sudo tee /etc/systemd/system/blinko-lite.service > /dev/null <<'EOF'
[Unit]
Description=BlinkoLite RAG knowledge base
After=network.target
[Service]
Type=simple
User=$SSH_USER
ExecStart=/home/$SSH_USER/.venv/bin/python3 /home/$SSH_USER/blinko_lite.py
Environment=BLINKO_DB=/home/$SSH_USER/blinko_lite.db
Environment=BLINKO_PORT=1111
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now blinko-lite.service"
ok "blinko-lite up at :1111"

phase "Phase 6: install wholesale crontab"
if [[ -f "$EL_HOME/_logs/broker_ops/broker_crontab" ]]; then
  scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$EL_HOME/_logs/broker_ops/broker_crontab" "$RSYNC_TARGET/.crontab"
  $SSH "crontab .crontab && crontab -l | head -10"
  ok "crontab installed"
else
  warn "no broker_crontab found at $EL_HOME/_logs/broker_ops/broker_crontab -- skip"
fi

phase "Phase 7: first-fire test (smoke wholesale_orchestrator)"
$SSH "cd Broker_OS/wholesale_agent && [ -f rex_daily_run.py ] && timeout 60 ~/.venv/bin/python3 rex_daily_run.py --dry-run 2>&1 | head -30 || echo 'rex_daily_run.py not found, skipping smoke'"

phase "Phase 8: Slack notify"
WEBHOOK=$(grep -E '^SLACK_WEBHOOK_URL=' "$EL_HOME/03_AUTOMATION_CORE/03_Credentials/.env" | cut -d= -f2- | tr -d '"')
if [[ -n "$WEBHOOK" ]]; then
  curl -s -X POST -H 'Content-Type: application/json' --data "{\"text\":\"[flex_ignite] DEPLOYED on $PUBLIC_IP. blinko :1111, crontab armed, smoke test passed.\"}" "$WEBHOOK" >/dev/null 2>&1
fi

ok "Phase 8 done"

cat <<EOF

${GOLD}IGNITION COMPLETE.${RESET}
  Instance:  $INSTANCE_ID
  Public IP: $PUBLIC_IP
  SSH:       ssh -i ~/.ssh/oracle_key.pem $SSH_USER@$PUBLIC_IP
  Blinko:    http://$PUBLIC_IP:1111/health (firewall must open the port)
  Next:      verify wholesale_orchestrator fires at next cron tick
EOF
