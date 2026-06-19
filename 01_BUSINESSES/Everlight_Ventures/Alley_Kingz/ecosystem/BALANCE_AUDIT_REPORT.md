# ALLEY KINGZ -- BALANCE AUDIT REPORT
**Date:** 2026-06-12 | **Auditor:** Wave-6 balance pass (WAVE6_RPG_DEPTH_SPEC section 2) | **Scope:** 106 troops + 5 spells in `game/canon.js`, audited against the power-budget formula in `data/_balance_pass.py` and the live engine rules in `game/engine.js` (AK-FEEL range bands, AK-SYNERGY, AK-ATTRS clamps, air/ground targeting). Analysis only -- ZERO stat changes applied.

---

## EXECUTIVE SUMMARY (the one page that matters)

**The roster is structurally sound but the rarity ladder is upside down on raw stats, and the Street variants are the strongest per-energy cards in the game.** The 48 originals sit on the budget curve almost perfectly. The 58 Heavy/Street variants match their spec multipliers EXACTLY (Heavy hp x1.28 / dmg x0.85 / aspd x0.90; Street hp x0.72 / dmg x1.25 / aspd x1.12) -- the implementation is clean. The problem is the spec itself: Street's "-1 cost, -1 rarity" stacks on top of a power-neutral stat trade, so Street commons deliver ~60% more combat power per energy than the roster average, while Heavy structures deliver the least. Real DPS = damage x attack_speed (engine `atkInterval = 1/atkSpd`).

### Verdict by axis

| Axis | Verdict | One-line evidence |
|---|---|---|
| 1. Cost curve (stat-per-cost) | **NEEDS TUNING** | Power-per-energy: cost-2 Street cards hit 148 vs combat-role mean 92.6; HP curve is clean (avg 596 at c2 -> 2123 at c8) but DPS-per-cost falls off a cliff above cost 6. |
| 2. Rarity fairness | **NEEDS TUNING** | Inverted: Common 90.4 power/energy, Rare 80.8, Epic 71.4, Legendary 68.4, Mythic 73.1. Higher rarity buys LESS stat value; the premium is utility only (queen_target, splash, abilities). |
| 3. Mythic premium | **NEEDS TUNING** | $BCARDD (Mythic, c10, 2850 HP) is out-bulked by Tombstone (Legendary, c10, 3648 HP) and even by Epic Anvil/Slab (c9, 3392 HP). The flagship chase card loses its own stat lane. Jagged/Crown Foxhound pay cost 11 for damage the 230 clamp already capped at cost ~9. |
| 4. Role balance | **FAIR** | All 11 archetype identities hold (tanks slow+bulky, flankers fast+fragile, supports low-DPS). Thin classes: Assassin n=2, Blaster n=2 -- fine for now, expand in the taxonomy wave. |
| 5. Counter web (air/ground + range) | **FAIR, one flag** | The triangle works (wall > flank > siege > wall; control > swarm). FLAG: Boneguard has only 7/26 anti-air cards while 5 Street skirmishers are AIR-domain melee that 35 ground-only cards can never hit. |
| 6. Spells | **FAIR, one flag** | CC spells (Freeze 5e, Tar 4e, Snare 3e) are priced right. Damage spells kill NOTHING real: min troop HP is 504, Strike does 320 (kills only 300-HP spawned tokens), Jolt 130 is pure chip+stun. The HEX STORM archetype leans on damage that is not there. |
| 7. Faction parity | **WATCH** | Power/energy by faction: Zoomie 93.7, Boneguard 81.6, Leashbreak 74.0, K9 70.5. K9/Leashbreak carry utility (anti-air, control) the stat math undercounts, but a 33% raw gap is worth one playtest cycle. |
| 8. Personalization safety (sec 7) | **FAIR** | AK-ATTRS Garage Tuning clamps (agi/aspd <= x1.25, def/spdef >= x0.80) bound any build to ~+25% on one axis -- per-card builds diverge accounts without breaking the curve. But tuning COMPOUNDS on already-over-budget Street cards; fix the base curve first. |

### Top 5 most-broken cards (suggested corrections -- NOT applied)

