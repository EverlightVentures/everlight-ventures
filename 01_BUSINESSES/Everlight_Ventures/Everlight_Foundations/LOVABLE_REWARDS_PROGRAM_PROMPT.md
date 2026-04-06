# LOVABLE PROMPT: Everlight Rewards -- Cross-Game Loyalty Engine

Paste this into Lovable to build the Everlight Rewards system.

---

## PROMPT:

Build a full cross-game rewards and loyalty program called **"Everlight Rewards"** integrated into the existing arcade at `/arcade`. This system uses **Gems** as the universal currency across all Everlight games. Gems can be earned through daily logins, streaks, achievements, and referrals -- or purchased with real money. Gems convert into any game-specific currency at fixed rates. The system includes a tiered VIP program, daily login calendar, achievement tracker, and referral engine.

All purchases go through the existing Supabase Edge Function at `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/create-checkout` with `{ slug, success_url, cancel_url }`. The anon key header is: `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

Player data (gem balance, login streaks, tier, achievements, referrals) should be stored in Supabase tables. Use the existing auth system.

---

### 1. GEM ECONOMY -- UNIVERSAL CURRENCY

Gems are the **single cross-game premium currency**. Every game in the Everlight Arcade accepts Gems and converts them into its local currency.

#### 1.1 Gem Conversion Rates

| Game | Local Currency | Icon | 1 Gem = | Example |
|------|---------------|------|---------|---------|
| Alley Kingz | NOS Bottles | Nitrous bottle (blue/orange) | 10 NOS Bottles | 5 Gems = 50 NOS |
| Blackjack | Chips | Casino chip (gold) | 100 Chips | 5 Gems = 500 Chips |
| Future Games | (auto-configured) | (per game) | Set per game | -- |

**Design rule:** 1 Gem ≈ $0.01 real value. This makes math easy: 100 Gems ≈ $1.00 worth of in-game value. Gems are **non-withdrawable** virtual currency with no cash-out.

#### 1.2 Gem Packs (IAP -- update existing shop)

| Pack | Gems | Price | Slug | Badge |
|------|------|-------|------|-------|
| Handful | 100 | $0.99 | `gems-100` | -- |
| Pouch | 600 | $4.99 | `gems-600` | POPULAR |
| Chest | 1,500 | $9.99 | `gems-1500` | BEST VALUE |
| Vault | 4,000 | $24.99 | `gems-4000` | WHALE |
| Treasury | 10,000 | $49.99 | `gems-10000` | ULTIMATE |

#### 1.3 Gem Conversion UI

On each game's shop page AND on the main rewards page, add a **"Convert Gems"** panel:
- Shows current Gem balance with purple diamond icon
- Dropdown or toggle to select target game currency
- Slider or input for how many Gems to convert (min 1)
- Live preview: "5 Gems → 50 NOS Bottles" or "5 Gems → 500 Chips"
- "CONVERT" button (purple gradient, instant, no checkout needed -- just updates balances in Supabase)
- Conversion is instant and irreversible. Show a confirm modal: "Convert X Gems to Y [Currency]? This cannot be undone."

---

### 2. DAILY LOGIN REWARDS -- "DAILY STREAK"

Route: `/arcade/rewards` (new page, also accessible from `/arcade` hub via "REWARDS" button)

#### 2.1 Login Calendar

Display a **28-day rolling calendar grid** (4 rows × 7 columns). Each day shows the reward for logging in that day. Days are numbered 1-28, then the cycle resets.

**Streak Rewards Schedule:**

| Day | Reward | Display |
|-----|--------|---------|
| 1 | 1 Gem | Small purple diamond |
| 2 | 1 Gem | Small purple diamond |
| 3 | 2 Gems | Two small diamonds |
| 4 | 2 Gems | Two small diamonds |
| 5 | 3 Gems | Three diamonds |
| 6 | 3 Gems | Three diamonds |
| 7 | **5 Gems + Mystery Box** | Gold border, sparkle effect, "WEEKLY BONUS" banner |
| 8 | 2 Gems | -- |
| 9 | 2 Gems | -- |
| 10 | 3 Gems | -- |
| 11 | 3 Gems | -- |
| 12 | 4 Gems | -- |
| 13 | 4 Gems | -- |
| 14 | **10 Gems + Mystery Box** | Gold border, "2-WEEK BONUS" banner |
| 15-20 | 3 Gems each | -- |
| 21 | **15 Gems + Rare Mystery Box** | Platinum border, "3-WEEK BONUS" |
| 22-27 | 4 Gems each | -- |
| 28 | **25 Gems + Epic Mystery Box + VIP Points** | Diamond border, glow animation, "MONTHLY BONUS" |

**Total per 28-day cycle: ~100 Gems** (equivalent to ~$1.00 value -- enough to taste the economy, not enough to replace buying)

#### 2.2 Mystery Boxes

Mystery Boxes contain randomized rewards weighted toward engagement:
- **Basic Mystery Box** (Day 7): 50% chance 5 bonus Gems, 30% chance game-specific currency bundle (50 NOS or 500 Chips), 20% chance cosmetic item
- **Rare Mystery Box** (Day 21): 50% chance 10 bonus Gems, 30% chance 100 NOS or 1000 Chips, 20% chance exclusive avatar frame
- **Epic Mystery Box** (Day 28): 40% chance 25 bonus Gems, 30% chance premium cosmetic, 30% chance exclusive title + avatar

Display mystery box opening as an animated reveal (card flip or chest opening animation).

#### 2.3 Streak Rules
- Must log in once per calendar day (midnight-to-midnight UTC, displayed in PT per user preference)
- Missing a day **resets the streak counter to Day 1** -- show a warning: "Don't lose your streak! Come back tomorrow."
- If the player has VIP Silver or above, they get **1 streak shield per month** (miss a day without losing streak)
- Show "Current Streak: X days" prominently with a flame icon that grows with streak length
- Push notification prompt (optional): "Your X-day streak is at risk! Log in today."

#### 2.4 Calendar UI Design
- Dark card (#1A1A1A) with grid of day cells
- Claimed days: green checkmark overlay, slightly dimmed
- Current day: glowing purple border, pulsing "CLAIM" button
- Future days: locked, shows reward preview but greyed out
- Missed days: red X overlay
- Bonus days (7, 14, 21, 28): larger cell, gold/platinum/diamond border, sparkle particles

---

### 3. VIP TIER SYSTEM -- "EVERLIGHT STATUS"

Players earn **VIP Points (VP)** through spending real money and completing achievements. VP determines tier. Tiers grant passive bonuses across ALL games.

#### 3.1 Tier Structure

| Tier | VP Required | Monthly Spend Equiv. | Icon | Color | Border |
|------|-------------|---------------------|------|-------|--------|
| **Bronze** | 0 | Free | Bronze shield | #CD7F32 | Thin bronze |
| **Silver** | 500 VP | ~$5 | Silver shield | #C0C0C0 | Silver glow |
| **Gold** | 2,000 VP | ~$20 | Gold crown | #D4AF37 | Gold shimmer |
| **Platinum** | 5,000 VP | ~$50 | Platinum diamond | #E5E4E2 | Platinum pulse |
| **Diamond** | 15,000 VP | ~$150 | Diamond gem | #B9F2FF | Diamond rainbow |
| **Alley King** | 50,000 VP | ~$500 | Crown + flame | #FF4500 | Animated fire border |

**VP Earning:**
- Every $1 spent = 100 VP
- Daily login completion (Day 28) = 50 VP bonus
- Referring a paying player = 200 VP
- Achievement milestones = 25-100 VP each

**VP does NOT decay.** Once earned, tier is permanent. This rewards lifetime loyalty.

#### 3.2 Tier Perks

| Perk | Bronze | Silver | Gold | Platinum | Diamond | Alley King |
|------|--------|--------|------|----------|---------|------------|
| Daily Gem bonus | +0 | +1/day | +2/day | +3/day | +5/day | +10/day |
| Gem conversion bonus | 0% | +5% | +10% | +15% | +20% | +30% |
| Streak shields/month | 0 | 1 | 2 | 3 | 5 | Unlimited |
| Mystery Box luck boost | -- | -- | +10% | +20% | +30% | +50% |
| Exclusive avatar frame | -- | Silver | Gold | Platinum | Diamond | Animated Crown |
| Name color in chat | White | Silver | Gold | Platinum | Cyan | Red + flame |
| Monthly bonus Gems | 0 | 10 | 25 | 50 | 100 | 250 |
| Priority support | -- | -- | -- | Yes | Yes | Yes |
| Exclusive game content | -- | -- | -- | Early access | Early access | Beta tester + input |

**Gem conversion bonus** means: at Gold tier, converting 10 Gems to NOS gives 110 NOS instead of 100 (10% bonus). This incentivizes spending to reach higher tiers where gems stretch further.

#### 3.3 VIP Status UI

On the `/arcade/rewards` page, show a **VIP Status Card**:
- Current tier badge (large, centered)
- Progress bar to next tier with VP count: "2,340 / 5,000 VP to Platinum"
- List of current tier perks with checkmarks
- "Next tier unlocks:" preview of upcoming perks (teaser to spend more)
- Tier history: "Member since [date]"

---

### 4. ACHIEVEMENTS -- "STREET CRED"

Route: `/arcade/rewards/achievements` (tab on rewards page)

Achievements award Gems + VP and drive cross-game engagement.

#### 4.1 Achievement Categories

**ARCADE-WIDE:**
| Achievement | Requirement | Reward |
|-------------|-------------|--------|
| First Login | Log in for the first time | 5 Gems |
| Week Warrior | 7-day login streak | 10 Gems + 25 VP |
| Grinder | 14-day login streak | 20 Gems + 50 VP |
| Iron Will | 28-day login streak (full cycle) | 50 Gems + 100 VP |
| Social Butterfly | Refer 1 friend who signs up | 15 Gems + 50 VP |
| Recruiter | Refer 5 friends | 50 Gems + 200 VP |
| Kingmaker | Refer a friend who reaches Gold VIP | 100 Gems + 500 VP |
| Big Spender | Spend $10 total | 25 Gems + 100 VP |
| Whale Watch | Spend $100 total | 200 Gems + 1000 VP |
| Multi-Gamer | Play 2+ different arcade games | 10 Gems |
| Arcade Rat | Play every game in the arcade | 25 Gems + 50 VP |

**ALLEY KINGZ SPECIFIC:**
| Achievement | Requirement | Reward |
|-------------|-------------|--------|
| First Blood | Win your first battle | 5 Gems |
| Deck Master | Build 3 different decks | 10 Gems |
| Arena Climber | Reach Strip Run arena (400 NOS) | 10 Gems |
| Neon Nights | Reach Neon District (2600 NOS) | 25 Gems |
| Empire Builder | Reach Empire State (5000 NOS) | 50 Gems + 100 VP |
| Card Collector | Collect 24 unique cards | 15 Gems |
| Full Roster | Collect all 48 cards | 100 Gems + 200 VP |

**BLACKJACK SPECIFIC:**
| Achievement | Requirement | Reward |
|-------------|-------------|--------|
| First Hand | Play your first hand | 5 Gems |
| Natural 21 | Get a blackjack (Ace + 10-value) | 10 Gems |
| Hot Streak | Win 5 hands in a row | 15 Gems |
| High Roller | Bet 1,000+ chips in a single hand | 10 Gems |
| Card Counter | Win 50 total hands | 25 Gems |

#### 4.2 Achievement UI
- Grid of achievement cards, 2 per row on mobile, 3-4 on desktop
- Each card shows: icon, name, description, reward, progress bar
- Completed: green border + checkmark + "CLAIMED" stamp
- In-progress: show progress (e.g., "3/7 days")
- Locked: greyed out, "???" for secret achievements
- Click to expand for details
- Toast notification when an achievement is completed: slide-in from top with gem sparkle animation

---

### 5. REFERRAL ENGINE -- "CREW UP"

Route: `/arcade/rewards/referrals` (tab on rewards page)

#### 5.1 Referral Flow
1. Player gets a unique referral link: `everlightventures.io/arcade?ref=PLAYER_CODE`
2. Player also gets a **referral code** (6 chars, auto-generated, e.g., "AK7X9M") they can share verbally
3. New player signs up via link OR enters code during signup
4. Referrer gets reward when referee completes milestones

#### 5.2 Referral Rewards (Split Trigger -- Anti-Fraud)

| Milestone | Referrer Gets | Referee Gets |
|-----------|--------------|--------------|
| Friend signs up | 5 Gems | 10 Gems (welcome bonus) |
| Friend plays first game | 5 Gems | 5 Gems |
| Friend makes first purchase ($1+) | 15 Gems + 50 VP | 10 Gems |
| **Total per referral** | **25 Gems + 50 VP** | **25 Gems** |

Split triggers prevent bot abuse -- the real payout comes when the friend actually spends money.

#### 5.3 Referral UI
- **Your Code**: Large display of referral code with "COPY" button
- **Your Link**: Full URL with "COPY" button
- **Share buttons**: Native share (mobile), Twitter/X, WhatsApp, Discord, SMS
- **Referral Stats**:
  - Total referred: X
  - Signed up: X
  - Made a purchase: X
  - Total Gems earned from referrals: X
- **Leaderboard**: Top 10 referrers this month with username + count (gamification)
- **Referral history**: Table of each referral with status badges (Signed Up / Played / Purchased)

#### 5.4 Anti-Fraud Rules
- 1 referral credit per unique email/device
- Self-referral blocked (same IP/device fingerprint)
- Referral rewards capped at 50 per month (prevents farming)
- Require email verification before referral bonus pays out

---

### 6. REWARDS HUB PAGE

Route: `/arcade/rewards`

This is the main rewards dashboard. Tabbed layout with persistent header.

#### 6.1 Page Layout

**Header Section (always visible):**
- "EVERLIGHT REWARDS" title in gradient text (purple → gold)
- Player's current Gem balance (large, purple diamond icon + count)
- VIP tier badge next to username
- Current streak: "🔥 X Day Streak" with flame that scales with streak length

**Tab Navigation:**
| Tab | Icon | Content |
|-----|------|---------|
| **Daily** | Calendar icon | Login calendar + claim button |
| **VIP Status** | Crown icon | Tier card + progress + perks |
| **Achievements** | Trophy icon | Achievement grid |
| **Convert** | Exchange arrows icon | Gem → currency converter |
| **Refer** | People icon | Referral code + stats |
| **Shop** | Cart icon | Gem packs purchase (existing shop, embedded) |

#### 6.2 Quick Actions Bar (sticky bottom on mobile)
- "CLAIM DAILY" button (green pulse if unclaimed, grey if claimed)
- Gem balance display
- "SHOP" quick link

---

### 7. ARCADE HUB INTEGRATION

Update the existing `/arcade` page:

#### 7.1 Rewards Banner
Add a banner below the Master Pass hero but above game cards:
- Gradient: linear-gradient(135deg, #7B2FF7, #D4AF37)
- "EVERLIGHT REWARDS" in bold white
- "Earn Gems every day. Level up your status. Convert to any game." subtitle
- Current streak + Gem balance shown
- "VIEW REWARDS" button → `/arcade/rewards`
- If daily unclaimed: pulsing "CLAIM NOW" badge

#### 7.2 Game Card Updates
Each game card on `/arcade` should now also show:
- Gem balance (universal, same on all cards)
- Local currency balance (NOS Bottles for AK, Chips for BJ)
- Small "Convert Gems" link under the currency display

---

### 8. AI-POWERED ENGAGEMENT (Smart Nudges)

Implement a lightweight "nudge engine" that shows contextual prompts to drive spending and retention. These are NOT push notifications -- they are **in-app UI elements** that appear based on player behavior.

#### 8.1 Nudge Triggers

| Trigger | Nudge | Location |
|---------|-------|----------|
| Player hasn't logged in for 2+ days | "We miss you! Your streak is waiting." email (if opted in) | Email |
| Streak about to reset (23+ hours since last login) | Countdown timer: "⏰ X hours to save your streak!" | Top banner on any page |
| Player at 70% of next VIP tier | "You're close! X more VP to unlock [next tier]." | VIP status card |
| Player wins 3+ games in a row | "You're on fire! Grab a Gem pack to keep the momentum." | Post-game overlay |
| Player loses 3+ games in a row | "Tough run. Here's 2 free Gems on us." (one-time daily) | Post-game overlay |
| Player has 0 local currency | "Out of [NOS/Chips]? Convert some Gems!" | Game shop |
| New game added to arcade | "NEW GAME! Try [game] and earn 10 Gems." | Arcade hub banner |
| Player referred but friend hasn't played | "Your friend signed up but hasn't played yet. Send them a reminder!" | Referral tab |
| Day 6 of streak (one day before weekly bonus) | "Tomorrow is your WEEKLY BONUS! Don't miss 5 Gems + Mystery Box!" | Daily tab |

#### 8.2 Nudge UI Rules
- Max 1 nudge visible at a time (no spam stacking)
- Each nudge has a dismiss "X" button
- Dismissed nudges don't reappear for 24 hours
- Nudges have a subtle slide-in animation (300ms ease)
- Color: dark card with purple left-border accent (#7B2FF7)

---

### 9. SUPABASE DATA MODEL

Create these tables in Supabase (use existing auth for user_id):

#### `player_rewards`
```sql
CREATE TABLE player_rewards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  gem_balance INTEGER DEFAULT 0,
  vip_points INTEGER DEFAULT 0,
  vip_tier TEXT DEFAULT 'bronze',
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_login_date DATE,
  streak_shields_remaining INTEGER DEFAULT 0,
  streak_shields_reset_date DATE,
  referral_code TEXT UNIQUE,
  total_referrals INTEGER DEFAULT 0,
  total_spent_cents INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);
