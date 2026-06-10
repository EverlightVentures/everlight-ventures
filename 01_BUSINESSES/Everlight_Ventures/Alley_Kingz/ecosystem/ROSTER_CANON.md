# ALLEY KINGZ -- ROSTER CANON
**The single source of truth for who/what is in the game.**
Date: 2026-06-02 | Owner: Game Canon (Hive) | Status: CANON LOCKED (pending operator sign-off on the kill-list)

> **Canon model (locked, from MASTER_ECOSYSTEM_PLAN Decision B):**
> **Dogs are the IP. Vehicles are the toys.**
> The 48 cyberpunk DOG characters in `cards.json` ARE the roster. The 12 cars from
> `GAME_VISION.md` are NOT separate characters -- they become the Twisted-Metal war-RIGS
> that the dog crews pilot. One dog, one currency ($BCARDD), one aesthetic, one arcade.
> $BCARDD the Dogo Argentino is card #0001 Mythic, the coin mascot, AND the blackjack dealer --
> the single thread through the whole ecosystem.

This file does NOT re-stat anything. All stats live in the canonical data files (Section 7).
This file declares: the 4 factions, the 4 Mythics, the full rarity ladder, how vehicles
attach to dogs, and which duplicate files we KEEP vs KILL.

---

## 1. THE FOUR FACTIONS (canon, from cards.json `class`)

The 48 dogs are split evenly across 4 crews -- **exactly 12 each**. Faction = the `class` field
in `cards.json` (unchanged). Each faction gets a Twisted-Metal rig-class identity so the cars map
cleanly onto the dogs.

