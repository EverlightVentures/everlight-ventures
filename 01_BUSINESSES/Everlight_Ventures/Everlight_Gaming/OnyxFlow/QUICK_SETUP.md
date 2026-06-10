# OnyxFlow - Quick Android Setup

## Automated Setup (Recommended)

Run this single command to set up everything:

```bash
sudo ./scripts/setup-android.sh
```

**What it does:**
- ✓ Installs Java JDK 21
- ✓ Installs Android Studio via Snap
- ✓ Configures environment variables
- ⚠ Launches Android Studio for you to complete setup

**Time:** ~5 minutes automated + 15 minutes manual (Android Studio wizard)

---

## Step-by-Step Instructions

### 1. Run the Setup Script

```bash
cd /home/mgn/Projects/OnyxFlow
sudo ./scripts/setup-android.sh
```

Enter your password when prompted.

### 2. Follow the Android Studio Wizard

The script will launch Android Studio. Follow these steps:

1. **Welcome Screen**: Click "Next"
2. **Install Type**: Choose "Standard"
3. **UI Theme**: Select your preference (Light/Dark)
4. **Verify Settings**: Click "Next"
5. **License Agreement**: Accept all licenses
6. **Downloading Components**: Wait (10-15 min) - downloads ~2GB
7. **Finish**: Click "Finish"

### 3. Create an Emulator

Once Android Studio is ready:

1. Click **Tools → Device Manager**
2. Click **Create Device**
3. Select **Pixel 6** → Click **Next**
4. Select **Tiramisu (API 33)** or **UpsideDownCake (API 34)**
5. If needed, click **Download** → Wait → Click **Next**
6. Name: `OnyxFlow_Emulator`
7. Click **Finish**

### 4. Verify Setup

Open a **NEW terminal** (important!) and run:

```bash
cd /home/mgn/Projects/OnyxFlow
./scripts/check-android-env.sh
```

You should see all green checkmarks ✓

### 5. Run OnyxFlow!

```bash
./scripts/run-android.sh
```

This will:
- Start the emulator (if needed)
- Launch Metro bundler
- Build and install the app
- Open OnyxFlow on the emulator

---

## Manual Setup (If Script Fails)

### Step 1: Install Java
```bash
sudo apt update
sudo apt install -y openjdk-21-jdk
java -version  # Verify
```

### Step 2: Install Android Studio
```bash
sudo snap install android-studio --classic
```

### Step 3: Add to ~/.bashrc
```bash
echo 'export ANDROID_HOME=$HOME/Android/Sdk' >> ~/.bashrc
echo 'export ANDROID_SDK_ROOT=$HOME/Android/Sdk' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/platform-tools' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/emulator' >> ~/.bashrc
source ~/.bashrc
```

### Step 4: Launch Android Studio
```bash
android-studio
```

Then follow steps 2-5 from above.

---

## Troubleshooting

### "command not found: android-studio"
**Solution**: Restart your terminal or run:
```bash
source ~/.bashrc
```

### "ANDROID_HOME is not set"
**Solution**: Open a NEW terminal (to reload environment variables)

### "No emulators found"
**Solution**: Create one in Android Studio: Tools → Device Manager → Create Device

### Script permission denied
**Solution**: Make it executable:
```bash
chmod +x ./scripts/setup-android.sh
```

---

## What Happens Next?

After setup completes:

1. **Emulator boots** (takes 1-2 minutes first time)
2. **App builds** (takes 3-5 minutes first time)
3. **OnyxFlow launches** on the emulator
4. **You can play the game!**

See `TESTING_GUIDE.md` for what to test.

---

## Quick Commands

```bash
# Setup (one time)
sudo ./scripts/setup-android.sh

# Check environment
./scripts/check-android-env.sh

# Run app
./scripts/run-android.sh

# Run tests
npm test

# View logs
adb logcat | grep OnyxFlow
```

---

## Timeline

- ☐ Run setup script: **2 min**
- ☐ Android Studio wizard: **15 min** (includes download)
- ☐ Create emulator: **3 min**
- ☐ First app build: **5 min**
- ✓ **Total: ~25 minutes**

Then you can play OnyxFlow! 🎮
