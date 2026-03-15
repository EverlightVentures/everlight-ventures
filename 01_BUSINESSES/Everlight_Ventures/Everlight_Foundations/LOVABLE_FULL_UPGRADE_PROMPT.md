# LOVABLE PROMPT: Blackjack Full Upgrade -- Persistence, Dealer AI, Bots & Polish

This is a MAJOR upgrade to the existing Everlight Arcade blackjack game. Do NOT rebuild from scratch -- upgrade what exists. Implement ALL fixes and features below.

**Supabase API:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Both headers use the same key:**
- `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
- `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

---

## PROMPT:

---

## SECTION 1: FIX DATA PERSISTENCE (CRITICAL -- Nothing saves)

### Problem
Hands played, wins, losses, achievements, and player history are NOT being saved. The game runs blackjack logic locally but NEVER reports results to the API. This is the #1 bug.

### Fix: Call `record-hand` After EVERY Hand

After every blackjack hand resolves (player wins, loses, pushes, or gets blackjack), the frontend MUST call the API:

```typescript
const recordHand = async (playerId: string, sessionId: string | null, tableId: string | null, betAmount: number, result: 'win' | 'loss' | 'blackjack' | 'push' | 'bust', payout: number, playerCards: string[], dealerCards: string[], playerTotal: number, dealerTotal: number) => {
  try {
    const res = await fetch('https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
      },
      body: JSON.stringify({
        action: 'record-hand',
        player_id: playerId,
        session_id: sessionId,
        table_id: tableId,
        bet_amount: betAmount,
        result: result,
        payout: payout,
        player_cards: playerCards,
        dealer_cards: dealerCards,
        player_total: playerTotal,
        dealer_total: dealerTotal,
      }),
    });
    const data = await res.json();
    if (data.success) {
      // Update local chip balance from server response (source of truth)
      setChipBalance(data.new_balance);
      setXp(data.xp);
      setLevel(data.level);
    }
    return data;
  } catch (err) {
    console.error('Failed to record hand:', err);
  }
};
```

**IMPORTANT RULES:**
- Call this AFTER every hand, not before. The hand must be fully resolved first.
- The `result` field must be one of: `"win"`, `"loss"`, `"blackjack"`, `"push"`, `"bust"`
- `payout` is the total amount returned to the player (bet + winnings for a win, 0 for a loss, bet amount for a push)
- After calling `record-hand`, update the LOCAL chip balance from `data.new_balance` -- the server is the source of truth
- Card format: `["AH", "KS", "10D", "7C"]` (rank + suit letter)
- If `record-hand` fails, do NOT block gameplay. Log the error and continue. Retry on next hand.

### Fix: Call `start-session` on Game Load

When a player enters a blackjack table, call:
```typescript
const res = await fetch(API_URL, {
  method: 'POST', headers: API_HEADERS,
  body: JSON.stringify({ action: 'start-session', player_id: playerId, table_id: tableId }),
});
const { session_id } = await res.json();
// Store session_id in state -- pass it to every record-hand call
```

### Fix: Call `end-session` on Game Exit

When a player leaves a table or navigates away:
```typescript
await fetch(API_URL, {
  method: 'POST', headers: API_HEADERS,
  body: JSON.stringify({ action: 'end-session', player_id: playerId, session_id: sessionId }),
});
```

Also call `end-session` on `beforeunload` event as a safety net.

### Fix: Player History Page

The action is `get-history` (NOT `get-hand-history`). In the player profile/stats page, fetch and display:
```typescript
const res = await fetch(API_URL, {
  method: 'POST', headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-history', player_id: playerId, limit: 50 }),
});
const { history } = await res.json();
// Display as a list: date, result, bet, payout
```

---

## SECTION 2: FIX GOOGLE/FACEBOOK OAUTH LOGIN

### Problem
Google login loops forever because the frontend calls `register` (requires DOB) instead of the new `oauth-login` action.

### Fix
After Supabase Auth confirms the OAuth session via `onAuthStateChange` or `getSession`, call:

```typescript
const bridgeOAuthToPlayer = async (authUser: any) => {
  const res = await fetch('https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
      'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww',
    },
    body: JSON.stringify({
      action: 'oauth-login',
      email: authUser.email,
      display_name: authUser.user_metadata?.full_name || authUser.email?.split('@')[0] || 'Player',
      avatar_url: authUser.user_metadata?.avatar_url || null,
      provider: authUser.app_metadata?.provider || 'google',
    }),
  });
  const data = await res.json();
  if (data.success && data.player) return data.player;
  throw new Error(data.error || 'OAuth bridge failed');
};
```

