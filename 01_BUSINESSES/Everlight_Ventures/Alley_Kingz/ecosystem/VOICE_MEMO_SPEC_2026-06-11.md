# OPERATOR VOICE MEMO SPEC -- 2026-06-11 4:50 PM (Alley Kingz update wave 2)
Transcribed requirements; feeds the post-build implementation workflow alongside
COMBAT_FEEL_SPEC.md + WORLD_MAP_REWARDS_SPEC.md + SKILL_TREE_RESEARCH.md.

## 1. Phase (district) respawn rules -- FINAL CANON
- Entering phases 2 and 3: FULL BOARD RESET. Nobody carries troops. Fresh fight.
- Entering phase 4 (the finale, "the chaos"): BOTH sides' surviving troops respawn
  at the back of their own towers and re-engage. Not just the winner's -- if
  player B got wiped, B spawns nothing; if both have survivors, both respawn.

## 2. AI difficulty = one smooth curve across all 400 phases
- Unit of difficulty: (city 1-10, level 1-10, phase 1-4) -> global index 1..400.
- Within a level: phase 4 hardest. Within a city: level 10 phase 4 = city boss.
- City 10 / level 10 / phase 4 = the final boss, veteran/expertise tier.
- City 1 / level 1 / phase 1 = Rookie, easiest. Increment smoothly between.
- Levers: AI energy rate, AI decision speed, AI deck quality/levels, unit level
  scaling. The curve must be tuned so a fresh account can clear city 1 and a
  maxed account is properly challenged at city 10.

## 3. Progression VISIBILITY (the rewards exist but the player cannot SEE them)
- End screen says +coins/+XP/+cards, but: no XP bar anywhere, cards do not
  visibly land in the collection, no chest area. FIX: player profile surface with
  XP bar + level; level-ups grant a visible reward (Google-Play-style).
- Chest inventory screen: open earned chests with a reveal; grants shown.
- Collection: every card shows copies X / Y-to-upgrade; upgrade button right
  there when affordable.
- Skill point section in the same area: assign points, see attribute changes.
- All recorded on the user profile (ak_profile / ak_world, cloud-saved).

## 4. TEST MODE text -- DONE 2026-06-11 (server disclaimer live-aware + client
  strings replaced; ships with next deploy). Charges are REAL and labeled as such.

## 5. Field unit SHAPES = classification language (research-driven)
- Stop drawing every unit as a circle. The unit's PHYSICAL token shape on the
  field = its range class, so formations read at a glance:
  e.g. long-range = diamond (back line), brawler/melee = circle (front),
  mid-range = octagon/hex -- final mapping comes from research into the best,
  coolest, most readable game shapes (research it, then assign).
- Each shape gets its own outline color; rarity adds a warm glow of the rarity
  color around the shape. Visually STACKABLE identity: shape -> class,
  outline -> class color, glow -> rarity.

## 6. SYNERGY SYSTEM (Merge-Tactics-style, micro-strategy layer)
- Specific troop combinations on the field together activate bonus effects
  (faction packs, breed pairs, role combos). Another deliberate strategy layer
  on top of: ranges/shapes (positioning), skill points (build), card levels.
- Design pass required: synergy table (who + who = what buff), UI hint when a
  synergy is active, balance within the power budget.

## 7. Per-card skill overlay (restated from chat, canonical)
- Universal card level = base stats (existing Garage).
- Skill points can ALSO be assigned to a specific card to raise an attribute.
- Stacks ON TOP of level: my L1 with points can match/beat a stock L2; when I
  level to 2, my overlay rides on top of the new base.
