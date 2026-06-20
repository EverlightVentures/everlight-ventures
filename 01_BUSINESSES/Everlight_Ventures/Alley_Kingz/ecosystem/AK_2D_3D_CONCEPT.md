# ALLEY KINGZ -- 2D/3D CONCEPT & MULTI-MODE ARCHITECTURE
## AK_2D_3D_CONCEPT.md
### Dual-Scale Reality: Strategic World Map + Tactical Hub Walk + Extraction Combat

---

## 1. THE VISION

Alley Kingz operates on a **dual-scale reality** — one game, two perspectives, seamless transitions. The player never plays "two different games." They play **one game at two scales**:

- **The Macro (Strategic):** World map view — your territory as a board, crew territories visible, raid targets, extraction zones, district nodes. Clash of Clans style.
- **The Micro (Tactical):** Hub walk view — boots on the ground, walking between buildings, chopping trees, talking to NPCs, upgrading structures. Sunflower Land style.
- **The Danger (Extraction):** Combat deployment — overhead tactical, backpack active, loot channeling, risk escalating. DMZ/Tarkov/Hunt: Showdown style.

The camera, UI, controls, and mental model shift contextually. The economy, deck, and progression remain consistent across all modes.

---

## 2. THE THREE MODES

### MODE A: WORLD MAP (Strategic / Zoomed Out)

**Camera:** Top-down, fixed orthographic, slight tilt for depth  
**Render:** Canvas2D, neon urban grid, territory borders glow, base icons pulse with shield status  
**Controls:** Tap-to-select, drag-to-pan, pinch-to-zoom  
**Metaphor:** *The Map* — you are the crew leader looking down at the city

**Visual Language:**
- Your base = 9-tile island icon with Main Tower level badge, shield aura, crew flag
- Crewmates' bases = smaller icons clustered in your territory color (Crowned = gold, Rusted = rust orange, Hologhosts = cyan, Unbound = purple)
- Enemy/rival bases = red-tinted icons with raid timer countdowns
- Contested zones = pulsing red zones with loot tier indicators (Low/Med/High/Extreme)
- District nodes = hexagonal portals, click to zoom in
- Extraction routes = neon dashed lines connecting safe districts to contested zones
- Bus stops / subway stations = green extraction markers

**HUD Elements:**
```
┌─────────────────────────────────────────────────────────────┐
│  [CREW BADGE]  NeonHowl Crew  |  TERRITORY: 12 tiles       │
│  [SHIELD]  8h remaining  |  [REPUTATION]  ████████░░ 84%    │
│                                                             │
│  [MAP]                                                      │
│  ┌─────┐  ┌─────┐  ┌─────┐                                  │
│  │YOUR │  │CREW1│  │CREW2│  [CONTESTED: Scrapyard]          │
│  │BASE │  │BASE │  │BASE │  Risk: HIGH | Loot: Scrap/Wood  │
│  └──┬──┘  └──┬──┘  └──┬──┘  [DEPLOY EXTRACTION RUN]        │
│     │        │        │                                     │
│  ┌──┴──┐  ┌──┴──┐  ┌──┴──┐  [ENEMY: Rival Crew]           │
│  │ZONE1│  │ZONE2│  │ZONE3│  [INITIATE RAID]                │
│  └─────┘  └─────┘  └─────┘                                  │
│                                                             │
│  [DISTRICT LIST]  [CREW CHAT]  [WAR TIMER]  [SETTINGS]     │
└─────────────────────────────────────────────────────────────┘
```

**Interactions:**
- Tap your base → "ZOOM IN" prompt → transitions to Hub Mode
- Tap contested zone → "DEPLOY" prompt → transitions to Extraction Mode
- Tap crewmate base → "VISIT" or "REINFORCE" options
- Tap enemy base → "SCOUT" (free, see layout) or "RAID" (costs energy, initiates async raid)
- Long-press any zone → radial menu: Scout / Deploy / Extract / Mark

---

### MODE B: HUB WALK (Tactical / Zoomed In)

**Camera:** Isometric follow, slight angle (30°), smooth lerp to player  
**Render:** Canvas2D, pixel-art / stylized 2D sprites, neon lighting effects, particle weather  
**Controls:** Virtual joystick (left) + tap-to-interact (right) + pinch-to-zoom (limited range)  
**Metaphor:** *The Street* — you are the dog walking your own territory

**Visual Language:**
- Your base = walkable 9-tile grid (expandable to 16-tile at Main Tower L10+)
- Buildings = physical sprites with collision boxes, upgrade visual states (L1=wooden shack, L5=brick, L10=neon tower)
- Dynamic obstacles = trees (grow stages 0-3), rocks (small/medium/boulder), scrap piles, barricade rubble
- NPCs = Doc Wattson (Infirmary), Switch the Broker (Trading Post), crew members (if online)
- Resource nodes = wood piles, stone rubble, scrap heaps — channel to gather
- Weather/time = day/night cycle affects lighting, stray spawn rate, NPC dialog
- Crew members = visible avatars walking around, collision enabled, proximity chat bubbles

**HUD Elements:**
```
┌─────────────────────────────────────────────────────────────┐
│  [GOLD] 12,450  [GEMS] 340  [SCRAP] 89  [KEYS] 3           │
│  [ENERGY] ████████░░ 8/10  |  [BACKPACK] 6/9 slots         │
│                                                             │
│  [MINIMAP]  ┌───┐                                           │
│             │ ● │  (player dot + building icons)            │
│             └───┘                                           │
│                                                             │
│  [MISSION LOG]  "Clear 3 trees"  "Talk to Doc Wattson"     │
│  [CREW CHAT]  [Tap to open]                                │
│                                                             │
│  [BUILD]  [DECK]  [DRIP]  [CREW]  [MAP/ZOOM OUT]          │
└─────────────────────────────────────────────────────────────┘
```

**Interactions:**
- Walk to building → proximity prompt: "Upgrade (2h, 500 Gold)" or "Manage"
- Walk to tree/rock → equip tool prompt: "Chop (Axe, 3s)" or "Clear (Builder, 10m)"
- Walk to NPC → dialog bubble opens, quest/mission/shop interface
- Walk to crewmate → proximity social: trade, emote, group up for extraction
- Tap ground → pathfind and walk (A* on tile grid)
- Pinch out beyond threshold → "ZOOM OUT" prompt → transitions to World Map

