# ALLEY KINGZ: COMPREHENSIVE DEEP-DIVE SYNTHESIS
## 3D Depth + Video Integration + Mission/Faction Karma + Unified Economy + Solana Crypto
### Prepared for: Alley Kingz Development Team
### Date: 2026-06-20
### Status: READY FOR IMPLEMENTATION

---

## TABLE OF CONTENTS

1. The 3D Depth Problem — CSS 3D Transforms + Extruded Photos
2. Video / MP4 Integration — Cinematic Loops
3. Mission System + Faction Karma — Friendly Encounters
4. Unified Economy — The Sunflower Land Model
5. Town Hall + Base Building — Personal Fortress
6. Solana Crypto Integration — $KINGZ Token
7. Build Sequence — Priority Order
8. Tech Stack Recommendation

---

## PART 1: THE 3D DEPTH PROBLEM

### The Core Issue
The game is photo-heavy, creating a "one-plane" flat feel. Photos have width and height but no depth. Even with parallax, they feel like sliding cards. Need VOLUME — the illusion of thickness and 3D space.

### Solution: CSS 3D Transforms + Layered Depth Maps (NOT Full WebGL)

**Why NOT Three.js/Babylon.js:**
- Three.js (~168kB) requires rebuilding entire rendering pipeline; manual scene/camera/material management
- Babylon.js (~1.4MB) is opinionated; fights existing Canvas2D photo stack
- Both require converting photos to 3D meshes — overkill, breaks art pipeline

**The RIGHT Approach: CSS 3D Transforms + "Extruded Photo" Technique**

This is what Brawl Stars and modern portfolio sites use. Pure CSS + minimal JS gives photos fake depth without changing the art pipeline.

**How It Works:**
1. Take photo
2. Create 3 layers: FRONT (main image), SIDE (squeezed edge), BOTTOM (squeezed edge)
3. Use `transform: perspective(800px) rotateY(15deg)` on container
4. Use `transform-style: preserve-3d` to keep children in 3D space
5. Position side/bottom layers with `translateZ` and `rotateX/Y` for thickness illusion

### Production-Ready CSS

```css
/* CONTAINER — sets the 3D camera */
.scene {
  perspective: 1000px;
  perspective-origin: 50% 50%;
}

/* THE EXTRUDED PHOTO WRAPPER */
.extruded-photo {
  position: relative;
  width: 300px;
  height: 400px;
  transform-style: preserve-3d;
  transform: rotateY(-15deg) rotateX(5deg);
  transition: transform 0.6s ease;
}

/* MAIN FACE — your actual photo */
.extruded-photo .face {
  position: absolute;
  width: 100%;
  height: 100%;
  background: url('your-photo.jpg') center/cover;
  transform: translateZ(12px);
  border-radius: 8px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.4);
}

/* RIGHT SIDE — extruded edge (darkened, squeezed) */
.extruded-photo .side-right {
  position: absolute;
  right: 0;
  top: 0;
  width: 24px;
  height: 100%;
  background: linear-gradient(to left, rgba(0,0,0,0.6), rgba(0,0,0,0.3));
  transform: rotateY(90deg) translateZ(12px);
  transform-origin: right center;
  filter: brightness(0.7);
}

/* BOTTOM — extruded edge */
.extruded-photo .bottom {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 24px;
  background: linear-gradient(to top, rgba(0,0,0,0.5), rgba(0,0,0,0.2));
  transform: rotateX(90deg) translateZ(12px);
  transform-origin: bottom center;
  filter: brightness(0.6);
}

/* HOVER: the photo "turns" to face you */
.extruded-photo:hover {
  transform: rotateY(0deg) rotateX(0deg) scale(1.05);
}
```

**Result:** Photos look like physical objects with thickness — trading cards on a table. Hover turns them to face you. Scroll tilts based on mouse position. The "Brawl Stars 2.5D" look.

