#!/bin/bash
# ============================================================
# setup_arch_pc.sh
# Everlight Hive Mind bootstrap for Arch Linux (AceMagician PC)
# ============================================================
# Mirrors the phone's toolchain so the Arch box becomes a peer
# Hive node: Claude / Gemini / Codex / PPX, full workspace,
# branded comms layer, agent definitions.
#
# This script is NOT for Oracle (auto-deploy is opt-in via
# deploy_to_oracle.sh). Run it ONLY on the Arch PC.
#
# Prereqs (manual, before running):
#   1. Arch booted, you are logged in as your normal user (NOT root)
#   2. Tailscale running on Arch and joined to the same tailnet as phone
#   3. SSH keys transferred from phone via Tailscale rsync:
#        mkdir -p ~/.ssh && chmod 700 ~/.ssh
#        rsync -av root@<phone-tailnet-ip>:/root/.ssh/github_deploy ~/.ssh/
#        rsync -av root@<phone-tailnet-ip>:/root/.ssh/oracle_key.pem ~/.ssh/
#        rsync -av root@<phone-tailnet-ip>:/root/.ssh/config ~/.ssh/
#        chmod 600 ~/.ssh/github_deploy ~/.ssh/oracle_key.pem
#
# Run:
#   bash setup_arch_pc.sh
#
# Idempotent: safe to re-run.
# ============================================================

set -euo pipefail

# ============================================================
# Constants
# ============================================================
EL_HOME="${EL_HOME:-$HOME/AA_MY_DRIVE}"
REPO_URL="git@github.com:EverlightVentures/everlight-ventures.git"
PHONE_TAILNET_IP="${PHONE_TAILNET_IP:-100.112.180.29}"
LOG_FILE="$HOME/.cache/setup_arch_pc.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Everlight gold theme (no em-dashes per Everlight standard)
GOLD='\033[38;5;214m'
GREEN='\033[0;32m'
RED='\033[0;31m'
DIM='\033[2m'
RESET='\033[0m'

log()  { printf "${GOLD}[ev]${RESET}  %s\n" "$*" | tee -a "$LOG_FILE" >&2; }
ok()   { printf "${GREEN}[ok]${RESET}  %s\n" "$*" | tee -a "$LOG_FILE" >&2; }
err()  { printf "${RED}[err]${RESET} %s\n" "$*" | tee -a "$LOG_FILE" >&2; }
note() { printf "${DIM}      %s${RESET}\n" "$*" | tee -a "$LOG_FILE" >&2; }

# ============================================================
# Layer 0 : Preflight
# ============================================================
preflight() {
  log "Preflight checks"

  if [ ! -f /etc/arch-release ]; then
    err "This script targets Arch Linux. /etc/arch-release not found."
    err "If you're on Manjaro / EndeavourOS / CachyOS, comment out this check and proceed."
    exit 1
  fi

  if [ "$(id -u)" = 0 ]; then
    err "Don't run as root. Use your normal user; sudo is invoked where needed."
    exit 1
  fi

  if ! ping -c 1 -W 3 1.1.1.1 >/dev/null 2>&1; then
    err "No internet connectivity"
    exit 1
  fi

  if ! sudo -n true 2>/dev/null; then
    log "You'll be prompted for sudo password during pacman steps"
  fi

  ok "Arch detected, non-root user, network up"
}

# ============================================================
# Layer 1 : Pacman dependencies
# ============================================================
install_pacman_deps() {
  log "Installing system packages"
  local pkgs=(
    git openssh rsync curl wget jq
    python python-pip python-virtualenv
    nodejs npm
    base-devel
    tailscale
  )
  sudo pacman -Sy --needed --noconfirm "${pkgs[@]}"
  ok "System packages installed"
}

# ============================================================
# Layer 2 : npm user-prefix (avoid sudo for global installs)
# ============================================================
setup_npm_userprefix() {
  log "Configuring npm user prefix (avoid sudo for globals)"
  mkdir -p "$HOME/.npm-global"
  npm config set prefix "$HOME/.npm-global"
  export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"
  ok "npm globals will install to ~/.npm-global/bin"
}

