#!/bin/bash
# install_oracle_watchdog.sh
# Run once on phone (Termux/PRoot) to set up:
#   1. Phone-side OCI watchdog cron (every 5 min)
#   2. SSH tunnel persistence cron (every 2 min, keeps dashboard accessible)
#   3. Pushes sshd tuning to Oracle VM to fix banner exchange server-side
#
# Usage: bash /mnt/sdcard/AA_MY_DRIVE/xlm_bot/install_oracle_watchdog.sh

set -euo pipefail

WATCHDOG="/mnt/sdcard/AA_MY_DRIVE/xlm_bot/oracle_watchdog.sh"
TUNNEL_SCRIPT="/mnt/sdcard/AA_MY_DRIVE/xlm_bot/oracle_tunnel.sh"
ORACLE_IP="163.192.19.196"
ORACLE_USER="opc"
SSH_KEY="/root/.ssh/oracle_key.pem"

echo "== Oracle Watchdog Installer =="

# 1. Verify OCI CLI works
echo "[1/4] Testing OCI CLI..."
oci compute instance get \
    --instance-id "ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq" \
    --query 'data."lifecycle-state"' \
    --raw-output
echo "OCI CLI OK"

# 2. Write tunnel persistence script
echo "[2/4] Writing tunnel script..."
cat > "$TUNNEL_SCRIPT" << 'TUNNEL'
#!/bin/bash
# oracle_tunnel.sh -- keeps dashboard tunnel alive
# Cron: */2 * * * * /mnt/sdcard/AA_MY_DRIVE/xlm_bot/oracle_tunnel.sh

ORACLE_IP="163.192.19.196"
SSH_KEY="/root/.ssh/oracle_key.pem"
PIDFILE="/tmp/oracle_tunnel.pid"
LOGFILE="/tmp/oracle_tunnel.log"

ts() { date '+%H:%M:%S'; }

# Check if tunnel is alive
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        # Verify the port is actually forwarded
        if nc -z -w 2 127.0.0.1 8502 2>/dev/null; then
            echo "[$(ts)] Tunnel alive (pid=$PID, port 8502 OK)" >> "$LOGFILE"
            exit 0
        fi
        # PID alive but port not forwarded -- kill stale
        kill "$PID" 2>/dev/null
    fi
fi

# Start fresh tunnel
echo "[$(ts)] Starting SSH tunnel to $ORACLE_IP:8502..." >> "$LOGFILE"
ssh \
    -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o BatchMode=yes \
    -o ConnectTimeout=15 \
    -o GSSAPIAuthentication=no \
    -o AddressFamily=inet \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=4 \
    -o ExitOnForwardFailure=yes \
    -o Ciphers=aes128-ctr,aes256-ctr \
    -o KexAlgorithms=curve25519-sha256,ecdh-sha2-nistp256 \
    -N \
    -L 8502:127.0.0.1:8502 \
    "opc@$ORACLE_IP" \
    >> "$LOGFILE" 2>&1 &

echo $! > "$PIDFILE"
echo "[$(ts)] Tunnel started (pid=$(cat $PIDFILE))" >> "$LOGFILE"
TUNNEL
chmod +x "$TUNNEL_SCRIPT"
echo "Tunnel script written: $TUNNEL_SCRIPT"

# 3. Push sshd fix to Oracle VM (server-side banner fix)
echo "[3/4] Pushing sshd tuning to Oracle VM..."
ssh \
    -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=20 \
    -o GSSAPIAuthentication=no \
    -o AddressFamily=inet \
    -o Ciphers=aes128-ctr,aes256-ctr \
    -o KexAlgorithms=curve25519-sha256,ecdh-sha2-nistp256 \
    -o LogLevel=ERROR \
    "$ORACLE_USER@$ORACLE_IP" << 'REMOTE'
set -e
echo "-- Tuning sshd for fast banner exchange --"

SSHD_CONF="/etc/ssh/sshd_config.d/xlmbot.conf"
sudo tee "$SSHD_CONF" > /dev/null << 'SSHD'
# XLM bot SSH tuning -- faster banner exchange for PRoot/Termux clients
UseDNS no
GSSAPIAuthentication no
LoginGraceTime 30
MaxAuthTries 3
# Fast ciphers
Ciphers aes128-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256
# Keepalives (server -> client)
ClientAliveInterval 20
ClientAliveCountMax 6
SSHD

sudo sshd -t && echo "sshd config valid" && sudo systemctl reload sshd
echo "-- sshd tuning applied --"
REMOTE
echo "sshd tuning pushed OK"

# 4. Install cron jobs
echo "[4/4] Installing cron jobs..."

# Read existing crontab (if any)
EXISTING_CRON=$(crontab -l 2>/dev/null || true)

# Remove old oracle watchdog/tunnel lines
CLEANED=$(echo "$EXISTING_CRON" | grep -v "oracle_watchdog\|oracle_tunnel" || true)

# Add new jobs
NEW_CRON="${CLEANED}
# Oracle VM watchdog (every 5 min)
*/5 * * * * flock -xn /tmp/oracle_wd.lock $WATCHDOG >> /tmp/oracle_watchdog.log 2>&1
# Dashboard tunnel keepalive (every 2 min)
*/2 * * * * $TUNNEL_SCRIPT
"

echo "$NEW_CRON" | crontab -
echo "Cron installed:"
crontab -l | grep -E "oracle|xlm"

echo ""
echo "== Install complete =="
echo "Watchdog: $WATCHDOG (runs every 5 min)"
echo "Tunnel:   $TUNNEL_SCRIPT (runs every 2 min)"
echo "Dashboard: http://localhost:8502 (once tunnel is up)"
echo ""
echo "Test now: bash $WATCHDOG"
echo "Test SSH: ssh oracle 'echo ok'"
echo "Logs: tail -f /tmp/oracle_watchdog.log"