```

#### `login_claims`
```sql
CREATE TABLE login_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  claim_date DATE NOT NULL,
  streak_day INTEGER NOT NULL,
  gems_awarded INTEGER NOT NULL,
  mystery_box_type TEXT,
  mystery_box_result JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, claim_date)
);
```

#### `achievements`
```sql
CREATE TABLE player_achievements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  achievement_id TEXT NOT NULL,
  progress INTEGER DEFAULT 0,
  target INTEGER NOT NULL,
  completed BOOLEAN DEFAULT false,
  claimed BOOLEAN DEFAULT false,
  completed_at TIMESTAMPTZ,
  claimed_at TIMESTAMPTZ,
  UNIQUE(user_id, achievement_id)
);
```

#### `referrals`
```sql
CREATE TABLE referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id UUID REFERENCES auth.users(id),
  referee_id UUID REFERENCES auth.users(id),
  referral_code TEXT NOT NULL,
  status TEXT DEFAULT 'signed_up',
  signup_bonus_paid BOOLEAN DEFAULT false,
  first_game_bonus_paid BOOLEAN DEFAULT false,
  first_purchase_bonus_paid BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(referrer_id, referee_id)
);
```

#### `gem_transactions`
```sql
CREATE TABLE gem_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  transaction_type TEXT NOT NULL,
  description TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

