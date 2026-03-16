#!/bin/bash
# One-shot script: copies automation scripts to Oracle VM + installs crontab
# Run from phone: bash xlm_bot/setup_oracle_24x7.sh

set -e

VM_IP="163.192.19.196"
VM_USER="opc"
SSH_KEY="$HOME/.ssh/oracle_key.pem"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -o ServerAliveInterval=5"
BOT_DIR="/home/opc/xlm-bot"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Step 1: Testing SSH ==="
ssh -i "$SSH_KEY" $SSH_OPTS ${VM_USER}@${VM_IP} 'echo "SSH OK: $(hostname)"' || {
    echo "ERROR: Cannot reach Oracle VM. Is it running?"
    exit 1
}

echo ""
echo "=== Step 2: Copying automation scripts ==="
scp -i "$SSH_KEY" $SSH_OPTS \
    "$LOCAL_DIR/watchdog.sh" \
    "$LOCAL_DIR/memory_guard.sh" \
    "$LOCAL_DIR/circuit_breaker.sh" \
    "$LOCAL_DIR/log_rotate.sh" \
    ${VM_USER}@${VM_IP}:${BOT_DIR}/

echo ""
echo "=== Step 3: Making scripts executable ==="
ssh -i "$SSH_KEY" $SSH_OPTS ${VM_USER}@${VM_IP} "chmod +x ${BOT_DIR}/{watchdog,memory_guard,circuit_breaker,log_rotate}.sh"

echo ""
echo "=== Step 4: Installing crontab ==="
ssh -i "$SSH_KEY" $SSH_OPTS ${VM_USER}@${VM_IP} 'bash -s' <<'REMOTE'
# Remove old XLM entries, add fresh ones
(crontab -l 2>/dev/null | grep -v "XLM BOT" | grep -v "xlm_" | grep -v "memory_guard" | grep -v "watchdog" | grep -v "circuit_breaker" | grep -v "log_rotate"; \
echo "### XLM BOT AUTOMATION ###"; \
echo "1-56/5 * * * * flock -xn /tmp/xlm_memguard.lock /home/opc/xlm-bot/memory_guard.sh"; \
echo "2-57/5 * * * * flock -xn /tmp/xlm_watchdog.lock /home/opc/xlm-bot/watchdog.sh"; \
echo "*/10 * * * * flock -xn /tmp/xlm_cb.lock /home/opc/xlm-bot/circuit_breaker.sh"; \
echo "0 * * * * flock -xn /tmp/xlm_logrotate.lock /home/opc/xlm-bot/log_rotate.sh"; \
echo "### END XLM BOT AUTOMATION ###") | crontab -
REMOTE

echo ""
echo "=== Step 5: Verifying ==="
ssh -i "$SSH_KEY" $SSH_OPTS ${VM_USER}@${VM_IP} 'echo "--- Crontab ---" && crontab -l && echo "" && echo "--- Docker ---" && docker ps --format "table {{.Names}}\t{{.Status}}" && echo "" && echo "--- Scripts ---" && ls -la '"${BOT_DIR}"'/*.sh'

echo ""
echo "=== DONE! 24/7 automation installed ==="
echo "Cron jobs: memory_guard (5m), watchdog (5m), circuit_breaker (10m), log_rotate (1h)"