**Dynamic Obstacle System:**
```javascript
// Obstacle spawn rules (per tile, per 24h cycle)
{
  type: 'tree' | 'rock' | 'scrap_pile' | 'barricade_rubble' | 'weed_patch',
  growthStage: 0-3,           // 0 = seed/small, 3 = fully grown (blocks path)
  hp: 50-500,                  // Based on type + stage
  toolRequired: 'axe' | 'pickaxe' | 'crowbar' | 'shears' | null,
  toolDurabilityCost: 1-5,    // Per hit
  channelTime: 2-5,           // Seconds to clear manually
  builderTime: 10-60,         // Minutes if assigned to builder
  lootOnClear: { wood: 3, xp: 5 },  // Immediate backpack add
  respawnTimer: 86400,         // 24h to regrow
  blockPath: true,             // A* collision when stage >= 2
  visualState: [              // Sprite index per stage
    'tree_seed.png',
    'tree_sapling.png',
    'tree_young.png',
    'tree_full.png'
  ]
}
```

**Tool Crafting (Workbench building required):**
| Tool | Cost | Durability | Speed Bonus | Bonus Loot |
|------|------|------------|-------------|------------|
| Rusty Axe | 10 Scrap | 5 uses | 0% | None |
| Standard Axe | 50 Gold + 20 Scrap | 15 uses | +20% | +10% wood |
| Power Axe | 200 Gold + 50 Scrap | 30 uses | +50% | +25% wood, chance for rare wood |
| Jackhammer | 500 Gold + 100 Scrap + 10 Gems | 20 uses | +100% | Insta-clear small rocks |

**Builder Queue (Clash of Clans style):**
```javascript
{
  maxBuilders: MainTowerLevel,  // L1 = 1, L5 = 3, L10 = 5
  activeQueue: [
    { task: 'upgrade_gold_mint', duration: 7200, builder: 1, started: timestamp },
    { task: 'clear_tree_cluster', duration: 600, builder: 2, started: timestamp }
  ],
  idleBuilders: 1,

  // Tasks that consume builders:
  // - Building upgrade (hours)
  // - Wall/barricade construction (minutes)
  // - Bulk obstacle clear (minutes, no tool durability cost)
  // - Expansion project (hours, unlocks new tile)

  // Tasks that DON'T consume builders (player manual):
  // - Single obstacle clear with tool (instant, costs durability)
  // - Barricade repair (instant if materials in backpack)
  // - Decorative placement (instant, no cost)
}
```

---

### MODE C: EXTRACTION RUN (Combat / Danger Zone)

**Camera:** Top-down tactical, slight rotation allowed, zoom locked to player  
**Render:** Canvas2D, tighter FOV, grittier palette, high contrast for threats  
**Controls:** Virtual joystick (left) + aim + shoot/skill buttons (right) + backpack quick-access (top)  
**Metaphor:** *The Hunt* — you are prey and predator in contested territory

**Visual Language:**
- Your avatar = dog sprite with backpack visible (cosmetic skin applied)
- Backpack fill meter = floating bar above avatar, color shifts green→yellow→red
- Movement penalty = avatar animation slows, dust trail shortens
- Loot nodes = glowing crates, scrap piles, stray dens (channeling indicator when looting)
- Other players = red nameplates (rivals), green (crew), yellow (neutral)
- Threat indicators = red arrow at screen edge showing off-screen enemies
- Extraction points = pulsing green beacons, 30s wait timer when activated
- Risk meter = border vignette darkens as risk escalates, heartbeat audio intensifies

**HUD Elements:**
```
┌─────────────────────────────────────────────────────────────┐
│  [HP] ████████░░ 82%  |  [ENERGY] 6/10  |  [DECK] 4 cards   │
│                                                             │
│  [BACKPACK]  ██████░░░ 6/9 slots                            │
│  ┌───┬───┬───┬───┬───┬───┬───┬───┬───┐                     │
│  │ W │ S │ C │ L │ P │ ? │ ? │ ? │ 🔒│  (🔒 = secure slot)│
│  └───┴───┴───┴───┴───┴───┴───┴───┴───┘                     │
│                                                             │
│  [RISK METER]  ████░░░░░  LOW  (time: 4:32, loot: $450)   │
│  [EXTRACTION]  🚌 Bus Stop 120m  |  🏠 Crew Safehouse 300m  │
│                                                             │
│  [MINIMAP]  ┌───┐  [SKILL 1] [SKILL 2] [SKILL 3] [ULTIMATE]│
│             │ ● │                                           │
│             └───┘  [AUTO-AIM] [MANUAL AIM] [DEPLOY CARD]   │
│                                                             │
│  [LOOT CHANNEL]  Rummaging... ██████░░░░ 3.2s remaining    │
│  ⚠️ VULNERABLE — cancel to defend                           │
└─────────────────────────────────────────────────────────────┘
```

**The Extraction Loop:**

