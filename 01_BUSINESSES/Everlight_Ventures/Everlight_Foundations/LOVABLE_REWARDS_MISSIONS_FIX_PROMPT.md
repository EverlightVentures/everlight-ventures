# LOVABLE PROMPT: Rewards, Missions, VIP, Achievements, Spin Wheel + Profile Fix

Paste everything below into Lovable. This wires up the full rewards/progression system that is now LIVE on the backend. All API endpoints are deployed and tested.

**Supabase API:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Headers:** `Content-Type: application/json`, `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
**Authorization:** `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

Do NOT remove or change any existing features. This is ADDITIVE.

---

## CRITICAL FIX: Profile Page Number Handling

The profile `.toFixed is not a function` crash is now fixed on the backend. All numeric values from `get-profile` are guaranteed to be JavaScript numbers. However, the frontend should STILL be defensive. Wrap any `.toFixed()` calls like this:

```typescript
// SAFE pattern for displaying numbers from API
const displayNumber = (val: unknown, decimals = 0): string => {
  const n = Number(val);
  return isNaN(n) ? "0" : n.toFixed(decimals);
};

// Use it everywhere:
displayNumber(profile.win_rate, 1)    // "52.3"
displayNumber(profile.chip_balance)    // "5000"
displayNumber(profile.total_wagered)   // "12500"
```

Add this `displayNumber` helper and use it in ALL places where profile numeric data is displayed with `.toFixed()`, `.toLocaleString()`, or string interpolation that expects a number.

---

## FEATURE 1: DAILY REWARDS CALENDAR

### New Route: /arcade/daily-rewards (or modal accessible from lobby)

Build a 28-day calendar showing daily login rewards. This is a core retention feature.

### API Endpoints

**Check today's reward:**
```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-daily-reward', player_id }),
});
// Response:
{
  can_claim: boolean,        // true = can claim now
  current_streak: number,    // 1-28 day streak
  today_reward: { day: 1, chips: 500, gems: 0 },
  calendar: [...],           // Full 28-day calendar array
  next_claim_at: string|null // ISO timestamp of next available claim
}
```

**Claim today's reward:**
```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'claim-daily-reward', player_id }),
});
// Response:
{
  success: true,
  reward: { day: 1, chips: 500, gems: 0 },
  streak_day: 1,
  new_chip_balance: 1500,
  next_claim_at: "2026-03-12T08:00:00.000Z"
}
// Error 429 if already claimed today
```

### UI Design

- **Calendar Grid**: 4 rows x 7 columns showing days 1-28
- Each day cell shows:
  - Day number (top-left, small)
  - Reward icon: gold coin for chips, blue gem for gems, gift box for mystery_box days
  - Reward amount below the icon
  - **Claimed days**: Green checkmark overlay, slightly faded
  - **Today (claimable)**: Glowing gold border, pulsing animation, "CLAIM" button
  - **Today (already claimed)**: Green checkmark, "Claimed!" text
  - **Future days**: Locked/gray, subtle outline only
  - **Mystery box days** (7, 14, 21, 28): Special gift box icon with sparkle animation, shows "Mystery Box" text

- **Streak counter**: "Day {n} Streak" displayed prominently above the calendar with a fire icon
- **If streak breaks** (missed a day): Show "Streak reset!" in red and restart from day 1
- **Claim button**: Large gold button below the calendar: "Claim {chips} Chips + {gems} Gems"
  - When clicked: coins rain animation, chip balance updates live, button changes to "Claimed! Come back tomorrow"
  - If `can_claim` is false: Button disabled, shows countdown timer to next midnight PT

- **Countdown timer**: When reward is already claimed, show "Next reward in: 5h 23m" with live countdown to `next_claim_at`

### Auto-show on Login
When a player logs in or opens the arcade, if `can_claim` is true, automatically show the daily reward modal with a slight delay (1 second after lobby loads). Player can dismiss it and claim later from the lobby.

### Lobby Access
Add a "Daily Reward" button in the lobby with a red notification dot when `can_claim` is true. Icon: calendar with a star.

