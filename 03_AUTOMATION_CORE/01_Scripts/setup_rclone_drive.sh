#!/usr/bin/env bash
# setup_rclone_drive.sh
# ─────────────────────
# One-time setup. Marquise runs this on PHONE (Termux) to:
#   1. Install rclone if missing
#   2. Authenticate rclone to his Google Drive (browser flow, ~2 min)
#   3. Verify the remote works
#   4. Optionally set up a crypt remote for encrypted backups
#
# After this runs once, the rclone.conf is saved at
# ~/.config/rclone/rclone.conf and never needs re-auth (refresh tokens).
# The post_arm_321_recovery.sh script copies this conf to the ARM
# instance when it lands.
#
# Cost: $0. Drive 15GB free is plenty (Blinko + n8n + .env ~ 1-2 GB).
set -euo pipefail

echo "═══════════════════════════════════════════════════════════════"
echo "  rclone Drive setup for Marquise's Google Drive"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: install rclone
if ! command -v rclone >/dev/null 2>&1; then
    echo "[install] rclone not found, installing..."
    if command -v pkg >/dev/null 2>&1; then
        # Termux
        pkg install -y rclone
    elif command -v apt >/dev/null 2>&1; then
        sudo apt install -y rclone
    else
        echo "FAIL: don't know how to install rclone on this system"
        exit 1
    fi
fi
echo "✓ rclone installed: $(rclone --version | head -1)"
echo ""

# Step 2: check if drive_everlight remote already exists
if rclone listremotes 2>/dev/null | grep -q "drive_everlight:"; then
    echo "✓ drive_everlight remote already configured"
    echo ""
    echo "Verifying it works..."
    if rclone lsd drive_everlight: 2>&1 | head -5; then
        echo "✓ Drive remote works"
    else
        echo "WARNING: remote exists but doesn't work. May need re-auth:"
        echo "  rclone config reconnect drive_everlight:"
    fi
else
    echo "drive_everlight remote not configured. Starting interactive setup."
    echo ""
    echo "WHEN PROMPTED:"
    echo "  - Choose 'n' for new remote"
    echo "  - Name: drive_everlight"
    echo "  - Storage: select 'Google Drive' (number 22 or so)"
    echo "  - client_id: leave blank (uses rclone's default)"
    echo "  - client_secret: leave blank"
    echo "  - scope: 1 (Full access)"
    echo "  - root_folder_id: leave blank"
    echo "  - service_account_file: leave blank"
    echo "  - Auto config: on a phone, choose 'n' (no browser available)"
    echo "    Then paste the URL into Chrome, log in to Marquise's Google,"
    echo "    grant permission, and paste the token back."
    echo ""
    echo "Press ENTER to start rclone config..."
    read -r
    rclone config
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Optional: encrypted layer on top (recommended for sensitive)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
if rclone listremotes 2>/dev/null | grep -q "drive_everlight_crypt:"; then
    echo "✓ drive_everlight_crypt already configured"
else
    echo "To set up encrypted Drive layer, run:"
    echo "  rclone config"
    echo "  -> n (new)"
    echo "  -> Name: drive_everlight_crypt"
    echo "  -> Storage: 'crypt'"
    echo "  -> Remote: drive_everlight:Everlight/encrypted"
    echo "  -> filename_encryption: standard"
    echo "  -> directory_name_encryption: yes"
    echo "  -> password: choose strong password (write it down)"
    echo "  -> password2: random string"
    echo ""
    echo "Skipping for now (you can add this later)."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Pre-stage Drive folder structure"
echo "═══════════════════════════════════════════════════════════════"
echo ""
rclone mkdir drive_everlight:Everlight 2>/dev/null && echo "✓ Created Everlight/" || echo "Everlight/ exists or failed"
rclone mkdir drive_everlight:Everlight/oracle_e5_backups 2>/dev/null && echo "✓ Created oracle_e5_backups/" || echo "oracle_e5_backups/ exists or failed"
rclone mkdir drive_everlight:Everlight/blinko_continuous 2>/dev/null && echo "✓ Created blinko_continuous/" || echo "blinko_continuous/ exists or failed"
rclone mkdir drive_everlight:Everlight/n8n_workflows 2>/dev/null && echo "✓ Created n8n_workflows/" || echo "n8n_workflows/ exists or failed"

echo ""
echo "✓ rclone Drive setup complete"
echo "  Config saved at: ${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
echo ""
echo "Verify with: rclone lsd drive_everlight:"
echo ""
echo "Once ARM A1.Flex capacity opens and auto-grab fires:"
echo "  → post_arm_321_recovery.sh will copy this rclone.conf to the ARM"
echo "  → ARM will push the orphan E5 data to drive_everlight:Everlight/"
echo "  → Phone pull cron will sync to /mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/offsite_mirror/active/"
echo "  → After verification, you approve Oracle duplicate cleanup"
