# Vantaris Game Architecture
## Master Blueprint -- Blackjack (then all games)

> This is the single source of truth for what the game IS,
> what it NEEDS, and what ORDER to build it in.
> No more patchwork. Build it right.

---

## AUDIT RESULTS: What Exists vs What's Missing

### LIVE AND WORKING (in Everlight VIP table)
- [x] 6-deck shoe, Fisher-Yates shuffle, auto-rebuild at <15 cards
- [x] Hit / Stand / Double / Surrender (server-authoritative)
- [x] Natural blackjack detection (instant settle)
- [x] Dealer hits to hard 17
- [x] 4 dealer personas with full voice line sets
- [x] ElevenLabs TTS + browser fallback
- [x] Dealer mood engine (neutral/impressed/annoyed)
- [x] Streak reactions (3-win, 5-win, 3-loss)
- [x] 10-hand milestone commentary
- [x] Idle chatter (45-90s interval)
- [x] 4 bot players with basic strategy AI (80%/20%)
- [x] Bot sitting-out mechanic (20% start, 10% toggle)
- [x] Bot rebuy at <200 chips
- [x] Three.js 3D casino scene (table, felt, chandelier, neon, fog, dust)
- [x] 2.5D card rendering (DOM over 3D canvas)
- [x] Card deal spring animation (scale 0 rotateY 90 -> 1/0)
- [x] Win particles (gold for BJ, green for win)
- [x] Result banner with bangIn spring animation
- [x] Procedural lounge jazz (Web Audio API)
- [x] Music + voice toggles
- [x] XP + 6-tier rank system
- [x] 9 achievements (server-triggered)
- [x] Table Presence multiplier (outfit x aura x rank)
- [x] Avatar studio (base/outfit/aura/colors)
- [x] Cosmetics shop (chips/gems dual currency)
- [x] Gem packages via Stripe
- [x] Ad rewards (100 chips, 10/day)
- [x] Leaderboard
- [x] Hand history
- [x] Profile sidebar

### STUBBED / BROKEN (exists but doesn't work)
- [ ] Split -- button shows, function returns "coming soon"
- [ ] Card backs -- shop category exists, not applied to card rendering
- [ ] Table felts -- shop category exists, not applied to Three.js felt
- [ ] Bacardi Ice voice -- shares Marcus's voice ID (needs unique)
- [ ] TWEEN.js -- imported, update called, no tweens defined
- [ ] OAuth -- Google/Facebook stubs, allauth not installed

### DESIGNED BUT NOT BUILT (in GDD documents)
- [ ] Side bets (Perfect Pairs, 21+3, Lucky Ladies, War)
- [ ] Insurance
- [ ] Jukebox system (Quarters currency, song queue)
- [ ] 4 vibe states (HYPE/HEAT/CHILL/AFTER-HOURS)
- [ ] NPC crowd reactions
- [ ] Cinematic camera zoom on blackjack
- [ ] Card scatter on bust
- [ ] Multi-deck selection (1/2/4/8 decks)
- [ ] Multiplayer (WebSocket / Photon PUN 2)
- [ ] Tournament tables
- [ ] Table variants (Classic, High Roller, Lounge, Tournament)
- [ ] Full 3D card meshes
- [ ] Jukebox skins
- [ ] DJ Crown seasonal cosmetic
- [ ] Story mode
- [ ] Battle Royale mode

### NEVER EXISTED -- NEW FROM RESEARCH
- [ ] Lightning multipliers (random 2x-25x per round)
- [ ] Infinite Blackjack (all players share starting hand)
- [ ] Speed Blackjack (fastest decision acts first)
- [ ] Blackjack Switch (swap top cards between two hands)
- [ ] Spanish 21 variant
- [ ] Progressive jackpot side bet
- [ ] Six Card Charlie rule
- [ ] Multi-hand (2-3 simultaneous hands)
- [ ] TCG card skins (deck-wide visual themes)
- [ ] Card rarity tiers (Common/Uncommon/Rare/Mythic/Legendary)
- [ ] Card XP / leveling (cards evolve visually with use)
- [ ] Holographic / foil card effects (tilt-reactive)
- [ ] Gambit energy effect (charge/vibrate/particle trail on play)
- [ ] Table lobby with seat selection
- [ ] VIP room (rank-gated, exclusive dealer)
- [ ] Camera angle selection (overhead/dealer-face/side/card-cam)
- [ ] Player decision visibility (see others hit/stand in real-time)
- [ ] Think timer (visible when other player is deciding)
- [ ] Chat/emotes during play
- [ ] P2P challenges (head-to-head blackjack)

