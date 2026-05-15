#!/usr/bin/env bash
# e5_mother provisioner -- runs from PHONE, SSHes into the new mother VM,
# brings up the heavy service stack (Blinko PG-backed, agentmemory MCP, Open WebUI,
# hive-voice). hive-django is DEFERRED to Phase 7 per recover-and-replace plan;
# see /root/.claude/plans/yeah-its-a-r3c9ver-polymorphic-crystal.md and
# 08_BACKUPS/recovery_log.md.
#
# Mirrors the ev-box pattern but for the always-on Tier-0 services.
# Idempotent. Auto by default. --interactive to confirm each phase.
#
# Usage:
#   bash provision.sh <public-ip-of-mother>
#   bash provision.sh <public-ip-of-mother> --interactive
#
# Prereqs:
#   - VM launched from e5_mother/cloud_init.yaml
#   - cloud-init finished -> /var/lib/cloud/mother.ready exists
#   - SSH key /root/.ssh/github_deploy on phone
#   - Tailscale auth key in /root/.ssh/tailscale_authkey (one-line file)

set -euo pipefail

EV_HOST="${1:-}"
MODE="auto"
[[ "${2:-}" == "--interactive" ]] && MODE="interactive"

if [[ -z "$EV_HOST" ]]; then
  cat >&2 <<EOF
ERROR: pass the public IP of the mother VM as arg 1

  Usage:  bash provision.sh <public-ip>
          bash provision.sh <public-ip> --interactive

EOF
  exit 2
fi

SSH_KEY="/root/.ssh/github_deploy"
SSH="ssh -i $SSH_KEY -p 2222 -o StrictHostKeyChecking=accept-new ubuntu@$EV_HOST"
SCP="scp -i $SSH_KEY -P 2222 -o StrictHostKeyChecking=accept-new"
WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
DEPLOY_LOG="$WORKSPACE/_logs/e5_mother_provision_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$DEPLOY_LOG")"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$DEPLOY_LOG"; }

confirm() {
  [[ "$MODE" == "auto" ]] && return 0
  read -r -p "  -> proceed with $1? [Y/n] " a
  [[ -z "$a" || "$a" == "y" || "$a" == "Y" ]]
}

phase_0_handshake() {
  log "Phase 0 -- SSH handshake to $EV_HOST:2222"
  $SSH "test -f /var/lib/cloud/mother.ready && echo READY" \
    | tee -a "$DEPLOY_LOG" | grep -q READY \
    || { log "FAIL: cloud-init not finished. Wait 2-3 more minutes and retry."; exit 3; }
  log "  ok -- cloud-init complete on remote"
}

phase_1_tailnet() {
  log "Phase 1 -- Tailscale auth"
  if [[ ! -f /root/.ssh/tailscale_authkey ]]; then
    log "FAIL: /root/.ssh/tailscale_authkey missing. Generate one at https://login.tailscale.com/admin/settings/keys"
    exit 4
  fi
  local TS_KEY
  TS_KEY="$(tr -d '[:space:]' < /root/.ssh/tailscale_authkey)"
  confirm "Tailscale auth" || return 0
  $SSH "sudo tailscale up --authkey='$TS_KEY' --hostname=e5-mother --ssh --advertise-tags=tag:mother --accept-routes=false" \
    2>&1 | tee -a "$DEPLOY_LOG"
  local TS_IP
  TS_IP="$($SSH 'tailscale ip -4 | head -1')"
  log "  ok -- mother on tailnet at $TS_IP"
  echo "$TS_IP" > "$WORKSPACE/_state/e5_mother_tailnet_ip.txt"
}

phase_2_workspace_mirror() {
  log "Phase 2 -- one-way workspace mirror to /home/ubuntu/AA_MY_DRIVE"
  confirm "workspace rsync" || return 0
  rsync -az --delete --exclude '_logs/' --exclude '.git/' --exclude 'node_modules/' --exclude '__pycache__/' \
    -e "ssh -i $SSH_KEY -p 2222" \
    "$WORKSPACE/" "ubuntu@$EV_HOST:/home/ubuntu/AA_MY_DRIVE/" 2>&1 \
    | tail -10 | tee -a "$DEPLOY_LOG"
  log "  ok -- workspace mirrored"
}

