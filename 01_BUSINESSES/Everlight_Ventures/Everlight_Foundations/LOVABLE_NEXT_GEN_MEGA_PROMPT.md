# LOVABLE PROMPT: Everlight Arcade -- Premium Rebuild

Paste this into Lovable. This is a COMPLETE upgrade of the /arcade section -- immersive casino experience, subtle VIP monetization, jukebox lounge, blockchain-optional features, and premium UX that rivals the best social casino games in the industry.

**This prompt supersedes and incorporates:** LOVABLE_BLACKJACK_V2_PROMPT, LOVABLE_BLACKJACK_V3_PROMPT, LOVABLE_ARCADE_SHOPS_PROMPT, LOVABLE_REWARDS_PROGRAM_PROMPT, and LOVABLE_AUTH_FIX_PROMPT. Do NOT lose any existing features -- this ADDS to everything already built.

---

## PROMPT:

Rebuild the Everlight Arcade (`/arcade` and all sub-routes) into a premium social casino platform. The design philosophy: **"Wynn Las Vegas meets Apple Store."** Every pixel should feel premium, every interaction should feel intentional, and every purchase opportunity should feel like a privilege -- never a demand. Players should WANT to spend, not feel pressured to.

All purchases use existing Supabase Edge Function at `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/create-checkout` with `{ slug, success_url, cancel_url }`. Anon key header: `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

---

## PART 1: DESIGN PHILOSOPHY -- "THE LOUNGE RULES"

These rules govern EVERY design decision in the arcade:

### Rule 1: Never Interrupt Gameplay to Sell
No popups. No modal overlays during active play. No "BUY NOW" banners blocking the table. Purchase options exist in dedicated spaces (shop pages, profile panel) and are accessed BY THE PLAYER, never pushed.

### Rule 2: The Empty Wallet Moment is a Concierge, Not a Salesman
When a player runs out of chips/gems/NOS, show a calm, elegant prompt:
- Subtle gold-bordered card that slides in from the bottom (NOT a popup)
- Copy: "Your balance is low. Visit the Lounge to continue." with a small "Lounge" link
- Dismiss with a tap anywhere -- it never returns for 30 minutes
- NEVER block the UI. Player can still navigate, view stats, spectate
- Think: a VIP casino host sliding a card across the table, not a bouncer blocking the door

### Rule 3: Status Speaks Louder Than Ads
Instead of screaming "BUY THE PASS!", show what paid players HAVE:
- At the table, Master Pass members have a subtle gold ring around their avatar
- Their name has a warm gold shimmer (not flashy -- think brushed gold, not glitter)
- Their seat has a slightly different material (leather vs. fabric)
- Other players see this and WANT it. The product sells itself through status.

### Rule 4: The Master Pass is the Crown Jewel
The Master Pass is never "advertised" -- it's "discovered." Players learn about it through:
- Seeing other players' gold status effects
- A single elegant line in the profile panel: "Unlock everything. $14.99/mo"
- The rewards page showing grayed-out perks with "Master Pass" labels
- NEVER a banner, NEVER a popup, NEVER an interstitial

### Rule 5: Prices Are Whispered, Not Shouted
Shop pages show prices in small, refined text -- never as the largest element on a card. The PRODUCT (what you get) is the hero. The price is secondary context.

### Rule 6: Three Touches Max
A player should never see more than 3 purchase-related elements on any single screen:
- One status indicator (VIP badge, pass status)
- One passive discovery point (greyed perk, gold avatar)
- One action point (shop link, if on a shop page)
Anything more feels like a popup casino on a shady website.

---

## PART 2: MASTER PASS -- THE MEMBERSHIP

Route: `/arcade/membership` (NOT `/arcade/shop` -- this is a MEMBERSHIP, not a store)

### 2.1 Master Pass ($14.99/mo) -- slug: `master-pass`

**This is Everlight's flagship product.** It should feel like joining a private club, not subscribing to software.

**LANGUAGE RULES:** Never call it a "subscription." Never say "subscribe." The language is always:
- "Become a member" / "Join the inner circle"
- "Your membership includes..." / "Members receive..."
- The word "subscribe" communicates obligation. "Membership" communicates belonging.

**Membership Page Design (Full-screen, NOT a modal or card):**

```
[Full-width hero section]
  Background: #0A0A0A with a single, very subtle radial gradient
  of #D4AF37 at 3% opacity, centered, creating a warm glow
  that the eye barely registers consciously.

  Center-aligned:
  - Cormorant Garamond wordmark: "EVERLIGHT"
  - Beneath it, smaller: "MASTER PASS"
  - A thin gold line (1px, 60px wide, centered)
  - Price: "$14.99" in Inter Bold 32px, #D4AF37
  - Beneath price: "per month" in Inter Regular 12px, #8A8A8A
  - 40px of whitespace
  - CTA: "Become a Member" -- gold text on transparent background,
    1px gold border, generous padding (16px 48px), Cormorant Garamond.
    On hover: background fills to #D4AF37, text becomes #0A0A0A.
    No gradients. No glow. No animation. The simplicity IS the luxury.

[Spacer: 80px]

