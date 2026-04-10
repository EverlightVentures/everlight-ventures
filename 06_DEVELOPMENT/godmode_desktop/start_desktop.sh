#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# LUCREX GOD MODE DESKTOP - Start Script
# Run from Termux (NOT inside PRoot)
# Launches: PulseAudio -> Termux X11 -> XFCE in PRoot Ubuntu
# ============================================================

# Kill any existing sessions
pkill -f "termux.x11" 2>/dev/null || true
pkill -f "pulseaudio" 2>/dev/null || true
pkill -f "virgl_test_server" 2>/dev/null || true

echo "========================================"
echo "  Starting LUCREX God Mode Desktop..."
echo "========================================"

# --- 1. Start PulseAudio ---
echo "[1/4] Starting PulseAudio (audio bridge)..."
pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" --exit-idle-time=-1 2>/dev/null
echo "  ✓ PulseAudio running"

# --- 2. Start VirGL (GPU passthrough for OpenGL fallback) ---
echo "[2/4] Starting VirGL renderer..."
if command -v virgl_test_server_android &>/dev/null; then
    MESA_NO_ERROR=1 virgl_test_server_android &>/dev/null &
    sleep 1
    echo "  ✓ VirGL running"
else
    echo "  ~ VirGL not installed (OK - Turnip handles GPU via Vulkan)"
fi

# --- 3. Start Termux X11 ---
echo "[3/4] Starting Termux X11 display..."
export DISPLAY=:0

# Start the Termux X11 server
termux-x11 :0 &>/dev/null &
sleep 1

# Launch Termux X11 Android activity
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity 2>/dev/null || {
    echo "  ! Termux X11 app not installed. Tap to install:"
    echo "    /sdcard/Download/termux-x11.apk"
    exit 1
}
sleep 2
echo "  ✓ Termux X11 started"

# --- 4. Launch XFCE inside PRoot ---
echo "[4/4] Launching XFCE desktop in PRoot Ubuntu..."

# Environment variables for the PRoot session
proot-distro login ubuntu --shared-tmp -- bash -c '
    export DISPLAY=:0
    export PULSE_SERVER=127.0.0.1
    export XDG_RUNTIME_DIR=/tmp/runtime-root
    export GALLIUM_DRIVER=virpipe
    export MESA_GL_VERSION_OVERRIDE=4.3

    # Turnip Vulkan environment
    export MESA_VK_WSI_PRESENT_MODE=immediate
    export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/freedreno_icd.json
    export TU_DEBUG=noconform

    mkdir -p $XDG_RUNTIME_DIR

    # Start dbus if not running
    if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
        eval $(dbus-launch --sh-syntax)
        export DBUS_SESSION_BUS_ADDRESS
    fi

    # Launch XFCE
    startxfce4 &
'

echo ""
echo "========================================"
echo "  God Mode Desktop is LIVE!"
echo "  Switch to Termux X11 app to see your desktop."
echo ""
echo "  Tips:"
echo "  - Connect Viture XR glasses via USB-C for big screen"
echo "  - Use xrandr to configure display resolution"
echo "  - Stop with: bash stop_desktop.sh"
echo "========================================"
