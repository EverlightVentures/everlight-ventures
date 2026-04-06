# LOVABLE PROMPT: Everlight Blackjack V3 -- Premium 3D Casino Upgrade

Paste everything below the line into Lovable. This builds ON TOP of V2 -- do not remove any existing features. This adds: 3D visual overhaul, avatar customization with fashion/accessories, Zynga-style social hooks (daily rewards, tournaments, gifting, VIP tiers, seasonal events), "Table Presence" ranking system, economy rebalancing, spectator mode, and premium polish that rivals Blackjackist and NetEnt's 3D blackjack.

---

## VISUAL UPGRADE: TRUE 3D CASINO ATMOSPHERE

The goal: make this look and feel like a $100M mobile casino game. Think Blackjackist's "amazing 3D interface" meets NetEnt's polished professional series meets Zynga's addictive social hooks.

### Enhanced 3D Table (upgrade existing)
Keep the existing `perspective(1200px) rotateX(35deg)` foundation but layer on:

- **Realistic felt texture**: Replace CSS noise with an SVG filter that simulates real green baize -- `<filter><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4"/><feDisplacementMap scale="2"/></filter>` applied as a background. Subtle fabric weave pattern.
- **Casino chip stacks**: Render bet amounts as actual stacked chip graphics (not just numbers). Use layered colored circles with shadows:
  - White chips = 1, Red = 5, Green = 25, Black = 100, Purple = 500, Gold = 1000
  - Stack them with 2px vertical offset per chip, slight rotation variance for realism
  - Chips have edge stripes (alternating white dashes around the perimeter using conic-gradient)
- **Dealer shoe**: Upgrade from a simple dark box to a 3D-rendered acrylic shoe with visible card stack inside (gradient showing card edges). Cards visibly deplete as hands are played.
- **Table nameplate**: Brass-look plate at the front rail edge showing table name + type + min/max bet. Uses `linear-gradient(135deg, #B8860B, #FFD700, #B8860B)` with embossed text.
- **Ambient particles**: Subtle floating dust motes in the spotlight beam (tiny circles, very slow drift animation, low opacity). 10-15 particles max for performance.
- **Felt wear marks**: Very subtle darker circles where cards frequently land (slightly darker green patches at deal positions). Adds lived-in realism.