| # | Card(s) | What is broken | Suggested correction |
|---|---|---|---|
| 1 | **Nitro + Spike** (Street Skirmisher, Common, cost 2) | 148 power/energy, +60% over combat mean; AIR domain at melee range -- 35 ground-only cards can never touch them; 174 DPS at 2 energy. | Cost 2 -> 3, OR hp 504 -> 420 and dmg 119 -> 105. Re-examine air domain on Street melee skirmishers. |
| 2 | **Knuckles + Flatline** (Street Striker, Rare, cost 5) | 258 DPS -- the highest in the game, above both cost-11 Mythic assassins, at 4 engine energy with 1080 HP. | dmg 219 -> 185 (DPS 258 -> 218, back under the Assassin ceiling), or cost 5 -> 6. |
| 3 | **Tombstone** (Heavy Vanguard, Legendary, cost 10) | 3648 HP smashes the roster HP law (2850 cap in `_balance_pass.py`) and out-tanks the Mythic king $BCARDD at equal cost. Anvil/Slab (Epic c9, 3392 HP) have the same sin. | Apply the 2850 clamp to variants too (Tombstone 3648 -> 2850, Anvil/Slab 3392 -> 2850), or raise the clamp to 3000 and give $BCARDD a compensating identity stat. |
| 4 | **Switchblade + Carrier + Hotwire** (Street Commons, cost 3) | ~200 DPS at 3 energy; 110-138 power/energy. The cheapest cycle slots become auto-includes, killing deck diversity (anti-personalization). | Street dmg mult 1.25 -> 1.15 for Common-tier landings, or no cost reduction when the parent already costs <= 4. |
| 5 | **Emplacement + Flakwall** (Heavy Structures, K9) | 60-66 power/energy, the worst combat slots in the roster -- the Heavy tax (dmg x0.85, aspd x0.90) hits static turrets twice because they cannot trade mobility for bulk. | For Structures only: Heavy dmg mult 0.85 -> 0.95, or cost -1. |

**Bottom line:** ship one variant-tuning pass (Street -10% dmg at Common/cheap landings, Heavy HP clamp at 2850, Structure-Heavy relief) and the 106-card set is tournament-fair. The originals need nothing. Rarity stays stat-inverted BY DESIGN only if Mythics get their utility premium protected -- right now Tombstone breaks that contract.

---
---

## APPENDIX -- METHOD + FULL TABLES

### A. Method and ground truth

- **Source:** `game/canon.js` CANON_CARDS (106 troops, verified via node export) + CANON_SPELLS (5). Engine truths from `game/engine.js`: `atkInterval(u) = 1/atkSpd` so **DPS = damage x attack_speed**; engine energy cost = `energyCost(canon) = round(2 + (canon-2)*7/9)` compressing canon 2..11 into energy 2..9; AK-FEEL range bands per role; melee (canon range 1) targets `ground` only, ranged (range >= 2) targets `both`; AK-ATTRS tuning clamps agi/aspd [1.0, 1.25], def/spdef [0.80, 1.0]; spawn tokens are 300 HP / 40 dmg (engine `spawnDrone`).
- **Budget formula** (`data/_balance_pass.py`): `stat = (stat_at_cost5 + (cost-5) * stat_per_cost) * rarity_mult`, HP rounded to 50 and clamped [450, 2850], dmg rounded to 5 and clamped [35, 230]. Rarity mult: Common 0.92, Rare 1.00, Epic 1.08, Legendary 1.14, Mythic 1.20.
- **Power proxy:** `sqrt(HP x DPS)` -- the effective-power geomean (a card that doubles HP or doubles DPS gets x1.41, doubling both gets x2). Divided by engine energy for value. Utility roles (Support/Spawner/Hacker/Controller) under-read on this proxy because heal/spawn/silence value is not stat-visible; combat-role comparisons are the reliable ones.
- **Caveat:** `_balance_pass.py` still asserts `len(cards) == 48` -- it predates the 106-card expansion and will refuse to run on today's SoT. Process flag: the budget formula file is STALE relative to the roster it governs. The expansion's intended multipliers live in `ALLEY_KINGZ_CARD_EXPANSION.md` section 1.1 and were verified faithful (measured Heavy x1.280/x0.852/x0.900, Street x0.720/x1.251/x1.124 -- exact).

### B. Effective DPS + stat-per-cost by role

