#!/bin/bash
# ============================================================
# VITURE XR + STEAM GAMING SETUP
# Run INSIDE PRoot Ubuntu
#
# Viture XR glasses connect via USB-C as a display.
# The neckband provides 3DOF/6DOF head tracking.
# This script sets up Steam + gaming tools to use them.
# ============================================================
set -e

echo "========================================"
echo "  VITURE XR GAMING - God Mode Setup"
echo "========================================"

# --- 1. Display configuration for Viture XR ---
echo "[1/5] Setting up Viture XR display support..."

# Viture XR glasses show up as a USB-C DisplayPort Alt Mode display
# xrandr will detect them as a second monitor
# Create a script to auto-configure when glasses are connected

mkdir -p /usr/local/bin
cat > /usr/local/bin/viture-display << 'VITURE_EOF'
#!/bin/bash
# Detect and configure Viture XR display
# Viture Pro XR: 1920x1080 @ 120Hz native

echo "Scanning for Viture XR display..."

# List all connected displays
DISPLAYS=$(xrandr --query 2>/dev/null)

if echo "$DISPLAYS" | grep -q "connected" | grep -v "primary"; then
    # External display detected (Viture XR via USB-C DP Alt)
    EXT_DISPLAY=$(echo "$DISPLAYS" | grep " connected" | grep -v "primary" | awk '{print $1}' | head -1)

    if [ -n "$EXT_DISPLAY" ]; then
        echo "Found external display: $EXT_DISPLAY"

        # Set to 1080p 120Hz if available, else 1080p 60Hz
        if echo "$DISPLAYS" | grep -A5 "$EXT_DISPLAY" | grep -q "1920x1080.*120"; then
            xrandr --output "$EXT_DISPLAY" --mode 1920x1080 --rate 120
            echo "  ✓ Set to 1920x1080 @ 120Hz"
        else
            xrandr --output "$EXT_DISPLAY" --mode 1920x1080 --rate 60 2>/dev/null || \
            xrandr --output "$EXT_DISPLAY" --auto
            echo "  ✓ Set to best available mode"
        fi

        # Mirror or extend based on argument
        if [ "$1" = "extend" ]; then
            xrandr --output "$EXT_DISPLAY" --right-of $(xrandr --query | grep "primary" | awk '{print $1}')
            echo "  ✓ Extended desktop mode"
        else
            # Default: mirror (best for VR/XR immersion)
            xrandr --output "$EXT_DISPLAY" --same-as $(xrandr --query | grep "primary" | awk '{print $1}')
            echo "  ✓ Mirror mode (immersive)"
        fi
    fi
else
    echo "No external display detected."
    echo "Plug in Viture XR glasses via USB-C and try again."
fi
VITURE_EOF
chmod +x /usr/local/bin/viture-display

echo "  ✓ Viture display script installed (run: viture-display)"

# --- 2. Steam via Box64 + Wine ---
echo "[2/5] Setting up Steam..."

# Steam runs via Wine + Box64 (x86_64 translation)
mkdir -p /opt/steam
cat > /usr/local/bin/steam << 'STEAM_EOF'
#!/bin/bash
# Launch Steam via Wine + Box64
# Box64 automatically translates x86_64 Wine -> ARM64

export WINEPREFIX=$HOME/.wine_steam
export WINEARCH=win64
export DISPLAY=:0
export PULSE_SERVER=127.0.0.1

# Turnip Vulkan for GPU accel
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/freedreno_icd.aarch64.json
export MESA_VK_WSI_PRESENT_MODE=immediate
export DXVK_HUD=fps

# Check if Steam is installed in Wine prefix
STEAM_EXE="$WINEPREFIX/drive_c/Program Files (x86)/Steam/steam.exe"

