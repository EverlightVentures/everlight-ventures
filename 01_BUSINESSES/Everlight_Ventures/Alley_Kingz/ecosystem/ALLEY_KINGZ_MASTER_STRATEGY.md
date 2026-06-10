# ALLEY KINGZ -- MASTER STRATEGY (definitive)
**Date:** 2026-06-07 | **Author:** Creative Director (Hive synthesis, phase 9 of 9)
**Status:** CANONICAL gameplay + live-ops spine for **Pillar 2 (THE GAME)** and the economy that rides it.
**Sits under:** `MASTER_BUILD_PLAN.md` (the 5-pillar ecosystem spine -- coin/game/NFT/arcade/metaverse). This doc does NOT re-open the locked ecosystem decisions (Solana-native, 48 cards, Option A legal, coin-first); it specifies *what the game actually is and how it ships*.
**Synthesized from (provenance cited per section):** `research_mlbb.md`, `research_clash.md`, `research_td.md`, `design_multimap.md`, `design_buffs.md`, `design_economy.md`, `design_tech.md`.

---

## 0. THE ONE-PARAGRAPH VISION

**Alley Kingz is a 4-minute, one-thumb tower-lane battler that goes somewhere.** Cyberpunk dog crews pilot Twisted-Metal war-rigs and fight Clash-Royale elixir-tempo lanes -- but instead of one static arena, **every match is a convoy run down a 4-district road** (the Alley -> the Empire), the camera panning to a new district each minute as the pace ramps 0.75x -> 4x. The alley itself turns on you: a **Storm Clock** rolls telegraphed, fixed-stat, symmetric map events from a public menu (lightning over the lot, scrap rain, a feeding frenzy, a flood surge), so chaos is something you *plan around*, never something you *lose to*. A **mini-boss gate** blocks the road out of each district; clear it fast and you bank the lead and roll on early. Underneath sits an ownership layer no Supercell game can match -- the cards ARE Solana NFTs, the chips ARE $BCARDD -- but **never as power, only as flex**. We are stealing the single best mechanic from four genres and fusing them onto the engine we already shipped: **Clash Royale's elixir tug-of-war + Merge Tactics' auto-merge sibling mode + Mobile Legends' rotation/objective drama + dungeon-TD's boss-gated staircase**, all wrapped in a dog-crew cyberpunk skin we already have on disk.

**The fusion, one line each (which research fed it):**
- **Clash Royale (`research_clash.md`):** the slow, capped, shared-clock elixir engine + dual-lane tower win-condition + 8-card deck + battle-pass spine + collection-wide "Crew Level."
- **Merge Tactics (`research_clash.md` Part 2):** a second genre off the same 48-card art library -- the **Garage Brawl** auto-merge mode (cosmetics-only monetization).
- **Mobile Legends (`research_mlbb.md`):** the **turret ratchet** (ordered, irreversible checkpoints = an advancing frontline), **rotation as the core skill** (purposeful relocation), the **3-act escalation arc**, and the **glanceable auto-threat minimap** -- all re-expressed as the convoy travelling the road.
- **Dungeon-TD / roguelike (`research_td.md`):** the **shared mid-match mini-boss gate** with a comeback-tuned reward, **staircase difficulty** (spike-then-plateau), **clear-speed = tempo currency**, and **mirrored server-seeded affixes** (chaos that is identical for both sides = provably fair).

---

## 1. WHAT ALREADY EXISTS (the load-bearing reuse insight)

*(Source: `design_tech.md` reuse audit + `design_multimap.md` section 0.)*

The prototype already ships **"4 of everything,"** and they were simply never wired to one axis:

| On disk today | Count | Becomes |
|---|---|---|
| `TIER_SPEED=[0.75,1.5,2.0,4.0]` + `matchTier()` | 4 | the 4 section clocks (pace ramp) |
| `PHASE_LABELS` dog-pun callouts | 4 | the 4 district names + transition banner |
| `assets/arena/*.png` (lot/neon/industrial/docks) | 4 | the 4 district backdrops |
| `assets/music/*.mp3` | 4 | the 4 district music loops |
| `assets/arena/towers/*` skin sets | 4 | the 4 district garrison skins |
| `ARENA_DIFFICULTY {0,3,5,7}` | 4 | the 4 district AI difficulty rungs (the staircase) |
| 4 factions (Boneguard/Zoomie/Leashbreak/K9) + `CANON_DECKS` | 4 | the 4 district garrison crews |

The engine (`engine.js`, ~1302 lines) is DOM-free behind `window.AK`; the renderer/input lives in `index.html`. **Multi-map is binding section index `0..3` to all of the above at once.** The combat machinery is already **multiplier-stacking-shaped**: `computeSynergy()` writes per-unit `synergyMul` that the getters (`getSpeed/atkInterval/doAttack/maybeFireAbility`) read -- a chaos buff is *one more multiplier layer*. `castSpell`/`applySplash` already does "apply an area effect at a point" -- a map hazard is `castSpell`-shaped. `matchTier` is already a time-driven global state machine that fires an event and flashes an HUD banner on transition -- it **is** the chaos-event scheduler template. **The genuinely net-new work is only the camera/scroll + the section world-model; everything else is reuse.**

