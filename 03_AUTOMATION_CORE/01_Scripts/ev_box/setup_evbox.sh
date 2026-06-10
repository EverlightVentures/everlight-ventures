#!/usr/bin/env bash
# setup_evbox.sh -- runs INSIDE the new ev-box proot-distro rootfs.
# Idempotent. Run once. Re-runnable safely.
#
# How to run (after `proot-distro install ubuntu --override-alias ev-box` from native Termux):
#   proot-distro login ev-box -- bash /sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ev_box/setup_evbox.sh
#
# After it finishes, you re-enter ev-box with:
#   proot-distro login ev-box
# Or from any tailnet device:
#   ssh ev-box
set -euo pipefail

LOG=/var/log/setup_evbox.log
mkdir -p /var/log
exec > >(tee -a "$LOG") 2>&1

echo "================================================================="
echo "  ev-box setup -- $(date)"
echo "================================================================="

# Detect we're actually inside ev-box rootfs
if [[ ! -f /etc/os-release ]] || ! grep -qi ubuntu /etc/os-release; then
  echo "FAIL: this script must run inside the ev-box Ubuntu proot." >&2
  exit 1
fi

WORKSPACE_HOST=/sdcard/AA_MY_DRIVE
WORKSPACE_LOCAL=/root/AA_MY_DRIVE

# ---------- 1. base packages ----------
echo ""
echo ">>> 1. Installing base packages..."
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  zsh tmux git curl wget jq python3 python3-pip python3-venv rclone \
  openssh-server fastfetch htop btop ripgrep fd-find fzf \
  net-tools dnsutils whois nmap traceroute mtr-tiny \
  ca-certificates gnupg lsb-release iproute2 \
  || { echo "WARN: some packages failed -- continuing"; }

# ---------- 2. ssh server on port 2222 ----------
echo ""
echo ">>> 2. Configuring sshd on port 2222..."
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-evbox.conf <<'SSHCFG'
Port 2222
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
X11Forwarding no
PrintMotd no
ClientAliveInterval 60
ClientAliveCountMax 3
SSHCFG

# Authorize the github_deploy key (same as host phone uses)
mkdir -p /root/.ssh
chmod 700 /root/.ssh
if [[ -f /sdcard/.ssh/github_deploy.pub ]]; then
  cp /sdcard/.ssh/github_deploy.pub /root/.ssh/authorized_keys
elif [[ -f /root/.ssh/authorized_keys ]]; then
  echo "  authorized_keys already present, leaving alone"
else
  # fall back: generate a new keypair, print public to log + copy to host workspace
  ssh-keygen -t ed25519 -f /root/.ssh/evbox_id -N '' -C 'evbox-self'
  cp /root/.ssh/evbox_id.pub /root/.ssh/authorized_keys
  cp /root/.ssh/evbox_id.pub "$WORKSPACE_HOST/03_AUTOMATION_CORE/01_Scripts/ev_box/evbox_id.pub" 2>/dev/null || true
  echo "  generated new evbox_id keypair, public copied to workspace"
fi
chmod 600 /root/.ssh/authorized_keys

# Generate host keys if missing
ssh-keygen -A -q

