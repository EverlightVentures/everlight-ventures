# COMBAT FEEL SPEC -- Range Bands, Separation, Knockback, Energy Curve
Alley Kingz | 2026-06-11 | Targets game/engine.js (1995 lines) + canon.js (106 cards)
Operator intent: no more huddle-pile fights. Ranged engages long, melee bites close,
bodies never overlap, hits BOUNCE (God of War), energy starts at 0 and ramps.

Engine ground truth (verified in code):
- 1 arena unit = 1 tile. ARENA_W=18, ARENA_H=30, RIVER_Y=15, lane crossing ~13 tiles (engine.js:124-125).
- Towers: princess range 6, king 6.5 (engine.js:255-256). Canon unit ranges: 1/2/3/4/5 only.
- Engage today: stMove() uses hitRange = effRange(u) + (Tower? 1.0 : 0.4), then keeps calling
  moveToward() at target CENTER every tick until inside -- that is the pile (engine.js:1297-1302).
- No collision radius and no separation pass exist anywhere. Units are points.
- Damage lands in doAttack() melee branch (engine.js:1503-1520) and updateProjectiles() impact
  (engine.js:1786-1810). Those two spots are the knockback hooks.
- Energy: ENERGY_MAX=10, ENERGY_RATE=1/1.4, START_ENERGY=6 (engine.js:127). Ticked with SIM dt,
  so the 4x section pace already multiplies regen (engine.js:1150-1152). AI gets ENERGY_RATE *
  (0.78 + DIFFICULTY*0.052).
- Sections: SECTIONS[0..3] (engine.js:165). repositionPlayerUnitsToBack() carries live player
  units across EVERY transition today (engine.js:701-744).
- Reference points (Clash Royale wiki): melee short <=0.8 / medium 1.2 / long 1.6 tiles, ranged
  >=2; collision radius 0.5-0.6 typical, 1.0 max; elixir 1 per 2.8s normal, 1.4s double, ~0.9s
  triple; Log pushback = 1 tile; knockback resets attack animation, heavies resist.

## 1. Range bands per role (engine tiles)

Add RANGE_BAND lookup in mapCanonToEngine(). Canon `range` stays verbatim on card.canonRange;
combat range becomes card.range = band value. Bands (operator numbers honored: melee ~1,
brawler 3-4, ranged 4-6):

| Band    | Combat range | Canon range -> band |
|---------|--------------|---------------------|
| melee   | 1.0 - 1.6    | 1                   |
| brawler | 3.5          | 2                   |
| mid     | 4.5          | 3                   |
| long    | 5.5          | 4                   |
| siege   | 6.5          | 5                   |

Role table (every canon role, ranges as shipped in canon.js):

| Role       | Canon range(s) | Band -> combat range            |
|------------|----------------|---------------------------------|
| Assassin   | 1              | melee short 1.0                 |
| Vanguard   | 1              | melee medium 1.2                |
| Striker    | 1              | melee long 1.6 (big swings)     |
| Skirmisher | 1 / 2          | melee 1.2 / brawler 3.5         |
| Spawner    | 2              | brawler 3.5                     |
| Support    | 2 / 3          | brawler 3.5 / mid 4.5           |
| Lancer     | 2 / 3          | brawler 3.5 / mid 4.5           |
| Controller | 3              | mid 4.5                         |
| Hacker     | 3              | mid 5.0 (beam, +0.5 over band)  |
| Blaster    | 4              | long 5.5                        |
| Structure  | 4 / 5          | long 5.5 / siege 6.5            |

Per-card overrides (description-implied snipers, keyed by exact card name):
- Rail Terrier (Blaster, "Long rail shots"): 6.0
- Byte Beagle (Blaster, "Long shots that pierce shields"): 6.0
- Laser Beagle (Structure, canon 5): 6.5 (already siege; longest on the board)
- Rosco (Mythic Controller): 5.0
Result: longs/sieges open fire 4-6.5 tiles out, BEFORE melee closes; princess tower (6) still
out-ranges everything except Laser Beagle at 6.5, matching CR siege logic.

## 2. Stop-at-range + approach

