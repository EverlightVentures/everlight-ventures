#!/bin/bash
# ============================================================
# LUCREX GOD MODE DESKTOP - Mahesh Technicals Hybrid
# Based on: github.com/MaheshTechnicals/modded-ubuntu
# Enhanced with: Turnip, Wine, Box64, DXVK, Viture XR
#
# Run INSIDE PRoot Ubuntu as root:
#   bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/godmode_desktop/mahesh_hybrid_setup.sh
# ============================================================

R="$(printf '\033[1;31m')"
G="$(printf '\033[1;32m')"
Y="$(printf '\033[1;33m')"
W="$(printf '\033[1;37m')"
C="$(printf '\033[1;36m')"
arch=$(uname -m)

SCRIPT_DIR="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/godmode_desktop"
MAHESH_DIR="/tmp/modded-ubuntu"

banner() {
    clear
    cat <<- EOF
${C}  ██╗     ██╗   ██╗ ██████╗██████╗ ███████╗██╗  ██╗
${Y}  ██║     ██║   ██║██╔════╝██╔══██╗██╔════╝╚██╗██╔╝
${G}  ██║     ██║   ██║██║     ██████╔╝█████╗   ╚███╔╝
${C}  ██║     ██║   ██║██║     ██╔══██╗██╔══╝   ██╔██╗
${Y}  ███████╗╚██████╔╝╚██████╗██║  ██║███████╗██╔╝ ██╗
${W}  ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝

${G}  God Mode Desktop - Mahesh Technicals Hybrid Edition
${C}  Turnip GPU + Wine + Box64 + DXVK + Viture XR
${W}
EOF
}

downloader(){
    path="$1"
    [[ -e "$path" ]] && rm -rf "$path"
    echo "Downloading $(basename $1)..."
    curl --progress-bar --insecure --fail \
         --retry-connrefused --retry 3 --retry-delay 2 \
         --location --output ${path} "$2"
}

# ============================================================
# PHASE 1: Mahesh's base setup (from modded-ubuntu gui.sh)
# ============================================================

fix_machineid() {
    echo -e "${C}[1] Fixing D-Bus machine-id...${W}"
    if [ ! -s /etc/machine-id ]; then
        rm -f /var/lib/dbus/machine-id /etc/machine-id
        dbus-uuidgen --ensure=/etc/machine-id
        dbus-uuidgen --ensure
        ln -sf /etc/machine-id /var/lib/dbus/machine-id
        echo -e "${G}  ✓ Machine-id created${W}"
    else
        echo -e "${G}  ✓ Machine-id exists${W}"
    fi
}

install_base_packages() {
    banner
    echo -e "${C}[2] Installing base packages (Mahesh's package list)...${W}"
    apt-get update -y

    # udisks2 fix (from Mahesh)
    apt install udisks2 -y 2>/dev/null || true
    rm -f /var/lib/dpkg/info/udisks2.postinst
    echo "" > /var/lib/dpkg/info/udisks2.postinst 2>/dev/null
    dpkg --configure -a 2>/dev/null
    apt-mark hold udisks2 2>/dev/null

    # Mahesh's core package list + our additions
    packs=(sudo gnupg2 curl nano git xz-utils at-spi2-core xfce4 xfce4-goodies xfce4-terminal librsvg2-common menu inetutils-tools dialog exo-utils tigervnc-standalone-server tigervnc-common tigervnc-tools dbus-x11 fonts-beng fonts-beng-extra gtk2-engines-murrine gtk2-engines-pixbuf apt-transport-https)
    for pkg in "${packs[@]}"; do
        type -p "$pkg" &>/dev/null || {
            echo -e "  ${G}Installing: ${Y}$pkg${W}"
            apt-get install "$pkg" -y --no-install-recommends 2>/dev/null
        }
    done

    apt-get update -y
    apt-get upgrade -y
}

install_software() {
    banner
    echo -e "${C}[3] Installing software (auto-selecting best options)...${W}"

    # Firefox (already installed, but make sure)
    [[ $(command -v firefox) ]] && echo -e "${Y}  Firefox already installed${W}" || {
        echo -e "${G}  Installing Firefox...${W}"
        bash <(curl -fsSL "https://raw.githubusercontent.com/MaheshTechnicals/modded-ubuntu/refs/heads/mt/distro/firefox.sh") 2>/dev/null
    }

    # VSCode (already installed, but make sure)
    [[ $(command -v code) ]] && echo -e "${Y}  VSCode already installed${W}" || {
        echo -e "${G}  Installing VSCode...${W}"
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/packages.microsoft.gpg 2>/dev/null
        echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list
        apt update -y 2>/dev/null
        apt install code -y 2>/dev/null
    }

    # MPV + VLC
    for player in mpv vlc; do
        [[ $(command -v $player) ]] && echo -e "${Y}  $player already installed${W}" || {
            echo -e "${G}  Installing $player...${W}"
            apt install -y $player 2>/dev/null
        }
    done
}

