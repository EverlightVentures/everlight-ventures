#!/bin/bash

# OnyxFlow - Android Environment Check Script
# This script checks if your Android development environment is properly configured

echo "================================================"
echo "   OnyxFlow - Android Environment Check"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2 is installed"
        if [ "$3" != "" ]; then
            echo "  Version: $($3 2>&1 | head -1)"
        fi
        return 0
    else
        echo -e "${RED}✗${NC} $2 is NOT installed"
        return 1
    fi
}

# Check environment variable
check_env_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}✗${NC} $1 is NOT set"
        return 1
    else
        echo -e "${GREEN}✓${NC} $1 is set"
        echo "  Path: ${!1}"
        return 0
    fi
}

# Check if path exists
check_path() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2 exists"
        echo "  Path: $1"
        return 0
    else
        echo -e "${RED}✗${NC} $2 does NOT exist"
        echo "  Expected: $1"
        return 1
    fi
}

ALL_GOOD=true

# 1. Check Java
echo "1. Checking Java JDK..."
if check_command java "Java" "java -version"; then
    :
else
    echo -e "  ${YELLOW}Install:${NC} sudo apt install openjdk-21-jdk"
    ALL_GOOD=false
fi
echo ""

# 2. Check Android Studio
echo "2. Checking Android Studio..."
if check_command android-studio "Android Studio" || [ -f "$HOME/android-studio/bin/studio.sh" ]; then
    echo -e "${GREEN}✓${NC} Android Studio is installed"
else
    echo -e "${RED}✗${NC} Android Studio is NOT installed"
    echo -e "  ${YELLOW}Install:${NC} sudo snap install android-studio --classic"
    ALL_GOOD=false
fi
echo ""

# 3. Check Environment Variables
echo "3. Checking Environment Variables..."
check_env_var "ANDROID_HOME" || ALL_GOOD=false
check_env_var "ANDROID_SDK_ROOT" || ALL_GOOD=false
echo ""

# 4. Check Android SDK
echo "4. Checking Android SDK..."
if [ -n "$ANDROID_HOME" ]; then
    check_path "$ANDROID_HOME" "Android SDK" || ALL_GOOD=false
    check_path "$ANDROID_HOME/platform-tools" "Platform Tools" || ALL_GOOD=false
    check_path "$ANDROID_HOME/emulator" "Emulator" || ALL_GOOD=false
else
    echo -e "${YELLOW}⚠${NC}  Skipping (ANDROID_HOME not set)"
    ALL_GOOD=false
fi
echo ""

# 5. Check Android Tools
echo "5. Checking Android Command-Line Tools..."
check_command adb "ADB (Android Debug Bridge)" "adb --version" || ALL_GOOD=false
check_command emulator "Android Emulator" || ALL_GOOD=false
echo ""

# 6. Check for AVDs
echo "6. Checking Android Virtual Devices (AVDs)..."
if command -v emulator &> /dev/null; then
    AVD_COUNT=$(emulator -list-avds 2>/dev/null | wc -l)
    if [ $AVD_COUNT -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $AVD_COUNT emulator(s):"
        emulator -list-avds 2>/dev/null | sed 's/^/  - /'
    else
        echo -e "${YELLOW}⚠${NC}  No emulators configured"
        echo "  Create one in Android Studio: Tools → Device Manager"
        ALL_GOOD=false
    fi
else
    echo -e "${YELLOW}⚠${NC}  Cannot check (emulator command not available)"
fi
echo ""

# 7. Check Node.js and npm
echo "7. Checking Node.js Environment..."
check_command node "Node.js" "node --version" || ALL_GOOD=false
check_command npm "npm" "npm --version" || ALL_GOOD=false
echo ""

# 8. Check React Native dependencies
echo "8. Checking OnyxFlow Project..."
if [ -f "package.json" ]; then
    echo -e "${GREEN}✓${NC} package.json found"
    if [ -d "node_modules" ]; then
        echo -e "${GREEN}✓${NC} node_modules exists"
    else
        echo -e "${YELLOW}⚠${NC}  node_modules not found"
        echo -e "  ${YELLOW}Run:${NC} npm install"
        ALL_GOOD=false
    fi
else
    echo -e "${RED}✗${NC} Not in OnyxFlow project directory"
    ALL_GOOD=false
fi
echo ""

# Summary
echo "================================================"
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✓ All checks passed! You're ready to run the app.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start an emulator: emulator -avd <name> &"
    echo "  2. Run the app: npm run android"
    echo ""
    echo "Or use the quick start script:"
    echo "  ./scripts/run-android.sh"
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    echo ""
    echo "See ANDROID_SETUP.md for detailed setup instructions."
fi
echo "================================================"
