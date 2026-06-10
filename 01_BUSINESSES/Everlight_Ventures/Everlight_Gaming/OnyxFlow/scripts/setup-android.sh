#!/bin/bash

# OnyxFlow - Automated Android Setup Script
# This script automates the Android development environment setup

set -e  # Exit on error

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "================================================"
echo "   OnyxFlow - Android Setup Automation"
echo "================================================"
echo ""
echo "This script will install:"
echo "  1. Java JDK 21"
echo "  2. Android Studio"
echo "  3. Configure environment variables"
echo ""
echo "Some steps require manual interaction."
echo "Please follow the prompts."
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script needs sudo privileges.${NC}"
    echo "Please run with: sudo ./scripts/setup-android.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo -e "${BLUE}Installing for user: $ACTUAL_USER${NC}"
echo -e "${BLUE}Home directory: $ACTUAL_HOME${NC}"
echo ""

# ==============================================
# STEP 1: Install Java JDK
# ==============================================
echo "================================================"
echo "STEP 1: Installing Java JDK 21"
echo "================================================"

if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1)
    echo -e "${YELLOW}Java is already installed: $JAVA_VERSION${NC}"
    read -p "Reinstall anyway? (y/n): " REINSTALL_JAVA
    if [ "$REINSTALL_JAVA" != "y" ]; then
        echo "Skipping Java installation."
    else
        apt update
        apt install -y openjdk-21-jdk
    fi
else
    echo "Installing Java JDK 21..."
    apt update
    apt install -y openjdk-21-jdk
fi

# Verify Java installation
if java -version 2>&1 | grep -q "openjdk"; then
    echo -e "${GREEN}✓ Java installed successfully${NC}"
    java -version 2>&1 | head -3
else
    echo -e "${RED}✗ Java installation failed${NC}"
    exit 1
fi

echo ""

# ==============================================
# STEP 2: Install Android Studio
# ==============================================
echo "================================================"
echo "STEP 2: Installing Android Studio"
echo "================================================"

if command -v android-studio &> /dev/null || [ -f "$ACTUAL_HOME/android-studio/bin/studio.sh" ]; then
    echo -e "${YELLOW}Android Studio appears to be installed${NC}"
    read -p "Reinstall anyway? (y/n): " REINSTALL_AS
    if [ "$REINSTALL_AS" != "y" ]; then
        echo "Skipping Android Studio installation."
    else
        snap install android-studio --classic
    fi
else
    echo "Installing Android Studio via Snap..."
    snap install android-studio --classic
fi

# Verify Android Studio installation
if command -v android-studio &> /dev/null; then
    echo -e "${GREEN}✓ Android Studio installed successfully${NC}"
else
    echo -e "${RED}✗ Android Studio installation failed${NC}"
    exit 1
fi

echo ""

# ==============================================
# STEP 3: Setup Environment Variables
# ==============================================
echo "================================================"
echo "STEP 3: Setting Up Environment Variables"
echo "================================================"

BASHRC="$ACTUAL_HOME/.bashrc"
ANDROID_SDK_PATH="$ACTUAL_HOME/Android/Sdk"

# Check if variables already exist
if grep -q "ANDROID_HOME" "$BASHRC"; then
    echo -e "${YELLOW}Android environment variables already exist in .bashrc${NC}"
    read -p "Update anyway? (y/n): " UPDATE_ENV
    if [ "$UPDATE_ENV" != "y" ]; then
        echo "Skipping environment variable setup."
    else
        # Remove old entries
        sed -i '/ANDROID_HOME/d' "$BASHRC"
        sed -i '/ANDROID_SDK_ROOT/d' "$BASHRC"
    fi
fi

# Add environment variables
echo "" >> "$BASHRC"
echo "# Android SDK - Added by OnyxFlow setup script" >> "$BASHRC"
echo "export ANDROID_HOME=\$HOME/Android/Sdk" >> "$BASHRC"
echo "export ANDROID_SDK_ROOT=\$HOME/Android/Sdk" >> "$BASHRC"
echo "export PATH=\$PATH:\$ANDROID_HOME/emulator" >> "$BASHRC"
echo "export PATH=\$PATH:\$ANDROID_HOME/platform-tools" >> "$BASHRC"
echo "export PATH=\$PATH:\$ANDROID_HOME/cmdline-tools/latest/bin" >> "$BASHRC"
echo "export PATH=\$PATH:\$ANDROID_HOME/tools" >> "$BASHRC"
echo "export PATH=\$PATH:\$ANDROID_HOME/tools/bin" >> "$BASHRC"

# Fix ownership
chown $ACTUAL_USER:$ACTUAL_USER "$BASHRC"

echo -e "${GREEN}✓ Environment variables added to .bashrc${NC}"
echo ""

# Export for current session
export ANDROID_HOME="$ANDROID_SDK_PATH"
export ANDROID_SDK_ROOT="$ANDROID_SDK_PATH"

echo ""

# ==============================================
# MANUAL STEPS REQUIRED
# ==============================================
echo "================================================"
echo "AUTOMATED SETUP COMPLETE!"
echo "================================================"
echo ""
echo -e "${GREEN}✓ Java JDK 21 installed${NC}"
echo -e "${GREEN}✓ Android Studio installed${NC}"
echo -e "${GREEN}✓ Environment variables configured${NC}"
echo ""
echo "================================================"
echo "NEXT STEPS (MANUAL)"
echo "================================================"
echo ""
echo -e "${CYAN}STEP 4: Configure Android Studio${NC}"
echo "  1. Close this terminal and open a NEW one (to load env vars)"
echo "  2. Run: android-studio"
echo "  3. Follow the setup wizard:"
echo "     - Choose 'Standard' installation"
echo "     - Select your preferred theme"
echo "     - Accept all licenses"
echo "     - Wait for SDK download (10-15 minutes)"
echo "  4. Click 'Finish' when done"
echo ""
echo -e "${CYAN}STEP 5: Create Android Virtual Device (AVD)${NC}"
echo "  1. In Android Studio, go to: Tools → Device Manager"
echo "  2. Click 'Create Device'"
echo "  3. Select 'Pixel 6' (or any recent device)"
echo "  4. Click 'Next'"
echo "  5. Select 'Tiramisu' (API 33) or 'UpsideDownCake' (API 34)"
echo "  6. Click 'Download' if needed, then 'Next'"
echo "  7. Name it 'OnyxFlow_Emulator'"
echo "  8. Click 'Finish'"
echo ""
echo -e "${CYAN}STEP 6: Run OnyxFlow${NC}"
echo "  1. Open a NEW terminal (important for env vars)"
echo "  2. cd /home/mgn/Projects/OnyxFlow"
echo "  3. Run: ./scripts/run-android.sh"
echo ""
echo "================================================"
echo ""
echo "After completing these steps, verify with:"
echo "  ./scripts/check-android-env.sh"
echo ""
echo "Need help? See ANDROID_SETUP.md for detailed instructions."
echo ""
echo -e "${YELLOW}Press ENTER to launch Android Studio now...${NC}"
read

# Launch Android Studio as the actual user
su - $ACTUAL_USER -c "android-studio &"

echo ""
echo -e "${GREEN}Android Studio launched!${NC}"
echo "Follow the setup wizard, then come back to run the app."
echo ""
