# OnyxFlow

> **Swipe into focus — luxury in a minute**

OnyxFlow is a premium 60-second productivity game for Android. Make quick decisions, build daily streaks, and unlock achievements in a beautifully designed luxury experience.

---

## 🎮 Features

### Core Gameplay
- **60-Second Sessions** - Quick, focused decision-making rounds
- **Swipe Mechanics** - Left (delete), Right (keep), Hold (prioritize)
- **4 Premium Decks** - Photos, Home, Work, Travel
- **Decision Roulette** - Spinning wheel selects action from held items
- **Smart Checklist** - Auto-generated 3-item action list
- **5-Minute Sprint** - Focus timer after each game

### Progression System
- **Daily Streaks** - Build consecutive day chains with shield protection
- **19 Achievements** - Unlock rewards across 4 categories
- **Token Economy** - Earn tokens, spend on shields and cosmetics
- **Milestone Rewards** - Special bonuses at streak days 3/7/14/30
- **Daily Rewards** - 7-day cycle with increasing token rewards

### Premium Features
- **OnyxFlow+ Subscription** - Ad-free, unlimited sessions, SmartFlow AI
- **7 IAP Packs** - $2.49 to $129.99 for tokens, decks, shields
- **Google AdMob** - Banner and interstitial ads for free users
- **Rewarded Ads** - Watch ads to earn bonus tokens/shields

### Polish & UX
- **60fps Animations** - Smooth Reanimated 3 throughout
- **Particle Effects** - Confetti and sparkles for celebrations
- **Haptic Feedback** - Rich tactile responses
- **Luxury Design** - Onyx black, champagne gold, premium gradients
- **Dark Theme** - Elegant, eye-friendly interface

---

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Android Studio
- Android SDK & emulator
- Java JDK 17+

### Installation

1. **Install dependencies**
   ```bash
   npm install --legacy-peer-deps
   ```

2. **Start Metro bundler**
   ```bash
   npm start
   ```

3. **Run on Android** (new terminal)
   ```bash
   npx react-native run-android
   ```

The app will build and launch on your emulator/device.

---

## 📂 Project Structure

```
src/
├── components/
│   ├── atoms/           # Button, Card, Text, Icon, ParticleEffect
│   ├── molecules/       # SwipeCard, TokenDisplay, AchievementToast, AdBanner
│   └── organisms/       # GameBoard, DecisionRoulette, Checklist, DailyRewardModal
├── screens/
│   ├── game/            # HomeScreen, GameScreen, ResultsScreen, RouletteScreen
│   └── profile/         # StatsScreen, AchievementsScreen
├── services/
│   ├── game/            # GameEngine, CardGenerator, StreakManager, ScoreCalculator
│   └── monetization/    # AdService
├── store/               # Zustand stores (gameStore, userStore)
├── navigation/          # AppNavigator, stack/tab navigators
├── hooks/               # useAnimatedPress
├── config/              # theme, constants, products, achievements, ads, animations
└── types/               # TypeScript definitions
```

---

## 🧪 Testing

See [TESTING.md](./TESTING.md) for comprehensive testing checklist.

**Quick Smoke Test:**
1. Launch app → HomeScreen loads
2. Tap "Play 60s" → Game starts
3. Swipe cards → Score updates
4. Timer hits 0 → Results screen
5. Check achievements → First Flow unlocked
6. Check ads → Banner on home (free users)

---

## 📈 Tech Stack

- React Native 0.83.1 + TypeScript
- Zustand (state management)
- React Navigation (routing)
- Reanimated 3 (animations)
- Google Mobile Ads (monetization)
- MMKV + Realm (storage)

---

## 🔧 Configuration

### AdMob Setup (Production)

Current setup uses Google test ad IDs for development.

**For production:**
1. Create AdMob account at https://admob.google.com
2. Create app and ad units (banner, interstitial, rewarded)
3. Update `src/config/ads.ts` with production IDs
4. Update `android/app/src/main/AndroidManifest.xml` with production App ID

---

## 📦 Build for Production

```bash
# Build release AAB
cd android
./gradlew bundleRelease

# Output: android/app/build/outputs/bundle/release/app-release.aab
```

---

## 🎯 What's Implemented

✅ 60-second swipe game with timer
✅ Score calculation with 6 multipliers
✅ Decision Roulette with animations
✅ 3-item Checklist with 5-min sprint
✅ Daily streak tracking with shields
✅ 19 achievements with unlock system
✅ Daily reward 7-day cycle
✅ Token economy (earn/spend)
✅ Stats & achievements screens
✅ Google AdMob integration
✅ Subscription logic (ad removal)
✅ Particle effects (confetti/sparkles)
✅ Premium animations (60fps)
✅ Haptic feedback

---

## 🚧 Future Features

- Google Sign-In & cloud sync
- In-App Purchase implementation
- Photos deck (camera roll access)
- ML-powered suggestions
- Social sharing (score cards)

---

## 📄 License

Copyright © 2025 OnyxFlow. All rights reserved.

---

**Ready to swipe into focus?** 🚀

```bash
npm start
npx react-native run-android
```
