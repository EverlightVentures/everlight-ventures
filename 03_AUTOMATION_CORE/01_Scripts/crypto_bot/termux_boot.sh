#!/bin/bash
#
# Termux Boot Script for CDE_BOT
#
# To enable auto-start on phone boot:
# 1. Install Termux:Boot from F-Droid
# 2. Copy this script: cp termux_boot.sh ~/.termux/boot/start_crypto_bot.sh
# 3. chmod +x ~/.termux/boot/start_crypto_bot.sh
#
# For proot-distro (Ubuntu), the boot script should be:
# #!/data/data/com.termux/files/usr/bin/bash
# termux-wake-lock
# proot-distro login ubuntu -- /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/cb start
#

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot"

# Acquire wake lock to keep device awake
termux-wake-lock 2>/dev/null || true

# Wait for network to be available
sleep 10

# Start the bot (24/7 watchdog) + dashboard
cd "$BOT_DIR"
bash "$BOT_DIR/cb" daemon
bash "$BOT_DIR/run_dashboard.sh" || true

# Log boot start
echo "$(date): CDE_BOT started via boot script" >> "$BOT_DIR/logs/boot.log"