- Use `oauth-login` for Google/Facebook users, `login` for email users
- Store `auth_return_to` in localStorage BEFORE triggering OAuth, redirect there after
- Default landing: `/arcade` (NEVER `/arcade/rewards`)
- Store player profile in localStorage for session persistence across refresh
- Max 2 retries on failure, then show "Use email login instead"
- Remove any "Coming Soon" labels on Google/Facebook buttons

---

## SECTION 3: DEALER AI -- Voice & Personality

### 3.1 Dealer Voice (Text-to-Speech)

> **UPGRADED in V4:** The dealer now uses ElevenLabs hyper-realistic voice via the `dealer-speak`
> Supabase Edge Function. See `LOVABLE_BLACKJACK_V4_PROMPT.md` Part 1 for the full implementation.
> The Web Speech API below is kept as the fallback only.

```typescript
const dealerSpeak = (text: string) => {
  if (!('speechSynthesis' in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 0.9;
  // Fallback: browser TTS (ElevenLabs is primary via V4 dealer-speak edge function)
  const voices = speechSynthesis.getVoices();
  const preferred = voices.find(v => v.name.includes('Daniel') || v.name.includes('Google UK English Male') || v.name.includes('James'));
  if (preferred) utterance.voice = preferred;
  speechSynthesis.speak(utterance);
};
```

### 3.2 Dealer Personality Lines

The dealer should have character. Add these contextual voice lines (spoken via TTS and printed on table):

**On Deal:**
- "Cards are out. Let's see what we're working with."
- "Fresh hand, fresh luck. Maybe."
- "Alright, let's do this."

**On Player Blackjack:**
- "Twenty-one on the nose. Respect."
- "Natural blackjack! Don't spend it all in one place."
- "Well well well... somebody came to play."

**On Player Bust:**
- "Ooh, that's a tough one. House takes it."
- "Little too ambitious there, friend."
- "Went one card too many. It happens."

**On Player Win:**
- "Winner winner. Chips coming your way."
- "Nice hand. You're making my boss nervous."
- "Clean win. Well played."

**On Dealer Bust:**
- "I busted. That's embarrassing."
- "Too many cards, not enough luck. You win."
- "Dealer goes over. Drinks are on me."

**On Push:**
- "Push. Nobody wins, nobody loses. Boring."
- "We matched. Money stays where it is."

**On Player Stand:**
- "Standing pat. Interesting choice."
- "Okay, let's see what I've got."

**On Player Hit:**
- "One more coming your way."
- "Feeling brave? Here you go."

Pick randomly from the category each time. Add a volume toggle/mute button in the game UI (speaker icon, top-right of table area). Default: ON.

### 3.3 GPT Dealer Chat (Optional Enhancement)

If possible, add a chat input at the table where players can talk to the dealer. The dealer responds with personality using an AI API. For MVP, use pre-written responses triggered by keywords:

| Player says | Dealer responds |
|-------------|----------------|
| "hi" / "hello" / "hey" | "Welcome to the table. Ready to play?" |
| "nice" / "thanks" | "That's what I'm here for." |
| "rigged" / "cheating" | "Every hand is verified fair. Check the fairness page if you don't believe me." |
| "tip" | "Appreciate the thought. Save it for the jukebox." |
| anything else | "Interesting. How about we focus on the cards?" |

---

## SECTION 4: PLAYER BOTS (Make Tables Feel Alive)

### 4.1 Bot Players at Tables

Tables should feel active and populated. Add AI bot players that sit at tables and play:

**Bot Names (pool -- pick randomly):**
LuckyLeo, CardShark99, VegasVince, AceHunter, BlackjackBetty, ChipChaser, RoyalFlush_Rick, NeonNina, HighRoller_Hank, CasinoQueen, MidnightMike, DiamondDave, JackpotJen, SlickSam, WildCard_Wendy, BetBoss, TableTitan, RollingRuby, CoolHand_Cal, PokerFace_Pat

**Bot Behavior:**
- Each standard/casual table should have 1-3 bots sitting when no real players are present
- When a real player joins, bots stay (makes table feel alive)
- Bots play basic strategy 80% of the time, random 20%:
  ```
  Basic strategy (simplified):
  - Hard 17+: Always stand
  - Hard 12-16 vs dealer 2-6: Stand, vs 7+: Hit
  - Hard 11: Always double (or hit if double not available)
  - Hard 10 vs dealer 2-9: Double, else hit
  - Soft 17 (A+6): Hit
  - Always split Aces and 8s
  - Never split 10s or 5s
  - 20% of the time: make a random choice instead
  ```
