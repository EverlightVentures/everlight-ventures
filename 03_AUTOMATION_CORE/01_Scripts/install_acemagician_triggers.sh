#!/usr/bin/env bash
# install_acemagician_triggers.sh
#
# Installs the auto-trigger chain on the AceMagician PC (Arch Linux at
# 100.93.253.49) so that sync_conflict_resolver.sh runs automatically when:
#   (a) Rich plugs the Z Fold 7 into the AceMagician via USB
#   (b) The phone reaches the AceMagician via Tailscale (hourly cron fallback)
#   (c) The PC boots after being offline (catch-up run)
#
# Run this script ONCE on the AceMagician (not on phone):
#   ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49
#   cd ~/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts
#   sudo bash install_acemagician_triggers.sh
#
# Or run it remotely from phone:
#   ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 \
#       'sudo bash ~/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/install_acemagician_triggers.sh'
#
# Reversible: writes systemd units + udev rule. To undo, see "Undo" block at the
# bottom of this file.
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "ERROR: run as root (sudo bash $0)"
    exit 1
fi

# --- Paths (adjust if your AceMagician workspace path differs) --------------
USER_NAME="richgee"
USER_HOME="/home/$USER_NAME"
WORKSPACE="$USER_HOME/AA_MY_DRIVE"
RESOLVER="$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/sync_conflict_resolver.sh"

if [ ! -f "$RESOLVER" ]; then
    echo "ERROR: resolver not found at $RESOLVER"
    echo "Sync the workspace first via claude_sync_acemagician.sh"
    exit 1
fi
chmod +x "$RESOLVER"

# --- Wrapper script that the udev rule + cron call -------------------------
WRAPPER="/usr/local/bin/run-sync-conflict-resolver"
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# Wrapper invoked by udev / cron / boot. Runs as $USER_NAME so the workspace
# permissions are correct.
LOG="$WORKSPACE/_logs/sync_conflict_trigger.log"
mkdir -p "\$(dirname "\$LOG")"
echo "[\$(date '+%Y-%m-%d %H:%M:%S %Z')] trigger=\${1:-manual} fired" >> "\$LOG"
sudo -u $USER_NAME bash "$RESOLVER" >> "\$LOG" 2>&1
EOF
chmod +x "$WRAPPER"
echo "Installed: $WRAPPER"

# --- udev rule: trigger on Z Fold 7 USB plug ---------------------------------
# Samsung vendor ID is 04e8. The Z Fold 7 product ID may vary by USB mode
# (MTP vs ADB vs PTP). The rule below catches the SAMSUNG vendor with the
# common product IDs; adjust after running `lsusb` while plugged in.
UDEV_RULE="/etc/udev/rules.d/99-zfold7-sync-conflict-resolver.rules"
cat > "$UDEV_RULE" <<'EOF'
# Z Fold 7 (Samsung) plug-in trigger -- runs sync_conflict_resolver.sh
# Catches MTP mode (6860) + ADB mode (6863) + PTP mode (6865)
# Adjust idProduct if `lsusb` shows a different value when phone is plugged in.
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", ATTR{idProduct}=="6860", RUN+="/usr/local/bin/run-sync-conflict-resolver usb-plug-mtp"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", ATTR{idProduct}=="6863", RUN+="/usr/local/bin/run-sync-conflict-resolver usb-plug-adb"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", ATTR{idProduct}=="6865", RUN+="/usr/local/bin/run-sync-conflict-resolver usb-plug-ptp"
EOF
echo "Installed: $UDEV_RULE"
udevadm control --reload-rules
udevadm trigger
echo "udev reloaded"

# --- systemd timer: hourly Tailscale-reachable fallback ---------------------
SERVICE_FILE="/etc/systemd/system/sync-conflict-resolver.service"
TIMER_FILE="/etc/systemd/system/sync-conflict-resolver.timer"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Sync conflict resolver (Tailscale-reachable phone fallback)
After=network-online.target tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/run-sync-conflict-resolver cron-hourly
EOF

cat > "$TIMER_FILE" <<EOF
[Unit]
Description=Run sync conflict resolver hourly

[Timer]
OnBootSec=2min
OnUnitActiveSec=1h
Unit=sync-conflict-resolver.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now sync-conflict-resolver.timer
echo "Installed: $SERVICE_FILE + $TIMER_FILE (hourly timer + boot-catch-up)"

# --- Verify ----------------------------------------------------------------
echo ""
echo "=== Verification ==="
systemctl status sync-conflict-resolver.timer --no-pager | head -10
echo ""
echo "=== Next scheduled run ==="
systemctl list-timers sync-conflict-resolver.timer --no-pager 2>/dev/null | head -3
echo ""
echo "=== Manual test ==="
echo "Plug the Z Fold 7 in via USB and check: tail -f $WORKSPACE/_logs/sync_conflict_trigger.log"
echo ""
echo "=== udev product IDs ==="
echo "If USB plug doesn't fire, run 'lsusb' while phone is plugged in and update"
echo "$UDEV_RULE with the actual idProduct value, then 'sudo udevadm control --reload-rules'."
echo ""
echo "DONE. Triggers installed."
echo ""
echo "==================================================================="
echo "UNDO (paste these to remove all installed pieces):"
echo "  sudo systemctl disable --now sync-conflict-resolver.timer"
echo "  sudo rm $SERVICE_FILE $TIMER_FILE $UDEV_RULE $WRAPPER"
echo "  sudo systemctl daemon-reload"
echo "  sudo udevadm control --reload-rules"
echo "==================================================================="
