# Alley Kingz -- COMBAT DIRECTION (operator playtest, 2026-06-27)
*How map/encounter/raid combat must FEEL. Folds into the captivation build + the world-map combat lane. Source of truth alongside AK_CORE_LOOP_CANON.md.*

## THE DIRECTION: real-time action RPG/MOBA on the map (Mobile Legends + Twisted Metal)
Right now the map combat is the tower-lane engine or quick mini-games -- static. The operator wants the WORLD-MAP / encounter / raid combat to be a LIVE, real-time, in-motion ACTION battle:
- **Mobile Legends feel:** you control your dog in real-time, MOVE around the arena, and FIRE the card's ABILITIES/SPELLS in real-time (not auto, not turn-based). Your cards fight as UNITS that use their REAL skills + stats (each canon card has an `ability` -- USE it). Show the card, its skill, its stats, MOBA-style.
- **Twisted Metal (PS2) vibe:** an arsenal -- you can drive/strafe and SHOOT lasers/projectiles at the enemy in real-time. Vehicular/projectile chaos energy. An "arsenal" of attacks the player picks from.
- **Inotia-style:** walking down a district, you REALLY have to fight -- spells + lasers + dodging -- a real interactive battle on the map, not a popup.

## WHAT THIS MEANS (build, not a new engine)
- The surface ALREADY EXISTS: `AK_MODES.openWorldMoba` (modes.js) -- a real-time ctx.overlay unit-fight with a hero, ability buttons (BTN.ult / BTN.blast), kstreak, and type advantage. The raid fix (2026-06-27) already routes raids here. ENHANCE openWorldMoba into the full real-time-MOBA feel below. engine.js (the tower lane) stays FROZEN + reserved for the ARENA door only.
- ENHANCE openWorldMoba: (1) real-time player MOVEMENT (drive/strafe) + AIM/FIRE projectiles (lasers) on a cooldown -- the Twisted-Metal arsenal; (2) each deployed CARD uses its OWN `ability` (canon card.ability) as a castable SPELL with its real stats (hp/damage/range/attack_speed from the card) -- shown MOBA-style (skill icons, cooldowns, HP bars, stat readout); (3) an ARSENAL bar -- the player picks abilities/spells to fire; (4) escalating spectacle (the killstreak DOG-GOD already feeds this) + the needle-drop audio.
- KEEP the mini-games (street fight, etc.) + mini-missions as SUBSETS/flavor -- do NOT remove them. They sit alongside the real-time map battle.
- This applies to: world-map RAIDS (done routing -> openWorldMoba), wild ENCOUNTERS (the long-fuse standoff leads INTO this real-time fight, not just leash-throws), and mission-objective fights.

## WHY (captivation)
A static popup fight is not captivating; a real-time skill battle where you dodge, aim, and unleash your dogs' spells IS -- it rewards mastery, it is different every time, and it is the RPG/MOBA core the operator keeps pointing at. This is the combat half of "immersive but not captivating."

## FOLD-IN
Add a WORLD-MAP REAL-TIME COMBAT lane to the upcoming captivation build: enhance openWorldMoba (real-time move + arsenal/laser fire + card-ability spells with real stats + MOBA HUD), wired as the combat for raids + encounters + mission fights. Mini-games remain subsets. Sensory package mandatory (it must look + feel good).
