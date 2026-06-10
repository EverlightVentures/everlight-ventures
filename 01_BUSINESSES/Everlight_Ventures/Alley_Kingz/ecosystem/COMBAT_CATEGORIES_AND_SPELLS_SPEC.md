# Alley Kingz - Combat Categories + Spells SPEC
**Date:** 2026-06-04 | Engine: `Alley_Kingz/ecosystem/game/engine.js` (+ canon.js card data, index.html UI)
**Problem (Rich):** today every card just attacks every card. Add Clash-Royale depth: ground/air/splash
targeting, per-card traits, and a spell layer (freeze/slow/trap/etc).

## 1. TARGETING MATRIX (the core depth, Clash-Royale model)
Every troop gets TWO tags:
- **domain** = where it lives: `ground` | `air` (air = dogs in drone/jetpack rigs, they FLY over the lane).
- **targets** = what it can hit: `ground` | `air` | `both`.

**The rule:** a unit may attack a target ONLY if `target.domain` is in the attacker's `targets`.
- Air troops can ONLY be hit by units whose `targets` includes `air` (anti-air). Ground-only attackers
  cannot touch flyers -> flyers wreck a ground-only army until you deploy anti-air. Rock-paper-scissors.
- Towers target `both` (so air can be defended against at the tower).

**Smart defaults (derive from existing data, minimal hand-tagging):**
- MELEE weapon -> `targets: ground` (can't hit air). RANGED (bullet/beam/lance/spread/cannon) -> `targets: both`.
- `domain: ground` for everyone by default; hand-assign ~8-10 cards as `air` (lore-fit: drone/jetpack rigs,
  spread across factions, at least one anti-air answer per faction so no faction is helpless vs air).

## 2. ATTACK TYPE: single vs SPLASH (AOE)
- **splash** (boolean + `splashRadius`): hits ALL enemies in a radius (crushes swarms, weak vs single tanks).
- Derive: `cannon` + `spread` weapon types -> splash; `bullet/beam/lance/melee` -> single-target.
  (A few legendaries can override to splash for identity.)

## 3. PER-CARD TRAITS (layer onto existing HP/DMG/range/speed/rarity)
Add to each card in canon: `domain`, `targets`, `splash`, `splashRadius`. Balance by faction + rarity:
- **Boneguard** (tanks): ground, high HP, mostly ground-target melee, slow. The wall.
- **Zoomie** (speed): fastest; the faction's AIR units live here (drone rigs); some anti-air.
- **Leashbreak** (tech): mixed; debuff-flavored; carries spell synergy.
- **K9 Circuitry** (turrets/range): best anti-air + splash (ranged, targets both); stationary/slow.
- Legendaries/Mythic ($BCARDD) get standout combos (e.g. air + splash, or both-target + high dmg).

## 4. SPELLS (new card type -- "do different things to the dogs")
New card `type: 'spell'`. Cast on a TARGET POINT/AREA (not a lane troop). 4 faction-themed + scalable:
| Spell | Faction | Effect | Duration | Notes |
|---|---|---|---|---|
| **FREEZE** | Boneguard | enemies in area STOP (no move, no attack) | ~3s | towers freeze too; classic reset |
| **TAR SLOW** | Leashbreak | -35% move + -35% attack speed in area | ~4s | softens a push |
| **SNARE TRAP** | K9 | invisible trap on the field; arms, triggers when an enemy crosses -> roots + small dmg | until triggered | zone control |
| **JOLT (zap)** | Zoomie | instant small AOE damage + 0.5s stun | instant | kills swarms, resets attacks |
| (opt) **STRIKE** | neutral | medium AOE burst damage | instant | the "fireball" |

Spell mechanics on units: a `status` on each unit -> `{frozen, slowUntil, snared}`; getSpeed()/doAttack()
read it (frozen = skip; slow = scale; snared = rooted). Spells cost energy like troops; on a cooldown.

## 5. ENGINE CHANGES (build plan)
1. **canon/cards.json:** add `domain`, `targets`, `splash`, `splashRadius` per card (script-derive from
   weapon type + a small air-unit list); add the spell cards with `type:'spell'` + effect params.
2. **engine.js targeting:** in target-acquisition, filter candidates by `target.domain in attacker.targets`.
   Air units skip ground-only attackers. Towers target both.
3. **engine.js splash:** on a splash unit's hit, damage all enemies within `splashRadius` of the target.
4. **engine.js status effects:** add `frozen/slowUntil/snared` to units; getSpeed + doAttack + ability
   timers honor them; tick them down each frame (use the existing sub-stepped update).
5. **engine.js spells:** a castSpell(spellId, x, y) that applies the area effect; energy cost + cooldown.
6. **index.html UI:** spell cards in hand render distinctly (no "deploy troop" -> "cast at point"); a target
   reticle for area spells; visual FX (freeze tint, slow web, trap marker, zap flash); air units render
   with a shadow/altitude offset so you can SEE they fly; a small ground/air/splash icon on each card.
7. Rebalance + harness no-throw test + bump ?v + deploy (Direct-Upload to alley-kingz.pages.dev).

## Open operator choices
- Which ~8-10 cards fly (air domain)? (proposal: derive a balanced spread, Rich tweaks)
- Spell set: the 4 above + optional STRIKE? Spell rarity/energy costs.
- Keep it 1 spell slot per deck, or spells share the 4-card hand?