- Bots bet between table min and 5x table min (random)
- Bots have randomized chip balances (5,000 - 50,000)
- Bots occasionally send chat messages: "Nice hand!", "Tough break", "Let's go!", "Dealer's hot tonight"
- Bot avatars: use generated character icons (NOT emojis)
- Bots have a small "BOT" badge visible on their seat (transparency -- players should know)

**Bot Rules:**
- NO bots on VIP, High Roller, Diamond Lounge, or Penthouse tables
- NO bots in tournaments
- NO bots in private tables
- Bots do NOT appear on the leaderboard
- Bot hands are NOT recorded to the API (purely cosmetic/local)

### 4.2 Table Lobby -- Show Activity

On the table selection screen, each table card should show:
- Table name and type
- Current player count: "3/5 players" (includes bots)
- Min/max bet range
- A subtle "LIVE" pulse indicator (green dot, gently pulsing) on active tables
- If real players are present, show their avatars on the table card

---

## SECTION 5: ACHIEVEMENTS SYSTEM

Track achievements on the FRONTEND and display them. The backend doesn't have an achievements table yet, so track in localStorage and display from the player's stats.

### Achievement Definitions

| Achievement | Condition | Reward |
|-------------|-----------|--------|
| First Hand | Play 1 hand | 50 chips |
| Getting Started | Play 10 hands | 200 chips |
| Card Shark | Play 100 hands | 1,000 chips |
| First Blood | Win 1 hand | 100 chips |
| Hot Streak | Win 5 hands in a row | 500 chips |
| On Fire | Win 10 hands in a row | 2,000 chips |
| Natural | Get a blackjack | 250 chips |
| Blackjack Master | Get 10 blackjacks | 2,500 chips |
| High Roller | Bet 1,000+ on a single hand | 500 chips |
| Whale | Bet 10,000+ on a single hand | 2,500 chips |
| Comeback Kid | Win after being down to less than 100 chips | 1,000 chips |
| Lucky 7 | Log in 7 days in a row | 500 chips + streak shield |
| Socializer | Send 10 chat messages | 100 chips |
| Big Winner | Win 10,000+ chips in a single session | 1,000 chips |

### Achievement UI
- When an achievement unlocks: toast notification slides up from bottom with gold border, achievement name, and reward amount
- Dealer says a voice line: "Achievement unlocked! Nice work."
- Achievement icon + name + date earned displayed in the player's profile under "Achievements" tab
- Unearned achievements shown grayed out with progress bar (e.g., "Card Shark: 47/100 hands")
- Store earned achievements in localStorage: `{ achievement_id: timestamp }`
- On earning: call `update-balance` to add the chip reward

---

## SECTION 6: FASHION & COSMETICS -- Earned, Not Free

### Problem
Fashion/glamor items are currently free for everyone. They must be EARNED or PURCHASED.

### Fix: Cosmetics Economy

**All cosmetic items (card backs, table themes, avatar items, emotes) must be:**
1. **Locked by default** -- show a lock icon overlay
2. **Unlockable via one of:**
   - Achievement (earn it through play)
   - Gem purchase (buy with gems)
   - Level milestone (reach level 5, 10, 20, etc.)
   - Master Pass (exclusive items for members)

**Cosmetic Categories:**

| Category | Free Items | Earnable | Purchasable (Gems) | Master Pass Exclusive |
|----------|-----------|----------|--------------------|-----------------------|
| Card Backs | 2 basic | 3 (achievements) | 5 (50-200 gems each) | 3 exclusive |
| Table Themes | 1 default | 2 (level milestones) | 3 (100-300 gems) | 2 exclusive |
| Emotes | 5 basic | 5 (achievement) | 10 (25-100 gems) | 5 exclusive |
| Avatar Frames | 1 default | 3 (rank/level) | 3 (150 gems) | 2 exclusive (gold ring) |
| Dealer Skins | 1 default | 0 | 2 (500 gems) | 1 exclusive |