**For District Map:**
- Each district card gets extruded treatment
- Hover = "lift" (translateZ + scale + shadow expansion)
- Select = rotate to face full-on while others recede
- Background map uses `perspective: 2000px` with subtle `rotateX(10deg)` for "tabletop" feel

**Performance:** Pure CSS, zero JS per frame, GPU-accelerated, mobile-friendly. `transform-style: preserve-3d` ensures single compositing layer.

---

## PART 2: VIDEO / MP4 INTEGRATION

### The Problem
Photos are static. Need LIFE — subtle motion making the world feel breathing.

### Solution: Cinematic Loops (NOT Full Videos)

Full MP4s are heavy, kill battery, don't loop seamlessly. Best approach: 3-5 second MP4s that loop perfectly.

**Use Cases:**
1. Background atmosphere (subtle, desaturated, no focus)
2. NPC idle states (dog breathing, tail wagging)
3. Weather effects (rain on glass, neon flicker)
4. Transition moments (zooming into district, "glitch" effect)

### Cinematic Loop Manager

```javascript
class CinematicLoop {
  constructor() {
    this.loops = new Map();
    this.activeLoops = new Set();
    this.budget = 3; // Max 3 videos playing at once
  }

  register(id, src, options = {}) {
    const video = document.createElement('video');
    video.src = src;
    video.loop = true;
    video.muted = true; // CRITICAL: muted = no autoplay restrictions
    video.playsInline = true; // iOS requirement
    video.preload = 'metadata';
    video.style.cssText = `
      position: absolute;
      width: 100%;
      height: 100%;
      object-fit: cover;
      opacity: ${options.opacity || 0.3};
      mix-blend-mode: ${options.blend || 'overlay'};
      pointer-events: none;
      z-index: ${options.zIndex || 0};
    `;

    this.loops.set(id, { video, options, priority: options.priority || 0 });
    return video;
  }

  play(id) {
    const loop = this.loops.get(id);
    if (!loop) return;
    if (this.activeLoops.size >= this.budget) {
      const lowest = [...this.activeLoops]
        .map(id => ({ id, priority: this.loops.get(id).priority }))
        .sort((a, b) => a.priority - b.priority)[0];
      this.pause(lowest.id);
    }
    loop.video.play().catch(e => console.log('Loop play failed:', e));
    this.activeLoops.add(id);
  }

  pause(id) {
    const loop = this.loops.get(id);
    if (loop) {
      loop.video.pause();
      this.activeLoops.delete(id);
    }
  }
}
```

**Key Rules:**
- Always muted — browsers block autoplay with sound
- Max 3 concurrent — more kills mobile performance
- Short loops (3-5s) — longer = bigger files, harder to loop
- Low opacity (0.1-0.3) — atmosphere, not focus
- Use `mix-blend-mode: overlay/screen/multiply` — blends into photo art naturally

**Where to Use in Alley Kingz:**
1. Hub buildings — subtle loops (smoke from chimneys, neon signs flickering)
2. District map — weather loops per district (rain in Slums, dust in Scrapyard, fog in Hologhost zone)
3. Combat transitions — "glitch" deploy effect is 0.8s video loop of neon static
4. NPCs — Doc Wattson breathing loop, Scratch tail-wag loop

**Art Pipeline:** Generate with AI video tools (Runway, Pika, Leonardo motion) from existing static art. Export 720p MP4, 3 seconds, H.264, ~500KB each.

---

## PART 3: MISSION SYSTEM + FACTION KARMA

### The Vision
Wild encounters are purely hostile. Need FRIENDLY encounters where players gain Karma by helping NPCs, doing missions, building reputation. Dual-track: Combat Reputation (fighting) + Social Karma (helping).

### Best-in-Class Reference: GTA V District System + Sunflower Land Reputation

District-specific reputation + mission tiers unlocking based on standing. Sunflower Land's $SFL token maintained stability through constant demand from crafting/upgrades.

### Karma System

