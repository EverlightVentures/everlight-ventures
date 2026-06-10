# Android Environment Setup Guide

This guide will help you set up your Android development environment to run OnyxFlow.

## Prerequisites Check

Run this command to check what's already installed:
```bash
./scripts/check-android-env.sh
```

## Step 1: Install Java JDK 21

```bash
sudo apt update
sudo apt install -y openjdk-21-jdk
```

Verify installation:
```bash
java -version
# Should show: openjdk version "21.x.x"
```

## Step 2: Install Android Studio

### Option A: Snap Install (Recommended - Easiest)
```bash
sudo snap install android-studio --classic
```

### Option B: Manual Install
1. Download from https://developer.android.com/studio
2. Extract and install:
```bash
cd ~/Downloads
tar -xzf android-studio-*.tar.gz -C ~/
~/android-studio/bin/studio.sh
```

## Step 3: Android Studio Initial Setup

1. **Launch Android Studio**
   ```bash
   android-studio
   # or if manually installed:
   ~/android-studio/bin/studio.sh
   ```

2. **Welcome Screen**: Click "Next"

3. **Install Type**: Choose "Standard" (installs SDK, emulator, etc.)

4. **Theme**: Choose your preference (Light/Dark)

5. **Verify Settings**: Review and click "Next"

6. **License Agreement**: Accept all licenses

7. **Download Components**: Wait for SDK download (this takes 10-15 minutes)

8. **Finish**: Click "Finish"

## Step 4: Configure Android SDK

1. In Android Studio, go to: **Tools → SDK Manager**

2. **SDK Platforms Tab**:
   - ✓ Android 14.0 (API 34) - Recommended
   - ✓ Android 13.0 (API 33)

3. **SDK Tools Tab**:
   - ✓ Android SDK Build-Tools
   - ✓ Android Emulator
   - ✓ Android SDK Platform-Tools
   - ✓ Android SDK Command-line Tools (latest)
   - ✓ Intel x86 Emulator Accelerator (HAXM) - if on Intel CPU

4. Click **Apply** and wait for downloads

## Step 5: Set Environment Variables

Add these to your shell config file (`~/.bashrc` or `~/.zshrc`):

```bash
# Android SDK
export ANDROID_HOME=$HOME/Android/Sdk
export ANDROID_SDK_ROOT=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
```

Apply the changes:
```bash
source ~/.bashrc
# or
source ~/.zshrc
```

## Step 6: Verify Installation

```bash
# Check ADB
adb --version
# Should show: Android Debug Bridge version x.x.x

# Check emulator
emulator -list-avds
# Should list available virtual devices

# Check SDK
sdkmanager --list | grep "system-images" | head -5
```

## Step 7: Create Android Virtual Device (AVD)

### Option A: Using Android Studio GUI
1. Open Android Studio
2. Click **Tools → Device Manager**
3. Click **Create Device**
4. Select **Phone → Pixel 6** (or any recent device)
5. Click **Next**
6. Select **System Image**: Choose **Tiramisu (API 33)** or **UpsideDownCake (API 34)**
7. Click **Download** if needed, then **Next**
8. Name it "OnyxFlow_Emulator"
9. Click **Finish**

### Option B: Using Command Line
```bash
# List available system images
sdkmanager --list | grep system-images

# Install a system image (example: API 33)
sdkmanager "system-images;android-33;google_apis;x86_64"

# Create AVD
avdmanager create avd -n OnyxFlow_Emulator -k "system-images;android-33;google_apis;x86_64" -d "pixel_6"
```

## Step 8: Start the Emulator

### Option A: From Android Studio
1. Open Device Manager
2. Click the **Play** button next to "OnyxFlow_Emulator"

### Option B: From Command Line
```bash
emulator -avd OnyxFlow_Emulator
```

## Step 9: Run OnyxFlow App

Once the emulator is running:

```bash
# Navigate to project
cd /home/mgn/Projects/OnyxFlow

# Start Metro bundler in one terminal
npm start

# In another terminal, run on Android
npm run android
```

Or use the quick start script:
```bash
./scripts/run-android.sh
```

## Troubleshooting

### Issue: "SDK location not found"
**Solution**: Make sure ANDROID_HOME is set correctly:
```bash
echo $ANDROID_HOME
# Should output: /home/mgn/Android/Sdk
```

### Issue: "adb: command not found"
**Solution**:
```bash
source ~/.bashrc  # Reload environment variables
which adb  # Should show path to adb
```

### Issue: Emulator won't start
**Solution**:
```bash
# Check virtualization is enabled
egrep -c '(vmx|svm)' /proc/cpuinfo
# Should be > 0

# Try starting with more RAM
emulator -avd OnyxFlow_Emulator -memory 2048
```

### Issue: "No connected devices"
**Solution**:
```bash
# List devices
adb devices

# If empty, restart ADB
adb kill-server
adb start-server
adb devices
```

### Issue: Build fails with "SDK not found"
**Solution**: Create `local.properties` in android folder:
```bash
echo "sdk.dir=/home/mgn/Android/Sdk" > android/local.properties
```

## Quick Reference Commands

```bash
# Check environment
./scripts/check-android-env.sh

# List emulators
emulator -list-avds

# Start emulator
emulator -avd OnyxFlow_Emulator &

# List connected devices
adb devices

# Run app
npm run android

# View logs
adb logcat | grep OnyxFlow

# Uninstall app
adb uninstall com.onyxflow

# Restart Metro bundler
npm start -- --reset-cache
```

## Next Steps

After setup is complete, see `RUNNING_THE_APP.md` for how to test the game functionality.
