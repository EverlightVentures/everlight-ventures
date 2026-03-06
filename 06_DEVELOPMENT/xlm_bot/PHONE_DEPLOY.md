# XLM Bot - Oracle Cloud Phone Deploy Guide
# Phone-first, Termux-native. All commands run from your Android terminal.

## Overview
- Instance: VM.Standard.A1.Flex (ARM64, free tier - always free)
- Shape: 2 OCPU, 12 GB RAM, 50 GB boot
- OS: Ubuntu 22.04 (Canonical, aarch64)
- Cost: $0/month from free tier, will NOT burn $300 trial credits
- Docker: linux/arm64 (already configured in docker-compose.yml)

---

## PART 1 - Create the Oracle VM (browser on phone)

1. Go to **cloud.oracle.com** -> sign in
2. Compute -> Instances -> **Create Instance**
3. Fill in:
   - **Name**: `xlm-bot`
   - **Image**: Ubuntu 22.04 (Canonical)
   - **Shape**: Click "Change Shape" -> **Ampere** -> VM.Standard.A1.Flex
     - OCPU: **2**
     - Memory: **12 GB**
4. **Networking**: Create new VCN (default settings) -> **Assign public IPv4: YES**
5. **SSH Keys**: Choose "Paste public keys" - paste your key (see Part 2 first)
6. **Boot Volume**: 50 GB
7. Click **Create** - takes 2-3 min to reach RUNNING state
8. Copy the **Public IP Address** from the instance details page

---

## PART 2 - SSH Key Setup in Termux

Run these once on your phone to generate your SSH key:

```bash
# Install openssh in Termux if not already installed
pkg install openssh rsync -y

# Generate key (press Enter for all prompts)
ssh-keygen -t ed25519 -f ~/.ssh/oracle_key -N ""

# Display your PUBLIC key -- copy this for Oracle's "Paste public keys" field
cat ~/.ssh/oracle_key.pub
```

Save your VM's IP:
```bash
# Replace with your actual IP from Oracle console
echo "129.XXX.XXX.XXX" > ~/.oracle_vm_ip
VM=$(cat ~/.oracle_vm_ip)
```

Test SSH access (Ubuntu VMs use `ubuntu` user):
```bash
ssh -i ~/.ssh/oracle_key ubuntu@$VM
# Type 'yes' to accept fingerprint, then Ctrl+D to exit
```

---

## PART 3 - Run Cloud Setup on VM

From Termux, copy the setup script then run it on the VM:

```bash
VM=$(cat ~/.oracle_vm_ip)

# Copy bootstrap script to VM
scp -i ~/.ssh/oracle_key \
    /mnt/sdcard/AA_MY_DRIVE/xlm_bot/cloud-setup.sh \
    ubuntu@$VM:~/

# Run it
ssh -i ~/.ssh/oracle_key ubuntu@$VM "bash cloud-setup.sh"
```

**Important**: Log out and back in after cloud-setup.sh runs so Docker group takes effect:
```bash
exit
ssh -i ~/.ssh/oracle_key ubuntu@$VM
docker ps  # should work without sudo now
```

---

## PART 4 - Open Firewall Port 8502 (Dashboard)

In Oracle Console (browser):
1. Networking -> Virtual Cloud Networks -> your VCN
2. Security Lists -> Default Security List
3. **Add Ingress Rule**:
   - Source CIDR: `0.0.0.0/0`
   - Protocol: TCP
   - Destination Port: `8502`
   - Click **Add**

Also run on the VM (Oracle Ubuntu blocks by default via iptables):
```bash
ssh -i ~/.ssh/oracle_key ubuntu@$VM
sudo iptables -I INPUT -p tcp --dport 8502 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
exit
```

---

## PART 5 - Deploy Bot Code + Secrets

From Termux on your phone (NOT inside the VM):

```bash
VM=$(cat ~/.oracle_vm_ip)
cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot

# Full deploy: uploads code, uploads secrets, builds Docker, starts bot
bash deploy.sh $VM ~/.ssh/oracle_key ubuntu
```

The deploy.sh script will:
- Upload all bot code via rsync (excludes secrets/data/logs)
- Auto-find and upload secrets/config.json
- Build the Docker image (5-10 min first time, ARM64 native)
- Start the bot with `docker compose up -d`