```
GEAR UP (Hub Mode)
    │
    ├── Equip backpack (choose tier based on mission risk)
    ├── Load consumables (Repels, Leashes, Potions)
    ├── Select deck (11 cards, always secure)
    ├── Set extraction goal ("Scrapyard for wood/stone" or "Hunt rare strays")
    └── Click contested zone on World Map → DEPLOY
    │
    ▼
ENTER DANGER ZONE (Extraction Mode)
    │
    ├── Backpack HUD appears, fill level empty
    ├── Speed penalty applied based on backpack tier
    ├── Risk meter starts ticking (time + loot value + zone difficulty)
    ├── Extraction points visible on mini-map
    └── Procedural loot nodes spawn, AI strays patrol, rival players may be present
    │
    ├── LOOT: Walk to node → channel 2-5s → backpack fills
    │   ├── Scrap piles (wood/stone/scrap) — low risk, no extraction needed
    │   ├── Abandoned crates (consumables, gold) — medium risk
    │   ├── Stray packs (bones, rare drops) — high risk, combat required
    │   ├── Rival kills (their backpack contents) — very high risk
    │   └── Boss strays (legendary gear, keys) — extreme risk
    │
    ├── COMBAT: Encounter stray or rival → deck deploys (Clash Royale style)
    │   ├── 4-card hand, elixir/energy system
    │   ├── Deploy cards around your avatar (avatar = mobile tower)
    │   ├── Win = loot drops, continue
    │   └── Lose = blackout sequence
    │
    ▼
DECISION POINT: Extract or Push?
    │
    ├── EXTRACT NOW → safe, keep everything, clean extraction bonus
    │   ├── Walk to safe district (slow, guaranteed)
    │   ├── Bus stop (30s wait, vulnerable, fast)
    │   ├── Crew safehouse (instant if controlled, may be contested)
    │   └── Emergency extract (consumable, anywhere, costs Gems)
    │
    └── PUSH DEEPER → more loot, higher risk, risk meter climbs faster
        └── Loop back to LOOT/COMBAT
    │
    ▼
DEATH (If you lose combat and can't extract)
    │
    ├── Screen shakes, red vignette
    ├── "YOU GOT JACKED!" comic-book splash (graffiti font)
    ├── Blackout (1s fade to black, dog yelp + glass shatter)
    ├── Wake in Infirmary (Hub Mode, auto-transition)
    ├── Backpack DROPPED at death location, marked on map
    ├── Secure container contents KEPT
    ├── Deck KEPT (always secure)
    └── 24h countdown to retrieve bag before despawn/loot
```

**The "YOU GOT JACKED" Death Sequence:**

```
1. FIGHT LOST
   [Screen shakes violently, red vignette pulses]
   [Sound: dog yelp, glass shatter, distant sirens]

   ┌─────────────────────────────┐
   │                             │
   │    YOU GOT JACKED!          │
   │    [graffiti splash font]   │
   │                             │
   │    [comic-book burst BG]    │
   │                             │
   └─────────────────────────────┘

2. BLACKOUT (1 second)
   [Screen fades to black]
   [Sound: heartbeat slows, fades]

3. INFIRMARY WAKE-UP (Hub Mode auto-loads)
   [Fade in: lying on cot, ceiling fan spinning]
   [Doc Wattson leans into frame]

   Doc: "Took a beating out there, mutt."
   Doc: "You're patched up, but... your bag's still in the streets."
   Doc: "24 hours. Clock's ticking."

   [Map opens automatically]
   [Red X with backpack icon, 24:00:00 countdown]

   CHOICES:
   ├─ "I'm going back for it" → World Map → death location
   ├─ "Call crew for backup" → Sends crew notification + reward promise
   ├─ "Pay The Fixer (50 Gems)" → Bag returned to stash in 1 hour
   └─ "Forget it, I'll re-gear" → Close dialog, back to hub
```

---

## 3. THE TRANSITION SYSTEM

### Transition Matrix

| From | To | Trigger | Transition Visual | Duration | Audio Cue |
|------|-----|---------|-------------------|----------|-----------|
| **Hub** | **World Map** | Tap "ZOOM OUT" button or pinch out beyond threshold | Camera pulls up and back, buildings shrink to icons, grid lines fade in, territory borders glow | 1.2s | Synth bass drop + vinyl scratch + city ambience fades |
| **World Map** | **Hub** | Tap your base icon, select "ENTER" | Camera dives down, icon expands to buildings, grid lines fade out, collision activates, NPCs spawn | 1.2s | Bass rise + street ambience fades in + distant dog barks |
| **World Map** | **Extraction** | Tap contested zone, select "DEPLOY" | Screen "glitches" with neon static, camera snaps to overhead tactical, HUD switches to combat mode, backpack appears on avatar | 0.8s | Siren wail + heartbeat starts + radio chatter |
| **Extraction** | **Hub** (success) | Reach extraction point, complete 30s timer | Extraction point "whoosh" effect, backpack contents fly to stash in comic-book motion lines, camera transitions to hub zoom, victory confetti | 1.5s | Victory brass + cash register + crew cheers |
| **Extraction** | **Hub** (death) | HP reaches 0, no extraction | Red flash, "YOU GOT JACKED" splash, fade to black, fade in to Infirmary cot, Doc Wattson dialog auto-opens | 2.0s | Dog yelp + glass shatter + Doc Wattson sigh |
| **Hub** | **Extraction** (retrieval) | Tap death marker on World Map, select "RETRIEVE" | Same as World Map → Extraction, but death marker is waypoint | 0.8s | Tense bass + ticking clock |

### Transition State Machine

```javascript
const GAME_MODE = {
  HUB: 'hub',
  WORLD_MAP: 'world_map',
  EXTRACTION: 'extraction',
  INFIRMARY: 'infirmary',
  COMBAT: 'combat',        // Sub-mode within extraction
  DIALOG: 'dialog',        // Sub-mode within hub
  BUILD: 'build',          // Sub-mode within hub
};

const MODE_TRANSITIONS = {
  [GAME_MODE.HUB]: {
    allowed: [GAME_MODE.WORLD_MAP, GAME_MODE.EXTRACTION, GAME_MODE.DIALOG, GAME_MODE.BUILD],
    exitAnimation: 'zoom_out',
    enterAnimation: 'zoom_in',
    statePreservation: 'full',  // Hub state persists
  },
  [GAME_MODE.WORLD_MAP]: {
    allowed: [GAME_MODE.HUB, GAME_MODE.EXTRACTION, GAME_MODE.INFIRMARY],
    exitAnimation: 'dive_in',
    enterAnimation: 'pull_back',
    statePreservation: 'full',
  },
  [GAME_MODE.EXTRACTION]: {
    allowed: [GAME_MODE.HUB, GAME_MODE.INFIRMARY, GAME_MODE.COMBAT],
    exitAnimation: 'extract_success',
    enterAnimation: 'deploy_glitch',
    statePreservation: 'backpack_only',  // Only backpack state transfers
  },
  [GAME_MODE.INFIRMARY]: {
    allowed: [GAME_MODE.HUB, GAME_MODE.WORLD_MAP],
    exitAnimation: 'stand_up',
    enterAnimation: 'wake_up',
    statePreservation: 'none',  // Fresh state after death
  },
};

// Transition guard checks
function canTransition(from, to, playerState) {
  if (!MODE_TRANSITIONS[from].allowed.includes(to)) return false;

  // Special guards
  if (from === GAME_MODE.HUB && to === GAME_MODE.EXTRACTION) {
    return playerState.energy >= 1 && playerState.backpack !== null;
  }
  if (from === GAME_MODE.EXTRACTION && to === GAME_MODE.HUB) {
    return playerState.extractionComplete || playerState.deathFlag;
  }
  if (from === GAME_MODE.WORLD_MAP && to === GAME_MODE.EXTRACTION) {
    return playerState.selectedZone !== null && playerState.energy >= 1;
  }

  return true;
}
```

