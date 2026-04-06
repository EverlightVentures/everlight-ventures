# Alley Kingz -- Product Requirements Document v2.0
Updated: 2026-02-28 | Hive Mind Session: 89059981

---

## Executive Summary

Alley Kingz is a real-time card battler set in a GTA-style urban world where players deploy street vehicles and crew members to destroy the opponent's HQ Van. It targets the same core loop as Clash Royale but owns an entirely different niche: urban car-battle culture nobody has claimed.

**Competitive target**: Match Clash Royale quality. Differentiate on theme, niche, and street culture brand.
**MVP definition**: 100-level PvE ladder + ranked PvP + deck builder + shop + social login + cloud save.

---

## 1. Core Game Loop

```
Login -> Daily Rewards -> Pick Deck -> Battle ->
Post-match (NOS Bottles +/-) -> Chest Unlock -> Upgrade Cards -> Repeat
```

### 1.1 Battle Rules
- 3 min match (2 min regular + 1 min double elixir)
- Sudden death overtime if tied after double elixir
- **Win condition**: Destroy opponent HQ Van (King Tower analog) OR score more tower kills at time
- **GAME OVER trigger**: YOUR HQ Van loses all HP -> battle ends immediately as LOSS
- 3 Crown (3-tower wipe) = maximum trophies/NOS Bottle bonus

### 1.2 HQ Van Rule (NEW -- Critical Path)
- HQ Van = King Tower. HP: 2800 base.
- If HQ Van reaches 0 HP -> **GAME OVER** screen triggers. Not just a crown -- battle ends.
- Animation: Van explosion with smoke plume, siren sound, "YOUR CREW IS DOWN" message.
- This applies to player AND opponent -- first HQ Van destroyed ends the match instantly.

---

## 2. Card System