# ============================================================
# Layer 3 : Clone workspace
# ============================================================
clone_workspace() {
  if [ -d "$EL_HOME/.git" ]; then
    log "Workspace already present at $EL_HOME, fetching latest"
    git -C "$EL_HOME" fetch --all 2>&1 | tee -a "$LOG_FILE" >&2 || true
    git -C "$EL_HOME" pull --ff-only 2>&1 | tee -a "$LOG_FILE" >&2 \
      || note "(pull skipped, you may have local changes)"
  else
    log "Cloning workspace to $EL_HOME"
    if ! git clone "$REPO_URL" "$EL_HOME" 2>&1 | tee -a "$LOG_FILE" >&2; then
      err "Clone failed. Did you set up the SSH key?"
      err "  Verify: ssh -T git@github.com"
      err "  Should output: 'Hi EverlightVentures! ...'"
      exit 1
    fi
  fi
  ok "Workspace at $EL_HOME ($(du -sh "$EL_HOME" 2>/dev/null | cut -f1))"
}

# ============================================================
# Layer 4 : AI CLIs
# ============================================================
install_ai_clis() {
  log "Installing AI CLIs"

  # ---- Claude Code ----
  if ! command -v claude >/dev/null 2>&1; then
    log "Installing Claude Code (official curl installer)"
    if curl -fsSL https://claude.ai/install.sh | bash; then
      ok "Claude Code installed"
    else
      log "Curl install failed, trying npm fallback"
      npm install -g @anthropic-ai/claude-code \
        || err "Claude Code install failed; install manually later"
    fi
  else
    ok "claude already at $(command -v claude)"
  fi

  # ---- Gemini CLI ----
  if ! command -v gemini >/dev/null 2>&1; then
    log "Installing Gemini CLI"
    npm install -g @google/gemini-cli 2>&1 | tee -a "$LOG_FILE" >&2 \
      || err "Gemini CLI install failed; check $LOG_FILE"
  else
    ok "gemini already at $(command -v gemini)"
  fi

  # ---- Codex CLI ----
  if ! command -v codex >/dev/null 2>&1; then
    log "Installing Codex CLI"
    npm install -g @openai/codex 2>&1 | tee -a "$LOG_FILE" >&2 \
      || err "Codex CLI install failed; check $LOG_FILE"
  else
    ok "codex already at $(command -v codex)"
  fi

  # ---- Perplexity wrapper (lives in repo) ----
  local ppx_script="$EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/ppx_terminal.py"
  if [ -f "$ppx_script" ]; then
    ok "ppx wrapper found in repo (alias added in shell-env step)"
  else
    err "ppx_terminal.py not found at $ppx_script"
  fi
}

# ============================================================
# Layer 5 : Global ~/.claude config (selective copy from phone)
# ============================================================
bootstrap_claude_global() {
  log "Bootstrapping global ~/.claude config"
  mkdir -p "$HOME/.claude/agents"

  # Project-level .claude/ ships with the repo (94 agents, hooks, modes,
  # commands, skills, memory) at $EL_HOME/.claude/. That's the heavy load.
  # Global ~/.claude/ only needs CLAUDE.md + settings.json + global agents.

  if ping -c 1 -W 2 "$PHONE_TAILNET_IP" >/dev/null 2>&1; then
    log "Phone reachable at $PHONE_TAILNET_IP, syncing global Claude config"
    # Pull only the durable parts. NEVER copy:
    #   sessions/, history.jsonl, telemetry/, statsig/, cache/,
    #   paste-cache/, security_warnings_state_*.json
    # Those are per-machine ephemeral state.
    rsync -av --ignore-existing \
      "root@${PHONE_TAILNET_IP}:/root/.claude/CLAUDE.md" \
      "root@${PHONE_TAILNET_IP}:/root/.claude/settings.json" \
      "$HOME/.claude/" 2>&1 | tee -a "$LOG_FILE" >&2 \
      || note "(rsync from phone failed; copy ~/.claude/{CLAUDE.md,settings.json} manually)"

    # Pull global agents directory (small)
    rsync -av --ignore-existing \
      "root@${PHONE_TAILNET_IP}:/root/.claude/agents/" \
      "$HOME/.claude/agents/" 2>&1 | tee -a "$LOG_FILE" >&2 \
      || true
  else
    note "Phone not reachable at $PHONE_TAILNET_IP. Skipping ~/.claude rsync."
    note "After phone is up, run:"
    note "  rsync -av root@<phone-ip>:/root/.claude/{CLAUDE.md,settings.json} ~/.claude/"
  fi

  ok "~/.claude scaffolded"
}

