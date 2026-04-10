# Everlight Ventures Site Enhancement Plan

## Context
Backend infrastructure just deployed (5 Edge Functions, 8 DB tables, Stripe webhook, Slack). Ebook purchases work end-to-end. Two customers paid but never got downloads. User wants: copy protection, per-game arcade shops, 3D game embedded, site audit, and customer recovery with README in downloads.

---

## PHASE 1: CUSTOMER RECOVERY + README (Do First)

### 1A. Add README.txt to all 7 download ZIPs
- Extract each ZIP in `Everlight_Literature/Ebook_Sells/Download_Packages/`
- Add README.txt: extract ZIP, open HTML in browser, EPUB for ebook readers
- Re-ZIP all 7, re-upload to Supabase "Ebooks" bucket

### 1B. Email the 2 affected customers
- Query `ebook_purchases` for earliest purchases to get emails + slugs
- Generate 7-day signed URLs for their book + Book 2 (free gift)
- Draft email: apology, links, free Book 2, README instructions

### 1C. Confirmation email Edge Function (future purchases)
- New: `send-confirmation-email/index.ts` using Resend API (free 3k/mo)
- Called after `verify-ebook-purchase` succeeds
- Sends: thank you, download link, instructions, support email

---

## PHASE 2: EBOOK COPY PROTECTION

### 2A. Download limit enforcement
- ALTER TABLE download_tokens ADD download_count INTEGER DEFAULT 0, max_downloads INTEGER DEFAULT 3
- New Edge Function: `download-ebook/index.ts`
  - Accepts { token }, validates count < 3 and not expired
  - Increments count, returns fresh 1-hour signed URL
- Update verify-ebook-purchase to return token for subsequent downloads
- Update Lovable success page to use download-ebook endpoint

### 2B. Social DRM watermark (defer -- skip for now)
- Inject buyer email into HTML reader footer
- Requires on-the-fly ZIP generation per customer
- Do when volume justifies complexity

---

## PHASE 3: PER-GAME ARCADE SHOPS

### 3A. New database tables
- `game_currencies` (player_id, game_id, currency_name, balance) -- per-game wallets
- `game_passes` (player_id, pass_type, game_id, active, expires_at) -- per-game and master passes

### 3B. Currency model
| Game | Currency | Use |
|------|----------|-----|
| Alley Kingz | NOS Bottles | Game-specific, earned + purchased |
| Blackjack | Chips | Game-specific, earned + purchased |
| Both | Gems | Premium cross-game currency |

### 3C. 9 new Stripe products (total 26)
- AK Game Pass $4.99/mo, BJ Game Pass $4.99/mo, Master Pass $9.99/mo
- NOS packs: 50/$0.99, 300/$4.99, 800/$9.99
- Chip packs: 500/$0.99, 3000/$4.99, 8000/$9.99

### 3D. Edge Function updates
- create-checkout: add 9 slugs to PRICE_MAP
- verify-arcade-purchase: route NOS/Chips to game_currencies, handle game passes
- stripe-webhook: handle game pass subscription events

### 3E. Lovable: per-game shops
- /arcade/alley-kingz: "NOS GARAGE" (NOS packs + AK Game Pass)
- /arcade/blackjack: "HIGH ROLLER LOUNGE" (Chip packs + BJ Game Pass)
- /arcade hub: "MASTER PASS" hero banner

---

## PHASE 4: ALLEY KINGZ 3D EMBED

### 4A. game_v8.html is production-ready (4,261 lines, self-contained Three.js)
- Upload to Lovable public assets
- Embed as iframe, responsive (9:16 mobile, 16:9 desktop, max 80vh)

### 4B. Add postMessage payment bridge (~30 lines)
- Game sends: GAME_OVER, REQUEST_LIVES
- Parent sends: LIVES_GRANTED
- Parent intercepts to show NOS purchase overlay

---

## PHASE 5: SITE AUDIT UPGRADES

- SEO: per-page title/description/og tags for all 10 pages
- Performance: lazy load images, WebP, font preload (target <3s)
- 404 page: branded dark page with venture links
- GA4 analytics: page views, CTA clicks, purchases
- Trust: stats bar, badges, social proof
- Accessibility: alt text, 48px touch targets, focus states

---

## PHASE 6: EVERLIGHT BLACKJACK OVERHAUL

### 6A. Core Gameplay Fixes

**Double Down for Less:**
- If player's chip balance < current bet, allow "Double for Less" (wager remaining balance)
- UI: grayed-out "DOUBLE" button shows "DOUBLE FOR LESS (X chips)" when balance is insufficient
- Preserves the "Double Down Madness" (any total) house rule

**Max Bet Upgrade:**
- Increase max bet from 240 to 1,000 chips
- Bet slider/chip selector: 10, 25, 50, 100, 250, 500, 1,000