| Role | n | avg DPS | DPS/canon-cost | HP/canon-cost | avg cost | Identity check |
|---|---|---|---|---|---|---|
| Vanguard | 12 | 103.8 | 13.1 | 330.5 | 8.17 | OK -- max HP/cost, min DPS/cost. The tank law holds. |
| Striker | 14 | 169.0 | 36.2 | 269.4 | 5.00 | OK -- bruiser midline. |
| Lancer | 12 | 168.7 | 36.7 | 216.2 | 5.00 | OK -- highest sustained DPS/cost with reach. |
| Skirmisher | 10 | 133.6 | 47.7 | 227.8 | 3.20 | FLAG -- best DPS/cost in the game (Street variants drag it up). |
| Assassin | 2 | 253.0 | 23.0 | 172.7 | 11.00 | OK -- burst kings, worst HP/cost. Thin class (n=2). |
| Blaster | 2 | 88.0 | 29.3 | 183.3 | 3.00 | OK. Thin class (n=2). |
| Hacker | 7 | 80.2 | 24.9 | 220.5 | 3.71 | OK -- pays stats for silence/disable. |
| Controller | 8 | 101.6 | 20.8 | 198.4 | 5.38 | OK. |
| Support | 22 | 55.5 | 13.4 | 219.9 | 4.64 | OK -- lowest DPS lane; value is heal/buff. Biggest role (n=22). |
| Spawner | 8 | 48.9 | 14.7 | 201.3 | 3.62 | OK -- token value (300 HP / 40 dmg drones) not in stats. |
| Structure | 9 | 107.2 | 21.9 | 231.0 | 5.33 | OK base; Heavy variants under-budget (see sec E). |

Speed-tier discipline (engine bins Static/Slow/Medium/Fast/VeryFast) is clean: all 9 static cards are Structures, all Slow cards are Vanguards, all VeryFast are Skirmishers. Card text reads true to behavior.

### C. Cost curve

| Canon cost | n | engine energy | avg HP | avg DPS |
|---|---|---|---|---|
| 2 | 9 | 2 | 596 | 82.5 |
| 3 | 18 | 3 | 682 | 103.7 |
| 4 | 20 | 4 | 869 | 113.0 |
| 5 | 21 | 4 | 1072 | 113.3 |
| 6 | 15 | 5 | 1337 | 109.6 |
| 7 | 10 | 6 | 1728 | 109.5 |
| 8 | 5 | 7 | 2123 | 96.9 |
| 9 | 3 | 7 | 3211 | 84.5 |
| 10 | 3 | 8 | 2699 | 123.6 |
| 11 | 2 | 9 | 1900 | 253.0 |

HP scales smoothly with cost; DPS plateaus at ~113 from cost 4-7 then splits into the two top-end identities (cost 9-10 = walls, cost 11 = burst). The flat DPS band means cost above 5 buys HP and utility, not damage -- intentional and healthy, but it is WHY cheap Street DPS cards over-perform: they buy damage at the only point on the curve where damage is cheap.

### D. Rarity fairness

| Rarity | n | avg cost | power/canon-cost | power/engine-energy | intended mult | delivered (hp x / dmg x vs Rare baseline) |
|---|---|---|---|---|---|---|
| Common | 34 | 3.35 | 88.4 | 90.4 | x0.92 | hp x0.84 / dmg x1.19 |
| Rare | 29 | 4.83 | 73.3 | 80.8 | x1.00 | hp x0.95 / dmg x1.15 |
| Epic | 29 | 5.83 | 59.4 | 71.4 | x1.08 | hp x1.16 / dmg x0.87 |
| Legendary | 10 | 7.10 | 57.9 | 68.4 | x1.14 | hp x1.28 / dmg x0.88 |
| Mythic | 4 | 10.50 | 59.2 | 73.1 | x1.20 | hp x1.15 / dmg x0.97 |

Two findings:
1. **The ladder is inverted on raw stats.** A Common delivers ~32% more stat power per energy than a Legendary. The original 48 were inverted only mildly (Common 81.0 vs Legendary 76.8); the variants blew it open (variant Common 93.5 vs variant Legendary 55.8) because Street pushes power DOWN-rarity and Heavy pushes cost UP-rarity.
2. **The intended rarity multiplier is not what ships.** Commons were budgeted at x0.92 damage but deliver x1.19 (Street landings); Legendaries budgeted x1.14 damage deliver x0.88. The BALANCE_NOTES claim "no card is strictly better than another at the same cost + role" no longer survives the variant layer: Knuckles (Rare, c5, 1080 HP, 258 DPS) strictly dominates several Epic strikers on stats.

**Is a Mythic always worth its cost premium? NO, not on stats -- and currently not on identity either.** The 4 Mythics rank mid-pack on power/energy (73.1). Their real premium is utility: all 4 are queen_target (the alternate win-con), $BCARDD and Crown Foxhound splash, and they anchor the ALPHA PACK / BIG DOG synergy combos. That contract is acceptable -- IF no lower-rarity card invades their lane. Tombstone (Legendary) out-tanking $BCARDD at equal cost, and Knuckles (Rare) out-DPSing Jagged (c11), both break it. The 230-damage clamp also silently ate Jagged/Crown Foxhound's cost-11 budget: the formula wanted 376 raw damage, the clamp pays them 230 -- cost-9 stats at cost-11 price, with queen access as the (unpriced) difference.