# ============================================================
# Layer 6 : Python venv + deps for content_tools
# ============================================================
install_python_deps() {
  log "Setting up Python venv for content_tools (branded comms layer)"

  cd "$EL_HOME"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Created .venv"
  else
    ok ".venv already exists"
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate

  pip install --upgrade pip 2>&1 | tee -a "$LOG_FILE" >&2

  # Core deps for the branded comms layer + AI delegate scripts
  pip install \
    requests \
    google-auth google-auth-oauthlib google-api-python-client \
    slack-sdk \
    anthropic openai google-generativeai \
    python-dotenv \
    rich \
    httpx \
    pyyaml \
    2>&1 | tee -a "$LOG_FILE" >&2 \
    || err "Some pip installs failed; check $LOG_FILE"

  deactivate
  ok "Python venv ready at $EL_HOME/.venv"
}

# ============================================================
# Layer 7 : Shell environment
# ============================================================
setup_shell_env() {
  log "Wiring shell environment"

  # Detect active shell
  local rc=""
  if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "$SHELL")" = "zsh" ]; then
    rc="$HOME/.zshrc"
  else
    rc="$HOME/.bashrc"
  fi
  touch "$rc"

  local marker_start="# >>> EVERLIGHT HIVE >>>"
  local marker_end="# <<< EVERLIGHT HIVE <<<"

  if grep -q "$marker_start" "$rc"; then
    ok "Hive env block already present in $rc, skipping"
    return
  fi

  cat >> "$rc" <<EOF

$marker_start
# Auto-added by setup_arch_pc.sh
export EL_HOME="\$HOME/AA_MY_DRIVE"
export PATH="\$HOME/.npm-global/bin:\$HOME/.local/bin:\$PATH"
export PHONE_TAILNET_IP="${PHONE_TAILNET_IP}"

# AI CLI aliases
alias ppx='python3 \$EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/ppx_terminal.py'
alias clx='python3 \$EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py'
alias gemx='python3 \$EL_HOME/03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_delegate.py'

# Workspace shortcut
alias el='cd \$EL_HOME'

# Tailscale-aware sync helpers
sync_from_phone() {
  rsync -av --progress "root@\${PHONE_TAILNET_IP}:\$1" "\$2"
}
sync_to_phone() {
  rsync -av --progress "\$1" "root@\${PHONE_TAILNET_IP}:\$2"
}
sync_creds_from_phone() {
  rsync -av --progress \\
    "root@\${PHONE_TAILNET_IP}:/mnt/sdcard/AA_MY_DRIVE/03_Credentials/" \\
    "\$EL_HOME/03_Credentials/"
}
$marker_end
EOF

  ok "Shell env wired in $rc"
  note "Reload with: source $rc  (or open a new terminal)"
}