phase_3_blinko() {
  log "Phase 3 -- Blinko RAG with PostgreSQL backend (Docker, :1111 bound to 127.0.0.1)"
  confirm "deploy Blinko (PG-backed compose, extracted from deploy_oracle_blinko.sh)" || return 0
  # Compose pattern lifted from /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/deploy_oracle_blinko.sh
  # (lines 34-91). Uses postgres:14-alpine as backend with restart=always and memory limits.
  # Bound to 127.0.0.1; nginx phase_6 exposes via tailnet0 only.
  $SSH 'mkdir -p ~/blinko && cat > ~/blinko/docker-compose.yml <<'"'"'COMPOSE'"'"'
version: "3.8"
services:
  blinko:
    image: blinkospace/blinko:latest
    container_name: everlight-blinko
    ports:
      - "127.0.0.1:1111:1111"
    environment:
      - NODE_ENV=production
      - NEXTAUTH_URL=http://localhost:1111
      - NEXT_PUBLIC_BASE_URL=http://localhost:1111
      - NEXTAUTH_SECRET=everlight_blinko_production_key_2026
      - DATABASE_URL=postgresql://blinko:blinko_secure_pass@blinko-db:5432/blinko
    volumes:
      - blinko_data:/app/.blinko
    depends_on:
      blinko-db:
        condition: service_healthy
    restart: always
    networks:
      - blinko-net
    deploy:
      resources:
        limits:
          memory: 1200M
  blinko-db:
    image: postgres:14-alpine
    container_name: everlight-blinko-db
    environment:
      - POSTGRES_USER=blinko
      - POSTGRES_PASSWORD=blinko_secure_pass
      - POSTGRES_DB=blinko
    volumes:
      - blinko_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U blinko"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always
    networks:
      - blinko-net
    deploy:
      resources:
        limits:
          memory: 400M
    command: postgres -c shared_buffers=128MB -c work_mem=8MB -c maintenance_work_mem=32MB -c effective_cache_size=256MB
volumes:
  blinko_data:
  blinko_pg_data:
networks:
  blinko-net:
    driver: bridge
COMPOSE
cd ~/blinko && sudo docker compose pull 2>&1 | tail -3 && sudo docker compose up -d 2>&1 | tail -5
echo "Waiting 20s for Blinko to start..."
sleep 20
curl -s -o /dev/null -w "Blinko HTTP status: %{http_code}\n" http://localhost:1111/' 2>&1 | tee -a "$DEPLOY_LOG"
  log "  ok -- Blinko + PG on :1111 (localhost). Run blinko_restore_from_lite.py to restore 614 notes."

  # Install nightly mirror cron + scripts dir per oracle-only-crons doctrine
  log "  installing nightly mirror cron (3:15 AM on mother)"
  $SCP "$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/blinko_mirror.sh" "ubuntu@$EV_HOST:/home/ubuntu/scripts/blinko_mirror.sh" 2>&1 | tail -2 | tee -a "$DEPLOY_LOG"
  $SSH 'mkdir -p ~/scripts ~/logs && chmod +x ~/scripts/blinko_mirror.sh 2>/dev/null
( crontab -l 2>/dev/null | grep -v blinko_mirror; echo "15 3 * * * /home/ubuntu/scripts/blinko_mirror.sh >> /home/ubuntu/logs/blinko_mirror.log 2>&1" ) | crontab -' 2>&1 | tee -a "$DEPLOY_LOG"
}

phase_4_agentmemory() {
  log "Phase 4 -- agentmemory MCP on :3108"
  confirm "deploy agentmemory" || return 0
  $SSH 'cd ~ && [ ! -d agentmemory ] && git clone https://github.com/rohitg00/agentmemory || (cd agentmemory && git pull)
cd ~/agentmemory && npm install --omit=dev 2>&1 | tail -3
# Use built-in MCP server if available; otherwise note for manual config
cat > ~/agentmemory.service <<UNIT
[Unit]
Description=agentmemory MCP server
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agentmemory
ExecStart=/usr/bin/node dist/cli/mcp.js --port 3108 --bind 127.0.0.1
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
sudo mv ~/agentmemory.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now agentmemory 2>&1 | tail -3' 2>&1 | tee -a "$DEPLOY_LOG"
  log "  ok -- agentmemory on :3108 (verify manually -- entrypoint may differ between releases)"
}