### Card Rendering Upgrade
- **Card faces**: Use a premium card design -- white cards with rounded corners (12px border-radius), subtle drop shadow, and a micro paper texture (very faint noise filter).
- **Court cards (J/Q/K)**: Display with rich colors -- red suits get deep crimson, black suits get true black. Face card symbols should be large and ornate.
- **Card back design**: Custom Everlight branded card back -- dark navy (#0D1B2A) with gold filigree pattern (SVG ornamental border), gold "E" monogram in center, subtle holographic shimmer animation on hover.
- **3D flip animation upgrade**: During the flip, show card thickness (2px dark edge visible during rotation using `transform-style: preserve-3d` with a pseudo-element for the card edge).

### Lighting & Atmosphere
- **Dynamic lighting**: The overhead spotlight subtly brightens during exciting moments (blackjack, big wins) and dims slightly during normal play. Use CSS `filter: brightness()` transitions on the table container.
- **Smoke/haze effect**: Very subtle dark gradient overlay at table edges that shifts slowly (CSS animation on background-position). Creates depth and atmosphere without obscuring gameplay.
- **Background casino floor**: Behind the table, render a blurred casino environment -- distant slot machines as colored bokeh lights (randomized position, size, color: amber, red, blue, green), faint silhouettes of other tables. All in heavy gaussian blur (30px+) so it's atmospheric, not distracting.

## AVATAR CUSTOMIZATION & FASHION SYSTEM ("Table Presence")

This is the killer feature. Inspired by Alley Kingz' "Territory Clout" system and Zynga's avatar customization. Players express themselves through fashion, and looking good grants status.

### Avatar Builder (accessible from Profile)
Replace the simple emoji selector with a full avatar customization system:

**Avatar Components (layered SVG/CSS):**
- **Base**: Choose from 8 skin tones (light to dark spectrum)
- **Hair**: 12 styles (fade, locs, braids, ponytail, buzz, wavy, curly, mohawk, bald, slicked back, afro, bob) x 8 colors (black, brown, blonde, red, gray, blue, pink, purple)
- **Eyes**: 6 shapes (round, almond, narrow, wide, sharp, soft) x 4 colors (brown, blue, green, hazel)
- **Expression**: 4 base expressions (confident smile, serious, playful smirk, mysterious)
- **Outfit**: 8 options (casual tee, dress shirt, suit jacket, leather jacket, hoodie, blazer, tank top, tuxedo) x 6 colors each
- **Accessories** (the premium stuff -- some free, most purchasable):
  - **Hats**: Snapback, fedora, beanie, crown (VIP only), none
  - **Glasses**: None, shades, aviators, round specs, diamond-encrusted (premium)
  - **Jewelry**: None, chain, diamond chain (premium), watch, gold watch (premium), earring
  - **Special**: Cigar (animated smoke wisps), headphones, face tattoo, gold tooth smile

**Rendering**: Each avatar component is a layered CSS/SVG element. Compose them into a 120px circular portrait. The avatar appears at the player's seat, in chat, on the leaderboard, and in the profile.

### "Table Presence" Score (Clout System)
Inspired by Alley Kingz' territory mechanic. Your avatar's style + your performance = your Table Presence score.

**Formula**: `Table Presence = (Accessories Score × 1.0) + (Win Streak Bonus × 0.5) + (Level × 2) + (Hands Played ÷ 100)`

**Accessories Score:**
- Free items: 0-1 points each
- Premium items: 2-5 points each
- Legendary/VIP items: 10 points each
- Full "Drip Set" bonus: +15 if all 4 accessory slots filled with premium items

**Table Presence Tiers (displayed as badges):**
| Score Range | Tier | Badge | Color | Perk |
|------------|------|-------|-------|------|
| 0-10 | Fresh | No badge | Gray | -- |
| 11-25 | Regular | Silver circle | Silver | Name visible to table |
| 26-50 | Styled | Gold circle | Gold | Custom seat glow color |
| 51-100 | VIP | Diamond | Purple | 1.1x side bet multiplier |
| 101-200 | High Roller | Crown | Gold shimmer | Priority seating + 1.15x side bet |
| 201+ | Legend | Animated crown + fire | Gold + fire | 1.2x side bet + custom dealer greeting |

**Visual representation at table:**
- Tier badge shown next to player name at their seat
- Higher tier = more elaborate seat border animation
- Legends get a subtle particle effect around their avatar
- When a Legend sits down, the dealer says a custom greeting: "Welcome back, Legend {name}. The table just got interesting."

### Fashion Store (new tab in Shop)
Add a "STYLE" tab alongside chips in the shop modal:

- **Free items**: 4 basic outfits, 2 hairstyles, default accessories -- unlocked at registration
- **Level unlocks**: New items unlock at levels 5, 10, 15, 20, 30, 50 (show locked items grayed out with "Unlocks at Level X")
- **Premium items** (purchased with chips or real money):
  - Accessory Packs: "Street Pack" (500 chips), "Executive Pack" (2000 chips), "Diamond Pack" ($4.99 real money)
  - Individual legendary items: 1000-5000 chips each
  - Seasonal/limited items: Only available during events (creates FOMO/urgency)
- **Preview**: Tapping any item shows your avatar wearing it before purchase
- **"NEW" badge**: Red dot on any item the player hasn't seen yet

## ZYNGA-STYLE SOCIAL HOOKS & RETENTION

These are the features that make Zynga games addictive and profitable. Implement ALL of them.

### 1. Daily Login Rewards (Zynga's #1 retention mechanic)
**Daily Reward Calendar** -- shows when the app/page loads, before entering the lobby:

- Full-screen modal with a 7-day calendar strip (Day 1 through Day 7)
- Each day shows the reward in a gift box:
  - Day 1: 200 chips
  - Day 2: 500 chips
  - Day 3: 1,000 chips + random free accessory
  - Day 4: 1,500 chips
  - Day 5: 2,500 chips + "Lucky Streak" buff (1 hour of 10% bonus on wins)
  - Day 6: 5,000 chips
  - Day 7: 10,000 chips + Exclusive weekly item (rotates each week)
- Current day glows gold and has "CLAIM" button. Past days show checkmark. Future days show lock.
- **Streak counter**: "Day 4 of 7 -- Keep it going!" Progress bar across the top.
- Missing a day resets the streak to Day 1 (this is the hook -- creates daily habit)
- Animation: When claiming, the gift box opens with a burst of gold particles, chips fly into balance counter.
- After claiming, auto-dismiss to lobby.
- **Store in player_accounts**: `last_daily_claim` timestamp and `daily_streak` counter. Check server-side via API call: `{ action: "claim-daily", player_id }`. Returns `{ success, reward, streak_day, next_claim_at }`. Returns error if already claimed today.

### 2. Tournaments (Zynga Poker's biggest engagement driver)

**Tournament Lobby** -- new tab in the blackjack page navigation:

- **Daily Tournament** (free entry):
  - Runs 24 hours, resets at midnight PT
  - All players start with 5,000 tournament chips (separate from regular chips)
  - Play as many hands as you want -- your best cumulative profit in a single "run" (10 consecutive hands) counts
  - Leaderboard ranks players by best run profit
  - Prizes: Top 1: 10,000 chips + "Daily Champion" title (24h). Top 2-5: 5,000 chips. Top 6-10: 2,000 chips. Top 11-25: 500 chips.
  - Show live leaderboard updating in real time

- **Weekend Tournament** (Saturday-Sunday, 1,000 chip entry fee):
  - Same format but 20-hand runs
  - Bigger prize pool: Top 1: 50,000 chips + exclusive weekend accessory. Top 2-3: 25,000 chips. Top 4-10: 10,000 chips.
  - Entry fee goes into prize pool (minus 10% house rake -- this is revenue)

- **Tournament UI**:
  - Tab shows "TOURNAMENTS" with red notification dot when a tournament is active
  - Tournament card: name, time remaining, entrants count, prize pool, your current rank, "ENTER" button
  - During tournament play, show tournament HUD: rank overlay, run counter ("Hand 6 of 10"), run profit, "BEST RUN: +3,200" tracker
  - When tournament ends, show results modal with podium animation (top 3 avatars on a 1st/2nd/3rd podium, confetti)

- **Backend**: Track tournament entries and scores in a `tournament_entries` concept (can use existing leaderboard table with a tournament_id filter, or the frontend can manage tournament state locally for now and use record-hand to track results). For the initial implementation, tournaments can run client-side using the existing blackjack game engine -- just wrap it in a tournament context that tracks the 10/20 hand run and reports the final score.

### 3. Social Gifting (Zynga's viral loop)
- **Send chips to friends**: In the friend list, each friend has a "GIFT" button
- Gift amounts: 100, 500, 1000 chips (sender pays from their balance)
- Recipient gets a notification toast: "{name} sent you 500 chips! [heart]"
- **Daily free gift**: Once per day, send ONE free gift of 100 chips to any friend (costs nothing). Shows "FREE GIFT" badge on the button. This drives daily friend engagement.
- Gifting creates reciprocity -- friends gift back, creating a daily loop
- Show "Gifts Received Today: 3" counter in profile

### 4. Spin-the-Wheel Bonus (every 4 hours)
- A "SPIN" button appears in the lobby with a timer countdown ("Next spin in 2:34:17")
- When available, button glows and pulses
- Clicking opens a wheel with 8 segments:
  - 100 chips (30% chance, green)
  - 250 chips (25%, blue)
  - 500 chips (20%, purple)
  - 1,000 chips (12%, gold)
  - 2,500 chips (8%, red)
  - 5,000 chips (3%, diamond)
  - Free accessory (1.5%, rainbow)
  - JACKPOT 25,000 chips (0.5%, animated gold/fire)
- Wheel spins for 4 seconds with realistic deceleration (cubic-bezier easing)
- Landing segment expands with celebration. Chips fly into balance.
- After spinning, 4-hour cooldown timer starts. Show "Watch an ad to spin again now!" option (ties into ad-to-chip system).
- **Implementation**: Random selection happens client-side with weighted probabilities. Log the result: `{ action: "log-event", player_id, event_type: "wheel_spin", event_data: { result, amount } }`

### 5. VIP Tier System (Zynga's monetization backbone)
Based on total real-money spent. Tiers persist permanently (never demote).

| Total Spent | Tier | Perks |
|------------|------|-------|
| $0 | Free Player | Base experience |
| $0.99+ | Bronze VIP | +10% daily reward, bronze name color, 1 extra daily gift |
| $9.99+ | Silver VIP | +25% daily reward, silver name + sparkle, 2 extra daily gifts, priority support |
| $24.99+ | Gold VIP | +50% daily reward, gold name + glow, 3 extra daily gifts, exclusive Gold accessories, early access to new features |
| $49.99+ | Platinum VIP | +100% daily reward, animated platinum name, unlimited daily gifts, ALL accessories unlocked free, custom table felt color, exclusive Platinum avatar frame |
| $99.99+ | Diamond VIP | Everything above + "Diamond" animated badge, custom dealer dialogue, name on the "Diamond Wall" (visible in lobby), personal welcome message when joining any table |

**Visual treatment**: VIP tier badge shown next to name everywhere (lobby, table, chat, leaderboard). Higher tiers have increasingly elaborate animations (Bronze: static badge, Silver: subtle shine, Gold: rotating shimmer, Platinum: particle trail, Diamond: full animated aura).

**VIP Progress Bar**: Show in profile -- "You've spent $7.42 -- $2.57 more to Silver VIP!" with progress bar. This nudges spending.

### 6. Seasonal Events & Limited Items
- **Current season theme**: Apply a seasonal overlay to the casino environment
  - Spring: Cherry blossom petals floating across the table
  - Summer: Tropical sunset lighting with warm amber tones
  - Fall: Orange/red leaf particles, darker felt color option
  - Winter: Snowflake particles, ice-blue accent lighting, holiday felt
- **Seasonal exclusive items**: 3-5 limited avatar accessories per season (e.g., Winter: santa hat, ugly sweater, candy cane cigar, snowflake glasses, ice crown)
- **Seasonal leaderboard**: Separate from the all-time leaderboard. Resets each season. Top players get exclusive permanent items.
- **Event banner**: At top of lobby, show current event: "WINTER ROYALE -- Earn 2x XP through March 31! Exclusive frost items in the shop!"
- For now, implement the UI framework for seasonal events. Hardcode the current season as "Spring 2026" with placeholder items. The backend can track seasonal scores using the existing leaderboard with a season tag.

### 7. Spectator Mode
- **Watch live games**: In the lobby, each table card shows "WATCH" button alongside "JOIN"
- Spectators see the full table in real-time (cards dealt, bets placed, results) but cannot interact
- Spectator count shown on table card: eye icon + "12 watching"
- Spectators CAN use the emote system and chat (labeled as "[SPECTATOR]" in chat)
- Spectators see a "JOIN TABLE" floating button if seats are available
- This drives FOMO -- watching others win makes players want to play
- Implementation: Same Supabase Realtime subscription as players, but spectator flag prevents action buttons from appearing. Use the existing `join-table` action with a `spectator: true` flag (frontend-managed -- no backend changes needed, just don't show action buttons).

### 8. Achievement System (expanded from V2)
Expand the existing toast notifications into a full achievement gallery:

**Achievement Page** (tab in Profile):
- Grid of achievement cards (4 columns desktop, 2 mobile)
- Unlocked: full color, gold border, earned date
- Locked: grayed out, "???" description, progress bar toward unlock
- Categories: "First Steps", "Grinder", "High Roller", "Social", "Strategy", "Seasonal"

**New achievements beyond V2:**
- "Social Butterfly": Add 5 friends
- "Generous Soul": Send 10 gifts
- "Fashion Icon": Own 20 accessories
- "Tournament Veteran": Enter 10 tournaments
- "Daily Devotee": 30-day login streak
- "Chart Master": Score 95%+ on strategy quiz (50+ questions)
- "Whale Watcher": Spectate 10 games
- "Double Trouble": Win 5 double-downs in a row
- "Split Decision": Win both hands on a split 3 times
- "Perfect Session": Win 10 hands in one session without a loss
- "The Closer": Win the last hand before a tournament ends to place top 3

Each achievement awards XP (50-500 depending on difficulty) and some award exclusive items.

## ECONOMY REBALANCING (from War Room analytics)

The war room flagged that the free chip economy is too generous. Adjust:

### Ad-to-Chip Rebalancing
- **Old**: 100 chips per ad, 10x daily cap = 1,000 free chips/day from ads
- **New**: 25 chips per ad view, 10x daily cap = 250 free chips/day from ads
- This makes purchased chips feel more valuable without killing the free experience
- Show a "Watch Ad for 25 Chips" button (with a small video icon) in the lobby. After watching, show "+25" floating animation. Show remaining ad watches today: "7 of 10 remaining"

### Chip Sinks (things that cost chips to prevent inflation)
- Tournament entry fees (1,000 chips for weekend tournaments)
- Fashion store purchases (500-5,000 chips for accessories)
- Table entry costs (already implemented for high-roller/VIP tables)
- "Lucky Charm" one-time buffs: 500 chips for "10% extra payout for next 5 hands" (cosmetic feel-good mechanic)
- Re-buy after going broke: First re-buy is free (500 chips), second is 250 chips, third requires watching 3 ads or purchasing

### Price Anchoring
- Show the "value" of chip packs in terms of gameplay:
  - 500 chips / $0.99 → "20 hands of play"
  - 3,000 chips / $4.99 → "120 hands + BEST VALUE badge"
  - 8,000 chips / $9.99 → "320 hands + bonus accessory"
- Show a "MOST POPULAR" badge on the $4.99 pack (social proof)

## LOBBY UPGRADE

### Table Cards (enhanced from V2)
Each table card in the lobby should show:
- **3D mini-preview**: A tiny top-down view of the table with current players' avatars visible in their seats (just small circles with their avatar)
- **Live stats ticker**: "Last hand: Player21 won 500 chips!" scrolling text at bottom of card
- **Heat indicator**: Based on recent action -- "HOT" (red fire, many big wins recently), "WARM" (orange, active), "COOL" (blue, quiet). Makes tables feel alive.
- **Spectator count**: Eye icon + number
- **Table atmosphere tag**: "Friendly", "Competitive", "High Stakes", "Chill" -- based on table type

### Lobby Background
- Panning casino floor view (slow CSS background-position animation on a dark gradient with bokeh lights)
- Soft jazz/lounge music option (Web Audio API: generate a smooth sine-wave based ambient loop, or just have a mute/unmute toggle for atmosphere -- use a low-pass filtered oscillator at 220Hz with gentle LFO modulation for a warm ambient hum)
- Player's avatar + name + chip balance + VIP badge displayed prominently at top of lobby

## MULTI-HAND MODE (inspired by 1x2 Network & NetEnt)
Allow players to play up to 3 hands simultaneously at the same table:

- "MULTI-HAND" toggle in the game settings (or on the table)
- When enabled, show 3 betting circles in front of the player instead of 1
- Player places independent bets on each hand
- Cards dealt to all 3 positions
- Player acts on each hand left to right (highlight active hand with gold glow, dim others)
- Each hand resolves independently
- Minimum bet applies per hand (so 3 hands at 25 min = 75 chip minimum total)
- Balance updates after all hands resolve
- This dramatically increases engagement and bet volume
- **Implementation**: The frontend manages 3 parallel hand states. Each hand calls record-hand separately with the same round_number but different data. The existing API already supports this -- just send 3 record-hand calls per round.

## MOBILE OPTIMIZATION (critical for Zynga-level quality)
- **Touch targets**: All buttons minimum 48x48px
- **Swipe gestures**: Swipe up on cards to Hit, swipe right to Stand, double-tap to Double Down, spread-pinch on pairs to Split
- **Portrait mode**: Table rotates to fill portrait view on phones. Cards and buttons resize.
- **Performance**: Limit particle effects to 50% on mobile (detect via `navigator.hardwareConcurrency < 4`). Reduce bokeh lights from 20 to 8. Disable ambient dust particles.
- **Haptic feedback**: Use `navigator.vibrate()` on supported devices -- short buzz (50ms) on card deal, double buzz on win, long buzz on blackjack/jackpot
- **Bottom sheet UI**: On mobile, move chat/emotes/profile into a swipe-up bottom sheet instead of side panel
- **Loading**: Show Everlight logo with a gold loading bar. Target < 3 second initial load.

## SOUND DESIGN UPGRADE
Add to existing sound set:
- **Ambient casino**: Low background murmur (filtered noise at very low volume). Toggle on/off.
- **Chip stacking**: When viewing chip count, subtle coin clink
- **Avatar dress-up**: Fabric swoosh sound when changing clothes
- **Tournament horn**: Brass fanfare when tournament starts/ends
- **Wheel spin**: Clicking/ticking that slows with the wheel
- **Daily reward**: Musical gift box opening jingle
- **Friend notification**: Warm two-tone chime
- **VIP upgrade**: Orchestral swell + ding

## IMPLEMENTATION PRIORITY
Build these features in this order:
1. **Daily Login Rewards** -- highest retention impact, simplest to build
2. **Avatar Customization** -- the "wow" factor that differentiates from every other blackjack app
3. **Table Presence / Clout Score** -- makes avatars meaningful, drives fashion purchases
4. **VIP Tier System** -- monetization backbone
5. **Spin-the-Wheel** -- easy engagement loop
6. **Fashion Store** -- monetizes the avatar system
7. **Tournaments** -- competitive engagement
8. **Multi-Hand Mode** -- increases bet volume
9. **Social Gifting** -- viral loop
10. **Spectator Mode** -- FOMO driver
11. **Seasonal Events** -- long-term retention framework
12. **Achievement Gallery** -- completionist hook
13. **Lobby visual upgrade** -- polish
14. **3D visual enhancements** -- premium feel

Start with items 1-6 in this prompt. Items 7-14 can be implemented in a follow-up if needed, but include the UI placeholders and navigation tabs for all of them now.

## DO NOT BREAK EXISTING FEATURES
- All V2 features must continue working (dealing, hitting, standing, doubling, splitting, chat, emotes, friends, leaderboard, strategy center, shop, sessions)
- All API endpoints remain the same
- All existing animations remain
- This is additive -- layering premium features on top of the working foundation