**Chip Balance Persistence (fix refresh exploit):**
- Current: refreshing the page resets chip count (stored in JS memory only)
- Fix: persist chip balance to Supabase `game_currencies` table on every hand result
- On page load, fetch balance from DB (not localStorage)
- Free 1,000 chips once per day (check `last_free_chips_at` column, reset at midnight PT)
- If balance is 0 and no free chips today: show "Buy Chips" overlay

**Chip Visual Design:**
- Replace numeric currency displays with casino chip graphics
- Denominations with colors: 10 (white), 25 (red), 50 (blue), 100 (green), 250 (black), 500 (purple), 1000 (gold)
- Chip stack animations on bet placement
- Chips slide, stack, and clink with sound effects

### 6B. User Registration for Leaderboard

- Require account to play (not just anonymous session)
- On first visit: "Enter the Casino" overlay
  - Display name (3-20 chars)
  - Email (for account recovery + purchase receipts)
  - Age verification (DOB, must be 18+)
- Store in `player_accounts` table
- Player ID stored in localStorage + Supabase auth session
- Leaderboard shows display name, not anonymous initials

### 6C. Lucky Lucky Side Bet

**Rules:** Evaluates player's first 2 cards + dealer's upcard (3 cards total).

| Hand | Payout |
|------|--------|
| Suited 7-7-7 | 200:1 |
| Suited 6-7-8 | 100:1 |
| Unsuited 7-7-7 | 50:1 |
| Unsuited 6-7-8 | 30:1 |
| Suited total of 21 | 15:1 |
| Unsuited total of 21 | 3:1 |
| Total of 20 | 2:1 |
| Total of 19 | 2:1 |

- Side bet placed before deal (separate chip area, left of main bet)
- Min: 10 chips, Max: 100 chips
- Evaluated immediately after initial deal (before player actions)
- Win animation: gold burst + payout text overlay

### 6D. Buster Blackjack Side Bet

**Rules:** Wins when the dealer busts. Payout scales with dealer's bust card count.

| Dealer Busts With | Payout | With Player BJ |
|-------------------|--------|----------------|
| 8+ cards | 250:1 | 2,000:1 |
| 7 cards | 50:1 | 800:1 |
| 6 cards | 18:1 | 200:1 |
| 5 cards | 4:1 | 50:1 |
| 3-4 cards | 2:1 | 5:1 |

- Side bet placed before deal (right of main bet)
- Min: 10 chips, Max: 100 chips
- CRITICAL: Dealer must finish hand even if all players bust (if any Buster bet is live)
- Win animation: red explosion + "BUSTED!" text

### 6E. Progressive Jackpot

**Mechanic:**
- Jackpot starts at 5,000 chips, increases by 1% of every Lucky Lucky side bet placed
- Climbs toward 10,000 chip cap (resets to 5,000 after win)
- **Win condition:** Player has suited 7-7-7 AND dealer's upcard is a 7 (any suit)
- Displayed as animated counter at top of table (always visible, gold text, pulsing glow)

**Win experience:**
- Full-screen takeover animation: slot machine reels spin, lock on 7-7-7
- Casino lights flash, confetti particles, jackpot bell sound
- "PROGRESSIVE JACKPOT WINNER!" in marquee gold text
- Chips cascade into player's balance with counting animation
- Slack notification: "JACKPOT WON! [player] hit suited 7-7-7 + dealer 7 for [X] chips!"
- Leaderboard entry auto-created

**Legal note:** Progressive jackpots on virtual chips (no cashout) are legal. Not gambling because chips have zero real-money value. Disclaimer required on jackpot display.

### 6F. Real-Time Multiplayer

**Technology:** Supabase Realtime (channels) for MVP, upgrade to Socket.IO later if needed

**Table structure:**
- Each table is a Supabase Realtime channel: `blackjack:table_[id]`
- Max 5 player seats + 1 dealer
- Players see each other's hands, bets, and actions in real time
- Turn-based: each player acts in seat order (left to right)
- 15-second action timer per player (auto-stand on timeout)

**Join flow:**
- /arcade/blackjack shows table lobby: list of open tables with seat count
- "Quick Join" button seats you at first available table
- "Create Table" for private games (share link with friends)
- "Join Friend" via table code