[Benefits section -- NOT a bullet list, three columns]
  Column 1: Diamond icon (gold, 24px line-weight)
    Label: EVERY GAME (caps, 11px, #8A8A8A)
    Text: All current and future game passes included. No add-ons.

  Column 2: Gem icon (gold, 24px line-weight)
    Label: DAILY GEMS
    Text: 50 Gems deposited to your account every day you log in.

  Column 3: Crown icon (gold, 24px line-weight)
    Label: VIP ACCESS
    Text: Priority matchmaking. Exclusive cosmetics. Early access to new titles.

[Spacer: 60px]

[Comparison strip -- understated]
  Single horizontal row:
  "Alley Kingz Pass: $4.99  +  Blackjack Pass: $4.99  +  50 daily gems  =  $14.99"
  All in #8A8A8A, 12px. No "SAVE $X!" badge. No strikethrough pricing.
  The math speaks. Let the player do it.

[Second CTA -- identical to the first]
```

**Full benefits (included but NOT displayed as a giant list):**
- All Game Passes (Blackjack + Alley Kingz + future games)
- 50 Gems daily (1,500/month value)
- VIP table access across all games
- Exclusive avatar frame (animated gold ring)
- Gold name treatment in all lobbies
- 5 streak shields per month
- Priority matchmaking
- Early access to new games and features
- Exclusive seasonal cosmetics
- Monthly mystery box (guaranteed rare+)

**What this page does NOT have:**
- No comparison table between free and paid
- No "BEST VALUE" badge
- No urgency text ("Limited time!")
- No multiple pricing tiers on the same page
- No testimonials or social proof clutter
- No countdown timers
- No discount hooks or "first month free" offers

### 2.2 Individual Passes

Individual passes appear in exactly ONE place: the settings/account page of each specific game. NOT the main arcade hub. NOT a separate shop page. NOT the rewards page.

Inside each game's settings panel:

```
[Card: 100% width, #111111 background, 1px #1A1A1A border, 16px padding]

  Left side:
    Game icon (small, 32px)
    "Blackjack Pass" in Inter Semi-Bold 16px, #E5E5E5
    Below: "$4.99 / month" in Inter Regular 13px, #8A8A8A

  Right side:
    Button: "Activate" -- outlined style, #E5E5E5 border and text
    (NOT gold -- gold is reserved for Master Pass)

  Below the card, a single line:
    "This pass is also included with Everlight Master Pass."
    "Master Pass" in gold. Rest in #8A8A8A.
```

Products:
- **Blackjack Pass** -- $4.99/mo (slug: `bj-pass-monthly`)
  - 2,000 daily free chips, exclusive card backs, High Roller table access
- **Alley Kingz Pass** -- $4.99/mo (slug: `ak-pass-monthly`)
  - 2x NOS earn rate, exclusive car skins, priority matchmaking

If a player who owns an individual pass later purchases the Master Pass, auto-credit remaining balance:
> "Your Blackjack Pass has been folded into your Master Pass membership. The remaining balance has been credited."

### 2.3 Master Pass Status Indicators (visible everywhere)

When a player HAS the Master Pass:
- A small gold diamond icon next to their username everywhere (chat, leaderboards, match lobbies). No text label. Members know what it means.
- The "Membership" nav item text changes from gold to white with a 4px gold dot
- On the Membership page, the CTA is replaced with: "Member since [Month Year]" and "Manage membership" link (Stripe portal)
- Daily gem deposits in rewards: "Master Pass -- 50 Gems" with gold diamond icon
- Subtle gold gradient on profile card background (5% opacity)

When a player does NOT have it:
- In the profile panel, a single line: "Become a Member" with right arrow, gold text
- In the rewards page, any Master Pass perk shown with small gold lock icon and "Member" label
- That's it. No banners, no popups, no red badges.

**The product is presented in exactly TWO locations: the Membership page and the profile sidebar. That is it. No urgency timers. No discount hooks. The product is the product.**

---

## PART 3: THE GEM LOUNGE (Gem Shop Redesign)

Route: `/arcade/lounge` (renamed from "shop" -- this is a Lounge, not a store)

### 3.1 Design

The Gem Lounge should feel like walking into a private room at a high-end casino. NOT a mobile game store with flashy cards and "BEST VALUE" stamps.

**Page layout:**
- Dark background with subtle ambient gradient (very dark purple-to-black radial, barely visible)
- Page title: "The Lounge" in Playfair Display, gold, centered
- Subtitle: "Your personal collection" in Inter 400, 14px, #6B7280

**Gem Balance (hero section):**
- Large gem count centered: purple diamond icon + number in 36px font
- Below: "1 Gem = 10 NOS Bottles = 100 Chips" in 12px, #6B7280
- If Master Pass holder: "+50 bonus Gems arriving tomorrow" in gold, 12px

**Gem Packs (displayed as a horizontal scroll on mobile, 3-across on desktop):**

| Pack | Gems | Price | Slug |
|------|------|-------|------|
| 100 | 100 | $0.99 | `gems-100` |
| 600 | 600 | $4.99 | `gems-600` |
| 1,500 | 1,500 | $9.99 | `gems-1500` |
| 4,000 | 4,000 | $24.99 | `gems-4000` |
| 10,000 | 10,000 | $49.99 | `gems-10000` |

**Pack card design:**

```
Card design (each):
  Background: #111111
  Border: 1px solid #1A1A1A
  Border-radius: 12px
  Padding: 24px, center-aligned

  Top: Gem count in Inter Bold 24px, #7B2FF7
  Middle: Purple diamond icon, sized proportionally
         (32px for 100, 40px for 600, 48px for 1500, 56px for 4000)
  Bottom: Price in Inter Semi-Bold 16px, #E5E5E5

  Button: "Purchase" -- 1px #7B2FF7 border, #7B2FF7 text,
          transparent background. On hover: filled #7B2FF7, white text.

  NO BADGES. No "BEST VALUE." No "POPULAR." No percentages.
  Value scaling is self-evident:
    100 for $0.99 = 101/dollar
    600 for $4.99 = 120/dollar
    1,500 for $9.99 = 150/dollar
    4,000 for $24.99 = 160/dollar
  Players who buy frequently will notice. That discovery feels like
  insider knowledge, not a sales pitch.
```

**Purchase flow:**
1. Player taps "Purchase" -- card subtly elevates (2px box-shadow, 150ms ease)
2. Confirmation appears INLINE beneath the card (NOT a modal):
   "600 Gems for $4.99" with [Confirm] [Cancel] text buttons
3. On confirm: redirect to Stripe Checkout (clean, fast)
4. On return: balance updates with subtle count-up animation. Brief toast: "+600 Gems" in purple, auto-dismisses after 3 seconds. No confetti. No fanfare.

**Conversion section (below packs):**
- "Convert" header, 16px
- Clean dropdown: select target currency
- Input field for gem amount
- Live preview: "100 Gems -> 1,000 Chips"
- "Convert" button (purple, not gold -- gold is reserved for membership)
- VIP tier bonus shown if applicable: "+10% bonus (Gold Member)" in #D4AF37, 12px

### 3.2 What the Lounge Does NOT Have
- No countdown timers
- No "limited time" offers
- No red notification badges pulling you to the shop
- No "first purchase bonus" popups
- No comparison to "real value" ($49.99 = "$100 worth of gems!")
- No animated gem icons flying around
- No "SALE" or discount badges ever
- No gem balance in persistent header/nav (show only on relevant pages)
- No push notifications about gem deals
- No "gem rain" animations after purchase

---

## PART 4: IN-GAME PURCHASE MOMENTS (The Concierge Pattern)

### 4.1 When Player's Balance is Low (but not zero)

At 20% of minimum bet or 10% of average session spend, show:
- A thin gold line appears at the bottom of the screen (like a notification drawer handle)
- If tapped/swiped up, it reveals a minimal card: "Visit the Lounge" with gem icon
- Auto-hides after 10 seconds if not interacted with
- Does NOT appear again for 1 hour

### 4.2 When Player Hits Zero Balance (The VIP Host Moment)

**Think:** sitting at a Wynn blackjack table and running out of chips. The dealer does not shout. A host appears at your shoulder, leans in quietly, and says, "Would you like me to bring more?" That is this interaction.

1. Player's chip count reaches zero. Table dims very slightly (brightness 0.92, not dramatic).
2. The betting interface grays out naturally -- bet slider unresponsive, "Deal" button fades to #8A8A8A. NO popup.
3. After 1.5 seconds, a single line fades in below the betting area: "Your table balance is empty." (Inter Regular, 14px, #8A8A8A)
4. After another 0.5s, two options appear side by side as TEXT LINKS (not buttons):
   - [Convert Gems] in #7B2FF7 | [Visit Gem Shop] in #8A8A8A
   - If player has gems, "Convert Gems" opens an inline mini-panel (NOT a modal):
     ```
     Your Gems: 247
     Convert: [slider, default 5] Gems -> 500 Chips
     [Convert]
     ```
     After conversion, table reactivates immediately. No celebration. Game continues.
   - If no gems, only "Visit Gem Shop" appears.
5. The table remains visible the entire time. Cards from the last hand stay dealt. The atmosphere does not break. Player never leaves the table mentally.

**KILLED:** Full-screen "OUT OF CHIPS" overlays, popup modals with tiered options, "watch an ad" buttons, countdown timers on special offers, anything that makes the player feel punished.

### 4.3 Luxury-Grade Conversion Nudges

**Nudge 1: The Quiet Upgrade Path**
After a strong session (3+ wins or profitable run), a single line appears on the summary:
> "Members earned 2x rewards this session."
Gold text. No button. No link. No CTA. Just a fact. Curiosity does the work. (Hermes does not advertise the Birkin. They let you see someone carrying one.)

**Nudge 2: The Member Glow**
Master Pass members have a gold diamond next to their name everywhere. Non-members see this constantly. They are never told what it means. Eventually they ask in chat (peer social proof > marketing copy) or find the Membership page on their own. (Members-only clubs do not explain their exclusivity. The velvet rope is the marketing.)

**Nudge 3: The Soft Gate**
Certain premium cosmetics are visible but dimmed with a small gold lock icon. No price tag. No "UNLOCK WITH GEMS." When tapped, item expands with one line: "Included with Master Pass" and a "Learn more" text link. (The Cartier window display. You see it. You walk in when ready.)

**Nudge 4: The Session Bookmark**
No exit-intent popup. On their NEXT visit, a single line on the arcade hub:
> "Welcome back. Your streak is at 4 days."
If non-member and 7th+ session, a second line: "Members earn 2x streak rewards." Small, muted. Disappears in 5 seconds.

**Nudge 5: Social Gifting (Future)**
Members can send 5-gem gift to opponents post-match. Recipient sees: "[Player Name] sent you a gift" with "Sent by a Master Pass member." Generosity as marketing. (AMEX Centurion cardholders buying rounds for strangers.)

### 4.4 The "Almost" Nudge

When a player is within 10% of the next VIP tier:
- In their profile panel (not a popup), show: "47 VP to Gold -- unlocks +10% gem conversion"
- Gold progress bar, nearly full
- No button. No "buy now to get there." Just the information.

---

## PART 5: THE JUKEBOX -- SOCIAL LOUNGE ATMOSPHERE

### 5.1 Jukebox Concept

Every blackjack table has a virtual jukebox. Players spend **Quarters** (earned through play or tiny IAP) to queue songs. The jukebox drives the room's atmosphere -- lighting, particle effects, and crowd energy change based on the music's tempo.

**Jukebox UI:** A small, elegant jukebox icon in the bottom-right of the table view. Tap to expand the queue panel.

### 5.2 Jukebox Queue Panel (slide-out from right)
- Current song: album art (or abstract visualizer), title, artist, BPM badge
- Queue: next 5 songs, each showing who queued it
- "Add Song" button opens the music browser
- "Skip Vote" button (costs 1 Quarter) with vote count
- "Fast Pass" option to jump the queue (20 Quarters)
- DJ badge next to the player who queued the current song

### 5.3 Music Browser
- Genre tabs: Lo-Fi, Hip-Hop, Jazz, EDM, R&B, Latin, Ambient
- Each track: title, artist, BPM, vibe tag (HYPE/HEAT/CHILL/AFTER-HOURS)
- Preview (5 second clip on hover/tap)
- "Queue" button (5 Quarters)
- Search bar at top
- Tracks are from licensed libraries (Epidemic Sound/Artlist style -- no copyright issues)

### 5.4 Vibe States -- Music Drives the Room

The table's visual environment reacts to the current song's BPM:

| Vibe State | BPM | Lighting | Crowd | Particles |
|------------|-----|----------|-------|-----------|
| HYPE | 128+ | Neon strobes, cyan/magenta, high bloom | Dancing, cheering | Light strobes |
| HEAT | 90-128 | Red/gold, warm high contrast | Excited idle | None |
| CHILL | 60-90 | Amber, dim, fog | Casual lean | Smoke haze |
| AFTER-HOURS | <60 | Deep blue, solo spotlight on table | Bar lean, quiet | None |

**Implementation:** Use CSS custom properties that change based on vibe state. The table container's `background`, `box-shadow`, and particle overlays transition smoothly (2s ease) when the vibe changes.

### 5.5 Quarters Economy
- Earn 1 Quarter per winning hand
- Earn 3 Quarters for a blackjack
- Earn 1 Quarter per 10 minutes of session time
- Daily login bonus includes 10 Quarters
- Optional: small Quarters packs in the Lounge (but NOT pushed)

### 5.6 Cinematic Moments

These make the game feel alive:

**Blackjack:** Dealer freezes, cards spread in a fan, gold shimmer burst, music ducks for 1 second then swells back. Crowd goes "Ooooh."

**Big Win (3x+ bet):** Quick camera zoom effect (scale 1.02 to 1.0), confetti, chips cascade animation. Jukebox volume surges briefly.

**Jackpot:** Full screen white flash (200ms), music cuts, jackpot sound plays, then music resumes. Everyone at the table gets a notification.

**Bust:** Cards scatter, subtle dealer smirk emote, quick dim on player's area.

---

## PART 6: BLOCKCHAIN INTEGRATION (Optional, Elegant)

Add an OPTIONAL blockchain layer. This is NOT crypto-bro branding. It's invisible to players who don't want it, and elegantly available to those who do.

### 6.1 Provably Fair Dealing (HMAC-SHA256 Commit-Reveal)

Show a small "Verified Fair" badge on each table (shield icon, 16px, #22C55E):
- Tap to see: "Every hand uses a cryptographic commit-reveal scheme. The deck is shuffled using a server seed + player seed hashed together. You can verify any hand."
- Link to verification page (`/arcade/fairness`) showing:
  - How it works (simple diagram)
  - Hand history with hash verification
  - "Verify" button that checks the hash

**Technical implementation:**
```
Before each round:
  1. Server generates random server_seed
  2. Server commits hash = HMAC-SHA256(server_seed, round_id + client_seed + nonce)
  3. Hash is shown to player BEFORE cards are dealt (proves server can't change the seed)

After round:
  4. Server reveals server_seed
  5. Player can independently compute: HMAC-SHA256(revealed_seed, round_id + their_seed + nonce)
  6. If hashes match → dealing was predetermined and fair
  7. Card positions derived from: SHA-256(server_seed + client_seed + nonce) → map to deck order

Client seed: auto-generated per player per session (shown in settings, editable)
Nonce: increments each hand (prevents replay)
All verification data stored in hand_history table for audit
```

- This builds trust. It's not flashy. It's just there. Players who care about fairness will find it. Players who don't will never notice.

### 6.2 Optional Wallet Connection

**Recommended chain:** Solana (fast, cheap, best NFT tooling for gaming). Stellar/XLM as secondary for future token features.
**Wallet SDK:** Use thirdweb Connect (supports MetaMask, Phantom, WalletConnect in one SDK, handles all chains).

In profile settings (NOT on the main screen), add:
- "Connect Wallet" option under a "Web3" tab in settings (clearly separated)
- Small text: "Optional. Connect to own your cosmetics on-chain and access token-gated tables."
- If connected, show wallet address (truncated) in profile

### 6.3 NFT Cosmetics (Phase 2)

For players with connected wallets:
- Certain exclusive card backs, table skins, and avatar items are NFTs
- They can be traded/sold on a simple marketplace (`/arcade/marketplace`)
- NFT items show a small chain icon in the corner
- Non-NFT players see and use regular cosmetics -- they miss nothing gameplay-wise
- NFT items are purely cosmetic flex

### 6.4 Token-Gated VIP Table

One exclusive table: "The Vault"
- Requires holding an Everlight NFT (or X amount of tokens) to access
- Higher stakes, exclusive dealer, unique table design
- Entry check happens via wallet signature (no gas fees to enter)
- If player doesn't have wallet connected or doesn't hold the token: table shows as "Invite Only" with a small info icon explaining requirements

### 6.5 Blockchain Rules
- NEVER make blockchain mandatory for any core feature
- NEVER show crypto prices or token charts in the game
- NEVER use the words "investment" or "returns" or "profit" related to tokens
- Blockchain features are in a "Web3" tab in settings, clearly separated
- All existing non-blockchain features continue to work identically

### 6.6 CRITICAL LEGAL WARNING
- Social casinos with blockchain elements face major 2025-2026 regulatory crackdown
- Gems MUST have NO cash-out path. NO real-world monetary value. Ever.
- NFT cosmetics are purely cosmetic -- zero gameplay advantage
- Token-gated access is for exclusive COSMETIC experiences, not pay-to-win
- Build the pure web game FIRST. Blockchain is an optional LAYER added second.
- All blockchain features must comply with UIGEA, state gambling laws, and SEC guidance on digital assets
- Include legal disclaimer on ALL blockchain-related pages

---

## PART 7: COMPETITIVE FEATURES (Learned from Top Games)

**Market context:** Social casino gaming is a $24B+ market. Research shows transparent, non-predatory monetization leads to players spending 3.2x more over their lifetime vs. aggressive tactics. The top-performing games (Genshin Impact, Marvel Snap, Zynga Poker) all use cosmetic-only stores, season passes, and live events -- NOT pay-to-win mechanics. We apply these proven patterns.

### 7.0 Table Tiers (Including Million-Chip High Roller)

We sell a 10,000-gem package ($49.99) that converts to 1,000,000 chips. We MUST have tables that support this level of play. Table tiers:

| Table | Min Bet | Max Bet | Seats | Access |
|-------|---------|---------|-------|--------|
| **Casual** | 10 | 500 | 5 | Everyone |
| **Standard** | 100 | 5,000 | 5 | Everyone |
| **High Roller** | 1,000 | 50,000 | 4 | 10,000+ chip balance |
| **Diamond Lounge** | 10,000 | 500,000 | 4 | 100,000+ chip balance OR Master Pass |
| **The Penthouse** | 50,000 | 1,000,000 | 3 | 500,000+ chip balance, invite-only feel |

**The Penthouse** is the premium table for whales who buy the 10,000-gem package:
- Unique table design: dark marble surface, gold trim, ambient cigar lounge lighting
- Exclusive dealer avatar (tuxedo, white gloves)
- Private jukebox queue (only Penthouse players control music)
- Table card on the lobby shows a gold crown icon + "Penthouse" label
- If player doesn't meet the balance requirement, table shows as locked with: "500,000 chip minimum" -- no upsell, just the fact
- Spectators allowed (creates aspiration for lower-tier players)

### 7.1 Private Tables (from Plato Games)
- Create a private table with a 6-character invite code
- Share via link, text, or QR code
- Host controls: min/max bet, deck count, jukebox permissions
- Private tables have their own jukebox queue (host is default DJ)
- Up to 6 players

### 7.2 Spectator Mode (from PokerStars)
- Any table can be watched by spectators
- Spectator count shown on table card: eye icon + count
- Spectators can chat (tagged as [SPECTATOR]) and use emotes
- Spectators see a "Join" floating button if seats open
- This creates social proof and FOMO

### 7.3 Daily Tournaments (from Zynga Poker)
- **Free Daily Tournament** (resets midnight PT):
  - 5,000 tournament chips (separate from real balance)
  - Best 10-hand run counts
  - Top 10 get chip prizes + exclusive daily title
- **Weekend Tournament** ($1,000 chip entry, Saturday-Sunday):
  - 20-hand runs, bigger prizes
  - 10% house rake on entry fees (revenue)
  - Podium animation for top 3

### 7.4 Social Gifting (from Zynga)
- Send chips to friends (from your balance)
- 1 free 100-chip gift per day per friend
- Creates reciprocity loops (they gift back)

### 7.5 Seasonal Events (from Genshin Impact / Marvel Snap)
- Current season theme changes the casino environment:
  - Spring: cherry blossom particles
  - Summer: warm amber sunset lighting
  - Fall: orange/red leaf particles
  - Winter: snowflake particles, ice-blue accents
- Exclusive seasonal cosmetics (avatar items, card backs)
- Seasonal leaderboard (resets each quarter)
- **Season Pass track** (from Marvel Snap model): Free track + Premium track ($4.99 or included in Master Pass). Free track gives chips/quarters. Premium track gives exclusive cosmetics, gems, and a seasonal avatar frame. 30 levels per season, unlocked through play (NOT pay-to-skip). This is the single highest-revenue feature in modern gaming.

### 7.7 Live Events (from Zynga / Huuuge Casino)
- **Weekend High Roller Events**: Limited-time tables with boosted payouts, special dealer, unique table theme. Creates urgency through experience, not sales tactics.
- **Lucky Hour**: Random 1-hour windows where chip earning is 2x. Announced via in-game notification (not push notification). Creates "come back and check" behavior.
- **Community Challenges**: All players contribute to a shared goal (e.g., "Table deals 1 million hands this week"). Progress bar visible on arcade hub. Rewards everyone when hit.

### 7.8 AI Strategy Coach (Differentiator)
- Powered by AI: "Ask the Dealer" feature during practice mode
- Players ask strategy questions in natural language, get instant tips
- Example: "Should I split 8s against a dealer 10?" -> contextual advice with basic strategy chart highlight
- Creates educational value that keeps players engaged longer
- Premium feature: unlimited in Master Pass, 3 questions/day for free players

### 7.6 Strategy Center (from Blackjack Bailey)
- Full basic strategy charts (interactive)
- AI coach powered by Perplexity: ask questions, get tips
- Practice mode: play hands with strategy hints overlay
- "Card Counter" achievement for scoring 95%+ on strategy quiz

---

## PART 8: UPDATED REWARDS SYSTEM

Keep the full rewards system from LOVABLE_REWARDS_PROGRAM_PROMPT.md but apply the Lounge Rules:

### 8.1 Daily Login -- Subtle Calendar
- NOT a blocking modal on load
- A warm gold dot appears on the "Rewards" nav icon indicating an unclaimed reward
- Player opens rewards page at their own pace
- Calendar is clean, minimal, on the rewards page
- Claiming animates a gentle gem collection (not a chest explosion)

### 8.2 VIP Tiers -- Status, Not Upsell
- Tier progress shown in profile panel
- No "buy more to level up" messaging
- Just the progress bar and what's next: "312 VP to Gold"
- Tier perks are discovered through experience, not a feature comparison table

### 8.3 Referrals -- Word of Mouth, Not Spam
- Referral code in profile settings (not a popup)
- Simple share: "Invite a friend. You both get 25 Gems."
- No "SHARE NOW" buttons on every page

---

## PART 9: NAVIGATION RESTRUCTURE

### 9.1 Arcade Hub (`/arcade`)

Clean, premium layout:

**Top section:** Player bar (avatar, name, gem balance, VIP badge if applicable)
- If member: warm gold "Member" badge
- If not: nothing (no "upgrade" prompt here)

**Game Grid (2 columns on mobile, flexible on desktop):**
Each game card:
- Fullbleed game artwork/thumbnail
- Game name
- Brief tagline
- "Play" button (primary, full-width)
- Currency balance shown small at bottom of card
- No "SHOP" button on game cards -- shopping is inside the game or in the Lounge

**Below games:** "The Lounge" link (gem icon + text, not a banner)

**Below that:** "Everlight Membership" link (gold text, small, centered)

### 9.2 Back Navigation (CRITICAL UX FIX)

Every sub-page inside the arcade MUST have a **back arrow** in the top-left corner. Navigating between pages currently feels tedious -- users get lost. Fix this:

- **Back arrow icon** (chevron-left, 24px) in the top-left of EVERY arcade sub-page
- Positioned left of the page title, always visible, always tappable
- Minimum touch target: 44x44px
- Behavior: navigates to the logical parent page, NOT browser history (prevents leaving the app)
- Route hierarchy:
  ```
  /arcade (hub -- no back arrow, this is the root)
    /arcade/blackjack → back to /arcade
      /arcade/blackjack/table/:id → back to /arcade/blackjack
      /arcade/blackjack/settings → back to /arcade/blackjack
    /arcade/alley-kingz → back to /arcade
    /arcade/lounge → back to /arcade
    /arcade/membership → back to /arcade
      /arcade/membership/passes → back to /arcade/membership
    /arcade/rewards → back to /arcade
    /arcade/fairness → back to /arcade
    /arcade/profile → back to /arcade
  ```
- Style: #8A8A8A icon, on hover/tap brightens to #E5E5E5
- On mobile: the back arrow + page title form a sticky top bar (48px height, #0A0A0A background)
- Swipe-right from left edge also triggers back navigation on mobile (iOS-style gesture)

### 9.3 Navigation Hierarchy (VIP-First, Intent-Driven)

The menu must mirror player intent frequency. Players come to PLAY first, check rewards second, shop third. The current menu mixes utility and lifestyle, creating choice fatigue.

**Arcade section nav (desktop -- top bar inside /arcade):**
```
Play  |  Rewards  |  Lounge  |  Membership
```

**Mobile -- bottom tab bar (4 icons, always visible):**
```
🎮 Play  |  ⭐ Rewards  |  💎 Lounge  |  👤 Profile
```
- "Play" is the DEFAULT tab -- always lands here first
- "Membership" accessed from Profile page (not a primary tab -- reduces clutter)
- Rewards nav icon has gold dot if daily reward unclaimed (the ONLY notification badge)
- NO diamond/VIP badge icons in the nav bar itself -- VIP status shows on the player's avatar, not in navigation chrome

**Menu rules:**
- "Play" tab shows the game grid (Blackjack, Alley Kingz, future games)
- NEVER redirect a player to Rewards or Lounge after login -- always land on Play
- Arcade (`/arcade`) is part of the main site nav, clearly visible -- NOT hidden as an Easter egg (players need to find their games easily)
- The VIP/premium FEEL comes from the design and status indicators, not from hiding features behind discovery triggers

---

## PART 10: TECHNICAL -- AUTH & IDENTITY (CRITICAL P0)

This is the #1 priority. Nothing else matters if players can't log in and reach the game.

### 10.1 OAuth Flow -- The `oauth-login` Action (DEPLOYED)

The backend now has an `oauth-login` action on the blackjack-api edge function. Use it.

**API endpoint:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Headers:** `Content-Type: application/json`, `apikey: [anon key]`, `Authorization: Bearer [anon key]`

```typescript
// After Supabase Auth confirms the OAuth session:
const { data: { session } } = await supabase.auth.getSession();
if (session?.user) {
  const res = await fetch(BLACKJACK_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: ANON_KEY, Authorization: `Bearer ${ANON_KEY}` },
    body: JSON.stringify({
      action: 'oauth-login',
      email: session.user.email,
      display_name: session.user.user_metadata?.full_name || session.user.email.split('@')[0],
      avatar_url: session.user.user_metadata?.avatar_url || null,
      provider: session.user.app_metadata?.provider || 'google'
    })
  });
  const data = await res.json();
  if (data.success) {
    // data.player has the full profile
    // data.returning = true if existing account, false if new
    // data.needs_dob = true if new (prompt for DOB later, not now)
    setPlayerProfile(data.player);
    localStorage.setItem('player_profile', JSON.stringify(data.player));
  }
}
```

**This replaces the old flow that called `register` (which required DOB and failed for OAuth users).**

### 10.2 Intent Preservation (FIX: "Play → Auth → Rewards" Bug)

**The problem:** Player clicks "Play Blackjack" → Google OAuth → redirects to `/arcade/rewards` instead of back to the blackjack table. The auth flow loses the player's intent.

**The fix:** Before triggering OAuth, store the intended destination. After auth completes, redirect there.

```typescript
// BEFORE triggering OAuth:
const handlePlayBlackjack = () => {
  // Store where the player wants to go BEFORE auth redirect
  localStorage.setItem('auth_return_to', '/arcade/blackjack');
  // Then trigger OAuth
  supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin + '/arcade' } });
};