```javascript
const KARMA_SYSTEM = {
  districts: {
    neon_howl: { name: 'Neon Howl', faction: 'crowned', baseKarma: 0 },
    scrapyard: { name: 'The Scrapyard', faction: 'rusted', baseKarma: 0 },
    ghost_district: { name: 'Ghost District', faction: 'hologhosts', baseKarma: 0 },
    unbound_zone: { name: 'Unbound Zone', faction: 'unbound', baseKarma: 0 },
    central_plaza: { name: 'Central Plaza', faction: 'neutral', baseKarma: 50 }
  },

  tiers: [
    { name: 'Stranger', min: -100, max: -1, color: '#ff4444', icon: '❌' },
    { name: 'New Face', min: 0, max: 49, color: '#888888', icon: '😐' },
    { name: 'Known', min: 50, max: 149, color: '#44ff88', icon: '👋' },
    { name: 'Trusted', min: 150, max: 299, color: '#44aaff', icon: '🤝' },
    { name: 'Respected', min: 300, max: 499, color: '#aa44ff', icon: '⭐' },
    { name: 'Revered', min: 500, max: 999, color: '#ffaa00', icon: '👑' },
    { name: 'Legend', min: 1000, max: Infinity, color: '#ff0066', icon: '💎' }
  ],

  missions: {
    tier0: [ // Stranger/New Face
      { type: 'delivery', name: 'Package Run', desc: 'Deliver supplies to safehouse', reward: { karma: 10, gold: 50, scrap: 5 } },
      { type: 'clear', name: 'Alley Cleanup', desc: 'Clear 3 obstacles', reward: { karma: 15, gold: 30, wood: 8 } },
      { type: 'escort', name: 'Pup Escort', desc: 'Walk lost pup to Kennel', reward: { karma: 20, gold: 40, bones: 2 } }
    ],
    tier1: [ // Known
      { type: 'faction', name: 'Tag Territory', desc: 'Spray faction graffiti on 5 walls', reward: { karma: 25, gold: 80, rep: 15 } },
      { type: 'defend', name: 'Guard Post', desc: 'Patrol district border 5 min', reward: { karma: 30, gold: 60, keys: 1 } },
      { type: 'gather', name: 'Resource Run', desc: 'Collect 20 scrap from contested zone', reward: { karma: 20, gold: 100, scrap: 20 } }
    ],
    tier2: [ // Trusted
      { type: 'story', name: "The Broker's Secret", desc: 'Help Scratch find missing shipment', reward: { karma: 50, gold: 200, gems: 5 } },
      { type: 'rescue', name: 'Crew Extraction', desc: 'Rescue crewmate dropped bag', reward: { karma: 40, gold: 150, rep: 30 } },
      { type: 'diplomacy', name: 'Peace Talks', desc: 'Mediate between rival factions', reward: { karma: 60, gold: 180, rep: 25 } }
    ],
    tier3: [ // Respected+
      { type: 'epic', name: 'District Defense', desc: 'Lead defense against night horde', reward: { karma: 100, gold: 500, gems: 20 } },
      { type: 'legend', name: 'The Heist', desc: 'Plan and execute major extraction', reward: { karma: 150, gold: 1000, legendaryKey: 1 } }
    ]
  }
};
```

### Karma Gating

```javascript
function getAvailableContent(districtId, playerKarma) {
  const tier = getKarmaTier(playerKarma);
  return {
    missions: KARMA_SYSTEM.missions[`tier${Math.min(tier.index, 3)}`],
    shopDiscount: tier.index * 0.05, // 0% to 30%
    dialogOptions: tier.index >= 2 ? ['ask_about_secrets', 'request_favor'] : [],
    buildings: {
      infirmary: true,
      trading_post: tier.index >= 1,
      black_market: tier.index >= 3,
      faction_hq: tier.index >= 4,
      legendary_vault: tier.index >= 6
    },
    perks: {
      free_heal: tier.index >= 2,
      fast_travel: tier.index >= 4,
      crew_bonus: tier.index >= 5,
      exclusive_skin: tier.index >= 6
    }
  };
}
```