---

## 4. THE BACKPACK SYSTEM (Cross-Mode Integration)

### Backpack Data Structure

```javascript
const BACKPACK_TIERS = {
  STARTER: {
    id: 'starter',
    name: 'The Runt',
    slots: 4,
    secureSlots: 0,
    speedPenalty: 0,
    cost: { gold: 0 },
    skin: 'tattered_canvas',
    description: 'A tattered canvas satchel. Better than nothing.'
  },
  SMALL: {
    id: 'small',
    name: 'The Scrounger',
    slots: 6,
    secureSlots: 1,
    speedPenalty: -0.05,
    cost: { gold: 500 },
    skin: 'leather_messenger',
    description: 'Leather messenger bag. One secure pocket.'
  },
  MEDIUM: {
    id: 'medium',
    name: 'The Hauler',
    slots: 9,
    secureSlots: 2,
    speedPenalty: -0.10,
    cost: { gold: 2000 },
    skin: 'tactical_street',
    description: 'Tactical street pack. Room for the big scores.'
  },
  LARGE: {
    id: 'large',
    name: 'The Mule',
    slots: 12,
    secureSlots: 3,
    speedPenalty: -0.15,
    cost: { gold: 5000, gems: 50 },
    skin: 'reinforced_duffel',
    description: 'Reinforced duffel. Heavy, but it hauls.'
  },
  EXTRA_LARGE: {
    id: 'extra_large',
    name: 'The Kingpin',
    slots: 16,
    secureSlots: 4,
    speedPenalty: -0.20,
    cost: { gold: 15000, gems: 150 },
    skin: 'neon_tactical_rig',
    description: 'Neon-trimmed tactical rig. The boss moves slow but carries everything.'
  },
  EVENT_GHOST: {
    id: 'event_ghost',
    name: 'The Ghost',
    slots: 14,
    secureSlots: 6,
    speedPenalty: -0.05,
    cost: { event: 'hologhost_invasion' },
    skin: 'hologhost_camo',
    description: 'Hologhost faction camo. Light, secure, invisible to scans.'
  },
  LEGENDARY_CROWN: {
    id: 'legendary_crown',
    name: 'The Crown Jewel',
    slots: 18,
    secureSlots: 5,
    speedPenalty: -0.10,
    cost: { pass_tier: 30 },
    skin: 'crowned_royal',
    description: 'Crowned faction royal pack. Fit for a king.'
  }
};

// Player backpack instance
const playerBackpack = {
  tier: 'medium',
  slots: [],           // Array of item objects, max length = tier.slots
  secureSlots: [],     // Subset of slots that are loss-proof
  skin: 'custom_neon_howl',  // Cosmetic override
  contents: {
    // Slot 0: { type: 'material', id: 'wood', quantity: 12, stackSize: 50 }
    // Slot 1: { type: 'consumable', id: 'leash_rare', quantity: 1 }
    // Slot 2: { type: 'valuable', id: 'stray_bone_legendary', quantity: 1 }
    // ... etc
  },
  totalValue: 0,       // Computed, affects risk meter
  weight: 0,           // Computed, affects speed penalty

  // Methods
  addItem(item) { /* find stack or empty slot, return success/fail */ },
  removeItem(slotIndex) { /* return item, shift array */ },
  moveToSecure(slotIndex) { /* if secureSlots available */ },
  computeStats() { /* recalculate value, weight, penalty */ }
};
```

### Backpack Per-Mode Behavior

| Mode | Backpack State | Visibility | Interaction |
|------|---------------|------------|-------------|
| **Hub** | Stowed in base | Icon in UI only, not on avatar | Manage contents, sort, discard, move to secure slots, craft/upgrade at Workbench |
| **World Map** | Equipped (selected for deployment) | Small icon on base avatar | View contents summary, change tier before deploy, check secure slots |
| **Extraction** | Active, on avatar | Visible sprite with fill meter, movement penalty applied | Loot adds to slots, secure slots protected, drop on death, retrieve on success |
| **Infirmary** | Dropped (death) or Empty (success) | Map marker (death) or stash summary | Retrieve (death), manage stash (success) |

### Secure Container Strategy

```javascript
// Secure slots are NEVER lost on death
// They force hard decisions:

// Strategy A: Protect the single most valuable item
secureSlots: [ { type: 'valuable', id: 'legendary_gear', value: 5000 } ]

// Strategy B: Spread across multiple lower-value items
secureSlots: [
  { type: 'material', id: 'rare_scrap', quantity: 5, value: 500 },
  { type: 'consumable', id: 'emergency_extract', value: 300 },
  { type: 'material', id: 'event_token', quantity: 2, value: 400 }
]

// The deck (11 cards) is ALWAYS secure — never in backpack, never lost
// It's your "equipped gear" like DMZ's Normal mode
```

---

## 5. THE MATERIAL ECONOMY (Fortress Layer)

### Resource Types & Sources

| Material | Found In | Used For | Backpack Stack | Hub Spawn |
|----------|----------|----------|----------------|-----------|
| **Wood** | Broken fences, construction sites, tree clearing | Walls, barricades, building upgrades, tool crafting | 10 units/slot | Trees (growth stages) |
| **Stone** | Rubble piles, old foundations, rock clearing | Reinforced walls, towers, advanced buildings | 5 units/slot | Rocks (small/medium/boulder) |
| **Scrap** | Junkyards, abandoned cars, scrap piles | Crafting, Card Forge, tool repair | 20 units/slot | Scrap piles (static + dynamic) |
| **Metal** | Rare nodes, boss drops, advanced mining | Advanced buildings, gear, legendary tools | 5 units/slot | Rare nodes (contested zones only) |
| **Food/Kibble** | Markets, stray dens, hunting | Heal troops, breeding, NPC gifts | 10 units/slot | Stray dens (hub + extraction) |
| **Consumables** | Shops, drops, crafting | Repels, Leashes, Potions, Emergency Extracts | 1 unit/slot (unstackable) | Shop purchase + rare drops |