`transaction_type` values: `daily_login`, `achievement`, `referral_bonus`, `purchase`, `conversion`, `vip_bonus`, `mystery_box`, `nudge_gift`, `admin`

#### Row Level Security
- Players can only read/update their own `player_rewards` row
- `login_claims` and `gem_transactions` are read-only for players (writes happen via Edge Functions)
- `referrals` visible to referrer only
- All writes to gem balances MUST go through Edge Functions to prevent client-side manipulation

---

### 10. GLOBAL STYLING

Match the existing site dark theme:

- Background: #0A0A0A
- Cards: #1A1A1A, border-radius 12px, subtle #2A2A2A border
- Primary accent: #7B2FF7 (purple, for Gems and rewards)
- Secondary accent: #D4AF37 (gold, for VIP and premium)
- Success: #22C55E (green, for claimed/completed)
- Warning: #F59E0B (amber, for streak warnings)
- Error: #EF4444 (red, for missed days)
- Text: #FFFFFF primary, #9CA3AF secondary
- Font: existing site font stack
- Gem icon: purple diamond, consistent everywhere
- All cards have hover: scale(1.02) + shadow increase
- Mobile-first: single column, tabs as bottom sheet or horizontal scroll
- Animations: Framer Motion or CSS transitions, 200-300ms, ease-out
- Toast notifications: slide from top, auto-dismiss 4s

