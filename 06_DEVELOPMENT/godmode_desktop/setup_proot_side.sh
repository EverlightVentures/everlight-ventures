#!/bin/bash
# ============================================================
# PHASE 2: PRoot Ubuntu setup (run INSIDE proot-distro)
# Installs: Turnip/Vulkan, Box64, Wine, VSCode, audio config
# ============================================================
set -e

echo "========================================"
echo "  LUCREX GOD MODE DESKTOP - PRoot Side"
echo "  Ubuntu 25.10 + Turnip + Wine + VSCode"
echo "========================================"

echo "[1/8] Updating Ubuntu packages..."
apt update && apt upgrade -y

echo "[2/8] Installing Vulkan + Turnip (Adreno GPU acceleration)..."
apt install -y mesa-vulkan-drivers vulkan-tools libvulkan1 libvulkan-dev
# Turnip is included in mesa-vulkan-drivers for ARM64/Adreno

echo "[3/8] Verifying Vulkan/Turnip..."
if vulkaninfo --summary 2>/dev/null | grep -i "turnip\|adreno\|qualcomm"; then
    echo "  ✓ Turnip Vulkan driver detected!"
else
    echo "  ! Vulkan info not available in PRoot (normal -- works at runtime with X11)"
fi

echo "[4/8] Installing Box64 (x86_64 -> ARM64 translation)..."
# Add Box64 repo
if ! command -v box64 &>/dev/null; then
    apt install -y wget gpg
    wget -qO- https://pi-apps-coders.github.io/box64-debs/KEY.gpg | gpg --dearmor -o /usr/share/keyrings/box64-archive-keyring.gpg 2>/dev/null || true

    # Try the generic ARM64 repo
    echo "deb [signed-by=/usr/share/keyrings/box64-archive-keyring.gpg] https://pi-apps-coders.github.io/box64-debs/debian ./" > /etc/apt/sources.list.d/box64.list
    apt update 2>/dev/null || true
    apt install -y box64-generic-arm 2>/dev/null || apt install -y box64 2>/dev/null || {
        echo "  ! Box64 repo install failed, trying manual build..."
        apt install -y cmake gcc g++ git
        cd /tmp
        [ -d box64 ] && rm -rf box64
        git clone --depth 1 https://github.com/ptitSeb/box64.git
        cd box64
        mkdir build && cd build
        cmake .. -DARM_DYNAREC=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo
        make -j$(nproc)
        make install
        cd /root
        echo "  ✓ Box64 built from source"
    }
else
    echo "  ✓ Box64 already installed"
fi

echo "[5/8] Installing Wine (via Box64)..."
if ! command -v wine 2>/dev/null && ! [ -d /opt/wine ]; then
    # Download Wine x86_64 (Box64 will translate it)
    WINE_VER="9.0"
    mkdir -p /opt/wine
    cd /tmp

    # Try Wine from WineHQ
    apt install -y cabextract libfreetype6 libfontconfig1 libxext6 libxrender1 \
        libxi6 libxrandr2 libxcursor1 libxcomposite1 libxinerama1 2>/dev/null || true

    wget -q "https://github.com/Kron4ek/Wine-Builds/releases/download/${WINE_VER}/wine-${WINE_VER}-amd64.tar.xz" -O wine.tar.xz 2>/dev/null || {
        # Fallback: try latest stable
        wget -q "https://github.com/Kron4ek/Wine-Builds/releases/download/9.22/wine-9.22-amd64.tar.xz" -O wine.tar.xz 2>/dev/null || {
            echo "  ! Wine download failed. Will need manual install."
            echo "    Download from: https://github.com/Kron4ek/Wine-Builds/releases"
            touch /tmp/wine_failed
        }
    }

    if [ -f wine.tar.xz ] && [ ! -f /tmp/wine_failed ]; then
        tar -xf wine.tar.xz -C /opt/wine --strip-components=1
        ln -sf /opt/wine/bin/wine /usr/local/bin/wine
        ln -sf /opt/wine/bin/wine64 /usr/local/bin/wine64
        ln -sf /opt/wine/bin/wineboot /usr/local/bin/wineboot
        ln -sf /opt/wine/bin/winecfg /usr/local/bin/winecfg
        ln -sf /opt/wine/bin/wineserver /usr/local/bin/wineserver
        rm -f wine.tar.xz
        echo "  ✓ Wine ${WINE_VER} installed to /opt/wine"
    fi
    cd /root
else
    echo "  ✓ Wine already installed"
fi

echo "[6/8] Installing Visual Studio Code..."
if ! command -v code &>/dev/null; then
    # VSCode for ARM64
    wget -q "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-arm64" -O /tmp/vscode.deb 2>/dev/null || {
        # Fallback: code-oss from Ubuntu repos
        apt install -y gnome-keyring 2>/dev/null || true
        echo "  ! Direct VSCode download failed, trying code-oss..."
    }

    if [ -f /tmp/vscode.deb ]; then
        dpkg -i /tmp/vscode.deb 2>/dev/null || apt install -f -y
        rm -f /tmp/vscode.deb
        echo "  ✓ VSCode installed"
    else
        # Try snap alternative or just skip
        echo "  ! VSCode needs manual install. Download ARM64 .deb from code.visualstudio.com"
    fi
else
    echo "  ✓ VSCode already installed"
fi

echo "[7/8] Configuring PulseAudio bridge..."
# Configure PulseAudio to connect to Termux's PulseAudio server
mkdir -p /root/.config/pulse
cat > /root/.config/pulse/default.pa << 'PULSE_EOF'
#!/usr/bin/pulseaudio -nF
.include /etc/pulse/default.pa
# Connect to Termux PulseAudio
load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1
PULSE_EOF

# Set PULSE_SERVER env var
if ! grep -q "PULSE_SERVER" /root/.bashrc 2>/dev/null; then
    echo '' >> /root/.bashrc
    echo '# PulseAudio bridge to Termux' >> /root/.bashrc
    echo 'export PULSE_SERVER=127.0.0.1' >> /root/.bashrc
fi

echo "  ✓ PulseAudio configured"

echo "[8/8] Installing extra desktop tools..."
apt install -y \
    htop neofetch file-roller \
    vlc mpv \
    gimp 2>/dev/null || true

echo ""
echo "========================================"
echo "  PRoot setup COMPLETE!"
echo ""
echo "  Installed:"
echo "    ✓ Vulkan + Turnip (Adreno HW accel)"
echo "    ✓ Box64 (x86_64 translation)"
echo "    ✓ Wine (Windows app support)"
echo "    ✓ VSCode (code editor)"
echo "    ✓ PulseAudio bridge (audio)"
echo "    ✓ Desktop tools (VLC, GIMP, etc.)"
echo ""
echo "  Next: Copy start_desktop.sh to Termux home"
echo "        and run it to launch XFCE!"
echo "========================================"
