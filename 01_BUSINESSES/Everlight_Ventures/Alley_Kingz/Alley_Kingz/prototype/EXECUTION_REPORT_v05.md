# Alley Kingz v0.5 - STREET KINGZ (Twisted Metal Edition)
## Execution Report | Feb 28, 2026

### What Was Built
Complete character roster overhaul inspired by Twisted Metal: Black (PS2). Every card reimagined with retro neon vehicular combat personas tied to 10 city arenas.

### Files
- `game_v5.html` - Source build (1659 lines, JS syntax verified)
- `index.html` - Deployed copy (identical to game_v5.html)
- `game_v4.html` - Previous version backup (1613 lines)
- `build_v5.py` - Python build script used for data splicing

### Card Roster: 41 Total

**30 Troop Characters (3 per city):**

| City (Levels) | Card 1 | Card 2 | Card 3 |
|---|---|---|---|
| Compton (1-10) | Scrapyard (5) | Corner Boyz (2) | Prospect (1) |
| Detroit (11-20) | Dead Mile (4) | Axle Grind (5) | Rust Bucket (2) |
| Chicago (21-30) | Blue Line (5) | Grim Ride (3) | Drill Van (4) |
| Brooklyn (31-40) | Phantom (4) | No Face (3) | Cabbie (3) |
| Atlanta (41-50) | Preacher (5) | Trap King (6) | Dirty South (3) |
| Oakland (51-60) | Sideshow (4) | Dock Boss (7) | Hyphy (2) |
| Miami (61-70) | Vice Queen (4) | Bass Cannon (5) | Jet Runner (2) |
| Las Vegas (71-80) | Ice Kream (6) | High Roller (5) | Showgirl (3) |
| Neo Tokyo (81-90) | Mecha (7) | Drone Lord (4) | Neon Blade (3) |
| Kingz Court (91-100) | Kingpin (6) | Warhawk (8) | Shadow King (5) |

**8 Spells:** Napalm (4), Blackout (3), Turbo Boost (3), Drive-By (2), Oil Slick (2), Spike Strip (3), Smoke Screen (1), Calypso's Wish (3)

**3 Buildings:** Car Bomb (3), Chop Shop (4), Turret Nest (3)

### New Abilities Implemented
- RAM - 2x first hit (Dead Mile)
- SHOCK - Stuns target 1s (No Face)
- JACKPOT - Random 1-3x damage multiplier (High Roller)
- DAZZLE - AoE stun 1.5s (Showgirl)
- TASER - Chain zap 3 targets (Blue Line)
- BARRAGE - 3-missile burst (Trap King)
- NITRO - +50% speed burst (Vice Queen)
- BASS_DROP - Slow aura (Bass Cannon)
- Calypso's Wish - Random: heal/damage/speed (spell)

### 7 Synergies (Twisted Metal Themed)
Speed Demon, Street Gang, Heavy Metal, Spell Cycle, Ghost Rider, Fire Starter, Dark Carnival

### 5 Deck Presets
Speed Demon (1.9 avg), Heavy Metal (5.0), Ghost Rider (2.8), Street Gang (2.6), Dark Carnival (3.4)

### Technical Changes
- Ability system now data-driven (checks card.ability field, not hardcoded IDs)
- Chop Shop spawns Rust Bucket instead of old Hooptie
- AI decks updated with new card IDs for all level tiers
- All old card references removed (muscle_car, sports_car, hooptie, etc.)

### Unlock Progression
- Compton + Detroit + spells/buildings: Unlocked from start (15 cards)
- Brooklyn: Locked at levels 32, 35, 38
- Atlanta: Locked at 42, 45, 48
- Oakland: Locked at 52, 55, 58
- Miami: Locked at 62, 65, 68
- Las Vegas: Locked at 72, 75, 78
- Neo Tokyo: Locked at 82, 85, 88
- Kingz Court: Locked at 92, 95, 98

### Hive Mind Agents Used
1. Researcher - Twisted Metal design philosophy, card game architecture, Clash Royale/Brawl Stars patterns
2. Explorer - Full code map of 150+ card references across 1613-line game file
3. Builder - Python splice script for surgical data replacement

### Known Issues / Next Steps
- Characters not yet tested in browser gameplay
- Visual rendering uses generic car shapes - future: unique silhouettes per character
- Death abilities (Rust Bucket BACKFIRE, Shadow King COFFIN) need code in updateUnits
- Hyphy GHOST_RIDE (keeps moving after death) needs code in updateUnits
- Cabbie UNDERGROUND (bypass units) needs pathfinding changes
- Sound effects are generic - could be unique per character
