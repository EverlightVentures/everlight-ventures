#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# termux_boot_nextcloud.sh -- Auto-start Nextcloud on phone boot
#
# INSTALL:
#   1. Install "Termux:Boot" from F-Droid (NOT Play Store)
#   2. Open Termux:Boot once to enable it
#   3. Copy this file:
#        cp /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/termux_boot_nextcloud.sh \
#           ~/.termux/boot/nextcloud
#   4. Make executable:
#        chmod +x ~/.termux/boot/nextcloud
#
# PHANTOM PROCESS KILLER (Android 12+):
#   If Termux gets killed by Android, run this from a PC via adb:
#     adb shell device_config put activity_manager max_phantom_processes 2147483647
#   Or enable "Disable child process limits" in Android Developer Options.
# =============================================================================

# Keep Termux awake (prevents Android from killing it)
termux-wake-lock

# Wait for system to settle after boot
sleep 20

LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud/boot.log"
mkdir -p "$(dirname $LOG)"
echo "$(date): Boot script started" >> "$LOG"

# Enter PRoot-Ubuntu and start services
proot-distro login ubuntu \
    --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/start_services.sh \
    >> "$LOG" 2>&1

echo "$(date): Services start attempted" >> "$LOG"

# Optional: start ngrok if authtoken is configured
# Uncomment and set your token:
# export NGROK_AUTHTOKEN="your_token_here"
# proot-distro login ubuntu \
#     --bind /mnt/sdcard:/mnt/sdcard \
#     -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/setup_ngrok.sh \
#     >> "$LOG" 2>&1

echo "$(date): Boot script complete" >> "$LOG"