---

## THE BUILD ORDER (Priority Tiers)

### TIER 1: FIX THE CORE GAME (Week 1)
These are broken or missing basics that make the game feel incomplete.

1. **Fix card positioning** -- absolute screen coordinates matching VIP table
   (dealer at 30%, player at 62%, 80px spacing, centered)
2. **Fix card visuals** -- proper white cards with red/black suits, rounded corners,
   face-down = navy gradient + gold diamond. Match the 70x100px originals.
3. **Wire Split** -- actual split mechanic, two hands, independent play
4. **Add Insurance** -- when dealer shows Ace, offer insurance (2:1 payout)
5. **Fix dealing order** -- animate one card at a time with 300ms stagger
   (P1 -> D1 -> P2 -> D2-facedown), not all at once
6. **Fix dealer reveal timing** -- 300ms gap, then reveal, then draw-to-17
   with 600ms between each draw (matching original)
7. **Result stays 2.2 seconds** then auto-reset (matching original)
8. **Remove hologram cones** -- replace with proper disc+beam+ring
   or remove entirely for cleaner look
9. **Fix bot labels** -- project 3D positions to 2D screen coordinates
   so bot names float above their seats correctly

### TIER 2: SIDE BETS + GAME DEPTH (Week 2)
What makes the game INTERESTING beyond basic blackjack.

10. **Perfect Pairs side bet** -- 5:1 mixed, 12:1 colored, 25:1 perfect
11. **21+3 side bet** -- poker hand from player 2 + dealer upcard
    (5:1 flush, 10:1 straight, 30:1 trips, 40:1 straight flush, 100:1 suited trips)
12. **Lucky Ladies** -- player total 20 pays 4:1 to 1,000:1
13. **Lightning multipliers** -- random 2x-25x assigned to a winning hand
    total each round. Huge excitement factor.
14. **Progressive jackpot** -- $1 side bet, suited Aces trigger jackpot
15. **Six Card Charlie** -- 6 cards without busting = auto-win
16. **Multi-hand mode** -- play 2-3 hands simultaneously

### TIER 3: CARD SKIN SYSTEM (Week 2-3)
The TCG layer that makes cards collectible and exciting.

17. **Deck skin system** -- visual themes applied to entire deck
    - Neon Noir (dark bg, neon suit outlines)
    - Royal Court (illustrated face cards, unique per dealer)
    - Voidwalker (black/purple, minimalist)
    - Sakura (watercolor painted, Japanese aesthetic)
    - Vantaris Black (Vantablack finish, absorbs light)
18. **Card rarity visual effects**
    - Common: plain card
    - Uncommon: silver foil border shimmer on hover
    - Rare: gold foil pulse, slow breathing glow
    - Mythic: animated diagonal shimmer sweep every 3s
    - Legendary: rainbow spectrum shift on cursor/tilt
19. **Card XP system** -- individual cards (e.g., your Ace of Spades)
    gain XP each time they appear in a winning hand.
    At thresholds: Base -> Bronze glow -> Gold aura -> Mythic particle trail
20. **Gambit energy effect** -- on Hit/Double/Split:
    card vibrates (3px, 8Hz), pink/magenta particle burst from corners,
    inner glow pulse, launches with trailing particle streak + motion blur

### TIER 4: TABLE LOBBY + MULTI-TABLE (Week 3)
The infrastructure for multiple game experiences.

21. **Table lobby page** -- grid/list of available tables
    - Filter by: stakes (min/max), game variant, dealer, theme
    - Each tile shows: dealer avatar, player count, bet range, theme badge
    - "HOT" tag on high-action tables
    - Quick Join button (auto-join lowest-stakes open table)