---

## FEATURE 2: MISSIONS PAGE

### New Route: /arcade/missions (or tab within the lobby)

### API Endpoint

```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-missions', player_id }),
});
// Response:
{
  daily: [
    { id: "daily_5_hands", type: "daily", name: "Play 5 Hands Today", description: "...",
      progress: 3, target: 5, reward_chips: 500, reward_gems: 0,
      completed: false, claimed: false, percent: 60 },
    ...
  ],
  lifetime: [
    { id: "play_50", type: "lifetime", name: "Getting Started", description: "Play 50 hands",
      progress: 37, target: 50, reward_chips: 2000, reward_gems: 5,
      completed: false, claimed: false, percent: 74 },
    ...
  ],
  total_completed: 3,
  total_claimed: 2
}
```

**Claim a completed mission:**
```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'claim-mission', player_id, mission_id: "play_50" }),
});
// Response: { success: true, reward: { chips: 2000, gems: 5 }, mission_id: "play_50" }
// Error 409 if already claimed
```

### UI Design

- **Two tabs**: "Daily" and "Lifetime" (default to Daily)
- **Daily missions** reset display each day. Show 3 daily missions.
- **Lifetime missions** are permanent progress trackers. Show all 11.

Each mission card:
- Left side: Mission icon (based on type: hands=cards, wins=trophy, blackjacks=star, wager=coins, level=shield)
- Center: Mission name (bold, 14px) + description (gray, 12px)
- Right side: Reward preview (gold coin + number, blue gem + number)
- Bottom: Progress bar (gold fill) with "37/50" text overlay
- **Completed but unclaimed**: Gold glow border, "CLAIM" button replaces progress bar
- **Claimed**: Green checkmark, grayed out, "Completed" text
- **In progress**: Normal display with progress bar

When "CLAIM" is tapped:
1. Call `claim-mission` API
2. Show reward animation (chips + gems floating up)
3. Update chip/gem balances in the header
4. Mark mission as claimed in the UI
5. Show toast: "Mission complete! +2,000 chips, +5 gems"

### Lobby Access
Add "Missions" button in lobby. Show badge count of claimable (completed but unclaimed) missions. Icon: target/bullseye.

---

## FEATURE 3: VIP TIER / REWARD PROGRESS

### New Route: /arcade/vip (or section within profile)

### API Endpoint

```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-vip-status', player_id }),
});
// Response:
{
  vip_points: 1250,
  tier: { name: "Silver", min: 500, max: 1999, perks: [...], color: "#C0C0C0", icon: "shield_silver" },
  next_tier: { name: "Gold", min: 2000, ... },
  progress_to_next: 50,    // percentage
  points_to_next: 750,     // points needed
  all_tiers: [...]          // Full tier array for display
}
```

### UI Design

- **Current Tier Card** (top, full-width):
  - Large tier icon + tier name (e.g., "SILVER" in silver text, 24px bold)
  - VIP points: "1,250 VP" in gold text
  - Progress bar to next tier with percentage: "Silver → Gold: 50%"
  - Points needed: "750 VP to Gold tier"

- **Tier Ladder** (scrollable vertical list):
  - Show all 6 tiers as cards stacked vertically
  - Current tier: highlighted with colored border matching tier color
  - Higher tiers: slightly faded with lock icon
  - Lower tiers: green checkmark, completed
  - Each tier card shows: tier name, icon, color accent, list of perks