**Database:**
```sql
CREATE TABLE blackjack_tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT,
  table_type TEXT DEFAULT 'standard',  -- 'standard', 'high_roller', 'vip'
  min_bet INTEGER DEFAULT 10,
  max_bet INTEGER DEFAULT 1000,
  seats_total INTEGER DEFAULT 5,
  seats_filled INTEGER DEFAULT 0,
  is_private BOOLEAN DEFAULT false,
  invite_code TEXT UNIQUE,
  progressive_pool INTEGER DEFAULT 5000,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE blackjack_seats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_id UUID REFERENCES blackjack_tables(id),
  seat_number INTEGER NOT NULL,  -- 1-5
  player_id UUID REFERENCES player_accounts(id),
  is_bot BOOLEAN DEFAULT false,
  status TEXT DEFAULT 'seated',  -- 'seated', 'playing', 'sitting_out', 'left'
  joined_at TIMESTAMPTZ DEFAULT now()
);
```

**Game state sync via Supabase Realtime:**
- Server (Edge Function) broadcasts: `{ type: 'DEAL', hands: [...], dealer: [...] }`
- Player sends: `{ type: 'ACTION', action: 'hit'|'stand'|'double'|'split', seat: 3 }`
- All players see actions animate in real time

### 6G. Bot Players

**Behavior profiles (3 types):**

| Profile | Play Style | Bet Pattern | Session Length |
|---------|-----------|-------------|----------------|
| "Tourist" | Cautious, stands early, rarely splits | Low bets (10-50), flat | 5-10 hands, leaves |
| "Regular" | Basic strategy, occasional mistakes (10%) | Medium (50-200), slight progression | 15-30 hands |
| "Whale" | Aggressive, doubles often, max splits | High (200-1000), volatile | 20-40 hands, tips dealer |

**Realism features:**
- Random 1.5-4 second delay on decisions (harder decisions = longer)
- Occasionally "think" for 5-8 seconds on tough hands (12 vs 3, soft 17)
- Join tables gradually (not all at once)
- Leave after random number of hands
- Chat occasionally: "nice hand", "tough break", "gl"
- Vary starting chip stacks (500-5000 range)
- Use randomized display names from a pool of 50+ names

**Table fill logic:**
- If table has < 3 humans after 30 seconds, add 1-2 bots
- If table fills to 5 humans, bots gracefully leave ("gotta go, gl everyone")
- Empty tables always have 2-3 bots to avoid dead lobby feeling

### 6H. Premium Tables

**Table tiers:**

| Table | Entry Fee | Min Bet | Max Bet | Perks |
|-------|-----------|---------|---------|-------|
| Standard | Free | 10 | 1,000 | Basic table, shared progressive |
| High Roller | 500 chips/session | 100 | 5,000 | Gold felt, faster deal, exclusive leaderboard |
| VIP Lounge | 2,000 chips/session OR VIP pass | 500 | 25,000 | Diamond table, private room, custom card backs, priority jackpot |

- Entry fee deducted from chip balance on join (one-time per session)
- VIP pass holders skip entry fee for VIP Lounge
- Premium tables have separate progressive jackpots (higher starting pool)
- Legal: charging virtual currency for table access is standard social casino practice