---

## 2.-1 PACING UPDATE (operator-locked 2026-06-07) -- 45s stages + transition telegraph
Match shortened for mobile punch (Clash is ~3min for a reason): **each stage = 45 seconds**, 4 stages =
**3:00 total** (was 60s/4:00). Section-advance time floor -> 45/90/135s (was 60/120/180); `MATCH_TIME` 240->180;
the pace ramp (0.75/1.5/2/4x) compresses into the 3-min arc. **Transition telegraph:** ~10s before each
stage change a "**NEW PHASE INCOMING**" alert appears, then the last 5s is a **5-4-3-2-1 countdown** into the
choreographed transition (the cooldown/LEVEL-PASSED/troop-reset already built). Builds anticipation + lets
players pre-load a push to exploit the speed-up. Stage length is a tunable const -- easy to dial 45<->60 on feel.
*(Build: edit matchTier thresholds + MATCH_TIME + a pre-transition telegraph in the HUD; applies after the
deck-builder agent finishes editing the engine, to avoid a file collision.)*

## 2.0 THE WORLD SCALE -- 10 CITIES x 10 LEVELS x 4 MAPS = 400 (operator-locked 2026-06-07)

**Confirmed scope (Rich): 400 unique maps.** The structure, Monopoly-GO / Spyro style:
- **10 ARENAS = 10 distinct CITIES**, connected by a **Spyro-style overworld mini-map** you travel across:
  `the_lot` (junkyard slum) -> `neon_night` -> `golden_industrial` -> `rain_docks` -> `undercity_subway` -> `skyline_rooftops` -> `toxic_sewers` -> `casino_strip` -> `frost_district` -> `crown_citadel` (the Empire, $BCARDD's throne). Junkyard -> Empire.
- **Each arena = 10 LEVELS** (rungs). **Each level = 4 MAPS** (the within-match convoy: gate -> market -> works -> core, themed to that city). **You must pass all 4 maps of a level to unlock the next level**; clear all 10 levels to travel to the next city.
- **= 10 x 10 x 4 = 400 unique map backgrounds.** Within a city the 10 levels ESCALATE (per-level time/weather/intensity shift: clear day -> dusk -> night -> fog -> rain -> storm -> embers -> neon-overload -> apocalyptic) so each level looks like going deeper into that city.
- **Sensory per city:** its own MUSIC track (10 themes; 4 originals exist, 6 new generating now) + tower skins + garrison crew + storm-event palette. The full package travels with the convoy.
- **GENERATION PIPELINE (the only sane way to make 400):** `art/generate_world_maps.py` -- data-driven, 10 cities x 10 levels x 4 districts, themed+escalating prompts, batchable + idempotent. Outputs `game/assets/maps/<arena>/L<NN>_<district>.png` + `game/assets/music/<arena>.mp3`.
- **CADENCE / COST (free-first):** Leonardo free tier ~10-15 imgs/day -> 400 maps ~= 30-40 days of daily batches (cron-able), OR a paid Leonardo tier ~$8 does all 400 fast, OR the HuggingFace-free fallback (no daily cap, slower). Operator picks the speed; the pipeline is the same.
- **ENGINE:** the convoy mechanic (Track 1, building now) stays the same; it just loads the section backdrop/music/skins by **(arena, level, district) index** from the maps manifest instead of 4 hardcoded files. The 4-map-per-match convoy IS the level; the trophy/ladder (2.2a) climbs levels; the overworld picks the city.

## 2. THE MULTI-MAP + CHAOS-BUFF DESIGN (merged + reconciled)

This is where the two design agents had to be reconciled. **They were operating at two different scales and collided on the phrase "4 maps = 4 factions." Resolution below.**

### 2.1 THE TWO AXES (the reconciliation -- READ THIS FIRST)

*(Conflict: `design_multimap.md` makes "4 districts" a WITHIN-match journey; `design_economy.md` makes "4 maps" a META campaign ladder across many matches. Both are right at their own scale.)*

- **AXIS A -- THE CONVOY RUN (within one 4-minute match).** Every match travels **4 sections** (`game.section` 0..3), one per pace tier. Source: `design_multimap.md`. The 4 sections are always the dramatic journey **Lot -> Neon -> Industrial -> Docks** (the alley to the empire), with the garrison crew, difficulty, music, backdrop, and affix swapping each minute. This is the moment-to-moment heartbeat of *every* match.
- **AXIS B -- THE NOS LADDER / CAMPAIGN (across many matches).** The meta progression is the 10-rung NOS trophy ladder, grouped into **4 chapters/regions** themed to the 4 factions, each capped by a **named meta mini-boss** that gates ladder advancement. Source: `design_economy.md`.

**The clean resolution = TWO TIERS OF BOSS:**
1. **District Gate (within-match, Axis A):** each section's enemy king tower is *promoted* to a beefier "District Gate" mini-boss. Generic, faction-flavored, appears every match. Clearing it = checkpoint cleared, roll on early. Source: `design_multimap.md` sec 5.
2. **Named Mini-Boss Gate (meta, Axis B):** at the end of each NOS *chapter* sits a named, hand-tuned boss -- **Stonejaw -> Jagged -> Rosco -> Crown Foxhound -> (final) $BCARDD "Crownbreaker"** -- that you cannot pass until you beat it, gating the next region of the ladder. This is the Dead Cells "boss-stem-cell" escalation. Source: `design_economy.md` sec 1.

So a player fights **District Gates every match** (the within-match drama) and **named Mini-Boss Gates at chapter boundaries** (the campaign wall that drives upgrade demand). No collision: the within-match convoy uses the 4 factions as its rotating garrison flavor; the meta ladder uses the 4 factions as its 4 chapter themes. Both consume the same 48-card / 4-faction canon.

### 2.2 THE CONVOY RUN -- the 4 within-match sections (Axis A)

*(Source: `design_multimap.md` sec 1, table reconciled with `design_economy.md` faction map.)*

| s | District (= `PHASE_LABELS[s]`) | Art / music | Pace | Garrison crew | AI diff | Section-entry affix (symmetric) |
|---|---|---|---|---|---|---|
| 0 | **SNIFFIN' DIRT** (The Lot) | `the_lot` | 0.75x recon | Boneguard (tanks) | 0 | none -- teaching district |
| 1 | **MARKIN' TERRITORY** (Neon Night) | neon | 1.5x | Zoomie (speed) | 3 | **ZOOMIES**: +25% move, +energy regen |
| 2 | **OFF THE LEASH** (Industrial) | industrial | 2.0x | Leashbreak (tech) | 5 | **OVERCLOCK**: +50% energy, -30% spell CD |
| 3 | **THAT'S MY SQUIRREL!** (Rain Docks/Empire) | docks | 4.0x sudden death | K9 (turret/range) | 7 | **STORM SURGE**: tower HP -25%, splash +20% |

**Section advance = `max(timeTier, gatesCleared)`** -- the clock is the floor (the convoy always rolls forward at 60/120/180s, preserving the 4-min match length and the existing pace ramp), but **clearing a District Gate early pulls you forward early** -- which also pulls the *speed-up* forward early. That is `research_td`'s **clear-speed = tempo currency**, made literal. *(Source: `design_multimap.md` sec 4.)*

**Carry-over rules (the "ride with the convoy" feel):** player units + player towers + energy + crowns **carry across all 4 sections**; the enemy garrison + its towers **reset fresh per district**. A clean Gate clear heals surviving player units ~25% and repairs player towers ~15% (the comeback equalizer -- it rewards the player's *clear*, it never secretly buffs the AI). A missed Gate sends 1-2 "Pursuer" units as chip pressure but never ends the run. *(Source: `design_multimap.md` sec 6 + sec 5.5.)*

**Scoring** = cumulative crowns over the run (each garrison princess +1, each Gate cleared +1 and a star). Match ends at the 4:00 clock (Empire district) on total crowns, OR early on a total rout (player king down = defeat; all 4 Gates cleared early = "CLEAN SWEEP" victory). *(Source: `design_multimap.md` sec 7.)*

### 2.2a TROPHY STRUCTURE (operator-locked 2026-06-07)
Crowns are the *within-match* tally; **TROPHIES are the ladder currency**, mapped onto the convoy:
- **Each of the 4 districts (maps) cleared in a match = 10 trophies** -> **up to 40 trophies per match** (a CLEAN SWEEP = all 4 districts = 40). Partial runs bank trophies per district actually cleared, so even a loss can pay.
- **Each ARENA = 10 levels** (rungs). Trophies climb you through the 10 levels of an arena, then promote you to the next arena (the 4 faction-themed chapters of the NOS ladder, sec 3). 
- **Difficulty rises as you climb** -- within a match across the 4 districts (AI rungs 0/3/5/7, sec 2.2 table) AND across arenas/levels as the ladder bands up (the staircase, `research_td`). 
- This binds the within-match convoy (Axis A) directly to the meta ladder (Axis B): a match's 0-40 trophies feed the 10-level arena climb. **The full sensory package travels with it** -- each district swaps backdrop + music + tower skin + garrison + affix, so climbing literally looks/sounds like advancing to a harder place.
- *(Build note: TRACK 1 G4.2 emits 10 trophies per District Gate cleared; TRACK 2 M4 consumes them into the 10-level x N-arena ladder. Trophy values are tunable.)*

### 2.2b TWO MODES (operator-locked 2026-06-07 -- build TROPHY mode now, RANKED later)
- **TROPHY MODE = the current focus.** Progressive **PvE / bot** play: the convoy ladder vs AI garrisons of
  rising difficulty, earning the 0-40 trophies per match to climb the 10-level arenas. Everything we are
  building NOW (the convoy, Storm Clock, District Gates, trophy road, card/tower leveling 1->10) is Trophy Mode.
- **RANKED MODE = later.** **PvP vs real ranked players** -- and it is essentially a **carbon copy of Trophy
  Mode with a live human opponent instead of a bot** (server-authoritative, mirrored seeds, NOS-banded MM --
  sec 3.5 / Track 2 M7). We do NOT build ranked until trophy mode is proven fun; the trophy build IS the
  ranked build minus the netcode opponent.
- **Player progression:** every player starts fresh at **level 1** (level-1 cards + towers) and climbs toward
  **level 10**, getting more competitive along the way (the copies-to-upgrade sink, 3.2a). The trophy road is
  the spine of that climb.

### 2.3 THE STORM CLOCK -- the chaos-event engine (the superset)

*(Conflict resolved: `design_multimap.md` proposes 4 fixed per-district affixes; `design_buffs.md` proposes a richer 9-event Storm Clock on its own ~50s cadence. Resolution: **the Storm Clock is the engine; the 4 per-district affixes are its first 4 catalog entries that fire on section-entry.** `design_buffs.md` explicitly designed the scheduler to be section-agnostic, so they unify with zero conflict.)*

The Storm Clock rolls **TELEGRAPH -> ACTIVE -> BREATHER** windows (~50s) from a tier-gated weighted pool, escalating with the pace staircase. **The public menu of 9 events** *(Source: `design_buffs.md` sec 3)*:

- **4 HAZARDS** (threats, hit cells not auto-locked units -> good spacing dodges them): **Junkyard Lightning** (the operator's example -- ~7 telegraphed strikes/window, both domains, no tower damage), **Scrap Rain** (the only sieger, 50% tower damage, rare + heavily telegraphed -- the late big-swing), **Flood Surge** (ground-only river band, knockback + slow -> rewards air decks), **Drone Sweep** (air-only strafe -> punishes flyer stacks).
- **4 FIELD BUFFS** (symmetric global multipliers): **Zoomies** (+25% move), **Overclock** (+50% energy, -30% spell CD = Clash double-elixir evolved), **Alley Smog** (towers/ranged -30% range, zero damage = a pure tactic-shifter), **Glass Bones** (+30% all damage = the sudden-death amplifier).
- **1 OBJECTIVE:** **Golden Hour ("$BCARDD's Blessing")** -- a contested center heal/shield zone = the scheduled flashpoint + comeback spine, and the $BCARDD-flavored tie-in to the coin.

**The 8-rule Fairness Doctrine is non-negotiable** *(Source: `design_buffs.md` sec 6)*: **symmetric** (both sides eat the identical event at the identical second), **telegraphed** (banner >=8s, per-strike reticle >=1.4s), **fixed stats** (frozen catalog, surfaced on a studyable "Storm Codex" screen), **known menu** (only when/where rolls), **no rubber-band** (events never read the score -- the only comeback path is contesting the symmetric Golden Hour), **positional dodge** (hazards hit cells -> spacing is the skill hook AND the cross-board fairness trick), **capped stacking** (`eventMods x synergy x pace` clamped: move <=2.0x, dmg <=1.8x), **damage-budgeted** (a fully-ignored hazard window threatens <=~18% of a tower -- chaos punishes mistakes, it does not decide games). **All Storm Clock timers tick on REAL wall-clock dt, never sim-dt** -- so an 8s warning stays readable even during the 4x final-minute blitz. *(Source: `design_buffs.md` sec 2; flagged independently as a risk in `design_tech.md` sec 3.5.)*

**For future PvP**, randomness resolves **server-side from one shared seed** (auditable, un-manipulable, mirrored across both boards) -- the same contract drops into the netcode build. *(Source: `research_td.md` sec 3 + `design_economy.md` sec 4.3.)*

### 2.4 Camera + transition (presentation only, engine stays authoritative)

*(Source: `design_multimap.md` sec 2 + `design_tech.md` sec 2-4.)*

The renderer has **one transform seam** -- every draw routes through `toX/toY`, and screen-shake already wraps the whole frame in a `ctx.translate`. We insert a `camera{offX,offY,zoom}` object there, defaulting to identity (zero visual regression). **v1 = "slide-pan":** on section advance, pan the camera one board-height while crossfading backdrop + tower skins + BGM (two-deck crossfader), reusing the existing `phaseAlert` banner as the "ENTERING <DISTRICT>" card. The carry-over snap is hidden at the pan mid-point (juice masks the swap). **v2 = "true tall-world"** (continuous scroll up an 18x120 stacked world) is an upgrade path, **explicitly do NOT block v1 on it.** The camera is auto-follow / semi-locked (never player-driven mid-skirmish) so one thumb stays free for deploys, and queued deploys fire on the new section the instant the pan completes (input buffering). *(Camera feel from `research_mlbb.md` sec 5; juice/latency-masking from `research_mlbb.md` sec 6.)*

**Top risk = mobile canvas perf** *(Source: `design_tech.md` sec 3)*: immediate-mode 2D with liberal `shadowBlur`, per-unit gradients, particle cap 240; multi-map + chaos = more entities + more FX at 4x speed. **Mitigation the camera itself unlocks:** offscreen culling (nothing is culled today because everything is on-screen -- a free win), a cached static-background canvas, throttled `shadowBlur`, tightened particle cap. Gate every section step behind a real-phone FPS check.

---

## 3. THE ECONOMY / PvP / NFT / METAVERSE PLAN

*(Source: `design_economy.md` in full, grounded against `MASTER_BUILD_PLAN.md` legal + chain locks.)*

### 3.1 The flywheel
**The campaign manufactures demand; card levels are the sink; the store is the supply; ranked is the retention spine; NFT + $BCARDD are the ownership/flex roof.** The named Mini-Boss Gate (Axis B) is a **soft power-wall tuned ~15-20% above the strongest free-earnable deck** at that NOS band -- never a paywall (every card is earnable), but the exact moment a few upgrades or the $2.99 Starter turns a 3-day grind into a same-session clear. **Jagged (chapter-2 boss) is deliberately the first hard wall**, placed where D3-D7 retention is decided.

### 3.2 Progression sink
- **Card levels 1-10**, linear `1 + 0.10*(L-1)` (HP+DMG only) so a maxed Common never outclasses a base Mythic -- the **no-P2W floor**.
- **CREW LEVEL** -- the collection-wide meta-level: *every* upgrade adds +1 to a global bar with milestone rewards every 10 (then 5). No dead-end upgrades; whales who maxed their main deck still progress. *(Steal from `research_clash.md` 1D/#4.)* Gates ranked unlock + map perks.
- **Mastery tasks** turn "try this card" into a paid quest -- keeps the 48-card long tail relevant.

### 3.2a CARD UPGRADE + ACQUISITION (operator-locked 2026-06-07 -- QUEUED for Track 2, do NOT block Track 1)
Refines 3.2 with the operator's exact model (Clash-Royale-style copies-to-upgrade):
- **Max level = 10 for BOTH cards AND towers. Everything starts at level 1.** Leveling raises HP + stats per
  the no-P2W curve `1 + 0.10*(L-1)` (a maxed Common still never beats a base Mythic).
- **Copies-to-level:** each level-up requires **a set number of duplicate copies of that card** (escalating
  per level, e.g. L1->2 cheap, ramping toward L10) **+ coins**. Standard collection-battler upgrade sink.
- **Card acquisition loop:** earn cards by (a) **winning / unlocking games** -> rewards **coins + free
  chests** (chests grant a batch of cards on a timer/unlock), AND (b) **buying cards in the shop**
  (deterministic Card Shop, sec 3.3 -- spend Scrap Tokens for the exact card). Both feed the copies needed
  to level up.
- **Towers level 1-10 too** (the 3 garrison/king towers), same copies-or-currency sink, scaling tower HP/dmg.
- **Every card needs a DESCRIPTION** (what it does -- its archetype, targeting ground/air, splash, special)
  -- including the 5 NEW spell cards (Boneshatter Freeze / Tar Pour / Snare Trap / Jolt / Strike: effect +
  radius + duration + energy + cooldown). Surface the description on the card-info/long-press popover + the
  shop + the NFT metadata. (A pass to author all 48 card + 5 spell descriptions is part of this task.)
- **Build placement:** this is **Track 2 M1 (accounts + card/tower levels + copies sink) + M2 (shop +
  acquisition) + a content pass for descriptions.** It rides ON TOP of the Track-1 game; do not block the
  Track-1 convoy/chaos build on it.

### 3.3 Store (legible roles, transparency out-retains dark patterns)
Nested reward loops at 4 timescales (per-match / arena-first-clear / **Mini-Boss Gate** / daily-season). The Gate grants a guaranteed chest + faction Scrap Tokens + a guaranteed card + **1 FREE DRAW TICKET** -- the conversion seed that hands a flush, powerful-feeling player to the store. **Two store lanes, never blended:**
- **Deterministic Card Shop (ships first, safest):** spend matching-rarity Scrap Tokens to buy the **exact** card -- no RNG. This is the clean-launch option.
- **Chop-Shop Escalating Draw (gated):** COD-model -- sell the draw, **prize is in-game play-card ONLY** (never an NFT, never cashable), disclosed odds, soft+hard pity (Mythic guaranteed by pull 40 ~= $260 ceiling), geofence WA/MN/HI. **Do NOT ship until PACK_RIP A/B/C is signed + Legal Gate 3 clears.**

### 3.4 Pass (the recurring-revenue backbone)
Ship **both** *(Source: `design_economy.md` sec 6)*: **Master Pass $14.99/mo** (arcade-wide: 2x earn, seasonal card track, +1 chest slot, +1 weekly draw ticket, $BCARDD airdrop *drip as access perk*) + **Crew Pass $4.99/season** (AK-only). Plus loyalty streaks, a **$1.99/7-day Joyride micro-pass**, and crown-skip/catch-up forgiveness. Each season spotlights one of the 4 factions -> a **built-in 4-season rotation calendar** (this is where Clash 5.7x'd revenue). Keep a deep top-end chase so the pass doesn't cannibalize draw spend.

### 3.5 Ranked PvP (retention spine, heaviest build, LAST)
Two ladders: **Ranked Standard** (all cards normalized to a fixed tournament level -> wallet buys **zero** win-rate; the competitive-integrity + legal-clean flagship) and **Open Ladder** (real levels count -> the progression dopamine). NOS-banded matchmaking, a **Reward Road** so climbing always pays even on a losing session, gated true-ranked (unlock after the chapter-2 boss). **Mirrored server-seeded RNG** is the fairness + anti-cheat spine: the server owns the result + the trophy/prize delta; the client never POSTs "I won." Ranked-season prizes are **skill-gated $BCARDD / skill-prize NFTs -- never time-gated, never chance** (the legal triple-clean: not gambling, not Howey, not money transmission).

### 3.6 Second genre off one asset library
**Garage Brawl** -- a Merge Tactics-style auto-merge mode reusing the same 48 cards (2x 1-star -> 2-star, merge refunds energy). **Cosmetics + pass ONLY, never power** (selling power in an auto-battler = community revolt). Doubles content value at a fraction of cost. *(Source: `research_clash.md` Part 2 / #9.)*

### 3.7 NFT + $BCARDD (ownership/flex, never power, never the random prize)
**Two-layer money, do not collapse:** $BCARDD = on-chain settlement layer (Phantom wallet); Fuel/Gears/Gems/NOS/Scrap = off-chain table credits. On-ramp always on ($BCARDD -> Gems, parallel to Stripe); **off-ramp = Legal Gate 1, default OFF.** A play-card and its NFT twin are **base-stat-identical** -- the NFT adds tradeability, Genesis scarcity, OG holo frame + aura + badge + boss-arena skin. **The load-bearing rule: a paid random draw NEVER outputs an NFT** (that edges into blockchain-gacha gambling); NFTs are deterministic-only (mint/buy on Tensor/Magic Eden in $BCARDD, or skill-prize). Marketplace fee = 2.5% burn + 2.5% treasury; nothing ever mints new $BCARDD (anti-Axie-spiral). *(Chain/legal locks per `MASTER_BUILD_PLAN.md` Decisions A + legal Option A.)*

### 3.8 Metaverse roof (option layer, last, never a dependency)
The 4 districts become the first 3D walkable zones; mini-bosses become world bosses; same wallet/NFT identity. If it never ships, coin + game + NFT + arcade is already a complete closed loop.

### 3.9 The legal wall (two lanes that never touch)
**Lane A (loot box/gacha):** sell the draw, prize = in-game value only (COD/PUBG, never sued). **Lane B (sweepstakes):** free entry, cash prize -- this is **B-CARDD BET blackjack, a SEPARATE product on a separate lane.** The one rule we never break: **never sell a paid draw whose prize is cashable for real money.** Disclaimer on every surface; AI never touches keys.

---

## 4. COMPETITIVE POSITIONING

### vs Clash Royale
We keep what makes it elegant -- the slow capped shared-clock elixir tug-of-war, dual-lane towers, the 8-card deck, the battle-pass spine, Crew Level. **Then we add the three things Supercell structurally cannot/will not:**
1. **The match goes somewhere.** CR is one static arena for 8 years; AK is a 4-district convoy with a camera that travels and a difficulty/affix staircase. *(`design_multimap.md`.)*
2. **The alley turns on you.** CR has only double-elixir + overtime; AK has a full Storm Clock of 9 telegraphed, fair, symmetric map events. *(`design_buffs.md`.)*
3. **You own your cards.** Supercell will never tokenize; AK cards are Solana NFTs and the chips are $BCARDD -- ownership + flex + a real marketplace, with a hard no-P2W wall so it never becomes pay-to-win.
**Tagline:** *"Clash Royale that goes somewhere -- and you own your deck."*

### vs Mobile Legends
ML's drama lives in rotation, objectives, and the 3-act teamfight arc -- but it costs 5-man coordination and 15-minute matches. AK **delivers the same map-movement and objective drama in a 4-minute, one-thumb, solo, auto-resolve-friendly package.** The convoy *is* the rotation; the District Gate *is* the objective gravity-well; the pace ramp *is* the 3-act escalation -- with none of the coordination tax. *(`research_mlbb.md` -> `design_multimap.md`.)*
**Tagline:** *"MOBA map-drama, in a 4-minute match you can play with one thumb."*

### The moat
Two genres off one 48-card library (battler + Garage Brawl), a cyberpunk-dog IP that's already ownable on-chain, and a coin/blackjack/arcade ecosystem none of the incumbents can bolt on. **Revenue frame:** Clash did $452M in 2025; capturing **0.1% of that lane (~$450k/yr)** is a realistic 12-24mo life-changing indie outcome IF retention holds. *(`design_economy.md` sec 9.)*

---

## 5. PHASED BUILD ROADMAP

**Sequencing law (resolves the `design_tech.md` vs `design_multimap.md` order conflict):** `design_tech.md` proved the **chaos layer delivers most of the "feel" with none of the geometry refactor, at the lowest risk** -- so we ship chaos FIRST on the existing single board, THEN the camera/sections. `design_multimap.md`'s camera-led ordering is overridden in favor of the risk-first tech sequence. Every step is static JS (no npm/bundler -- phone-proot SIGSEGVs), tested via `python3 -m http.server`, deployed via the wrangler-free `cf_pages_direct_upload.py` (verify the LIVE edge, never the tool exit code).

### TRACK 1 -- THE GAME (ships on alley-kingz.pages.dev, static JS, NOW)

**Phase G1 -- Storm Clock chaos layer (ships first, highest feel-per-effort, zero geometry).** *(tech steps 0-2 + buffs B1-B4 + O1.)*
- G1.0: generalize `matchTier` into a data-driven event scheduler firing ONE global buff on the existing board (banner + sim-speed rail reuse). Verify it fires, shows, expires.
- G1.1: add `game.eventMods` + edit the 3 combat getters to multiply through it; wire the 4 field buffs (Zoomies/Overclock/Smog/Glass Bones) + caps.
- G1.2: chaos HUD chip + telegraph banner + the studyable **Storm Codex** screen.
- G1.3: `applyMapDamage()` neutral hazard helper (12-line `castSpell` mirror); wire Junkyard Lightning (operator's example) + Flood Surge + Drone Sweep + Scrap Rain.
- G1.4: Golden Hour objective zone (the comeback/$BCARDD-flavored flashpoint).
- **Ship checkpoint:** the single arena now has the full "alley turns on you" loop, fair + telegraphed, on alley-kingz.pages.dev. This alone is a visible leap over the current build.

**Phase G2 -- Camera as identity + perf pass (regression-gated).** *(tech steps 3-4.)*
- G2.0: insert `camera{offX,offY,zoom}` at the `toX/toY` seam, default identity; rebase `canvasToArena()` so deploys still land correctly. Verify pixel-identical play (no behavior change).
- G2.1: now that a camera exists, add offscreen culling + cached background canvas + shadowBlur throttle + particle-cap tighten. Verify real-phone FPS holds BEFORE adding sections.

**Phase G3 -- The 4-section convoy.** *(tech steps 5-6 + multimap secs 1-4.)*
- G3.0: `SECTIONS[]` table + per-section state swap (preload all 4 bg/skins/music; `game.section`, `game.gatesCleared`).
- G3.1: slide-pan transition (crossfade bg/skins + two-deck BGM crossfader, reuse `phaseAlert` as the district banner).
- G3.2: bind section advance to `max(timeTier, gatesCleared)`; drive `gameSpeed = TIER_SPEED[section]`; wire the carry-over rules (units/towers/energy/crowns carry, enemy resets).
- G3.3: per-district affixes wired as section-entry Storm Clock events (Zoomies/Overclock/Storm Surge); Scrap Rain as the CHAOS-tier finale event.

**Phase G4 -- District Gates + scoring.** *(multimap secs 5-7.)*
- G4.0: promote each section's enemy king to a District Gate mini-boss (faction-flavored mechanic reusing existing shield/zap/disable_tower paths) + Gate health-bar/label.
- G4.1: mini-map road-strip HUD (A-B-C-D nodes, convoy icon, star/half-star per gate).
- G4.2: cumulative-crown scoring + Gate Reward (heal/repair/+energy/+crown) + Pursuer spawn on miss + CLEAN SWEEP early win.
- **Ship checkpoint:** the full convoy-run battler is live on alley-kingz.pages.dev.

**Phase G5 (LATER, do not block) -- v2 true tall-world continuous scroll** -- only if the continuous pan proves worth the engine rewrite. *(multimap sec 2.3.)*

### TRACK 2 -- THE META / ECONOMY (Supabase + Stripe + Solana; per MASTER_BUILD_PLAN, after the game proves fun)

- **M1 -- Accounts + progression:** `player_accounts`, card levels 1-10, Crew Level meta-bar, mastery tasks. (Supabase reuse.)
- **M2 -- Store v1 (clean-launch):** Gems choke-point + Stripe SKUs, free daily/ad crate, **deterministic Card Shop ONLY** (defer paid random draws), Starter $2.99 + Revival $1.99.
- **M3 -- Passes:** Master $14.99/mo + Crew $4.99/season + Joyride micro-pass + loyalty/catch-up. (Blocks on operator decision 2.)
- **M4 -- NOS ladder + 4-chapter campaign + named Mini-Boss Gates** (Stonejaw/Jagged/Rosco/Crown Foxhound -> $BCARDD Crownbreaker). Reward road + checkpoint chests.
- **M5 -- Garage Brawl auto-merge mode** (cosmetics-only) -- second genre off the same library.
- **M6 -- Solana NFT cards + $BCARDD on-ramp** (Metaplex Core, off-ramp Gate-1 OFF) -- per MASTER_BUILD_PLAN Phase 3.
- **M7 -- Ranked PvP** (Standard normalized + Open ladder, server-authoritative, mirrored seeds) -- the heaviest build, LAST.
- **M8 -- Paid random draws** -- ONLY after PACK_RIP signed + Legal Gate 3 (geofence + odds).
- **M9 -- Metaverse roof** -- option layer, last, never a dependency.

---

## 6. OPEN DECISIONS FOR THE OPERATOR

**The immediate game build (Track 1, Phases G1-G4) has NO blocking decision** -- every gameplay choice has a recommended default below, so the chaos layer can start shipping today. The blocking decisions are all on the meta/economy side.

**Top 3 (blocking, in priority order):**
1. **Monetization + legal posture.** Confirm **Option A** (pure utility/cosmetic, off-ramp OFF, $BCARDD-only marketplace, skill-gated prizes) and launch with the **deterministic Card Shop ONLY**; defer paid random draws until **PACK_RIP A/B/C is signed + Legal Gate 3** clears, and assign a legal contact now. *(Recommend: confirm A.)*
2. **Pass model lock.** Approve **Master Pass $14.99/mo (arcade-wide) + Crew Pass $4.99/season (AK-only)** -- blocks all pass SKUs/art and is the recurring-revenue backbone. *(Recommend: both.)*
3. **Campaign spine lock.** Ratify the **two-tier boss reconciliation** (within-match District Gates vs meta named Mini-Boss Gates) and lock the meta roster **Stonejaw -> Jagged -> Rosco -> Crown Foxhound -> $BCARDD "Crownbreaker."** *(Recommend: ratify + lock.)*

**Lower-stakes gameplay dials (defaults proposed -- change only if you disagree):**
- Pan direction: **up** (drive north up the road). | Carry-over heal on clean Gate clear: **25% units / 15% towers.** | Early-advance on Gate clear: **ship it** (tempo reward). | v1 slide-pan now, **v2 tall-world deferred.** | Affix set: **ship the 4 fixed district affixes + Scrap Rain finale**, expand the Storm Clock catalog later. | Hazard targeting: **Hunter mode** (densest-cluster) for single-player now, **Grid mode** (seeded cells) for ranked. | Ranked Standard normalized level: **L9.**

**Already locked upstream (no action -- per `MASTER_BUILD_PLAN.md`):** Solana-native NFTs, 48-card roster, coin-first sequencing, web-first arcade, two-layer money.

---

## 7. RESEARCH -> SECTION PROVENANCE (auditable)

| Section of this doc | Fed primarily by |
|---|---|
| 0. Vision / genre fusion | all 3 research docs + both design forks |
| 1. Reuse insight | `design_tech.md` + `design_multimap.md` sec 0 |
| 2.1 Two-axis reconciliation | `design_multimap.md` (Axis A) + `design_economy.md` (Axis B) -- conflict resolved here |
| 2.2 Convoy run | `design_multimap.md` + `research_mlbb.md` + `research_td.md` |
| 2.3 Storm Clock | `design_buffs.md` (superset) absorbing `design_multimap.md` affixes (subset) -- conflict resolved here |
| 2.4 Camera + perf | `design_multimap.md` + `design_tech.md` |
| 3. Economy/PvP/NFT/metaverse | `design_economy.md` + `MASTER_BUILD_PLAN.md` |
| 4. Positioning | `research_clash.md` + `research_mlbb.md` |
| 5. Roadmap order | `design_tech.md` risk-ordering overriding `design_multimap.md` -- conflict resolved here |
| 6. Operator decisions | `design_economy.md` sec 9 + `design_multimap.md` sec 9 |

**Three cross-agent conflicts resolved in this doc:** (1) "4 maps = 4 factions" scale collision -> two-axis / two-tier-boss model (sec 2.1); (2) per-district affixes vs Storm Clock -> Storm Clock is the engine, affixes are its section-entry entries (sec 2.3); (3) chaos-first vs camera-first build order -> chaos-first per the tech risk audit (sec 5).

---
*Synthesized 2026-06-07. This is the decision-resolved gameplay + economy spine for Pillar 2. The 7 source docs remain the deep reference. Next: operator clears the 3 top decisions (sec 6); the Hive ships Track-1 Phase G1 (Storm Clock chaos layer) to alley-kingz.pages.dev immediately -- no operator gate required.*