phase_5_openwebui() {
  log "Phase 5 -- Open WebUI (Docker, :8080 tailnet-only)"
  confirm "deploy Open WebUI" || return 0
  $SSH 'sudo docker run -d \
    --name openwebui \
    --restart always \
    -p 127.0.0.1:8080:8080 \
    -v openwebui_data:/app/backend/data \
    -e WEBUI_AUTH=true \
    ghcr.io/open-webui/open-webui:main 2>&1 | tail -3' 2>&1 | tee -a "$DEPLOY_LOG"
  log "  ok -- Open WebUI on :8080. Reach via http://<mother-tailnet-ip>:8080 after nginx proxy."
}

phase_5b_hive_voice() {
  log "Phase 5b -- hive-voice (Twilio webhook handler on :8200)"
  confirm "deploy hive-voice" || return 0
  $SSH 'mkdir -p /home/ubuntu/hive_voice /home/ubuntu/hive_voice/logs' 2>&1 | tee -a "$DEPLOY_LOG"
  $SCP "$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/hive_voice_handler.py" "ubuntu@$EV_HOST:/home/ubuntu/hive_voice/handler.py" 2>&1 | tail -2 | tee -a "$DEPLOY_LOG"

  # Try to install Python deps the handler needs (flask + twilio at minimum)
  $SSH 'cd /home/ubuntu/hive_voice && python3 -m venv venv 2>&1 | tail -3
. venv/bin/activate && pip install --quiet flask twilio requests python-dotenv 2>&1 | tail -3' 2>&1 | tee -a "$DEPLOY_LOG"

  # Empty .env placeholder; secrets regenerated per recovery_log.md
  $SSH 'test -f /home/ubuntu/hive_voice/.env || cat > /home/ubuntu/hive_voice/.env <<ENVFILE
# Regenerate these from provider dashboards per 08_BACKUPS/recovery_log.md
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
ELEVENLABS_API_KEY=
ANTHROPIC_API_KEY=
ENVFILE
chmod 600 /home/ubuntu/hive_voice/.env' 2>&1 | tee -a "$DEPLOY_LOG"

  $SSH 'sudo tee /etc/systemd/system/hive-voice.service > /dev/null <<UNIT
[Unit]
Description=Hive Voice Handler (Marcus Twilio webhook)
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/hive_voice
EnvironmentFile=-/home/ubuntu/hive_voice/.env
ExecStart=/home/ubuntu/hive_voice/venv/bin/python /home/ubuntu/hive_voice/handler.py
Restart=always
RestartSec=8
StandardOutput=append:/home/ubuntu/hive_voice/logs/hive_voice.log
StandardError=append:/home/ubuntu/hive_voice/logs/hive_voice.err
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable hive-voice 2>&1 | tail -2
# Start only if .env has TWILIO creds (avoid crash-loop on empty config)
if grep -q "^TWILIO_ACCOUNT_SID=." /home/ubuntu/hive_voice/.env 2>/dev/null; then
  sudo systemctl start hive-voice
  sleep 2
  systemctl is-active hive-voice
else
  echo "hive-voice unit installed but NOT started -- fill in .env then: sudo systemctl start hive-voice"
fi' 2>&1 | tee -a "$DEPLOY_LOG"
  log "  ok -- hive-voice unit installed. Status depends on whether .env was populated."
}

phase_5c_n8n() {
  # n8n is PARKED 2026-04-24. See 08_BACKUPS/recovery_log.md and CLAUDE.md doctrine.
  # All workflows were on the dead .250 mother and are unrecoverable (no exports).
  # The Python content_tools chain replaces it: branded_mailer / branded_slack / publish_gdoc.
  log "Phase 5c -- n8n: PARKED, skipping (see 08_BACKUPS/recovery_log.md)"
}

