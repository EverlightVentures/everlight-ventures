#!/bin/bash
# Verify Everlight Autonomous System Setup

echo "==========================================================="
echo "  EVERLIGHT AUTONOMOUS SYSTEM - SETUP VERIFICATION"
echo "==========================================================="
echo ""

# Check folder structure
echo "📂 Checking folder structure..."
folders=(
    "01_BUSINESSES/Everlight_Ventures"
    "01_BUSINESSES/Last_Light_Protocol"
    "02_CONTENT_FACTORY"
    "03_AUTOMATION_CORE"
    "04_MEDIA_LIBRARY"
    "05_PERSONAL"
)

for folder in "${folders[@]}"; do
    if [ -d "/mnt/sdcard/AA_MY_DRIVE/$folder" ]; then
        echo "  ✓ $folder"
    else
        echo "  ✗ $folder (missing)"
    fi
done

echo ""
echo "🤖 Checking AI worker scripts..."
scripts=(
    "03_AUTOMATION_CORE/01_Scripts/ai_workers/ai_terminal.py"
    "03_AUTOMATION_CORE/01_Scripts/ai_workers/ppx_terminal.py"
    "03_AUTOMATION_CORE/01_Scripts/setup_vault.py"
    "03_AUTOMATION_CORE/01_Scripts/file_organizer/merge_duplicate_folders.py"
    "03_AUTOMATION_CORE/01_Scripts/file_organizer/deduplicate_files.py"
)

for script in "${scripts[@]}"; do
    if [ -f "/mnt/sdcard/AA_MY_DRIVE/$script" ]; then
        echo "  ✓ $(basename $script)"
    else
        echo "  ✗ $(basename $script) (missing)"
    fi
done

echo ""
echo "⚡ Checking shell aliases..."
alias_commands=("ai" "ppx" "organize" "dedupe" "merge-folders" "ev" "llp")
for cmd in "${alias_commands[@]}"; do
    if alias $cmd &>/dev/null; then
        echo "  ✓ $cmd"
    else
        echo "  ✗ $cmd (not found - run: source ~/.zshrc)"
    fi
done

echo ""
echo "☁️  Checking Proton Drive connection..."
if rclone lsd protondrive: &>/dev/null; then
    echo "  ✓ Proton Drive connected"
else
    echo "  ✗ Proton Drive connection failed (CAPTCHA?)"
fi

echo ""
echo "🐍 Checking Python dependencies..."
if python3 -c "import requests" 2>/dev/null; then
    echo "  ✓ requests library installed"
else
    echo "  ✗ requests library missing (run: pip install requests --break-system-packages)"
fi

echo ""
echo "==========================================================="
echo "  NEXT ACTIONS"
echo "==========================================================="
echo ""
echo "1. Secure credentials:"
echo "   vault-setup"
echo ""
echo "2. Test AI workers:"
echo "   ai \"hello\""
echo ""
echo "3. Clean up files:"
echo "   merge-folders --execute"
echo "   dedupe --execute"
echo ""
echo "4. Sync to cloud:"
echo "   sync-proton"
echo ""
echo "Read: YOUR_ACTION_PLAN.md for detailed instructions"
echo ""
