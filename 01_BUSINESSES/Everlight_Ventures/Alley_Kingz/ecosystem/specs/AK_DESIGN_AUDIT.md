# ALLEY KINGZ -- DESIGN-ADHERENCE AUDIT
**Every `AK_*.md` design doc cross-checked against the LIVE build.**
Date: 2026-06-20 | Auditor: Hive (Lucrex) | Scope: `ecosystem/AK_*.md` + `specs/*.md` vs `game/*` + `game/systems/*.js` + `supabase/functions/*`
Grounds (read end-to-end): the 21 `AK_*.md` docs, `specs/MODULE_CONTRACT.md`, `specs/WAVE_INTEGRATION.md`, `game/index.html`, `game/engine.js`, `game/economy.js`, `game/game.html`, `game/canon.js`, the 8 `game/systems/*.js`, `data/cards.json` (106), `data/decks.json`, `game/handlers_data.js`, `AGENT_MAILBOX.md`, `ALLEY_KINGZ_TODO.md`.

> ONE-LINE VERDICT: The `AK_SYSTEMS` 8-wave plug-in layer (2026-06-20) is **built, committed, parse-clean, and bootstrapped into the host** with strong theme + crypto discipline. The biggest issues are NOT in the code -- they are **doc-vs-doc contradictions** (deck size, the lore-faction layer, two competing raid architectures) and an **unverified live deploy** of the 8 waves. The grand `AK_2D_3D_CONCEPT.md` extraction-shooter vision is almost entirely **designed-not-built**, and the build took a different (and arguably better-scoped) path than that doc's sprint plan.

---

## 0. STATUS LEGEND
`LIVE` = shipped + reachable on alleykingz.online · `BUILT` = code committed + parse-clean, deploy/browser-verify pending · `WIRED` = host seams landed · `DSGN` = designed in a doc, no code · `STUB` = building exists with `url:'soon'`, nothing behind it · `GAP` = designed but absent · `SERVER-PENDING` = client done, edge fn not deployed.

---

## (a) PER-SYSTEM TABLE -- DESIGNED vs BUILT vs LIVE vs GAPS