### Friendly Encounter Table

```
KARMA < 0 (Hostile):
  70% Hostile stray, 20% Rival crew, 10% Nothing

KARMA 0-49 (Neutral):
  40% Hostile, 30% Friendly NPC, 20% Resource node, 10% Nothing

KARMA 50-149 (Known):
  25% Hostile, 40% Friendly NPC, 25% Resource, 10% Special

KARMA 150+ (Trusted+):
  15% Hostile, 45% Friendly NPC, 25% Resource, 15% Special
```

**Friendly NPC Types:**
- Lost Pup — escort to Kennel for Karma + Bones
- Injured Stray — heal at Infirmary for Karma + Gold
- Merchant Caravan — trade (better rates) for Karma + Scrap
- Faction Recruiter — join faction mission for Karma + Rep
- Mysterious Stranger — starts story chain for Karma + Gems

**Special Encounters (Karma 150+ only):**
- The Fixer — rare, high-risk/high-reward mission
- Legendary Stray — capture without combat
- Crew Distress Call — rescue mission, massive Karma + crew rep

---

## PART 4: UNIFIED ECONOMY

### The Problem
Currencies: Gold, Gems, Scrap, Keys, Bones, Cards, Wood, Stone, Metal, Food, Consumables, Reputation, Karma. Not talking to each other. Players hoard one while starving for another. Creates friction, not fun.

### Solution: Sunflower Land Model — Unified Sink Web

Every currency needs a SINK — a place it MUST be spent, creating constant demand. Sunflower Land's $SFL survived because it was required for seeds, upgrades, crafting, trading.

### Economy Web

```
GOLD (Soft)
├─ SOURCE: Matches, production buildings, missions, selling items
├─ SINK: Card upgrades, building upgrades, shop purchases, repairs
└─ CONVERTS TO: Scrap (Trading Post), Gems (rare exchange events)

GEMS (Hard)
├─ SOURCE: IAP, events, pass rewards, rare drops
├─ SINK: Time skips, cosmetics, convenience, insurance
└─ CONVERTS TO: Nothing directly (premium only)
   HARD RULE: Gems NEVER buy power. Only time/cosmetics/convenience.

SCRAP (Craft)
├─ SOURCE: Dupes, Chop Shop, missions, extraction loot
├─ SINK: Card Forge, gear crafting, tool crafting, barricades
└─ CONVERTS TO: Cards (Card Forge), Gold (selling crafted items)

KEYS (Convenience)
├─ SOURCE: Match loot, diamond crates, mission rewards
├─ SINK: Opening crates, fast-travel, skipping wait timers
└─ CONVERTS TO: Crate contents (cards, gold, scrap, consumables)

BONES (Soulbound)
├─ SOURCE: Post-match, quests, breeding, high-karma missions
├─ SINK: Skill trees, per-card tune, breeding costs, commander upgrades
└─ CONVERTS TO: Nothing (soulbound = never tradable, never sellable)

WOOD / STONE / METAL (Materials)
├─ SOURCE: Hub gathering, extraction loot, missions, barricade salvage
├─ SINK: Building upgrades, wall/barricade construction, tool crafting
└─ CONVERTS TO: Gold (selling excess), Scrap (Chop Shop)

REPUTATION (Crew)
├─ SOURCE: Crew wars, helping crewmates, betrayal log positive actions
├─ SINK: Crew roles, territory expansion, crew shop purchases
└─ CONVERTS TO: Nothing (social currency only)

KARMA (District)
├─ SOURCE: Friendly encounters, missions, helping NPCs
├─ SINK: Mission unlocks, shop discounts, building access, perks
└─ CONVERTS TO: Reputation (at high tiers, karma converts to crew rep)

CONSUMABLES (Items)
├─ SOURCE: Crafting, shops, mission rewards, extraction loot
├─ SINK: Used in combat/extraction (Repels, Leashes, Potions, Extracts)
└─ CONVERTS TO: Nothing (one-time use)
```