Replace the stMove() hitRange slack with edge-aware stop:
- engageDist(u,t) = effRange(u) + (t instanceof Tower ? 1.0 : t.colR) where colR is section 3.
- STOP: if d <= engageDist * 0.95 -> hold position (do NOT call moveToward), face target, attack
  when atkCD <= 0.
- RESUME: only if d > engageDist * 1.10 (hysteresis band so units do not stutter-step).
- While holding, the separation pass (section 3) may still slide the body; that is allowed and
  does not re-trigger approach unless the 1.10 line is crossed.
- Ranged units NEVER walk inside engageDist * 0.95 chasing a closer target; findTarget keeps
  current nearest-first logic, movement just stops at the band.

## 3. Separation physics (no overlapping bodies, ever)

Collision radius by size class from maxHp (canon hp 550-2850):
- small  colR 0.35 (hp < 700)        - large colR 0.60 (1501-2400)
- medium colR 0.45 (700-1500)        - huge  colR 0.75 (> 2400, e.g. Vanguards 2850)
- Structures/turrets colR 0.60, immovable. Towers colR 1.0, immovable.
Store at map time: card.colR, card.mass = max(1, hp/1000).

Resolve pass, run AFTER updateUnits() each tick, allies AND enemies, ground domain only
(air ignores ground bodies, air-vs-air separates):
- For each pair within (a.colR + b.colR): overlap = (a.colR + b.colR) - dist.
- Push along the center line: a gets overlap * (b.mass/(a.mass+b.mass)), b the remainder.
  Immovables take 0; the other unit absorbs the full overlap.
- ITERATIONS = 2 per tick. MAX_PUSH = 0.35 tiles per unit per tick (no teleport pops).
- dist < 0.001 (perfect stack): push apart on a deterministic angle from (a.id*2.4) radians.
- Clamp results to x in [0.5, ARENA_W-0.5], y in [0.5, ARENA_H-0.5]. Do not bridge-check the
  separation nudge (max 0.35 cannot cross the 1.4-tile river meaningfully).
- Perf: 40-unit board = ~800 pair checks * 2 iters; fine without a grid. If peakUnits > 80,
  add a coarse 3x3-tile bucket grid (boids separation standard practice).

## 4. Hit knockback (God of War bounce)

Add per-unit kbVx/kbVy velocity, integrated in updateUnits BEFORE the state machine:
- u.x += kbVx*dt; u.y += kbVy*dt; decay kbV *= exp(-dt/0.06) (dead in ~0.18s, snappy).
MELEE HIT (doAttack melee branch, after target.takeDamage):
- Defender pushback distance = clamp(0.45 * attacker.mass / defender.mass, 0.10, 0.90) tiles
  along the attack direction. Convert to impulse: kbV = (dist/0.12) over a 0.12s burst.
- Attacker recoil = 0.15 tiles backward (same impulse form). The pair visibly bounces apart.
- Heavy resist: defender.mass >= 2.4 (hp >= 2400) takes 25% of computed pushback. Structures
  and Towers take 0.
- HIT-STOP: freeze attacker+defender state timers for 0.04s on melee impact (skip their state
  switch for 1 tick window). Pair with the existing game.shake += for weight.
- Animation reset (CR rule): pushback >= 0.5 tiles also resets the victim's atkCD windup
  (kick them out of ACQUIRE/WINDUP back to MOVE).
RANGED: bullet/lance/beam/spread = ZERO knockback. cannon projectiles = flat 0.30 tile
pushback (Bowler-style heavy shell), same mass resist rule. Ability knockback (ABILITY_KIND
knockback, engine.js:1543) keeps its 1.2-tile shove and now uses the same impulse path.

## 5. Attack styles per weaponType (deriveWeaponType, engine.js:98)

| weaponType | Roles (typical)             | Style                                              |
|------------|-----------------------------|----------------------------------------------------|
| melee      | Vanguard/Striker/Assassin   | LUNGE: 0.30-tile forward hop over 0.10s during WINDUP, settle back in RECOVER + recoil from sec 4 |
| bullet     | Striker/Skirmisher ranged   | VOLLEY: keep parabolic arc, 0.10-tile recoil hop   |
| cannon     | Vanguard/Blaster ranged     | HEAVY VOLLEY: high arc, muzzle 0.5, +knockback, +shake (already +3) |
| lance      | Lancer                      | PIERCE: flat fast bolt (projSpeed 20), 0.10 brace recoil |
| beam       | Hacker/Controller, range>=4 | BEAM HOLD: rooted while firing, beam drawn 0.25s, 0.05-tile tremble, no recoil |
| spread     | Spawner / spawn+chain       | FAN: existing 3-pellet 0.18-rad fan, 0.20 recoil   |