**Visual differentiation:**
- Standard: green felt, white trim
- High Roller: gold felt (#D4AF37), black trim, subtle particle effects
- VIP Lounge: deep purple felt, diamond accents, ambient lighting, premium card animations

### 6I. Google Ads Integration

**Google AdSense (display ads ON your pages):**
- Sign up at adsense.google.com
- Add ad units to non-game pages (homepage, publishing, logistics)
- Do NOT place ads inside the game iframe (disrupts gameplay)
- Sidebar/banner ads on /arcade lobby page are fine

**Google Ads (promote your site):**
- Apply for "Social Casino Games" certification at ads.google.com
- Requirements: 18+ disclaimer, no real-money gambling, disclose IAP
- Run campaigns targeting: "free blackjack online", "social casino game", "play blackjack with friends"
- Landing page: /arcade/blackjack with clear "FREE TO PLAY" messaging

**Lovable prompt for ad placement:**
```
Add Google AdSense ad units to the site. Place a responsive banner ad
below the hero section on the homepage, a sidebar ad on the /publishing
page, and a leaderboard ad (728x90) at the bottom of the /arcade lobby.
Do NOT place ads inside game iframes. Use the AdSense script tag with
data-ad-client and data-ad-slot attributes (I'll provide the IDs after
AdSense approval).
```

### 6J. Rules Display + Side Bet Explainers

**In-game rules panel (accessible via "?" button, top-right):**

Tabs: RULES | LUCKY LUCKY | BUSTER | PROGRESSIVE | PAYOUTS

**Lucky Lucky tab:**
```
LUCKY LUCKY SIDE BET
Place your bet before the deal. Your first 2 cards + dealer's
upcard are evaluated:

  Suited 7-7-7 ........... 200:1
  Suited 6-7-8 ........... 100:1
  Unsuited 7-7-7 .......... 50:1
  Unsuited 6-7-8 .......... 30:1
  Suited 21 ................ 15:1
  Unsuited 21 ............... 3:1
  Total 20 .................. 2:1
  Total 19 .................. 2:1

Min bet: 10 chips | Max bet: 100 chips
```

**Buster tab:**
```
BUSTER BLACKJACK
Wins when the dealer BUSTS. More cards = bigger payout!

  Dealer busts with 8+ cards ... 250:1 (2,000:1 w/ your BJ!)
  Dealer busts with 7 cards .... 50:1  (800:1 w/ your BJ!)
  Dealer busts with 6 cards .... 18:1  (200:1 w/ your BJ!)
  Dealer busts with 5 cards ..... 4:1  (50:1 w/ your BJ!)
  Dealer busts with 3-4 cards ... 2:1  (5:1 w/ your BJ!)

The dealer MUST complete their hand if any Buster bet is active.
Min bet: 10 chips | Max bet: 100 chips
```

**Progressive tab:**
```
PROGRESSIVE JACKPOT
Current pool shown at top of table. Starts at 5,000 chips,
grows with every Lucky Lucky bet placed (1% contribution).

WIN CONDITION: Suited 7-7-7 when dealer shows a 7.
Max jackpot: 10,000 chips. Resets to 5,000 after win.
You MUST have a Lucky Lucky bet active to qualify.
```

---

## EXECUTION ORDER

| # | Task | Key Files |
|---|------|-----------|
| 1 | README.txt in ZIPs + re-upload | 7 ZIPs, Supabase Storage |
| 2 | Query + draft email for 2 customers | Supabase SQL, Gmail |
| 3 | Download limit (alter table + download-ebook function) | download_tokens, new edge function |
| 4 | Per-game DB tables | Supabase SQL |
| 5 | Create 9 Stripe products (Master Pass $9.99) | Stripe API |
| 6 | Update + deploy Edge Functions | 3 existing + 2 new edge functions |
| 7 | postMessage bridge in game_v8.html | game_v8.html |
| 8 | Lovable prompts: game embed, shops, SEO, 404 | Lovable |
| 9 | Confirmation email function | new edge function + Resend |
| 10 | BJ core fixes: double for less, max bet 1000, chip persistence | blackjack game code |
| 11 | BJ user registration overlay | Lovable + player_accounts |
| 12 | BJ chip graphics (replace numbers) | game assets + CSS |
| 13 | Lucky Lucky + Buster side bets + rules panel | blackjack game code |
| 14 | Progressive jackpot (pool, counter, win animation) | blackjack game + new DB table |
| 15 | Multiplayer tables (Supabase Realtime channels) | new tables + Edge Function |
| 16 | Bot players (3 profiles, join/leave logic) | blackjack game code |
| 17 | Premium table tiers (Standard/High Roller/VIP) | blackjack_tables + Lovable |
| 18 | Google AdSense setup + Social Casino Ads certification | Lovable + Google |

## VERIFICATION
- Download limit: buy book, download 3x, verify 4th blocked
- Per-game currency: buy NOS pack, check game_currencies table
- Game embed: load /arcade/alley-kingz, verify Three.js renders
- Slack: verify purchase notifications in #ev-sales
- Lighthouse: target 90+ performance
- BJ double for less: bet 500 with 300 balance, verify doubles for 300
- BJ chip persistence: play, refresh, verify balance restored from DB
- BJ free chips: claim 1000, refresh, verify no second claim same day
- Lucky Lucky: deal suited 21, verify 15:1 payout
- Buster: dealer busts with 6 cards, verify 18:1 payout
- Progressive: verify counter increments with each Lucky Lucky bet
- Multiplayer: open 2 browser tabs, join same table, verify real-time sync
- Bots: sit at table, verify bots join after 30 seconds
- Premium table: pay 500 chip entry, verify deducted and seated at gold table
- Google Ads: verify ad units render on non-game pages

| # | Task | Key Files |
|---|------|-----------|
| 1 | README.txt in ZIPs + re-upload | 7 ZIPs, Supabase Storage |
| 2 | Query + draft email for 2 customers | Supabase SQL, Gmail |
| 3 | Download limit (alter table + download-ebook function) | download_tokens, new edge function |
| 4 | Per-game DB tables | Supabase SQL |
| 5 | Create 9 Stripe products | Stripe API |
| 6 | Update + deploy Edge Functions | 3 existing + 2 new edge functions |
| 7 | postMessage bridge in game_v8.html | game_v8.html |
| 8 | Lovable prompts: game embed, shops, SEO, 404 | Lovable |
| 9 | Confirmation email function | new edge function + Resend |

## VERIFICATION
- Download limit: buy book, download 3x, verify 4th blocked
- Per-game currency: buy NOS pack, check game_currencies table
- Game embed: load /arcade/alley-kingz, verify Three.js renders
- Slack: verify purchase notifications in #ev-sales
- Lighthouse: target 90+ performance
