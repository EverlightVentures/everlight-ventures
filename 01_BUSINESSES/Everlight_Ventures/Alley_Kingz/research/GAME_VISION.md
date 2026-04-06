# Alley Kingz -- Game Vision & Research Notes
Updated: 2026-02-27 | Hive Mind Session: 969b83a1

---

## What This Game Is

**Genre:** Real-time card-battle strategy (Clash Royale DNA)
**Setting:** GTA-style urban streets, hood aesthetic, car-themed everything
**Core loop:** Deploy cars, destroy enemy towers (which are also cars), win trophies
**Differentiator:** No one owns the urban car-battler niche. This lane is open.

---

## Prototype Status (v0.2)

File: `Alley_Kingz/prototype/index.html` -- open in any browser, no server needed.

### What v0.2 added vs v0.1:
- **Princess/King towers are now top-down car models** (Hooptie + Boss SUV)
- **Units are mini top-down cars** with visible wheels, windshield, owner-colored outline
- **Variable drive speeds**: Lowrider 0.42 (slowest) vs Drag Racer 2.2 (locked, fastest)
- **Car abilities**: RAM (Muscle Car double hit), NITRO (GTR speed burst), ARMORED (Pickup)
- **GTA street arena**: Asphalt + lane markers + sidewalks + crosswalk + traffic lights + graffiti
- **Deck picker screen**: Pick 8 cars from your collection before battle
- **Main menu revamp**: Night city skyline, neon road, trophy display
- **Mode select screen**: 1v1, Ranked (working), 2v2 and 3v3 (Coming Soon)
- **Garage screen**: View all 12 cars, locked ones show "CAR PASS"
- **Store screen**: Car Pass S1 panel + chest tiers (Silver/Gold/Legendary)
- **Post-game rewards**: Trophy delta, coin/star rewards on win

---

## Car Roster (v0.2)

### Unlocked (8)
| Car | Cost | Speed | Role |
|-----|------|-------|------|
| Muscle Car | 3 | 0.9 | Melee brawler, RAM doubles first hit |
| Lowrider | 3 | 0.42 | Heavy tank, tons of HP |
| GTR | 4 | 1.55 | Fast assassin, NITRO burst |
| Pickup | 5 | 0.48 | Building-only tank |
| Bike Duo | 3 | 1.85 | Fast ranged pair |
| Van | 4 | 0.82 | Long-range sprayer |
| Molotov | 4 | spell | Area fire damage |
| EMP | 3 | spell | Wide energy blast |

### Locked -- Car Pass (4)
| Car | Cost | Speed | Notes |
|-----|------|-------|-------|
| Monster Truck | 7 | 0.35 | Area damage on every attack |
| Armored SUV | 5 | 0.78 | Blocks first spell hit |
| Drag Racer | 4 | 2.2 | Fastest unit, glass cannon |
| Oil Slick | 2 | spell | Slow + DoT |

---

## Research Findings (Hive Mind + Everlight Researcher)

### Market Opportunity
- Strategy games = 21.4% of mobile revenue, only 4% of downloads (best ROI ratio)
- No major card-battler uses urban/car aesthetic -- this lane is wide open
- Clash Royale: $452M revenue in 2025, $0.21 ARPDAU (double industry average)

### Breeding Mechanic (Dragon City -- translate to "Chop Shop")
- Two parent cars go in, randomized hybrid comes out
- Variable ratio reinforcement = most addictive reward schedule (Skinner box)
- Dopamine spikes during the REVEAL animation, not just on rare outcomes
- Monetize: speed-up timers, extra Chop Shop slots, event-exclusive cars
- Call it the "CHOP SHOP" -- fits the urban aesthetic perfectly

### Monetization Stack to Build
1. **Crew Pass** $9.99-$12.99 / 35-day season (primary recurring anchor)
2. **Gem IAP** -- direct currency purchase (impulse trigger)
3. **Revival Packs** $2.99-$4.99 at loss streaks (biggest uplift driver)
4. **Cosmetics only** -- skins, emotes, no P2W
5. **Clan Gifting** -- Pass holders auto-gift to crew (social obligation retention)

### Visual Direction
- Primary: Stylized 3D cars with hand-drawn GTA-style card art
- Palette: Midnight black + concrete grey + chrome + neon (orange/teal/purple)
- Arenas: Isometric city blocks -- parking structure, strip, intersection, rooftop
- UI: Dark dashboard feel, chrome type, speedometer motifs
- DO NOT use GTA branding/fonts -- aesthetic inspired by, not licensed

### ASO Keywords (own these early -- no incumbent)
- Primary: "car battle game", "street racing strategy", "card battle cars"
- Long-tail: "Clash Royale with cars", "urban car strategy game", "car deck builder"
- Seasonal: SEMA Show (November), car show season (June-August)
- Icon: Bold stylized car on dark background
- First screenshot: cars in active battle
- Preview video hook: car reveal or destruction in first 2 seconds

---

## Roadmap

### Phase 1 -- Browser Prototype (DONE)
- [x] Core gameplay loop
- [x] Car-themed units and towers
- [x] GTA street arena
- [x] Deck picker
- [x] Menu screens with Store/Garage
- [x] Variable speeds per car type

### Phase 2 -- Feature Additions
- [ ] Chop Shop (breeding) -- random car fusion
- [ ] Persistent deck saves (localStorage)
- [ ] Sound effects + music (engine revs, screeches, explosions)
- [ ] More arena skins (Parking Garage, Rooftop, Freeway)
- [ ] City-specific arenas: LA hoods, Miami strips, NYC blocks

### Phase 3 -- Multiplayer
- [ ] WebSocket 1v1 real-time PvP
- [ ] 2v2 Turf War mode
- [ ] Leaderboard / trophy tracking backend

### Phase 4 -- Monetization
- [ ] Crew Pass implementation
- [ ] Chest opening animation
- [ ] Revival pack popup (triggered at loss streak)
- [ ] Gem shop

### Phase 5 -- Polish
- [ ] Actual car artwork (not emoji icons)
- [ ] Drive animations (wheels spinning, exhaust, nitro trails)
- [ ] Character portraits for crews
- [ ] Collision sparks, burnout effects
