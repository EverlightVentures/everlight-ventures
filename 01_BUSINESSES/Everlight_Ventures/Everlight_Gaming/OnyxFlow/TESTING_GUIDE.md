# OnyxFlow - Testing Guide

This guide will help you test the complete OnyxFlow game functionality, including the newly implemented checklist and roulette features.

## Quick Test Workflow

```bash
# 1. Check environment
./scripts/check-android-env.sh

# 2. Run the app (if environment is ready)
./scripts/run-android.sh

# 3. Run unit tests
npm test
```

## Unit Testing (No Device Required)

### Run All Tests
```bash
npm test
```

### Run Specific Test Suites
```bash
# GameEngine tests (checklist & roulette)
npm test -- __tests__/GameEngine.test.ts

# Watch mode for development
npm test -- --watch

# With coverage
npm test -- --coverage
```

### What's Tested
- ✓ Game session creation and initialization
- ✓ Held cards tracking (swipe up/hold)
- ✓ Dynamic checklist generation from held cards
- ✓ Roulette action selection from held cards
- ✓ Scoring system with combos and multipliers
- ✓ Card type handling (task, photo, decision)

## Manual Testing on Emulator/Device

### 1. Pre-Launch Setup

Make sure you have:
- Android emulator running OR physical device connected
- Metro bundler running (`npm start`)
- App installed (`npm run android`)

### 2. Test the Complete Game Flow

#### A. Home Screen
**Expected Behavior:**
- [ ] See three deck options: Home, Work, Travel
- [ ] Each deck shows a description
- [ ] "Start Game" button is visible and enabled

**Actions:**
1. Tap on "Home" deck
2. Tap "Start Game"

#### B. Game Screen (60-second session)
**Expected Behavior:**
- [ ] Timer starts counting down from 60 seconds
- [ ] Cards appear one at a time
- [ ] Swipe gestures work smoothly
- [ ] Score updates in real-time
- [ ] Combo counter shows when building combos

**Actions:**
1. **Swipe Left** on 3-5 cards (dismiss/delete)
2. **Swipe Right** on 3-5 cards (keep/later)
3. **Swipe Up/Hold** on 3-5 cards (mark as important)
   - 🎯 **KEY**: These held cards should appear in your checklist!
4. Note which cards you held (e.g., "Clean kitchen", "Review emails")
5. Let timer run out OR process all cards

#### C. Results Screen
**Expected Behavior:**
- [ ] Final score displayed
- [ ] Shows breakdown: left swipes, right swipes, holds
- [ ] Shows max combo achieved
- [ ] "View Checklist" button visible

**Actions:**
1. Check that hold count matches cards you held
2. Note your final score
3. Tap "View Checklist"

#### D. Checklist Screen (NEW FEATURE)
**Expected Behavior:**
- [ ] List shows the exact cards you held during the game
- [ ] Task cards show: task title + estimated time
- [ ] Photo cards show: contextual action (e.g., "Organize screenshot")
- [ ] Each item has a checkbox
- [ ] Items match what you held in step B

**Test Cases:**
1. **If you held task cards:**
   - [ ] Checklist shows task titles
   - [ ] Shows estimated time if available (e.g., "15 min")

2. **If you held photo cards:**
   - [ ] Shows photo-specific actions
   - [ ] Different messages for screenshots vs regular photos

3. **If you held NO cards:**
   - [ ] Shows default message: "Great session! Take a quick break"

**Actions:**
1. Verify checklist items match cards you held
2. Check off 1-2 items
3. Navigate to Roulette

#### E. Roulette Screen (NEW FEATURE)
**Expected Behavior:**
- [ ] Roulette wheel displays
- [ ] Selected action relates to a card you held
- [ ] Action is specific and actionable

**Test Cases:**
1. **If you held a high-priority task:**
   - [ ] Action says: "Complete high-priority task: [task name]"

2. **If you held a regular task:**
   - [ ] Action says: "Start task: [task name]"

3. **If you held a screenshot photo:**
   - [ ] Action says: "Delete 10 screenshots from your photo library"

4. **If you held a duplicate photo:**
   - [ ] Action says: "Remove duplicate photos"

5. **If you held NO cards:**
   - [ ] Shows default action (e.g., "Take a 5-minute break")

**Actions:**
1. Note the roulette action
2. Verify it's related to a card you held
3. Spin again if multiple actions available

### 3. Test Different Deck Types

#### Test Work Deck
```
Cards include:
- Review pull request (high priority, 30 min)
- Team standup (medium, 15 min)
- Update documentation (low, 45 min)
```

**Expected Checklist:**
- If you hold "Review pull request": ✓ "Review pull request (30 min)"

