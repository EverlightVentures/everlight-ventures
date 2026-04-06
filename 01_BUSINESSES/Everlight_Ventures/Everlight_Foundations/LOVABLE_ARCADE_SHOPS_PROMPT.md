# LOVABLE PROMPT: Per-Game Arcade Shops

Paste this into Lovable to build the per-game shop system.

---

## PROMPT:

Create per-game shop pages for the arcade. Each game has its own currency and shop with a unique theme. There is also a cross-game Master Pass. All purchases go through the Supabase Edge Function at `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/create-checkout` with `{ slug, success_url, cancel_url }`. The anon key header is: `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

### CURRENCY MODEL
| Game | Currency | Icon |
|------|----------|------|
| Alley Kingz | NOS Bottles | Nitrous bottle icon (blue/orange flame) |
| Blackjack | Chips | Casino chip icon (gold) |
| Both | Gems | Diamond icon (purple, existing) |

### 1. ALLEY KINGZ SHOP -- "NOS GARAGE"
Route: /arcade/alley-kingz/shop

Theme: street racing garage vibe. Dark background (#0A0A0A) with neon blue and orange accents. Think Need for Speed underground.

Header: "NOS GARAGE" in neon glow text (blue outline, slight blur glow). Subtitle: "Fuel Up. Race Hard."

**NOS Packs (one-time purchase):**
- 50 NOS Bottles -- $0.99 (slug: `nos-50`)
  - Small nitrous bottle icon
  - Tag: "Starter Tank"
- 300 NOS Bottles -- $4.99 (slug: `nos-300`)
  - Medium nitrous bottle icon with flame
  - Tag: "Street Supply" + "POPULAR" badge
- 800 NOS Bottles -- $9.99 (slug: `nos-800`)
  - Large nitrous tank with dual flames
  - Tag: "Race Day Crate" + "BEST VALUE" badge

**Alley Kingz Game Pass -- $4.99/mo (slug: `ak-game-pass`):**
- Card with racing stripe border
- Perks: 2x NOS earn rate, exclusive car skins, priority matchmaking
- "SUBSCRIBE" button

Display as cards in a row (3 NOS packs + 1 pass). Each card has:
- Icon at top
- Name
- Amount
- Price button (gold for one-time, blue for subscription)
- Badge if applicable

Each purchase button calls create-checkout with the slug. success_url should be `/arcade/alley-kingz/shop?purchased=true`. Show a success toast when `?purchased=true` is in the URL.

### 2. BLACKJACK SHOP -- "HIGH ROLLER LOUNGE"
Route: /arcade/blackjack/shop (also accessible from the in-game chip shop button)

Theme: luxury casino lounge. Dark background with gold (#D4AF37) accents. Velvet and gold vibes.

Header: "HIGH ROLLER LOUNGE" in elegant gold serif text (Playfair Display). Subtitle: "Stack Your Chips."

**Chip Packs (one-time purchase):**
- 500 Chips -- $0.99 (slug: `chips-500`)
  - Single gold chip icon
  - Tag: "Pocket Change"
- 3,000 Chips -- $4.99 (slug: `chips-3000`)
  - Stack of gold chips
  - Tag: "Table Stakes" + "POPULAR" badge
- 8,000 Chips -- $9.99 (slug: `chips-8000`)
  - Large chip stack with sparkle effect
  - Tag: "High Roller Stack" + "BEST VALUE" badge

**Blackjack Game Pass -- $4.99/mo (slug: `bj-game-pass`):**
- Card with gold border
- Perks: 2,000 daily free chips (instead of 1,000), exclusive card backs, High Roller table access
- "SUBSCRIBE" button

Same card layout as Alley Kingz shop but with gold/luxury styling.

### 3. MASTER PASS -- Hero Banner on /arcade hub
On the main /arcade page, add a prominent hero banner above the game list:

- Full-width gradient banner: linear-gradient(135deg, #D4AF37, #B8960C)
- "MASTER PASS" in large bold text (#0A0A0A)
- "$9.99/mo -- Unlock Everything" subtitle
- Perks listed in a row with check icons:
  - All game passes included
  - 5,000 daily free chips
  - VIP table access
  - Exclusive content across all games
  - Priority support
- "GET MASTER PASS" button (dark bg, gold text, slug: `master-pass`)
- Small text: "Cancel anytime. Covers Alley Kingz + Blackjack + future games."

### 4. GEM SHOP (existing, update styling)
The existing gem shop should remain cross-game but get a visual refresh to match the new shop styling:
- Route: keep at existing location
- Add note: "Gems work across all Everlight games"
- Existing slugs: gems-100, gems-600, gems-1500, gems-4000

### 5. ARCADE HUB PAGE (/arcade)
Update the /arcade page layout:
- Master Pass hero banner at top (as described above)
- Game cards below:
  - Alley Kingz card: racing theme, shows NOS balance if logged in, "PLAY" + "SHOP" buttons
  - Blackjack card: casino theme, shows Chip balance if logged in, "PLAY" + "SHOP" buttons
- Each game card shows:
  - Game thumbnail/artwork
  - Game name
  - Brief description
  - Currency balance (if player has one)
  - Two buttons: "PLAY" (goes to game) and "SHOP" (goes to game shop)

### SHARED STYLING
- All shops use the site's dark theme (#0A0A0A background)
- Cards: #1A1A1A background, rounded corners (12px), subtle border
- Hover effect on cards: slight scale(1.02) + shadow increase
- "POPULAR" badge: blue pill
- "BEST VALUE" badge: gold pill
- Price buttons: full-width at bottom of card, 48px height, bold text
- Mobile: cards stack vertically, full-width
- Back button on each shop page to return to /arcade

### LEGAL
Every shop page footer: "All in-game currencies are virtual with no real-world value. Must be 18+ to purchase. Prices in USD."