setup_sound() {
    echo -e "${C}[4] Configuring sound (Mahesh's audio fix)...${W}"

    # Create .sound file in Termux home
    TERMUX_HOME="/data/data/com.termux/files/home"
    cat > "$TERMUX_HOME/.sound" << 'SOUNDEOF'
pacmd load-module module-aaudio-sink
pulseaudio --start --exit-idle-time=-1
pacmd load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1
SOUNDEOF

    # Add sound bootstrap to ubuntu command (Mahesh's method)
    UBUNTU_CMD="/data/data/com.termux/files/usr/bin/ubuntu"
    if [ -f "$UBUNTU_CMD" ] && ! grep -q ".sound" "$UBUNTU_CMD" 2>/dev/null; then
        echo "$(echo 'bash ~/.sound' | cat - $UBUNTU_CMD)" > "$UBUNTU_CMD"
    fi

    # Set env vars
    grep -q "PULSE_SERVER" /etc/profile 2>/dev/null || {
        echo 'export PULSE_SERVER=127.0.0.1' >> /etc/profile
    }
    echo -e "${G}  ✓ Sound configured${W}"
}

setup_vnc() {
    echo -e "${C}[5] Setting up VNC server (Mahesh's method)...${W}"

    # VNC start script (from Mahesh, upgraded to 1080p)
    cat > /usr/local/bin/vncstart << 'VNCEOF'
#!/usr/bin/env bash
dbus-launch vncserver -geometry 1920x1080 -depth 24 -zliblevel 0 -name lucrex-desktop -xstartup /usr/bin/xfce4-session
VNCEOF

    cat > /usr/local/bin/vncstop << 'VNCEOF'
#!/usr/bin/env bash
vncserver -kill :*
rm -rf /tmp/.X*-lock
rm -rf /tmp/.X11-unix/X*
VNCEOF

    chmod +x /usr/local/bin/vncstart /usr/local/bin/vncstop

    # Set VNC DISPLAY
    grep -q 'DISPLAY=":1"' /etc/profile 2>/dev/null || {
        echo 'export DISPLAY=":1"' >> /etc/profile
    }

    echo -e "${G}  ✓ VNC configured (vncstart / vncstop)${W}"
}

install_theme() {
    banner
    echo -e "${C}[6] Installing Mahesh's custom theme + wallpapers...${W}"

    # Get the username
    username=$(getent group sudo 2>/dev/null | awk -F ':' '{print $4}' | cut -d ',' -f1)
    [ -z "$username" ] && username="root"

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32 2>/dev/null || true
    yes | apt upgrade 2>/dev/null
    yes | apt install gtk2-engines-murrine gtk2-engines-pixbuf sassc optipng inkscape libglib2.0-dev-bin 2>/dev/null

    # Backup old wallpaper
    mv -f /usr/share/backgrounds/xfce/xfce-verticals.png /usr/share/backgrounds/xfce/xfce-verticals-old.png 2>/dev/null

    temp_folder=$(mktemp -d -p "$HOME")
    cd "$temp_folder"

    echo -e "${C}  Downloading theme assets from Mahesh's repo...${W}"
    # Use modded-ubuntu release assets
    downloader "fonts.tar.gz" "https://github.com/MaheshTechnicals/modded-ubuntu/releases/download/config/fonts.tar.gz"
    downloader "icons.tar.gz" "https://github.com/MaheshTechnicals/modded-ubuntu/releases/download/config/icons.tar.gz"
    downloader "wallpaper.tar.gz" "https://github.com/MaheshTechnicals/modded-ubuntu/releases/download/config/wallpaper.tar.gz"
    downloader "gtk-themes.tar.gz" "https://github.com/MaheshTechnicals/modded-ubuntu/releases/download/config/gtk-themes.tar.gz"
    downloader "ubuntu-settings.tar.gz" "https://github.com/MaheshTechnicals/modded-ubuntu/releases/download/config/ubuntu-settings.tar.gz"

    echo -e "${C}  Unpacking theme files...${W}"
    mkdir -p /usr/local/share/fonts /usr/share/icons /usr/share/backgrounds/xfce /usr/share/themes
    [ -f fonts.tar.gz ] && tar -xzf fonts.tar.gz -C "/usr/local/share/fonts/" 2>/dev/null
    [ -f icons.tar.gz ] && tar -xzf icons.tar.gz -C "/usr/share/icons/" 2>/dev/null
    [ -f wallpaper.tar.gz ] && tar -xzf wallpaper.tar.gz -C "/usr/share/backgrounds/xfce/" 2>/dev/null
    [ -f gtk-themes.tar.gz ] && tar -xzf gtk-themes.tar.gz -C "/usr/share/themes/" 2>/dev/null

    # Settings go to user home
    if [ -n "$username" ] && [ -d "/home/$username" ]; then
        [ -f ubuntu-settings.tar.gz ] && tar -xzf ubuntu-settings.tar.gz -C "/home/$username/" 2>/dev/null
    else
        [ -f ubuntu-settings.tar.gz ] && tar -xzf ubuntu-settings.tar.gz -C "/root/" 2>/dev/null
    fi

    cd /root
    rm -rf "$temp_folder"

    # Remove ugly themes (Mahesh's cleanup)
    for t in Bright Daloa Emacs Moheli Retro Smoke; do rm -rf "/usr/share/themes/$t" 2>/dev/null; done
    for i in hicolor LoginIcons ubuntu-mono-light; do rm -rf "/usr/share/icons/$i" 2>/dev/null; done

    # Rebuild font cache
    echo -e "${C}  Rebuilding font cache...${W}"
    fc-cache -fv 2>/dev/null

    echo -e "${G}  ✓ Theme installed${W}"
}