| System | Design doc(s) | DESIGNED | BUILT (code) | LIVE | GAP / note |
|---|---|---|---|---|---|
| **Walkable 9-zone hub** | AK_LIVING_WORLD, AK_V2_BUILD_SPEC, AK_GAME_VISION | 3x3 district grid, edge-transitions, locked silhouettes, radar | `index.html` ZONES (9 zones, 2 locked: THE_OVERLOOK/POLICE CHECKPOINT, THE_UNDERCITY/COLLAPSED BRIDGE) | **LIVE** | Matches design. The city-is-the-menu doctrine is honored. |
| **Battler (tower)** | AK_SYSTEMS_DESIGN, AK_MASTER_GAME_DESIGN_SYNTHESIS | CR elixir/energy + 4-card cycle + 21 named combos + L10 cap | `engine.js` (ENERGY_MAX=10, `dealHand=deck.slice(0,4)`, computeNamedSynergy) | **LIVE** | Verified constants match the doc. Do-not-fork rule respected. |
| **AK_SYSTEMS bootstrap** | MODULE_CONTRACT S6, WAVE_INTEGRATION A-D | registry + `AK_CTX` + 6 host seams | `_registry.js` + index.html (canon.js, 8 script loads, AK_CTX@:400, seams @:212/:281/:321/:446-452), economy.js 10-field block @:91-101, engine.js mode seam @:1397/:1445/:2662, game.html @:2106/:5048/:5287 | **WIRED** (committed) | **Deploy + browser-verify NOT confirmed** (see Fix #1). WAVE_INTEGRATION still says "READY TO LAND" though it has landed -- stale status. |
| **production** (5 producers) | AK_RAID_DEFENSE S3, AK_CONTENT_BACKLOG, MODULE_CONTRACT 3.1 | offline-accrual GEM/MINT/FORGE/LAB/GEN, collect+upgrade, "ready" pip | `systems/production.js` | **BUILT** | No server (deterministic client accrual -- by design). Resource mapping diverges from the contract EXAMPLE (see (b) Div-1) -- compliant. The 5 buildings are `url:'soon'` stubs in the hub until the wave deploys. |
| **missions** (Hit List + deliveries) | AK_CONTENT_BACKLOG D, MODULE_CONTRACT 3.2 | keeper deliveries, claim, goal-gradient | `systems/missions.js` (keeper "Marrow the Fixer") reuses `ak-quests` (LIVE) | **BUILT** | Degrades to `shop#hit2` if hub lacks `ak_account.js`+`quests.js`+`social.js` (current hub does not load them) -- see Fix #5. |
| **encounters** (wild dogs) | AK_SYSTEMS_DESIGN S4, AK_GAME_VISION, MODULE_CONTRACT 3.3 | symbol-encounters, detect/vision/strike + `chaseLeashR`, capture below HP threshold | `systems/encounters.js` (roamers, `chaseLeashR` present, MAX_TOTAL=14, "!"/"?" alerts) | **BUILT** | The doc's flagged anti-grief `chaseLeashR` IS implemented (good). Capture copies marked `// TODO-SERVER` non-tradeable. No server v1 (by design). |
| **raid / night-defense** | AK_RAID_DEFENSE (6 subsystems), AK_AI_BOTS_PLAN, MODULE_CONTRACT 3.4 | async bot-base raids, surgical building damage, 5 shield tiers, crew reinforce, revenge, night PvE | `systems/raid.js` (local snapshot-as-bot fallback, gold shields settle client-side, gem shields route to server, night TD overlay) | **BUILT, SERVER-PENDING** | `ak-raid` edge fn **NOT deployed** (spec-only). v1 has NO surgical per-building raid (`AK_MODES.raid` absent -> plain board match, QA-5). Diverges from AK_SYSTEMS_DESIGN's "build on RaidController" -- see (b) Div-2 + (d) Contradiction-3. |
| **seasons** (chapters/Marks) | AK_CONTENT_BACKLOG A/B, MODULE_CONTRACT 3.5 | 6 chapters, Marks (cosmetic, resets), seasonal track + leaderboard | `systems/seasons.js` (all 6 chapters: Junkyard Dynasty/Neon Howl/Dog Days/Blood Moon/Frostbite/Golden Leash; keeper "Goldie") reuses `ak-pass`+`ak-crew` (LIVE) | **BUILT** | Chapters + Mythic figures match canon exactly. Perf watch on `onDrawWorld` (Fix #7). |
| **trading** (barter post) | AK_CONTENT_BACKLOG C, MODULE_CONTRACT 3.6 | server-escrow card/cosmetic/soft barter, dupe-proof, no token | `systems/trading.js` (keeper "Switch the Broker", refund-on-fail offline) | **BUILT, SERVER-PENDING** | `ak-trading` edge fn **NOT deployed** (spec embedded in trading.js :649-713). Name mismatch `ak-trade` vs `ak-trading` (Fix #3). |
| **arcade** (mini-games) | AK_CONTENT_BACKLOG P3, MODULE_CONTRACT 3.7 | dog-themed mini-games, capped soft payouts | `systems/arcade.js` (keeper "Joystick Jonah", Bone Dig/Alley Dash/Whack-a-Stray, 500g/20b daily cap) | **BUILT** | Catalog is a subset of the AK_CONTENT_BACKLOG list (7 arcade + 7 micro) -- the rest are DSGN. |
| **modes** (alt win-conditions) | AK_GAME_VISION (multi-mode), MODULE_CONTRACT 3.8 | survival/gulag/MOBA/encounter as win-condition overlays on engine | `systems/modes.js` -> `AK_MODES` keys: `survival, encounter, openWorldMoba, openGulag, routeEncounter` (keeper "THE STREET") | **BUILT** | Engine seam (C1-C4) landed. Street War MOBA + Gulag shooter exist here as Canvas2D **overlays** (NOT engine forks) -- partially realizes two "DSGN-only" modes. |
| **Economy (soft 5-currency)** | AK_SYSTEMS_DESIGN S5 | Gold/Copies/Scrap/Keys/Bones; defer NOS+ALK; gems=time+cosmetic | `economy.js` AK_ECON + `bones:0` field landed | **LIVE** | Matches. `wood/stone/metal` material economy (AK_2D_3D, AK_GAME_VISION fortress) is **GAP** -- not in economy.js. |
| **Social (crews/chat/2v2)** | SOCIAL_LAYER_ARCHITECTURE, AK_GAME_VISION | crews, world/crew chat, donations, ghost-2v2 | `social.js` + `ak-crew`/`ak-chat` (LIVE) | **LIVE** | "crew" used throughout. The hub building label is "CLAN YARD" (id `CLAN`) -- the one theme wart (see (c) Theme-1). |
| **Handlers (6 commanders)** | HANDLER_CLASSES_*, project memory | Mender/Tracker/Shadow/Rigger/Bruiser/Dealer + Bones trees | `handlers_data.js` (all 6 present, schema `{id,name,bones,...}`) | **LIVE** | Matches roster exactly. Portraits still glyph-fallback (Seedance-blocked). |
| **Shop / Pass / Drip / Codex / Cosmetics** | AK_SHOP_INTEGRATION, FORTNITE_ELEMENTS, drip.js/pass.js/quests.js | gem packs, Alley Pass 30-tier, Drip cosmetics, Codex | `shop/`, `pass.js`, `drip.js`, `codex.js`, `ak-pass`/`ak-cosmetics` (LIVE) | **LIVE** | Stripe live (per memory). |
| **ALLEY_KINGZ_CORE spine** | AK_SYSTEMS_DESIGN (critical correction), TODO Wave-0 | EventBus/DataValidator/ConfigLoader/SaveLoad/AntiCheat/RaidController/BuildingBase | built, 38/38 tests pass (TODO) | **BUILT, NOT WIRED** | grep of `game/` for EventBus = 0 hits (confirmed by AK_SYSTEMS_DESIGN). Competes with AK_SYSTEMS -- see (d) Contradiction-3. |
| **3-mode reality (World Map / Hub Walk / Extraction)** | AK_2D_3D_CONCEPT (entire doc) | macro world map + hub walk + DMZ-style extraction w/ backpack/death/retrieval | -- | **DSGN ONLY** | Backpack tiers, secure slots, "YOU GOT JACKED" death, Doc Wattson infirmary, dynamic obstacle/tree growth, tool crafting, builder queue, crew-shared hub instances, betrayal log = **all unbuilt.** The 5-sprint plan in AK_2D_3D S10 was NOT the path taken. See (b) Div-4. |
| **Breeding (The Kennel)** | AK_SYSTEMS_DESIGN S3, AK_GAME_VISION | fixed-roster, stats-decoupled, Mythics never breed, Bones sink | -- | **DSGN ONLY** | No Kennel breeding screen / roll fn / incubation FSM. (THE KENNEL building currently = handlers shop.) |
| **Fortress + night-defense + wood/stone** | AK_GAME_VISION, AK_2D_3D S5, AK_RAID_DEFENSE | gather wood/stone -> walls/barricades, night zombie-stray waves, infirmary | partial: `raid.js` night TD overlay | **DSGN / partial** | Materials economy absent from economy.js; walls/barricades + infirmary unbuilt. |
| **Bot living-world (LLM flavor)** | AK_AI_BOTS_PLAN | `ak_flavor_pool` + nightly batch + snapshot-as-bot | partial: `raid.js` local snapshot-as-bot | **DSGN / partial** | `ak-flavor` edge fn + `ak_flavor_pool`/`ak_bot_bases` tables not built. |
| **Lore-faction layer (Crowned/Rusted/Hologhosts/Unbound)** | AK_SYSTEMS_DESIGN (locked decision 2), AK_2D_3D, AK_WORLD_BIBLE | every card carries combat-faction (class) AND lore-faction (tribe) | -- | **GAP** | `cards.json` `tribe`/lore-faction = **null on all 106 cards**. Only combat-faction (class) is populated. See (d) Contradiction-2. |

---

## (b) BUILD-vs-DOC DIVERGENCES (and whether each is fine or a fix)

**Div-1 -- production resource mapping (FINE).** MODULE_CONTRACT 3.1 EXAMPLE maps GEM->gold, LAB->sp. `production.js` maps GEM->Rare scrap, MINT->gold, FORGE->key-fragments, LAB->Epic scrap, GEN->keys+rate-boost. Every output is soft-currency, gem-free, token-free -> all HARD RULES hold; the contract calls 3.1 an *example*. Keeper names match `KEEPERS` (Prospector Pip / Banker Bones / Sparks / Doc Wattson / Volt). **Accept; just don't expect the example mapping.** (Matches WAVE_INTEGRATION QA-8.)

**Div-2 -- raid built as a self-contained module, NOT on `RaidController` (NEEDS A DOC DECISION).** AK_SYSTEMS_DESIGN S6 says build the raid loop on the ALLEY_KINGZ_CORE `RaidController/DamageCalculator/ShieldSystem` kernels. `raid.js` instead implements raids client-side (local mulberry32 bot bases + `ak-raid` edge fn), never importing those kernels. This is *consistent with MODULE_CONTRACT* (which never references ALLEY_KINGZ_CORE) but *contradicts AK_SYSTEMS_DESIGN*. Not a code bug -- a **governance gap**: two design docs prescribe two raid stacks. Pick one (recommend: AK_SYSTEMS/raid.js is the realized path; demote ALLEY_KINGZ_CORE RaidController to reference). See (d) Contradiction-3 + Fix #2.

**Div-3 -- `mode:'raid'` has no win-condition (ACCEPTABLE MVP GAP).** `raid.js` calls `battle.launch({mode:'raid'})` but `AK_MODES.raid` does not exist -> engine runs a plain non-convoy single-board match labeled RAID (ends via the C4 crown/tiebreak path). Playable + byte-safe, but it is NOT the "defender's base layout = battlefield" surgical raid the operator described in AK_GAME_VISION / AK_RAID_DEFENSE. Flag so no one expects base-raid mechanics in v1. (Matches WAVE_INTEGRATION QA-5.)

**Div-4 -- the build did NOT follow AK_2D_3D_CONCEPT's sprint plan (FINE, but the doc should say so).** AK_2D_3D S10 lays out a 5-sprint extraction-shooter build (Zoom -> Backpack -> Danger -> Social -> Polish). The realized build is the AK_SYSTEMS 8-wave plug-in layer instead. The extraction/backpack/death loop is a far heavier, riskier lift; the 8-wave path is better-scoped for the 2.5D Canvas2D constraint. **No code fix** -- but AK_2D_3D_CONCEPT's `Status: READY FOR IMPLEMENTATION` is misleading; it is aspirational/V2+, not the current track. Re-label it (Fix #8).

**Div-5 -- hub `systems/*.js` script tags carry no `?v=` cache-bust (MINOR).** In `index.html` the 8 module loads are bare (`<script src="systems/production.js">`), while `game.html` stamps `?v=1781486888`. If `ship.sh`'s stamping only rewrites certain patterns, the hub modules could serve stale from the CDN edge after an update. Verify `ship.sh` stamps the hub `systems/` tags, or add `?v=` (Fix #6).

**Div-6 -- WAVE_INTEGRATION + AK_2D_3D + MODULE_CONTRACT statuses are stale.** All three say "READY"/"READY FOR IMPLEMENTATION"; the bootstrap + 8 modules are actually committed in the host files (verified: index.html :74-83/:212/:400, economy.js :91-101, engine.js :1397, game.html :2106/:5287). Flip the status banners to "LANDED (committed) -- deploy-verify pending" (Fix #1/#8).

---

## (c) DOG-THEME / VIBE CONSISTENCY FINDINGS

Overall: **excellent.** All 8 modules carry the "gritty gold cyberpunk dog-gang, crew never clan, NeonReach" voice in headers + keeper copy. No fantasy drift (zero hits for rune/wizard/elf/knight/dragon-as-fantasy). Cards/factions/Mythics are referenced BY NAME from the real roster. Specific findings:

- **Theme-1 (real wart, in a FROZEN host file) -- "CLAN YARD".** `index.html:138` building label is `'CLAN YARD'` (id `CLAN`), and `seasons.js:421` player-facing copy says *"Start or join a crew in the **Clan Yard**"*. This violates the "crew never clan" hard law. The id `CLAN` can stay for compat, but the **display label + the seasons copy should read "CREW YARD"**. (WAVE_INTEGRATION QA-10 acknowledges it as "the sole 'Clan Yard' string... the literal index.html building label" -- but it has now leaked into module copy.) Files: `game/index.html:138`, `game/systems/seasons.js:421`. -> Fix #4.
- **Theme-2 (consistency WIN) -- Mythic-to-faction mapping is internally perfect.** `cards.json` SoT: `$BCARDD`->Boneguard Crew, `Jagged`->Zoomie Syndicate, `Rosco`->Leashbreak Tactix, `Crown Foxhound`->K9 Circuitry. `raid.js` faction pools and `seasons.js` chapter figures BOTH match this exactly. No drift.
- **Theme-3 (WIN) -- seasons honor NeonReach canon.** `seasons.js:84` "A Blood Moon over NeonReach -- Crown Foxhound's circuits run red." Chapters match AK_CONTENT_BACKLOG verbatim.
- **Theme-4 (minor) -- combat-faction naming: docs abbreviate, data expands.** Docs say "Boneguard/Zoomie/K9/Leashbreak"; `cards.json` class values are "Boneguard Crew / Zoomie Syndicate / Leashbreak Tactix / K9 Circuitry". Modules use the full data values (correct). Just align doc shorthand to the canonical full names to avoid future string mismatches.

---

## (d) DOC-vs-DOC CONTRADICTIONS + LOCKED RESOLUTION

**Contradiction-1 -- TOWER DECK SIZE: 8 vs 10 vs 11 (HEADLINE).**
- AK_SYSTEMS_DESIGN.md (locked decision 1) + AGENT_MAILBOX checkpoint: **"8-card tower deck (live, Clash-Royale-standard, NO rebalance)"**, with the "11" reassigned to a separate CITY WORKFORCE.
- AK_GAME_VISION.md + AK_2D_3D_CONCEPT.md: **"your TOWER deck is ALWAYS 11 cards"** / "Select deck (11 cards, always secure)".
- AK_MASTER_GAME_DESIGN_SYNTHESIS.md: cites CR's **"8-card deck, 4 in hand"**.
- **LIVE CODE (the tiebreaker):** `data/decks.json` = **11 cards** in every one of the 10 faction decks; `engine.js STARTER_DECK_NAMES` = **10**; `dealHand=deck.slice(0,4)` = 4-card cycling hand.
- **LOCKED RESOLUTION:** the live tower deck is **11 (decks.json) with a 10-card starter and a 4-card cycle** -- the "8-card live" claim in AK_SYSTEMS_DESIGN is **factually wrong** and must be corrected. Either (a) accept 11 as canonical and fix AK_SYSTEMS_DESIGN + AK_MASTER_GAME_DESIGN_SYNTHESIS, OR (b) if 8 is genuinely desired, that is a *rebalance* (decks.json + starter rewrite), not "no rebalance / live". Recommend **(a) canonical = 11**, since it is what ships and the operator's own AK_GAME_VISION says 11. -> Fix #2 (highest priority).

**Contradiction-2 -- the LORE-FACTION layer is locked in docs but absent in data.**
- AK_SYSTEMS_DESIGN (locked decision 2) + AK_2D_3D + AK_WORLD_BIBLE: every card carries BOTH combat-faction (class) AND lore-faction/tribe (Crowned/Rusted/Hologhosts/Unbound), which drives world/crew allegiance + territory color.
- LIVE: `cards.json` `tribe` = **null on all 106 cards**; only `class` (combat-faction) is populated. AK_2D_3D's World-Map territory colors (Crowned=gold etc.) therefore have no data to bind to.
- **LOCKED RESOLUTION:** the lore-faction is **DSGN, not built.** Either populate a `tribe`/`loreFaction` field on all 106 cards (a `data/_build_*.py` pass mapping the 4 combat factions -> 4 lore factions, or a richer mapping) BEFORE any world-map/territory feature relies on it, OR mark the lore-faction layer explicitly "DEFERRED -- not in card data" in AK_SYSTEMS_DESIGN so no module assumes it exists. -> Fix #9.

**Contradiction-3 -- TWO raid/economy architectures (ALLEY_KINGZ_CORE vs AK_SYSTEMS).**
- AK_SYSTEMS_DESIGN says build raids/base-defense on the ALLEY_KINGZ_CORE kernels (RaidController/DamageCalculator/ShieldSystem); TODO shows that Wave-0 spine "FINISHED, 38/38 tests."
- MODULE_CONTRACT + the realized `systems/raid.js` ignore ALLEY_KINGZ_CORE entirely and implement raid client-side + an `ak-raid` edge fn.
- **LOCKED RESOLUTION:** the **realized canonical path is AK_SYSTEMS** (it's wired into the live hub; ALLEY_KINGZ_CORE is built-but-NOT-wired, grep EventBus = 0). Demote ALLEY_KINGZ_CORE to a reference/optional-server-verifier; update AK_SYSTEMS_DESIGN S6 so it no longer prescribes RaidController as the build target. Otherwise the next builder wires a dead scaffold. -> Fix #2/Div-2.

**Contradiction-4 -- shield currency (already RESOLVED in docs, verify in code).** Old AK_RAID_DEFENSE / ShieldSystem priced shields in ALK (100/250/700). The 2026-06-19 crypto-gate deleted that: shields are soft/fiat only; gem tiers (Fortress Dome/Panic) are server-routed and skip timers only. `raid.js` reflects the fix (gold shields client-side, gem shields -> server, NO ALK). **Resolved + code-consistent.** Keep the deleted ALK tiers out of any future copy.

**Contradiction-5 -- "Doc Wattson" role conflict (MINOR).** AK_2D_3D casts Doc Wattson as the **Infirmary** keeper (death/heal/insurance). MODULE_CONTRACT 3.1 + `production.js` cast Doc Wattson as the **RESEARCH LAB (sp)** producer keeper. Same NPC, two buildings. Pick one home for Doc Wattson (recommend Infirmary per the richer AK_2D_3D characterization; give the Lab a different keeper) -> minor, Fix #10.

---

## (e) PRIORITIZED FIX-LIST

| # | Pri | Fix | File(s) | Effort |
|---|-----|-----|---------|--------|
| 1 | **P0** | **Deploy the 8-wave bootstrap from e5 + Playwright-verify each building** (production smoke test first), then flip the stale "READY TO LAND" banners to "LANDED + LIVE". Nothing in the mailbox confirms the waves are live on alleykingz.online. | e5 `~/ak_deploy`->`ship.sh`; then WAVE_INTEGRATION.md, MODULE_CONTRACT.md status lines | M |
| 2 | **P0** | **Resolve deck size to 11 (canonical) + fix the "8-card live" claim**; and **declare AK_SYSTEMS the canonical raid path** (demote ALLEY_KINGZ_CORE RaidController). Two doc edits that stop the next builder from coding to a wrong number / dead scaffold. | AK_SYSTEMS_DESIGN.md, AK_MASTER_GAME_DESIGN_SYNTHESIS.md | S |
| 3 | **P1** | **Reconcile `ak-trade` vs `ak-trading`** before the server lands -- pick one name for the fn dir AND `trading.js` `TRADE_FN` (:32). Recommend `ak-trading` (the module literal) to avoid editing a frozen wave file. | trading.js OR new edge-fn dir name; MODULE_CONTRACT 3.6 / WAVE_INTEGRATION E3 | S |
| 4 | **P1** | **"CLAN YARD" -> "CREW YARD"** display label + the seasons copy. Keep id `CLAN`. Honors the crew-never-clan hard law. | game/index.html:138, game/systems/seasons.js:421 | S |
| 5 | **P2** | For the LIVE in-place Hit List + claim, **load `ak_account.js`+`quests.js`+`social.js` in the hub** (missions currently degrades to `shop#hit2`). Optional -- degrade is graceful. | game/index.html | S |
| 6 | **P2** | **Verify `ship.sh` cache-busts the hub `systems/*.js` tags** (or add `?v=`); game.html stamps them, index.html does not. | ship.sh / game/index.html:75-83 | S |
| 7 | **P2** | **Perf-audit `seasons.onDrawWorld`** on a real phone: full-screen `soft-light` `fillRect` (alpha .55) + ~22 particles EVERY frame in EVERY zone, stacking under raid's night tint. Cache the wash or gate cadence if FPS dips. (Do NOT strip glows -- operator veto; pre-render instead.) | game/systems/seasons.js | M |
| 8 | **P2** | **Re-label AK_2D_3D_CONCEPT.md** from "READY FOR IMPLEMENTATION" to "V2+ ASPIRATIONAL -- not the current build track" (extraction/backpack/infirmary loop is DSGN-only; the 8-wave path was taken instead). | AK_2D_3D_CONCEPT.md | S |
| 9 | **P3** | **Decide the lore-faction layer**: either populate `tribe` on all 106 cards (a `data/_build_*.py` pass) or mark it DEFERRED so no module assumes it. Blocks any world-map/territory-color feature. | data/cards.json (+ build script), AK_SYSTEMS_DESIGN.md | M |
| 10 | **P3** | **Resolve Doc Wattson's home** (Infirmary vs Research Lab keeper) -- one NPC, two buildings across docs/code. | AK_2D_3D vs MODULE_CONTRACT/production.js | S |
| 11 | **P3** | **Append a dated AGENT_MAILBOX entry for the 2026-06-20 AK_SYSTEMS build** (continuity-rail law) -- the 8-wave layer, MODULE_CONTRACT, and WAVE_INTEGRATION are not yet logged in the mailbox (last entry = 2026-06-19). | AGENT_MAILBOX.md, ALLEY_KINGZ_TODO.md | S |

---

## CRYPTO / PARITY -- PASS (verified across all 8 waves)
No module grants `gems` (`ctx.currency.grant('gems')` is a host no-op @ index.html:433). No `$BCARDD`/`ALK` in any reward/trade/utility line: occurrences are (a) flavor strings, (b) `$BCARDD` as a Mythic SPRITE never fielded as loot (raid caps defender loot at Legendary; encounters/arcade exclude Mythics), (c) hard-block regex `/\$|bcardd|alk/i` in trading.js:160. Marks (seasons) are cosmetic-only and reset. Mythics are never tradeable (trading.js:45) and never breed/roam (by design). Gems skip TIMERS only. Supabase target is `mfghdobptredxxhbjwyz` (the live fns: ak-chat/ak-cosmetics/ak-crew/ak-pass/ak-quests). **All HARD RULES hold.**

---
*Audit method: 21 AK docs + 2 specs read in full; host integration markers grepped + line-confirmed; 8 modules `node --check` clean; cards.json/decks.json/handlers_data.js parsed; theme grep for off-canon terms. Live-deploy state could not be browser-verified from the phone (sandbox) -- that is Fix #1.*