// AFTER auth completes (in onAuthStateChange or getSession callback):
const returnTo = localStorage.getItem('auth_return_to');
if (returnTo) {
  localStorage.removeItem('auth_return_to');
  navigate(returnTo); // Go to blackjack, not rewards
} else {
  navigate('/arcade'); // Default fallback
}
```

**Rules:**
- Store `auth_return_to` in localStorage before EVERY OAuth trigger (Play button, Login button, etc.)
- Clear it immediately after use (one-shot)
- Default to `/arcade` if no stored intent
- NEVER default to `/arcade/rewards` -- that's a destination players navigate to by choice, not a landing page
- This applies to Google, Facebook, and any future OAuth provider

### 10.3 Identity Merge (Personal Email + Gmail = Same Player)

**The problem:** A player registers with `richgee@email.com` (personal email), then later logs in with Google (`1m.rich.gee@gmail.com`). The system sees two different emails and creates a second profile, or fails.

**The fix -- Safe Identity Linking:**

1. **On OAuth login:** After `oauth-login` returns, check if the player already has a different account linked. The `oauth-login` action matches by email -- if the Gmail matches an existing `player_accounts` row, it returns that profile. This already works.

2. **Account linking UI (in Profile Settings):**
   - Add section: "Linked Accounts"
   - Show which auth methods are connected (Google, Facebook, Email)
   - "Link another account" button → triggers OAuth flow → on return, calls a `link-account` action
   - Before linking: show confirmation: "Link [google email] to your existing account [display_name]?"
   - After linking: both emails can access the same player_accounts row

3. **Safety rules:**
   - NEVER auto-merge accounts by email string matching alone
   - Require the player to be logged in to one account FIRST, then explicitly link the other
   - If an email is already linked to a different player_accounts row, show: "This email is already associated with another account. Contact support."
   - Log all link operations to an audit table

4. **For now (MVP):** If a player logs in with Google and `oauth-login` doesn't find a matching email in `player_accounts`, it creates a new account. The player can manually contact support to merge. This is SAFE. Auto-merge is Phase 2.

### 10.4 Auth State Machine

```
INITIALIZING (app loads)
  → check getSession()
  → if session exists: go to BRIDGING
  → if no session: go to UNAUTHENTICATED