### 11. NAVIGATION

Add "REWARDS" to the existing site navigation:
- In the arcade section nav: add "Rewards" link with purple diamond icon
- On mobile nav: add rewards icon (diamond) to bottom bar if in arcade section
- Badge on nav icon showing unclaimed daily reward (red dot)

---

### 12. LEGAL FOOTER

Every rewards page must include:
"Gems and all in-game currencies are virtual items with no real-world monetary value. Rewards are non-transferable and non-refundable. Everlight Ventures reserves the right to modify the rewards program at any time. Must be 18+ to purchase. Prices in USD."

---

### 13. PROFIT STRATEGY NOTES (for implementation context, not displayed)

The economy is designed so free players earn ~$1/month in Gems through daily logins. This is enough to convert into one meaningful play session per week -- keeping them engaged but always wanting more. The VIP tier system creates a "status treadmill" where spending unlocks better conversion rates, making each subsequent dollar more valuable. The streak system creates daily habit loops, and missing a day creates loss aversion that drives consistent engagement. Mystery boxes add variable-ratio reinforcement (slot machine psychology) at weekly milestones. The referral system turns every player into a marketer with split-trigger payouts ensuring only real users generate rewards. AI nudges intervene at high-intent moments (loss streaks, near-tier thresholds, low currency) to convert attention into revenue. The entire system is designed to be ethically engaging -- no pay-to-win, no predatory loot boxes, all content earnable through play -- while maximizing LTV through status, habit, and social mechanics.