22. **Table variants**
    - Classic (standard rules, 3:2 blackjack)
    - Lightning (random multipliers each round)
    - Speed (fastest decision acts first)
    - Switch (swap cards between two hands)
    - High Roller (500+ min bet, VIP dealers, exclusive felt)
23. **VIP Room** -- rank-gated (Diamond+), Bacardi Ice exclusive,
    different ambient music, velvet/obsidian theme, higher limits
24. **Seat selection** -- see 7 seats, which are occupied (avatars shown),
    click open seat to join

### TIER 5: MULTIPLAYER + SOCIAL (Week 4+)
What makes it a COMMUNITY, not a solo game.

25. **See other players' cards** -- after their turn, cards visible
26. **Decision visibility** -- "Player 2 HIT" / "Player 4 STAND" shown live
27. **Think timer** -- visible countdown when a player is deciding
28. **Chat** -- text chat at the table
29. **Emotes** -- quick reactions (fire, crown, money, clap)
30. **Proper dealing order** -- left to right, one player at a time
31. **Camera angles** -- overhead, dealer face, side profile, card close-up
32. **Watch mode** -- spectate a table without playing
33. **Tournament mode** -- timed entry, fixed buy-in, elimination rounds

---

## CARD DESIGN SPEC

### Card Dimensions
- Base: 70px x 100px (mobile), 80px x 115px (desktop)
- Border radius: 8px
- Box shadow: 0 4px 20px rgba(0,0,0,0.6)