- **VIP Tiers** (from lowest to highest):
  1. **Bronze** (#CD7F32) - 0 VP
  2. **Silver** (#C0C0C0) - 500 VP
  3. **Gold** (#FFD700) - 2,000 VP
  4. **Platinum** (#E5E4E2) - 5,000 VP
  5. **Diamond** (#B9F2FF) - 15,000 VP
  6. **Everlight Elite** (#D4AF37) - 50,000 VP (animated gold glow)

- **How to earn VP** section (collapsible):
  - "1 VP per 100 chips wagered"
  - "2 VP per hand played"
  - "10 VP per level gained"
  - "1 VP per day as a member"

### Lobby Access
Show current VIP tier badge in the lobby header next to the player's level. Tap to open VIP page.

---

## FEATURE 4: ACHIEVEMENTS PAGE

### New Route: /arcade/achievements

### API Endpoint

```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-achievements', player_id }),
});
// Response:
{
  achievements: [
    { code: "first_hand", name: "First Hand", description: "Play your first hand",
      icon: "cards", progress: 1, target: 1, category: "beginner",
      completed: true, unlocked: true, unlocked_at: "2026-03-10T...", percent: 100 },
    ...
  ],
  total: 21,
  unlocked: 5,
  categories: ["beginner", "player", "veteran", "legend", "loyalty"]
}
```

### UI Design

- **Header**: "Achievements: 5/21 Unlocked" with a progress ring
- **Category filter tabs**: All | Beginner | Player | Veteran | Legend | Loyalty
- **Achievement grid**: 2 columns on mobile, 3 on desktop

Each achievement card:
- Icon (large, 48px, colored when unlocked, gray when locked)
- Name (bold, 14px)
- Description (gray, 12px)
- Progress bar with "37/50" text
- **Unlocked**: Full color icon, green "Unlocked" badge, subtle glow
- **Locked**: Gray icon, progress bar showing current/target

Categories have themed colors:
- Beginner: Green
- Player: Blue
- Veteran: Purple
- Legend: Gold with shimmer
- Loyalty: Rose/Pink

### Lobby Access
Add "Achievements" button in lobby. Show "X new!" badge when achievements were auto-unlocked. Icon: trophy.

---

## FEATURE 5: SPIN THE WHEEL

### Accessible from lobby as a prominent button

### API Endpoints

**Check wheel status:**
```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-wheel-status', player_id }),
});
// Response:
{
  can_spin: true,
  next_spin_at: null,         // or ISO timestamp if on cooldown
  cooldown_remaining_ms: 0,   // ms until next spin
  last_result: null,          // last spin result
  segments: [
    { label: "100 Chips", chips: 100, gems: 0, weight: 30 },
    { label: "250 Chips", chips: 250, gems: 0, weight: 25 },
    { label: "500 Chips", chips: 500, gems: 0, weight: 18 },
    { label: "1,000 Chips", chips: 1000, gems: 0, weight: 12 },
    { label: "2,500 Chips", chips: 2500, gems: 0, weight: 7 },
    { label: "5 Gems", chips: 0, gems: 5, weight: 5 },
    { label: "10 Gems", chips: 0, gems: 10, weight: 2 },
    { label: "JACKPOT 5,000", chips: 5000, gems: 0, weight: 1 },
  ]
}
```

**Spin the wheel:**
```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'spin-wheel', player_id }),
});
// Response:
{
  success: true,
  result: { label: "500 Chips", chips: 500, gems: 0, weight: 18 },
  segments: [...],
  next_spin_at: "2026-03-11T04:48:00.000Z"
}
// Error 429 if on cooldown, with next_spin_at and cooldown_remaining_ms
```

### UI Design

- **Full-screen modal** with dark glass backdrop
- **Wheel**: Canvas or CSS-based circular wheel with 8 colored segments
  - Each segment labeled with the prize name
  - Colors: alternating gold, dark, silver, dark pattern
  - Center: Everlight Casino logo
  - Pointer/arrow at top (12 o'clock position)

- **Spin animation**:
  1. Wheel starts spinning fast (2-3 full rotations)
  2. Gradually decelerates over 3-4 seconds
  3. Stops on the winning segment (calculate the correct rotation angle based on the result index from the API)
  4. Winning segment flashes/glows
  5. Prize display pops up: "You won 500 Chips!" with confetti

- **Before spin**: Large "SPIN!" button below the wheel (gold, 56px tall)
- **On cooldown**: Button shows countdown timer "Next spin in: 3h 47m", wheel is slightly grayed out
- **After spin**: Show the result for 3 seconds, then button changes to cooldown timer

### Lobby Access
Add "Spin & Win" button in lobby. Show a spinning wheel icon. Red dot notification when `can_spin` is true. When on cooldown, show the countdown on the button itself.

---

## FEATURE 6: LOBBY NAVIGATION UPDATE

The lobby needs buttons/cards for all these features. Update the lobby layout:

### Lobby Quick Actions Row (horizontal scrollable)
Below the player info bar, add a scrollable row of action buttons:

1. **Play Blackjack** (gold, largest) - Navigates to table selection
2. **Daily Reward** (calendar icon) - Opens daily reward modal. Red dot if claimable.
3. **Spin & Win** (wheel icon) - Opens spin wheel. Red dot if available. Countdown if on cooldown.
4. **Missions** (target icon) - Opens missions page. Badge with count of claimable missions.
5. **Achievements** (trophy icon) - Opens achievements page. Badge if new unlocks.
6. **VIP** (crown icon) - Opens VIP status page. Shows current tier badge.
7. **Profile** (user icon) - Opens profile page.
8. **Leaderboard** (chart icon) - Opens leaderboard.
9. **Shop** (cart icon) - Opens shop.

Each button: 64px wide, icon on top (24px), label below (10px). Dark glass background, gold icon for active/available, gray for cooldown/locked. Scrollable horizontally on mobile.

### Notification Badges
These buttons should poll for status on mount and show red notification dots:
- Daily Reward: `get-daily-reward` → show dot if `can_claim`
- Spin & Win: `get-wheel-status` → show dot if `can_spin`
- Missions: `get-missions` → show badge count of missions where `completed && !claimed`

Fetch all three in parallel when the lobby mounts:
```typescript
useEffect(() => {
  Promise.all([
    fetch(API, { method: 'POST', headers, body: JSON.stringify({ action: 'get-daily-reward', player_id }) }).then(r => r.json()),
    fetch(API, { method: 'POST', headers, body: JSON.stringify({ action: 'get-wheel-status', player_id }) }).then(r => r.json()),
    fetch(API, { method: 'POST', headers, body: JSON.stringify({ action: 'get-missions', player_id }) }).then(r => r.json()),
  ]).then(([daily, wheel, missions]) => {
    setCanClaimDaily(daily.can_claim);
    setCanSpin(wheel.can_spin);
    const claimable = [...missions.daily, ...missions.lifetime].filter(m => m.completed && !m.claimed);
    setClaimableMissions(claimable.length);
  });
}, [player_id]);
```

---

## TESTING CHECKLIST

1. **Profile page loads without errors** -- no `.toFixed` crash, all numbers display correctly
2. **Daily Reward calendar** shows 28 days, current streak, correct claimed/unclaimed states
3. **Claiming daily reward** updates chip balance, shows animation, disables button until tomorrow
4. **Countdown timer** ticks down live after claiming, resets at midnight PT
5. **Missions page** shows 3 daily + 11 lifetime missions with progress bars
6. **Claiming a completed mission** awards chips+gems, shows toast, marks as claimed
7. **VIP page** shows current tier, progress to next, all 6 tiers with perks
8. **VIP progress bar** fills based on real player data (wagered, hands, level, days)
9. **Achievements page** shows 21 achievements, auto-unlocked ones show as unlocked
10. **Category filter** on achievements works correctly
11. **Spin wheel** animates smoothly, lands on correct segment, awards prize
12. **Wheel cooldown** (4 hours) prevents re-spin, shows countdown
13. **Lobby buttons** show correct notification badges (red dots, counts)
14. **All API calls** use the correct headers and handle errors gracefully
15. **Mobile layout** works on 375px screens without horizontal overflow

## IMPORTANT: Do NOT break existing features
- Keep ALL existing game functionality
- Keep ALL existing auth flows
- Keep ALL existing profile features
- Keep ALL existing shop/economy
- This is ADDITIVE -- new pages and features layered on the existing foundation
