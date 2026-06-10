# Alley Kingz Prototype -- Combat Feel + Diversity Upgrade Spec
**Date:** 2026-06-03 | From operator playtest feedback. Goal: lane discipline, every unit visually + mechanically unique, readable cards, and real combat juice.

Sources for the FX work: game juice / game-feel ("juice the most frequent action" = attacks; screen shake; particles at hit location; squash and stretch) -- gt3000 "Juice It" + GameDev Academy game-feel.

---

## 1. LANE DISCIPLINE (gameplay correctness)
- Arena has a LEFT lane and a RIGHT lane split at center x = ARENA_W/2 (9).
- On deploy, a unit is assigned `lane` = 0 (left) if gx < 9 else 1 (right).
- **Default units stay in their lane:** they path straight DOWN their lane toward the same-side bridge, then the same-side enemy princess tower. No diagonal drift to the other lane.
- **Targeting is lane-scoped:** `findTarget` only considers enemy units whose x is within the unit's lane band (a unit in the left lane ignores right-lane enemies), plus the same-side princess tower. The king is targetable only after a princess falls (existing rule), and only by units whose lane princess is down OR queen_target units.
- **Special crossers:** `crossLane=true` units may switch lanes / target across. Set crossLane for abilityType in {teleport, dash, lane_swap} and role in {Assassin, Skirmisher}. Everyone else is lane-locked.
- Result: left lane fights left, right lane fights right, like Clash Royale; only special cards flank.

## 2. PER-CARD VISUAL IDENTITY (no two the same) -- engine derives, renderer draws
Engine adds these fields in `mapCanonToEngine(c)` (the CONTRACT the renderer reads off `unit.card`):
- `palette`: faction base family -- boneguard_crew = amber/brick (#C9772E base, #6e2f12 dark, #ffb060 light); zoomie_syndicate = hot magenta/cyan (#FF2E88 / #5e0e33 / #ff8ad0); leashbreak_tactix = violet (#7B5CFF / #2a1a55 / #b9a6ff); k9_circuitry = teal/chrome (#00E0C0 / #064b42 / #9affec).
- `accent`: a per-card hue derived from a hash of the card name (HSL -> hex), so same-faction same-role cards still differ. No two cards share the exact accent.
- `bodyShape`: from role -- Vanguard=tank (wide/heavy), Striker=brawler, Lancer=lance (long pointed), Support=rounded, Assassin=blade (sleek), Skirmisher=scout (small), Spawner=carrier (boxy w/ bay), Hacker=dish (antenna), Blaster=turret, Controller=dish, Structure=fixed turret.
- `weaponType`: derived from role + range + abilityType, one of:
  - `melee` (range 1): no projectile; a SLASH/ram arc on hit. Fast windup.
  - `bullet` (Striker/Skirmisher, range 2-3): small FAST projectile, accent color.
  - `cannon` (Vanguard/Blaster, range 2-3, high dmg): SLOW heavy lobbed shell, brick color, big impact.
  - `lance` (Lancer / pierce/line abilityType): FAST straight piercing bolt, long thin.
  - `beam` (Hacker/Controller/range>=4): near-INSTANT thin beam line, faction-light color.
  - `spread` (Spawner / spawn/chain): 3 medium pellets in a small fan.
- `projSpeed` (arena units/s): melee n/a, bullet ~15, cannon ~5, lance ~20, beam ~40 (instant feel), spread ~10. THIS is the "some fast some slow" the operator asked for.
- `projColor`: bullet=accent, cannon=#FF6B2C, lance=palette.light, beam=palette.base, spread=accent.
- `projSize`: bullet 0.16, cannon 0.34, lance 0.12 (long), beam 0.08 (thin), spread 0.14.
- `projShape`: 'dot' | 'shell' | 'lance' | 'beam' | 'pellet'.
- `silhouetteSeed`: hash(name) for small per-unit shape jitter (size, accent stripes).
- Rarity drives frame/glow: Mythic = gold crown frame + pulsing aura; Legendary = bright gold edge; Epic = brick edge; Rare = blue edge; Common = steel. (already partly present.)

## 3. ATTACK + PROJECTILE BEHAVIOR (engine)
- `doAttack` branches on `weaponType`: melee = instant slash arc + impact at target (no projectile); cannon = slow lob with big AoE-ish impact + screen shake; beam = instant line hit + thin flash; lance = fast pierce (can hit first target, light pierce); bullet = standard fast; spread = 3 pellets.
- `launchProjectile` carries `shape,size,color,trail,speed` so the renderer draws each kind differently.
- On every shot: push a `muzzle` effect (color = projColor, size by weaponType) at the muzzle.
- On every impact: push `impact` particles (color by projColor, count by weaponType: cannon 14, bullet 5, beam 6, lance 4, spread 4-per-pellet).
- **Screen shake:** add `game.shake` (a decaying number). Tower hit += 4, cannon impact += 3, unit death += 2, tower destroyed += 12. Renderer offsets the canvas by a random vector scaled by shake, then decays it.
- **Squash/stretch:** units squash on deploy (already deployScale) and pulse on attack windup. (renderer)
- Keep ability NAME floating on ability fire (exists). 

## 4. CARD READABILITY (so the player knows what cards do)
- Each hand card already shows cost, glyph, name, ability name. ADD a small role tag + a faction color bar.
- **Card info popover:** when a card is selected (tapped), show a popover ABOVE the hand with: name, role + rarity, cost, HP / DMG, RANGE, the rig name, and the full `ability.description` (it exists in the canon, e.g. $BCARDD "Shield self; can target Queen"). Tapping the card again or deploying closes it. This directly fixes "I do not know how to use my cards."
- The hint line also names the selected card and its ability.

## 5. ENGINE <-> RENDERER CONTRACT (field names, do not rename)
`unit.card`: palette{base,dark,light}, accent, bodyShape, weaponType, projSpeed, projColor, projSize, projShape, silhouetteSeed, crossLane, role, rarity, isMythic, abilityName, abilityDesc, rig{name}, hp/maxHp, dmg, range.
`unit`: lane (0/1).
`projectile`: shape, size, color, speed, trail (bool), owner.
`effect` types: 'muzzle'(color,size), 'impact'(color,count handled by particles), 'slash'(angle,color), existing 'txt'/'ability'/'crown'/'ring'.
`game.shake`: number (renderer reads + decays).

## 6. BUILD ORDER
- Pass 1 (engine.js + canon card map): sections 1, 2 (field derivation), 3 (attack/projectile/shake logic), lane assignment + targeting + pathing. Keep canon stats verbatim.
- Pass 2 (index.html renderer + UI): draw unique units (bodyShape+palette+accent+rarity frame+weapon mount), draw projectiles by shape/size/color/trail, FX (muzzle, impact particles, screen shake, death explosions, charge trails, squash/stretch), and the card info popover (section 4). Bump script cache to ?v=3.
- Verify each pass with the node DOM harness (`/tmp/ak_domtest.js`) + a lane-discipline assertion + render-field presence. No em-dashes (repo hook).

*Keep it self-contained static (no npm). Phone proot safe. The engine stays the single source; index.html is the renderer.*
