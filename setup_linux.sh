#!/bin/bash
# setup_linux.sh - Bootstrap hive mind on a Linux laptop
# Run once after cloning the repo:
#   git clone https://github.com/YOUR_USER/YOUR_REPO ~/AA_MY_DRIVE
#   cd ~/AA_MY_DRIVE && bash setup_linux.sh

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] && SHELL_RC="$HOME/.zshrc"

echo "=== Hive Mind Linux Setup ==="
echo "Repo root: $REPO_DIR"

# ---- 1. Set EVERLIGHT_ROOT so path_resolver finds the right root ----
if ! grep -q "EVERLIGHT_ROOT" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Hive Mind root path" >> "$SHELL_RC"
    echo "export EVERLIGHT_ROOT=\"$REPO_DIR\"" >> "$SHELL_RC"
    echo "[OK] Added EVERLIGHT_ROOT to $SHELL_RC"
else
    echo "[SKIP] EVERLIGHT_ROOT already in $SHELL_RC"
fi

# ---- 2. Python dependencies ----
echo ""
echo "--- Python setup ---"
if ! command -v python3 &>/dev/null; then
    echo "[WARN] python3 not found. Install with: sudo apt install python3 python3-pip"
else
    python3 --version
    if [ -f "$REPO_DIR/requirements.txt" ]; then
        pip3 install -r "$REPO_DIR/requirements.txt" --quiet
        echo "[OK] requirements.txt installed"
    fi
    # XLM bot specific
    if [ -f "$REPO_DIR/xlm_bot/requirements.txt" ]; then
        pip3 install -r "$REPO_DIR/xlm_bot/requirements.txt" --quiet
        echo "[OK] xlm_bot requirements installed"
    fi
fi

# ---- 3. tmux config ----
echo ""
echo "--- tmux ---"
if command -v tmux &>/dev/null; then
    if [ ! -f "$HOME/.tmux.conf" ]; then
        cp "$REPO_DIR/tmux_config_optimized.conf" "$HOME/.tmux.conf"
        echo "[OK] tmux config installed"
    else
        echo "[SKIP] ~/.tmux.conf already exists"
    fi
else
    echo "[WARN] tmux not found. Install with: sudo apt install tmux"
fi

# ---- 4. Claude Code config ----
echo ""
echo "--- Claude Code ---"
if ! command -v claude &>/dev/null; then
    echo "[WARN] claude CLI not found."
    echo "       Install: npm install -g @anthropic-ai/claude-code"
else
    echo "[OK] claude found: $(claude --version 2>/dev/null || echo 'unknown version')"
fi

# .claude/ is gitignored (local only). Copy the template if present.
if [ -d "$REPO_DIR/.claude" ]; then
    echo "[NOTE] .claude/ exists locally (gitignored). Copy manually if needed."
fi

# ---- 5. Verify path resolver ----
echo ""
echo "--- Path resolver test ---"
python3 "$REPO_DIR/everlight_os/_meta/path_resolver.py" 2>/dev/null | head -3

# ---- 6. Summary ----
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Reload shell: source $SHELL_RC"
echo "  2. Restore secrets (NOT in git):"
echo "     - xlm_bot/secrets/config.json  (copy from phone via scp or USB)"
echo "     - 03_AUTOMATION_CORE/03_Credentials/ (API keys)"
echo "  3. For Nextcloud sync of media/backups: see NEXTCLOUD_SYNC_GUIDE.md"
echo "  4. To run the orchestrator: bash everlight_orchestrator.sh"
echo ""
