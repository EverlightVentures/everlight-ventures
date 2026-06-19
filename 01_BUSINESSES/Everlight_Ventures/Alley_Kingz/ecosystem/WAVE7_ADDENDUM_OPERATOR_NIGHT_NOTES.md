# WAVE 7 ADDENDUM -- operator live-test notes, 2026-06-12 ~3:15 AM
Every item below is operator-ordered. Merge into WAVE7_BUILD_CONTRACT lanes.

## BUGS (fix first, before features)
1. UPGRADE STATS DO NOT UPDATE: leveling a card (copies) or adding skill points
   does not change the displayed stats -- AND VERIFY THE ENGINE actually applies
   card level to deployed units (if local cardLvls never reach unit stats,
   upgrades are cosmetic = critical gameplay bug). Stats must visibly and
   mechanically update.
2. ENEMY KING TOWER HP INVISIBLE: princess towers show health, the opponent
   king tower does not. Show it (and verify ours shows too, all districts).
3. DRAG-RETURN CANCEL: dragging a troop from the tray and returning it to the
   tray must CANCEL the deploy (release, no field drop).

## RULE CHANGES
4. PHASE CARRY: ONLY TOWERS persist across phases -- surviving towers stay as
   they are entering the new phase; all units leave (both sides) EXCEPT phase 4
   keeps the both-side survivor respawn. (Refines the AK-RESPAWN rule.)
5. PRINCESS TOWER RANGE SUPREMACY (Clash model): princess towers out-range
   nearly every card; only 1-2 long-range siege/archer cards may outrange them.
   Rebalance the AK-FEEL range bands so towers <- range 6 beats the 5.5 band;
   audit which cards keep outranging (siege only).

## BASE-STAT DEPTH (ties to taxonomy)
6. Per-card BASE attributes beyond attack/defense: dexterity/speed, special
   attack, special defense assigned + evaluated PER CHARACTER (taxonomy lane
   assigns; engine consumes). Skill points and levels modify these visibly.
7. UPGRADE PREVIEW: before confirming any upgrade (level or skill point),
   show the next-state preview (current -> next stats side by side). Each card
   upgrades at its own pace (per-rarity/per-card curves already exist -- show
   them).

## EXPERIENCE / FEEDBACK LAYER
8. LIVE XP BAR AT MATCH END: result screen shows the XP bar filling in REAL
   TIME with numbers (current/needed), level-up moment celebrated; each level
   needs more XP (curve exists -- surface it).
9. HAPTICS: navigator.vibrate patterns per hit -- varying by card type and
   attack style (melee thud vs cannon boom vs beam buzz), small and tasteful,
   respect a settings toggle (ak_haptics, default on), fully guarded.
10. BORDER EVERYWHERE: the arena's glowing edge frame goes on EVERY screen
    (lobby, collection/garage, chop shop, world map, profile) as a static/
    breathing gold guide frame (beat-reactivity stays arena-only).

## CONTENT SURFACES
11. ENCYCLOPEDIA ("THE CODEX"): a browsable page explaining every card (stats,
    class, elevation, combos, storyline), each faction/tribe, divisions,
    elevation rules, synergies -- pulls from cards_lore + STORYLINE_CANON +
    TAXONOMY_DESIGN so it stays one source of truth.
12. NEW-PLAYER TUTORIAL: first launch on a fresh account = guided real-time
    tutorial: drag-and-drop teaching, what the objective is, playing different
    card types, energy, towers; skippable, never shows again (ak_tut_done).
13. OPPONENT NAMES LADDER: every phase shows a NEW generated opponent name
    (cool street names), climbing a chain of command across the level/city up
    to the named final boss -- wire into the nemesis name-generator tables.

## STANDING ORDERS REINFORCED
14. LOOT DROPS (DMZ): still the key feature -- kill drops with miniaturized
    real art, rare high-tier drops from high-level units. Phase 1 in wave 7.
15. Everything must BLEND -- one synergistic dynamic, not bolted-on features.
