#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# Oracle Cloud Always-Free Setup Script for XLM Bot
# Run this ONCE after SSH-ing into your new VM
# Usage: bash cloud-setup.sh
# ──────────────────────────────────────────────────────────────────────
set -e

echo "═══════════════════════════════════════════════"
echo "  XLM Bot — Oracle Cloud Setup"
echo "═══════════════════════════════════════════════"

# ── 1. System updates + Docker install ───────────────────────────────
echo ""
echo "[1/6] Installing Docker..."

# Detect OS
if [ -f /etc/oracle-release ] || [ -f /etc/redhat-release ]; then
    # Oracle Linux / RHEL
    sudo dnf -y install dnf-utils
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
elif [ -f /etc/lsb-release ]; then
    # Ubuntu
    sudo apt-get update -qq
    sudo apt-get install -y -qq ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
    echo "Unknown OS — install Docker manually"
    exit 1
fi

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
echo "  ✓ Docker installed"

# ── 2. Create bot directory ──────────────────────────────────────────
echo ""
echo "[2/6] Creating directory structure..."
BOT_DIR="$HOME/xlm-bot"
mkdir -p "$BOT_DIR"/{secrets,data,logs}
echo "  ✓ Created $BOT_DIR"

# ── 3. Firewall (iptables for Oracle Linux) ──────────────────────────
echo ""
echo "[3/6] Opening firewall port 8502..."
if command -v firewall-cmd &>/dev/null; then
    sudo firewall-cmd --permanent --add-port=8502/tcp 2>/dev/null || true
    sudo firewall-cmd --reload 2>/dev/null || true
    echo "  ✓ firewall-cmd: port 8502 opened"
elif command -v iptables &>/dev/null; then
    sudo iptables -I INPUT -p tcp --dport 8502 -j ACCEPT 2>/dev/null || true
    echo "  ✓ iptables: port 8502 opened"
fi

# ── 4. Remind about secrets ─────────────────────────────────────────
echo ""
echo "[4/6] Secrets setup..."
echo ""
echo "  ⚠  You need to copy your Coinbase API config to the server:"
echo ""
echo "  From your phone/laptop, run:"
echo "    scp -i your_key.pem config.json opc@YOUR_IP:~/xlm-bot/secrets/"
echo ""
echo "  The config.json should contain your Coinbase API key, secret, etc."
echo "  (Same file that's in your Termux secrets/ folder)"
echo ""

# ── 5. Create .env file ─────────────────────────────────────────────
echo "[5/6] Creating .env file..."
cat > "$BOT_DIR/.env" << 'ENVEOF'
COINBASE_CONFIG_PATH=/app/secrets/config.json
CRYPTO_BOT_DIR=/app
TZ=America/Los_Angeles
# Paste your Slack webhook URL below (optional)
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxxx
ENVEOF
echo "  ✓ Created $BOT_DIR/.env"

# ── 6. Summary ───────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Setup complete! Next steps:"
echo "═══════════════════════════════════════════════"
echo ""
echo "  1. Upload your bot code:"
echo "     scp -i key.pem -r xlm_bot/* opc@YOUR_IP:~/xlm-bot/"
echo ""
echo "  2. Upload Coinbase secrets:"
echo "     scp -i key.pem config.json opc@YOUR_IP:~/xlm-bot/secrets/"
echo ""
echo "  3. Update Slack webhook in ~/xlm-bot/.env (optional)"
echo ""
echo "  4. Start the bot:"
echo "     cd ~/xlm-bot && docker compose up -d"
echo ""
echo "  5. View dashboard at: http://YOUR_IP:8502"
echo ""
echo "  6. View logs:"
echo "     docker compose logs -f"
echo ""
echo "  NOTE: Log out and back in for Docker group to take effect:"
echo "     exit"
echo "     ssh -i key.pem opc@YOUR_IP"
echo ""
