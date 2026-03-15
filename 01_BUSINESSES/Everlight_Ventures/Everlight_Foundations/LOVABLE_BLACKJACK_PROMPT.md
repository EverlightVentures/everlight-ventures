# LOVABLE PROMPT: Everlight Blackjack Overhaul

Paste this into Lovable. It's a comprehensive game rebuild.

---

## PROMPT (paste below this line into Lovable):

Build a full-featured social casino Blackjack game at /arcade/blackjack. This is a complete overhaul -- replace the existing blackjack page entirely. Think Zynga Poker meets MyBookie Blackjack: polished, animated, immersive social casino feel. This is a FREE social casino -- virtual chips only, no real-money gambling.

### SUPABASE BACKEND (already deployed)
The backend Edge Functions are live. Connect to them:
- Base URL: `https://jdqqmsmwmbsnlnstyavl.supabase.co`
- Anon key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
- All game actions go to: `POST /functions/v1/blackjack-api` with `{ "action": "...", ... }`

Available actions:
- `register` -- `{ action: "register", display_name, email, date_of_birth }` returns player_id, chip_balance
- `claim-chips` -- `{ action: "claim-chips", player_id }` grants 1000 free chips (once per day, midnight PT reset)
- `get-balance` -- `{ action: "get-balance", player_id }` returns balance + can_claim_free boolean
- `update-balance` -- `{ action: "update-balance", player_id, new_balance, hand_result: { won: bool, payout: number } }`
- `get-leaderboard` -- `{ action: "get-leaderboard" }` top 50 players
- `get-jackpot` -- `{ action: "get-jackpot", table_id }` current progressive pool
- `jackpot-contribute` -- `{ action: "jackpot-contribute", table_id, amount }` adds 1% of Lucky Lucky bets
- `jackpot-win` -- `{ action: "jackpot-win", player_id, table_id, display_name }` awards jackpot, resets pool, Slack notification
- `get-tables` -- `{ action: "get-tables" }` list of available tables

Store player_id in localStorage after registration. On page load, check localStorage for existing player_id, fetch balance from API (NOT from localStorage).