### 2.1 Card Types (Visual Differentiation)
| Type | Border Color | Badge | Visual |
|------|-------------|-------|--------|
| **Troop** | Chrome Silver (#C0C0C0) | CREW badge | Unit art, stat bars (HP/DMG/SPD) |
| **Spell** | Flame Gold (#FFD700) | SPELL badge | Effect art, blast radius indicator |
| **Building** | Neon Teal (#00FFD4) | STRUCTURE badge | Structure art, DPS/HP |

### 2.2 Card Data Fields
Every card has:
- id, name, description, lore (flavor text)
- cardType: Troop | Spell | Building
- cardClass: Street | Cartel | Tech | Lowrider | Muscle | Ghost | Rookie
- synergies: Array of synergy tags (e.g., ["speed_stack","gang_rush"])
- traits: Array (e.g., ["flying","armored","splash","building_target"])
- elixirCost: 1-10
- rarity: Common | Rare | Epic | Legendary | Icon (new top tier)
- stats: hp, dmg, speed, range, atkSpd (troops/buildings)
- unlockLevel: 1-100 (level required to unlock)
- upgradeMultiplier: 1.10 default, varies by rarity

### 2.3 Card Classes (for deck organization)
| Class | Flavor | Color |
|-------|--------|-------|
| **Street** | Everyday brawlers, backbone of any deck | Orange |
| **Cartel** | High value, high cost, high impact | Red |
| **Tech** | Electronic and gadget-based attacks | Cyan |
| **Lowrider** | Slow but unstoppable tanks | Pink |
| **Muscle** | Brute force and raw damage | Gold |
| **Ghost** | Stealth, evasion, flankers | Purple |
| **Rookie** | Starter cards, low cost, swarm | Green |

### 2.4 Card Synergies (for deck building UI)
| Tag | Description |
|-----|-------------|
| speed_stack | Units that chain movement speed buffs |
| gang_rush | Multi-unit deploy combos |
| splash_squad | AoE damage synergy group |
| tank_line | Tanks that shield behind each other |
| spell_cycle | Low-cost spell cycling deck |
| ghost_flanks | Flanking route exploiters |
| chopped_up | Chop Shop created cards synergy |

### 2.5 Card Count (200+ Target)
Current: 12 | Target v1.0: 48 | Target v2.0: 120+ | Max: 200+

#### Full 48-Card Roster (v1.0)

**Troops -- Street Class (8)**
1. Muscle Car (cost:3, Common) -- RAM ability
2. Lowrider (cost:3, Common) -- heavy tank
3. Street Bike Duo (cost:3, Common) -- fast flankers
4. Drive-By Van (cost:4, Rare) -- long range spray
5. Hooptie (cost:2, Common) -- cheap swarm unit, pair
6. Chopper (cost:5, Rare) -- airborne, targets troops
7. Graffiti Crew (cost:3, Common) -- 3 units, ranged
8. Street Preacher (cost:4, Rare) -- heals nearby allies

**Troops -- Muscle Class (6)**
9. GTR (cost:4, Rare) -- NITRO speed burst
10. Pickup Truck (cost:5, Epic) -- building-target tank
11. Impala Cruiser (cost:4, Rare) -- balanced brawler
12. The Battering Ram (cost:6, Epic) -- breaks through guards
13. Bone Crusher (cost:5, Epic) -- area melee
14. Drag Racer (cost:4, Legendary) -- fastest, glass cannon [LOCKED L25]

**Troops -- Cartel Class (6)**
15. Monster Truck (cost:7, Epic) -- area crush [LOCKED L15]
16. Armored SUV (cost:5, Rare) -- spell shield [LOCKED L20]
17. Kingpin (cost:6, Legendary) -- buffs adjacent troops [LOCKED L30]
18. Sicario Crew (cost:4, Rare) -- targeted assassins
19. El Jefe (cost:8, Legendary) -- mega tank + area + aura [LOCKED L50]
20. Black Cadillac (cost:5, Epic) -- summons two guards at death [LOCKED L35]

**Troops -- Tech Class (4)**
21. Drone Squad (cost:4, Rare) -- air unit, rains missiles [LOCKED L18]
22. Tesla Roadster (cost:5, Epic) -- chain lightning attack [LOCKED L22]
23. Bot Patrol (cost:3, Rare) -- mini robot trio [LOCKED L12]
24. Jammer Van (cost:4, Rare) -- slows all enemies in range [LOCKED L28]

**Troops -- Ghost Class (4)**
25. Ghost Rider (cost:3, Epic) -- invisible for 3s on deploy [LOCKED L40]
26. Shadowrun Bikes (cost:4, Rare) -- flanks from sides [LOCKED L16]
27. Hood Ninja (cost:3, Rare) -- teleports on attack
28. Smoke Screen Car (cost:4, Epic) -- deploy smoke, bypass defenses [LOCKED L45]

**Troops -- Rookie Class (4)**
29. Corner Boys (cost:2, Common) -- 4 cheap units
30. Prospect (cost:1, Common) -- single weak unit, fast cycle
31. Tuner (cost:2, Common) -- weak but quick mechanic unit
32. Dice Rollers (cost:3, Common) -- random ability on deploy

**Buildings -- Structure (4)**
33. Trap Car (cost:2, Rare) -- explosive on trigger
34. Chop Shop (cost:4, Epic) -- generates a random unit every 20s [LOCKED L10]
35. Hydrant (cost:2, Common) -- area slow, splashes water
36. Graffiti Wall (cost:3, Rare) -- blocks path, absorbs damage [LOCKED L8]

**Spells -- Tech (5)**
37. EMP (cost:3, Common) -- wide energy blast
38. NOS Bomb (cost:4, Rare) -- speed-up allies in radius
39. Oil Slick (cost:2, Common) -- slow + DoT
40. Cyber Hack (cost:4, Epic) -- temporarily disables enemy building [LOCKED L20]
41. Sonic Boom (cost:5, Rare) -- pushes all enemies backward [LOCKED L35]

**Spells -- Street (5)**
42. Molotov (cost:4, Common) -- area fire damage
43. Drive-By Shot (cost:2, Common) -- targeted single dmg
44. Smoke Signal (cost:1, Common) -- stuns 1 unit briefly
45. Riot Burst (cost:5, Rare) -- area + ongoing burn [LOCKED L25]
46. Spike Strip (cost:3, Rare) -- deploys trap strip [LOCKED L15]

**Iconic Cards (2 -- Ultra Rare)**
47. The OG (cost:8, Icon) -- legendary OG crew boss with giant aura [LOCKED L75]
48. Phantom Ride (cost:7, Icon) -- self-propelled ghost car, phases through units [LOCKED L80]

---

## 3. Level System (100 Levels)

### 3.1 Difficulty Scaling Algorithm
```
level_scale = 1 + (level - 1) * 0.065 + (level / 100)^2 * 0.5

enemy_hp_mult    = level_scale
enemy_dmg_mult   = 1 + (level - 1) * 0.05
enemy_ai_delay   = max(0.5, 2.5 - (level * 0.02))
enemy_elixir_iq  = min(0.95, 0.3 + (level * 0.0065))
```

| Range | Label | Characteristics |
|-------|-------|----------------|
| 1-10 | **Rookie** | Slow AI, basic decks, no abilities |
| 11-25 | **Street Kid** | Abilities active, mixed deck, moderate speed |
| 26-50 | **Grinder** | Full deck variation, ability chaining |
| 51-75 | **Hustler** | Smart targeting, counter decks, combos |
| 76-95 | **Kingpin** | Near-optimal AI, hard counters, fast plays |
| 96-100 | **Legend** | Expert AI, top meta decks, no mercy |

### 3.2 Hunger Games Unlock Logic
- Completing a level ALWAYS grants XP + chest
- Cards unlock at specific levels (see roster above)
- **Hunger Games gates**: Every 10 levels, a "District Challenge" must be won to proceed
  - Lose the district challenge -> lose cards from your active deck for that zone
  - Win -> earn the zone's Legendary card reward
- Completing Level 50 unlocks "Ranked" mode permanently
- Completing Level 100 unlocks "Icon" card tier access

### 3.3 Level Select UI
- Map view: Street grid from "Training Block" (1) to "Empire Tower" (100)
- Zones: 10 levels per zone (10 zones total)
- Zone icons: car culture themed (Junkyard -> Strip -> Freeway -> Downtown -> etc.)
- Locked zones greyed out with zone boss preview card shown

---

## 4. Trophy System -> NOS Bottle Ladder

### 4.1 NOS Bottles Replace "Trophies"
- Trophy count renamed to **NOS Bottles** everywhere
- Icon: NOS canister (orange/blue)
- Gain NOS on win, lose NOS on loss
- NOS floor at arena thresholds (can't fall below floor)

### 4.2 Ladder Arenas (Alley Kings Themed)
| Arena | NOS Bottles | Zone Name |
|-------|------------|-----------|
| The Lot | 0 | Starting area, rusted cars |
| Strip Run | 400 | Neon-lit drag strip |
| Parking Structure | 800 | Multi-deck urban brawl |
| The Blocks | 1200 | Hood residential |
| Interchange | 1600 | Freeway overpass |
| The Yard | 2000 | Industrial salvage yard |
| Neon District | 2600 | Downtown nightlife |
| Embassy Row | 3200 | High-end zone |
| The Penthouse | 4400 | Corporate tower tops |
| Empire State | 5000+ | Elite bracket, league play |

### 4.3 Leagues (5000+ NOS Bottles)
Bronze Crew -> Silver Crew -> Gold Crew -> Platinum Crew -> Diamond Crew -> The Council -> Alley King

---

## 5. Economy & Currencies

### 5.1 Three-Currency System
| Currency | Name | Source | Sink |
|----------|------|--------|------|
| **Fuel** (soft) | In-game gold analog | Wins, dailies, chests | Card upgrades, shop offers |
| **Gears** (mid) | Season currency | Season pass, events | Premium cards, exclusive skins |
| **Gems** (hard/IAP) | Premium currency | Real money, rare rewards | Chest skips, pass, shop |

### 5.2 Monetization Stack
1. **Crew Pass** $9.99 / 35 days -- premium reward track, exclusive card
2. **Gem packs** -- $0.99-$99.99, standard IAP
3. **Revival Pack** $2.99 -- triggered at 5-loss streak (highest uplift driver)
4. **Starter Pack** $4.99 -- gems + Fuel + Legendary chest (one-time)
5. **Chop Shop speedup** -- merge two duplicate cards, random new card emerges
6. **Cosmetics only shop** -- car skins, arena themes, emotes
7. **Event passes** -- limited-time event access ($3.99)

### 5.3 F2P Guardrails (retention protection)
- All cards earnable via play (no pay-to-win)
- Cosmetics = paid exclusive only
- No energy system / stamina gates on PvP
- Daily free chest always available
- NOS floor prevents total ladder collapse

---

## 6. Deck Builder System

### 6.1 Filter/Sort Options
- **By Class**: Street | Cartel | Tech | Lowrider | Muscle | Ghost | Rookie
- **By Synergy**: speed_stack | gang_rush | splash_squad | tank_line | spell_cycle | ghost_flanks
- **By Traits**: flying | armored | splash | building_target | stealth | ranged | healer
- **By Elixir**: 1-3 (cheap) | 4-5 (mid) | 6-8 (heavy) | 8+ (win con)
- **By Rarity**: Common | Rare | Epic | Legendary | Icon
- **Sort by**: Elixir (default) | Name | Level | Class

### 6.2 Deck Stats Panel
- Average elixir cost (live calculation)
- Synergy meter (how well cards combo)
- Role coverage: Tank % / DPS % / Support % / Spell %
- Troop/Spell/Building ratio
- Win condition highlight (highest cost/damage card)

### 6.3 Deck Slots
- 5 deck slots default
- 8 slots with Crew Pass

---

## 7. Social & Auth

### 7.1 Login Options
- Google Play Games (Android)
- Apple Game Center / Sign in with Apple (iOS)
- Facebook Login (web/app)
- Guest mode (local only, warning on unlink)
- Email/password fallback

### 7.2 Cloud Save (PlayFab / UGS)
- Full profile sync on every session end
- Conflict resolution: higher NOS bottle count wins
- Cross-device support (phone to tablet)
- Clan/friend systems (Phase 3)

---

## 8. Audio System

### 8.1 SFX Events (per action, distinct sounds)
| Event | Sound |
|-------|-------|
| Card deploy (troop) | Engine rev / tire squeal |
| Card deploy (spell) | Whoosh + impact |
| Unit attack | Car engine burst / weapon fire |
| Unit takes damage | Metal crunch / screech |
| Unit death | Explosion + crash |
| Tower damaged | Deep thud + structural creak |
| Tower destroyed | Full explosion + distant sirens |
| **HQ Van destroyed** | MASSIVE explosion + wail |
| Elixir fill ding | NOS tank pressurize sound |
| Victory | Car horns + crowd cheer |
| Defeat | Sad engine stall |
| Menu click | Gear shift click |

### 8.2 Music
- Battle: Low BPM hip-hop with build tension toward double elixir
- Double elixir: Beat drops, higher intensity
- Overtime: Maximum intensity, bass-heavy
- Menu: Chill lo-fi with street ambience

---

## 9. Visual Direction

### 9.1 Card Visuals (Pokemon/Garage Stat Card Vibes)
- **Troop cards**: Chrome silver border, stat bars at bottom (HP bar, DMG bar, SPD bar), unit art in center, CREW badge top-left, rarity gemstone top-right
- **Spell cards**: Gold/flame border, blast radius indicator, effect art, SPELL badge, damage number prominent
- **Building cards**: Teal border, structure art, DPS + HP display
- **Rarity glow**: Common=none, Rare=subtle blue shine, Epic=purple pulse, Legendary=gold shimmer, Icon=rainbow holo

### 9.2 Visual Polish
- Particle effects: deploy spawns light burst, deaths spawn metal sparks
- Hit effects: screen shake on heavy hits
- Elixir bar: liquid NOS animation, bubbles
- HQ Van health bar: red glow when under 30%
- Arena: Animated street elements (traffic lights, graffiti tags flickering)

### 9.3 UI Style
- Dark backgrounds: #0A0A0F (near-black)
- Accent: Orange #FF6B00, Teal #00FFD4, Chrome #C0C0C0
- Typography: Bold, condensed, urban (Bebas Neue or similar)
- Speedometer motifs on loading screens and stat dials

---

## 10. Technical Architecture

### 10.1 Tech Stack
- **Engine**: Unity 6 LTS (2026 recommended)
- **Backend**: PlayFab (auth, economy, cloud save, leaderboards)
- **Auth**: Unity Gaming Services (Google, Apple, Facebook)
- **Analytics**: Unity Analytics + Firebase
- **Audio**: FMOD Studio (event-driven SFX and music)
- **UI**: UI Toolkit with DOTween animations
- **Cards**: ScriptableObject architecture
- **Assets**: Addressables for 200+ card asset management

### 10.2 Repo Structure
```
Assets/
  Scripts/
    Core/         # PlayerData, InputHandler, Auth
    Battle/       # BattleSystem, UnitBehaviour, HQVanManager
    Cards/        # CardDefinition, DeckBuilder, CardCatalog
    Progression/  # LevelManager, UnlockSystem, ProgressionTracker
    Economy/      # EconomyManager, ShopSystem, ChestSystem
    Audio/        # AudioEventBus, SFXManager, MusicManager
    UI/           # All UI controllers
    Services/     # PlayFabService, AuthService, CloudSave
    Managers/     # GameManager, SceneManager
  Data/
    Cards/        # ScriptableObject assets (48 -> 200)
    Levels/       # Level config assets
    Economy/      # Shop offer configs
```

### 10.3 Phase Plan
| Phase | Features | Target |
|-------|---------|--------|
| **Alpha** | HQ Van death, 10 levels, spell/troop outlines, NOS ladder | Week 4 |
| **Beta** | 48 cards, deck builder, shop, basic social auth | Week 8 |
| **v1.0** | 100 levels, full auth, cloud save, 2 arenas | Week 16 |
| **v1.5** | 120 cards, 2v2 mode, Chop Shop, live ops | Month 6 |
| **v2.0** | 200 cards, clans, ranked seasons, full marketplace | Month 12 |

---

## 11. KPIs & Success Metrics
- **D1 retention**: >40% (industry: 35%)
- **D7 retention**: >20% (industry: 15%)
- **D30 retention**: >10%
- **ARPDAU**: $0.10 (target $0.21 at Clash Royale parity)
- **Payer conversion**: >3% within 30 days
- **Session length**: 12-18 min average
- **Battles/day**: 8-12 per active user

---

## 12. Legal + Differentiation
- **DO NOT** copy Clash Royale assets, code, or UI layouts
- **DO** replicate genre mechanics (elixir regen, 3-tower format) -- these are genre conventions, not IP
- All card names, art, world-building = original urban street culture theme
- "NOS Bottles" / "Crew Pass" / "Chop Shop" = our brand terms
- Card class taxonomy is original
- Arena names are original (not Clash Royale arenas)