### Economic Synergy Loop

Every action touches multiple currencies:

```
EXAMPLE: Player Does a Mission
─────────────────────────────────
1. Accept "Alley Cleanup" mission → Costs: 1 Energy
2. Clear 3 trees → Gains: 15 Karma, 30 Gold, 8 Wood
3. Wood to stash → Use for: Building upgrades OR Barricades OR Sell for Gold
4. Gold from mission + wood sale → Use for: Card upgrade OR Shop OR Save for TH
5. Karma increases → Unlocks: Next tier missions, shop discount, new NPC dialog
6. Higher karma = better missions → Better missions = more Gold + rare drops
7. Scrap + Bones → Card Forge + Skill Tree → Stronger cards → Better combat
8. Loop repeats with MORE options, not just MORE numbers
```

### Burn Mechanisms (Anti-Inflation)

| Currency | Burn Mechanism | Rate |
|----------|---------------|------|
| Gold | Card upgrades (increasing cost), building repairs | ~60% of income |
| Scrap | Card Forge (random outcomes, can fail), tool durability | ~70% of income |
| Keys | Opening crates (consumed per use) | 100% of income |
| Bones | Skill tree nodes (permanent, irreversible) | 100% of income |
| Wood/Stone | Building upgrades, barricades (destroyed in raids) | ~50% of income |
| Karma | Nothing (accumulates, tiers get exponentially harder) | 0% — prestige resets |

---

## PART 5: TOWN HALL + BASE BUILDING

### Vision
Every player has a 9-tile personal island. Buildings snap to grid. Walls/barricades around perimeter. Layout matters for defense (raids attack actual layout). Clash of Clans layer.

### Grid System

```javascript
const BASE_GRID = {
  size: 9, // 3x3, expandable to 16 at TH L10+, 25 at TH L15+
  tiles: [
    { x: 0, y: 0, building: 'main_tower', level: 3 },
    { x: 1, y: 0, building: 'gold_mint', level: 2 },
    { x: 2, y: 0, building: null },
    { x: 0, y: 1, building: 'card_forge', level: 1 },
    { x: 1, y: 1, building: 'wall_north', level: 1 },
    { x: 2, y: 1, building: null },
    { x: 0, y: 2, building: 'infirmary', level: 2 },
    { x: 1, y: 2, building: 'wall_west', level: 1 },
    { x: 2, y: 2, building: null }
  ],
  barricades: [
    { edge: 'north', x: 0, y: 0, type: 'wood', hp: 200 },
    { edge: 'north', x: 1, y: 0, type: 'wood', hp: 200 },
    { edge: 'west', x: 0, y: 1, type: 'stone', hp: 500 }
  ]
};
```

### Building Types & Costs

| Building | Unlock | Cost (L1→L2→L3) | Function |
|----------|--------|-------------------|----------|
| Main Tower | Start | — | Caps everything, crew size, card level |
| Gold Mint | TH L2 | 300G+30W / 1000G+100W+50S | Generates Gold offline |
| Gem Mine | TH L3 | 500G+50W / 2000G+200W+100S | Generates Gems (slow) |
| Card Forge | TH L2 | 400G+40W / 1500G+150W+75S | Craft cards from Scrap |
| Research Lab | TH L4 | 800G+80W+20S | Skill tree research |
| Generator | TH L3 | 600G+60W+30S | Reduces upgrade timers |
| Infirmary | TH L3 | 500G+50W | Heal, respawn, insurance |
| The Kennel | TH L5 | 2000G+200W+100S+20M | Breed dogs |
| Trading Post | TH L4 | 1000G+100W+50S | Trade, barter, auction |
| Trophy Hall | TH L6 | 5000G+500W+200S | Display achievements |
| Workshop | TH L5 | 1500G+150W+75S | Craft tools, gear |
| Barracks | TH L7 | 3000G+300W+150S+50M | Train troops for defense |
| Wall Segment | TH L2 | 10W each | Blocks path, absorbs damage |

