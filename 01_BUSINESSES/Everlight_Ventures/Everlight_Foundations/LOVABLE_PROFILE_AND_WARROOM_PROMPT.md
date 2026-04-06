# LOVABLE PROMPT: Player Profile System + War Room 83877943 Fixes

Paste everything below into Lovable. This is a focused build that adds: a rich player profile customization page, bot humanization for immersion, and table UI spacing fixes. Do NOT remove or change any existing features.

**Supabase API:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Headers:** `Content-Type: application/json`, `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
**Authorization:** `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
**Supabase URL:** `https://jdqqmsmwmbsnlnstyavl.supabase.co`
**Anon Key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

---

## FEATURE 1: PLAYER PROFILE PAGE (New route: /arcade/profile)

Build a rich, immersive player profile page accessible from the lobby. This is the player's personal space -- their identity in the casino. Think Instagram profile meets gaming character sheet.

### Profile Header Section (Top of page)
- **Banner area**: 200px tall gradient banner at the top. Default color is deep purple-to-gold gradient (#1a0033 to #D4AF37). Players can pick from 8 banner color themes: Royal Purple, Ocean Blue, Crimson Red, Emerald Green, Midnight Black, Sunset Orange, Rose Gold, Diamond Ice. Store selection as `banner_color` in player_accounts.
- **Profile photo**: 96px circular photo overlapping the banner bottom edge (offset -48px). Shows the player's uploaded photo, or their OAuth avatar, or a default avatar with their emoji. Tap to change photo.
- **Display name**: Large bold text below the photo. Tap the pencil icon to edit. Show "(X free renames left)" or "Costs 50 gems" based on rename_count.
- **Title/Badge**: Below the name, show the player's equipped title in a colored pill badge. Example: "High Roller" in a gold pill, "Card Shark" in silver, "Legend" in animated gold+fire gradient. Tap to open title selector.
- **Bio**: Short text below the title, max 160 characters. Italic, lighter color (#A0A0A0). Tap pencil icon to edit. Placeholder: "Tell the table who you are..."
- **Quick stats row**: Horizontal row of 4 stat pills below the bio:
  - Level (gold number in circle)
  - Win Rate (percentage with green/red color based on >50% or <50%)
  - Total Hands (number)
  - Rank (#N or "Unranked")

### Profile Card Section ("Player Card" -- the clout showcase)
This is a visual "trading card" style display that shows off the player's identity. It should look premium and shareable.

- **Card background**: Dark glass effect (backdrop-blur, semi-transparent dark bg with subtle border glow matching banner color)
- **Table Presence Score**: Big number display with the tier name and badge icon
  - Tiers: Fresh (0-10, gray), Regular (11-25, silver), Styled (26-50, gold), VIP (51-100, purple diamond), High Roller (101-200, gold crown), Legend (201+, animated crown + fire)
  - Progress bar showing progress to next tier
- **Stats Grid** (2x3 grid of stat boxes):
  - Chips: current balance with gold coin icon
  - Gems: current gem balance with gem icon
  - Blackjacks: total count with star icon
  - Biggest Win: amount with trophy icon
  - Total Wagered: lifetime amount with chip stack icon
  - Member Since: "X days" with calendar icon
- **Achievements Row**: Show last 4 unlocked achievement icons in a horizontal row. If less than 4, show locked placeholders. Tap to go to full achievements page.

### Name Editing (with rename economy)
- First 3 renames are FREE. Show "2 free renames remaining" in green text.
- After 3 free renames, each rename costs 50 gems. Show "Rename costs 50 gems" in amber text.
- If player doesn't have enough gems, show the cost in red with "Get Gems" button that opens the shop.
- Name validation: 2-20 characters, alphanumeric + spaces + underscores only. No profanity filter needed for now.
- API call: `{ action: "update-profile", player_id, display_name: "NewName" }`
- API returns `{ error: "Name changes cost 50 gems...", rename_count, gem_cost, gems_available }` if out of free renames and insufficient gems. Handle this gracefully with a modal explaining the cost.
- On success the API returns `{ success: true, player: { ...updatedProfile } }`. Update local state AND localStorage immediately.

### Photo Upload
- Tap the profile photo to open upload flow
- Show two options: "Take Photo" (camera) and "Choose from Gallery" (file picker)
- Accept JPEG, PNG, WebP, GIF. Max 5MB.
- After selecting, show a circular crop preview with pinch-to-zoom
- Upload flow:

```typescript
// Step 1: Get a signed upload URL from the edge function
const uploadRes = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({
    action: 'upload-photo',
    player_id: player.player_id,
    file_name: 'profile_photo.jpg',
    content_type: 'image/jpeg',
  }),
});
const { upload_url, public_url } = await uploadRes.json();

// Step 2: PUT the cropped image file to the signed URL
await fetch(upload_url, {
  method: 'PUT',
  headers: { 'Content-Type': 'image/jpeg' },
  body: croppedImageBlob,
});

// Step 3: Save the public URL to the player profile
await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({
    action: 'update-profile',
    player_id: player.player_id,
    profile_photo_url: public_url,
  }),
});
```

- Show loading spinner during upload with "Uploading..." text
- On success, immediately update the displayed photo and persist to localStorage

### Bio Editing
- Tap pencil icon to open inline edit (textarea replaces the bio text in place)
- Max 160 characters with live character counter ("42/160") shown bottom-right of the textarea
- Counter turns amber at 140+, red at 155+
- Save on blur or "Done" button tap
- API call: `{ action: "update-profile", player_id, bio: "My bio text" }`
- On success, show brief green checkmark toast

### Title Selector (Modal)
- Full-screen modal (dark glass overlay) showing all available titles
- Each title shown as a horizontal card with: name, description, color preview, and locked/unlocked state
- Unlocked titles have a green checkmark and are tappable to equip
- Locked titles are grayed out with progress text (e.g., "Play 100 hands (67/100)")
- Currently equipped title has a gold border and "EQUIPPED" badge
- API to get titles: `{ action: "get-titles", player_id }`
  - Returns: `{ titles: [{ code: "card_shark", name: "Card Shark", description: "Play 100 hands", unlocked: true, progress: 100, target: 100 }, ...], equipped: "newcomer" }`
- API to equip: `{ action: "update-profile", player_id, equipped_title: "card_shark" }`
- Available titles (unlocked by stats):

| Code | Name | Requirement | Badge Color |
|------|------|-------------|-------------|
| newcomer | Newcomer | Always unlocked | Gray |
| card_shark | Card Shark | Play 100 hands | Silver |
| high_roller | High Roller | Wager 50,000+ chips total | Gold |
| blackjack_ace | Blackjack Ace | Hit 10 natural blackjacks | Purple |
| veteran | Veteran | Play 500 hands | Blue |
| champion | Champion | Win 250 hands | Green |
| legend | Legend | Reach Level 20 | Animated gold + fire |
| whale | Whale | Wager 500,000+ chips total | Diamond shimmer |
| vip_member | VIP Member | Active VIP subscription | Purple diamond |
| the_grinder | The Grinder | Play 1,000 hands | Dark silver |
| perfectionist | Perfectionist | Reach Level 50 | Platinum |

### Banner Color Picker
- Shown as a horizontal strip of 8 color swatches below the banner in edit mode
- Each swatch is a 40px circle with the gradient preview, outlined when selected
- Tap to select, banner updates immediately with a smooth 300ms CSS transition
- API call: `{ action: "update-profile", player_id, banner_color: "ocean_blue" }`
- Color options with their gradients:

| Key | Name | Gradient (left to right) |
|-----|------|--------------------------|
| royal_purple | Royal Purple | #1a0033 -> #D4AF37 |
| ocean_blue | Ocean Blue | #0a1628 -> #1E90FF |
| crimson_red | Crimson Red | #1a0000 -> #DC143C |
| emerald_green | Emerald Green | #001a0a -> #50C878 |
| midnight_black | Midnight Black | #0a0a0a -> #333333 |
| sunset_orange | Sunset Orange | #1a0800 -> #FF6347 |
| rose_gold | Rose Gold | #1a0d0d -> #E8B4B8 |
| diamond_ice | Diamond Ice | #0a1a1a -> #B0E0E6 |

### Profile Navigation
- Add a "PROFILE" icon button in the lobby header (user silhouette icon, `lucide-react` `User` icon) next to the settings gear
- The profile page has a back arrow in the top-left that returns to /arcade (consistent with existing back-nav patterns)
- Profile is also accessible by tapping your own avatar anywhere in the app (lobby, table seat, leaderboard)
- Other players' profiles are viewable by tapping their avatar at a table or on the leaderboard -- opens a read-only bottom sheet (no edit buttons, no pencil icons)

---

## FEATURE 2: PROFILE MINI-CARD AT TABLE

When seated at a table, the player's seat area should show a richer identity:

- **Avatar**: 48px circle with the player's profile photo (or OAuth avatar, or emoji fallback). Subtle 2px border matching their title tier color.
- **Name + Title**: Display name in white (14px, semibold), title below in smaller (10px) colored text matching the title tier color.
- **Table Presence Badge**: Small tier icon (12px) inline next to the name.
- **Level indicator**: Thin XP progress ring around the avatar circle (gold arc showing progress to next level, implemented as an SVG circle with `stroke-dasharray`).
- **Tap to view profile**: Tapping any player's seat area opens their profile in a slide-up bottom sheet (read-only for other players, editable for self).

---

## FEATURE 3: BOT HUMANIZATION (War Room 83877943)

Currently bots at tables show as "Bot" with static chip counts. This kills immersion. Make bots feel like real players.

### Bot Name Generator
- Remove ALL instances of "Bot" as a display name throughout the codebase
- Generate realistic player names from a pool. Mix first names + optional style suffixes:
  - **First names pool** (30): "Marcus", "Jade", "DeShawn", "Aria", "Viktor", "Luna", "Kai", "Zara", "Trey", "Mika", "Phoenix", "Sage", "Rio", "Nova", "Dante", "Isla", "Axel", "Maya", "Jace", "Lena", "Omar", "Sienna", "Blaze", "Ivy", "Remy", "Kira", "Chase", "Nyla", "Soren", "Ember"
  - **Optional suffixes** (30% chance to append one): "21", "_VIP", "Ace", "Lucky", "Pro", "xo", "99", "Jr", "Real", "_"
  - Example outputs: "Marcus21", "Jade", "DeShawn_VIP", "AriaAce", "Viktor"
- Each bot gets a randomly selected emoji from the existing emoji avatar set
- Each bot gets a random title from: "Newcomer" (40%), "Card Shark" (25%), "Regular" (20%), "Veteran" (15%)
- Each bot gets a random level between 3-25 (normal distribution centered on 10, stddev 5)
- Bot identities are generated on table join and persist for the duration of that bot's sit session (not re-randomized each hand)

### Bot Chip Count Randomization
- Bots should NOT all start with the same chip count
- Random chip balance between 800-15,000 (normal distribution centered on 3,500, stddev 2,000, clamped to 800-15,000)
- Chip counts should change between hands: add or subtract their bet amount based on win/loss to simulate real play
- Don't let bot chips go below 200 -- when a bot drops below 200, auto-refresh their balance to a random amount between 1,000-3,000 (simulates a "rebuy")

### Bot Sit/Walk Behavior
- Bots should join and leave tables at random intervals to simulate a living casino
- **Sit duration**: random between 3-15 minutes (normal distribution centered on 7 min)
- After a bot leaves, a new bot (different name/avatar/level) joins within 30-90 seconds
- **Leave animation**: Avatar fades out over 500ms, seat briefly shows "Empty" in gray italic text
- **Arrive animation**: New bot slides into the seat from below (200ms ease-out), brief toast notification at the bottom of the table view: "{name} joined the table"
- Always maintain at least 1 bot at each table (never let a table go completely empty while a player is seated)
- During the player's active hand (between deal and settle), bots do NOT leave -- they wait for the current round to resolve before departing

### Bot Betting Behavior
- Bots should vary their bet amounts realistically based on their personality type (assigned at creation):
  - **Conservative bots** (40% of all bots): bet 1-2x the table minimum
  - **Moderate bots** (35%): bet 2-5x the minimum
  - **Aggressive bots** (20%): bet 5-15x the minimum
  - **Whale bots** (5%): bet 50-100% of the table maximum
- Bots occasionally "think" before acting: show a pulsing "..." animation for a random 1-3 second delay before hit/stand decisions
- Bots sometimes make "suboptimal" plays (15% chance of deviating from basic strategy) to feel human -- e.g., hitting on 17, standing on 12 against a dealer 6

---

## FEATURE 4: TABLE UI SPACING FIXES (War Room 83877943)

### Overlap/Squeeze Fixes
- **Card overlap at full table**: When 4-5 players are seated, cards can overlap between adjacent seats. Fix by:
  - Reducing card size from 70px to 60px width when 4+ players are seated (use dynamic class)
  - Increasing seat spacing: use `gap: 8px` minimum between seat container elements
  - Cards stack tighter vertically within a hand: 12px overlap between cards instead of 16px
- **Bet amount overlap with cards**: Move the bet chip display to BELOW the seat area (beneath the player name), not overlapping the card zone
- **Chat bubble overlap**: Player chat messages/emotes should appear ABOVE the table surface area as floating bubbles, never overlapping player seat elements
- **Mobile responsiveness** (screens < 400px wide):
  - Hide bot title badges (just show the display name)
  - Reduce avatar size from 48px to 36px
  - Stack chip count below name instead of inline beside it
  - Cards scale to 50px width
  - Reduce font sizes by 2px across the table view

### Dealer Area Spacing
- Add 16px padding between the dealer's card area and the first row of player seats
- Dealer name plate ("DEALER") should not overlap with the deck/shoe graphic -- place it centered above the dealer's cards
- Center the dealer area horizontally regardless of how many players are seated

### Seat Layout (5-seat arc)
- Seats should form a gentle arc (not a straight line) mimicking a real blackjack table
- Use CSS transforms with slight rotation to create the curve:

```css
/* 5-seat arc layout */
.seat-1 { transform: translateX(-120%) rotate(-8deg); }
.seat-2 { transform: translateX(-60%) rotate(-4deg); }
.seat-3 { transform: translateX(0) rotate(0deg); }   /* center seat */
.seat-4 { transform: translateX(60%) rotate(4deg); }
.seat-5 { transform: translateX(120%) rotate(8deg); }

/* Mobile: compress the arc to fit viewport */
@media (max-width: 480px) {
  .seat-1 { transform: translateX(-90%) rotate(-6deg); }
  .seat-2 { transform: translateX(-45%) rotate(-3deg); }
  .seat-3 { transform: translateX(0) rotate(0deg); }
  .seat-4 { transform: translateX(45%) rotate(3deg); }
  .seat-5 { transform: translateX(90%) rotate(6deg); }
}
```

- Each seat container should have `transform-origin: bottom center` so cards fan outward naturally
- When fewer than 5 players are seated, spread remaining seats evenly across the arc (don't cluster them to one side)

---

## FEATURE 5: PROFILE QUICK-VIEW IN LOBBY

In the lobby, enhance the player info bar at the top:

- **Left side**: Player's profile photo (40px circle, border matching title color) + display name (16px, semibold, white) + title badge (small colored pill, 10px text)
- **Center**: Chip balance (gold text, coin icon) + Gem balance (blue text, gem icon)
- **Right side**: Level badge (24px gold circle with level number in white) + Settings gear icon
- Tapping the left side (photo + name area) navigates to the full profile page (/arcade/profile)
- This bar should be sticky at the top of the lobby view with `position: sticky; top: 0; z-index: 50;` and a subtle dark glass background (`bg-black/70 backdrop-blur-md`)

---

## DATABASE MIGRATIONS NEEDED (run in Supabase SQL Editor)

The edge function expects these new columns. Run this SQL in Supabase BEFORE deploying the frontend update:

```sql
-- Add new profile columns to player_accounts
ALTER TABLE player_accounts ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT '';
ALTER TABLE player_accounts ADD COLUMN IF NOT EXISTS profile_photo_url TEXT;
ALTER TABLE player_accounts ADD COLUMN IF NOT EXISTS banner_color TEXT DEFAULT 'royal_purple';
ALTER TABLE player_accounts ADD COLUMN IF NOT EXISTS equipped_title TEXT DEFAULT 'newcomer';
ALTER TABLE player_accounts ADD COLUMN IF NOT EXISTS rename_count INTEGER DEFAULT 0;

-- Create player_achievements table if it doesn't exist
CREATE TABLE IF NOT EXISTS player_achievements (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  player_id UUID REFERENCES player_accounts(player_id),
  achievement_code TEXT NOT NULL,
  unlocked_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(player_id, achievement_code)
);

-- Index for fast achievement lookups
CREATE INDEX IF NOT EXISTS idx_player_achievements_player
  ON player_achievements(player_id);

-- Create player-assets storage bucket for profile photos
-- (Run this via Supabase Dashboard -> Storage -> New Bucket)
-- Bucket name: player-assets
-- Public: Yes
-- Max file size: 5MB
-- Allowed MIME types: image/jpeg, image/png, image/webp, image/gif

-- Storage policy: allow authenticated uploads to player-assets
-- (Run via Dashboard -> Storage -> player-assets -> Policies -> New Policy)
-- Policy name: "Allow player photo uploads"
-- Operation: INSERT
-- Target roles: anon, authenticated
-- WITH CHECK: true

-- Add gems currency row for existing players who don't have one yet
INSERT INTO game_currencies (player_id, game_id, currency_name, balance)
SELECT player_id, 'blackjack', 'gems', 0
FROM player_accounts
WHERE player_id NOT IN (
  SELECT player_id FROM game_currencies
  WHERE game_id = 'blackjack' AND currency_name = 'gems'
);
```

---

## EDGE FUNCTION UPDATES NEEDED

The `blackjack-api` edge function needs to handle these new actions. If the edge function does not yet support them, the frontend should gracefully degrade (show cached data, suppress errors for missing endpoints, and log warnings to console).

### API Response Types (IMPORTANT)

The `get-profile` response returns ALL numeric fields as actual JavaScript numbers (not strings). Do NOT call `.toFixed()` or `.toString()` on them without first wrapping in `Number()`. Example safe pattern:
```typescript
// SAFE: all these are guaranteed numbers from the API
const winRate = profile.win_rate;  // number, e.g. 52.3
const chips = profile.chip_balance; // number, e.g. 5000
const hands = profile.total_hands;  // number, e.g. 247
const rank = profile.rank;          // number, e.g. 5 (0 = unranked)
```

### Actions the frontend will call:

1. **`update-profile`** -- already partially exists. Must now also accept: `bio`, `profile_photo_url`, `banner_color`, `equipped_title`. The edge function should increment `rename_count` when `display_name` changes and enforce the 3-free / 50-gems-after economy.

2. **`upload-photo`** -- new action. Accepts `player_id`, `file_name`, `content_type`. Returns `{ upload_url, public_url }` using Supabase Storage `createSignedUploadUrl` for the `player-assets` bucket at path `{player_id}/{file_name}`.

3. **`get-titles`** -- new action. Accepts `player_id`. Returns all title definitions with unlock status computed from the player's stats (hands_played, total_wagered, blackjack_count, wins, level).

### Frontend graceful degradation:
- If `upload-photo` returns 400/404/500, fall back to showing a toast: "Photo uploads coming soon!" and keep the existing avatar.
- If `get-titles` fails, show a hardcoded list of titles with all marked as locked except "Newcomer".
- If `update-profile` fails for new fields (bio, banner_color, etc.), save to localStorage only and retry on next app load.

---

## TESTING CHECKLIST

1. Profile page loads at /arcade/profile with all sections visible (banner, photo, name, title, bio, stats, player card)
2. Name edit works 3 times free, then prompts for 50 gems on the 4th attempt
3. Photo upload works end-to-end (pick image -> crop preview -> upload -> new photo displays)
4. Bio edit works with 160 char limit, live counter updates, saves on blur
5. Title selector modal shows unlocked/locked titles correctly with progress indicators
6. Banner color picker changes the banner immediately with smooth gradient transition
7. Bots have realistic human names (no "Bot" label anywhere), varied chip counts, and join/leave tables over time
8. Table UI has no overlapping elements when 5 players are seated (test on 375px wide viewport)
9. Other players' profiles are viewable in read-only mode (no edit controls shown)
10. Profile is accessible from: lobby header icon, tapping own avatar, leaderboard entry
11. Back arrow on profile page navigates to /arcade correctly
12. Mobile layout renders cleanly on screens 320px-480px wide without horizontal scroll or element overlap
13. Bot sit/walk animations play smoothly (fade out on leave, slide in on arrive)
14. Bot "thinking" delay shows the pulsing dots before their action
15. Dealer area has proper spacing from player seats on both desktop and mobile

## IMPORTANT: Do NOT break existing features
- Keep ALL existing game functionality (dealing, hitting, standing, doubling, splitting, side bets, insurance)
- Keep ALL existing auth flows (Google OAuth, Facebook OAuth, email login/register)
- Keep ALL existing animations and visual styling (card flips, chip animations, win celebrations)
- Keep ALL existing social features (chat, emotes, friends, leaderboard, gifting)
- Keep ALL existing shop and economy features (chip purchases, daily rewards, spin wheel)
- This is ADDITIVE -- new profile features + bot improvements + spacing fixes layered on top of the working foundation