phase_6_nginx_tailnet() {
  log "Phase 6 -- nginx tailnet reverse proxy"
  confirm "configure nginx" || return 0
  local TS_IP
  TS_IP="$($SSH 'tailscale ip -4 | head -1')"
  $SSH "sudo tee /etc/nginx/sites-available/mother-tailnet > /dev/null <<NGX
server {
  listen $TS_IP:80;
  server_name _;

  location /blinko/    { proxy_pass http://127.0.0.1:1111/; proxy_set_header Host \\\$host; }
  location /agentmem/  { proxy_pass http://127.0.0.1:3108/; proxy_set_header Host \\\$host; }
  location /openwebui/ { proxy_pass http://127.0.0.1:8080/; proxy_set_header Host \\\$host; proxy_http_version 1.1; proxy_set_header Upgrade \\\$http_upgrade; proxy_set_header Connection 'upgrade'; }
  location /voice/     { proxy_pass http://127.0.0.1:8200/; proxy_set_header Host \\\$host; }
  location /           { return 200 'e5-mother online\\n'; add_header Content-Type text/plain; }
}
NGX
sudo ln -sf /etc/nginx/sites-available/mother-tailnet /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx" 2>&1 | tee -a "$DEPLOY_LOG"
  log "  ok -- nginx proxying http://$TS_IP/{blinko,agentmem,openwebui}"
}

phase_7_register() {
  log "Phase 7 -- register mother in phone SSH config + workspace state"
  local TS_IP
  TS_IP="$(cat "$WORKSPACE/_state/e5_mother_tailnet_ip.txt" 2>/dev/null || echo '')"
  [[ -z "$TS_IP" ]] && { log "  skip -- no tailnet IP captured"; return 0; }
  if ! grep -q "Host e5-mother" /root/.ssh/config 2>/dev/null; then
    cat >> /root/.ssh/config <<EOF

Host e5-mother
  HostName $TS_IP
  User ubuntu
  Port 2222
  IdentityFile $SSH_KEY
  StrictHostKeyChecking no

Host e5-mother-public
  HostName $EV_HOST
  User ubuntu
  Port 2222
  IdentityFile $SSH_KEY
  StrictHostKeyChecking no
EOF
    log "  ok -- added 'e5-mother' (tailnet) and 'e5-mother-public' (break-glass) to ~/.ssh/config"
  fi
}

phase_8_smoke() {
  log "Phase 8 -- smoke tests"
  $SSH 'for url in http://127.0.0.1:1111 http://127.0.0.1:3108 http://127.0.0.1:8080 http://127.0.0.1:8200; do
    printf "%s -> " "$url"
    curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 "$url"
  done
echo "--- systemd units ---"
for u in agentmemory hive-voice; do
  printf "%s: " "$u"
  systemctl is-active "$u" 2>&1
done
echo "--- docker ---"
sudo docker ps --format "{{.Names}} {{.Status}}"' | tee -a "$DEPLOY_LOG"
}

log "=== e5_mother provisioning start  host=$EV_HOST mode=$MODE ==="
phase_0_handshake
phase_1_tailnet
phase_2_workspace_mirror
phase_3_blinko
phase_4_agentmemory
phase_5_openwebui
phase_5b_hive_voice
phase_5c_n8n
phase_6_nginx_tailnet
phase_7_register
phase_8_smoke
log "=== e5_mother provisioning complete -- see $DEPLOY_LOG ==="
log ""
log "Next steps (manual):"
log "  1. Verify Blinko UI:    ssh e5-mother 'curl -s localhost:1111 | head -5'"
log "  2. Restore 614 Blinko notes: bash $WORKSPACE/03_AUTOMATION_CORE/01_Scripts/blinko_restore_from_lite.py"
log "  3. Regenerate secrets from provider dashboards into /home/ubuntu/hive_voice/.env, then:"
log "     ssh e5-mother 'sudo systemctl start hive-voice'"
log "  4. Add agentmemory MCP entry to /mnt/sdcard/AA_MY_DRIVE/.mcp.json on port 3108"
log "  5. Verify OCI VCN: allow TCP 2222 from 0.0.0.0/0 (break-glass), nothing else from public."
log "  6. (Phase 7 deferred) hive-django restore decision: see 08_BACKUPS/recovery_log.md"
