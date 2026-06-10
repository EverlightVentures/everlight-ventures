#!/usr/bin/env bash
# ev-box provisioner -- runs from the PHONE, SSHes into the new VM, sets it up.
# Idempotent. Auto by default. Pass --interactive to be prompted.
#
# Usage:
#   bash provision.sh <public-ip-of-ev-box>
#   bash provision.sh <public-ip-of-ev-box> --interactive
#
# Prereqs:
#   - VM created from cloud_init.yaml in OCI Console
#   - SSH key /root/.ssh/github_deploy (already present on phone)
#   - cloud-init flag /var/lib/cloud/ev-box.ready exists on the VM
set -euo pipefail

EV_HOST="${1:-}"
MODE="auto"
[[ "${2:-}" == "--interactive" ]] && MODE="interactive"

if [[ -z "$EV_HOST" ]]; then
  echo "ERROR: pass the public IP of ev-box as arg 1" >&2
  echo "  Usage: bash provision.sh 1.2.3.4" >&2
  exit 2
fi

SSH_KEY="/root/.ssh/github_deploy"
SSH="ssh -i $SSH_KEY -p 2222 -o StrictHostKeyChecking=accept-new ubuntu@$EV_HOST"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
DEPLOY_LOG="$WORKSPACE/_logs/ev_box_provision_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$DEPLOY_LOG")"

# ---------- helpers ----------
log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$DEPLOY_LOG"; }
die() { log "FATAL: $*"; exit 1; }
slack_post() {
  # Branded Slack post; degrades silently off-Oracle
  python3 -c "
from content_tools.branded_slack import post_branded_slack
post_branded_slack(channel='#deploy-log', category='ops',
                   title='ev-box provision: $1', body='''$2''')
" 2>>"$DEPLOY_LOG" || log "  (slack post skipped -- not on Oracle)"
}

# ---------- 0. wait for cloud-init ----------
log "Waiting for cloud-init to finish on $EV_HOST..."
for i in $(seq 1 60); do
  if $SSH 'test -f /var/lib/cloud/ev-box.ready' 2>/dev/null; then
    log "  cloud-init ready"
    break
  fi
  sleep 10
  [[ $i -eq 60 ]] && die "cloud-init did not finish in 10 min"
done

# ---------- 1. Tailscale up ----------
log "Bringing Tailscale up (auth URL will be posted to Slack)..."
TS_URL=$($SSH "sudo tailscale up --ssh --accept-routes --hostname=ev-box --reset 2>&1 | grep -oE 'https://login.tailscale.com[^ ]+' | head -1" || true)
if [[ -n "$TS_URL" ]]; then
  log "  AUTH NEEDED: $TS_URL"
  slack_post "Tailscale auth required" "Open this URL on any device to authorize ev-box:\n$TS_URL"
  log "  Waiting for tailnet auth (max 10 min)..."
  for i in $(seq 1 60); do
    if $SSH 'tailscale status | head -1 | grep -qE "^[0-9]"' 2>/dev/null; then
      log "  Tailscale authorized"
      break
    fi
    sleep 10
    [[ $i -eq 60 ]] && die "tailscale auth timeout"
  done
else
  log "  Tailscale already authorized"
fi
TS_IP=$($SSH "tailscale ip -4 | head -1")
log "  ev-box tailnet IP: $TS_IP"

# ---------- 2. Add ev-box to phone ssh config ----------
log "Adding ev-box + ev-box-public to phone ~/.ssh/config..."
SSH_CFG="$HOME/.ssh/config"
touch "$SSH_CFG"
if ! grep -q "^Host ev-box$" "$SSH_CFG"; then
  cat >> "$SSH_CFG" <<EOF

# ev-box -- personal ops VM (added $(date))
Host ev-box
  HostName $TS_IP
  User ubuntu
  IdentityFile $SSH_KEY
  ServerAliveInterval 30
Host ev-box-public
  HostName $EV_HOST
  Port 2222
  User ubuntu
  IdentityFile $SSH_KEY
  ServerAliveInterval 30
EOF
  log "  added to $SSH_CFG"
else
  log "  ev-box block already in $SSH_CFG -- skipping"
fi

# ---------- 3. zsh + starship + dotfiles ----------
log "Installing zsh as default shell + starship..."
$SSH 'sudo chsh -s "$(which zsh)" ubuntu' || log "  (chsh already done)"
$SSH 'curl -fsSL https://starship.rs/install.sh | sudo sh -s -- --yes' >>"$DEPLOY_LOG" 2>&1 || log "  starship install failed (continuing)"

log "Copying starship + zshrc base..."
[[ -f /root/.config/starship.toml ]] && \
  rsync -az -e "ssh -i $SSH_KEY -p 2222" /root/.config/starship.toml ubuntu@$EV_HOST:/home/ubuntu/.config/starship.toml || true
