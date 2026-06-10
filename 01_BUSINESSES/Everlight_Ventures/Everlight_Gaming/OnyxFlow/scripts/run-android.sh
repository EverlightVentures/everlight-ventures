#!/bin/bash

# OnyxFlow - Quick Android Run Script
# This script helps you run the app on Android emulator

echo "================================================"
echo "   OnyxFlow - Android Quick Start"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Not in OnyxFlow project directory${NC}"
    echo "Please run this script from the project root."
    exit 1
fi

# Check if ADB is available
if ! command -v adb &> /dev/null; then
    echo -e "${RED}Error: ADB not found${NC}"
    echo "Please run: ./scripts/check-android-env.sh"
    echo "And follow the setup guide: ANDROID_SETUP.md"
    exit 1
fi

# Check for running emulators/devices
echo "Checking for Android devices..."
DEVICE_COUNT=$(adb devices | grep -v "List" | grep "device$" | wc -l)

if [ $DEVICE_COUNT -eq 0 ]; then
    echo -e "${YELLOW}No running Android devices found${NC}"
    echo ""
    echo "Available emulators:"

    if command -v emulator &> /dev/null; then
        AVD_LIST=$(emulator -list-avds 2>/dev/null)

        if [ -z "$AVD_LIST" ]; then
            echo -e "${RED}No emulators configured${NC}"
            echo "Please create one in Android Studio: Tools → Device Manager"
            exit 1
        fi

        echo "$AVD_LIST" | sed 's/^/  - /'
        echo ""

        # Ask if user wants to start an emulator
        read -p "Start an emulator? (y/n): " START_EMU

        if [ "$START_EMU" = "y" ] || [ "$START_EMU" = "Y" ]; then
            # If only one AVD, use it; otherwise ask
            AVD_COUNT=$(echo "$AVD_LIST" | wc -l)

            if [ $AVD_COUNT -eq 1 ]; then
                AVD_NAME="$AVD_LIST"
            else
                echo ""
                echo "Enter emulator name:"
                read AVD_NAME
            fi

            echo -e "${BLUE}Starting emulator: $AVD_NAME${NC}"
            emulator -avd "$AVD_NAME" &
            EMU_PID=$!

            echo "Waiting for emulator to boot..."
            adb wait-for-device

            # Wait for boot to complete
            while [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]; do
                sleep 2
                echo -n "."
            done
            echo ""
            echo -e "${GREEN}Emulator is ready!${NC}"
            echo ""
        else
            echo "Please start an emulator manually and run this script again."
            exit 0
        fi
    else
        echo -e "${RED}Emulator command not found${NC}"
        echo "Please check your Android SDK installation."
        exit 1
    fi
else
    echo -e "${GREEN}Found $DEVICE_COUNT Android device(s)${NC}"
    adb devices | grep "device$" | sed 's/^/  - /'
    echo ""
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found. Installing dependencies...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}npm install failed${NC}"
        exit 1
    fi
fi

# Ask if user wants to start Metro bundler in a new terminal
echo -e "${BLUE}Starting Metro bundler...${NC}"
echo ""

# Check if Metro is already running
if lsof -Pi :8081 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}Metro bundler is already running on port 8081${NC}"
else
    echo "Metro bundler will start in the background."
    echo "To view Metro logs, check the metro.log file."
    npm start > metro.log 2>&1 &
    METRO_PID=$!
    echo -e "${GREEN}Metro started (PID: $METRO_PID)${NC}"

    # Wait a bit for Metro to start
    sleep 3
fi

echo ""
echo -e "${BLUE}Building and running OnyxFlow on Android...${NC}"
echo "This may take a few minutes on first run."
echo ""

# Run the app
npm run android

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}   OnyxFlow is running!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "The app should now be open on your emulator/device."
    echo ""
    echo "To test the game:"
    echo "  1. Select a deck (Home/Work/Travel)"
    echo "  2. Start the 60-second game"
    echo "  3. Swipe cards left/right, hold for important ones"
    echo "  4. View your personalized checklist and roulette action"
    echo ""
    echo "To view live logs:"
    echo "  adb logcat | grep OnyxFlow"
    echo ""
    echo "To reload the app:"
    echo "  - Press 'r' in the Metro bundler"
    echo "  - Or shake the device and select 'Reload'"
else
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}   Build failed${NC}"
    echo -e "${RED}================================================${NC}"
    echo ""
    echo "Common fixes:"
    echo "  1. Clean build: cd android && ./gradlew clean && cd .."
    echo "  2. Reset Metro: npm start -- --reset-cache"
    echo "  3. Check logs above for specific errors"
fi

echo ""