## 6. Energy curve (operator: start 0, slightly slower, less late chaos)

- START_ENERGY = 0 (both sides; AI too -- same curve, fairness doctrine).
- ENERGY_RATE = 1/1.8 (~0.556/s). Slightly slower than today's 1/1.4 (~0.714/s).
- DECOUPLE from sim pace: tick energy on REAL dt (the 4x section-4 pace currently quadruples
  regen, that is the late-game chaos). New explicit per-section multiplier:

| Section (1-based) | Mult | Effective rate | Feel                      |
|-------------------|------|----------------|---------------------------|
| 1 SNIFFIN' DIRT   | 1.0  | 1 per 1.8s     | slow open, CR single-ish  |
| 2 MARKIN'         | 1.2  | 1 per 1.5s     | warming                   |
| 3 OFF THE LEASH   | 1.4  | 1 per 1.29s    | pressure                  |
| 4 FINAL (overtime)| 2.0  | 1 per 0.9s     | CR triple-elixir overtime |

- AI keeps its difficulty factor (0.78 + DIFFICULTY*0.052) on top of the SAME base curve.
- Keep eventMods.energy (Zoomies/Overclock) as a final multiplier. ENERGY_MAX stays 10.
- Gate-clear +3 energy reward (grantGateReward) stays; with start-0 it matters more.

## 7. Section reset rule (reset 1->2 and 2->3, carry into 4)

In advanceSection(next) (engine.js:~680):
- next === 1 or next === 2 (entering sections 2 and 3, 1-based): FULL PLAYER RESET. Drop ALL
  player units (alive included) instead of calling repositionPlayerUnitsToBack(). Clear
  projectiles. Player energy: keep current value + the +3 gate reward (the reset is the cost;
  energy is the refund channel). Enemy side: resetEnemyGarrison(next) unchanged.
- next === 3 (entering final section 4): CARRY. Call repositionPlayerUnitsToBack() exactly as
  today -- live units regroup at PLAYER_BACKLINE_Y=25 in lane columns and ride into the finale.
- repositionPlayerUnitsToBack() itself is unchanged; it just becomes conditional. Update its
  comment block (engine.js:698-703) which currently claims carry-over on every map change.
- Pursuers (spawnPursuers) and gate rewards are independent of this rule; no change.

## 8. QA checklist

Visual (run a full match in browser at alleykingz.online build, all 4 sections):
- [ ] No two ground bodies overlap at any point (worst case: 8-unit bridge funnel).
- [ ] Blasters/Structures open fire 5.5-6.5 tiles out, visibly BEFORE melee meets.
- [ ] Mid roles (Hacker/Controller/Support) hold at ~4.5-5.0 and do not drift closer.
- [ ] Melee pairs bounce visibly on each swing; Vanguard (2850 hp) barely budges vs a small.
- [ ] Cannon shells shove targets ~0.3 tiles; bullets/beams shove nothing.
- [ ] No stutter-stepping at the stop line (hysteresis working).
- [ ] Energy bar starts EMPTY both sides; first deploy ~4-6s in; section 4 fills fast but
      no faster than 1 per 0.9s.
- [ ] Sections 1->2 and 2->3 clear the player board; 3->4 carries survivors to the backline.
- [ ] Separation never pushes a unit through river/walls or off-arena.
Harness (headless, from ecosystem/): `node tests/ak_match_harness.js`
- [ ] Output ends `=== VERDICT: FULL MATCH RAN CLEAN (no throw) ===` with deploys > 0 and
      peakUnits sane; no SIM STALLED EARLY.

Sources: CR wiki range/collision blogs (clashroyale.fandom.com AesDragon hidden stats), CR wiki
Elixir + The Log + Bowler pages, jdxdev "Boids for RTS", howtorts.github.io avoidance.