### Town Hall Gating (Clash of Clans DNA)

```javascript
const TOWN_HALL_GATES = {
  1: { maxCardLevel: 3, maxCrewSize: 5, maxBuilders: 1, gridSize: 9 },
  2: { maxCardLevel: 5, maxCrewSize: 8, maxBuilders: 2, gridSize: 9 },
  3: { maxCardLevel: 7, maxCrewSize: 12, maxBuilders: 2, gridSize: 9 },
  4: { maxCardLevel: 9, maxCrewSize: 15, maxBuilders: 3, gridSize: 12 },
  5: { maxCardLevel: 11, maxCrewSize: 20, maxBuilders: 3, gridSize: 12 },
  6: { maxCardLevel: 13, maxCrewSize: 25, maxBuilders: 4, gridSize: 12 },
  7: { maxCardLevel: 14, maxCrewSize: 30, maxBuilders: 4, gridSize: 16 },
  8: { maxCardLevel: 15, maxCrewSize: 40, maxBuilders: 5, gridSize: 16 },
  9: { maxCardLevel: 16, maxCrewSize: 50, maxBuilders: 5, gridSize: 16 },
  10: { maxCardLevel: 18, maxCrewSize: 75, maxBuilders: 6, gridSize: 25 }
};

// To upgrade Town Hall:
// 1. All production buildings at max level for current TH
// 2. Card collection average level >= TH level * 2
// 3. Gold cost (escalating)
// 4. Time (escalating, reducible with Gems)
```

### Wall/Barricade System

```javascript
const BARRICADES = {
  wood: {
    hp: 200, buildCost: { wood: 10 }, repairCost: { wood: 5 },
    buildTime: 30, blocksPath: true, visionBlock: false,
    damageStates: ['fresh', 'cracked', 'broken', 'destroyed']
  },
  stone: {
    hp: 500, buildCost: { wood: 5, stone: 10 }, repairCost: { wood: 3, stone: 5 },
    buildTime: 60, blocksPath: true, visionBlock: true,
    damageStates: ['fresh', 'cracked', 'chipped', 'rubble']
  },
  metal: {
    hp: 1200, buildCost: { wood: 5, stone: 10, metal: 5 }, repairCost: { wood: 3, stone: 5, metal: 2 },
    buildTime: 120, blocksPath: true, visionBlock: true,
    damageStates: ['fresh', 'dented', 'breached', 'melted']
  },
  electric: {
    hp: 800, buildCost: { wood: 5, stone: 5, metal: 10, scrap: 20 }, repairCost: { metal: 5, scrap: 10 },
    buildTime: 180, blocksPath: true, visionBlock: true, damagePerSecond: 15,
    damageStates: ['charged', 'spark', 'failing', 'dead']
  }
};
```

---

## PART 6: SOLANA CRYPTO INTEGRATION

### Vision
Launch on Solana with own token. Smart — Solana has lowest fees ($0.00025), fastest finality (400ms), most mature gaming ecosystem 2026. Star Atlas, Aurory, Stepn proved model.

### Token: $KINGZ (Alley Kingz Token)

**Tokenomics (Anti-Axie Design):**

```
TOTAL SUPPLY: 1,000,000,000 $KINGZ (fixed, no minting)

DISTRIBUTION:
├─ 40% Game Rewards (play-to-earn, missions, leaderboards)
├─ 20% Team & Advisors (4-year vest, 1-year cliff)
├─ 15% Ecosystem Fund (partnerships, marketing, exchange listings)
├─ 15% Treasury (community governance, future development)
├─ 7% Initial Liquidity (DEX pool, locked 2 years)
└─ 3% Airdrop (early players, beta testers)

UTILITY:
├─ Governance: Vote on game updates, features, balance
├─ Staking: Lock $KINGZ for passive rewards + VIP status
├─ Marketplace: Buy/sell cosmetic NFTs (skins, emotes, portraits)
├─ Events: Entry fee for high-stakes tournaments (optional)
└─ Premium Pass: Buy Alley Pass with $KINGZ (discount vs Gems)

HARD RULES (Axie collapse lessons):
├─ NEVER required for core gameplay (F2P can ignore it)
├─ NEVER buy power (no "buy level 10 cards with $KINGZ")
├─ NEVER breed-for-profit (breeding costs soft currency + $KINGZ cosmetic)
├─ ALWAYS have a sink (tournament fees, marketplace tax, staking lockup)
└─ ALWAYS transparent (on-chain supply, burn metrics, open treasury)
```

