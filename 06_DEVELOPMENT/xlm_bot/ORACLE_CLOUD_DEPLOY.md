# Oracle Cloud Free Tier Deployment Guide
# XLM Perp Bot - 24/7 Cloud Deployment

## Why Oracle Cloud (Free Forever)
- Ampere A1 (ARM64): 4 OCPU + 24GB RAM - free forever tier
- Ubuntu 22.04 LTS - stable Linux environment
- Static IP available free
- Bot runs 24/7 without phone battery/Android killing it
- ~$0/month if you stay within free tier limits

## Step 1: Create Oracle Cloud Account
1. Go to cloud.oracle.com and sign up
2. Use a real credit card (required for verification, not charged on free tier)
3. Select home region closest to you (e.g. US West Phoenix, or US East Ashburn)
4. Wait for account activation email (can take 1-24 hours)

WARNING: Oracle free tier availability varies by region. If Ampere A1 shows
"Out of capacity", try a different region or check back in a few hours.
Alternative: Google Cloud e2-micro (always-free, 1 vCPU, 1GB RAM, US regions only)

## Step 2: Create Your Free VM

In Oracle Cloud Console:
1. Compute > Instances > Create Instance
2. Name: xlm-bot
3. Image: Ubuntu 22.04 (Canonical)
4. Shape: Change to "Ampere" > VM.Standard.A1.Flex
   - OCPU: 2 (free tier gives 4 total, use 2 for the bot)
   - Memory: 12 GB
5. Networking: Create new VCN or use existing
   - Make sure "Assign public IPv4" is checked
6. SSH keys: Paste your public SSH key (generate with: ssh-keygen -t ed25519)
7. Boot volume: 50GB (free tier gives 200GB total)
8. Click Create

Wait 2-3 minutes for instance to become RUNNING.

## Step 3: Configure Firewall (Open Port 8502 for Dashboard)

In Oracle Cloud Console:
1. Networking > Virtual Cloud Networks > your VCN > Security Lists
2. Add Ingress Rule:
   - Source CIDR: 0.0.0.0/0 (or your IP for security)
   - Destination Port: 8502
   - Protocol: TCP

Also on the VM itself (Ubuntu firewall):
```bash
sudo iptables -I INPUT -p tcp --dport 8502 -j ACCEPT
sudo netfilter-persistent save
```

## Step 4: SSH Into Your VM

```bash
ssh ubuntu@YOUR_VM_PUBLIC_IP
```

## Step 5: Install Docker

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin
docker compose version  # verify
```

## Step 6: Copy Bot Files to Cloud VM

From your phone/local machine, copy the bot directory:

Option A - rsync (recommended):
```bash
rsync -avz --exclude='data/' --exclude='logs/' --exclude='__pycache__' \
    /mnt/sdcard/AA_MY_DRIVE/xlm_bot/ \
    ubuntu@YOUR_VM_IP:~/xlm_bot/
```

Option B - git (if you push to a private repo):
```bash
git clone https://github.com/YOUR_REPO/xlm_bot.git ~/xlm_bot
```

## Step 7: Set Up Secrets and Config

On the cloud VM:
```bash
cd ~/xlm_bot
mkdir -p secrets data logs

# Copy your Coinbase API credentials
# Either scp from phone or paste manually:
nano secrets/config.json
# Paste your Coinbase API JSON (api_key + api_secret fields)

# Create .env file from example
cp .env.example .env
nano .env
```

Fill in your .env:
```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
GEMINI_API_KEY=AIzaSy-YOUR_GEMINI_KEY (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/... (optional)
```

Get your ANTHROPIC_API_KEY from: console.anthropic.com > API Keys

## Step 8: Build and Start the Bot

```bash
cd ~/xlm_bot

# Build Docker image (takes 5-10 min first time, installs Node + claude CLI)
docker compose build

# Start bot (detached mode, auto-restarts on crash)
docker compose up -d

# Watch logs
docker compose logs -f xlm-bot

# Check health status
docker ps  # should show "healthy" after ~2 min
```

## Step 9: Verify Bot is Trading

```bash
# Check bot cycle logs
docker compose exec xlm-bot tail -50 logs/xpb_console.log

# Check AI advisor logs
docker compose exec xlm-bot tail -20 logs/ai_debug.log

# Check heartbeat (should be <60 seconds old)
docker compose exec xlm-bot python3 -c "
import time; from pathlib import Path
hb = Path('data/.heartbeat')
age = time.time() - float(hb.read_text())
print(f'Heartbeat age: {age:.0f}s')
"

# Dashboard: open browser to http://YOUR_VM_IP:8502
```

## Step 10: Verify Auto-Restart Works

```bash
# Test that restart:always works
docker compose restart xlm-bot
docker ps  # should come back up within 10s
```

## Ongoing Management

### Check bot status:
```bash
docker compose logs -f --tail=100 xlm-bot
```

### Update bot code:
```bash
rsync -avz /mnt/sdcard/AA_MY_DRIVE/xlm_bot/ ubuntu@YOUR_VM_IP:~/xlm_bot/
docker compose build && docker compose up -d
```

### Stop/start:
```bash
docker compose stop
docker compose start
```

### View all logs:
```bash
# Console log (bot cycles)
docker compose exec xlm-bot tail -f logs/xpb_console.log

# AI decisions
docker compose exec xlm-bot tail -f logs/ai_debug.log

# Trade history
docker compose exec xlm-bot cat logs/trades.csv
```

## Troubleshooting

### Bot not starting:
```bash
docker compose logs xlm-bot  # check for errors
```
Common: secrets/config.json missing or invalid format

### Claude Opus not working (AI says "disabled"):
- Verify ANTHROPIC_API_KEY is in .env
- Check: docker compose exec xlm-bot env | grep ANTHROPIC
- Test: docker compose exec xlm-bot claude -p "say hello"

### Dashboard not accessible:
- Check Oracle VCN security list has port 8502 open
- Check Ubuntu firewall: sudo ufw status

### Out of disk space (50GB fills up with logs):
```bash
# Rotate old logs
docker compose exec xlm-bot sh -c "ls -lh logs/"
# Truncate large files
docker compose exec xlm-bot sh -c "truncate -s 5M logs/decisions.jsonl"
```

## Cost Notes
- Ampere A1 VM: FREE (4 OCPU/24GB per account)
- Outbound data: 10TB/month free
- Static IP: 1 free when attached to a running instance
- Total expected cost: $0/month

If Oracle shows "Out of capacity" on sign-up, try:
1. Different region (us-phoenix-1, us-ashburn-1, ap-osaka-1)
2. Wait and try again (capacity frees up)
3. Fallback: Google Cloud e2-micro is also free (but only 1GB RAM, no ARM)