**If secrets are not auto-found**, upload manually:
```bash
VM=$(cat ~/.oracle_vm_ip)
scp -i ~/.ssh/oracle_key \
    /mnt/sdcard/AA_MY_DRIVE/xlm_bot/secrets/config.json \
    ubuntu@$VM:~/xlm-bot/secrets/config.json
```

---

## PART 6 - Set API Keys in .env (for AI exec mode)

SSH into VM and edit .env:
```bash
VM=$(cat ~/.oracle_vm_ip)
ssh -i ~/.ssh/oracle_key ubuntu@$VM "cd ~/xlm-bot && nano .env"
```

Add your keys:
```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/URL
```

Then restart:
```bash
ssh -i ~/.ssh/oracle_key ubuntu@$VM "cd ~/xlm-bot && docker compose up -d"
```

---

## PART 7 - Verify It's Running

```bash
VM=$(cat ~/.oracle_vm_ip)
ssh -i ~/.ssh/oracle_key ubuntu@$VM

# Container status (should show "healthy" after ~2 min)
docker ps

# Live log stream
docker compose -f ~/xlm-bot/docker-compose.yml logs -f --tail=50 xlm-bot

# Check heartbeat freshness
docker compose exec xlm-bot python3 -c "
import time; from pathlib import Path
hb = Path('data/.heartbeat')
age = time.time() - float(hb.read_text())
print(f'Heartbeat: {age:.0f}s old')
"
```

Open dashboard in phone browser: `http://YOUR_VM_IP:8502`

---

## PART 8 - Ongoing Management from Phone

Add this alias to Termux `~/.bashrc`:
```bash
echo 'alias xlpcloud="ssh -i ~/.ssh/oracle_key ubuntu@$(cat ~/.oracle_vm_ip)"' >> ~/.bashrc
source ~/.bashrc
```

Quick commands once SSH'd in:
```bash
docker compose logs -f                  # live logs
docker compose restart xlm-bot          # restart container
docker compose down                     # stop everything
docker compose up -d --build            # rebuild + restart
```

Update bot after local code changes (from Termux):
```bash
cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot
bash deploy.sh $(cat ~/.oracle_vm_ip) ~/.ssh/oracle_key ubuntu
```

Emergency stop from phone:
```bash
ssh -i ~/.ssh/oracle_key ubuntu@$(cat ~/.oracle_vm_ip) \
    "docker compose -f ~/xlm-bot/docker-compose.yml stop"
```

---

## Secrets: Where is config.json?

The Coinbase CDP API key lives at:
- **Phone local**: `/mnt/sdcard/AA_MY_DRIVE/xlm_bot/secrets/config.json` (ready to use)
- **Original CDP format**: `/mnt/sdcard/Download/cdp_api_key.json`

If you ever need to regenerate secrets/config.json from the raw CDP key:
```bash
cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot
bash secrets/prep_secrets.sh
```

---

## Troubleshooting

**Container crashes immediately:**
```bash
docker compose logs xlm-bot | tail -30
# Usually: missing secrets/config.json or bad .env
```

**Dashboard not loading at port 8502:**
- Check Oracle VCN security list has port 8502 open (browser console)
- Check iptables on VM: `sudo iptables -L INPUT | grep 8502`

**Bot won't trade (no margin):**
- Intraday window is 5 AM - 1 PM PT only at current equity level
- Check decisions log: `docker compose exec xlm-bot tail -5 logs/decisions.jsonl`

**Claude AI exec mode not working:**
- Verify `ANTHROPIC_API_KEY` in .env: `docker compose exec xlm-bot env | grep ANTHROPIC`
- Test: `docker compose exec xlm-bot claude -p "say hello"`

**Disk filling up (50 GB logs):**
```bash
docker compose exec xlm-bot sh -c "du -sh logs/*"
docker compose exec xlm-bot sh -c "truncate -s 5M logs/decisions.jsonl"
```

---

## Cost Summary

| Resource         | Free Tier Limit      | Bot Usage  |
|-----------------|----------------------|------------|
| A1 OCPU         | 4 total/account      | 2          |
| RAM             | 24 GB total/account  | 12 GB      |
| Boot volume     | 200 GB total/account | 50 GB      |
| Outbound data   | 10 TB/month          | ~1 GB/mo   |
| Static IP       | 1 free (attached)    | 1          |
| Monthly cost    |                      | **$0**     |

$300 trial credits are preserved for scaling up to a larger paid instance later.