# Trimmed zshrc -- references /home/ubuntu/AA_MY_DRIVE not phone sdcard path
$SSH 'cat > /home/ubuntu/.zshrc' <<'ZSHRC'
export EL_HOME="/home/ubuntu/AA_MY_DRIVE"
export PATH="$HOME/.local/bin:$PATH"
alias cdw="cd $EL_HOME"
alias ev="cd $EL_HOME/01_BUSINESSES/Everlight_Ventures"
alias dev="cd $EL_HOME/06_DEVELOPMENT"
alias auto="cd $EL_HOME/03_AUTOMATION_CORE"
alias ll="ls -lah"
alias ide="tmux new-session -s everlight 2>/dev/null || tmux attach -t everlight"
[[ -f /usr/bin/fastfetch ]] && [[ -z "$EV_FETCH_SHOWN" ]] && { fastfetch; export EV_FETCH_SHOWN=1; }
eval "$(starship init zsh)"
ZSHRC

# ---------- 4. AI CLIs (Claude is interactive-login; rest are pip) ----------
log "Installing AI CLIs..."
$SSH 'curl -fsSL https://claude.ai/install.sh | bash' >>"$DEPLOY_LOG" 2>&1 || log "  Claude install needs manual login -- run 'claude login' over SSH"
# Codex / Gemini / Perplexity -- pip from existing requirements
if [[ -f "$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/ai_workers/requirements.txt" ]]; then
  rsync -az -e "ssh -i $SSH_KEY -p 2222" \
    "$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/ai_workers/requirements.txt" \
    ubuntu@$EV_HOST:/tmp/ai_workers_req.txt
  $SSH 'pip3 install --user -r /tmp/ai_workers_req.txt' >>"$DEPLOY_LOG" 2>&1 || log "  some AI CLIs failed (non-fatal)"
fi

# ---------- 5. .claude/ rsync ----------
log "Syncing ~/.claude/ agents + skills + commands to ev-box..."
rsync -az --delete -e "ssh -i $SSH_KEY -p 2222" \
  --exclude 'projects/' --exclude 'shell-snapshots/' --exclude '*.log' \
  --max-size=50M \
  /root/.claude/ ubuntu@$EV_HOST:/home/ubuntu/.claude/

# ---------- 6. Workspace mirror ----------
log "Rclone-syncing AA_MY_DRIVE workspace (one-way phone->ev-box)..."
rclone sync "$WORKSPACE" "ev-box:/home/ubuntu/AA_MY_DRIVE" \
  --sftp-host "$TS_IP" --sftp-user ubuntu --sftp-key-file "$SSH_KEY" \
  --exclude '08_BACKUPS/**' --exclude '04_MEDIA_LIBRARY/**' \
  --exclude '_logs/**' --exclude '*.log' --exclude '.git/**' \
  --transfers 4 --progress 2>>"$DEPLOY_LOG" || log "  rclone sync had errors -- check $DEPLOY_LOG"

# ---------- 7. Symlinks for muscle memory ----------
log "Creating convenience symlinks..."
$SSH 'ln -sfn /home/ubuntu/AA_MY_DRIVE/03_AUTOMATION_CORE /home/ubuntu/auto
      ln -sfn /home/ubuntu/AA_MY_DRIVE/06_DEVELOPMENT /home/ubuntu/dev
      ln -sfn /home/ubuntu/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures /home/ubuntu/ev'

# ---------- 8. DFIR-lite + Claude layer ----------
log "Installing DFIR-lite security layer..."
rsync -az -e "ssh -i $SSH_KEY -p 2222" "$SCRIPT_DIR/install_dfir_lite.sh" ubuntu@$EV_HOST:/tmp/
$SSH 'bash /tmp/install_dfir_lite.sh' >>"$DEPLOY_LOG" 2>&1 || log "  DFIR-lite install had errors -- check $DEPLOY_LOG"

log "Installing Claude Code optimization layer..."
rsync -az -e "ssh -i $SSH_KEY -p 2222" "$SCRIPT_DIR/install_claude_layer.sh" ubuntu@$EV_HOST:/tmp/
$SSH 'bash /tmp/install_claude_layer.sh' >>"$DEPLOY_LOG" 2>&1 || log "  Claude layer install had errors -- check $DEPLOY_LOG"

# ---------- 9. Final report ----------
log "Provisioning complete."
log "  Tailnet:     ssh ev-box"
log "  Public:      ssh ev-box-public"
log "  Full log:    $DEPLOY_LOG"
slack_post "ev-box online" "Tailnet: $TS_IP\nPublic: $EV_HOST:2222\nLog: $DEPLOY_LOG"

# Trigger next phase: cron migration
log ""
log "Next: bash $SCRIPT_DIR/migrate_crons.sh --auto"