if [ ! -f "$STEAM_EXE" ]; then
    echo "Steam not installed yet. Downloading installer..."
    mkdir -p /tmp/steam_setup

    wget -q "https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe" \
        -O /tmp/steam_setup/SteamSetup.exe 2>/dev/null

    if [ -f /tmp/steam_setup/SteamSetup.exe ]; then
        echo "Running Steam installer (this takes a few minutes)..."
        echo "Follow the installer in the desktop window."
        wine /tmp/steam_setup/SteamSetup.exe
    else
        echo "Download failed. Visit store.steampowered.com and download manually."
        echo "Then run: wine SteamSetup.exe"
    fi
else
    echo "Launching Steam..."
    wine "$STEAM_EXE" -no-browser "$@"
fi
STEAM_EOF
chmod +x /usr/local/bin/steam

echo "  ✓ Steam launcher installed (run: steam)"

# --- 3. DXVK (DirectX -> Vulkan translation for games) ---
echo "[3/5] Installing DXVK (DirectX to Vulkan)..."

DXVK_VER="2.4.1"
if [ ! -d /opt/dxvk ]; then
    cd /tmp
    wget -q "https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VER}/dxvk-${DXVK_VER}.tar.gz" -O dxvk.tar.gz 2>/dev/null || {
        # Fallback
        wget -q "https://github.com/doitsujin/dxvk/releases/download/v2.3.1/dxvk-2.3.1.tar.gz" -O dxvk.tar.gz 2>/dev/null || true
    }

    if [ -f dxvk.tar.gz ]; then
        mkdir -p /opt/dxvk
        tar -xzf dxvk.tar.gz -C /opt/dxvk --strip-components=1
        rm dxvk.tar.gz

        # Install DXVK into default Wine prefix
        cat > /usr/local/bin/install-dxvk << 'DXVK_EOF'
#!/bin/bash
# Install DXVK into a Wine prefix
PREFIX=${WINEPREFIX:-$HOME/.wine}
echo "Installing DXVK into $PREFIX..."
cd /opt/dxvk
bash setup_dxvk.sh install --with-d3d10 2>/dev/null || {
    # Manual copy
    for dll in d3d9.dll d3d10core.dll d3d11.dll dxgi.dll; do
        cp -f x64/$dll "$PREFIX/drive_c/windows/system32/" 2>/dev/null
        cp -f x32/$dll "$PREFIX/drive_c/windows/syswow64/" 2>/dev/null
    done
}
echo "  ✓ DXVK installed in $PREFIX"
DXVK_EOF
        chmod +x /usr/local/bin/install-dxvk
        echo "  ✓ DXVK ${DXVK_VER} installed (run: install-dxvk)"
    else
        echo "  ! DXVK download failed -- install manually later"
    fi
    cd /root
else
    echo "  ✓ DXVK already installed"
fi

# --- 4. Gaming optimizations ---
echo "[4/5] Applying gaming optimizations..."

cat > /usr/local/bin/gamemode << 'GAMEMODE_EOF'
#!/bin/bash
# Quick gamemode toggle -- optimizes for gaming performance
echo "=== GAME MODE ACTIVATED ==="

# GPU: max performance
export MESA_VK_WSI_PRESENT_MODE=immediate
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/freedreno_icd.aarch64.json
export TU_DEBUG=noconform
export MESA_GL_VERSION_OVERRIDE=4.3
export GALLIUM_DRIVER=virpipe

# DXVK: show FPS overlay
export DXVK_HUD=fps,memory

# Wine: gaming optimizations
export STAGING_SHARED_MEMORY=1
export WINE_LARGE_ADDRESS_AWARE=1

echo "  ✓ Vulkan: Turnip (Adreno HW accel)"
echo "  ✓ DXVK: DirectX -> Vulkan active"
echo "  ✓ FPS overlay enabled"
echo ""
echo "Run your game now, e.g.:"
echo "  wine game.exe"
echo "  steam"
echo ""

# If argument provided, run it
if [ -n "$1" ]; then
    exec "$@"
else
    exec bash