### E. Outliers >15% off the budget curve

58 of 106 cards sit >15% off the `_balance_pass.py` curve on HP or DPS -- but ALL 58 are the Heavy/Street variants, and every one matches the expansion spec multipliers exactly. The 48 originals are ALL within rounding of the curve (largest original deviation < 3%). So this is one systematic finding, not 58 random ones:

- **Street family (29 cards), pattern: HP -14 to -23%, DPS +60 to +79% vs the curve at their printed cost+rarity.** The stat trade alone is power-neutral (sqrt(0.72 x 1.40) = 1.00) -- the over-budget comes from ALSO getting -1 cost and -1 rarity. Worst offenders (power/engine-energy, combat mean 92.6): Nitro 148, Spike 148, Switchblade 138, Knuckles 132, Flatline 132, Carrier 126, Switch 114, Ricochet 111, Hotwire 110 (also AIR), Lugnut 109, Hairtrigger 108, Razorgums (a 2052-HP "Vanguard" with Striker DPS -- identity drift).
- **Heavy family (29 cards), pattern: HP +8 to +28%, DPS -30 to -38%.** The stat trade is power-NEGATIVE (sqrt(1.28 x 0.77) = 0.99) and they ALSO pay +1 cost and +1 rarity. Mildly under-budget across the board; Structures hit worst: Emplacement 60.1, Flakwall 65.5, Bunker 67, Anvil/Slab 70.8, Tombstone 68.8 (under-budget on value EVEN while breaking the HP ceiling -- it pays 8 energy for a stat line the curve prices at ~7).
- **Clamp saturation (8 cards):** $BCARDD, Stonejaw, Iron Rottweiler, Jagged, Crown Foxhound, Tombstone, Anvil, Slab all wanted more raw budget than the [2850 HP / 230 dmg] clamps allow. The clamps protect the engine (computeBulk collision mass, token interactions) -- the variants ignored the HP clamp, the originals respect it. Pick one law and enforce it everywhere.

Suggested global corrections (NOT applied): Street = no cost reduction when parent cost <= 4, dmg mult 1.25 -> 1.15 on Common landings. Heavy = enforce the 2850 HP clamp, Structures get dmg mult 0.95. Then re-run a 106-aware `_balance_pass.py` (fix the 48-card assert) so the formula file and the roster agree again.

### F. Who counters who (role/class level, AK-FEEL bands)

Engine engagement bands: Assassin 1.0 / Vanguard 1.2 / Skirmisher 1.2 (melee) / Striker 1.6 / Lancer-Support-Spawner 3.5-4.5 / Controller 4.5 / Hacker 5.0 / Blaster 5.5 / Structure 5.5-6.5 tiles. Melee (canon range 1) cannot target air; all 71 ranged cards are anti-air. Towers: Pack Guard 1400 HP / Alpha Den 2600 HP, range 6-6.5.

Read: ROW counters COLUMN (+ = favored, - = countered, o = even).

| vs -> | WALL (Vanguard) | BRUISER (Striker) | LANCE (Lancer) | FLANK (Skirm/Assassin) | SIEGE (Blaster/Structure) | CONTROL (Hacker/Ctrl) | BACKLINE (Supp/Spawner) | AIR (17 flyers) |
|---|---|---|---|---|---|---|---|---|
| **WALL** | o | + | o | + (melee divers bounce off 2300+ HP) | - (kited at 5.5-6.5 vs 1.2 band) | - (slow/freeze ruins the slow walk) | + | **-- (9 of 12 melee, cannot target air)** |
| **BRUISER** | - | o | + (closes the 3.5 gap fast) | + | + | o | + | - (7 of 14 melee) |
| **LANCE** | + (pierce + reach 3.5-4.5 outdamages the wall) | - | o | - (dived before the lance lines up) | o | o | + (pierce shreds lines) | + (ranged, anti-air) |
| **FLANK** | - | - | + | o | + (1.85-2.35 tiles/s crosses the kite gap) | + (dives the 4.5-5.0 band) | + | o (5 Street flyers ARE flank) |
| **SIEGE** | + (range 5.5-6.5 vs band 1.2, full kite) | + | o | - | o | - (disable_tower/silence shuts the turret) | + (outranges 3.5) | + (all anti-air) |
| **CONTROL** | + (slow/freeze the slow walk) | o | o | - (too fast to lock before contact) | + (silence/disable) | o | o | + (range 3+, anti-air) |
| **BACKLINE** | - | - | - | -- (the prime dive target) | - | o | o | o (most are ranged anti-air) |
| **AIR** | ++ (free hits on 35 ground-only melee) | + | - | o | - (every siege card is anti-air) | - | o | o |