UNAUTHENTICATED
  → show login/register options
  → on OAuth click: store auth_return_to, trigger signInWithOAuth

BRIDGING (session exists, need player_accounts profile)
  → show subtle loading spinner (NOT "Setting up profile..." with no escape)
  → call oauth-login (or login for email users)
  → if success: go to AUTHENTICATED, navigate to auth_return_to
  → if error: go to ERROR (NOT a loop)

AUTHENTICATED
  → player profile loaded, game ready
  → store in localStorage for fast reload

ERROR
  → show clean error message: "Something went wrong. Try again or use a different login method."
  → "Try Again" button (ONE retry, then show "Contact support")
  → "Use Email Instead" button as fallback
  → NEVER loop. Max 2 retries, then stop and show support link.
  → Player can still navigate the arcade (browse, view leaderboard, etc.) -- just can't play
```

### 10.5 Session Persistence

- On successful auth: store player profile in `localStorage` under key `player_profile`
- On page refresh: check localStorage FIRST, show cached profile immediately
- In background: validate with `getSession()` + fresh `oauth-login` call
- If session expired: clear localStorage, go to UNAUTHENTICATED (no loop)
- This prevents the "refresh wipes state" bug

### 10.6 Error Microcopy

Replace all generic error messages with actionable ones:

| Situation | Bad (current) | Good (new) |
|-----------|---------------|------------|
| Profile load fails | "Profile Failed" | "Couldn't load your profile. Tap to retry." |
| OAuth returns error | (blank loop) | "Login didn't complete. Try again or use email." |
| Network timeout | (infinite spinner) | "Connection lost. Check your signal and retry." |
| Account already exists | "Error" | "An account with this email already exists. Try logging in instead." |
| Unknown error | "Something went wrong" | "Something unexpected happened. If this keeps up, reach out to support." |

All error states show a clear action (retry button, alternative path, or support link). No dead ends.

---

## PART 11: MOBILE OPTIMIZATION

- All layouts mobile-first (single column, then expand)
- Bottom sheet modals instead of centered modals on mobile
- Swipe gestures: swipe left/right on jukebox queue
- Touch targets: minimum 44px
- Haptic feedback on: card deal, chip bet, gem collect, achievement unlock
- Landscape preferred for blackjack (but portrait works)
- Performance: max 60fps target, lazy load all non-critical assets
- Offline indicator: if connection drops, show subtle "reconnecting..." bar at top

---

## PART 12: ELEMENTS TO REMOVE (Kill List)

Remove ALL of the following from the current implementation:

| Kill | Why |
|------|-----|
| Gem balance in persistent header/nav | Creates constant spending anxiety. Show only on relevant pages. |
| "SALE" or "LIMITED TIME" badges on any product | Discount culture destroys premium positioning. |
| Tiered purchase popups at moment of loss | Predatory. The worst mobile game pattern. |
| "Best Value" / "Most Popular" / "WHALE" badges on gem packs | Let the math speak. Players are not stupid. |
| Animated gem/coin icons anywhere in the UI | Slot machine energy. Kill it. |
| Push notifications about deals, sales, or spending | Never interrupt a player's life to ask for money. |
| "First purchase bonus" or "starter pack" promotions | Signals that the base product is overpriced. |
| Comparison charts between free and paid tiers | Creates a "free = inferior" feeling. |
| Any countdown timer attached to a purchase opportunity | Fabricated urgency is the opposite of luxury. |
| Full-screen "OUT OF CHIPS" overlays | Replaced by inline concierge pattern. |
| "Watch an ad for free chips" buttons | No ads in the Everlight ecosystem. Ever. |
| Multiple "BUY" buttons on game screens | Three touches max rule. |

---

## PART 13: COLOR SYSTEM (Monetization-Specific)

| Role | Hex | Usage |
|------|-----|-------|
| Canvas | #0A0A0A | All backgrounds, surfaces |
| Elevated Surface | #111111 | Cards, panels, modal backgrounds |
| Border / Divider | #1A1A1A | Subtle separations |
| Gold Primary | #D4AF37 | Master Pass, premium accents, membership CTAs |
| Gold Soft | #E8D48B | Hover states, secondary gold text |
| Gem Purple | #7B2FF7 | Gem currency, gem shop accents |
| Gem Purple Soft | #9B6DFF | Gem hover, gem quantity text |
| Text Primary | #E5E5E5 | Headings, body copy |
| Text Muted | #8A8A8A | Captions, metadata, secondary info |
| Success | #2ECC71 | Purchase confirmations, "Verified Fair" badge |

**Typography:**
- Product names: Cormorant Garamond Semi-Bold, letterspaced +80
- Prices: Inter Bold (no cents if .00)
- Body: Inter Regular 14px, line-height 1.6, #8A8A8A
- Billing period: shown separately beneath price in 11px muted text

---

## PART 14: LEGAL FOOTER

Every page in the arcade:
"All in-game currencies are virtual items with no real-world monetary value. Rewards are non-transferable and non-refundable. Everlight Ventures reserves the right to modify any program at any time. Must be 18+ to purchase. Not a real-money gambling platform. Prices in USD."