---

### 14. FIX: GOOGLE & FACEBOOK OAuth LOGIN + SESSION PERSISTENCE

**This is a P0 fix that MUST be included in this update.** The Google and Facebook login buttons currently say "Coming Soon" but the OAuth secrets are already configured in Supabase. The login must work for the rewards system to function.

#### 14.1 Remove "Coming Soon" Gate

Find all login/auth components where Google and Facebook buttons are disabled or show "Coming Soon" text. Replace with working OAuth handlers:

```typescript
// Google Login
const handleGoogleLogin = async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin + '/arcade/rewards'
    }
  });
  if (error) console.error('Google login error:', error.message);
};

// Facebook Login
const handleFacebookLogin = async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'facebook',
    options: {
      redirectTo: window.location.origin + '/arcade/rewards'
    }
  });
  if (error) console.error('Facebook login error:', error.message);
};
```

Remove any feature flags, `disabled` props, or conditional rendering that blocks these buttons. They should be fully interactive with proper loading states.

#### 14.2 Session Persistence (Fix Reload Reset)

The app currently loses all user state on browser refresh. Fix this by implementing an auth state listener at the app root level:

```typescript
// In App.tsx or a top-level AuthProvider
useEffect(() => {
  // Restore session on mount
  supabase.auth.getSession().then(({ data: { session } }) => {
    if (session) {
      setUser(session.user);
      loadPlayerProfile(session.user.id);
    }
  });

  // Listen for auth changes (login, logout, token refresh)
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    async (event, session) => {
      if (session) {
        setUser(session.user);
        await loadPlayerProfile(session.user.id);
      } else {
        setUser(null);
        clearPlayerProfile();
      }
    }
  );

  return () => subscription.unsubscribe();
}, []);
```

