# ALLEY KINGZ -- DESIGN BIBLE & API CONTRACT
### The engine-agnostic spec the Unity 3D build converts from
*Authored 2026-07-03 by Lucrex. Source of truth = the shipped Canvas2D web build at alleykingz.online (the proven, balanced, retentive reference). This document is what carries over untouched; only rendering/input/UI get rebuilt in Unity.*

---

## 0. CONVERSION DOCTRINE
- **This is a CONVERSION, not a teardown.** The web build is the playable reference + design bible. Unity re-implements rendering/input/UI in C# against this spec.
- **Carries over untouched:** the entire Supabase backend (auth, crews, chat, presence, pass, quests, cosmetics, grants -- engine-agnostic edge functions Unity calls verbatim), all game design + tuning below, the $BCARDD brand/lore/cinematics.
- **Gets rebuilt:** Canvas2D drawImage/DOM into C# + 3D scenes.
- **DUAL-TRACK:** keep the web build live as the instant-play, no-install, viral ?ref= top-of-funnel demo. Its job = hook in 30 seconds, convert to the premium Unity app. Web = acquisition; Unity = retention/monetization depth.
- **Free-first** still governs asset production (Blender + Rigify, AI concept refs).

---

## 1. CORE LOOP CANON
1. **TOWN HALL** gates buildings + builders + the DECK CARD-LEVEL MAX. Deck strength is capped by Town Hall level.
2. The city is run by the **11-CARD DECK** -- assign cards to buildings by TRAITS + FACTIONS.
3. **RAID STAKES:** getting raided drops your Town Hall/buildings, so your deck is no longer max level. Defense matters.
4. **TWO combat modes (never conflate):** TOWER LANE BATTLE (engine.js, Clash-lane) vs WORLD-MAP RAID (in-hub raid -- you walk the opponent's district rendered by the SAME hub renderer, wreck it, win = core cracked into star-scaled loot).
5. **Death goes to INFIRMARY** (heal before reuse).
6. **Crops** = tradeable currency + missions. **Wood/stone** = FORTIFY districts vs raids.
7. **Card unlock = exactly 3 paths:** wild-encounter win (copy), Town Hall upgrade, shop.
8. **Navigation law:** every wild encounter / raid / task / mission returns to the walkable DISTRICT MAP. Only entering the Town Hall building shows the main menu. Death spawns at the Infirmary. (Real-life logic: left is left everywhere; walls rotate in 90-degree steps.)

---

## 2. ECONOMY & CURRENCIES
| Currency | Type | Source | Sink | Notes |
|---|---|---|---|---|
| coins (GOLD) | soft | matches, jobs, production | upgrades, cards, recolor cosmetics | client-writable |
| gems | **premium** | Stripe ($4.99/500 .. $99.99/14000) | crates, rarer cosmetics, pass premium | **SERVER-ONLY** (never client granted/spent; audited) |
| bones | skill/soulbound | arcade, duties, hit-list | crate skip, skills | client-writable |
| scrap | dupe | dupes, raids | card copies | per-rarity |
| keys | chest | fragments, day-7 streak | open crates | forged |
| wood/stone/metal | harvest | raids, gardens, nodes | fortify, sells | material |
| produce | tradeable | gardens | trade, missions | peasant resource |
| crops | harvested | garden plant->grow->harvest | trade, missions | timed |

**Pricing law (tutorial-canon):** "Gems only skip waits and buy looks, never power." Cosmetic price ladder reuses GEM_PER_COPY: {Common:2, Rare:10, Epic:50, Legendary:500, Mythic:2000} gems (or gold for common recolors).

**Rarity ladder (canonical, engine.js RARITY_COL):** Mythic > Legendary > Epic > Rare > Common. Cards carry rarity + isMythic.

---

## 3. CARD ROSTER & STAT SCHEMA
- **111 cards** + 6 handlers, keyed by cardNumber (0001 = $BCARDD, Mythic king). Canonical data in canon.js; resolver akCardArtRel(card) returns cards/<NNNN>_<slug>.webp (png fallback).
- **Combat classes** (drive the walk/engage clip fallback + role shape): assassin, bruiser, caster, marksman, summoner, support, structure.
- **Variants** (e.g. [HEAVY] +HP vs [STREET] +dmg glass-cannon) are SEPARATE cards with their own cardNumber/stats -- a gameplay build, NOT a skin.
- Stats per card: HP, dmg, rarity, family, combatClass, faction, weaponType, silhouetteSeed. (Port the table verbatim.)

---

## 4. RETENTION SYSTEMS (timings are tuning -- port verbatim)
- **Daily streak (Block Tribute):** 30-day ladder, deterministic (n-1)%len. Day 7/14 = chest key, Day 21 x2, **Day 30 = Legendary crate + 1000 gold + 40 bones + 1 key**. Loops with per-week mult capped x5. Server check-in rail (season Marks) rides the same claim.
- **Timed-unlock crate slots (Clash-style):** 3 slots. Durations by rarity: Common 15m, Rare 3h, Epic 8h, Legendary 12h, Mythic 24h. Skip = bones (1 bone / 6 remaining min). Claim rolls rarity (Common70/Rare22/Epic7/Mythic1) then a variable-ratio suspense reveal (near-miss overshoot, always lands true). Slots full = instant-open fallback.
- **Ranked ladder:** 7 tiers (Stray, Pup, Runner, Warrior, Enforcer, Right Paw, King of the Block). Rep swing +20 win (+3/gate) / -12 loss, demotion protection. Monthly soft-reset + seasonal exclusive dog. Promotion fires a shareable levelup clip.
- **Battle pass (Alley Pass):** 30 tiers, free + premium lanes (premium 800 gems). XP from matches.
- **Seasons:** 6 chapters (Junkyard Dynasty, Neon Howl, Dog Days, Blood Moon, Frostbite, Golden Leash), world re-theme + faction, daysLeft countdown, Marks reset at chapter boundary. Win = 6 Marks (daily-capped 60).
- **Quests (5 layers):** match sidequests, daily clan duties (win-tower/run-raid/stand-watch), weekly duties (bigger targets, same metric bumps), server hit-list (daily+weekly), flywheel "TODAY ON THE BLOCK" agenda ("what next"). Hit-of-the-Day bounty (bones, once/PT-day).
- **Stamina:** 12 max, ~8h regen, refill 20 bones. Meters reward-raids only. Arcade daily caps (gold 500, bones 20, etc.).
- **Post-match "one more thing" nudge:** single line from rank distance / daily progress / streak / pass tier. Every session ends with a hook, not a conclusion.

---

## 5. RAID SYSTEM
- **Multi-district:** opponent base = 2-3 walkable districts (own art per rival, 4 layout templates: ring/grid/cluster/fortress). Town Hall in the last district. E/W edge-walk swaps districts.
- **Victory:** the instant ALL defenders are cleared OR core destroyed OR all structures down (not just the 90s timer). Core kill = 3 stars.
- **Difficulty (competitive-but-winnable):** 14 defenders, HP 220+tier*24, ~1/3 ranged, no passive leash (hold ground + chase), defender melee 14 / ranged 12, buildings (core+METAL+STONE+producers) shoot 12. Player 100 HP, energy regen +7/s, 2 allies.
- **Player arsenal (rebalanced, akfx.js):** bolt 42/0.75s, beam 120/5s, nova 60 AoE/8s, chain 130/9s, dot 24tick/5s, nuke 360 AoE/42s. No board-clear-on-cooldown.
- **Mine & steal:** harvest nodes (tree->wood, scrap->scrap, garden->produce) inside enemy bases -- attack to deplete, drops to your bag alongside building loot.
- **Loot:** star-scaled; retreat keeps what you grabbed. Loss downs your hero to the Infirmary.

---

## 6. MOVEMENT & ANIMATION
- Every animal (hero + roamer bots + battle units) uses **live walk/idle clips**, never a static card. Side clip mirrors by travel direction (mind native-facing per asset). Battle units walk toward each other, counter-rotated upright.
- Clip registry (AK_CARDFX): assets/cardfx/<cardNumber>_<state>.mp4 then class_<combatclass>_<state>.mp4. States: idle, engage, vs_structure, walk. Pooled (max 8), LRU.
- **In Unity:** these become skeletal animation states on the rig; the per-card to per-class fallback becomes an animator override controller.

---

## 7. COSMETICS -- PAPER-DOLL TO 3D SOCKET MAP (the key port)
The Canvas2D paper-doll is the **exact same modular concept as the 3D rig** (rig once, swap parts). **Author the Unity rig sockets with THESE names so the cosmetics catalog + ownership ledger port 1:1:**

| 2D slot | 3D socket | Anchor (frac of dxd square) | Example parts |
|---|---|---|---|
| head | Head_Socket | y 0.02-0.30 | crown_gold (Legendary), cap_snap (Common) |
| eyes | Eyes_Socket | y 0.30-0.45 | aviator_flag (Epic), shades_black (Common) |
| neck | Neck_Socket | y 0.55-0.70 | chain_dollarb (Epic), rope_bone (Common) |
| muzzle | Jaw_Socket | y 0.42-0.52 | cigar_gold (Rare) |
| torso | Spine_Socket | y 0.55-0.95 | jacket_varsity (Rare), tank_wife (Common) |
| hand | Hand_R_Socket | x 0.70-1.0 | bat_spike (Rare) |

- **Draw order (back-to-front):** torso, neck, muzzle, head, eyes, hand.
- **Part descriptor:** {id, slot, rarity, name, img, dx, dy, scale} on a canonical square. In Unity = a prefab per part parented to the socket.
- **Equip model:** per-card + squad-wide default; persisted client-side + server ownership via ak-cosmetics.
- **Monetization tiers (Brawl-Stars model):** recolors (palette swap, cheapest, many), then accessory swaps (parts, mid), then legendary full-render skins (few, premium). $BCARDD identity is FIXED (white Dogo, cropped ears, crown, flag aviators, dollar-B chain, cigar); wardrobe flexes.
- **$BCARDD canon lock:** never mix his identity; wardrobe/accessories vary, the dog does not.

---

## 8. SOCIAL / MULTIPLAYER
- **REAL (Supabase, live):** auth (Google OAuth), crews/clans (ak-crew: create/join/leave/list/mine, donations, grants inbox), world+crew chat (ak-chat + Realtime presence), revenge pings. 50-member crews, faction/tag/trophies/privacy.
- **SIMULATED (cold-start, deterministic seed):** 29 bots (4 clans x 6 + 5 strays), Street Talk feed (bot actions + overnight chaos + hit-of-day), hourly Fence listings, up to 3 walking roamers/district. **Ghost clans** backfill the crew browser when empty so a new player never sees an empty room.
- **Viral loop:** ?ref= invite link + 9:16 branded clip capture (win/killstreak/raid_win/chest/levelup). Invitee welcome bonus on first run; inviter credit via grants (server).
- **Leaderboards:** global/rival + crew/friend board + "passed you" ping.
- **SPEC-ONLY (deploy for full MMO):** ak-raid edge fn (raiding real players' persisted bases) -- today raids are simulated. **First Unity-era backend task.**

---

## 9. SUPABASE API CONTRACT (engine-agnostic -- Unity calls these verbatim)
Base: https://<project>.supabase.co. Auth: Google OAuth (ak_account). Edge functions, {action, ...} payloads:
- ak-crew : {create|join|leave|list|mine|don-request|don-fill|don-list|claim-grants|referral}
- ak-chat : send + Realtime subscribe (world/crew), ak_chat_messages, ak_raid_revenge
- ak-pass : reportMatch, tier/xp, premium unlock
- ak-quests : reportMatch/reportEvent, claim via grants
- ak-cosmetics : {get|buy, id} ownership ledger (extend for paper-doll parts)
- ak-gems / Stripe : premium currency (server-authoritative)
- ak-raid : **TODO/spec-only**: publishMyBase, targets, resolve, revenge, buy-shield
Client shared module for all calls; NEVER write gems/premium economy client-side.

---

## 10. CINEMATIC / MEDIA CHAIN
- **Chain of command:** Higgsfield (best, Kling PRO min, MCSLA film-language) > Seedance > Leonardo > Cloudflare (free). Tier by player impact.
- Every big moment = a shareable MP4; interactions sandwich MP4s around static images. No android emoji anywhere -- custom art only.
- **In Unity:** cinematics stay as MP4 (video player) or become in-engine sequences; the brand/palette (gold #D4AF37, dark, Playfair/Inter) is set.

---

## 11. WEB BUILD FILE MAP (reference for the port)
- index.html = hub/district map (Canvas2D) + raid engine. game.html = tower battler + lobby. Shared state via localStorage + Supabase.
- Logic modules (engine-agnostic, port as C# services): economy.js (AK_ECON), systems/population.js (AK_POPULATION cold-start), systems/seasons.js, systems/missions.js (duties), systems/loops.js (reveal), systems/flywheel.js (agenda), pass.js, quests.js, social.js (crews), drip.js (cosmetics), systems/cardfx.js (clip registry), systems/viral.js (share loop).
- Data: canon.js (roster), classes.js, handlers_data.js, cards_lore.js.

---

## 12. UNITY BUILD ORDER (recommended)
1. Import the Supabase SDK + wire the existing edge functions (backend works day 1).
2. Build the rig ($BCARDD + gang) with the Section-7 socket names; import cosmetic parts as prefabs.
3. Port the data tables (Sections 2-3) as ScriptableObjects.
4. Re-implement the two combat modes + district map (Sections 1, 5) against the tuning here.
5. Wire retention systems (Section 4) -- mostly UI over existing server state.
6. Ship dual-track: web funnels to app (Section 0).

*Cost reality (eyes open): 3D dog models + rigs are the real new line item (modular parts keep it manageable), plus app-store review/distribution. Not the license.*

---
*This bible is living. Update it as web-build tuning changes so the Unity target never drifts. Companion memory: project_ak_unity_conversion_dual_track, project_ak_core_loop_canon, feedback_ak_cinematic_viral_growth_model.*
