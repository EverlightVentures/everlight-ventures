#!/bin/bash
# Setup shell aliases for Everlight Autonomous System

SCRIPT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts"

# Detect shell
if [ -n "$ZSH_VERSION" ]; then
    RC_FILE="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    RC_FILE="$HOME/.bashrc"
else
    RC_FILE="$HOME/.profile"
fi

echo "Setting up aliases in: $RC_FILE"

# Backup RC file
cp "$RC_FILE" "${RC_FILE}.backup_$(date +%Y%m%d_%H%M%S)"

# Add aliases
cat >> "$RC_FILE" << 'EOF'

# ============================================================
# EVERLIGHT AUTONOMOUS SYSTEM ALIASES
# ============================================================

# AI Workers
alias ai='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/ai_terminal.py'
alias ppx='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/ppx_terminal.py'
alias cx='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/cx_terminal.py'
alias ask='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/ask_router.py'
alias gmx='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_delegate.py'
alias gem-mode='bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_mode.sh'
alias clx='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py'
alias claude-mode='bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_mode.sh'

# File Organization
alias organize='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/file_organizer/organize_files.py'
alias merge-folders='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/file_organizer/merge_duplicate_folders.py'
alias dedupe='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/file_organizer/deduplicate_files.py'

# Sync
alias sync-status='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/file_organizer/sync_manager.py --status'
alias sync-now='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/file_organizer/sync_manager.py'
alias sync-proton='rclone sync /mnt/sdcard/AA_MY_DRIVE protondrive:AA_MY_DRIVE --progress --exclude ".claude/**" --exclude "_logs/**" --exclude "*.tmp" --exclude "*.log"'

# Security
alias vault-setup='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/setup_vault.py'

# Navigation
alias ev='cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures'
alias llp='cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Last_Light_Protocol'
alias content='cd /mnt/sdcard/AA_MY_DRIVE/02_CONTENT_FACTORY'
alias auto='cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE'
alias drive='cd /mnt/sdcard/AA_MY_DRIVE'

# Utilities
alias everlight-status='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/system_status.py'

# Operations
alias brief='bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/morning_brief.sh'
alias route='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/task_router.py'
alias inbox='python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/staging_inbox_watcher.py --once'

EOF

echo "✓ Aliases added to $RC_FILE"
echo ""
echo "Reload shell or run: source $RC_FILE"
echo ""
echo "Available commands:"
echo "  ai \"question\"         - Ask GPT from terminal"
echo "  ppx \"research query\"  - Ask Perplexity from terminal"
echo "  cx \"coding task\"      - Ask Codex-style GPT for code"
echo "  ask \"question\"        - Auto-route query to best AI worker"
echo "  gmx \"task\"            - Delegate task to Gemini (JSON envelope)"
echo "  gem-mode plan         - Start Gemini plan-mode session"
echo "  clx \"task\"            - Delegate task to Claude (JSON envelope)"
echo "  claude-mode plan      - Start Claude plan-mode session"
echo "  organize              - Run file organizer"
echo "  merge-folders         - Merge duplicate folders"
echo "  dedupe                - Remove duplicate files"
echo "  sync-now              - Sync to Proton Drive"
echo "  sync-status           - Check sync status"
echo "  vault-setup           - Setup encrypted vault"
echo ""
echo "Navigation shortcuts:"
echo "  ev                    - Go to Everlight"
echo "  llp                   - Go to Last Light Protocol"
echo "  content               - Go to Content Factory"
echo "  auto                  - Go to Automation Core"
echo "  drive                 - Go to AA_MY_DRIVE"