#### 14.3 Profile Data Persistence

All player data (blackjack chips, game stats, wins, losses) MUST be saved to the Supabase database keyed by `user_id`, NOT just held in React state. On every significant state change (game result, purchase, currency change):

1. Write to database immediately
2. On page load / auth restore, read from database to hydrate state
3. Merge guest session data into authenticated profile on first login (don't lose progress)

Create or update a `player_profiles` table:
```sql
CREATE TABLE IF NOT EXISTS player_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  display_name TEXT,
  avatar_url TEXT,
  nos_balance INTEGER DEFAULT 0,
  chip_balance INTEGER DEFAULT 1000,
  blackjack_stats JSONB DEFAULT '{"wins": 0, "losses": 0, "pushes": 0, "blackjacks": 0, "biggest_win": 0}',
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

This table links to `player_rewards` via `user_id`. When a player logs in:
1. Check if `player_profiles` row exists → create if not
2. Check if `player_rewards` row exists → create if not (with default gem balance, generate referral code)
3. Load both into app state
4. All subsequent updates write-through to database

#### 14.4 Auth Error States

Replace vague "Coming Soon" with actionable UI:
- Loading: Show spinner on button during OAuth redirect
- Error: Toast with "Login failed. Please try again." + retry button
- Success: Toast "Welcome back, [name]!" + redirect to rewards page
- Logged in state: Show avatar + display name in nav, replace login buttons with "My Profile" / "Logout"

#### 14.5 Auth Testing Checklist (verify all before shipping)
- [ ] Google login redirects and returns with session
- [ ] Facebook login redirects and returns with session
- [ ] Email/password login works
- [ ] Page refresh preserves logged-in state
- [ ] Blackjack chip balance persists after refresh
- [ ] Gem balance persists after refresh
- [ ] Logging out clears all state
- [ ] Logging back in restores all data
- [ ] Guest-to-auth migration preserves in-progress data
