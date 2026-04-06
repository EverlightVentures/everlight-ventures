# LOVABLE PROMPT: Everlight Blackjack -- Unified Merge Build

Paste everything below the line into Lovable. This is a full rebuild prompt that merges the best features from two existing versions of Everlight Blackjack into one unified experience. Do not remove any existing Supabase integrations, edge functions, or player data. All existing database tables (players, purchases, VIP) remain unchanged.

---

## OVERVIEW

You are rebuilding the Everlight Blackjack game experience on Lovable by combining two source versions:

- **Version A (Django/local)**: A Three.js-powered 3D casino with a cinematic loading sequence, dealer chip tray rendered in 3D, bot players with labels projected from 3D space, a categorized shop with filter chips, and a full arcade entry portal feel.
- **Version B (current Lovable)**: Oval felt table, Supabase-backed user profiles, custom chip designs, daily rewards, missions, VIP tiers, tournaments, ElevenLabs dealer voice, NPC bots with human names and randomized behavior.

The goal: one unified product that feels like walking into a premium digital casino. Keep everything that already works in Lovable. Layer on the visual and UX upgrades from the Django version.

---

## PART 1: ARCADE ENTRY PORTAL

### What to build

Replace any plain page load or simple fade-in with a cinematic boot sequence. This is how Version A handles the entry -- the player sees a black screen with the brand name, a gold loading bar, and status messages that tick through stages. It makes the experience feel like launching a real game, not loading a web page.

### Implementation

When the user navigates to `/arcade/blackjack`, show a full-screen loading overlay (z-index above everything) with:

1. **Brand title** -- "EVERLIGHT BLACKJACK" in Cinzel font, large, with a gold gradient text effect (background-clip: text, gradient from #c9a84c to #f0d080).
2. **Progress bar** -- 300px wide, 4px tall, dark background, gold gradient fill that animates from 0% to 100%.
3. **Status text** -- Below the bar, small caps, faded white. Cycle through these messages with 300-500ms delays:
   - "LOADING ASSETS..."
   - "BUILDING CASINO TABLE..."
   - "SUMMONING AVATARS..."
   - "DEALING THE DECK..."
   - "IGNITING ATMOSPHERE..."
   - "WELCOME TO EVERLIGHT"
4. After the sequence completes, fade the overlay out over 600ms, then remove it from the DOM.

The loading overlay must block interaction until complete. It should run the actual initialization behind it (table render, Supabase auth check, profile fetch, bot spawn) so there is zero dead time after it fades.

### Auth gate

After the loading overlay fades:
- If the user is authenticated via Supabase, go straight to the table.
- If not, show the auth panel (sign in / register / play as guest) as a centered overlay on top of the table scene. The table should be visible but dimmed behind it. Guest mode gives 1,000 chips, no persistence.

---

## PART 2: TABLE DESIGN -- OVAL FELT WITH 3D DEPTH

### What to keep from Lovable
- The oval felt table shape (not the round cylinder from Django).
- The existing card rendering, hand value display, and bet controls.
- Custom chip designs that players have purchased.

### What to add from Django

Add visual depth and perspective to the oval felt table using CSS transforms. The table should feel like you are looking down at it from a slight angle, not viewing a flat 2D surface.

Apply these CSS properties to the table container:

```css
.blackjack-table-wrapper {
  perspective: 1200px;
  perspective-origin: center 60%;
}

.blackjack-table {
  transform: rotateX(18deg) translateZ(0);
  transform-style: preserve-3d;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.7),
    0 0 80px rgba(201, 168, 76, 0.08),
    inset 0 2px 40px rgba(0, 0, 0, 0.3);
}
```

Add a gold trim border around the oval (2px solid with color #c9a84c at 40% opacity). Add a subtle pulsing glow on the table edge -- animate the box-shadow gold component between 0.05 and 0.12 opacity on a 4-second CSS keyframe loop.

The background behind the table should be very dark (#04040a), with a radial gradient spotlight effect centered above the table to simulate overhead casino lighting:

```css
.table-scene-bg {
  background:
    radial-gradient(ellipse 60% 40% at 50% 35%, rgba(201, 168, 76, 0.06), transparent 70%),
    radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0, 0, 30, 0.3), transparent),
    #04040a;
}
```

### Ambient particles

Add a floating dust/gold particle layer using a canvas overlay (pointer-events: none, z-index above background but below UI). Spawn 60-100 small circles (2-4px) with color #c9a84c at 20-40% opacity. Each particle drifts slowly upward and horizontally with slight randomness. Recycle particles that leave the viewport. This is decorative only -- keep it subtle and performant.

---

## PART 3: DEALER CHIP TRAY (VISUAL ONLY)

### What to build

Add a visual dealer chip tray on the table, positioned behind the dealer's card area (toward the top of the oval). This is decoration -- it is not interactive and does not represent real chip counts.

### Layout

- A dark rectangular tray (rounded corners, background rgba(20, 20, 20, 0.8), border 1px solid rgba(201, 168, 76, 0.3)).
- Inside the tray: 5 stacks of chips rendered as small colored circles stacked vertically with 2-3px overlap.
- Stack colors (left to right): red (#e74c3c), green (#27ae60), blue (#2980b9), purple (#8e44ad), gold (#c9a84c).
- Each stack has 4-6 chips visible.
- Each chip is a 24px diameter circle with a radial gradient, a thin white inner ring, and a slight drop shadow.

### CSS structure

```css
.dealer-chip-tray {
  display: flex;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(20, 20, 20, 0.8);
  border: 1px solid rgba(201, 168, 76, 0.3);
  border-radius: 6px;
  margin: 0 auto 8px;
  width: fit-content;
}

.chip-stack {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
  gap: -2px; /* use negative margin on children instead */
}

.tray-chip {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  margin-bottom: -6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}
```

Position the tray between the dealer label and the dealer's cards. It should scale down on mobile but remain visible.

---

## PART 4: SHOP OVERHAUL -- DJANGO LAYOUT

### What to replace

Replace the current Lovable shop UI with the categorized, filtered shop layout from the Django version. The Django shop has:

1. **Currency display bar** at the top showing current chips and gems, plus a "BUY GEMS" button.
2. **Filter chips row** -- horizontal scrollable row of pill-shaped filter buttons: ALL, OUTFITS, ACCESSORIES, AURAS, CARD BACKS, TABLE FELTS, TITLES. Active filter has gold border and text.
3. **2-column grid** of shop items.
4. Each item card shows:
   - Rarity label (top, color-coded: common=#aaa, rare=#3498db, epic=#9b59b6, legendary=#c9a84c)
   - Item name (bold)
   - Price in chips (orange) and/or gems (blue) and/or USD
   - "OWNED" badge (green, top-right) if already purchased
   - Rank requirement if applicable (small orange text)
5. Clicking an unowned item triggers purchase flow.
6. Owned items are dimmed (opacity 0.5) and not clickable.

### Implementation details

Keep all existing Supabase shop data fetching and purchase endpoints (`verify-arcade-purchase`, `create-checkout`). Just rebuild the UI layer.

```css
.shop-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.filter-chip {
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.filter-chip.active {
  border-color: #c9a84c;
  color: #c9a84c;
  background: rgba(201, 168, 76, 0.1);
}

.shop-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.shop-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.shop-item:hover {
  border-color: #c9a84c;
  background: rgba(201, 168, 76, 0.06);
}

.shop-item.owned {
  opacity: 0.5;
  cursor: default;
}
```

On mobile, the grid collapses to 1 column below 400px width.

---

## PART 5: KEEP ALL EXISTING LOVABLE FEATURES

Do NOT remove or break any of the following. These stay exactly as they are:

### User profiles
- Supabase auth (email/password + OAuth)
- Player row in `players` table: chips, gems, xp, rank, avatar, vip_tier
- Profile panel showing stats, win rate, hands played, best streak

### Custom chips
- Player-purchased chip designs stored in Supabase
- Chip appearance changes based on owned cosmetics
- Chip selection in avatar studio

### Rewards and missions
- Daily login rewards
- Mission system (play X hands, win X in a row, etc.)
- Mission progress tracking
- Reward claim flow

### VIP system
- VIP tiers with benefits
- Game pass purchases via Stripe
- VIP badge display

### ElevenLabs dealer voice
- Edge function `dealer-speak`
- Audio caching on frontend
- Browser TTS fallback

### NPC bot system
- Human name pool (Marcus, DeShawn, Aaliyah, etc.)
- Randomized chip stacks per bot
- Timed sit/walk behavior (3-12 min arrival, 5-25 min stay)
- Basic strategy decision engine with think delay
- Thinking bubble animation

### AI Strategy Coach
- Keep the coach panel and all coaching logic

### Tournaments and leaderboards
- Keep tournament system
- Keep leaderboard (Hall of Legends) panel

---

## PART 6: SUPABASE DATA CONTRACT

All game state reads and writes go through Supabase. No local-only persistence for authenticated users.

### Tables used (do not modify schema)
- `players` -- chips, gems, xp, rank, avatar JSON, vip_tier, hands_played, hands_won, best_streak, biggest_win, win_rate, presence_multiplier
- `purchases` -- item_id, player_id, currency, timestamp
- `shop_items` -- item_id, name, category, rarity, price_chips, price_gems, price_usd, rank_required

### Edge functions used (do not modify signatures)
- `blackjack-api` -- deal, hit, stand, double, surrender, settlement
- `create-checkout` -- Stripe checkout for gem packs and VIP
- `verify-gem-purchase` -- confirm Stripe payment, credit gems
- `verify-arcade-purchase` -- confirm Stripe payment, credit shop item
- `dealer-speak` -- ElevenLabs TTS

### Auth flow
- Supabase Auth handles sign-up, sign-in, OAuth (Google, Facebook)
- On auth state change, fetch or create player row
- Guest mode uses local state only -- no Supabase writes

---

## PART 7: DESIGN SYSTEM

### Fonts
- **Display / headings**: Cinzel (serif), weights 400/700/900
- **Body / UI**: Inter (sans-serif), weights 300/400/600

### Color palette
```
--gold:          #c9a84c
--gold-light:    #f0d080
--green-felt:    #0d5c2e
--dark:          #04040a
--panel-bg:      rgba(8, 9, 15, 0.92)
--border-gold:   1px solid rgba(201, 168, 76, 0.4)
--chip-red:      #e74c3c
--chip-green:    #27ae60
--chip-blue:     #2980b9
--chip-purple:   #8e44ad
--chip-gold:     #c9a84c
```

### Button styles
- **Primary (Deal, Save, Purchase)**: Gold gradient background (#c9a84c to #f0d080), black text, Cinzel font, gold glow on hover.
- **Hit**: Green background (rgba(39, 174, 96, 0.9)), white text.
- **Stand**: Red background (rgba(231, 76, 60, 0.9)), white text.
- **Double**: Blue background (rgba(52, 152, 219, 0.9)), white text.
- **Surrender**: Gray background (rgba(127, 140, 141, 0.9)), white text.
- **Clear/Cancel**: Dark background with gray border, muted text.

### Panel overlays
All modal panels (shop, profile, avatar studio, leaderboard, gem packages, settings) use:
- Full-screen backdrop with rgba(0, 0, 0, 0.8)
- Centered card with panel-bg background, gold border, 16px border radius, 32px padding
- Max-width 520px (or 600px for avatar studio)
- Close button top-right
- Title in Cinzel, gold color, 2px letter spacing

### Mobile behavior
- All panels scroll vertically if content exceeds viewport
- Shop grid goes to 1 column below 400px
- Chip buttons shrink from 56px to 42px below 700px
- Card size shrinks from 60x84 to 44x62 below 700px
- Dealer chip tray scales to 80% on mobile

---

## PART 8: RESULT ANIMATIONS

Keep the existing result banner system but make sure it matches this spec:

- **Win**: Gold text, gold particle burst (120 particles, gold/white colors, explode from center, gravity pull down, 2-second lifetime)
- **Blackjack**: Brighter gold text, larger particle burst, dealer voice "Blackjack! Congratulations."
- **Loss/Bust**: Red text, no particles
- **Push**: Gray text, no particles
- **Surrender**: Gray text, "HALF BET RETURNED" subtitle

The banner animates in with a scale-up bounce (cubic-bezier(0.34, 1.56, 0.64, 1)), holds for 2 seconds, then fades out. The result banner should appear centered over the table.

---

## PART 9: BOT LABEL POSITIONING

Bots sit at specific seats around the oval table. Their name labels and chip counts should be positioned relative to their seat positions on the table. The labels should include:

- Bot name (light blue-white color)
- Chip count (gold color)
- Brief action flash ("WIN +150", "BUST", "PUSH") that appears for 1.2 seconds after each bot hand resolves, then reverts to just name + chips

Position the labels at the outer edge of the table oval, one at each seat. The player always sits at the center-bottom seat. Bots fill 2-4 of the remaining seats with randomized timing.

---

## PART 10: TOP BAR HUD

The top bar spans the full width, fixed at the top, with a gradient fade from dark to transparent. Contents left to right:

1. **Brand mark** -- "EVERLIGHT" in Cinzel, gold gradient text, 1.3rem
2. **Chips pill** -- Dark background, gold border, shows chip icon + count
3. **Gems pill** -- Same style, gem icon + count
4. **Rank badge** -- Right-aligned, shows rank emoji + rank name in gold Cinzel text
5. **Menu buttons** -- PROFILE, AVATAR, SHOP, RANKS, FREE CHIPS -- small gold-bordered buttons in Cinzel font

On mobile, collapse menu buttons into a hamburger or bottom nav.

---

## PART 11: PRESENCE MULTIPLIER

Display the current table presence multiplier in the top-left corner below the top bar:

- Label: "TABLE PRESENCE" (tiny, faded white, letter-spaced)
- Value: "1.00x" (gold, bold, 1.1rem)
- Dark background pill with gold border
- Updates when avatar outfit/aura changes
- Presence multiplier affects chip payouts on wins (purely visual motivation for cosmetic purchases)

---

## SOCIAL CASINO DISCLAIMER

At the bottom of the page (below the game area), include a small, always-visible disclaimer:

> Everlight Blackjack is a social casino game for entertainment only. All currency is virtual. No real money can be won or redeemed. Purchases are for virtual items only. You must be 18+ to play.

Style: 0.7rem, rgba(255, 255, 255, 0.3), centered, max-width 600px, 20px padding.

---

## DO NOT BREAK

- Existing Supabase table schemas
- Existing edge function signatures
- Stripe checkout flow
- ElevenLabs voice integration
- Daily rewards logic
- Mission tracking
- VIP tier benefits
- NPC bot behavior from V4
- AI coach functionality
- Tournament system
- Leaderboard system

This prompt adds visual and UX upgrades only. All backend contracts remain identical.