### Gathering Mechanics

**In Hub (Sunflower Land style):**
- Walk to resource node → proximity prompt → channel 2-5 seconds
- Tool equipped = faster channel, bonus loot, no durability cost in hub
- Builder assigned = auto-gather over time, no player action needed
- Resources go directly to stash (not backpack — hub is safe zone)

**In Extraction (DMZ style):**
- Walk to loot node → channel 2-5 seconds → VULNERABLE during channel
- No tools needed (scavenging, not harvesting)
- Resources go to backpack (risky — lose on death)
- Other players see "looting" indicator above your head
- Can cancel channel but lose progress

### Building Integration (Clash of Clans + Sunflower Land)

```javascript
// Building costs include materials
const BUILDING_UPGRADES = {
  main_tower: {
    2: { gold: 500, wood: 50, stone: 20, time: 300 },
    3: { gold: 2000, wood: 200, stone: 100, metal: 10, time: 1800 },
    4: { gold: 5000, wood: 500, stone: 300, metal: 50, time: 3600 },
    // ... etc
  },
  gold_mint: {
    2: { gold: 300, wood: 30, time: 180 },
    3: { gold: 1000, wood: 100, stone: 50, time: 600 },
  },
  wall_segment: {
    build: { wood: 10, time: 30 },
    reinforce: { stone: 5, wood: 5, time: 60 },
    upgrade: { metal: 2, stone: 10, time: 300 }
  }
};

// Barricade placement (strategic layout)
const BARRICADE = {
  hp: 200,           // Wood barricade
  hpReinforced: 500, // Stone reinforced
  hpAdvanced: 1200,    // Metal reinforced
  buildCost: { wood: 15 },
  reinforceCost: { stone: 10, wood: 5 },
  upgradeCost: { metal: 5, stone: 15 },
  placement: 'grid_aligned',  // Snap to tile grid
  maxPerTile: 1,
  blocksPath: true,
  visionBlock: true,  // Enemies can't see/shoot through

  // Visual states
  states: ['wood_planks', 'wood_reinforced', 'stone_reinforced', 'metal_fortified'],
  damageStates: [1.0, 0.75, 0.5, 0.25, 0.0]  // 100%, 75%, 50%, 25%, destroyed
};
```

---

## 6. THE INFIRMARY SYSTEM

### Building: Infirmary

**Unlock:** Main Tower L3  
**Function:** Respawn point, heal hub, insurance broker, troop recruitment  
**NPC:** Doc Wattson (permanent resident, dialog-driven)

### Features by Level

| Level | Unlock | Feature | Effect |
|-------|--------|---------|--------|
| 1 | Main Tower L3 | Basic respawn | Full HP on death, 30s respawn timer, no backpack |
| 2 | 500 Gold + 50 Wood | Alley Watch insurance | Bag stays 48h instead of 24h, 100 Gold/run |
| 3 | 1500 Gold + 150 Wood + 50 Stone | Heal timer reduction | Dog heal time -25% (was 5-30m, now 3.75-22.5m) |
| 4 | 3000 Gold + 300 Wood + 100 Stone | Crew Guard insurance | Bag hidden from other players, 250 Gold/run |
| 5 | 5000 Gold + 500 Wood + 200 Stone + 20 Metal | Fast respawn | Respawn timer 15s (was 30s) |
| 6 | 8000 Gold + 50 Gems | The Fixer's Promise | Bag returned to stash after 1h, 50 Gems/run |
| 7 | 12000 Gold + 100 Gems | Mass heal | Heal all dogs simultaneously |
| 8 | 20000 Gold + 200 Gems + VIP Pass | Iron Collar | Bag instantly returned on death, 200 Gems/run |

### Doc Wattson Dialog System

```javascript
const DOC_WATSON_DIALOG = {
  // Triggered on Infirmary wake-up (death)
  wakeUp: {
    lines: [
      "Took a beating out there, mutt.",
      "You're patched up, but... your bag's still in the streets.",
      "24 hours. Clock's ticking.",
      "Want me to call The Fixer? Costs extra, but your bag comes back clean."
    ],
    choices: [
      { text: "I'm going back for it", action: 'open_map_death_marker' },
      { text: "Call crew for backup", action: 'send_crew_rescue_request' },
      { text: "Pay The Fixer (50 Gems)", action: 'insurance_claim', cost: { gems: 50 }, req: 'infirmary_l6' },
      { text: "Forget it, I'll re-gear", action: 'close_dialog' }
    ]
  },

  // Triggered on Infirmary visit (not death)
  visit: {
    lines: [
      "Back again? You dogs are gluttons for punishment.",
      "Need a patch-up? Or just here to chat?"
    ],
    choices: [
      { text: "Heal my dogs", action: 'heal_dogs', cost: 'variable' },
      { text: "Buy insurance", action: 'insurance_menu' },
      { text: "Recruit new dog", action: 'recruit_menu', req: 'infirmary_l4' },
      { text: "Upgrade Infirmary", action: 'upgrade_building' },
      { text: "Just visiting", action: 'close_dialog' }
    ]
  },

  // Random idle lines (when walking past)
  idle: [
    "Watch your step, the floor's still wet.",
    "Another one bites the dust, eh?",
    "I've seen worse. Not much worse, but worse.",
    "Your crew's been asking about you."
  ]
};
```

---

## 7. SOCIAL SYSTEMS (Option B: MMO Hub)

### Crew Presence in Hub

**Architecture:** Hub instances are **crew-shared** — when you enter your hub, you see other online crew members who are also in their hub (yours is the "crew headquarters" hub). This is NOT individual instances per player.