# ============================================================
# Layer 8 : Verification
# ============================================================
verify() {
  log "Running verification"
  local fails=0

  # CLI presence
  for cli in git claude gemini codex python3 npm rsync curl jq; do
    if command -v "$cli" >/dev/null 2>&1; then
      ok "$cli -> $(command -v "$cli")"
    else
      err "$cli MISSING"
      fails=$((fails + 1))
    fi
  done

  # Filesystem checks
  [ -d "$EL_HOME/.git" ] && ok "Repo at $EL_HOME" || { err "Repo NOT at $EL_HOME"; fails=$((fails + 1)); }
  [ -d "$HOME/.claude" ] && ok "~/.claude exists" || { err "~/.claude MISSING"; fails=$((fails + 1)); }
  [ -d "$EL_HOME/.venv" ] && ok ".venv at $EL_HOME/.venv" || { err ".venv MISSING"; fails=$((fails + 1)); }
  [ -f "$EL_HOME/.claude/agents" ] || [ -d "$EL_HOME/.claude/agents" ] \
    && ok "Workspace .claude/agents/ ($(ls "$EL_HOME/.claude/agents/" 2>/dev/null | wc -l) files)" \
    || { err "Workspace .claude/agents MISSING"; fails=$((fails + 1)); }

  # Tailscale liveness
  if command -v tailscale >/dev/null 2>&1; then
    if tailscale status >/dev/null 2>&1; then
      ok "Tailscale up: $(tailscale ip -4 2>/dev/null | head -1)"
    else
      note "Tailscale installed but not up. Run: sudo tailscale up"
    fi
  fi

  echo
  if [ $fails -eq 0 ]; then
    ok "All checks passed"
    return 0
  else
    err "$fails check(s) failed; see $LOG_FILE"
    return 1
  fi
}

# ============================================================
# Manual followups (cannot be automated)
# ============================================================
print_manual_followup() {
  cat <<EOF

${GOLD}=========================================================${RESET}
${GOLD}  MANUAL FOLLOWUPS                                       ${RESET}
${GOLD}=========================================================${RESET}

1. ${GOLD}CREDENTIALS${RESET} (.env files, gitignored, rsync from phone):
     sync_creds_from_phone        # alias added by this script
   or manually:
     rsync -av root@${PHONE_TAILNET_IP}:/mnt/sdcard/AA_MY_DRIVE/03_Credentials/ \\
                 ${EL_HOME}/03_Credentials/

2. ${GOLD}CLAUDE CODE FIRST RUN${RESET}:
   Open a new shell, then run: claude
   First launch auto-installs the 13 plugins listed in ~/.claude/settings.json
   (agent-sdk-dev, code-review, commit-commands, feature-dev, security-guidance,
    pr-review-toolkit, plugin-dev, hookify, explanatory-output-style,
    learning-output-style, frontend-design, ralph-loop, claude-code-setup)

3. ${GOLD}TAILSCALE FOR THE 3RD NODE (Oracle E5)${RESET}:
   ssh oracle-e5
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up --auth-key=tskey-auth-XXXX
   Once joined: phone + Arch + Oracle = full mesh

4. ${GOLD}OPTIONAL: VNC SERVER${RESET} (so phone can see this Arch desktop):
   sudo pacman -S x11vnc
   x11vnc -storepasswd
   x11vnc -display :0 -auth ~/.Xauthority -rfbauth ~/.vnc/passwd \\
          -rfbport 5900 -forever -shared -bg
   Then connect from phone's RealVNC Viewer to <arch-tailnet-ip>:5900

5. ${GOLD}RELOAD SHELL${RESET}: source ~/.bashrc  (or ~/.zshrc)

EOF
}

# ============================================================
# Main
# ============================================================
main() {
  log "Everlight Hive bootstrap starting"
  log "Log file: $LOG_FILE"

  preflight
  install_pacman_deps
  setup_npm_userprefix
  clone_workspace
  install_ai_clis
  bootstrap_claude_global
  install_python_deps
  setup_shell_env

  echo
  if verify; then
    print_manual_followup
    log "Done."
    exit 0
  else
    print_manual_followup
    log "Done with errors. See $LOG_FILE."
    exit 1
  fi
}

main "$@"
