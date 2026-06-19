# WORLD MAP REWARDS SPEC (operator-locked 2026-06-11)

## The shape
- 10 cities x 10 levels. Per city: levels 1-9 pay a SMALL first-clear chest,
  level 10 pays the BIG city-completion chest -> unlocks the next city.
  "9 small rewards and then one big reward" -- operator verbatim.
- Rewards flow AS YOU GO: every level still pays normal match rewards
  (XP/coins/drops per PROGRESSION_DESIGN.md) on top of chest logic below.

## First-clear vs replay
- FIRST-TIME CLEAR of a level = the major chest for that slot:
  - Levels 1-9: Crew Crate tier, contents scale mildly with level number.
  - Level 10: City Vault -- guaranteed Epic-or-better card, big coins+scrap,
    bonus skill point. The milestone moment.
- REPLAYS are always allowed (stomping old levels with leveled cards is fine)
  but pay only a MINOR chest, and value DECAYS with distance behind the
  player's frontier:
  - frontier = highest globally unlocked level index (city*10 + level).
  - distance d = frontier - levelIndex.
  - replay chest value multiplier = max(0.15, 1 - 0.15*d)  (floor keeps it
    never zero -- worth a quick farm, never worth grinding).
  - replay chests never drop above Rare.
- First-clear flags persist in ak_world (per level: cleared, bestStars,
  bestTime, firstClearClaimed) -- cloud-saved automatically via ak_*.

## Premium stays bought
- Earned chests are just "better rewards." PREMIUM chests (Kingpin tier etc)
  remain shop purchases only. No earned path to the top shop tier; no paid
  path required for progression. Keeps the Lane-A legal posture clean.

## Why (design intent)
- Forward pressure: the best loot is always at the frontier.
- Mercy: stuck players can farm small value behind the line.
- The level-10 spike makes finishing a city feel like beating a boss.