```javascript
const HUB_INSTANCE = {
  crewId: 'neon_howl_42',
  maxPlayers: 20,  // Crew size cap
  currentPlayers: ['player_1', 'player_2', 'player_5'],

  // Sync priorities (bandwidth optimization)
  sync: {
    position: 10,      // Hz — player positions
    state: 2,          // Hz — animation state, interaction state
    building: 0.1,     // Hz — building upgrades (rare, batch)
    obstacle: 0.05,    // Hz — obstacle changes (very rare, batch)
    chat: 'event',     // Event-driven — only when message sent
  },

  // Proximity features
  proximityChat: true,       // Chat only visible within 200px
  proximityEmote: true,      // Emotes visible globally in hub
  proximityTrade: true,      // Trade request within 100px
  proximityHelp: true,       // "Help clear this tree" requests within 150px
};
```

### Crew Member Interactions

| Action | Range | Effect | Cooldown |
|--------|-------|--------|----------|
| **Wave/Emote** | Global | Cosmetic, no effect | None |
| **Chat** | 200px proximity | Text bubble above head | None |
| **Trade** | 100px | Exchange items (both must confirm) | 60s between trades |
| **Help Clear** | 150px | Both channel obstacle, 2x speed, split loot | 5m per obstacle |
| **Group Up** | 100px | Form squad for extraction (shared deck pool) | None |
| **Reinforce** | 200px | Buff nearby crew member's buildings (temporary) | 10m per building |
| **Heal** | 100px | Doc Wattson can heal crew dogs (if Infirmary L5+) | 5m per dog |

### Crew Bag Retrieval (Social Extraction)

```javascript
// When a crewmate dies and their bag drops:
const CREW_RESCUE = {
  // Death notification sent to all online crew
  notification: {
    type: 'crew_bag_down',
    player: 'player_3',
    location: { x: 1200, y: 3400, zone: 'scrapyard' },
    lootValue: 4500,
    timeRemaining: 86400,  // 24h
    reward: { gold: 500, reputation: 50 }  // For rescuer
  },

  // Rescue mechanics
  rescue: {
    minSquadSize: 2,       // Must group up to attempt
    maxSquadSize: 5,
    riskMultiplier: 1.5,   // Zone difficulty increases for rescue runs
    rewardSplit: 'equal',  // All rescuers get full reward
    bagReturn: 'owner',    // Bag goes to original owner, rescuers get bonus
    betrayal: 'possible',  // Rescuer can choose to steal bag instead
  }
};
```

### Betrayal Log

```javascript
const BETRAYAL_LOG = {
  // Tracks social violations within crew
  entries: [
    {
      timestamp: 1718900000,
      type: 'abandoned_reinforcement',
      player: 'player_7',
      target: 'player_3',
      details: 'Promised reinforcements for raid, never sent',
      consequence: 'reputation -10, flagged in crew chat'
    },
    {
      timestamp: 1718903600,
      type: 'stole_bag',
      player: 'player_2',
      target: 'player_5',
      details: 'Retrieved crewmate bag but kept contents',
      consequence: 'reputation -50, "Thief" title for 48h, open to crew vengeance'
    },
    {
      timestamp: 1718907200,
      type: 'left_during_war',
      player: 'player_9',
      target: 'crew',
      details: 'Offline during DvD siege phase',
      consequence: 'reputation -25, "Deserter" mark for 24h'
    }
  ],

  // Consequences escalate
  reputationThresholds: {
    100: 'Trusted',      // Can assign crew roles
    50: 'Member',        // Standard
    0: 'Suspect',        // Restricted from war participation
    -50: 'Pariah',       // Can be kicked by vote, open season
    -100: 'Exiled'       // Auto-kicked, bounty placed
  }
};
```

---

## 8. EVENTBUS INTEGRATION

### New Events for Multi-Mode System

```javascript
// MODE TRANSITIONS
'game.mode.enter' { mode, from, transitionDuration }
'game.mode.exit' { mode, to, transitionDuration }
'game.mode.ready' { mode }  // Transition complete, input enabled

// WORLD MAP
'worldmap.base.select' { baseId, isOwn, isCrew, isEnemy }
'worldmap.zone.select' { zoneId, riskLevel, lootTypes }
'worldmap.deploy.start' { zoneId, backpackTier, squad }
'worldmap.raid.initiate' { targetBaseId, energyCost }
'worldmap.reinforce.send' { targetBaseId, troops }

// HUB WALK
'hub.player.move' { x, y, velocity }
'hub.player.interact' { targetType, targetId, action }
'hub.obstacle.clear.start' { obstacleId, tool, channelTime }
'hub.obstacle.clear.complete' { obstacleId, loot }
'hub.obstacle.clear.cancel' { obstacleId, progress }
'hub.building.upgrade.start' { buildingId, duration, builder }
'hub.building.upgrade.complete' { buildingId, newLevel }
'hub.npc.dialog.open' { npcId, dialogKey }
'hub.npc.dialog.choice' { npcId, choiceIndex, action }
'hub.crewmember.join' { playerId, position }
'hub.crewmember.leave' { playerId }
'hub.crewmember.proximity' { playerId, distance, action }

// EXTRACTION
'extraction.deploy' { zoneId, backpack, deck, squad }
'extraction.loot.channel.start' { source, duration, slotIndex }
'extraction.loot.channel.complete' { source, item, slotIndex }
'extraction.loot.channel.interrupt' { source, reason, progress }
'extraction.combat.start' { opponentType, opponentId }
'extraction.combat.end' { result, loot, damageTaken }
'extraction.extract.start' { pointId, waitTime }
'extraction.extract.complete' { success, lootValue, timeInZone }
'extraction.extract.cancel' { reason }

// DEATH & RETRIEVAL
'death.player' { location, backpackDropped, secureKept, insuranceTier, killer }
'death.retrieval.start' { location, timeRemaining, bagContents }
'death.retrieval.complete' { success, itemsRecovered, retriever }
'death.retrieval.expired' { location, itemsLost }
'death.retrieval.stolen' { thief, itemsStolen }
'infirmary.respawn' { healAmount, timeSpent, insuranceClaimed }
'infirmary.heal.complete' { dogId, healAmount, timeSaved }

// BACKPACK
'backpack.equipped' { tier, slots, secureSlots, skin }
'backpack.loot.added' { item, slot, source, value }
'backpack.loot.removed' { item, slot, reason }
'backpack.full' { tier, slotsUsed, slotsMax }
'backpack.secure.used' { slot, item }
'backpack.upgrade' { fromTier, toTier, cost }
'backpack.skin.change' { skin }

// INSURANCE
'insurance.purchase' { tier, cost, runId }
'insurance.claim' { tier, bagContents, returnTime }
'insurance.expire' { runId, reason }

// MATERIALS
'material.gather' { type, quantity, source, mode }
'material.craft' { recipe, inputs, outputs }
'material.build' { building, materials, result }
```