| # | Faction (canon `class`) | Count | Identity | Rig-class (vehicle skin language) | Mythic anchor |
|---|---|---|---|---|---|
| 1 | **Boneguard Crew** | 12 | Tank/guard pack. Broad, imposing, soak-and-hold. | Armored bruiser rigs -- ram plows, plate armor, slow + unstoppable | **$BCARDD** (#0001) |
| 2 | **Zoomie Syndicate** | 12 | Speed/assassin/dash. Lean, fast, crit-and-vanish. | Muscle + sport rigs -- nitro, drag bodies, glass-cannon speed | **Jagged** |
| 3 | **Leashbreak Tactix** | 12 | Control/hacker/support. Disable, slow, heal, shield. | Tech-ops rigs -- jammer vans, EMP arrays, signal-warfare | **Rosco** |
| 4 | **K9 Circuitry** | 12 | Structure/turret/drone/spawner. Hold ground, deploy bots. | Turret + utility rigs -- mounted-gun trucks, drone carriers, rail platforms | **Crown Foxhound** |

Total = 48 cards (12 x 4). Verified by count against `cards.json` 2026-06-02.

> NOTE: the master plan and earlier briefs say "50-card roster." The actual `cards.json` holds
> **48** dogs (12 per faction). 48 is the truth; "50" was an estimate. Flagged in Section 8.

The faction NAMES are the canon spine. (PRD_V2 lists a different 7-class taxonomy --
Street/Cartel/Tech/Lowrider/Muscle/Ghost/Rookie -- which was written for the human/car
draft. That taxonomy is DEMOTED to "rig-body archetypes" / deck-builder filter tags, NOT
factions. See Section 6.)

---

## 2. THE FOUR MYTHICS (canon, named)

These are the only 4 cards with `"rarity": "Mythic"` in `cards.json`. They are the hero set --
first Seedance videos, first NFT mints, the marketing tip of the spear.

| Card # | Name | Breed | Faction | Role | Cost | Signature ability | Queen-target | Pilots rig |
|---|---|---|---|---|---|---|---|---|
| **#0001** | **$BCARDD** | Dogo Argentino | Boneguard Crew | Vanguard | 10 | Crownbreaker (shield self, can target Queen) | YES | **The Crown Rig** -- matte-black armored war-truck, gold trim, ram plow. The coin/dealer dog. |
| **#0002** | **Jagged** | Doberman | Zoomie Syndicate | Assassin | 11 | Shadow Fang (teleport to Queen) | YES | **Shadowblade** -- low-slung nitro muscle car, blade fenders |
| **#0003** | **Rosco** | Australian Cattle Dog | Leashbreak Tactix | Controller | 10 | Leashbreak (disable tower, can target Queen) | YES | **The Jammer** -- antenna-bristled tech van, EMP dish |
| **#0004** | **Crown Foxhound** | Foxhound | K9 Circuitry | Assassin | 11 | Royal Hunt (can target Queen) | YES | **Railhound** -- turret-platform rig, rail-cannon mount |

> Card numbers #0002-#0004 are ASSIGNED HERE (only #0001 $BCARDD pre-existed). Mythic order
> = faction order. This makes the NFT mint indices deterministic.

---

## 3. RARITY LADDER (canon, from cards.json `rarity` counts)

Exact counts pulled from `cards.json` (do not guess -- these drive mint scarcity + Seedance budget):

| Rarity | Count | Cards | NFT / video priority | Frame (ART_BIBLE) |
|---|---|---|---|---|
| **Mythic** | 4 | $BCARDD, Jagged, Rosco, Crown Foxhound | Batch 1 -- cinematic hero videos | Crown Gold holo + crown glow (top of Legendary tier, "Mythic" = Mythic crown variant) |
| **Legendary** | 1 | Stonejaw | Batch 1 -- hero treatment | Crown Gold holographic, gold foil emboss |
| **Epic** | 9 | Balboa, Iron Rottweiler, Razor Vizsla, Aero Malinois, Synth Collie, Noir Setter, Pulse Border Collie, Circuit Retriever, Nova Shepherd | Batch 2 -- short hero clips | Brick/orange flame, ember sparks, hammered copper |
| **Rare** | 20 | (all `rarity: Rare` -- see cards.json) | Batch 3 -- batch video | Blue chrome, subtle pulse |
| **Common** | 14 | (all `rarity: Common` -- see cards.json) | Batch 4 -- short loop, long tail | Asphalt brushed steel, no glow |

Total = 4 + 1 + 9 + 20 + 14 = 48. Verified by count against `cards.json` 2026-06-02.

> ART_BIBLE.md v1.0 only defines 4 rarity frames (Common/Rare/Epic/Legendary). **Mythic is a
> new top tier** that needs its own frame spec -- recommend: Legendary's Crown Gold holo PLUS an
> animated crown sigil + rainbow-edge holo (the "Icon" treatment PRD_V2 reserved for tier 5).
> ACTION: ART_BIBLE gets a "Mythic" row added (flagged, Section 8).

---

## 4. HOW VEHICLES ATTACH TO DOGS (the fusion mechanic)

The 12 cars from `GAME_VISION.md` are NOT cards and NOT characters. They are **RIGS** -- the
vehicle a dog crew pilots into the lane. This is the Twisted-Metal layer bolted onto the dog roster.

**Binding rule:** a RIG is a property of a dog card, not its own entity. In data terms, each card
gains an optional `rig` object (see schema, Section 9). One dog = one signature rig at base; rigs
are skinnable/swappable later (cosmetic + Chop Shop output), never pay-to-win.

**The 12 GAME_VISION cars -> rig-classes (mapped to faction, NO new characters invented):**

| GAME_VISION car | Becomes RIG | Rig-class | Maps to faction | Why |
|---|---|---|---|---|
| Lowrider | Heavy plate hauler | Bruiser | Boneguard Crew | Slowest, tankiest -- matches Vanguard guard dogs |
| Pickup | Building-breaker rig | Bruiser | Boneguard Crew | Building-only tank -> Boneguard structure pressure |
| Muscle Car | Ram bruiser | Bruiser | Boneguard Crew | RAM double-hit -> Striker/Vanguard melee |
| Monster Truck | Area-crush rig | Bruiser | Boneguard Crew | Area damage -> heavy Boneguard finisher |
| GTR | Nitro sport | Sprinter | Zoomie Syndicate | NITRO burst -> dash/assassin dogs |
| Drag Racer | Glass-cannon dragster | Sprinter | Zoomie Syndicate | Fastest unit -> Skirmisher zoomies |
| Bike Duo | Twin sport bikes | Sprinter | Zoomie Syndicate | Fast ranged pair -> Zoomie skirmishers |
| Armored SUV | Spell-shield cruiser | Tech-ops | Leashbreak Tactix | Blocks first spell -> Tactix support/control |
| Van | Long-range sprayer | Tech-ops | Leashbreak Tactix | Ranged control -> Tactix backline |
| EMP (spell) | EMP array (rig weapon) | Tech-ops | Leashbreak Tactix | Energy blast -> hacker/disable kit |
| Oil Slick (spell) | Slick-layer (rig weapon) | Turret-util | K9 Circuitry | Slow + DoT zone -> K9 ground-control |
| Molotov (spell) | Incendiary launcher (rig weapon) | Turret-util | K9 Circuitry | Area fire -> K9 turret/structure |

> The 4 GAME_VISION "spell" cars (EMP, Oil Slick, Molotov + the implied spell slot) do NOT become
> dog characters or standalone spell cards. They become **rig weapon mods** -- the armament a
> dog's rig carries. Spells in the shipping game come from PRD_V2's spell list, themed to dogs
> (e.g. "Frost Bark" AoE slow already exists as Chill Samoyed's ability), not from the car spells.

**The Chop Shop (from GAME_VISION) survives as the RIG breeding bay:** two rigs in, a hybrid
rig out (cosmetic body + weapon-mod reroll). It breeds RIGS, never dogs -- the 48 dogs are a
fixed, ownable IP roster (NFT scarcity depends on the roster staying closed). This keeps the
addictive breeding loop GAME_VISION wanted without diluting the character IP.

---

## 5. THE THREAD (one dog, one currency, one aesthetic, one arcade)

| Surface | $BCARDD's role | Tie |
|---|---|---|
| **$BCARDD coin** | The mascot face (Solana/pump.fun) | `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md` |
| **Card game** | Card #0001 Mythic, pilots the Crown Rig | `cards.json` |
| **NFT set** | #0001 mint, on-chain stats = the card | `nft_metadata_template.json` |
| **Blackjack dealer** | The same Dogo who deals your hand | `Everlight_Gaming/Blackjack/` |
| **Arcade** | Hero of the Everlight Arcade landing | `vantaris/src/app/arcade/` |

Aesthetic spine for ALL of it: Crown Gold `#D4AF37` on Midnight Deep `#0D0D1A` / vanta-black
`#050507`, hyper-real PBR per ART_BIBLE, golden-hour-or-neon-night lighting. No cartoon, no slop.

---

## 6. WHAT HAPPENS TO THE PRD_V2 TAXONOMY (reconciliation, not deletion)

PRD_V2 + 05_DATA_MODEL.md were written for the human/car draft. They are NOT thrown away --
they are RE-SCOPED so nothing useful is lost:

| PRD_V2 concept | Canon disposition |
|---|---|
| 7 card classes (Street/Cartel/Tech/Lowrider/Muscle/Ghost/Rookie) | DEMOTED to deck-builder **filter tags** + rig-body archetypes. The 4 dog factions are the real classes. |
| 48-card human/car roster (Muscle Car, El Jefe, Ghost Rider...) | RETIRED as characters. Useful ones survive as RIG names or arena flavor, never as dog cards. |
| Rarity tier "Icon" (5th tier) | RENAMED to **Mythic** to match cards.json. Same holo treatment. |
| HQ Van = King Tower, NOS Bottles, Crew Pass, Chop Shop, 100-level ladder | KEPT as-is. These are systems, not characters -- they all stay canon. |
| 05_DATA_MODEL.md CardDefinition schema | KEPT as the engine schema, EXTENDED with `factionId`, `rig`, `breed`, `queenTarget`, `cardNumber` (Section 9). |
| `cardClass` enum | EXTENDED: add the 4 factions as the primary class; old 7 become a `bodyArchetype` sub-tag. |

Net: dogs win the character layer; PRD_V2 keeps the systems layer.

---

## 7. CANONICAL DATA FILES (the keep / kill decision)

Four divergent card-data lineages exist on disk. This is the explicit ruling.

### KEEP -- ONE canonical set (the 48-dog roster)
| File | Path | Why |
|---|---|---|
| **cards.json** (CANON) | `01_OnyxPOS/prototype_dec2025/game_design/cards.json` | The 48-dog roster, 4 factions, $BCARDD #0001. Master plan's named source of truth. |
| **decks.json** (CANON) | `01_OnyxPOS/prototype_dec2025/game_design/decks.json` | 4 faction starter decks, references the dogs. |
| **ability_params.json** (CANON) | `01_OnyxPOS/prototype_dec2025/game_design/ability_params.json` | 2-ability rotation per dog + rarity scaling. |

> NOTE on the canonical HOME: the master plan (Phase 2) wants ONE merged canon under the game.
> The CURRENT bytes live under OnyxPOS. RECOMMENDED next step (not yet done): move/copy these 3
> files to `Alley_Kingz/ecosystem/data/` as the permanent home and repoint readers, so the canon
> lives with the game, not under the unrelated OnyxPOS prototype. Flagged in Section 8.

### KILL -- duplicates + divergent drafts (do NOT let these fragment the game)
| File | Path | Ruling | Reason |
|---|---|---|---|
| Unity cards.json | `BCARDI_Crypto/dell_unity_setup_dec2025/Assets/BCARDI/Resources/cards.json` | **KILL as a source; regenerate from canon** | Byte-identical to canon (verified `cmp`). Keep the Unity FOLDER, but it must be a build-time COPY of canon, never hand-edited. |
| Unity decks.json | same Resources/ | KILL as source | Byte-identical duplicate. |
| Unity ability_params.json | same Resources/ | KILL as source | Byte-identical duplicate. |
| App_Files GameData.json | `Alley_Kingz/App_Files/GameData.json` | **KILL (archive)** | A THIRD, conflicting roster -- 19 HUMAN-crew cards (Street Brawler, Neon Marksman, $BCARDD as a Legendary human-hybrid `bcardd_yung_printz`). Pre-dog-canon draft. Contradicts dogs-are-IP. |
| ArenaAdvance GameData.Json | `Alley_Kingz/Alley_Kingz/ArenaAdvance/Assets/Resources/GameData.Json` | **KILL (archive)** | Near-duplicate of App_Files GameData (15740 vs 14543 bytes, minor description drift). Same human-crew draft. |

**Disposition rule (per Comms Doctrine -- no deletion without a memory pass):**
the two GameData.json drafts go through `memory_pipeline.ingest_before_delete()` then to
`08_BACKUPS/archived_prototypes/alley_kingz_human_crew_draft/`. The Unity Resources JSONs are
NOT deleted -- they are flagged "generated, do not hand-edit" and a build step copies canon into
them so they can never drift again.

**One-line summary:** KEEP the 3 OnyxPOS dog JSONs as canon (move home to `ecosystem/data/` next).
The Unity copies become generated mirrors. The 2 GameData.json human-crew drafts are archived.

---

## 8. OPEN DECISIONS / GAPS (surfaced; defaults recommended)

1. **Canon file home.** Files currently live under OnyxPOS. RECOMMEND moving the 3 canon JSONs to
   `Alley_Kingz/ecosystem/data/` and repointing the Unity build to copy from there. (Default: yes, move.)
2. **Mythic frame spec.** ART_BIBLE v1.0 stops at Legendary. RECOMMEND adding a Mythic row =
   Crown Gold holo + animated crown sigil + rainbow holo edge. (Default: add it.)
3. **Card numbering.** Only $BCARDD (#0001) was numbered. This file assigns #0002-#0004 to the
   Mythics by faction order. RECOMMEND numbering all 48 by faction then descending rarity for
   deterministic NFT mint indices. (Default: yes, number all 48.)
4. **Rig data location.** Rigs added as a `rig` block on each card (Section 9) vs a separate
   `rigs.json`. RECOMMEND inline `rig` on the card for v1 (one dog = one signature rig), split to
   `rigs.json` only when rig-skinning/Chop-Shop-breeding ships. (Default: inline for v1.)
5. **Faction count vs PRD.** Canon = 4 factions; PRD = 7 classes. Resolved in Section 6 (4 factions
   win, 7 become filter tags). Logged here so it is not re-litigated.
6. **Roster size correction.** Master plan / task brief say "50 cards." `cards.json` actually holds
   **48** (12 per faction). This canon uses 48. RECOMMEND fixing the "50" in MASTER_ECOSYSTEM_PLAN
   to 48, OR adding 2 new dogs (e.g. a 2nd Legendary + a 13th to one faction) if 50 is desired for
   marketing-round numbers. (Default: keep 48, correct the master plan. No new characters invented here.)

---

## 9. THE SCHEMA (what a canon card looks like after the merge)

Extends `cards.json` (existing fields KEPT verbatim) + 05_DATA_MODEL.md `CardDefinition`
(engine schema KEPT) with the merge fields. NOTHING existing is renamed or restatted.

```jsonc
{
  // === EXISTING cards.json fields (UNCHANGED -- do not restat) ===
  "class": "Boneguard Crew",      // = factionId (canon class). One of the 4 factions.
  "name": "$BCARDD",
  "breed": "Dogo Argentino",       // dog identity (NEW canon: every card is a dog)
  "cost": 10,                       // elixir cost
  "role": "Vanguard",              // gameplay role (Vanguard/Assassin/Controller/Support/etc.)
  "rarity": "Mythic",              // Mythic | Legendary | Epic | Rare | Common
  "tags": ["Pack", "Guard"],
  "hp": 2600,
  "damage": 160,
  "attack_speed": 0.7,
  "move_speed": 0.6,
  "range": 1,
  "ability": { "name": "Crownbreaker", "description": "...", "cooldown": 18 },
  "queen_target": true,

  // === MERGE FIELDS (NEW -- added by this canon, no stat changes) ===
  "cardNumber": "0001",            // deterministic NFT mint index ($BCARDD=0001)
  "factionId": "boneguard_crew",   // machine key for "class"
  "bodyArchetype": "bruiser",      // demoted PRD_V2 class -> rig-body tag (bruiser|sprinter|tech_ops|turret_util)
  "isMythic": true,                // hero-set flag (drives Seedance batch + frame)
  "rig": {                          // the Twisted-Metal vehicle this dog pilots (TOY, not a character)
    "name": "The Crown Rig",
    "rigClass": "bruiser",          // bruiser | sprinter | tech_ops | turret_util
    "weaponMod": "ram_plow",        // from the 4 retired car-spells: ram_plow|emp_array|slick_layer|incendiary
    "sourceCar": "Muscle Car",      // provenance: which GAME_VISION car this rig descends from
    "skinnable": true,              // cosmetic swap allowed (never pay-to-win)
    "choppable": true               // eligible for Chop Shop rig-breeding
  },

  // === NFT BINDING (from nft_metadata_template.json -- on-chain stats = the card) ===
  "nft": {
    "chain": "solana",              // per Decision A (recommended Solana-native)
    "animation_url": "",            // Seedance Twisted-Metal battle clip of this dog-crew rig
    "onchain_stats": ["hp", "damage", "ability"]  // stats encoded on-chain = playable card
  }
}
```

**Ability detail** stays in `ability_params.json` (2-ability rotation per dog) -- unchanged,
referenced by `name`. **Deck membership** stays in `decks.json` -- unchanged.

---

## 10. ONE-PAGE TAKEAWAY

- **48 dogs = the roster** (4 factions, 12 each: Boneguard Crew, Zoomie Syndicate, Leashbreak Tactix, K9 Circuitry).
- **4 Mythics:** $BCARDD (#0001, the coin/dealer dog), Jagged, Rosco, Crown Foxhound -- one per faction.
- **Rarity:** 4 Mythic / 1 Legendary / 9 Epic / 20 Rare / 14 Common = 48.
- **12 cars = rigs, not characters.** Each maps to a faction; the 4 car-spells become rig weapon mods; Chop Shop breeds rigs, not dogs.
- **Keep ONE data set:** the 3 OnyxPOS dog JSONs. Unity copies = generated mirrors. The 2 GameData.json human-crew drafts = archived.
- **PRD_V2 systems survive** (HQ Van, NOS Bottles, Crew Pass, ladder); its 7-class taxonomy is demoted to filter tags; its "Icon" tier is renamed "Mythic".

*Canon authored 2026-06-02. Pairs with MASTER_ECOSYSTEM_PLAN_2026-06-02.md (Decisions A+B) and BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md. Changes require Game-Canon sign-off.*
