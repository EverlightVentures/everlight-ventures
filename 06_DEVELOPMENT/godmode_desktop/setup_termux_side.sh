#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# PHASE 1: Termux-side setup (run FROM Termux, not PRoot)
# Installs: x11-repo, termux-x11, pulseaudio, virglrenderer
# ============================================================
set -e

echo "========================================"
echo "  LUCREX GOD MODE DESKTOP - Termux Side"
echo "========================================"

echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "[2/6] Installing x11-repo (gives us Termux X11 packages)..."
pkg install -y x11-repo

echo "[3/6] Installing Termux X11 nightly + display deps..."
pkg install -y termux-x11-nightly
pkg install -y xorg-xrandr xorg-xsetroot

echo "[4/6] Installing PulseAudio for audio bridge..."
pkg install -y pulseaudio

echo "[5/6] Installing VirGL renderer (OpenGL passthrough)..."
pkg install -y virglrenderer-android

echo "[6/6] Installing utilities..."
pkg install -y wget git proot-distro

echo ""
echo "========================================"
echo "  Termux side DONE!"
echo "  Now open Termux X11 app once (just open and close it)"
echo "  Then run: proot-distro login ubuntu -- bash /root/setup_proot_side.sh"
echo "========================================"