The Clash triangle holds: wall-beatdown > flank/cycle > siege > wall, with control as the swarm answer. Deck-web cross-check vs `ALLEY_KINGZ_CARD_EXPANSION.md` 10 meta decks: consistent (IRON WALL loses to cycle+disable, TURRET TRAP loses to beatdown, DECAPITATION loses to wall).

**Air audit:** 17 flyers (16% of roster), anti-air per faction: Leashbreak 28/28, K9 25/26, Zoomie 11/26, **Boneguard 7/26**. Boneguard is the designated air-weak faction -- acceptable as faction identity, but the 5 STREET melee flyers (Nitro, Spike, Hotwire + Roadblock, Crashcage) are over-budget cards that 35 ground-only cards can never answer. Over-budget + unanswerable is the toxic combo; fix the budget (sec E) and the air lane is fine.

### G. Spells -- cost vs impact

| Spell | Energy | CD | Damage | Radius | Effect | Verdict |
|---|---|---|---|---|---|---|
| Jolt | 3 | 9 | 130 | 2.4 | 0.5s stun | FAIR-MINUS. Kills nothing (min troop HP 504, tokens 300). Value = the attack-reset stun. 43 dmg/energy is the worst damage rate; fine as the cheap reset, mislabeled as "kills swarms" in its codex text. |
| Snare Trap | 3 | 13 | 90 | 1.8 | 1.6s root, hidden | FAIR. Zone denial priced right. |
| Strike | 4 | 11 | 320 | 2.6 | burst | FAIR. Kills spawn tokens (300 HP) outright -- the real anti-swarm tool; 2-3 unit hits = 640-960 value. Cannot execute even a cost-2 troop (504 HP) -- chip only. |
| Tar Pour | 4 | 12 | 0 | 3.2 | -35% move + atk spd, 4s | FAIR-PLUS. Biggest radius; vs a 4x sudden-death push this is the best defensive energy in the game. |
| Boneshatter Freeze | 5 | 14 | 0 | 3.0 | full stop 3s, hits towers | FAIR. The premium CC; tower-freeze justifies 5 energy. |

Flag, not a break: NO damage spell can kill ANY deployed troop. In Clash, cheap spells execute cheap swarms; here the 450-HP floor (504 actual min) puts every troop out of Strike's reach. The HEX STORM meta deck's "melt every push" promise actually means "slow every push and clear its tokens." Either accept and reword, or give Strike an execute threshold (e.g. kills troops below 15% HP) instead of raw damage inflation. Spell costs are NOT compressed by `energyCost()` (troops are) -- at canon cost 3-5 they land in the compressed band anyway, so no unfairness there.

### H. Personalization interaction (WAVE6 sec 7 -- the governing principle)

The balance curve is the floor under radical personalization: per-card Garage Tuning (AK-ATTRS) lets two accounts run the SAME card at up to +25% agi/aspd or -20% damage-taken -- meaningfully different builds, bounded by clamps so no build escapes the budget by more than ~x1.25 on one axis. This passes the anti-generic test (two veteran $BCARDDs CAN feel different) -- but only if the base curve is fair: a maxed-aspd Knuckles (258 x 1.25 = 323 DPS at 4 energy) shows how tuning AMPLIFIES every base-curve outlier. Fix the 5 flagged cards before the attribute-sheet UI (sec 1) makes the numbers visible to players, because visible broken numbers become the meta overnight. The team-up layers (faction crew + 10 named synergy combos) are capped at MOVE_CAP 2.0 / DMG_CAP 1.8 and are symmetric to the AI -- no balance leak found there.

### I. Process flags

1. `data/_balance_pass.py` asserts a 48-card roster -- stale vs the 106-card SoT; it will crash if re-run. Extend it to apply variant multipliers ON TOP of the formula so one file regenerates the whole fair curve.
2. The HP clamp law (2850) is enforced for originals, ignored by variants (Tombstone 3648). One law, everywhere.
3. `BALANCE_NOTES.md`'s "no card strictly better at same cost + role" claim is no longer true post-expansion -- update it after the variant tuning pass so the doctrine matches the data.

*Audit grounded in: canon.js (106 troops + 5 spells, node-verified), engine.js (atkInterval, energyCost, rangeBand, AK-ATTRS clamps, spawnDrone, TOWER_STATS, synergy caps), data/_balance_pass.py + data/BALANCE_NOTES.md (budget formula), ALLEY_KINGZ_CARD_EXPANSION.md (variant spec + meta deck web), WAVE6_RPG_DEPTH_SPEC.md sections 1, 2, 7.*