### TABLE DESIGN -- THE FELT
The table is the centerpiece. Design a premium casino felt that dominates the screen:
- Deep green felt (#1a5c2a) with subtle fabric texture (CSS radial gradient to simulate felt grain)
- "EVERLIGHT VENTURES" embossed in gold (#D4AF37) in an arc across the center of the table felt (large, elegant, serif font like Playfair Display). This should look like it's printed/stitched into the felt like a real casino table
- Below the name: "BLACKJACK PAYS 3 TO 2" in smaller gold text
- Curved wooden rail around the table edge (dark walnut brown gradient border, 8px, with subtle shadow)
- Betting circles: gold rings on the felt for main bet, Lucky Lucky (left), and Buster (right)
- Table type indicator in corner: green badge for Standard, gold for High Roller, purple diamond for VIP

### VISUAL STYLE -- Zynga/MyBookie Casino Vibe
- Dark ambient background behind the table (#0a0a0a with subtle radial vignette)
- Cards: realistic card faces with slight 3D shadow, smooth flip animations (CSS 3D transform, 0.4s)
- Dealing animation: cards slide from shoe position (top-right) to player/dealer spots
- Hit animation: card slides in from right, flips to reveal
- Chip graphics: actual casino chip designs (not just numbers):
  - 10 chips: white with blue edge stripes
  - 25 chips: red with white edge stripes
  - 50 chips: blue with white edge stripes
  - 100 chips: green with white edge stripes
  - 250 chips: black with gold edge stripes
  - 500 chips: purple with gold edge stripes
  - 1000 chips: gold with black edge stripes
- Chips are circular, ~40px, with denomination number in center, stack when placed (CSS stacking with slight offset)
- Chip click sound on bet placement (use Web Audio API, short "clink" tone)
- Card deal sound (short "swoosh")
- Win sound (coins cascading), Lose sound (subtle low tone)
- Blackjack sound (triumphant fanfare, 1 second)
- Ambient casino background hum (very subtle, toggleable in settings)

### PLAYER REGISTRATION -- "Enter the Casino" Overlay
On first visit (no player_id in localStorage), show a full-screen overlay:
- Dark backdrop with spotlight effect
- "EVERLIGHT CASINO" in gold marquee text at top
- "Welcome to the Table" subtitle
- Form fields (dark inputs, gold borders, gold focus glow):
  - Display Name (3-20 chars)
  - Email
  - Date of Birth (date picker, must be 18+)
- "TAKE YOUR SEAT" gold button
- Small print: "This is a social casino. Virtual chips only -- no real-money gambling. Must be 18+."
- Call `register` action on submit, store player_id in localStorage

### CHIP BALANCE & FREE CHIPS
- Chip balance displayed top-left in a "chip tray" UI element (gold border box with chip icon + animated number)
- If can_claim_free is true, show pulsing "FREE 1,000 CHIPS" button next to balance (gold glow animation)
- Clicking it calls `claim-chips`, plays coin cascade animation, balance updates
- If balance hits 0 and no free chips available: show "Out of Chips" overlay with:
  - "Come back tomorrow for 1,000 free chips!"
  - Countdown timer to midnight PT
  - "Buy Chips" button (links to chip shop -- see below)

### BETTING INTERFACE
- Bet placement phase: chip selector at bottom of screen (row of clickable chip denominations)
- Click a chip, then click the betting circle on the table to place bet
- Each click adds that chip value to the bet (chips visually stack in the circle)
- Right-click or long-press on bet circle to remove last chip
- "CLEAR" button to remove all bets
- "REBET" button to repeat last hand's bet
- "DEAL" button (large, gold, center-bottom) -- only active when main bet is placed
- Bet limits: Standard table 10-1,000, High Roller 100-5,000, VIP 500-25,000
- Show current bet total next to the betting circle

### SIDE BET AREAS
Two additional betting circles on the felt:

**Lucky Lucky (left of main bet):**
- Smaller gold circle labeled "LUCKY LUCKY"
- Min: 10 chips, Max: 100 chips
- Evaluated immediately after deal: player's 2 cards + dealer's upcard
- Payout table (show on hover/tap):
  - Suited 7-7-7: 200:1
  - Suited 6-7-8: 100:1
  - Unsuited 7-7-7: 50:1
  - Unsuited 6-7-8: 30:1
  - Suited 21: 15:1
  - Unsuited 21: 3:1
  - Total 20: 2:1
  - Total 19: 2:1
- Win animation: gold particle burst from the circle + payout amount floats up in gold text

**Buster Blackjack (right of main bet):**
- Smaller gold circle labeled "BUSTER"
- Min: 10 chips, Max: 100 chips
- Wins when dealer busts, payout by dealer card count:
  - 8+ cards: 250:1 (2,000:1 with player BJ)
  - 7 cards: 50:1 (800:1 with player BJ)
  - 6 cards: 18:1 (200:1 with player BJ)
  - 5 cards: 4:1 (50:1 with player BJ)
  - 3-4 cards: 2:1 (5:1 with player BJ)
- CRITICAL: If any Buster bet is active at the table, dealer MUST complete their hand even if all players bust
- Win animation: red explosion effect + "BUSTED!" text with payout

### GAME ACTIONS
Bottom action bar appears after deal:
- **HIT** -- green button, card slides in
- **STAND** -- red button, hand locks
- **DOUBLE DOWN** -- gold button:
  - If balance >= current bet: doubles the bet normally
  - If balance < current bet but > 0: show "DOUBLE FOR LESS" with remaining balance amount. Wager whatever is left.
  - Double allowed on any total (house rule: "Double Down Madness")
- **SPLIT** -- appears only when first 2 cards match rank
  - Split into 2 hands, play each sequentially
  - Re-splitting allowed up to 3 hands
- **INSURANCE** -- appears when dealer shows Ace
  - Costs half the main bet, pays 2:1 if dealer has blackjack
- 15-second action timer (animated gold ring around active player's area). Auto-stand on timeout.

### DEALER BEHAVIOR
- Dealer hits on soft 17 (standard casino rule)
- Dealer cards: first card face down (hole card), second face up
- After all players act, dealer reveals hole card with flip animation
- Dealer draws with 1-second delay between cards (tension building)

### PROGRESSIVE JACKPOT
- Animated counter at top-center of table, always visible
- Gold text with pulsing glow: "PROGRESSIVE JACKPOT: 5,247 CHIPS"
- Number ticks up in real-time when Lucky Lucky bets are placed (1% contribution)
- Starts at 5,000, caps at 10,000 (resets to 5,000 after win)
- **Win condition:** Player has suited 7-7-7 AND dealer's upcard is any 7
- Player MUST have a Lucky Lucky bet active to qualify
- Win experience:
  - Full-screen takeover: dark overlay with spotlight
  - Slot machine reels animation: three 7s locking in
  - "PROGRESSIVE JACKPOT WINNER!" in large marquee gold text
  - Confetti particles + flashing lights
  - Chip cascade counting animation into balance
  - Dismisses after 5 seconds or on click
  - Calls `jackpot-win` API action

### RESULTS & PAYOUTS
After each hand:
- Blackjack: pays 3:2 (1.5x bet)
- Win: pays 1:1
- Push: bet returned
- Lose: bet lost
- Result text appears over player's hand area: "BLACKJACK!" (gold), "WIN" (green), "PUSH" (gray), "BUST" (red)
- Chips animate: wins slide from dealer to player, losses slide from player to dealer
- After result, call `update-balance` API with new balance and hand result

### RULES PANEL
"?" button in top-right corner opens a slide-out panel with tabs:
- **RULES**: Standard blackjack rules, dealer hits soft 17, double any total, split up to 3x
- **LUCKY LUCKY**: Full payout table with examples
- **BUSTER**: Full payout table, note about dealer completing hand
- **PROGRESSIVE**: Win condition, contribution rate, current pool
- **PAYOUTS**: All payout rates in one view
- Dark panel (#1a1a1a), gold headers, white text

### LEADERBOARD
Accessible from lobby or in-game menu icon:
- "HALL OF FAME" header in gold
- Table: Rank, Name, Total Winnings, Hands Won, Biggest Win, Jackpots
- Top 3 get gold/silver/bronze medal icons
- Current player highlighted in gold
- Pulls from `get-leaderboard` API

### TABLE LOBBY (pre-game screen)
Before sitting at a table, show lobby:
- "EVERLIGHT CASINO" header with ambient casino background
- Table cards showing available tables:
  - Table name, type badge (Standard/High Roller/VIP), seats filled/total
  - Min-Max bet range
  - Current progressive jackpot amount
  - "JOIN" button
- "QUICK PLAY" large button -- joins first available Standard table
- Table type visual distinction:
  - Standard: green card border
  - High Roller: gold card border, gold badge, "Entry: 500 chips"
  - VIP: purple card border, diamond icon, "Entry: 2,000 chips OR VIP Pass"
- High Roller deducts 500 chips on join, VIP deducts 2,000 (or free with pass)

### CHIP SHOP
Accessible from balance area or "Buy Chips" button:
- Modal overlay, dark with gold accents
- Chip packs:
  - 500 chips -- $0.99
  - 3,000 chips -- $4.99
  - 8,000 chips -- $9.99
- Game Pass: Blackjack Pass $4.99/mo (unlimited daily chip claims of 2,000 instead of 1,000)
- Master Pass: $9.99/mo (covers all games + 5,000 daily chips + VIP table access)
- Purchase buttons call create-checkout Edge Function at `POST /functions/v1/create-checkout` with appropriate slug

### LEGAL DISCLAIMER
Required on every page of the game:
- Footer text: "Everlight Casino is a social casino. All chips are virtual with no real-world value. No real-money gambling. Must be 18+ to play. Play responsibly."
- Also include in registration overlay and chip shop

### MOBILE RESPONSIVENESS
- Table scales to fit viewport (use vw/vh units)
- On mobile: action buttons become larger touch targets (min 48px)
- Chip selector becomes a horizontal scroll strip
- Side bet circles stack vertically on very small screens
- Landscape mode preferred -- show "Rotate for best experience" on portrait

### SETTINGS MENU (gear icon, top-left)
- Sound ON/OFF toggle
- Music ON/OFF toggle
- Card speed: Normal / Fast
- Auto-rebet toggle
- Hand history (last 20 hands)

### ANIMATIONS SUMMARY
- Card deal: slide from shoe + flip (0.4s)
- Card hit: slide in from right + flip
- Chip place: drop with bounce + clink sound
- Win: chips slide to player + sparkle
- Lose: chips slide to dealer
- Blackjack: golden flash + fanfare
- Bust: red flash + cards dim
- Side bet win: particle burst (gold for Lucky Lucky, red for Buster)
- Jackpot: full-screen takeover, reels, confetti, cascade
- Timer: gold ring countdown around active player
- Balance update: number rolls up/down (like a counter)

### COLOR PALETTE
- Background: #0A0A0A
- Felt: #1a5c2a (standard), #D4AF37 felt tint (high roller), #4a1a6b (VIP)
- Gold accents: #D4AF37
- Text: #E0E0E0 (primary), #999 (secondary)
- Win green: #22c55e
- Lose red: #ef4444
- Cards: white face, dark border
- Chip colors as defined above