---

## 9. SENSOR PACKAGES (Per-Entity)

### Player Avatar (Hub Mode)

```javascript
{
  // GAMEPLAY SENSORS
  detectR: 0,        // Player doesn't auto-detect (manual interaction)
  visionR: 200,      // Can see/interact within 200px
  strikeR: 0,        // No combat in hub
  sepR: 30,          // Minimum spacing from other players (collision)
  aoeR: 0,

  // HUB-SPECIFIC
  interactionRange: 80,      // Proximity prompt distance
  buildRange: 120,           // Can place buildings within 120px of self
  toolEquipped: 'axe',      // Current tool
  toolDurability: 12,        // Remaining uses

  // INSTRUMENTATION
  events: ['hub.player.move', 'hub.player.interact', 'hub.obstacle.clear.*'],
  metrics: { 
    avgSessionLength: 0, 
    obstaclesCleared: 0, 
    buildingsUpgraded: 0,
    crewInteractions: 0 
  },
  perf: { updateHz: 60 }  // Full 60Hz for responsive movement
}
```

### Player Avatar (Extraction Mode)

```javascript
{
  // GAMEPLAY SENSORS
  detectR: 150,      // Detection radius (sees threats)
  visionR: 400,      // Vision radius (can target)
  strikeR: 60,       // Attack/deploy radius
  sepR: 40,          // Separation from allies
  aoeR: 0,           // Personal AOE (from cards)

  // EXTRACTION-SPECIFIC
  backpack: {
    tier: 'medium',
    slotsUsed: 6,
    slotsMax: 9,
    secureSlots: 2,
    totalValue: 4500,
    weight: 0.65,     // 0-1, affects speed
    speedPenalty: -0.10
  },
  riskLevel: 0.4,    // 0-1, computed from time + value + zone
  extractionPoints: [
    { id: 'bus_stop_1', distance: 120, status: 'available' },
    { id: 'crew_safehouse', distance: 300, status: 'contested' }
  ],

  // INSTRUMENTATION
  events: ['extraction.*', 'death.player', 'combat.*'],
  metrics: { 
    avgLootValue: 0, 
    extractionRate: 0, 
    deathRate: 0, 
    retrievalRate: 0,
    avgTimeInZone: 0 
  },
  perf: { updateHz: 60 }
}
```

### Dropped Backpack (World Entity)

```javascript
{
  // GAMEPLAY SENSORS
  detectR: 0,
  visionR: 0,
  strikeR: 0,
  sepR: 40,          // Minimum spacing between dropped bags
  aoeR: 0,

  // BACKPACK-SPECIFIC
  ownerId: 'player_3',
  contents: [ /* item array */ ],
  totalValue: 4500,  // Attracts predators/rivals
  secureSlots: [],     // Already stripped (secure goes to owner stash)
  timeRemaining: 72000,  // 20h left
  insuranceTier: 'crew_guard',  // Affects visibility
  hidden: true,        // Crew Guard = hidden from non-crew

  // INSTRUMENTATION
  events: ['backpack.dropped', 'backpack.retrieved', 'backpack.stolen', 'backpack.expired'],
  metrics: { 
    timeOnGround: 0, 
    retrievalAttempts: 0, 
    theftAttempts: 0 
  },
  perf: { updateHz: 1 }  // Low-frequency, just countdown
}
```

### Dynamic Obstacle (Tree)

```javascript
{
  // GAMEPLAY SENSORS
  detectR: 0,
  visionR: 0,
  strikeR: 0,
  sepR: 60,          // Minimum spacing from other obstacles
  aoeR: 0,

  // OBSTACLE-SPECIFIC
  type: 'tree',
  growthStage: 3,    // Full grown, blocks path
  hp: 300,
  maxHp: 300,
  toolRequired: 'axe',
  toolDurabilityCost: 3,
  channelTime: 4,    // Seconds to clear manually
  builderTime: 600,  // 10 minutes if assigned
  lootOnClear: { wood: 8, xp: 15 },
  respawnTimer: 86400,
  blockPath: true,

  // INSTRUMENTATION
  events: ['obstacle.spawn', 'obstacle.clear.start', 'obstacle.clear.complete', 'obstacle.respawn'],
  metrics: { 
    timesCleared: 0, 
    avgClearTime: 0, 
    totalWoodProduced: 0 
  },
  perf: { updateHz: 0.1 }  // Very low, only growth check
}
```

---

## 10. BUILD SEQUENCE (Revised Priority)

### SPRINT 1: THE ZOOM (Week 1-2)

**Goal:** Establish dual-mode foundation — Hub walk + World Map overlay

1. **World Map overlay** in `hub_proto.html`
   - Add "ZOOM OUT" button to hub HUD
   - Render strategic view: base icon, territory borders, district nodes
   - Camera transition: pull back (1.2s, lerp)
   - Base icon shows: Main Tower level, shield status, crew badge

2. **Base icon click → "ENTER" → zoom in**
   - Camera transition: dive down (1.2s, lerp)
   - Hub state restores: player position, NPCs, buildings

3. **Dynamic obstacles in hub**
   - Add tree/rock spawn system to tile grid
   - Growth stages (0-3) with visual progression
   - Collision when stage >= 2
   - 24h respawn timer

4. **Tool system (basic)**
   - Rusty Axe + Pickaxe craftable at Workbench (if built)
   - Equip tool → proximity prompt on obstacle → channel → clear
   - Tool durability (5-15 uses)
   - Loot to stash (hub is safe)

5. **Builder queue (basic)**
   - 1 builder at Main Tower L1
   - Assign builder to clear obstacle (10-60m)
   - No tool durability cost for builder clears

### SPRINT 2: THE BACKPACK (Week 3-4)

**Goal:** Core extraction loop — backpack, loot, death, retrieval