### Integration Architecture

```
PHASE 1: SOFT LAUNCH (Web2 Game, No Crypto)
─────────────────────────────────────────────
• Game launches with Gold/Gems/Scrap only
• All crypto code stubbed but ready
• Players build habits, economy balances
• Duration: 3-6 months

PHASE 2: WALLET CONNECT (Optional)
──────────────────────────────────
• Add "Connect Wallet" button (Phantom, Solflare, Backpack)
• Wallet = cosmetic badge + leaderboard name
• NO token yet — just wallet integration
• Duration: 1 month

PHASE 3: $KINGZ AIRDROP (Reward Early Players)
───────────────────────────────────────────────
• Snapshot of active players (by XP, not by spend)
• Airdrop $KINGZ based on: playtime + missions completed + crew contribution
• NO purchase required — purely earned
• Duration: 1 month

PHASE 4: MARKETPLACE + STAKING (Token Goes Live)
────────────────────────────────────────────────
• NFT marketplace for cosmetics (skins, emotes, portraits)
• 5% transaction tax → Burn + Treasury
• Staking pool: Lock $KINGZ for 30/90/180 days → Earn more $KINGZ + VIP
• Duration: Ongoing

PHASE 5: GOVERNANCE (Community-Owned)
─────────────────────────────────────
• DAO votes on: new card releases, balance patches, event themes
• Treasury funds community-created content (UGC maps, skins)
• Duration: Ongoing
```

### Technical Implementation (Solana)

```javascript
import { Connection, PublicKey, Transaction } from '@solana/web3.js';
import { Program, AnchorProvider, web3 } from '@coral-xyz/anchor';

const TOKEN_PROGRAM_ID = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');

class SolanaIntegration {
  constructor() {
    this.connection = new Connection('https://api.mainnet-beta.solana.com');
    this.programId = new PublicKey('YOUR_PROGRAM_ID_HERE');
  }

  async connectWallet() {
    const { solana } = window;
    if (!solana) {
      alert('Please install Phantom wallet');
      return null;
    }
    const response = await solana.connect();
    this.wallet = response.publicKey;
    return this.wallet;
  }

  async rewardPlayer(playerId, amount, reason) {
    // Server-side only — never client-side
    const transaction = new Transaction();
    // Create token account if needed
    // Transfer $KINGZ from treasury to player
    // Log reason on-chain (memo program)
    return this.connection.sendTransaction(transaction, [serverKeypair]);
  }

  async stake(amount, durationDays) {
    // Lock tokens in staking contract
    // Duration: 30/90/180 days
    // Reward: APY based on duration + game activity
  }

  async buyNFT(nftMint, price) {
    // Escrow $KINGZ
    // Transfer NFT from seller to buyer
    // 5% tax split: 2.5% burn, 2.5% treasury
  }
}
```

### Legal Guardrails (CRITICAL)

1. **$KINGZ is utility token, not security** — Genuine in-game utility (governance, cosmetics, staking rewards from gameplay, not investment returns)
2. **No "investment expectation"** — Never promise price appreciation, never market as investment
3. **No US players without KYC** — Geoblock US IP addresses OR implement full KYC/AML
4. **Transparent treasury** — All funds visible on-chain, community-controlled
5. **Theo GC sign-off** — Lawyer MUST review token design before launch

---

## PART 7: BUILD SEQUENCE

### Priority Order