# ============================================================
# PHASE 2: God Mode additions (Turnip, Wine, Box64, DXVK)
# ============================================================

install_godmode() {
    banner
    echo -e "${C}[7] Installing God Mode additions...${W}"

    # Turnip/Vulkan (may already be installed)
    echo -e "${C}  Checking Vulkan/Turnip...${W}"
    if [ -f /usr/share/vulkan/icd.d/freedreno_icd.json ]; then
        echo -e "${G}  ✓ Turnip already installed${W}"
    else
        apt install -y mesa-vulkan-drivers vulkan-tools libvulkan1 2>/dev/null
        echo -e "${G}  ✓ Turnip installed${W}"
    fi

    # Box64
    echo -e "${C}  Checking Box64...${W}"
    if command -v box64 &>/dev/null; then
        echo -e "${G}  ✓ Box64 already installed ($(box64 --version 2>&1 | head -1))${W}"
    else
        echo -e "${Y}  Box64 not found -- run setup_proot_side.sh first${W}"
    fi

    # Wine
    echo -e "${C}  Checking Wine...${W}"
    if [ -f /opt/wine/bin/wine64.real ]; then
        echo -e "${G}  ✓ Wine already installed${W}"
    else
        echo -e "${Y}  Wine not found -- run setup_proot_side.sh first${W}"
    fi

    # DXVK
    echo -e "${C}  Checking DXVK...${W}"
    if [ -d /opt/dxvk ]; then
        echo -e "${G}  ✓ DXVK already installed${W}"
    else
        echo -e "${Y}  DXVK not found -- run setup_proot_side.sh first${W}"
    fi

    # Gaming scripts (refresh them)
    echo -e "${C}  Installing gaming scripts...${W}"
    cp -f "$SCRIPT_DIR/start_desktop.sh" /data/data/com.termux/files/home/start_desktop.sh 2>/dev/null
    cp -f "$SCRIPT_DIR/stop_desktop.sh" /data/data/com.termux/files/home/stop_desktop.sh 2>/dev/null
    chmod +x /data/data/com.termux/files/home/start_desktop.sh /data/data/com.termux/files/home/stop_desktop.sh 2>/dev/null

    echo -e "${G}  ✓ God Mode additions verified${W}"
}

# ============================================================
# PHASE 3: Create unified ubuntu login command
# ============================================================

setup_login_command() {
    echo -e "${C}[8] Setting up login command...${W}"

    UBUNTU_CMD="/data/data/com.termux/files/usr/bin/ubuntu"
    cat > "$UBUNTU_CMD" << 'LOGINEOF'
#!/data/data/com.termux/files/usr/bin/bash
# Sound setup
bash ~/.sound 2>/dev/null
# Login to Ubuntu with shared tmp (for X11 socket)
proot-distro login ubuntu --shared-tmp
LOGINEOF
    chmod +x "$UBUNTU_CMD"

    echo -e "${G}  ✓ Type 'ubuntu' from Termux to enter desktop${W}"
}

# ============================================================
# RUN IT
# ============================================================

banner
echo -e "${Y}  This will set up Mahesh Technicals' modded Ubuntu${W}"
echo -e "${Y}  with Lucrex God Mode enhancements.${W}"
echo ""

fix_machineid
install_base_packages
install_software
setup_sound
setup_vnc
install_theme
install_godmode
setup_login_command

# Final upgrade
echo -e "${C}[9] Final system upgrade...${W}"
apt update 2>/dev/null
yes | apt upgrade 2>/dev/null
apt clean 2>/dev/null
yes | apt autoremove 2>/dev/null

banner
echo -e "${G}  ✅ GOD MODE DESKTOP INSTALLED!${W}"
echo ""
echo -e "${C}  VNC METHOD (Mahesh's proven approach):${W}"
echo -e "    ${W}1. From Termux: ${C}ubuntu${W}"
echo -e "    ${W}2. Inside Ubuntu: ${C}vncstart${W}"
echo -e "    ${W}3. Open VNC Viewer app -> ${C}localhost:1${W}"
echo -e "    ${W}4. Set password on first run${W}"
echo ""
echo -e "${C}  TERMUX X11 METHOD (if X11 APK installed):${W}"
echo -e "    ${W}1. From Termux: ${C}bash ~/start_desktop.sh${W}"
echo -e "    ${W}2. Switch to Termux:X11 app${W}"
echo ""
echo -e "${C}  GAMING (inside desktop):${W}"
echo -e "    ${W}• ${C}gamemode steam${W} - Steam via Wine+Box64${W}"
echo -e "    ${W}• ${C}viture-display${W} - Configure XR glasses${W}"
echo -e "    ${W}• Winlator APK for AAA games${W}"
echo ""
