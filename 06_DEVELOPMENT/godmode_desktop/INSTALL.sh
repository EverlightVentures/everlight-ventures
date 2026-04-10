#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#   LUCREX GOD MODE DESKTOP - Master Installer
#   Full Linux Desktop + Turnip GPU + Wine + Steam + Viture XR
#
#   Run this from TERMUX (not PRoot):
#     bash /sdcard/AA_MY_DRIVE/06_DEVELOPMENT/godmode_desktop/INSTALL.sh
# ============================================================
set -e

SCRIPT_DIR="/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/godmode_desktop"

echo ""
echo "  ██╗     ██╗   ██╗ ██████╗██████╗ ███████╗██╗  ██╗"
echo "  ██║     ██║   ██║██╔════╝██╔══██╗██╔════╝╚██╗██╔╝"
echo "  ██║     ██║   ██║██║     ██████╔╝█████╗   ╚███╔╝ "
echo "  ██║     ██║   ██║██║     ██╔══██╗██╔══╝   ██╔██╗ "
echo "  ███████╗╚██████╔╝╚██████╗██║  ██║███████╗██╔╝ ██╗"
echo "  ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
echo ""
echo "       GOD MODE DESKTOP INSTALLER"
echo "       Snapdragon + Turnip + Wine + Viture XR"
echo ""
echo "  This will install:"
echo "    [1] Termux X11 display server"
echo "    [2] Turnip Vulkan (Adreno GPU acceleration)"
echo "    [3] PulseAudio (audio bridge)"
echo "    [4] Box64 + Wine (Windows app support)"
echo "    [5] Visual Studio Code"
echo "    [6] Steam + DXVK + gaming tools"
echo "    [7] Viture XR display + head tracking"
echo ""
echo "  Storage needed: ~10-15 GB"
echo "  Time: ~15-30 minutes"
echo ""
read -p "  Press ENTER to start (Ctrl+C to cancel)... "

echo ""
echo "========================================="
echo "  STEP 1: Termux-side packages"
echo "========================================="
bash "$SCRIPT_DIR/setup_termux_side.sh"

echo ""
echo "========================================="
echo "  STEP 2: PRoot Ubuntu packages"
echo "========================================="
proot-distro login ubuntu --shared-tmp -- bash "$SCRIPT_DIR/setup_proot_side.sh"

echo ""
echo "========================================="
echo "  STEP 3: Gaming + Viture XR"
echo "========================================="
proot-distro login ubuntu --shared-tmp -- bash "$SCRIPT_DIR/setup_viture_gaming.sh"

echo ""
echo "========================================="
echo "  STEP 4: Installing start/stop scripts"
echo "========================================="

# Copy start/stop to Termux home for easy access
cp "$SCRIPT_DIR/start_desktop.sh" "$HOME/start_desktop.sh"
cp "$SCRIPT_DIR/stop_desktop.sh" "$HOME/stop_desktop.sh"
chmod +x "$HOME/start_desktop.sh" "$HOME/stop_desktop.sh"

# Add aliases to .bashrc
if ! grep -q "start_desktop" "$HOME/.bashrc" 2>/dev/null; then
    echo '' >> "$HOME/.bashrc"
    echo '# God Mode Desktop' >> "$HOME/.bashrc"
    echo 'alias godmode="bash ~/start_desktop.sh"' >> "$HOME/.bashrc"
    echo 'alias stopdesktop="bash ~/stop_desktop.sh"' >> "$HOME/.bashrc"
fi

echo "  ✓ Start script: ~/start_desktop.sh (or just type: godmode)"
echo "  ✓ Stop script:  ~/stop_desktop.sh (or just type: stopdesktop)"

echo ""
echo "========================================="
echo "  STEP 5: Pre-flight checks"
echo "========================================="

# Quick verification
echo "  Checking Termux X11..."
command -v termux-x11 &>/dev/null && echo "    ✓ termux-x11 binary" || echo "    ✗ termux-x11 missing"

echo "  Checking PRoot packages..."
proot-distro login ubuntu -- bash -c '
    command -v vulkaninfo &>/dev/null && echo "    ✓ Vulkan tools" || echo "    ✗ Vulkan tools missing"
    command -v box64 &>/dev/null && echo "    ✓ Box64" || echo "    ✗ Box64 missing"
    [ -f /usr/local/bin/wine ] && echo "    ✓ Wine" || echo "    ✗ Wine missing"
    command -v code &>/dev/null && echo "    ✓ VSCode" || echo "    ✗ VSCode missing"
    command -v firefox &>/dev/null && echo "    ✓ Firefox" || echo "    ✗ Firefox missing"
    [ -f /usr/local/bin/steam ] && echo "    ✓ Steam launcher" || echo "    ✗ Steam launcher missing"
    [ -f /usr/local/bin/viture-display ] && echo "    ✓ Viture XR scripts" || echo "    ✗ Viture scripts missing"
' 2>/dev/null

echo ""
echo "========================================="
echo ""
echo "  ✅ GOD MODE DESKTOP INSTALLED!"
echo ""
echo "  IMPORTANT - You still need:"
echo "    1. Termux X11 APK installed (from GitHub/F-Droid)"
echo "       https://github.com/nickolasmayerpro/termux-x11-nightly/releases"
echo "    2. Winlator APK for AAA gaming (optional but recommended)"
echo "       https://github.com/nickolasmayerpro/Winlator/releases"
echo "    3. SpaceWalker app for Viture 6DOF (Play Store)"
echo ""
echo "  TO START:  godmode  (or: bash ~/start_desktop.sh)"
echo "  TO STOP:   stopdesktop"
echo ""
echo "  GAMING:"
echo "    - Lighter games: gamemode steam (inside desktop)"
echo "    - AAA games: Use Winlator app directly"
echo "    - VR/XR: Connect Viture glasses, run viture-display"
echo ""
echo "========================================="