6. **Backpack data structure**
   - Tier system (Starter → Kingpin)
   - Slots + secure slots
   - Skin system (cosmetic)
   - HUD overlay (fill meter, secure indicators)

7. **Loot channeling**
   - 2-5s channel on loot nodes
   - Vulnerable during channel (can be attacked)
   - Cancelable but lose progress
   - "Looting" indicator visible to others

8. **Death → drop → wake flow**
   - Combat death triggers blackout sequence
   - "YOU GOT JACKED" splash
   - Infirmary wake-up (auto-transition to Hub)
   - Doc Wattson dialog (auto-open)
   - Map marker with 24h countdown

9. **Bag retrieval**
   - Tap death marker on World Map → "RETRIEVE"
   - Deploy to extraction mode at death location
   - 2s channel to pick up bag
   - Return to hub, contents restored

10. **Secure container**
    - 1-2 slots on starter backpacks
    - NEVER lost on death
    - Force strategic decisions

### SPRINT 3: THE DANGER (Week 5-6)

**Goal:** Extraction run prototype — procedural zones, AI threats, extraction points

11. **Extraction run prototype**
    - Procedural loot node placement
    - AI stray patrols (symbol encounters, avoidable)
    - Risk meter (time + value + zone)
    - Extraction points: bus stop (30s wait), safehouse (crew-controlled)

12. **Combat in extraction**
    - Deck deploys (same 4-card hand, energy system)
    - Avatar = mobile tower, deploy cards around self
    - Win = continue, lose = death sequence

13. **Material economy**
    - Wood/stone/scrap nodes in extraction zones
    - Stack sizes by backpack tier
    - Return to hub → materials to stash → use for building

14. **Barricade building**
    - Place walls with wood/stone (snap to grid)
    - Strategic layout matters for defense
    - Visual damage states

### SPRINT 4: THE SOCIAL (Week 7-8)

**Goal:** Crew presence, shared hub, betrayal mechanics

15. **Crew-shared hub instance**
    - Online crew members visible in hub
    - Position sync (10Hz), state sync (2Hz)
    - Proximity chat, trade, help clear

16. **Crew bag retrieval**
    - Death notification to crew
    - Group up for rescue run
    - Reward for rescuer, bag returned to owner

17. **Betrayal log**
    - Track abandoned reinforcements, bag theft, desertion
    - Reputation consequences
    - Crew vote to kick

18. **Insurance tiers**
    - Infirmary L2-L8 unlocks
    - Alley Watch → Iron Collar
    - Gold/Gems cost per run

### SPRINT 5: POLISH (Week 9-10)

19. **Transition polish**
    - All 5 transition animations (zoom out, dive in, deploy glitch, extract success, death wake)
    - Audio cues for each
    - Loading state management

20. **Shop integration**
    - Backpack tiers in The Drop (Gold/Gems)
    - Backpack skins in The Garage (cosmetic)
    - Insurance consumables

21. **EventBus wiring**
    - All new events implemented
    - Telemetry pipeline for balancing metrics

22. **Performance optimization**
    - Hub: 60Hz for responsive movement
    - World Map: 30Hz (no physics)
    - Extraction: 60Hz for combat
    - Sync: Prioritized by distance and relevance

---

## 11. CRYPTO GUARDRAILS

| System | Currency | ALK/Token Eligible? | Notes |
|--------|----------|---------------------|-------|
| Backpack tiers | Gold/Gems | NO | Soft currency only, gameplay progression |
| Backpack skins | Gems (cosmetic) | YES (future) | Cosmetic only, never functional advantage |
| Insurance | Gold/Gems | NO | Convenience purchase, never power |
| Loot items | Soft currency only | NO | Never tradable for ALK/BCARDD |
| Secure slots | Gameplay progression | NO | Never gem-buyable beyond tier provision |
| Tool crafting | Gold/Scrap | NO | Core gameplay loop |
| Building upgrades | Gold + materials | NO | Time-gated, builder-queue limited |
| Barricades | Wood/Stone/Metal | NO | Strategic layout, no pay-to-win |
| Death retrieval | Time + risk | NO | 24h window is equal for all |
| Crew rescue | Reputation + reward | NO | Social mechanic, not monetized |

**Parity Invariant (HARD LAW):**  
Gems may ONLY skip timers (insurance return speed, builder speed-ups) or buy cosmetics (backpack skins, avatar drip). Gems NEVER raise slot caps, secure slot counts, loot quality, or building levels. Card Forge + Research Lab feed combat power, so timer-skip-only keeps it not-pay-to-win.

---

## 12. THE OPERATOR'S VISION (Verbatim Integration)

From AK_GAME_VISION.md:

> "You have to build your card collection, manage it, upgrade it... get gold like Clash Royale... once the collection is leveled enough you level up your Town Hall. Everybody has the same resources -- what makes it unique is the player decides which skins, how their map is set up, their card levels. When it's time to fight it's like Brawl Stars, but the map is whoever's getting attacked -- everyone zooms in, mini-map like the Clash of Clans attack, structure troops, drop cards around your teammates' map. Battle maps adapt in real-time to each individual's territory. Every clan has a territory, every territory has members, every member has a radius, the union is the clan area. One person attacked -> the clan helps. Wild Pokemon a.k.a. dog breeds; outside the zone at night like Whiteout/Dark War, zombie mutant dogs attack, need your clan. Macro, micro, mini, personal strategy -- all from the base of this game."

This architecture delivers exactly that:
- **Macro:** World Map — territories, crew areas, raid planning, extraction routes
- **Micro:** Hub Walk — building placement, resource gathering, social interaction, daily life
- **Mini:** Extraction Run — combat, loot, risk, death, retrieval
- **Personal:** Deck building, card levels, backpack loadout, strategic decisions

The zoom transitions make the "macro, micro, mini" feel seamless — not three games, but one game with three lenses.

---

*Document version: 2026-06-20*  
*Companion to: AK_GAME_VISION.md, AK_SYSTEMS_DESIGN.md, AK_HUB_INTERACTION_ROAMING_COMBAT_SPEC.md, AK_MASTER_GAME_DESIGN_SYNTHESIS.md, AK_RAID_DEFENSE_SYSTEM.md*  
*Author: Alley Kingz Design Team*  
*Status: READY FOR IMPLEMENTATION*