**Cosmetic Shop (inside each game's settings, NOT a separate store page):**
- Show all items in a grid
- Locked items: dimmed with lock icon
- Below each locked item: how to unlock ("Win 10 blackjacks" or "200 Gems" or "Master Pass")
- Tapping a gem-purchasable item shows inline confirmation (not a popup)
- Equipped items have a gold checkmark

**IMPORTANT:** Replace all emoji-based cosmetics with placeholder text descriptions until real artwork is generated. Remove emoji avatars from the player table seats. Keep emojis ONLY in the chat system.

---

## SECTION 7: PRIVATE TABLES & TOURNAMENTS

### 7.1 Private Tables -- Implement NOW (Remove "Coming Soon")

Remove the "Coming Soon" label. Implement:

- "Create Private Table" button on the table lobby
- Generates a 6-character invite code (alphanumeric)
- Creator becomes host with controls: min/max bet, deck count
- Share code via a "Copy Code" button + "Share Link" button
- Private tables show in lobby ONLY for players with the code
- Max 5 players per private table
- Host can kick players
- Use the existing `invite-friend` and `get-invites` API actions for the invite flow

### 7.2 Tournament Tables -- Implement NOW (Remove "Coming Soon")

Remove the "Coming Soon" label. Implement a simple tournament structure:

**Daily Free Tournament:**
- Entry: Free, available once per day
- Format: 10-hand sprint with 5,000 tournament chips (separate from real balance)
- Scoring: Final chip count = score
- Leaderboard: Top 10 shown, updates in real-time during the day
- Prizes: 1st = 2,000 chips, 2nd = 1,000 chips, 3rd = 500 chips
- Reset daily at midnight PT
- Tournament table has a unique design (green felt with gold trim border)

**Weekend Tournament (Saturday-Sunday):**
- Entry: 1,000 chips from real balance
- Format: 20-hand sprint
- Prizes: 1st = 10,000 chips, 2nd = 5,000, 3rd = 2,500
- Top 3 get podium animation and "Tournament Champion" badge for the week

---

## SECTION 8: REMOVE PLAYER AVATAR FROM TABLE

Remove the player's avatar/emoji icon from the table view during gameplay. The seat should show:
- Player name (text only)
- Chip count
- Current bet
- Cards

No avatar, no emoji, no profile picture at the table seats. Keep it clean and card-focused.

---

## SECTION 9: ARTWORK ASSET LIST (For AI Generation)

Replace all emoji graphics with proper game art. Until custom artwork is generated, use clean SVG icons or simple illustrated placeholders. Here is the complete list of artwork needed:

### Dealer Character
- **Main dealer portrait**: Professional male dealer, mid-30s, slicked-back dark hair, subtle confident smile, black vest over white dress shirt, gold name tag reads "HOUSE". Shoulders-up portrait, dark casino background with bokeh lights. Photorealistic style, warm lighting.
- **Dealer expressions** (variants of same character): neutral, smirk (player bust), impressed (player blackjack), shrug (push), wince (dealer bust)

### Card Assets
- **Custom card back designs** (5 variations): Classic red, Midnight blue, Gold foil, Neon green, Everlight purple with "E" monogram
- **Card face design**: Clean, modern playing cards with sharp typography, slightly rounded corners

### Table Assets
- **Table felt**: Top-down view of blackjack table with betting circles, clean layout
- **Chip stacks**: 3D-style chip illustrations in 5 colors (white=$1, red=$5, green=$25, black=$100, purple=$500, gold=$1000)

### UI Icons (replace all emojis)
- **Achievement badges**: 14 unique icons matching each achievement
- **Rank icons**: Bronze shield, Silver shield, Gold shield, Diamond shield, Crown
- **Status icons**: Win (gold star), Loss (red X), Push (gray equals), Blackjack (gold 21)

### Avatar Frames
- **Default**: Simple gray circle
- **Level 5**: Blue ring
- **Level 10**: Purple ring
- **Level 20**: Gold ring
- **Master Pass**: Animated gold ring with subtle pulse

### Prioritized Generation Order (for limited Seedance credits)
1. Dealer portrait (main + 3 expressions) -- 4 images, ~80 credits
2. Card back designs (5) -- ~100 credits
3. Chip illustrations (6 colors) -- ~120 credits
4. Achievement badges (14) -- ~280 credits
5. Table felt + UI -- ~120 credits
**Total: ~700 credits** (leaves buffer from 1,300)

For dealer video (breathing/live effect): Generate a 3-second loop of the dealer portrait with subtle head movement and blink. Use remaining ~300 credits for 1 video. Display as a looping video element behind the dealer's chat area.

---

## SECTION 10: BACK ARROWS ON ALL PAGES

Add a back arrow (chevron-left, 24px) top-left of EVERY arcade sub-page:
- Touch target: 44x44px
- Color: #8A8A8A, brightens to #E5E5E5 on tap
- Routes to logical parent (not browser history):
  - `/arcade/blackjack` → `/arcade`
  - `/arcade/blackjack/table/:id` → `/arcade/blackjack`
  - `/arcade/lounge` → `/arcade`
  - `/arcade/membership` → `/arcade`
  - `/arcade/rewards` → `/arcade`
  - `/arcade/profile` → `/arcade`
- `/arcade` (hub) has NO back arrow
- Mobile: sticky top bar (48px) with back arrow + page title
