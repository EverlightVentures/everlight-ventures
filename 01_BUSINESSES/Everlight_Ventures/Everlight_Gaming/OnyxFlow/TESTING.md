# OnyxFlow Testing Guide

## Prerequisites

- ✅ Node.js 20+ installed
- ✅ Android Studio installed
- ✅ Android SDK and emulator configured
- ✅ Java JDK 17+ installed

## Quick Start

### 1. Start Metro Bundler

```bash
npm start
```

### 2. Run on Android (in a new terminal)

```bash
npx react-native run-android
```

The app will build and launch on your Android emulator/device.

---

## Testing Checklist

### ✅ Core Game Flow

1. **Launch App**
   - [ ] App opens to HomeScreen
   - [ ] No crashes on startup
   - [ ] AdMob initializes (check console logs)

2. **HomeScreen**
   - [ ] Token balance shows (0 for new user)
   - [ ] Streak counter displays
   - [ ] "Play 60s" button visible
   - [ ] Banner ad shows at bottom (free users only)

3. **Start Game**
   - [ ] Tap "Play 60s" button
   - [ ] GameScreen loads with cards
   - [ ] Timer shows 60 seconds
   - [ ] Score displays as 0

4. **Swipe Mechanics**
   - [ ] Swipe card left → card animates left, next card appears
   - [ ] Swipe card right → card animates right, next card appears
   - [ ] Long press (hold) → card highlights, adds to checklist
   - [ ] Haptic feedback on each swipe
   - [ ] Score increases with each swipe
   - [ ] Timer counts down

5. **Game Completion**
   - [ ] Timer reaches 0
   - [ ] Interstitial ad shows (every 3rd game for free users)
   - [ ] ResultsScreen displays
   - [ ] Final score shown
   - [ ] Cards processed count
   - [ ] Max combo displayed

6. **Results Screen**
   - [ ] All animations stagger in smoothly
   - [ ] "View Roulette" button if action selected
   - [ ] Checklist preview shows
   - [ ] "Start 5-Min Sprint" button works
   - [ ] "Play Again" button works
   - [ ] "Go Home" button works

7. **Decision Roulette**
   - [ ] Wheel spins automatically
   - [ ] Lands on selected action
   - [ ] Action highlights
   - [ ] Haptic feedback on land
   - [ ] "Start Sprint" navigates to checklist

8. **Checklist Screen**
   - [ ] Shows 3 items from game
   - [ ] 5-minute timer starts
   - [ ] Can tap items to complete
   - [ ] Progress bar updates
   - [ ] Completion celebration when all done

---

### ✅ Streaks & Achievements

9. **Daily Streak**
   - [ ] Play game → streak increments
   - [ ] Streak counter updates on HomeScreen
   - [ ] Shield icon shows if shields available

10. **Achievements**
    - [ ] First game unlocks "First Flow" achievement
    - [ ] Achievement toast slides in from top
    - [ ] Tokens awarded for achievement
    - [ ] Achievement shows in Stats screen

11. **Stats Screen**
    - [ ] Navigate to Profile → Stats
    - [ ] Shows total games, high score, avg score
    - [ ] Streak information displays
    - [ ] Achievement progress shown
    - [ ] All animations work

12. **Achievements Screen**
    - [ ] Shows all 19 achievements
    - [ ] Category filters work (All, Games, Streaks, Score, Special)
    - [ ] Locked achievements show progress bar
    - [ ] Unlocked achievements show timestamp

---

### ✅ Daily Rewards

13. **Daily Reward System**
    - [ ] Tap "Daily Reward" on HomeScreen
    - [ ] Modal shows 7-day calendar
    - [ ] Current day highlights
    - [ ] Can claim today's reward
    - [ ] Sparkle particles appear on claim
    - [ ] Tokens added to balance
    - [ ] Shield added if day 3/6/7
    - [ ] Next reward shows countdown

---

### ✅ Monetization

14. **Ads (Free Users)**
    - [ ] Banner ad shows on HomeScreen
    - [ ] Interstitial ad after 3rd game
    - [ ] Minimum 3 minutes between interstitials
    - [ ] Ads use Google test IDs
    - [ ] No crashes from ads

15. **Subscription Logic**
    - [ ] Free users see ads
    - [ ] When isPlusSubscriber = true:
      - [ ] No banner ads
      - [ ] No interstitial ads
      - [ ] Daily rewards show "OnyxFlow+ 50% Bonus" badge

---

### ✅ Visual Polish

16. **Animations**
    - [ ] HomeScreen elements fade in staggered
    - [ ] ResultsScreen zooms/fades in
    - [ ] MilestoneModal shows confetti particles
    - [ ] Card swipes are smooth (60fps)
    - [ ] Button presses have scale feedback

17. **Haptics**
    - [ ] Swipe feedback
    - [ ] Achievement unlock
    - [ ] Daily reward claim
    - [ ] Checklist item complete
    - [ ] Game completion

---

## Common Issues & Solutions

### Issue: App won't build
```bash
# Clear build cache
cd android
./gradlew clean
cd ..
npm start -- --reset-cache
npx react-native run-android
```

### Issue: Metro bundler errors
```bash
# Kill existing Metro
pkill -f "react-native"
# Restart
npm start -- --reset-cache
```

### Issue: AdMob errors
- Check AndroidManifest.xml has AdMob App ID
- Verify internet permission in manifest
- Test IDs should work without AdMob account

### Issue: Navigation errors
- Ensure all screens are properly registered
- Check navigation types match routes

---

## Performance Testing

### Expected Performance
- [ ] App starts in < 3 seconds
- [ ] 60fps animations throughout
- [ ] No frame drops during swipes
- [ ] Smooth particle effects
- [ ] No memory leaks after 10+ games

### Check Console for:
- ✅ "AdMob initialized"
- ✅ "AdService initialized"
- ✅ No red errors
- ⚠️ Yellow warnings are OK

---

## Production Checklist (Before Play Store)

### Required Changes:
1. **AdMob Production IDs**
   - Create AdMob account
   - Create app in AdMob console
   - Replace test IDs in `src/config/ads.ts`
   - Replace test App ID in `AndroidManifest.xml`

2. **In-App Purchases**
   - Set up products in Google Play Console
   - Match IDs in `src/config/products.ts`
   - Implement IAP service (react-native-iap)

3. **Build Configuration**
   - Update version in package.json
   - Create release keystore
   - Configure signing in android/app/build.gradle
   - Generate release AAB

4. **Assets**
   - App icon (512x512 for Play Store)
   - Screenshots (phone & tablet)
   - Feature graphic (1024x500)
   - Privacy policy URL

---

## Success Metrics

### Game is Ready When:
- ✅ All 60+ features work
- ✅ No crashes during 10 consecutive games
- ✅ Ads display correctly
- ✅ Subscription logic verified
- ✅ Achievements unlock properly
- ✅ Daily rewards cycle works
- ✅ Animations run at 60fps
- ✅ Haptics work on physical device

---

## Next Steps After Testing

1. Fix any bugs found
2. Get production AdMob IDs
3. Set up Google Play Console
4. Create store assets
5. Build release AAB
6. Submit to Play Store
7. 🚀 Launch!