**Expected Roulette:**
- If high priority: "Complete high-priority task: Review pull request"

#### Test Home Deck
```
Cards include:
- Clean kitchen (high, 15 min)
- Water plants (low, 5 min)
- Organize closet (medium, 60 min)
```

**Expected Checklist:**
- If you hold "Clean kitchen": ✓ "Clean kitchen (15 min)"

#### Test Travel Deck
```
Cards include:
- Book accommodation (high, 20 min)
- Pack luggage (medium, 30 min)
```

## Edge Cases to Test

### 1. No Cards Held
**Steps:**
1. Start game
2. Swipe left/right on ALL cards (don't hold any)
3. Check results

**Expected:**
- Checklist shows: "Great session! Take a quick break"
- Roulette shows: Generic productivity action

### 2. Only One Card Held
**Steps:**
1. Start game
2. Hold exactly 1 card
3. Swipe left/right on others

**Expected:**
- Checklist shows: 1 item matching that card
- Roulette shows: Action based on that specific card

### 3. All Cards Held
**Steps:**
1. Start game
2. Hold ALL cards (swipe up on everything)

**Expected:**
- Checklist shows: All cards as checklist items
- Roulette selects: Random action from all held cards

### 4. Mixed Card Types
**Steps:**
1. Hold 2 task cards + 1 photo card
2. Complete game

**Expected:**
- Checklist shows: 3 items (2 tasks with titles, 1 photo action)
- Roulette picks: One of the 3 held cards

## Performance Testing

### Timer Accuracy
- [ ] Timer counts down correctly (60 → 0)
- [ ] Game ends exactly at 0 seconds
- [ ] Pause/resume works (if implemented)

### Scoring
- [ ] Base score increases with each swipe
- [ ] Combo multiplier applies correctly
- [ ] Hold gives more points than left/right
- [ ] Speed bonus applies if playing fast

### UI Responsiveness
- [ ] Cards swipe smoothly (60 FPS)
- [ ] No lag when updating score
- [ ] Transitions between screens are smooth

## Viewing Logs

### Android Logs
```bash
# View all OnyxFlow logs
adb logcat | grep OnyxFlow

# Filter for errors only
adb logcat | grep -E "OnyxFlow.*ERROR"

# View game engine logs
adb logcat | grep GameEngine
```

### Metro Bundler Logs
```bash
# If running in foreground
# Just check the terminal where npm start is running

# If running in background
tail -f metro.log
```

## Debugging Common Issues

### Checklist is Empty
**Problem:** Checklist shows nothing or only default message

**Debug:**
1. Check if you actually held cards (swiped up)
2. Verify hold count in results screen
3. Check logs: `adb logcat | grep generateChecklist`

### Roulette Action Not Related to Held Cards
**Problem:** Roulette shows generic action when you held cards

**Debug:**
1. Check if held cards array is populated
2. Verify card types are correct
3. Check logs: `adb logcat | grep selectRouletteAction`

### App Crashes After Game
**Problem:** App crashes when viewing results/checklist

**Debug:**
1. Check logs for errors: `adb logcat | grep -E "ERROR|FATAL"`
2. Verify GameEngine is properly ending session
3. Check if all cards have valid content

## Test Checklist Summary

Before considering OnyxFlow complete, verify:

**Core Functionality:**
- [ ] Game starts and runs for 60 seconds
- [ ] All swipe directions work (left, right, hold)
- [ ] Score calculates correctly
- [ ] Combo system works

**New Features (Completed Today):**
- [ ] Held cards are tracked in session
- [ ] Checklist generates from held cards
- [ ] Checklist shows task titles with time estimates
- [ ] Checklist shows photo-specific actions
- [ ] Roulette selects action from held cards
- [ ] Roulette action matches card type and priority
- [ ] Default messages work when no cards held

**UI/UX:**
- [ ] All screens render correctly
- [ ] Navigation flows smoothly
- [ ] No crashes or freezes
- [ ] Performance is smooth (60 FPS)

## Next Steps After Testing

Once manual testing is complete:

1. **Document Issues**: Create a list of bugs found
2. **Performance Profiling**: Use React DevTools to check for performance issues
3. **Accessibility Testing**: Test with TalkBack/screen readers
4. **Different Devices**: Test on various screen sizes
5. **Production Build**: Test with release build (`npm run android -- --variant=release`)

## Getting Help

If you encounter issues:

1. Check `ANDROID_SETUP.md` for environment issues
2. Run `./scripts/check-android-env.sh`
3. Review logs: `adb logcat`
4. Check the test output: `npm test -- --verbose`