fi
GAMEMODE_EOF
chmod +x /usr/local/bin/gamemode

echo "  ✓ Gamemode script installed (run: gamemode)"

# --- 5. Viture 6DOF head tracking (experimental) ---
echo "[5/5] Setting up Viture head tracking bridge..."

# The Viture neckband exposes 6DOF data via USB HID
# SpaceWalker API or the Viture SDK can read it
# For now, create a helper that maps it to mouse input (useful in FPS games)

cat > /usr/local/bin/viture-headtrack << 'TRACK_EOF'
#!/bin/bash
# Viture 6DOF Head Tracking Bridge
# Reads IMU data from Viture neckband and maps to mouse/gamepad
#
# Requirements:
#   - Viture XR glasses + neckband connected
#   - SpaceWalker app running on Android (provides the tracking data)
#   - OR: Viture SDK (if building native support)
#
# For now, SpaceWalker handles the 6DOF -> virtual display mapping
# natively on Android. The Linux desktop sees it as a standard display.
#
# For games that need head tracking input:
#   1. Use SpaceWalker's "mouse emulation" mode
#   2. Or use OpenTrack with UDP input from SpaceWalker

echo "=== Viture 6DOF Head Tracking ==="
echo ""
echo "The Viture neckband provides 6DOF tracking via SpaceWalker."
echo ""
echo "Option 1 (Recommended): SpaceWalker App"
echo "  - Install SpaceWalker from Play Store"
echo "  - Enable '6DOF Mode' in settings"
echo "  - It maps head movement to the virtual screen"
echo "  - Games see it as a large immersive display"
echo ""
echo "Option 2: OpenTrack (for flight sims, racing games)"
echo "  - Install opentrack: apt install opentrack"
echo "  - Configure SpaceWalker to send UDP tracking data"
echo "  - OpenTrack translates it to game-compatible head tracking"
echo ""
echo "Option 3: Direct HID (advanced)"
echo "  - Neckband IMU data available via /dev/hidraw*"
echo "  - Parse with python3 + pyusb"
echo "  - Map pitch/yaw/roll to mouse movement"
echo ""

# Check if opentrack is installed
if command -v opentrack &>/dev/null; then
    echo "OpenTrack is installed. Launch with: opentrack"
elif [ "$1" = "install" ]; then
    echo "Installing OpenTrack..."
    apt install -y opentrack 2>/dev/null || {
        echo "OpenTrack not in repos. Building from source..."
        apt install -y cmake g++ qtbase5-dev libopencv-dev
        cd /tmp
        git clone --depth 1 https://github.com/opentrack/opentrack.git
        cd opentrack && mkdir build && cd build
        cmake .. && make -j$(nproc) && make install
        cd /root
    }
fi
TRACK_EOF
chmod +x /usr/local/bin/viture-headtrack

echo "  ✓ Head tracking helper installed (run: viture-headtrack)"

echo ""
echo "========================================"
echo "  VITURE XR GAMING SETUP COMPLETE!"
echo ""
echo "  Commands available:"
echo "    viture-display    - Configure XR glasses display"
echo "    viture-display extend  - Extended desktop mode"
echo "    steam             - Launch Steam via Wine"
echo "    gamemode          - Activate gaming optimizations"
echo "    gamemode wine game.exe  - Run game with optimizations"
echo "    install-dxvk      - Install DirectX->Vulkan in Wine prefix"
echo "    viture-headtrack  - 6DOF head tracking options"
echo ""
echo "  Quick start:"
echo "    1. Connect Viture XR glasses via USB-C"
echo "    2. Run: viture-display"
echo "    3. Run: gamemode steam"
echo "    4. Install a game and play!"
echo ""
echo "  For best performance:"
echo "    - Use Winlator for heavy AAA games (separate APK)"
echo "    - Use Wine+Box64 for lighter Windows games"
echo "    - Steam Remote Play works great over WiFi too"
echo "========================================"
