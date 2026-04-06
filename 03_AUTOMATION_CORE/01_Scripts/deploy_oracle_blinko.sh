#!/bin/bash
# =============================================================================
# Deploy Docker + Blinko + Broker OS to Oracle Cloud VM
# Run from Termux (NOT PRoot) for reliable SSH:
#   bash /sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/deploy_oracle_blinko.sh
# =============================================================================

set -e
ORACLE_HOST="163.192.19.196"
ORACLE_USER="opc"
SSH_KEY="$HOME/.ssh/oracle_key.pem"
REMOTE_CMD="ssh -o ConnectTimeout=30 -o ServerAliveInterval=15 -i $SSH_KEY $ORACLE_USER@$ORACLE_HOST"

echo "=== Step 1: Install Docker on Oracle VM ==="
$REMOTE_CMD 'bash -s' << 'DOCKER_INSTALL'
set -e
if command -v docker &>/dev/null; then
    echo "Docker already installed: $(docker --version)"
else
    echo "Installing Docker..."
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl enable docker --now
    sudo usermod -aG docker opc
    echo "Docker installed: $(sudo docker --version)"
fi
DOCKER_INSTALL

echo "=== Step 2: Deploy Blinko ==="
$REMOTE_CMD 'bash -s' << 'BLINKO_DEPLOY'
set -e
mkdir -p ~/blinko

cat > ~/blinko/docker-compose.yml << 'COMPOSE'
version: '3.8'
services:
  blinko:
    image: blinkospace/blinko:latest
    container_name: everlight-blinko
    ports:
      - "1111:1111"
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
          memory: 200M

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
          memory: 100M
    command: postgres -c shared_buffers=32MB -c work_mem=4MB -c maintenance_work_mem=16MB -c effective_cache_size=64MB

volumes:
  blinko_data:
  blinko_pg_data:

networks:
  blinko-net:
    driver: bridge
COMPOSE

cd ~/blinko
sudo docker compose pull
sudo docker compose up -d
echo "Waiting for Blinko to start..."
sleep 15
curl -s -o /dev/null -w "Blinko HTTP status: %{http_code}\n" http://localhost:1111/
sudo docker ps
echo "=== Blinko deployed ==="
BLINKO_DEPLOY

echo "=== Step 3: Copy Broker OS files ==="
# Copy orchestrator and reddit_monitor to Oracle
SRC="/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts"
scp -o ConnectTimeout=30 -i "$SSH_KEY" \
    "$SRC/broker_daily_orchestrator.py" \
    "$SRC/reddit_monitor.py" \
    "$ORACLE_USER@$ORACLE_HOST:~/broker_os/"

echo "=== Step 4: Set up Broker OS cron on Oracle ==="
$REMOTE_CMD 'bash -s' << 'CRON_SETUP'
mkdir -p ~/broker_os
# Install crontab for Broker OS
cat > /tmp/broker_crontab << 'CRON'
# Broker OS Autonomous Pipeline - 4x daily
0 12 * * * cd ~/broker_os && python3 broker_daily_orchestrator.py full >> ~/broker_os/orchestrator.log 2>&1
0 19 * * * cd ~/broker_os && python3 broker_daily_orchestrator.py outreach >> ~/broker_os/orchestrator.log 2>&1
0 1 * * * cd ~/broker_os && python3 broker_daily_orchestrator.py scout >> ~/broker_os/orchestrator.log 2>&1
0 5 * * * cd ~/broker_os && python3 broker_daily_orchestrator.py match >> ~/broker_os/orchestrator.log 2>&1
# Reddit Monitor - Every 30 min during business hours (8 AM - 8 PM PT)
*/30 15-23 * * * cd ~/broker_os && python3 reddit_monitor.py scan >> ~/broker_os/reddit_monitor.log 2>&1
*/30 0-3 * * * cd ~/broker_os && python3 reddit_monitor.py scan >> ~/broker_os/reddit_monitor.log 2>&1
CRON
crontab /tmp/broker_crontab
echo "Cron installed:"
crontab -l
CRON_SETUP

echo "=== Step 5: Open firewall for Blinko (port 1111) ==="
$REMOTE_CMD 'sudo firewall-cmd --permanent --add-port=1111/tcp 2>/dev/null && sudo firewall-cmd --reload 2>/dev/null; echo "Firewall updated"'

echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE"
echo "=========================================="
echo "  Blinko: http://$ORACLE_HOST:1111"
echo "  Broker OS: cron running 4x daily"
echo "  Reddit Monitor: every 30 min"
echo ""
echo "  Next: Update BLINKO_URL in .env to http://$ORACLE_HOST:1111"
echo "=========================================="
