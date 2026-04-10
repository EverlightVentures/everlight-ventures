#!/data/data/com.termux/files/usr/bin/bash
# Run this FROM TERMUX (not PRoot) to install remaining packages
# Only needed if virglrenderer-android install failed
echo "Installing remaining Termux packages..."
pkg install -y virglrenderer-android 2>/dev/null || echo "virglrenderer-android not available (OK - Turnip handles GPU)"
pkg install -y angle-android 2>/dev/null || true
echo "Done! All Termux packages installed."
