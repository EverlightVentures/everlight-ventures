# Alley Kingz -- Competitive Balance + Traits Pass

**Date:** 2026-06-03 | **Scope:** STATS + abilities only. Names, cardNumbers, factions, rarities, and rig objects are unchanged.
**Generator:** `data/_balance_pass.py` (deterministic; re-runnable). Mirrors the SoT into `game/canon.js` and back into the OnyxPOS source so `_build_canon.py` stays consistent.

The goal: 48 cards that feel distinct and fair, not random. Stats are now a function of
ARCHETYPE (role) x rarity x cost, with a real spread (tanks slow + huge HP, glass cannons
fast + fragile, ranged longer reach). Numbers stay believable against the towers in
`engine.js` TOWER_STATS (princess 1400 HP, king 2600 HP) for a 2-3 minute match.

## Power budget formula

```
hp  = (hp_at_cost5  + (cost - 5) * hp_per_cost ) * rarity_mult, rounded to 50
dmg = (dmg_at_cost5 + (cost - 5) * dmg_per_cost) * rarity_mult, rounded to 5
```

`rarity_mult`: Common 0.92, Rare 1.00, Epic 1.08, Legendary 1.14, Mythic 1.20.
So a card never gets free power -- a higher rarity or higher cost buys a bigger budget,
and no card is strictly better than another at the same cost + role.

## Archetype table (role -> blueprint)

| Role | HP @cost5 | DMG @cost5 | Atk Spd | Move tier | Range | Ability type | Identity |
|---|---|---|---|---|---|---|---|
| Vanguard   | 2300 | 110 | 0.7  | Slow      | 1   | dr / shield / knockback | Tank. Soaks, walks slow, low DPS. |
| Striker    | 1300 | 150 | 1.05 | Medium    | 1   | stun / crit / buff      | Brawler. Balanced melee bruiser. |
| Lancer     | 1050 | 165 | 0.95 | Medium    | 2   | pierce                  | High single-target, pierces a line. |
| Skirmisher | 820  | 120 | 1.3  | Very Fast | 1   | dash / evasion          | Glass cannon flanker. Fragile, fast. |
| Assassin   | 1150 | 205 | 1.1  | Fast      | 1   | teleport                | Burst killer, can dive the Queen. |
| Blaster    | 720  | 110 | 1.1  | Medium    | 4   | pierce                  | Ranged DPS. Long reach, soft body. |
| Hacker     | 820  | 85  | 1.0  | Medium    | 3   | silence / disable_tower | Disruptor. Shuts off abilities/towers. |
| Controller | 950  | 95  | 0.95 | Medium    | 3   | slow / disable_tower    | Zone control. Slows + locks the lane. |
| Support    | 950  | 60  | 0.9  | Medium    | 3   | heal / shield / buff    | Backline utility, low DMG. |
| Spawner    | 800  | 60  | 0.9  | Medium    | 2   | spawn                   | Deploys drones/pups, weak alone. |
| Structure  | 1150 | 95  | 1.0  | Static    | 4-5 | ramp                    | Turret. No move, long ranged defence. |

All `abilityType` values are keys the engine can fire (`ABILITY_KIND` in `engine.js` L149-160):
shield, buff, aura, dr, stun, slow, heal, crit, teleport, dash, spawn, disable_tower,
silence, knockback, ramp, line, aoe, double_hit, queen_target, turret_break, pierce,
reveal, evasion, invuln, blind, root, chain, dot, burst, lane_swap. No invented types.

## Spread by role (after the pass)

| Role | n | HP min-max | DMG min-max | Range | Move speed |
|---|---|---|---|---|---|
| Vanguard   | 6  | 2250-2850 | 110-180 | 1    | 0.55 (Slow) |
| Striker    | 6  | 1050-1500 | 110-175 | 1    | 0.85-1.1 |
| Lancer     | 4  | 1000-1150 | 150-180 | 2-3  | 0.85 |
| Skirmisher | 4  | 600-750   | 75-110  | 1-2  | 1.1-1.4 |
| Assassin   | 2  | 1900      | 230     | 1    | 1.1 (Fast) |
| Blaster    | 2  | 550       | 80      | 4    | 0.85 |
| Hacker     | 3  | 600-900   | 55-90   | 3    | 0.85 |
| Controller | 4  | 750-1600  | 70-170  | 3    | 0.85 |
| Support    | 10 | 700-1100  | 40-70   | 2-3  | 0.85-1.1 |
| Spawner    | 4  | 550-750   | 40-55   | 2    | 0.85 |
| Structure  | 3  | 1050-1450 | 85-125  | 4-5  | 0.0 (Static) |

**Roster spread:** HP 550-2850, DMG 40-230, RANGE spans 1..5.
Move tiers land cleanly in the engine bins (0 Static, <=0.6 Slow, <=0.95 Medium,
<=1.25 Fast, >1.25 Very Fast), so card text reads true to behaviour.

## Soft rock-paper-scissors

- **Tanks beat squishies:** Vanguards carry the most HP (up to 2850) but the lowest DPS, so they front-line.
- **Ranged kites melee:** Blasters/Structures fire from range 4-5 with low HP, so they punish slow melee but fold to fast flankers.
- **Fast flanks punish slow backlines:** Skirmishers/Assassins move Fast/Very Fast and cross lanes, diving the soft ranged + support cards.
- **Control answers swarms:** Controllers/Hackers slow, silence, or disable the spawners and turrets that would otherwise snowball.

## Cards that changed most (vs the legacy flat numbers)

| Card | Role | HP before -> after | DMG before -> after | Why |
|---|---|---|---|---|
| Stonejaw          | Vanguard | 2100 -> 2850 | 120 -> 145 | Legendary cost-7 tank now reads as a true wall. |
| Rust Cane Corso   | Vanguard | 2000 -> 2650 | 120 -> 135 | Cost-8 Rare tank pushed up to the Vanguard curve. |
| Granite Saint     | Vanguard | 2200 -> 2650 | 110 -> 135 | Cost-8 guard now soaks like its Bodywall implies. |
| Jagged            | Assassin | 1400 -> 1900 | 210 -> 230 | Mythic diver gets glass-cannon burst, still fragile vs tanks. |
| Brick Bullmastiff | Vanguard | 1700 -> 2250 | 100 -> 110 | Common bruiser lifted onto the tank floor. |
| Alloy Akita       | Lancer   | 1400 -> 1100 | 130 -> 180 | Reshaped into a range-2 pierce Lancer (less HP, more DMG). |

*Built by the balance pass 2026-06-03. Pairs with `README.md`, `ROSTER_CANON.md`, and `ability_params.json`.*
