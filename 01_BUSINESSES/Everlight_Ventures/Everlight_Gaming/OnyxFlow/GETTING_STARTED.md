# OnyxFlow - Getting Started

Welcome back! This guide will help you pick up where we left off.

## What Was Completed Today ✓

### Core Features Implemented
1. **Held Cards Tracking** - Game now tracks which cards users mark as important
2. **Dynamic Checklist** - Generates personalized to-do list from held cards
3. **Smart Roulette** - Selects focused action based on held cards
4. **Type Safety** - Improved TypeScript type checking
5. **Unit Tests** - 11 tests covering all new functionality (all passing ✓)

### Documentation Created
- `ANDROID_SETUP.md` - Complete Android environment setup
- `TESTING_GUIDE.md` - How to test the app
- `PROJECT_STATUS.md` - Detailed project overview
- Helper scripts in `scripts/` directory

## Quick Start

### Option 1: Run Unit Tests (No Setup Required)

```bash
# Run all tests
npm test

# Run specific tests
npm test -- __tests__/GameEngine.test.ts

# Watch mode
npm test -- --watch
```

**All 11 tests should pass!**

### Option 2: Set Up Android & Run App

**Step 1: Check Your Environment**
```bash
./scripts/check-android-env.sh
```

**Step 2: Follow Setup If Needed**
If the check fails, follow: `ANDROID_SETUP.md`

Quick summary:
```bash
# Install Java
sudo apt install openjdk-21-jdk

# Install Android Studio
sudo snap install android-studio --classic

# Set environment variables (add to ~/.bashrc)
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
source ~/.bashrc
```

**Step 3: Run the App**
```bash
./scripts/run-android.sh
```

This script will:
- Check for running emulators
- Offer to start one if needed
- Launch Metro bundler
- Build and run OnyxFlow

## Testing the New Features

Once the app is running, test the complete flow:

### 1. Start a Game
- Select a deck (Home/Work/Travel)
- Tap "Start Game"

### 2. Play the Game (60 seconds)
- **Swipe Left**: Dismiss cards
- **Swipe Right**: Keep for later
- **Swipe Up/Hold**: Mark as important ⭐

**Important:** Pay attention to which cards you hold!

### 3. View Results
- Check your score
- Note how many cards you held

### 4. Check the Checklist ⭐ NEW
- Should show the exact cards you held
- Task cards → Show title + time estimate
- Photo cards → Show contextual action
- Verify items match what you held

### 5. Spin the Roulette ⭐ NEW
- Should show an action from one of your held cards
- High-priority tasks → "Complete..."
- Regular tasks → "Start..."
- Photos → "Organize..." or "Delete..."

## Project Structure

```
OnyxFlow/
├── GETTING_STARTED.md        ← You are here
├── ANDROID_SETUP.md           ← Android environment setup
├── TESTING_GUIDE.md           ← Comprehensive testing guide
├── PROJECT_STATUS.md          ← Detailed project status
│
├── src/
│   ├── services/game/
│   │   └── GameEngine.ts      ← Main game logic (updated today)
│   └── types/
│       └── game.ts            ← Type definitions (updated today)
│
├── __tests__/
│   └── GameEngine.test.ts     ← New test suite (created today)
│
└── scripts/
    ├── check-android-env.sh   ← Environment checker
    └── run-android.sh         ← Quick start script
```

## What's Next?

### Immediate Next Steps
1. **Set up Android environment** (30-60 min)
   - See `ANDROID_SETUP.md`
2. **Run the app** (5 min after setup)
   - Use `./scripts/run-android.sh`
3. **Manual testing** (15-20 min)
   - Follow `TESTING_GUIDE.md`

### Future Features (Optional)
- Photo library integration
- Database persistence (Realm)
- Authentication (Google Sign-In)
- In-app purchases
- More unit tests

See `PROJECT_STATUS.md` for the complete roadmap.

## Quick Commands Reference

```bash
# Environment check
./scripts/check-android-env.sh

# Run app (if environment ready)
./scripts/run-android.sh

# Run tests
npm test

# Lint code
npm run lint

# View Android logs
adb logcat | grep OnyxFlow

# List emulators
emulator -list-avds

# Start specific emulator
emulator -avd <emulator-name> &
```

## Need Help?

### Environment Issues
1. Run: `./scripts/check-android-env.sh`
2. Check: `ANDROID_SETUP.md` troubleshooting section
3. Verify: `adb devices` shows your emulator

### App Issues
1. Check logs: `adb logcat | grep OnyxFlow`
2. Reset Metro: `npm start -- --reset-cache`
3. Clean build: `cd android && ./gradlew clean && cd ..`

### Test Failures
1. Run: `npm test -- --verbose`
2. Check: Node version (`node --version` should be 16+)
3. Clear cache: `npm test -- --clearCache`

## What You Can Test Right Now

**Without Android setup:**
- ✓ Run unit tests
- ✓ Review code
- ✓ Check TypeScript types
- ✓ Read documentation

**With Android setup:**
- ✓ Play the full game
- ✓ Test checklist generation
- ✓ Test roulette selection
- ✓ Verify UI/UX
- ✓ Test performance

## Summary

**OnyxFlow is 70-80% complete!**

✅ **Working:**
- Complete 60-second game mechanics
- Dynamic checklist from held cards
- Smart roulette action selection
- Scoring, combos, streaks, rewards
- 11 passing unit tests

⏳ **Pending:**
- Android environment setup (your action required)
- Manual testing on device
- Photo library integration
- Backend persistence

**Next session:** Follow the Android setup guide and run the app to see your work in action!

---

**Welcome back and happy testing!** 🎮