# ---------- 3. Tailscale (userspace networking) ----------
echo ""
echo ">>> 3. Installing Tailscale userspace..."
if ! command -v tailscale >/dev/null 2>&1; then
  TS_VERSION=$(curl -s https://pkgs.tailscale.com/stable/ | grep -oE 'tailscale_[0-9.]+_arm64.tgz' | head -1)
  if [[ -z "$TS_VERSION" ]]; then
    TS_VERSION="tailscale_1.78.1_arm64.tgz"  # fallback
  fi
  cd /tmp
  curl -fsSL "https://pkgs.tailscale.com/stable/$TS_VERSION" -o tailscale.tgz
  tar xzf tailscale.tgz
  TS_DIR=$(tar tzf tailscale.tgz | head -1 | tr -d /)
  cp "$TS_DIR/tailscale" "$TS_DIR/tailscaled" /usr/local/bin/
  rm -rf tailscale.tgz "$TS_DIR"
  echo "  installed: $(tailscale version | head -1)"
fi

# ---------- 4. Mirror ~/.claude + workspace from host ----------
echo ""
echo ">>> 4. Mirroring .claude/ + workspace from /sdcard..."
# /sdcard is bind-mounted by proot-distro by default
if [[ -d /sdcard/AA_MY_DRIVE ]]; then
  # Symlink the workspace (cheaper than copying and stays auto-synced)
  if [[ ! -L "$WORKSPACE_LOCAL" ]]; then
    ln -sfn /sdcard/AA_MY_DRIVE "$WORKSPACE_LOCAL"
  fi
  echo "  workspace -> $WORKSPACE_LOCAL (symlink to /sdcard/AA_MY_DRIVE)"
fi

# Mirror .claude (real copy, not symlink, so ev-box can have its own state)
if [[ -d /root/.claude ]]; then
  echo "  .claude/ already present"
else
  if [[ -d /sdcard/.claude_seed ]]; then
    cp -a /sdcard/.claude_seed /root/.claude
  else
    # First-time: copy from the host's /root/.claude via /sdcard bridge
    HOST_CLAUDE="/sdcard/AA_MY_DRIVE/.claude_seed"
    if [[ ! -d "$HOST_CLAUDE" ]] && [[ -d /root/.claude ]]; then
      :  # already in place inside ev-box (happens if user ran setup twice)
    else
      mkdir -p /root/.claude
      echo "  WARN: no .claude seed found; you can copy ~/.claude from host later"
    fi
  fi
fi

# ---------- 5. Claude CLI + AI workers ----------
echo ""
echo ">>> 5. Installing Claude CLI..."
if ! command -v claude >/dev/null 2>&1; then
  curl -fsSL https://claude.ai/install.sh | bash || echo "  Claude CLI install incomplete -- retry later"
fi

# pip-install AI worker requirements if available from workspace
REQ="$WORKSPACE_LOCAL/03_AUTOMATION_CORE/01_Scripts/ai_workers/requirements.txt"
if [[ -f "$REQ" ]]; then
  pip3 install --break-system-packages -q -r "$REQ" 2>&1 | tail -3 || echo "  some pip installs failed"
fi

# ---------- 6. DFIR-lite subset (proot-compatible only) ----------
echo ""
echo ">>> 6. Installing proot-compatible DFIR-lite (osquery + Medusa + Velociraptor)..."
mkdir -p /opt/dfir-lite

# Velociraptor agent (single binary)
if [[ ! -f /opt/dfir-lite/velociraptor ]]; then
  VELO_URL=$(curl -s https://api.github.com/repos/Velocidex/velociraptor/releases/latest 2>/dev/null | \
    grep "browser_download_url.*linux-arm64" | head -1 | cut -d'"' -f4)
  if [[ -n "$VELO_URL" ]]; then
    curl -fsSL "$VELO_URL" -o /opt/dfir-lite/velociraptor
    chmod +x /opt/dfir-lite/velociraptor
  fi
fi

# Medusa SAST (pip, userspace)
pip3 install --break-system-packages -q medusa-sast 2>/dev/null || \
  pip3 install --break-system-packages -q git+https://github.com/Pantheon-Security/medusa.git 2>/dev/null || \
  echo "  Medusa not installed (optional)"

# osquery
if ! command -v osqueryi >/dev/null 2>&1; then
  curl -fsSL https://pkg.osquery.io/deb/pubkey.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/osquery.gpg 2>/dev/null
  echo 'deb [arch=arm64] https://pkg.osquery.io/deb deb main' > /etc/apt/sources.list.d/osquery.list
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y osquery 2>&1 | tail -2 || echo "  osquery install failed (non-fatal)"
fi

# ---------- 7. fastfetch banner for ev-box ----------
echo ""
echo ">>> 7. Configuring fastfetch banner for ev-box..."
mkdir -p /root/.config/fastfetch
cat > /root/.config/fastfetch/config.jsonc <<'FF'
{
  "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
  "logo": { "type": "auto", "padding": { "top": 1, "right": 3 } },
  "display": { "separator": "  ", "color": { "keys": "33", "title": "33", "output": "37" } },
  "modules": [
    { "type": "title", "format": "{user-name}@{host-name}  ::  EV-BOX :: PERSONAL OPS" },
    "separator", "os", "kernel", "uptime", "shell", "memory", "disk",
    { "type": "custom", "format": "" },
    { "type": "custom", "format": "[1;33m  EV-BOX READY[0m" },
    { "type": "custom", "format": "[33m  ----------------------------------------------------[0m" },
    { "type": "custom", "format": "  [33mssh[0m   ssh ev-box        [37m# tailnet, port 2222[0m" },
    { "type": "custom", "format": "  [33mtail[0m  tail -f /var/log/setup_evbox.log" },
    { "type": "custom", "format": "  [33mwork[0m  cd /root/AA_MY_DRIVE  [37m# symlinked to host /sdcard/AA_MY_DRIVE[0m" },
    "break", "colors"
  ]
}
FF

# Trimmed zshrc inside ev-box
cat > /root/.zshrc <<'ZRC'
export EL_HOME=/root/AA_MY_DRIVE
export PATH=$HOME/.local/bin:$PATH
alias ll='ls -lah'
alias cdw='cd $EL_HOME'
alias dev='cd $EL_HOME/06_DEVELOPMENT'
alias auto='cd $EL_HOME/03_AUTOMATION_CORE'
alias sshd-start='/usr/sbin/sshd -D &'
alias ts-up='/usr/local/sbin/tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
sleep 2
/usr/local/bin/tailscale up --hostname=ev-box --ssh'
[[ -f /usr/bin/fastfetch && -z "$EV_FETCH_SHOWN" ]] && { fastfetch; export EV_FETCH_SHOWN=1; }
ZRC

# Make zsh default
chsh -s /usr/bin/zsh root 2>/dev/null || true

# ---------- 8. Final summary ----------
echo ""
echo "================================================================="
echo "  ev-box setup complete -- $(date)"
echo "================================================================="
echo ""
echo "What's next:"
echo ""
echo "  1. Start sshd inside ev-box:"
echo "     /usr/sbin/sshd -D &"
echo ""
echo "  2. Start Tailscale (userspace mode, no /dev/net/tun needed):"
echo "     mkdir -p /var/lib/tailscale /var/run/tailscale"
echo "     /usr/local/sbin/tailscaled --tun=userspace-networking \\"
echo "       --state=/var/lib/tailscale/tailscaled.state \\"
echo "       --socket=/var/run/tailscale/tailscaled.sock &"
echo "     sleep 2"
echo "     /usr/local/bin/tailscale up --hostname=ev-box --ssh --accept-routes"
echo ""
echo "  3. Click the auth URL Tailscale prints. ev-box will appear on your tailnet."
echo ""
echo "  4. From any other tailnet device:  ssh ev-box"
echo ""
echo "Logs:  $LOG"
