#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# LUCREX GOD MODE DESKTOP - Stop Script
# Cleanly shuts down the desktop session
# ============================================================

echo "Stopping God Mode Desktop..."

# Kill XFCE session inside PRoot
proot-distro login ubuntu --shared-tmp -- bash -c '
    pkill -f xfce4-session 2>/dev/null
    pkill -f xfwm4 2>/dev/null
    pkill -f xfce4-panel 2>/dev/null
    pkill -f xfdesktop 2>/dev/null
' 2>/dev/null

# Kill Termux-side services
pkill -f "virgl_test_server" 2>/dev/null
pkill -f "pulseaudio" 2>/dev/null

# Close Termux X11 activity
am force-stop com.termux.x11 2>/dev/null

echo "  ✓ Desktop stopped."
echo "  Run start_desktop.sh to restart."