```
WEEK 1-2: 3D DEPTH + VIDEO ATMOSPHERE
────────────────────────────────────────
□ Implement CSS 3D extruded photos for district cards
□ Add cinematic loop manager (3 loops max, muted, low opacity)
□ Test on mobile — ensure 60fps
□ Art: Generate 5 loop videos (neon flicker, rain, dust, fog, smoke)

WEEK 3-4: KARMA + MISSION SYSTEM
─────────────────────────────────
□ Build karma data structure (per district, per player)
□ Create 4 mission tiers (20 missions total)
□ Implement friendly encounter table
□ Build NPC dialog system with karma-gated options
□ Test: Can player go from Stranger to Legend in one district?

WEEK 5-6: UNIFIED ECONOMY
─────────────────────────
□ Map all currency flows (source → sink → convert)
□ Implement burn mechanisms for each currency
□ Build "synergy loop" — one action touches 3+ currencies
□ Balance: Ensure F2P player can reach TH L5 in 30 days

WEEK 7-8: TOWN HALL + BASE BUILDING
────────────────────────────────────
□ Implement 9-tile grid (expandable to 16, then 25)
□ Build 12 building types with upgrade costs
□ Implement wall/barricade system (wood/stone/metal/electric)
□ Add builder queue (Clash of Clans style)
□ Test: Raid a base, does layout matter?

WEEK 9-10: SOLANA INTEGRATION (STUBS)
─────────────────────────────────────
□ Add "Connect Wallet" button (Phantom)
□ Implement wallet read-only (badge, name)
□ Write $KINGZ token contract (devnet)
□ Test airdrop mechanism (devnet)
□ Legal review with Theo GC

WEEK 11-12: POLISH + TESTING
────────────────────────────
□ All systems integration test
□ Economy stress test (1000 simulated players)
□ Mobile performance audit
□ Beta launch with 100 players
```

---

## PART 8: TECH STACK RECOMMENDATION

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Canvas2D + CSS 3D Transforms | Existing stack, proven, mobile-friendly |
| Video | HTML5 `<video>` muted loops | Lightweight, no WebGL overhead |
| Backend | Node.js + PostgreSQL | Existing stack, proven |
| Blockchain | Solana + Anchor Framework | Lowest fees, fastest finality, best gaming ecosystem |
| Wallet | Phantom + Solflare + Backpack | 90% of Solana users use these |
| NFTs | Metaplex (Token Metadata) | Solana standard, proven by Magic Eden |
| Indexing | Helius / QuickNode | Real-time on-chain data for leaderboards |
| Storage | Arweave / IPFS | Permanent storage for NFT art |

---

## KEY INSIGHTS SUMMARY

1. **3D Depth:** CSS 3D transforms give 80% of depth perception with 20% of technical cost. Don't rebuild in Three.js.

2. **Video:** Cinematic loops (3-5s, muted, max 3 concurrent) add life without killing performance.

3. **Karma:** District-specific reputation with 7 tiers. Friendly encounters at higher karma. Missions unlock by tier.

4. **Economy:** Every currency must have a source, sink, and conversion path. The synergy loop = one action touches 3+ currencies.

5. **Base Building:** 9-tile grid, expandable. Town Hall gates everything. Walls/barricades matter for defense.

6. **Crypto:** Launch game first, crypto second. $KINGZ = utility only, never power. 5-phase rollout. Legal review mandatory.

---

*Document prepared based on Alley Kingz game design documents (AK_GAME_VISION.md, AK_2D_3D_CONCEPT.md, AK_MASTER_GAME_DESIGN_SYNTHESIS.md, AK_HUB_INTERACTION_ROAMING_COMBAT_SPEC.md) and 2026 best-in-class research.*
*Sources: Sunflower Land economy design, Solana gaming ecosystem (Star Atlas, Aurory, Stepn), Brawl Stars 2.5D rendering, CSS 3D transform techniques, Clash of Clans base-building mechanics, GTA V district reputation systems.*
*Legal: Theo GC review required before token launch. US geoblock or KYC mandatory.*