### Card Face (standard)
- White background (#fff) with subtle gradient (#fff -> #f8f6f0)
- Red suits (hearts, diamonds): #c0392b
- Black suits (spades, clubs): #111
- Rank text: 1.5rem, bold, top-left + bottom-right (rotated)
- Suit symbol: 1.1rem below rank
- Center pip: large suit symbol or face card letter
- Face cards (J/Q/K): subtle gold tint on border

### Card Back (face-down)
- Background: linear-gradient(135deg, #1a3a6b, #0d1f3c)
- Border: 2px solid #c9a84c
- Center: gold diamond icon (2rem)
- When using custom card back skin: replace entire face-down visual

### Card Deal Animation
1. Card starts off-screen right, scale(0), rotateY(90deg)
2. Spring transition: scale(1), rotateY(0) with cubic-bezier(0.34,1.56,0.64,1)
3. Duration: 300ms per card
4. Stagger: 300ms between cards (total deal: ~1.2s for 4 cards)

### Card Flip (dealer reveal)
1. 300ms anticipation gap (silence)
2. Card rotates Y from 0 to 90deg (150ms)
3. At 90deg: swap content from back to face
4. Card rotates Y from 90deg to 0 (150ms)
5. Total flip: 300ms + 300ms gap = 600ms

---

## CHIP DESIGN SPEC

### SVG Casino Chips (already built in CasinoChip.tsx)
- Concentric circles: outer ring, inner ring, dashed ring, core
- 8 edge notches evenly spaced (alternating accent color)
- Metallic sheen radial gradient overlay
- Denomination in Cinzel serif
- 6 colors: Red(10), Green(25), Blue(100), Purple(500), Gold(1K), Black(5K)
- Sizes: 60px unselected, 72px selected
- Hover: lift -6px, scale 1.1
- Selected: breathing pulse animation + white ring

---

## DEALER PERSONA SPEC

### 4 Dealers (preserved from original)
| Dealer | Table | Voice | Default For |
|--------|-------|-------|-------------|
| Aria Sinclair | Classic | Sarah (EXAVITQu4vr4xnSDxMaL) | Public floor |
| Marcus Vega | High Roller | Deep male (onwK4e9ZLuTAKqWW03F9) | High stakes |
| Kanisha Thompson | VIP Lounge | Warm female (XrExE9yKIg1WjnnlVkGX) | VIP room |
| Bacardi Ice | VIP Elite | NEEDS UNIQUE VOICE | Vanta Black table |

### Voice Line Categories (per dealer, 2-3 lines each)
deal, hit, stand, bust, win, blackjack, push, dealer_bust,
dealer_draw, surrender, low_chips, streak_3_win, streak_5_win,
streak_3_loss, hand_10_milestone, idle (3 lines, 45-90s interval)

---

## TABLE LOBBY SPEC

### Layout
```
[Filter Bar: Stakes | Variant | Dealer | Theme]
[Game Cards Grid]
  [Classic Table  ] [Lightning    ] [Speed       ]
  [Min:10 Max:5K  ] [Min:50 Max:25K] [Min:25 Max:10K]
  [Aria | 4/7 seats] [Marcus | 6/7 ] [Kanisha | 2/7]
  [           PLAY ] [        PLAY  ] [        PLAY ]

[High Roller     ] [Switch       ] [Tournament  ]
[Min:500 Max:50K ] [Min:100 Max:25K] [Buy-in: 1K ]
[Marcus | 3/7    ] [Aria | 5/7   ] [Bacardi | 0/8]
[     VIP ONLY   ] [        PLAY  ] [   REGISTER ]

[Quick Join: Auto-join lowest stakes open table]
```

### Table Card Contents
- Dealer avatar (circular, 48px) + name + title
- Table name + variant badge
- Bet range (MIN-MAX)
- Player count / max seats
- "HOT" tag if >5 players
- "VIP" lock icon if rank-gated
- Table theme color (felt color as card accent)

---

## SIDE BET PAYOUT TABLES

### Perfect Pairs
| Type | Condition | Payout |
|------|-----------|--------|
| Mixed Pair | Same rank, different color | 5:1 |
| Colored Pair | Same rank, same color, different suit | 12:1 |
| Perfect Pair | Identical rank + suit | 25:1 |

### 21+3 (Player's 2 cards + dealer upcard)
| Hand | Payout |
|------|--------|
| Flush | 5:1 |
| Straight | 10:1 |
| Three of a Kind | 30:1 |
| Straight Flush | 40:1 |
| Suited Trips | 100:1 |

### Lucky Ladies (Player total = 20)
| Condition | Payout |
|-----------|--------|
| Any 20 | 4:1 |
| Suited 20 | 9:1 |
| Matched 20 | 19:1 |
| Queen of Hearts pair | 125:1 |
| QH pair + dealer blackjack | 1,000:1 |

### Lightning Multipliers
Random multiplier assigned to a winning hand total each round:
2x, 5x, 8x, 10x, 15x, 20x, or 25x.
Mandatory 100% lightning fee on top of bet.
If your winning total matches the multiplied total, payout is boosted.

---

## CARD SKIN CATALOG

### Deck Themes (apply to entire deck)
| Skin | Aesthetic | Unlock |
|------|-----------|--------|
| Classic | White card, standard pips | Free |
| Neon Noir | Dark bg, bright neon suit outlines | 5,000 GC |
| Royal Court | Illustrated face cards, gold filigree | 100 Gems |
| Voidwalker | Black/purple, minimalist geometry | 150 Gems |
| Sakura | Watercolor, cherry blossom pips | 200 Gems |
| Vantaris Black | Vantablack finish, gold edge | Legend rank |
| Gambit | Pink/magenta energy effect on every card | Legendary drop |

### Card Back Designs
| Back | Style | Unlock |
|------|-------|--------|
| Classic Navy | Navy gradient + gold diamond | Free |
| Dragon | Red/black embossed dragon | 3,000 GC |
| Gold Foil | Pure gold foil finish | 60 Gems |
| Deep Space | Nebula and stars | 75 Gems |
| Vantaris Seal | Vantablack with gold star logo | VIP only |

---

## WHAT WE BUILD NEXT

Stop here. Before writing code, confirm:

1. Do we start with TIER 1 (fix the core game mechanics)?
2. Or jump to TIER 2 (side bets / Lightning multipliers)?
3. Or TIER 3 (card skins / TCG system)?
4. Or TIER 4 (table lobby)?

Each tier is ~1 week of focused building.
All 4 tiers make the best blackjack game ever built online.
Then we replicate the quality standard across the other 5 games.

The game architecture is now documented. No more guessing.
