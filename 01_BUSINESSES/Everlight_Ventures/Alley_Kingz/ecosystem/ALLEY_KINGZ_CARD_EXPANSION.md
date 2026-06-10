# ALLEY KINGZ -- CARD EXPANSION MASTER PLAN (the 110-card set)
**Date:** 2026-06-07 | **Creative Director synthesis (phase 9 of 9)**
**Sits under:** `ALLEY_KINGZ_MASTER_STRATEGY.md` (the gameplay + economy spine) and `MASTER_BUILD_PLAN.md` (the 5-pillar ecosystem). This doc does NOT re-open locked ecosystem decisions (Solana-native NFTs, coin-first, Option A legal, web-first). It specifies the **card roster, the decks, the deck-builder, the shop/gacha economy, the build roadmap, and the art direction.**
**Synthesized from:** `design_roster.md`, `design_decks.md`, `design_economy.md`, `research_economy.md`, `research_gacha_meta.md`, current `data/cards.json` (48) + `data/decks.json`.
**Companion artifact:** `data/card_art_manifest.json` -- machine-readable, 106 character cards, one gritty TV-MA Leonardo prompt each, for the unattended art cron.

---

## 0. WHAT THIS EXPANSION IS (one paragraph)
We grow the canon **48 dogs + 5 spells** into a **110-card set** by adding a **VARIANT FAMILY** layer: every Rare and Epic dog now anchors a 3-card family -- the canon **[ORIGINAL]**, a bunkered **[HEAVY]** build, and a stripped **[STREET]** build -- same dog line, same faction, same role/targeting, different chop-shop spec. Mythic signatures, the Stonejaw Legendary, and the Commons stay 1-of-1 (scarcity is the point; `$BCARDD` #0001 = the coin = the dealer). The result is **106 character cards + 5 spells = 111 NFTs** (marketed as the "110-card set"), the rarity pyramid the economy curve was tuned for, and a collection deep enough to feed 10 meta decks, a clean-gacha draw, and a 90-day rotating shop -- without inventing a single new mechanic.

**Headline numbers:**
- **106 character cards** (4 Mythic / 10 Legendary / 29 Epic / 29 Rare / 34 Common) **+ 5 spells = 111 NFTs.**
- **58 NEW cards** (the Heavy/Street variants, `cardNumber` 0049-0106) **+ 48 originals** (0001-0048, stats untouched).
- **Faction balance:** Boneguard 26 / Zoomie 26 / Leashbreak 28 / K9 26.
- **10 premade decks** (8 meta + 2 wildcard), 11 cards each, counter-web closed.

---

## 1. THE FINAL 110-CARD ROSTER

### 1.1 The VARIANT FAMILY system (how 48 -> 106)
Each eligible CHARACTER anchors a **3-card family** -- same faction, same role, same targeting profile, different *build*:
- **[ORIGINAL]** -- the canon dog. Stats verbatim from `cards.json`. Untouched.
- **[HEAVY]** -- the bunkered build: **+28% HP, -15% dmg, -10% atk speed, -12% move, +1 cost, +2 cooldown, rarity +1 tier.** Defensive tilt. The chase tank.
- **[STREET]** -- the stripped glass-cannon: **-28% HP, +25% dmg, +12% atk speed, +10% move, -1 cost (min 1), -2 cooldown (min 6), rarity -1 tier.** Aggressive/execute tilt. The cheap killer.

**Who gets variants:**
- **Signatures** (4 Mythic: $BCARDD, Jagged, Rosco, Crown Foxhound + the Stonejaw Legendary) -> **1-of-1, no variants.**
- **Commons** (the 14 canon commons) -> **1-of-1** ladder staples.
- **Every Rare + Epic** (29 dogs) -> **full 3-card family** (original + Heavy + Street).

**Stat-tilt math (deterministic, applied by the data generator -- never hand-typed):**
```
HEAVY : hp*1.28  dmg*0.85  atkspd*0.90  move*0.88  cost+1      cooldown+2      rarity+1
STREET: hp*0.72  dmg*1.25  atkspd*1.12  move*1.10  cost-1(min1) cooldown-2(min6) rarity-1
```
Structures keep `move_speed 0`. Domain / targets / splash / queen_target / faction / rig-class are **inherited unchanged** -- a variant plays the same lane role as its parent, it just trades survivability for punch (or vice-versa). This is what keeps the 110-set balanceable: no new targeting rules, no new mechanics, just a survivability<->damage slider with a cost+rarity consequence.

### 1.2 Rarity pyramid + faction balance (collection health)
| Rarity | Count | | Faction | Count |
|---|---|---|---|---|
| Mythic | 4 | | Boneguard Crew | 26 |
| Legendary | 10 | | Zoomie Syndicate | 26 |
| Epic | 29 | | Leashbreak Tactix | 28 |
| Rare | 29 | | K9 Circuitry | 26 |
| Common | 34 | | **Total** | **106** |
| **Total** | **106** | | | |

The pyramid is intentionally bottom-heavy (34 Common base) so the daily shop + chest + ladder have a deep common pool to draw from, while the 10 Legendary + 4 Mythic at the apex are the chase that funds the draw banner.

### 1.3 MASTER ROSTER TABLE (all 106)
Legend: **V** = variant (O=Original / H=Heavy / S=Street). **Dom**=domain, **Tgt**=targets, **Spl**=splash (Y/radius), **Q**=can strike the Queen. New cards (0049-0106) in the Heavy/Street rows.

#### Boneguard Crew (26) -- tanks, ram-plows, junkyard
| # | Card | V | Breed | Role | Rarity | Cost | HP | DMG | AtkSpd | Move | Rng | Dom | Tgt | Spl | Q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0001 | $BCARDD | O | Dogo Argentino | Vanguard | Mythic | 10 | 2850 | 180 | 0.7 | 0.55 | 1 | ground | ground | Y/1.4 | Y |
| 0002 | Stonejaw | O | Mastiff | Vanguard | Legendary | 7 | 2850 | 145 | 0.7 | 0.55 | 1 | ground | ground | - | - |
| 0003 | Balboa | O | Boxer | Striker | Epic | 6 | 1500 | 175 | 1.05 | 0.85 | 1 | ground | ground | - | - |
| 0049 | Cinderblock | H | Boxer | Striker | Legendary | 7 | 1920 | 149 | 0.95 | 0.75 | 1 | ground | ground | - | - |
| 0050 | Knuckles | S | Boxer | Striker | Rare | 5 | 1080 | 219 | 1.18 | 0.94 | 1 | ground | ground | - | - |
| 0004 | Iron Rottweiler | O | Rottweiler | Vanguard | Epic | 9 | 2850 | 155 | 0.7 | 0.55 | 1 | ground | ground | - | - |
| 0051 | Tombstone | H | Rottweiler | Vanguard | Legendary | 10 | 3648 | 132 | 0.63 | 0.48 | 1 | ground | ground | - | - |
| 0052 | Razorgums | S | Rottweiler | Vanguard | Rare | 8 | 2052 | 194 | 0.78 | 0.61 | 1 | ground | ground | - | - |
| 0005 | Granite Saint | O | St. Bernard | Vanguard | Rare | 8 | 2650 | 135 | 0.7 | 0.55 | 1 | ground | ground | - | - |
| 0053 | Anvil | H | St. Bernard | Vanguard | Epic | 9 | 3392 | 115 | 0.63 | 0.48 | 1 | ground | ground | - | - |
| 0054 | Hatchet | S | St. Bernard | Vanguard | Common | 7 | 1908 | 169 | 0.78 | 0.61 | 1 | ground | ground | - | - |
| 0006 | Grit Bulldog | O | Bulldog | Striker | Rare | 5 | 1300 | 150 | 1.05 | 0.85 | 1 | ground | ground | - | - |
| 0055 | Bonecrusher | H | Bulldog | Striker | Epic | 6 | 1664 | 128 | 0.95 | 0.75 | 1 | ground | ground | - | - |
| 0056 | Switch | S | Bulldog | Striker | Common | 4 | 936 | 188 | 1.18 | 0.94 | 1 | ground | ground | - | - |
| 0007 | Alloy Akita | O | Akita | Lancer | Rare | 6 | 1100 | 180 | 0.95 | 0.85 | 2 | ground | both | - | - |
| 0057 | Warhorse | H | Akita | Lancer | Epic | 7 | 1408 | 153 | 0.85 | 0.75 | 2 | ground | both | - | - |
| 0058 | Lugnut | S | Akita | Lancer | Common | 5 | 792 | 225 | 1.06 | 0.94 | 2 | ground | both | - | - |
| 0010 | Tank Pug | O | Pug | Support | Common | 3 | 750 | 45 | 0.9 | 0.85 | 3 | air | both | - | - |
| 0011 | Copper Chow | O | Chow | Striker | Common | 4 | 1100 | 125 | 1.05 | 0.85 | 1 | ground | ground | - | - |
| 0008 | Warden Newfie | O | Newfoundland | Support | Rare | 7 | 1100 | 70 | 0.9 | 0.85 | 2 | ground | both | - | - |
| 0059 | Ironhide | H | Newfoundland | Support | Epic | 8 | 1408 | 60 | 0.81 | 0.75 | 2 | ground | both | - | - |
| 0060 | Snaggle | S | Newfoundland | Support | Common | 6 | 792 | 88 | 1.01 | 0.94 | 2 | ground | both | - | - |
| 0009 | Rust Cane Corso | O | Cane Corso | Vanguard | Rare | 8 | 2650 | 135 | 0.7 | 0.55 | 1 | ground | ground | - | - |
| 0061 | Slab | H | Cane Corso | Vanguard | Epic | 9 | 3392 | 115 | 0.63 | 0.48 | 1 | ground | ground | - | - |
| 0062 | Brassknuck | S | Cane Corso | Vanguard | Common | 7 | 1908 | 169 | 0.78 | 0.61 | 1 | ground | ground | - | - |
| 0012 | Brick Bullmastiff | O | Bullmastiff | Vanguard | Common | 6 | 2250 | 110 | 0.7 | 0.55 | 1 | ground | ground | - | - |

#### Zoomie Syndicate (26) -- speed, street-racers, neon
| # | Card | V | Breed | Role | Rarity | Cost | HP | DMG | AtkSpd | Move | Rng | Dom | Tgt | Spl | Q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0013 | Jagged | O | Doberman | Assassin | Mythic | 11 | 1900 | 230 | 1.1 | 1.1 | 1 | ground | ground | - | Y |
| 0016 | Pixel Greyhound | O | Greyhound | Skirmisher | Rare | 3 | 700 | 95 | 1.3 | 1.4 | 1 | air | ground | - | - |
| 0063 | Roadblock | H | Greyhound | Skirmisher | Epic | 4 | 896 | 81 | 1.17 | 1.23 | 1 | air | ground | - | - |
| 0064 | Nitro | S | Greyhound | Skirmisher | Common | 2 | 504 | 119 | 1.46 | 1.54 | 1 | air | ground | - | - |
| 0017 | Circuit Shiba | O | Shiba Inu | Striker | Rare | 4 | 1200 | 135 | 1.05 | 1.1 | 1 | ground | ground | - | - |
| 0065 | Bullbar | H | Shiba Inu | Striker | Epic | 5 | 1536 | 115 | 0.95 | 0.97 | 1 | ground | ground | - | - |
| 0066 | Switchblade | S | Shiba Inu | Striker | Common | 3 | 864 | 169 | 1.18 | 1.21 | 1 | ground | ground | - | - |
| 0021 | Neon Whippet | O | Whippet | Skirmisher | Common | 2 | 600 | 75 | 1.3 | 1.4 | 1 | air | ground | - | - |
| 0022 | Turbo Jack | O | Jack Russell | Striker | Common | 3 | 1050 | 110 | 1.05 | 1.1 | 1 | ground | ground | - | - |
| 0014 | Razor Vizsla | O | Vizsla | Lancer | Epic | 5 | 1150 | 180 | 0.95 | 0.85 | 2 | ground | both | - | - |
| 0067 | Rollcage | H | Vizsla | Lancer | Legendary | 6 | 1472 | 153 | 0.85 | 0.75 | 2 | ground | both | - | - |
| 0068 | Ricochet | S | Vizsla | Lancer | Rare | 4 | 828 | 225 | 1.06 | 0.94 | 2 | ground | both | - | - |
| 0018 | Flash Saluki | O | Saluki | Skirmisher | Rare | 4 | 750 | 110 | 1.3 | 1.4 | 1 | air | ground | - | - |
| 0069 | Crashcage | H | Saluki | Skirmisher | Epic | 5 | 960 | 94 | 1.17 | 1.23 | 1 | air | ground | - | - |
| 0070 | Hotwire | S | Saluki | Skirmisher | Common | 3 | 540 | 138 | 1.46 | 1.54 | 1 | air | ground | - | - |
| 0019 | Bolt Corgi | O | Corgi | Spawner | Rare | 4 | 750 | 55 | 0.9 | 0.85 | 2 | air | both | Y/1.8 | - |
| 0071 | Bumper | H | Corgi | Spawner | Epic | 5 | 960 | 47 | 0.81 | 0.75 | 2 | air | both | Y/1.8 | - |
| 0072 | Backfire | S | Corgi | Spawner | Common | 3 | 540 | 69 | 1.01 | 0.94 | 2 | air | both | Y/1.8 | - |
| 0020 | Glitch Basenji | O | Basenji | Hacker | Rare | 3 | 700 | 70 | 1.0 | 0.85 | 3 | ground | both | - | - |
| 0073 | Gridiron | H | Basenji | Hacker | Epic | 4 | 896 | 60 | 0.9 | 0.75 | 3 | ground | both | - | - |
| 0074 | Skidmark | S | Basenji | Hacker | Common | 2 | 504 | 88 | 1.12 | 0.94 | 3 | ground | both | - | - |
| 0015 | Aero Malinois | O | Malinois | Striker | Epic | 6 | 1500 | 175 | 1.05 | 1.1 | 1 | ground | ground | - | - |
| 0075 | Deadweight | H | Malinois | Striker | Legendary | 7 | 1920 | 149 | 0.95 | 0.97 | 1 | ground | ground | - | - |
| 0076 | Flatline | S | Malinois | Striker | Rare | 5 | 1080 | 219 | 1.18 | 1.21 | 1 | ground | ground | - | - |
| 0023 | Drift Sheltie | O | Sheltie | Support | Common | 2 | 700 | 40 | 0.9 | 1.1 | 3 | air | both | - | - |
| 0024 | Byte Beagle | O | Beagle | Blaster | Common | 3 | 550 | 80 | 1.1 | 0.85 | 4 | ground | both | - | Y |

#### Leashbreak Tactix (28) -- tech, hacker-vans, signal-yard
| # | Card | V | Breed | Role | Rarity | Cost | HP | DMG | AtkSpd | Move | Rng | Dom | Tgt | Spl | Q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0025 | Rosco | O | Australian Cattle Dog | Controller | Mythic | 10 | 1600 | 170 | 0.95 | 0.85 | 3 | ground | both | - | Y |
| 0026 | Synth Collie | O | Border Collie | Hacker | Epic | 5 | 900 | 90 | 1.0 | 0.85 | 3 | ground | both | - | - |
| 0077 | Firewall | H | Border Collie | Hacker | Legendary | 6 | 1152 | 76 | 0.9 | 0.75 | 3 | ground | both | - | - |
| 0078 | Glitchfork | S | Border Collie | Hacker | Rare | 4 | 648 | 112 | 1.12 | 0.94 | 3 | ground | both | - | - |
| 0029 | Holo Husky | O | Husky | Support | Rare | 5 | 950 | 60 | 0.9 | 0.85 | 3 | ground | both | - | - |
| 0079 | Deadbolt | H | Husky | Support | Epic | 6 | 1216 | 51 | 0.81 | 0.75 | 3 | ground | both | - | - |
| 0080 | Static | S | Husky | Support | Common | 4 | 684 | 75 | 1.01 | 0.94 | 3 | ground | both | - | - |
| 0030 | Chill Samoyed | O | Samoyed | Support | Rare | 4 | 900 | 55 | 0.9 | 0.85 | 3 | ground | both | - | - |
| 0081 | Bunkerlink | H | Samoyed | Support | Epic | 5 | 1152 | 47 | 0.81 | 0.75 | 3 | ground | both | - | - |
| 0082 | Shortcircuit | S | Samoyed | Support | Common | 3 | 648 | 69 | 1.01 | 0.94 | 3 | ground | both | - | - |
| 0031 | Prism Poodle | O | Poodle | Controller | Rare | 4 | 850 | 85 | 0.95 | 0.85 | 3 | ground | both | - | - |
| 0083 | Faraday | H | Poodle | Controller | Epic | 5 | 1088 | 72 | 0.85 | 0.75 | 3 | ground | both | - | - |
| 0084 | Hexer | S | Poodle | Controller | Common | 3 | 612 | 106 | 1.06 | 0.94 | 3 | ground | both | - | - |
| 0034 | Echo Dalmatian | O | Dalmatian | Controller | Common | 3 | 750 | 70 | 0.95 | 0.85 | 3 | ground | both | - | - |
| 0035 | Static Sheba Inu | O | Shiba Inu | Hacker | Common | 2 | 600 | 55 | 1.0 | 0.85 | 3 | ground | both | - | - |
| 0036 | Vibe Shih Tzu | O | Shih Tzu | Support | Common | 2 | 700 | 40 | 0.9 | 0.85 | 3 | ground | both | - | - |
| 0027 | Noir Setter | O | Setter | Controller | Epic | 6 | 1100 | 110 | 0.95 | 0.85 | 3 | ground | both | - | - |
| 0085 | Sandbag | H | Setter | Controller | Legendary | 7 | 1408 | 94 | 0.85 | 0.75 | 3 | ground | both | - | - |
| 0086 | Whitenoise | S | Setter | Controller | Rare | 5 | 792 | 138 | 1.06 | 0.94 | 3 | ground | both | - | - |
| 0032 | Signal Pointer | O | Pointer | Lancer | Rare | 4 | 1000 | 150 | 0.95 | 0.85 | 3 | ground | both | - | - |
| 0087 | Blacksite | H | Pointer | Lancer | Epic | 5 | 1280 | 128 | 0.85 | 0.75 | 3 | ground | both | - | - |
| 0088 | Carrier | S | Pointer | Lancer | Common | 3 | 720 | 188 | 1.06 | 0.94 | 3 | ground | both | - | - |
| 0033 | Ghost Spaniel | O | Spaniel | Skirmisher | Rare | 3 | 700 | 95 | 1.3 | 1.1 | 2 | air | both | - | - |
| 0089 | Hardline | H | Spaniel | Skirmisher | Epic | 4 | 896 | 81 | 1.17 | 0.97 | 2 | air | both | - | - |
| 0090 | Spike | S | Spaniel | Skirmisher | Common | 2 | 504 | 119 | 1.46 | 1.21 | 2 | air | both | - | - |
| 0028 | Pulse Border Collie | O | Border Collie | Support | Epic | 5 | 1050 | 65 | 0.9 | 0.85 | 3 | ground | both | - | - |
| 0091 | Bulwark | H | Border Collie | Support | Legendary | 6 | 1344 | 55 | 0.81 | 0.75 | 3 | ground | both | - | - |
| 0092 | Brownout | S | Border Collie | Support | Rare | 4 | 756 | 81 | 1.01 | 0.94 | 3 | ground | both | - | - |

#### K9 Circuitry (26) -- turrets, gun-rigs, docks
| # | Card | V | Breed | Role | Rarity | Cost | HP | DMG | AtkSpd | Move | Rng | Dom | Tgt | Spl | Q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0037 | Crown Foxhound | O | Foxhound | Assassin | Mythic | 11 | 1900 | 230 | 1.1 | 1.1 | 1 | ground | ground | Y/1.3 | Y |
| 0040 | Laser Beagle | O | Beagle | Structure | Rare | 4 | 1050 | 85 | 1.0 | 0.0 | 5 | ground | both | - | - |
| 0093 | Bunker | H | Beagle | Structure | Epic | 5 | 1344 | 72 | 0.9 | 0.0 | 5 | ground | both | - | - |
| 0094 | Buckshot | S | Beagle | Structure | Common | 3 | 756 | 106 | 1.12 | 0.0 | 5 | ground | both | - | - |
| 0045 | Neon Dachshund | O | Dachshund | Spawner | Common | 3 | 650 | 45 | 0.9 | 0.85 | 2 | air | both | Y/1.8 | - |
| 0041 | Volt Corgi | O | Corgi | Spawner | Rare | 4 | 750 | 55 | 0.9 | 0.85 | 2 | ground | both | Y/1.8 | - |
| 0095 | Howitzer | H | Corgi | Spawner | Epic | 5 | 960 | 47 | 0.81 | 0.75 | 2 | ground | both | Y/1.8 | - |
| 0096 | Tripwire | S | Corgi | Spawner | Common | 3 | 540 | 69 | 1.01 | 0.94 | 2 | ground | both | Y/1.8 | - |
| 0042 | Grid Schnauzer | O | Schnauzer | Structure | Rare | 5 | 1150 | 95 | 1.0 | 0.0 | 4 | ground | both | - | - |
| 0097 | Flakwall | H | Schnauzer | Structure | Epic | 6 | 1472 | 81 | 0.9 | 0.0 | 4 | ground | both | - | - |
| 0098 | Deadeye | S | Schnauzer | Structure | Common | 4 | 828 | 119 | 1.12 | 0.0 | 4 | ground | both | - | - |
| 0046 | Flux Pomeranian | O | Pomeranian | Support | Common | 2 | 700 | 40 | 0.9 | 0.85 | 3 | ground | both | - | - |
| 0047 | Rail Terrier | O | Terrier | Blaster | Common | 3 | 550 | 80 | 1.1 | 0.85 | 4 | ground | both | - | - |
| 0038 | Circuit Retriever | O | Retriever | Support | Epic | 6 | 1100 | 70 | 0.9 | 0.85 | 3 | ground | both | Y/1.8 | - |
| 0099 | Casemate | H | Retriever | Support | Legendary | 7 | 1408 | 60 | 0.81 | 0.75 | 3 | ground | both | Y/1.8 | - |
| 0100 | Shrapnel | S | Retriever | Support | Rare | 5 | 792 | 88 | 1.01 | 0.94 | 3 | ground | both | Y/1.8 | - |
| 0043 | Chrome Airedale | O | Airedale | Lancer | Rare | 5 | 1050 | 165 | 0.95 | 0.85 | 3 | ground | both | Y/1.8 | - |
| 0101 | Pillbox | H | Airedale | Lancer | Epic | 6 | 1344 | 140 | 0.85 | 0.75 | 3 | ground | both | Y/1.8 | - |
| 0102 | Hairtrigger | S | Airedale | Lancer | Common | 4 | 756 | 206 | 1.06 | 0.94 | 3 | ground | both | Y/1.8 | - |
| 0044 | Beacon Basset | O | Basset | Support | Rare | 4 | 900 | 55 | 0.9 | 0.85 | 3 | ground | both | - | - |
| 0103 | Stronghold | H | Basset | Support | Epic | 5 | 1152 | 47 | 0.81 | 0.75 | 3 | ground | both | - | - |
| 0104 | Snubnose | S | Basset | Support | Common | 3 | 648 | 69 | 1.01 | 0.94 | 3 | ground | both | - | - |
| 0048 | Pixel Pug | O | Pug | Spawner | Common | 2 | 550 | 40 | 0.9 | 0.85 | 2 | air | both | Y/1.8 | - |
| 0039 | Nova Shepherd | O | German Shepherd | Structure | Epic | 7 | 1450 | 125 | 1.0 | 0.0 | 4 | ground | both | Y/1.5 | - |
| 0105 | Emplacement | H | German Shepherd | Structure | Legendary | 8 | 1856 | 106 | 0.9 | 0.0 | 4 | ground | both | Y/1.5 | - |
| 0106 | Salvo | S | German Shepherd | Structure | Rare | 6 | 1044 | 156 | 1.12 | 0.0 | 4 | ground | both | Y/1.5 | - |

### 1.4 SPELLS (unchanged from canon -- keep the existing `spells` array)
| # | Spell | Faction | Rarity | Cost | CD | Effect | Radius | Dur | Dmg | Description |
|---|---|---|---|---|---|---|---|---|---|---|
| S001 | Boneshatter Freeze | Boneguard | Epic | 5 | 14 | freeze | 3.0 | 3.0 | 0 | Enemies in the area STOP (no move/attack) ~3s. Towers freeze too. |
| S002 | Tar Pour | Leashbreak | Rare | 4 | 12 | slow | 3.2 | 4.0 | 0 | Tar slick: -35% move + -35% attack speed to enemies in area ~4s. |
| S003 | Snare Trap | K9 | Rare | 3 | 13 | trap | 1.8 | 1.6 | 90 | Hidden trap arms, then roots + small dmg when crossed. Zone control. |
| S004 | Jolt | Zoomie | Common | 3 | 9 | zap | 2.4 | 0.5 | 130 | Instant AOE dmg + 0.5s stun. Kills swarms, resets attacks. |
| S005 | Strike | Neutral | Epic | 4 | 11 | strike | 2.6 | 0 | 320 | The fireball: medium AOE burst at a point. |

### 1.5 Card descriptions (the data rule)
Every card carries a one-line `desc` surfaced on the long-press popover + the shop + the NFT metadata. Originals keep their canon ability line. Variants read as a build of the parent line, e.g.:
- **Heavy:** *"Tombstone -- a plated Rottweiler yard enforcer, the bunkered build of Iron Rottweiler's line (Vanguard). Reinforced frame: soaks the first hit (-25% dmg taken 3s on deploy); ability radius +30% but fires slower."*
- **Street:** *"Knuckles -- a chromed-out Boxer yard enforcer, the stripped glass-cannon build of Balboa's line (Striker). +25% bite damage and executes targets under 35% HP -- but folds to one clean shot."*

The full 106-object drop-in for `data/cards.json` (with rig/nft/family/variant tags + per-variant ability text) lives in `design_roster.md` -> "MACHINE-READABLE CARD LIST". The data-expansion phase (Phase 2 below) merges it; the spells array stays as-is.

---

## 2. THE 10 PREMADE DECKS (8 meta + 2 wildcard, 11 cards each)

**Ground rules:** a deck is **exactly 11 cards, singleton** (no duplicate in one deck), drawn from the open 106-troop + 5-spell pool. **Open faction** -- any card is legal; running **6+ of one faction** lights that faction's **Crew Bonus** (Boneguard +4% tank HP / Zoomie +4% move / Leashbreak +1s debuff dur / K9 +4% turret-drone HP). Hand of 4 + next-card preview; cards cycle to the bottom on play; an 11-card deck cycles slower than 8, so cheap cards are the cycle lever. **Avg deck cost is the single biggest "feel" differentiator** and is printed live in the builder. Every deck's *"loses to"* line is a design feature -- it's where the counter web attaches; no deck is >~60% favored field-wide.

**Anti-air legality:** a unit hits a target only if `target.domain in attacker.targets`. Air units can only be hit by `targets:both` units + towers. Every meta deck below carries an anti-air answer; Sky Pack weaponizes the absence of one.

### The 8 meta decks
| # | Deck | Archetype | Avg cost | Win condition (1 line) |
|---|---|---|---|---|
| 1 | **CROWN MARCH** | Beatdown (Boneguard) | 6.2 | One unstoppable splash-tank push behind $BCARDD they can't answer in time. |
| 2 | **HYPER LOOP** | Cycle (Zoomie) | 3.3 | Death by a thousand cuts -- cheapest deck, fastest hand, never stop chipping. |
| 3 | **SIGNAL LOCKDOWN** | Control (Leashbreak) | 4.5 | Out-resource + outlast; slow/silence/disable every push, win the chip war with Rosco. |
| 4 | **TURRET TRAP** | Siege (K9) | 4.5 | Park static turrets and protect the engine while it chips from range. |
| 5 | **SKY PACK** | Air (Zoomie/K9) | 3.2 | Flood with AIR a ground-only army physically cannot hit; punish light anti-air. |
| 6 | **IRON WALL** | Heavy-Tank (Bone/Leash) | 6.6 | Build an *immortal* tank ball (double Vanguard + heal + shield) that doesn't die on the walk. |
| 7 | **DRONE FLOOD** | Swarm-Bait (K9/Zoomie) | 3.7 | Bait the one splash/spell, then overwhelm with constant spawned drones. |
| 8 | **HEX STORM** | Spell-heavy (cross) | 3.3 | Run all 5 spells; bait support out, melt every push, finish with Strike+Jolt while Byte Beagle chips. |

### The 2 wildcard decks (off-meta, high skill/variance -- each bends a rule the 8 metas obey)
| # | Deck | Archetype | Avg cost | Win condition (1 line) |
|---|---|---|---|---|
| 9 | **DECAPITATION** | Triple-Assassin Queen Dive (WC) | 5.0 | Ignore the lane war; run every Queen-target threat and assassinate the Queen before they build a defense. |
| 10 | **FOUR CROWNS** | Rainbow Midrange Toolbox (WC) | 4.6 | No single plan -- one signature tool from all 4 factions; out-value every matchup by always having the answer. |

### 2.1 Full deck lists
**1 CROWN MARCH (6.2):** $BCARDD(10) · Iron Rottweiler(9) · Stonejaw(7) · Warden Newfie(7) · Balboa(6) · Alloy Akita(6,AA) · Brick Bullmastiff(6) · Grit Bulldog(5) · Boneshatter Freeze(5) · Copper Chow(4) · Tank Pug(3,AA). *Beats Siege/single-target/slow Cycle; loses to Control + pure Cycle on the clock.*

**2 HYPER LOOP (3.3):** Neon Whippet(2) · Drift Sheltie(2) · Pixel Greyhound(3) · Turbo Jack(3) · Byte Beagle(3,AA,Q) · Glitch Basenji(3,AA) · Jolt(3) · Circuit Shiba(4) · Flash Saluki(4) · Bolt Corgi(4,AA) · Razor Vizsla(5,AA). *Beats Control/Siege; loses to Beatdown/Heavy-Tank + stacked splash.*

**3 SIGNAL LOCKDOWN (4.5):** Rosco(10,Q) · Noir Setter(6) · Synth Collie(5) · Pulse Border Collie(5) · Chill Samoyed(4) · Prism Poodle(4) · Signal Pointer(4) · Tar Pour(4) · Echo Dalmatian(3) · Static Sheba Inu(2) · Vibe Shih Tzu(2). *All Leashbreak units are range-3 `both` = naturally anti-air. Beats Beatdown/Heavy-Tank; loses to Cycle + Assassin Dive.*

**4 TURRET TRAP (4.5):** Crown Foxhound(11,Q) · Nova Shepherd(7) · Grid Schnauzer(5) · Chrome Airedale(5,AA) · Laser Beagle(4) · Beacon Basset(4) · Volt Corgi(4) · Rail Terrier(3) · Snare Trap(3) · Flux Pomeranian(2) · Pixel Pug(2). *Best stacked AA+splash in the game. Beats Air/Swarm; loses to heavy Beatdown + anti-structure rush.*

**5 SKY PACK (3.2):** Bolt Corgi(4,AA) · Flash Saluki(4) · Neon Dachshund(3) · Pixel Greyhound(3) · Ghost Spaniel(3) · Tank Pug(3,AA) · Jolt(3) · Pixel Pug(2) · Neon Whippet(2) · Drift Sheltie(2) · Aero Malinois(6, GROUND mixup). *Beats ground beatdown w/o AA + slow Control; loses to Siege + splash/AA + AOE spells.*

**6 IRON WALL (6.6):** $BCARDD(10) · Iron Rottweiler(9) · Granite Saint(8) · Rust Cane Corso(8) · Stonejaw(7) · Warden Newfie(7) · Alloy Akita(6,AA) · Holo Husky(5) · Pulse Border Collie(5) · Boneshatter Freeze(5) · Tank Pug(3,AA). *Beats Beatdown/Siege/Spell-heavy; loses to Cycle/Air on the clock + disable Control.*

**7 DRONE FLOOD (3.7):** Circuit Retriever(6) · Grid Schnauzer(5) · Chrome Airedale(5,AA) · Bolt Corgi(4) · Volt Corgi(4) · Beacon Basset(4) · Neon Dachshund(3) · Rail Terrier(3) · Snare Trap(3) · Flux Pomeranian(2) · Pixel Pug(2). *Beats Control/single-target Beatdown/Assassin; loses to Spell-heavy + Heavy-Tank.*

**8 HEX STORM (3.3) = 5 spells + 6 units:** Boneshatter Freeze(5) · Strike(4) · Tar Pour(4) · Jolt(3) · Snare Trap(3) · Signal Pointer(4,AA) · Byte Beagle(3,AA,Q) · Echo Dalmatian(3) · Glitch Basenji(3,AA) · Static Sheba Inu(2) · Vibe Shih Tzu(2). *Beats Swarm/Cycle/Control; loses to Heavy-Tank/Beatdown + Bridge-spam.*

**9 DECAPITATION (5.0):** Crown Foxhound(11,Q) · Jagged(11,Q) · Rosco(10,Q) · Circuit Shiba(4) · Byte Beagle(3,AA,Q) · Ghost Spaniel(3) · Jolt(3) · Snare Trap(3) · Tank Pug(3,AA) · Static Sheba Inu(2) · Drift Sheltie(2). *Three 10-11 win-cons = greedy by design. Beats Control/Siege; loses to Heavy-Tank/Swarm/defensive.*

**10 FOUR CROWNS (4.6):** Balboa(6) · Aero Malinois(6) · Noir Setter(6) · Chrome Airedale(5,AA) · Razor Vizsla(5,AA) · Grit Bulldog(5) · Prism Poodle(4) · Beacon Basset(4) · Strike(4) · Turbo Jack(3) · Glitch Basenji(3,AA). *One tool from each faction. Beats unfocused decks/misplays; loses to top-tier focused Cycle + Iron Wall.*

### 2.2 Counter-web check (the meta closes -- no deck dominates)
Core triangle: **Control > Beatdown > Siege > Cycle/Air > Control**, with Swarm / Spell / Air / Assassin as the tech spokes. Every deck beats ~2-3 and loses to ~2-3. Variant cards expand each archetype's depth (a Street striker for Hyper Loop's cheaper curve; a Heavy Vanguard for Iron Wall's wall) without breaking the web -- they're sidegrades on the same role.

---

## 3. DECK-BUILDER + UNLOCK FLOW

### 3.1 Builder rules (enforced)
- Deck = **exactly 11 cards, no duplicates.** Save blocked at 10 or 12; slot shows `9/11`.
- **Open faction** -- any *owned* card is legal; 6+ same-faction lights the **Crew Bonus** badge.
- Only **owned** cards are placeable; unowned render greyed with a lock + "Unlock via Play / Shop."
- **Soft linters (warn, never block):** (a) avg-cost meter with archetype read-out (Heavy/Midrange/Cycle); (b) **No anti-air** flag if 0 cards are `targets:both`; (c) **No win-con** flag if 0 cards are `queen_target` / Structure / Assassin. Players *can* save a "bad" deck -- the warnings teach.

### 3.2 Level 1 = one deck, one slot (the on-ramp)
- New account ships a **fixed Starter Collection** (~14 cards: Boneguard commons/rares + a couple cheap Zoomie/K9) and **one pre-built starter deck in Slot 1** (a Crown March-lite "Slow Roll").
- **Only Slot 1 unlocked at L1**, but it's editable from minute one within the owned collection. You literally cannot field 10 metas on day 1 -- you grow into them.

### 3.3 Unlocking cards + slots
- **Cards unlock two ways** (clean-gacha line, sec 4): **(1) Play** -- ladder wins, daily/cycle chests, and the escalating single-line Lucky Draw (capped cost, soft+hard pity, won cards removed from pool, odds shown pre-draw; premium draw currency one-way, **no cash-out**). **(2) Marketplace** -- buy/trade the NFT cards directly (separate legal track; utility, never marketed as investment).
- **Duplicates upgrade a card's level** (sec 4.2) rather than letting you run two in a deck.
- **Deck SLOTS unlock on player level:** Slot 1 @L1, Slot 2 @L3, Slot 3 @L6, Slot 4 @L9, Slot 5 @L12, up to **8 slots.**

### 3.4 Screens
1. **Collection** -- grid of all 111 cards; owned = full art, unowned = locked silhouette + "how to get." Filters: faction, rarity, cost, role, owned/unowned, anti-air, win-con, **variant (O/H/S)**, family. Tap = full stats + ability + which suggested decks use it.
2. **Deck Slots carousel** -- saved decks as cards (name, avg-cost dial, faction badge, archetype tag). Buttons: New / Edit / Copy / Rename / Delete / Set Active.
3. **Deck Edit** -- top: 11 slots (tap to remove). Bottom: filtered Collection tray (drag/tap to add). Live HUD: `cards 11/11`, avg-cost meter + archetype label, anti-air check, win-con check, Crew Bonus badge. Save / Discard.
4. **Suggested Decks** -- the **10 designed decks ship as one-tap templates.** "Copy to slot" auto-fills owned cards and flags the rest: *"Need 3 more -- 2 in Shop, 1 from Drone Flood reward track,"* with deep-link CTAs. **This is the funnel:** the meta list itself drives card-acquisition + (clean) monetization.
5. **Battle deck selector** -- pre-match, pick any *filled* slot; last-used remembered; quick-swap without leaving matchmaking.

### 3.5 Save / share
- Decks save to the player profile (**Supabase = source of truth**) keyed to an owned-card snapshot; trade a card away and that slot shows `incomplete` until refilled.
- **Deck codes:** every deck (incl. the 10 templates) exports a short shareable import string for creators.

---

## 4. ECONOMY -- RARITY/GEM UPGRADE + SHOP + GACHA (legal-gated)

### 4.1 Currency spine (no new currencies)
| Currency | Type | Earn | Spend | Fiat-buyable |
|---|---|---|---|---|
| **Fuel** | soft | wins, dailies, chests, Gate clears | card upgrades (the only real sink) | NO (anti-P2W throttle) |
| **Gears** | mid/season | pass track, events | seasonal/expansion cards, skins | via pass only |
| **Gems** | hard | Stripe SKU, $BCARDD on-ramp (later), slow drip | copies, Fuel, chests, skips, pass, draws | **YES (the on-ramp)** |
| **Scrap Tokens** (C/R/E/L/M) | crafting | Chop Shop, dupes of maxed cards, chests, pass | buy ANY same-rarity card, or sub a missing dupe 1:1 | indirect (gems->chests) |

**Scrap-value ladder (single internal pricing unit):** Common 1 / Rare 5 / Epic 25 / Legendary 250 / Mythic 1000 common-equivalents. **Deliberately-bad direct rate:** `1 gem = 20 Fuel` -- the worst value in the game, so a whale *can* brute-force but everyone else is steered to pass/chests (the fog lever).

### 4.2 Card upgrade per rarity (copies-to-level, the grind engine)
Max level 10, curve `1 + 0.10*(L-1)` (HP+DMG only -> a maxed Common never beats a base Mythic; the no-P2W floor). Each L->L+1 = **N matching-rarity copies + a Fuel payment**, exponential + back-loaded (~85% of lifetime cost in the top 3 bands). A matching-rarity **Scrap Token subs a missing copy 1:1.**
| Rarity | Copies per band (L2..L10) | Fuel per band | To L10 | Feel |
|---|---|---|---|---|
| Common | 2,4,6,10,20,40,80,150,300 | 5..4k | ~612 / ~7.9k | days |
| Rare | 1,2,4,8,16,30,60,120,250 | 50..30k | ~491 / ~60k | weeks |
| Epic | 1,1,2,4,8,16,30,60,120 | 0.4k..120k | ~242 / ~240k | 1-2 mo |
| Legendary | 1,-,1,-,2,-,4,-,8 (dupe-drip) | up to 150k/band | ~16 / ~250k | months |
| Mythic | 1,-,-,1,-,-,1,-,1 | up to 250k/band | ~4 / ~430k | the long chase |

*Note: the expanded set has 10 Legendary / 4 Mythic, so the dupe-drip pool is wider than the original single-Legendary canon -- the curve per card is unchanged.*

### 4.3 Gem upgrades -- the "finish it now" shortcut (Gems = the Stripe product)
- **4.3a Deterministic Top-Off (clean, ships with the deterministic shop):** buy the EXACT missing copies for a level off scrap-ladder x2 (gems/copy: C 2 / R 10 / E 50 / L 500 / M 2,000) + (band Fuel / 20). One tap, no random, always in shop. Legal lane **A**.
- **4.3b Indirect (chests + draw):** gems -> chests / Lucky Draw yield copies + Scrap at a better gems-per-copy rate but with variance. The bad direct rate is what makes these *feel* like value (intentional fog).
- **Mirror:** Ranked Standard normalizes every card to a fixed level -> gems buy **zero ranked win-rate**; they buy speed-to-collection + flex + ladder tempo. Never sells ranked power.

### 4.4 The Shop (everything in one place)
| Surface | Sells | Currency | Status |
|---|---|---|---|
| **Daily Lot** | free gift (slot 1, login magnet) + 5 rotating cards/cosmetic | Fuel/Scrap/gems | LIVE |
| **Card Shop** | EXACT cards, deterministic (Scrap: C1/R5/E25/L250/M1000) | Scrap/gems | LIVE |
| **Upgrade Top-Off** | missing copies + Fuel to finish a level NOW | gems | LIVE |
| **Chests** | odds-disclosed packs (Scrap Crate 40 -> Mythic Vault 2000) | gems | LIVE w/ odds |
| **Lucky Draw** | escalating draw for featured Legendary/Mythic | gems | **DARK STUB -- Gate 3** |
| **Garage consumables** | Nitro/Spells/Potions (PvE-only), Decals | gems/Fuel | LIVE (PvE-only) |
| **Cosmetics** | rig skins, arena themes, emotes, dealer skins | gems | LIVE (safest revenue) |
| **Passes** | Master $14.99/mo + AK Crew $4.99/season | Stripe | LIVE (operator-lock pending) |
| **Bundles** | Starter $2.99, Revival $1.99 (streak-triggered) | Stripe | LIVE |

**Card Shop rotation-with-guarantee:** every eligible card in your arena appears at least once per ~90-day window -- scarcity becomes a calendar players check daily. This deterministic surface is the anti-gacha pressure valve + lowest loot-box-law risk; it ships FIRST.

### 4.5 The Lucky Draw (legal-clean, in-game-value ONLY, GATED STUB)
Escalating single-line, **capped 10-pull line**, one featured grand prize per banner, **hard pity @ pull 10**, **soft-pity ramp pulls 8-10**, every pull gives something, won featured card removed, progress carries across rotation.
| Banner | Pull cost curve (gems 1->10) | To hard pity | ~USD | Hard pity |
|---|---|---|---|---|
| Legendary | 150,180,220,260,300,360,430,520,620,740 | ~3,780 | ~$30-47 | featured Legendary @10 |
| Mythic | 400,500,620,760,940,1160,1430,1760,2170,2670 | ~12,410 | ~$95-155 | featured Mythic @10 |

**Disclosed odds (pre-purchase, non-negotiable):** Mythic banner base = featured Mythic 1% / off-banner Legendary 4% / Epic 15% / Rare 35% / Common 45%. Legendary banner = featured Legendary 4% / Epic 18% / Rare 38% / Common 40%. Plain-language gem->draw math + "items have no cash value, this is not gambling" label + spend reminders.

**Why legal-clean (Lane A) + the one rule:** in-game value ONLY (no cash-out / no publisher resale / no withdrawal = the "no thing of value" defense). A free earn path exists (chests/Gates/Card Shop) so the draw is never the only path. **THE WRINKLE:** AK cards are also $BCARDD/Solana NFTs -- a paid draw whose prize has resale value edges toward gambling. **LOCKED SAFE PLAY: the Lucky Draw outputs IN-GAME, non-tradable card instances ONLY.** The tradable NFT mint is a SEPARATE deterministic track (Tensor/Magic Eden), **never a draw output.** **THE ONE RULE NEVER BROKEN: never sell a paid draw whose prize is cashable for real money.** (Sweeps = free entry + cashable prize = B-CARDD BET blackjack, a SEPARATE Lane-B product, not in this shop.)

**Gate status:** Lucky Draw stays a dark code stub (schema + UI + odds engine present, purchase endpoint disabled, banner hidden) until **Legal Gate 3 (loot-box sign-off) + PACK_RIP A/B/C model** clears. Geofence paid random packs where required (BE/NL historically; flag WA/MN/HI + US-minors).

### 4.6 Data backbone (reuse + deltas)
Reuses `verify-arcade-purchase` edge fn + `game_currencies`/`game_passes`/`arcade_purchases`. Deltas: `shop_products.kind='draw'` + mandatory `odds` jsonb for draw/chest; `player_currencies` (fuel/gears/gems/scrap_*); NEW `draw_banners` (featured_card, pool, pull_cost_curve, soft/hard pity, active=FALSE, legal_gate_cleared=FALSE); NEW `player_draw_progress` (pulls_done, owned_grand carry-over); `transactions` (idempotent stripe_event_id, server-side write only -- client never self-grants).

---

## 5. PHASED BUILD ROADMAP
**Sequencing law:** static JS only (no npm/bundler -- phone-proot SIGSEGVs), tested via `python3 -m http.server`, deployed via the wrangler-free `cf_pages_direct_upload.py` (**verify the LIVE edge, never the tool exit code** -- per `reference_cf_pages_deploy_from_proot`). Supabase = source of truth; Stripe = the one hard-currency choke. Deterministic surfaces ship before any random one. The Lucky Draw stays dark until legal Gate 3.

| Phase | Name | Ships | Gate |
|---|---|---|---|
| **P1** | **Deck Builder UI** | Collection grid (53 cards now), 11-card slot editor, avg-cost/AA/win-con linters, 10 templates as one-tap copies, deck-codes. Wire the 10 decks into `data/decks.json` + `game/canon.js`, replacing the 4 stub decks. Save to Supabase profile. | none -- ship on `alley-kingz.pages.dev` now |
| **P2** | **Card data expansion (48 -> 106)** | Merge the `design_roster.md` machine-readable list into `data/cards.json` via the deterministic stat-tilt generator (Heavy/Street math, family+variant tags, rig/nft fields). Add variant filters to Collection. Author/confirm all 106 descriptions. Verify counts (4/10/29/29/34). | none |
| **P3** | **Art generation cron** | Feed `data/card_art_manifest.json` (106 prompts, this artifact) to a Leonardo/HuggingFace batch cron -> `game/assets/cards/<slug>.png`. Free-first: Leonardo free ~10-15/day = ~7-8 days for 58 new (or a one-shot paid tier ~$2-3). Idempotent + batchable; skip slugs already painted. Wire art into Collection/Deck cards. | none (free-first) |
| **P4** | **Shop + upgrades (deterministic ONLY)** | Currencies (Fuel/Gears/Gems/Scrap), copies-to-level upgrade sink, Daily Lot + Card Shop + Top-Off + chests-with-odds + cosmetics + bundles. Lucky Draw built as a **dark stub** (no purchase endpoint). | none beyond standard consumer terms |
| **P5** | **Stripe wire** | Gems = the single Stripe product; Starter $2.99 + Revival $1.99 bundles; then Master $14.99/mo + Crew $4.99/season passes. Server-side idempotent `transactions`. | operator: pass-model lock + legal contact assigned |
| **P6** | **Push to everlightventures.io** | Promote the proven `alley-kingz.pages.dev` build to the public site funnel (lead capture via `vantaris/supabase/functions/notify-lead/`); SEO pass; marketplace + Lucky Draw remain gated. | coin-first sequencing + Legal Gate 1/3 for any on-chain/draw surface |

**Hard gates that DON'T move:** Lucky Draw live = Legal Gate 3 + PACK_RIP signed. NFT mint = deterministic-only, never a draw output, Gates 1-3. Off-ramp = Gate 1, default OFF. Every paid surface = Stripe -> Gems choke point.

---

## 6. THE GRITTY TV-MA ART DIRECTION GUIDE

### 6.1 North star (operator-locked)
**GRITTY, TV-MA, street / "Fast Boyz" energy.** Cyberpunk dog crews in Twisted-Metal war-rigs, gangster/street callsigns, scarred coats, neon-on-grime. Adult and edgy -- **NOT** kiddish, **NOT** Disney, **NOT** chibi. Every variant reads like a different chop-shop build of the same dog line, never a recolor.

### 6.2 Per-faction visual kit (the chop-shop language)
| Faction | Rig | Palette | Turf |
|---|---|---|---|
| **Boneguard Crew** | armored bruiser war-truck, steel ram-plow, riveted plate, matte-black + tarnished gold, exhaust stacks | rust / gunmetal / oxblood / dirty gold | smoke-choked scrapyard fight-pit |
| **Zoomie Syndicate** | low-slung neon street-racer, nitrous bottles, exposed turbo, chopped chassis, light-trail underglow | electric cyan / hot magenta / neon violet on wet asphalt | rain-slick neon-strip back-alley at night |
| **Leashbreak Tactix** | matte recon/hacker van, antennae, signal-jammers, cracked holo-screens, EMP coils | cold teal / sodium-amber / static grey / glitch-green | industrial signal-yard of dead screens + cable |
| **K9 Circuitry** | bristling gun-rig technical, mounted auto-turrets, belt-fed ammo, artillery racks, sensor masts | hazard-orange / gunmetal / circuit-cyan / scorched steel | fortified weapons-depot dockyard |

### 6.3 Role -> pose, Rarity -> frame, Variant -> build
- **Role poses:** Vanguard (planted tank, soaking fire) · Striker (mid-lunge brawler) · Lancer (leveling an energy-lance) · Skirmisher (airborne mid-dash) · Support (projecting an aura/field) · Spawner (flinging drones) · Hacker (jacking an intrusion-spike, code-glyphs) · Controller (slowing shockwave) · Structure (dug-in turret-rig) · Blaster (shouldering a rail-cannon) · Assassin (mid-teleport, blade-claws, after-images).
- **Rarity frames:** Common = worn steel, minimal aura · Rare = chrome + faint cyan aura · Epic = gunmetal + violet aura + embers · Legendary = gold-filigree + radiant aura + light-motes · Mythic = molten-gold/black crown-motif frame, blinding divine aura, 1-of-1 centerpiece.
- **Variant builds:** ORIGINAL = the canon, definitive look. HEAVY = bunkered, up-armored, bulked, heavier plating, bigger/slower, scarred from soaking hits. STREET = stripped glass-cannon, panels torn off, chromed/lightened, exposed engine, lean/twitchy, all teeth no armor.
- **Build adjectives** (folded into variant prompts for variety): scarred / chromed-out / plated / oil-slick / war-torn / neon-tagged / junkyard-welded / blood-streaked / rust-armored / razor-collared / blast-shielded / wire-thin / battle-scabbed / strung-out.

### 6.4 The locked style suffix (every prompt ends with this)
> *GRITTY TV-MA, adult and edgy, cyberpunk gangland 'Fast Boyz' energy, Twisted-Metal war-rig vibe, scarred coat and battle-worn gear, neon-on-grime, cinematic dramatic rim-lighting, volumetric haze, ultra-detailed character splash-art for a collectible trading card, vertical 3:4 portrait composition, anthropomorphic but believable canine anatomy. NOT cute, NOT cartoonish, NOT Disney, NOT kiddish.*

**Global negative prompt:** *cute, chibi, kawaii, disney, pixar, childish, pastel, clean, glossy toy, watermark, text, signature, logo, blurry, low-detail, extra limbs, deformed anatomy, mutated paws.*

### 6.5 Generation spec
- **Engine:** Leonardo (Phoenix / Vision XL), **832x1216** (3:4 card portrait), guidance ~7, 1 image per slug -> `game/assets/cards/<slug>.png`.
- **Manifest:** `data/card_art_manifest.json` -- 106 objects `{cardNumber, slug, name, breed, faction, role, rarity, variant, is_new, art_path, prompt, negative_prompt}`. `is_new=true` = the 58 new variant cards (paint these first); `is_new=false` = the 48 originals (re-paint to unify the style).
- **Cron:** idempotent (skip painted slugs), batchable to fit the Leonardo free daily cap, free-first per the Golden Rule. Same pipeline shape as `art/generate_world_maps.py`.
- **Consistency rule:** one model + one style suffix + one negative across all 106 = a coherent set where Heavy/Street/Original of the same dog clearly read as the same character in three builds.

---

## 7. RECONCILIATION NOTES (what changed vs canon)
- **48 originals: UNTOUCHED.** Stats, abilities, rig, ids verbatim. Variants are additive only.
- **"110-card set" = 106 character cards + 5 spells (111 NFTs).** The round "110" is the marketing headline; the true count is 106 troops + 5 spells. Rarity now 4/10/29/29/34 (was 4/1/9/20/14) because Heavy promotes 17 cards up a tier and Street demotes 17 down -- the pyramid the economy curve was tuned for.
- **Decks: the 4 stub 8-card decks in `data/decks.json` are REPLACED** by the 10 full 11-card decks here.
- **No new mechanics.** Variants reuse every existing targeting/splash/queen rule; the Storm Clock, convoy, District Gates, and two-tier boss spine from `ALLEY_KINGZ_MASTER_STRATEGY.md` are unchanged.
- **Legal posture: Option A confirmed in spirit** -- deterministic shop ships first; Lucky Draw is a dark stub; NFT is deterministic-only; never sell a cashable paid draw.

---
*Synthesized 2026-06-07 by the Creative Director. Source forks (`design_roster`, `design_decks`, `design_economy`, `research_economy`, `research_gacha_meta`) remain the deep reference. Companion: `data/card_art_manifest.json`. Next: P1 deck-builder UI on `alley-kingz.pages.dev` (no operator gate), then P2 data merge, then the P3 art cron.*
