# Alley Kingz -- Kill-Streak Card Evolution (build spec + research)

Status: DESIGNED, not built. Operator concept 2026-06-16. Researched (cited below).

## The concept (operator)
A deployed unit that gets kills "evolves" mid-match: escalating visual tiers
(basic -> advanced -> ... -> "dog god") with cooler kill effects, AND its effective
LEVEL rises (a lvl-1 card temporarily plays like lvl-3) for a stat boost. Resets on
unit DEATH and on match end. Permanent power stays in the shop; kill streaks are a
temporary in-match spike. "Free in-game upgrade, but you still need the shop."

## Verdict: GO. It's a proven mechanic and his instinct (reset every match, power lives
in the shop) is the SAFE version -- it sidesteps the pay-to-win complaints Clash Royale's
permanent Evolutions drew.

## How the top games do it (research, cited)
- **CoD Mobile mythic / reactive camo = closest match.** Weapon visuals escalate through
  ~4 stages driven by kills in one match; reactive camo bumps every ~2 kills and (key)
  does NOT reset on death once maxed. Crucially these tiers are **cosmetic-only** -- the
  genre's most-copied "evolve from kills" mechanic avoids balance risk entirely.
  (callofduty.com Dark Frontier; jaxon.gg; dotesports; sportskeeda)
- **Brawl Stars Hypercharge = best mechanical template.** A 2nd bar fills by dealing/taking
  damage; when full, a player-activated, time-limited TOTAL power spike (dmg+speed+shield).
  The ability to HAVE it is gated by permanent progression (Power 11). Exactly the
  "permanent in shop, temporary in match" split. (clutchpoints; mobilematters; supercell)
- **Clash Royale Evolutions:** NOT earned mid-match -- pre-set deck slots + cycle gate.
  Drew pay-to-win / grind-wall backlash. AK's earned-in-match + resets model is safer.
- **Archero:** clean split we copy -- run-scoped skills are disposable, equipment is the
  permanent power. (levelwinner; androidauthority)
- **Anti-snowball theory:** kill-streak power is a positive feedback loop; mitigate with
  hard caps, reset valves, and comeback flashpoints for the trailing side.
  (code.tutsplus; waywardstrategy; gamedeveloper.com)

## Recommended design (wires into EXISTING engine primitives -- no new subsystem)
Kill attribution already exists: `creditKill(att)` (~engine.js:696), `killsByCard`,
`Unit.takeDamage(d,...,att)` records `t.lastHitBy`. Global power ceiling `DMG_CAP=1.8`
(~engine.js:204) already governs the buff layer -- the streak buff lives INSIDE it.

Tiers (per UNIT instance; only unit kills count, not tower last-hits/spells):
| Tier | Name | Kills | Grant (multiplicative, capped, composes under DMG_CAP=1.8) |
|------|------|-------|------------------------------------------------------------|
| T0 | Basic     | 0  | shop default level |
| T1 | Advanced  | 2  | +10% dmg, +10% maxHP |
| T2 | Excellent | 4  | +20% dmg, +20% maxHP, +5% atkSpd |
| T3 | Supreme   | 6  | +30% dmg, +30% maxHP, +10% atkSpd |
| T4 | Dog God   | 8+ | +40% dmg, +40% maxHP, +15% atkSpd, signature FX + crown |
(operator's "supreme/excellent" order inverted -- fixed above. When maxHP rises, add the
same delta to current hp so the dog visibly toughens.)

Show it for ~ZERO new art (do NOT draw 5x48=240 arts):
ONE shared, tier-parameterized overlay over each unit's single base sprite --
1. rim-glow/outline (canvas stroke + shadowBlur), color ramps by tier
2. kill-count pips + a shared crown sprite (one tinted PNG) at T3-T4
3. particle-trail intensity from the existing `particles` pool, color by tier
4. kill-effect escalation: reuse the hit/death FX fn with a tier param
5. body palette shift via the EXISTING `drip.js` CSS-filter trick (e.g. Dog God = Inferno filter) -- free
6. optional: ONE bespoke "Dog God" aura asset shared by all 48 cards
This is the CoD reactive-camo / rarity-frame pattern: one parametric layer, every card reuses it.

Reset rules: streak dies with the unit (the key anti-snowball valve -- focus-fire the fed
dog); nothing persists past match end (engine already rebuilds unit stats from canon+shop
level at deploy). Permanent power = shop only.

Anti-snowball guardrails: streak dies with unit; +40% hard cap under DMG_CAP=1.8; the
tier is TELEGRAPHED to the enemy (crown/glow/pips) so they can counter; buffs stay
unit-local (never compound with energy/tower leads); lean on the existing GOLDEN HOUR
flashpoint for the trailing player.

Risks: snowball if HP buffs too generous or streak lives too long (death-reset + cap
mitigate); board readability with many glowing units (cap simultaneous high-tier FX);
must verify Dog God + a symmetric event buff (e.g. GLASS BONES 1.3) clamps to DMG_CAP=1.8;
lock streaks to Unit instances (not spell/splash last-hits).

## RELATED FINDING: the phase-4 "all cards same speed" bug
NOT a phase-scaling bug -- the code is correct (per-card `maxSpeed` x phase mult `sp`,
ratios preserved; `sdt = dt*sp*combatScale` sub-stepped). The REAL cause: the per-card
speed DATA in `canon.js` is a narrow, clustered band (35 cards share 0.85; most 0.55-0.95;
slowest->fastest only ~2.6x). At 4x pace travel time collapses, so a ~1.5x gap between the
two big clusters is imperceptible -> "they all look the same."
Fix options:
  (a) WIDEN the speed spread in the data (clear tiers, e.g. Slow 0.5 / Med 0.85 / Fast 1.3 /
      VeryFast 1.8) so the difference reads even x4. <- what the operator wants; balance pass.
  (b) soften movement's phase-scaling (e.g. movement x sqrt(phaseMult) or cap at ~2x) while
      energy/attacks stay full 4x, so travel stays long enough to SEE the speed identity.
Recommend (a) + optionally (b).

## Sources
CoD: callofduty.com/blog Dark Frontier; jaxon.gg/cod-mobile-mythic-skins; dotesports;
item4gamer; sportskeeda. Clash Royale: clashroyale.fandom.com Card_Evolution; supercell
release notes; mobilematters; royaleapi. Brawl Stars: clutchpoints; mobilematters;
supercell. Vampire Survivors: appgamer; vampire.survivors.wiki. Archero: levelwinner;
androidauthority. Snowball: code.tutsplus; esportsheaven; waywardstrategy; gamedeveloper.com.
Cheap VFX: cghow UE5 rarity glow; Unity palette-swap shader; animaticsassetstore GPU particles.
