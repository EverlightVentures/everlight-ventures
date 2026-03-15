# LOVABLE PROMPT: Everlight Blackjack V2 -- Full Rebuild

Paste everything below the line into Lovable.

---

COMPLETE BLACKJACK REBUILD -- Hyper-realistic 3D casino, multiplayer, social features, unique dealers, player accounts, dynamic celebrations, interactive AI chat adlibs. Fix all crashes. This replaces the existing blackjack page entirely at /arcade/blackjack.

## CRITICAL CRASH FIXES (apply first)
1. API now returns camelCase fields: table.name, table.type, table.minBet, table.maxBet, table.seatsTotal, table.seatsFilled, table.jackpot, table.entryCost, table.dealerName, table.dealerAvatar, table.dealerGender
2. Always fallback: `(value ?? 0).toLocaleString()`, `(value ?? "").toUpperCase()`
3. Theme lookup: `TABLE_STYLES[table.type] || TABLE_STYLES["standard"] || { border: "#22C55E" }`
4. Error boundary on every component. Never crash to black screen.
5. All API calls to `https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api` need BOTH headers:
   ```
   "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww",
   "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
   ```

## HYPER-REALISTIC 3D TABLE DESIGN
Make the player feel like they're SITTING at a real high-end casino table. Not flat UI -- immersive 3D perspective:

- **3D perspective view**: Use CSS `perspective(1200px) rotateX(35deg)` on the table to create depth -- you're looking DOWN at the table from the player's POV like sitting in a chair
- **Table surface**: Rich green felt with CSS noise texture overlay (use repeating radial-gradient for fabric grain). Subtle shadow at edges.
- **Wooden rail**: 3D-looking curved rail using multiple box-shadows and gradient (dark walnut to light walnut). Should look thick and rounded like a real casino table bumper rail.
- **Ambient lighting**: Radial gradient spotlight from above illuminating the center of the table. Darker at edges. Like a real casino overhead lamp.
- **Table reflections**: Subtle glossy reflection on the wooden rail (thin white gradient line at top of rail)
- **Background**: Dark casino room behind the table. Subtle bokeh lights in the background (small blurred gold/amber circles at random positions using pseudo-elements). Think luxurious private casino room.
- **Felt texture**: "EVERLIGHT VENTURES" embossed in center of felt in gold (#D4AF37) with font: 'Playfair Display', Georgia, serif. Text-shadow for stitched/embossed look. Size: clamp(1.5rem, 4vw, 3rem).
- **Betting circles**: Gold rings with inner shadow to look inset into the felt
- **Card shoe**: Visible in top-right corner -- a dark box representing the card shoe. Cards deal from here.

## FUTURISTIC ANIMATIONS

**Card Animations:**
- Deal: Cards fly from shoe with a slight arc trajectory (CSS @keyframes with translateX/Y + rotate), land with a soft bounce (scale 1.05 then 1.0), flip with 3D CSS transform (rotateY 0 to 180deg, 0.5s)
- Hit: Card spins in from top-right with trail effect (use pseudo-element with blur that fades)
- Stand: Player's cards get a subtle golden shimmer sweep (linear-gradient animation left to right, 0.5s)
- Bust: Cards crack and shatter -- split into 4 fragments that fly outward with rotation (use clip-path + translateX/Y + rotate + opacity)
- Blackjack: Cards levitate up slightly, golden rays burst outward from behind (conic-gradient rotating), "BLACKJACK!" text scales up with electric glow

**Chip Animations:**
- Place bet: Chip drops from above with realistic physics bounce (2 bounces, decreasing height)
- Win payout: Chips cascade from dealer area to player in a fountain arc, each chip slightly delayed (staggered animation-delay)
- Big win (5x+ bet): Screen shakes slightly (CSS animation translateX +-3px, 0.3s), chip explosion with particle trails
- Loss: Chips dissolve with a swirl effect (rotate + scale down + opacity, sucked toward dealer)

**Table Transitions:**
- Joining table: Camera zoom effect -- scale from 0.8 to 1.0 with blur-to-sharp (filter: blur(10px) to blur(0))
- Leaving table: Reverse zoom out with fade
- Phase transitions (betting -> dealing -> turns -> payout): Subtle light pulse on the felt edges

**UI Element Animations:**
- Buttons: Holographic shimmer on hover (animated gradient shine sweeping across)
- Balance change: Numbers flip like an airport departures board (digit-by-digit roll animation)
- Level up: Full-screen golden particle explosion + shield icon + "LEVEL UP!" with level number
- XP gain: Floating "+10 XP" text that rises and fades after each hand

## DEALER AVATARS -- Unique per table
Each table has a unique dealer. Render a stylized premium avatar above the dealer's card area:

- **Avatar style**: Large circular portrait (120px) with animated gold border ring (rotating dashed border). Chibi-proportioned but HIGH QUALITY -- big expressive eyes, stylish hair, sharp outfits. Premium Supercell-meets-casino art style.
- **Use layered CSS/SVG art** for each dealer:
  - **Aria** (Table 1, female): Warm skin tone (#D4A574), dark wavy hair (drawn with layered box-shadows), gold hoop earrings, black dealer vest with gold trim. Friendly warm smile. Pink gradient glow behind.
  - **Marcus** (Table 2, male): Rich dark skin (#8B5E3C), clean fade haircut, sharp jawline (use clip-path), black suit with gold tie clip. Confident smirk. Blue gradient glow behind.
  - **Valentina** (High Roller, female): Fair skin (#F5DEB3), platinum blonde updo (elaborate SVG path hair), red lips, elegant black dress with diamond necklace (sparkling animation). Sophisticated raised eyebrow. Gold gradient glow behind.
  - **Dominic** (VIP, male): Olive skin (#C4A882), slicked back dark hair, groomed beard (layered shadows), black tuxedo with gold cufflinks (subtle sparkle). Intense mysterious gaze. Purple gradient glow behind.
- **Dealer name plate**: Gold text below avatar with slight letter-spacing: "DEALER: VALENTINA"
- **Dealer animations**:
  - Idle: Subtle breathing (scale 1.0 to 1.015, 4s ease infinite) + occasional blink (every 5s, scaleY on eyes 1 to 0.1 to 1, 0.2s)
  - Dealing: Avatar shifts slightly (translateX -5px then back, 0.3s)
  - Player blackjack: Dealer eyebrows raise (translateY -3px on brow elements), slight impressed nod
  - Player bust: Subtle smirk animation
  - Jackpot: Dealer claps (arm elements animate)
- **Dealer speech bubbles**: The dealer "talks" contextually (see Dynamic Celebrations below)

## DYNAMIC CELEBRATIONS & INTERACTIVE ADLIBS
This is what makes the game feel ALIVE. The system watches game events and triggers personalized messages, animations, and celebrations:

**Dealer Adlibs (speech bubbles from dealer avatar):**
Dealer says contextual things based on game events. Speech bubble appears above dealer for 3 seconds then fades:

On deal:
- "Good luck, {playerName}!"
- "Let's see what the cards have in store..."
- "Feeling lucky today?"

On player blackjack:
- "Impressive, {playerName}! Natural 21!"
- "Now THAT'S how you play!"
- "{playerName} came to WIN today!"

On player bust:
- "Tough break. The cards will turn."
- "So close! Better luck next hand."
- "The table giveth and the table taketh..."

On big bet (500+ chips):
- "High roller alert! {playerName} means business!"
- "Bold move! Let's see if it pays off..."
- "The table just got interesting..."

On win streak (3+ wins):
- "{playerName} is ON FIRE! {streak} wins in a row!"
- "Can anyone stop {playerName}?!"
- "The hot hand continues!"

On lose streak (3+ losses):
- "Hang in there, {playerName}. Your moment is coming."
- "The comeback is always greater than the setback."
- "Keep your head up. Fortune favors the persistent."

On dealer bust:
- "Well... that didn't go as planned for me!"
- "Your patience paid off, {playerName}!"

**Player Achievement Toasts (pop up at top of screen):**
Fancy animated notifications for milestones:
- First hand ever: "WELCOME TO THE TABLE! Your journey begins now." (with confetti)
- 10th hand: "GETTING WARMED UP! 10 hands played." (bronze medal icon)
- 50th hand: "TABLE REGULAR! 50 hands deep." (silver medal)
- 100th hand: "HIGH ROLLER STATUS! 100 hands." (gold medal with sparkle)
- First blackjack: "FIRST BLACKJACK! Remember this moment!" (cards explode into gold particles)
- 5 blackjacks: "BLACKJACK MASTER!" (crown icon descends onto player avatar)
- First big win (1000+ payout): "BIG WINNER! {amount} chips in one hand!" (screen flash gold)
- Win streak 5: "UNSTOPPABLE! 5 wins in a row!" (fire trail animation around player seat)
- Win streak 10: "LEGENDARY STREAK! Can anyone stop you?!" (lightning bolt effects)
- Level up: Full-screen celebration -- golden shield, level number, particle burst, new perks unlocked text

**Multiplayer Social Reactions:**
When playing with others at the table, auto-generated contextual messages appear in chat:
- When someone hits blackjack: "{name} just hit BLACKJACK! [fire emoji]" (auto-posted to chat)
- When someone busts on 22: "So close! {name} busted at 22"
- When someone doubles down and wins: "{name} DOUBLED DOWN and WON! Bold play! [money emoji]"
- When someone splits and wins both: "{name} split and won BOTH hands! [mind blown emoji]"
- When someone makes a huge bet: "[eyes emoji] {name} just bet {amount} chips!"
- When someone's balance hits 0: "{name} is all out! Send them some luck! [prayer emoji]"

**Streak Indicators (visible to all players):**
- 3+ win streak: Fire icon appears next to player name, growing bigger with streak
- 5+ streak: Name turns gold with glow
- 10+ streak: Crown icon replaces fire, electric border on player card
- Losing streak 5+: Rain cloud emoji (subtle, not mean)

**Big Win Celebrations (visible to whole table):**
When any player wins 5x+ their bet:
- Screen-wide gold flash
- "MASSIVE WIN!" text with neon glow effect, scaling animation
- Chip explosion particles from their seat area
- Other players' chat auto-shows "[clap] Nice one, {name}!"
- Sound: triumphant crescendo

When jackpot is won:
- FULL SCREEN TAKEOVER for 5 seconds
- Dark overlay with spotlights scanning
- Slot machine reels locking in 7-7-7
- "PROGRESSIVE JACKPOT WINNER!" in giant marquee letters
- Confetti cannon from all corners
- Chip waterfall counting animation
- Fireworks behind the text
- All players at table see it
- Auto-chat: "!!!JACKPOT!!! {name} just won {amount} chips! [crown][fire][diamond]"

## MULTIPLAYER -- Play with friends in real time
Use Supabase Realtime to sync game state between players at the same table.

**Joining a table:**
- Call `{ action: "join-table", player_id, table_id, display_name, emoji }`
- Subscribe to Supabase Realtime channels:
```javascript
const supabase = createClient("https://jdqqmsmwmbsnlnstyavl.supabase.co", ANON_KEY);
supabase.channel(`table-${tableId}`)
  .on('postgres_changes', { event: '*', schema: 'public', table: 'blackjack_seats', filter: `table_id=eq.${tableId}` }, handleSeatChange)
  .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'table_chat', filter: `table_id=eq.${tableId}` }, handleNewChat)
  .subscribe();
```

**Table view:**
- 5 seat positions in semi-circle at bottom of table
- Your seat: gold glow border, slightly larger
- Other players: visible cards, bets, emoji avatar, name + level badge
- Empty seats: "OPEN" with subtle pulse
- Player join/leave: slide animation + chat announcement

**Leaving:** "LEAVE TABLE" button, calls `{ action: "leave-table", player_id, table_id }`

## SOCIAL FEATURES -- Xbox + Discord + Supercell + Roblox

**1. Live Table Chat (Discord-style)**
- Collapsible chat panel on right side
- Dark background (#111), message bubbles
- Player emoji + name (color-coded by level tier: white 1-5, green 6-10, blue 11-20, purple 21-50, gold 51+) + message + timestamp
- Quick emoji reaction bar: thumbs up, fire, 100, laugh, cry, skull, clap, heart
- Auto-messages for game events (blackjacks, busts, big wins, joins/leaves)
- Send: `{ action: "send-chat", player_id, table_id, display_name, message }`

**2. Player Gamer Cards (Xbox-style)**
- Floating above each seat:
  - Large emoji (48px)
  - Bold display name
  - "LVL {n}" gold pill badge
  - Streak fire indicators
  - Animated border: green=winning, red=losing, gold=hot streak, purple=high level

**3. Emote System (Supercell-style)**
- Quick emote button opens animated grid:
  - Thumbs Up, Clap, Laugh, Angry, Cry, Mind Blown, Fire, Crown, GG, Thanks, Nice, Wow
- Emote pops up as large animated bubble above player seat (2s, scale up then fade)
- Visible to all players via Realtime
- 3-second cooldown between emotes

**4. Friend System (Roblox-style)**
- In profile: "FRIENDS" tab
- Search players: `{ action: "search-players", query }`
- Friends list: online dot (green if at table), current table name, "JOIN" button
- Invite to table: `{ action: "invite-friend", from_player_id, to_player_id, table_id }`

**5. Notifications (mobile game style)**
- Slide-in toasts from top:
  - Friend invites with Accept/Decline
  - Achievement unlocked banners
  - Daily chips reminder
- Check invites: `{ action: "get-invites", player_id }`

**6. Mini-Profile Popup**
- Click any player to see: emoji + name + level + win rate + hands played + biggest win + "Add Friend" button

## WELCOME SCREEN (Login/Register)
Two tabs, smooth slide animation:

**Tab: NEW PLAYER**
- Display Name, Email, Date of Birth (18+ required)
- "CREATE ACCOUNT" gold button
- Calls `register` action

**Tab: RETURNING PLAYER**
- Email only
- "LOG IN" gold button
- Calls `{ action: "login", email }` -- returns full profile if found, 404 if not
- On success, straight to lobby

**Biometric Login (WebAuthn/Passkeys):**
- After first login/register, prompt: "Enable Face ID / Fingerprint login?" with a toggle
- If enabled, use the Web Authentication API (navigator.credentials.create) to register a passkey linked to their player_id
- Store the credential ID in localStorage alongside player_id
- On return visit, if biometric credential exists, show "Log in with Face ID / Fingerprint" button prominently at top of welcome screen
- Uses navigator.credentials.get() to authenticate -- no email/password needed
- Fallback to email login if biometric fails or isn't available
- This works on: iPhones (Face ID/Touch ID), Android (fingerprint/face), laptops (Windows Hello, Touch ID)
- Implementation: store `{ credentialId, playerId }` in localStorage. On biometric success, load player by stored playerId from API.

**Social Login (Google & Facebook):**
- Use Supabase Auth for OAuth. Import `createClient` from `@supabase/supabase-js`.
- Supabase URL: `https://jdqqmsmwmbsnlnstyavl.supabase.co`
- Supabase anon key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
- Google button: `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin + '/arcade/blackjack' } })`
- Facebook button: `supabase.auth.signInWithOAuth({ provider: 'facebook', options: { redirectTo: window.location.origin + '/arcade/blackjack' } })`
- Style: Full-width buttons with official brand colors (Google: white bg + colored G logo, Facebook: #1877F2 blue)
- On OAuth callback, check if player_accounts row exists for that email. If not, auto-create one using their OAuth profile (name, email, avatar_url from provider).
- Show these prominently -- most players will use Google/Facebook instead of typing email/password

## PLAYER PROFILE (slide-out panel)
- Emoji avatar selector (15 options)
- Editable display name
- Level + XP bar (500 XP per level)
- Stats grid: Hands, Win Rate, Winnings, Biggest Win, Blackjacks, Rank
- Hand History: last 50 hands, color-coded (green win, red lose, gray push, gold BJ)
  - Calls `{ action: "get-history", player_id }`
- After each hand, call `{ action: "record-hand", player_id, table_id, bet_amount, side_bets, result, payout, player_cards, dealer_cards, player_total, dealer_total }`
- Friends list, Settings (Sound/Music/Speed/Auto-rebet), Log Out

## DEAL BUTTON -- MUST WORK
When mainBet >= table.minBet: DEAL glows gold, clickable. onClick: lock bets, deal cards with arc animation from shoe. Console.log for debug.

## SESSION TIMER & ANALYTICS
When the player enters the casino (loads the blackjack page), call `{ action: "start-session", player_id, device_type: navigator.userAgent.includes("Mobile") ? "mobile" : "desktop", browser: navigator.userAgent.split(" ").pop() }`. Store the returned `session_id` in React state.

Display a session timer in the top-right corner of the game UI:
- Small pill-shaped badge: clock icon + "12:34" (mm:ss format, counting up)
- Also show hands played this session: "Hands: 7"
- Font: monospace, small (12px), semi-transparent (opacity 0.6)
- Clicking it shows a mini stats popup: session duration, hands played, chips won/lost this session, average bet size

After each hand, also call `{ action: "log-event", player_id, session_id, event_type: "hand_complete", event_data: { bet, result, payout } }`.

Every 60 seconds, send a heartbeat: `{ action: "session-ping", player_id, session_id, current_chips, hands_this_session }`.

On page unload (beforeunload event) or when player clicks "Leave Table", call `{ action: "end-session", player_id, session_id }` using `navigator.sendBeacon()` for reliability.

## SMART SHOP OFFERS (personalized, context-aware)
Instead of a static chip shop, use the smart targeting system:
- Call `{ action: "get-smart-offers", player_id, session_id }` every 5 minutes and after losing 3+ hands in a row
- The API returns up to 3 personalized offers based on: chip balance, session performance, spending history, engagement level
- Display offers as a subtle slide-up banner at bottom of screen (NOT a popup -- non-intrusive)
- Banner shows the top offer: icon + title + price + "BUY" button
- Tap banner to expand and see all offers
- Each offer has a `slug` -- the BUY button calls `POST /functions/v1/create-checkout` with that slug
- Offer badges: "POPULAR" (blue), "BEST VALUE" (gold), "FIRST BUY" (green), "HIGH ROLLER" (purple), "VIP" (gold shimmer)
- If player has urgency text, show it in small red text under the offer

Trigger conditions the API handles:
- Low chips (< 200): pushes chip packs aggressively
- Losing streak (down 500+ this session): pushes best value pack
- Long session (15+ min, no pass): pushes game pass
- High roller behavior: pushes large packs
- Never purchased anything: nudges first buy at $0.99
- Already spent $20+: upsells to Master Pass

## CHIP SHOP (manual access, always available)
- "BUY CHIPS" button always visible in corner. One tap opens full shop modal.
- 500/$0.99, 3000/$4.99, 8000/$9.99
- Blackjack Pass $4.99/mo, Master Pass $9.99/mo
- `POST /functions/v1/create-checkout` with slug

## DOUBLE DOWN RULES
- Player can double down on ANY two-card hand (not just 9/10/11)
- Double down doubles the bet and deals exactly one more card
- Show a "DOUBLE" button next to HIT/STAND when player has exactly 2 cards and enough chips to cover the double
- After doubling, the hand automatically stands (no more actions)
- Double after split is also allowed

## STRATEGY CENTER - "The Everlight Academy"
Add a dedicated strategy education area accessible from the blackjack page. A full learning hub for mastering blackjack basic strategy across all deck types.

### ACCESS POINTS
- **Tab/button on the blackjack page**: Gold book icon with "STRATEGY" label in the game's top navigation bar (next to SHOP, PROFILE, etc.)
- **Post-hand hint**: After each hand, show a small "Was that the right play?" link if the player's action differed from basic strategy. Clicking it opens the strategy center pre-loaded with that hand analysis.
- **AI Coach bubble**: Floating chat bubble (bottom-right corner, above the smart offers banner) - a gold circle with a graduation cap icon. Pulsates subtly. Always accessible during gameplay.

### STRATEGY CENTER LAYOUT (full-screen modal or slide-out panel)
Dark luxury theme consistent with casino (#0A0A0A bg, gold accents, Playfair Display headings).

**Header**: "EVERLIGHT ACADEMY" in gold with subtle glow. Subtitle: "Master the Game" in light gray. Small shield/crest icon.

**Deck Type Selector** (top bar, horizontal tabs):
- Single Deck | Double Deck | 4-Deck Shoe | 6-Deck Shoe
- Active tab: gold underline + gold text. Inactive: gray text.
- Switching tabs updates ALL charts and content below for that deck type.
- Show house edge badge next to each tab:
  - Single: "0.15% Edge"
  - Double: "0.31% Edge"
  - 4-Deck: "0.40% Edge"
  - 6-Deck: "0.42% Edge"

### INTERACTIVE STRATEGY CHARTS
Three charts per deck type: Hard Totals, Soft Totals, Pairs. Display as a tabbed sub-section.

**Chart Design:**
- Grid/table with dealer upcards (2-A) as columns, player hands as rows
- Color-coded cells:
  - **Hit**: Red (#DC2626) with "H"
  - **Stand**: Green (#16A34A) with "S"
  - **Double**: Gold (#D4AF37) with "D" (double if allowed, otherwise hit)
  - **Double/Stand**: Gold outline with "Ds" (double if allowed, otherwise stand)
  - **Split**: Blue (#2563EB) with "SP"
  - **Surrender**: Purple (#7C3AED) with "R" (surrender if allowed, otherwise hit)
- Cells have subtle borders (#333). Rounded corners on outer edges.
- **Hover effect**: Cell expands slightly (scale 1.05), shows tooltip with full explanation: "Hard 16 vs Dealer 10: Surrender if allowed, otherwise Hit. The dealer has a ~77% chance of making 17+ here."
- **Tap on mobile**: Same tooltip as an overlay.
- Header row (dealer cards): Show actual card images (small, stylized) not just numbers.
- Left column (player hands): Show the hand composition (e.g., "A,7" for soft 18, "8,8" for pair of 8s).

**HARD TOTALS CHART (single deck, S17 - example data, adjust per deck type):**
```
Player | 2    | 3    | 4    | 5    | 6    | 7    | 8    | 9    | 10   | A
-------|------|------|------|------|------|------|------|------|------|-----
  8    | H    | H    | H    | D    | D    | H    | H    | H    | H    | H
  9    | D    | D    | D    | D    | D    | H    | H    | H    | H    | H
  10   | D    | D    | D    | D    | D    | D    | D    | D    | H    | H
  11   | D    | D    | D    | D    | D    | D    | D    | D    | D    | D
  12   | H    | H    | S    | S    | S    | H    | H    | H    | H    | H
  13   | S    | S    | S    | S    | S    | H    | H    | H    | H    | H
  14   | S    | S    | S    | S    | S    | H    | H    | H    | H    | H
  15   | S    | S    | S    | S    | S    | H    | H    | H    | R    | H
  16   | S    | S    | S    | S    | S    | H    | H    | R    | R    | R
  17+  | S    | S    | S    | S    | S    | S    | S    | S    | S    | S
```

**SOFT TOTALS CHART (example for single deck):**
```
Player | 2    | 3    | 4    | 5    | 6    | 7    | 8    | 9    | 10   | A
-------|------|------|------|------|------|------|------|------|------|-----
 A,2   | H    | H    | D    | D    | D    | H    | H    | H    | H    | H
 A,3   | H    | H    | D    | D    | D    | H    | H    | H    | H    | H
 A,4   | H    | H    | D    | D    | D    | H    | H    | H    | H    | H
 A,5   | H    | H    | D    | D    | D    | H    | H    | H    | H    | H
 A,6   | D    | D    | D    | D    | D    | H    | H    | H    | H    | H
 A,7   | S    | Ds   | Ds   | Ds   | Ds   | S    | S    | H    | H    | S
 A,8   | S    | S    | S    | S    | Ds   | S    | S    | S    | S    | S
 A,9   | S    | S    | S    | S    | S    | S    | S    | S    | S    | S
```

**PAIRS CHART (example for single deck):**
```
Player | 2    | 3    | 4    | 5    | 6    | 7    | 8    | 9    | 10   | A
-------|------|------|------|------|------|------|------|------|------|-----
 A,A   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | SP
 2,2   | SP   | SP   | SP   | SP   | SP   | SP   | H    | H    | H    | H
 3,3   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | H    | H    | H
 4,4   | H    | H    | H    | D    | D    | H    | H    | H    | H    | H
 5,5   | D    | D    | D    | D    | D    | D    | D    | D    | H    | H
 6,6   | SP   | SP   | SP   | SP   | SP   | SP   | H    | H    | H    | H
 7,7   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | H    | R    | H
 8,8   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | SP   | SP
 9,9   | SP   | SP   | SP   | SP   | SP   | S    | SP   | SP   | S    | S
 10,10 | S    | S    | S    | S    | S    | S    | S    | S    | S    | S
```

NOTE: The chart data above is example/approximate for single deck S17. Implement the full correct basic strategy for each deck type. Key differences between deck types:
- Single deck: More aggressive doubling (double 8 vs 5-6, double A/2-A/5 vs 4-6)
- Double deck: Slightly less aggressive than single, more doubles than shoe
- 4-deck H17: Surrender 15 vs A, double A/8 vs 6
- 6-deck H17: Most conservative, fewer doubles, more surrenders vs A

### STRATEGY GUIDE / "THE BOOK" (scrollable content section below charts)
For each deck type, show a well-formatted guide with sections:

**1. "The Golden Rules" - Quick Reference**
- Bulleted list of the 5 most important rules for that deck type
- Example: "Always split Aces and 8s", "Never split 10s", "Double 11 against everything (except Ace in 6-deck)"
- Gold bullet points, clean typography

**2. "Key Differences" - Why Deck Count Matters**
- Short explanation (3-4 paragraphs) of how fewer decks favor the player
- Card removal effect explained simply
- How it changes doubling and splitting decisions
- Include a visual: small comparison table showing the 5-10 hands that change between deck types

**3. "Common Mistakes" - Hands Most Players Get Wrong**
- List of 10 commonly misplayed hands with explanation
- Format: X "Most players stand on 12 vs 2" -> Checkmark "Hit! Dealer only busts 35% with a 2 showing."
- Each with a "Why?" expandable accordion

**4. "Memory Tricks" - Mnemonics and Analogies**
- Fun, memorable ways to learn the chart:
  - "The Surrender Zone: 15 vs 10, 16 vs 9/10/A - think of it as knowing when to fold in poker"
  - "Soft 18 is NOT a standing hand vs 9/10/A - it is a weak hand in disguise"
  - "8-8 always splits because 16 is the worst hand in blackjack, but two 8s give you two chances at 18"
  - "The dealer's 4/5/6 are bust cards - that is when you get aggressive with doubles and stands on low totals"
- Format: Each trick in a styled card with icon + mnemonic + explanation

**5. "Practice Mode" - Flash Card Drill**
- A mini interactive quiz:
  - Shows a random hand (player cards + dealer upcard) for the selected deck type
  - 4 buttons: HIT, STAND, DOUBLE, SPLIT (split only shown for pairs)
  - Player picks their action
  - Immediate feedback: Checkmark "Correct!" (green flash) or X "The optimal play is Double" (red flash + explanation)
  - Track streak: "12 correct in a row!" with fire icon
  - Track accuracy: "Session: 47/52 (90.4%)"
  - Categories filter: "Hard Only", "Soft Only", "Pairs Only", "All Hands", "My Weak Spots" (hands they have gotten wrong)
  - Speed round mode: 5-second timer per question, rapid fire

### AI STRATEGY COACH - Floating Chat Bubble
The AI coach is powered by a Supabase Edge Function at `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/strategy-coach`.

**Chat Bubble UI:**
- Floating gold circle (56px) in bottom-right corner with graduation cap icon
- Pulse animation (ring expands outward, fades, repeats every 3s)
- Badge: "AI" in small text
- Click to expand into a chat panel (400px wide, 500px tall, slides up from the bubble)
- Chat panel: dark bg (#1A1A1A), gold header "STRATEGY COACH", message history with scroll

**Chat Panel Design:**
- Coach messages: left-aligned, dark card (#252525), gold name "Coach", serif font for the message text
- Player messages: right-aligned, blue card (#1E3A5F)
- Typing indicator: three gold dots bouncing
- Input field at bottom: dark bg, gold border on focus, send button (gold arrow icon)
- Pre-loaded suggestions above input (pill buttons): "Analyze my last hand", "When should I double?", "Explain surrender", "Quiz me"

**Deck Type Context:**
- The coach knows which deck type tab is currently selected in the strategy center
- If the player is at a game table, the coach knows the table type and can reference it
- Always includes deck_type in API calls

**API Calls (all POST to /functions/v1/strategy-coach):**

Headers for all calls: `{ "apikey": "<anon-key>", "Authorization": "Bearer <anon-key>", "Content-Type": "application/json" }`

1. **Ask a freeform question (AI-powered via Perplexity Sonar):**
```
Body: { "action": "ask", "question": "Should I ever take insurance?", "deck_type": "6-deck" }
Response: { "answer": "No, never take insurance...", "deck_type": "6-deck", "citations": ["url1", "url2"], "powered_by": "perplexity-sonar" }
```

2. **Analyze a hand (instant static chart lookup -- free, no AI):**
```
Body: { "action": "analyze-hand", "player_cards": ["A","7"], "dealer_upcard": "9", "deck_type": "6-deck", "player_action": "stand" }
Response: { "correct": false, "optimal_play": "Hit", "optimal_code": "H", "explanation": "Hit because dealer 9 likely has a made hand...", "ev_impact": "Suboptimal play. Over time this deviation costs you expected value.", "hand_classification": { "type": "soft", "key": "A7", "total": 18 } }
```

3. **Get a random tip (instant static -- free, no AI):**
```
Body: { "action": "get-tip", "deck_type": "single", "category": "pairs" }
Response: { "tip": "Always split Aces and 8s...", "deck_type": "single", "category": "pairs", "house_edge": "0.00% to 0.02%", "rules": { "decks": 1, "soft17": "stand" } }
```

4. **Chart lookup (get full strategy chart data for rendering interactive tables):**
```
// Full chart for a deck type (for rendering the grid):
Body: { "action": "chart-lookup", "deck_type": "6-deck" }
Response: { "deck_type": "6-deck", "rules": {...}, "house_edge": "0.54% to 0.63%", "hard": {...}, "soft": {...}, "pairs": {...}, "action_legend": { "H": "Hit", "S": "Stand", ... } }

// Single cell lookup:
Body: { "action": "chart-lookup", "deck_type": "single", "hand_type": "soft", "hand_key": "A7", "dealer_upcard": "9" }
Response: { "action_code": "H", "action": "Hit" }
```

Use chart-lookup to populate the interactive strategy chart grids. Color-code cells: green=Stand, red=Hit, blue=Double, yellow=Split, orange=Surrender.

**Integration with Gameplay:**
- After EVERY hand, silently check if the player's action matched basic strategy
- If it did not match, show a subtle gold sparkle on the AI coach bubble + tooltip: "Want to review that hand?"
- Clicking it opens the coach pre-loaded with the hand analysis
- The coach tracks which hands the player consistently gets wrong and proactively offers tips: "I have noticed you tend to stand on soft 17. Want me to explain why hitting is better?"

**Anon key for all strategy-coach calls:**
`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

Use both `apikey` and `Authorization: Bearer` headers (same key for both), same as all other API calls.

## SOUND DESIGN (Web Audio API, no external files)
- Chip clink: 200ms sine burst at 800Hz
- Card swoosh: filtered white noise, 150ms
- Win: ascending C-E-G chord arpeggio
- Lose: descending low tone
- Blackjack: triumphant brass chord + shimmer
- Chat ping: soft 1200Hz blip
- Emote pop: 600Hz bounce
- Big win: extended crescendo with reverb
- Jackpot: 5-second fanfare sequence
- Level up: ascending scale with chime

## LEGAL
Footer: "Everlight Casino is a social casino. All chips are virtual with no real-world value. No real-money gambling. Must be 18+ to play. Play responsibly."
