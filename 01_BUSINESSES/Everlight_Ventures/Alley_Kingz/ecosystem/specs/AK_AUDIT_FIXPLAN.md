# ALLEY KINGZ -- AUDIT FIX PLAN (consolidated, de-duplicated, prioritized)
**Source:** `specs/AK_DESIGN_AUDIT.md` section (e) fix-list + (b) divergences + (c) theme + (d) contradictions.
**Date:** 2026-06-20 | **Status:** `spec-only` (this doc prescribes the edits; nothing here is applied yet).
**Scope rule:** every entry below is CONCRETE + SAFE + theme/consistency-bound (a bug, a vibe-drift string, or a doc contradiction with a one-line resolution). Big new features are listed under section D -- DEFERRED-TO-ROADMAP, not as quick-fixes.
**HARD GUARD (verified against every edit below):** no edit touches gems/$BCARDD/ALK economics. All changes are copy/label/doc-status/string-name corrections. Crypto-gate (soft-currency + cosmetic only; gems skip timers only; Mythics never tradeable) is untouched. Theme law: crew never clan; NeonReach canon; 106 cards + 6 handlers by name.

---

## AUDIT SELF-CORRECTION (the audit's own number was wrong -- fix it before propagating)
The audit (Contradiction-1, line 76) says *"`engine.js STARTER_DECK_NAMES` = 10."* **It is 8, not 10.** Verified `game/engine.js:634-642`:
```
$BCARDD, Grit Bulldog, Pixel Greyhound, Strike, Chill Samoyed, Jolt, Rail Terrier, Laser Beagle  = 8 cards
```
So the real live picture is a **split, not a single number**:
- **Hardcoded fallback `STARTER_DECK_NAMES` = 8** (CR-standard starter; used only when `playerDeckNames` is empty).
- **The 10 selectable faction decks (`data/decks.json`) = 11 each** (CROWN MARCH / HYPER LOOP / ... / FOUR CROWNS).
- **Hand cycle = 4** (`engine.js:2424 dealHand = deck.slice(0,4)`), universal.
This refines Fix #2 below: the "8-card" claim is **half-true** (it matches the starter fallback, not the fielded faction decks). The canonical *fielded* tower deck is **11**. Whether to bump the 8-card starter up to 11 for internal consistency is a **rebalance -> section D**, not a quick-fix.

---

## A. P0 QUICK-FIXES -- the Lead applies these now (concrete edits, no deploy/ops dependency)

### P0-1 -- "CLAN YARD" building label -> "CREW YARD" (live hub) *(theme hard-law: crew never clan)*
**File:** `game/index.html:140`
```
OLD:  buildings:[B('CLAN','CLAN YARD','#9d8bff',560,560,170,104,'shop/shop.html#crew2','crews / chat'),
NEW:  buildings:[B('CLAN','CREW YARD','#9d8bff',560,560,170,104,'shop/shop.html#crew2','crews / chat'),
```
**Why:** the building id `CLAN` stays (deep-link/compat) but the *player-facing label* violates "crew never clan." Display only -- zero logic change.

### P0-2 -- seasons leaderboard copy "Clan Yard" -> "Crew Yard" *(theme hard-law)*
**File:** `game/systems/seasons.js:421`
```
OLD:  ...Start or join a crew in the Clan Yard -- your wins put your crew on the ' + ch.name + ' board.'
NEW:  ...Start or join a crew in the Crew Yard -- your wins put your crew on the ' + ch.name + ' board.'
```
**Why:** the wart leaked from the index.html label into live module copy. Same hard law. Pure string.

### P0-3 -- hub_proto "CLAN YARD" -> "CREW YARD" (keep proto in parity) *(theme hard-law)*
**File:** `game/hub_proto.html:140`
```
OLD:  buildings:[B('CLAN','CLAN YARD','#9d8bff',560,560,170,104,'shop/shop.html#crew2','crews / chat'),
NEW:  buildings:[B('CLAN','CREW YARD','#9d8bff',560,560,170,104,'shop/shop.html#crew2','crews / chat'),
```
**Why:** `hub_proto.html` is the prototype mirror of the live hub; leaving it on "CLAN YARD" reseeds the wart on the next copy-forward. Display only.

### P0-4 -- doc sweep "Clan Yard" -> "Crew Yard" (4 strings across 3 docs) *(theme hard-law)*
**Files / exact strings:**
- `AK_HUB_INTERACTION_ROAMING_COMBAT_SPEC.md:27` -- `...guarding the Clan Yard.` -> `...guarding the Crew Yard.`
- `AK_HUB_INTERACTION_ROAMING_COMBAT_SPEC.md:97` -- table cell `| **CLAN YARD** | Chief |` -> `| **CREW YARD** | Chief |`
- `AK_LIVING_WORLD.md:5` -- `Clan Yard->Crew` -> `Crew Yard->Crew`
- `AK_CONTENT_BACKLOG_AND_SEASONS.md:56` -- `CLAN YARD (crews/chat)` -> `CREW YARD (crews/chat)`
**Why:** these are the remaining "Clan Yard" sources of truth; if left, the next builder re-introduces the label from the docs. Doc copy only.

### P0-5 -- correct the "8-card tower deck (live, ... NO rebalance)" claim *(doc contradiction-1)*
**File:** `AK_SYSTEMS_DESIGN.md:46`
```
OLD:  (1) DECK SIZE = 8-card tower deck (live, Clash-Royale-standard, NO rebalance).
NEW:  (1) DECK SIZE = 11-card fielded tower deck is CANONICAL (all 10 faction decks in data/decks.json = 11). The hardcoded STARTER_DECK_NAMES fallback is 8 (CR-standard starter, used only when no deck is built); the hand cycle is 4 (engine.js dealHand=deck.slice(0,4)). The earlier "8-card live, NO rebalance" line was imprecise -- fielded decks already ship at 11. Reconciling the 8-starter up to 11 would be a REBALANCE (see AK_AUDIT_FIXPLAN section D), not a no-op.
```
**Why:** stops the next builder coding to a wrong number / assuming "8 = live." Doc only; no code/decks.json change here.

### P0-6 -- align AK_MASTER deck-size line to live reality *(doc contradiction-1)*
**File:** `AK_MASTER_GAME_DESIGN_SYNTHESIS.md:106`
```
OLD:  - 8-card deck, 4 in hand
NEW:  - Fielded faction decks = 11 cards, 4 in hand (CR fusion target was 8; the live decks.json ships 11). Starter fallback = 8.
```
**Why:** keeps the 14-game fusion doc from re-asserting "8" as the live number. The CR reference at lines 108/115 (cycle-tracking, anti-whale) stays valid regardless of size. Doc only.

### P0-7 -- reconcile `ak-trade` -> `ak-trading` (match the live module literal) *(audit Fix #3 / WAVE_INTEGRATION QA-2)*
**Files:** `specs/MODULE_CONTRACT.md` lines **303, 352, 587, 602** -- replace every `ak-trade` with `ak-trading` (and `migrations/<ts>_trade.sql` -> `migrations/<ts>_trading.sql` at :602). Sweep the stale mentions in `specs/WAVE_INTEGRATION.md:461` (`#ak-trade` -> `#ak-trading`) and `:498` (`ak-trade` -> `ak-trading`).
**Why:** `game/systems/trading.js:32` already hard-codes `TRADE_FN = "ak-trading"` and that wave file is frozen. Renaming the DOC (not the frozen module) is the safe direction; it makes the deployed edge-fn dir name unambiguous before the server lands. No code edit.

### P0-8 -- declare AK_SYSTEMS the canonical raid path; demote ALLEY_KINGZ_CORE RaidController *(doc contradiction-3 / Div-2)*
**File:** `AK_SYSTEMS_DESIGN.md` -- append a one-line correction to the S6 line (`:33`, the "GREENFIELD raid + base-defense ... RaidController/DamageCalculator/ShieldSystem" prescription):
```
ADD (after the S6 sentence): >> CORRECTION 2026-06-20: the REALIZED canonical raid path is AK_SYSTEMS/game/systems/raid.js (client snapshot bot-bases + ak-raid edge fn), which IS wired into the live hub. ALLEY_KINGZ_CORE (RaidController/DamageCalculator/ShieldSystem) is built-but-NOT-wired (grep game/ for EventBus = 0) and is now REFERENCE/optional-server-verifier ONLY -- do NOT build new raid logic against it.
```
**Why:** two design docs prescribe two raid stacks; without this note the next builder wires a dead scaffold. Doc only -- no code touched, no behavior change.

> **integration_hooks = P0-1 through P0-8 above.** All eight are pure string/label/doc corrections the Lead can apply immediately; none require a deploy, a migration, or a logic change; none touch crypto.

---

## B. P1 -- apply soon (concrete, low-risk, but slightly more than a one-string edit)

### P1-1 -- relabel `AK_2D_3D_CONCEPT.md` status banner *(audit Fix #8 / Div-4, Div-6)*
**File:** `AK_2D_3D_CONCEPT.md:1149`
```
OLD:  *Status: READY FOR IMPLEMENTATION*
NEW:  *Status: V2+ ASPIRATIONAL -- NOT the current build track. The AK_SYSTEMS 8-wave plug-in layer was the path taken; the extraction/backpack/"YOU GOT JACKED"/Doc-Wattson-infirmary loop remains DSGN-only.*
```
**Why:** the banner reads as shippable spec; it is V2+ vision. Prevents a builder from starting the heavy extraction-shooter lift thinking it's the agreed track. Doc only.

### P1-2 -- flip the stale "READY TO LAND" wave banners to "LANDED (committed)" *(audit Fix #1 doc-half / Div-6)*
**Files:** `specs/WAVE_INTEGRATION.md` + `specs/MODULE_CONTRACT.md` status lines that still say "READY TO LAND" / "READY FOR IMPLEMENTATION."
```
PATTERN: "READY TO LAND" -> "LANDED (committed 2026-06-20) -- deploy/browser-verify pending (see P1-3)"
```
**Why:** the bootstrap + 8 modules are committed in the host (index.html:74-85, economy.js:91-101, engine.js:1397, game.html:2106/5287). Stale banners misreport state. Doc only. (The *deploy itself* is P1-3, an ops action, not a doc edit.)

### P1-3 -- DEPLOY + Playwright-verify the 8 waves from e5, then mark LIVE *(audit Fix #1 ops-half)*  -- **OPS ACTION, not a text diff**
e5 `~/ak_deploy` -> `ship.sh` (the SOLE deployer; phone never deploys). Smoke-test production first, then walk each building in a real browser on e5. After verify, flip the P1-2 banners "deploy-verify pending" -> "LIVE". Cannot be expressed as an old->new edit; logged here so it is not lost.

### P1-4 -- faction-name shorthand -> canonical full names in docs *(audit Theme-4)*
Where docs abbreviate ("Boneguard / Zoomie / K9 / Leashbreak"), align to the `cards.json` canonical values: **Boneguard Crew / Zoomie Syndicate / Leashbreak Tactix / K9 Circuitry**. Prevents future string-match bugs against card `class`. Doc-copy only; modules already use the full data values. (Apply on touch; not worth a mass rewrite.)

---

## C. P2/P3 -- roadmap (verify/decide; safe but needs a check or a small decision)

### P2-1 -- cache-bust the hub `systems/*.js` tags *(audit Fix #6 / Div-5)*
**File:** `game/index.html:76-85` -- the 10 `systems/*.js` (+ `economy.js:74`, `canon.js:75`) loads are BARE; `game.html` stamps `?v=1781486888`. **Action:** first verify `ship.sh` (on e5, not in repo) rewrites the hub `systems/` tags. If it does not, add the same `?v=<stamp>` suffix so the CDN edge can't serve stale modules:
```
e.g.  <script src="systems/seasons.js"></script>  ->  <script src="systems/seasons.js?v=1781486888"></script>
```
**Why P2 not P0:** it interacts with the deploy stamper; applying a literal `?v=` blind could fight ship.sh's own rewrite. Verify-first.

### P2-2 -- (optional) load `ak_account.js`+`quests.js`+`social.js` in the hub *(audit Fix #5)*
Lets the LIVE in-place Hit List + claim run instead of degrading to `shop#hit2`. **Degrade is graceful today**, so this is an enhancement, not a correction -> apply only when in-place missions are wanted. `game/index.html` script block.

### P2-3 -- perf-audit `seasons.onDrawWorld` on a real phone *(audit Fix #7)*  -- **INVESTIGATION, not a one-line fix**
Full-screen `soft-light fillRect` (alpha .55) + ~22 particles every frame in every zone, stacking under raid's night tint. If FPS dips: cache the wash to an offscreen canvas or gate cadence. **HARD: do NOT strip glows (operator veto) -- pre-render instead.** `game/systems/seasons.js`.

### P3-1 -- resolve Doc Wattson's home (one NPC, two buildings) *(audit Fix #10 / contradiction-5)*
`production.js:58` casts Doc Wattson as the **RESEARCH LAB** keeper (LIVE code). `AK_2D_3D_CONCEPT.md` casts him as the **Infirmary** keeper (DSGN-only). **Resolution:** keep Wattson at the Research Lab (code wins); reassign the (unbuilt) Infirmary to a new keeper.
**File:** `AK_2D_3D_CONCEPT.md` -- change the Infirmary keeper from "Doc Wattson" to a new NPC (e.g. "Patch the Medic"). Doc-only; no code change (Infirmary is unbuilt).

### P3-2 -- mark the lore-faction (tribe) layer DEFERRED in data *(audit Fix #9 / contradiction-2)*  -- quick-fix half
`cards.json` `tribe`/lore-faction = **null on all 106 cards**; only combat `class` is populated. The SAFE quick-fix is the one-line doc flag (the data populate is section D):
**File:** `AK_SYSTEMS_DESIGN.md:46` decision (2) -- append:
```
ADD: >> NOTE 2026-06-20: lore-faction (tribe: Crowned/Rusted/Hologhosts/Unbound) is DEFERRED -- tribe is null on all 106 cards.json. No module may assume it exists until the data populate (AK_AUDIT_FIXPLAN section D) lands. World-map territory colors have nothing to bind to yet.
```
**Why:** prevents a world-map/territory feature from being built against a null field.

### P3-3 -- append the 2026-06-20 AK_SYSTEMS build to the mailbox *(audit Fix #11 / continuity-rail law)*
**Files:** `AGENT_MAILBOX.md` (dated entry: 8-wave layer + MODULE_CONTRACT + WAVE_INTEGRATION committed), `ALLEY_KINGZ_TODO.md` (flip wave statuses). Continuity-rail action; the Lead appends at session end.

---

## D. DEFERRED-TO-ROADMAP -- these are FEATURES, not fixes (do NOT apply as quick edits)
1. **Lore-faction data populate** -- a `data/_build_*.py` pass writing `tribe` on all 106 cards (4 combat factions -> 4 lore factions, or richer). Blocks world-map territory color. *(audit Fix #9 build-half)*
2. **Starter-vs-faction deck reconciliation** -- bumping the 8-card `STARTER_DECK_NAMES` to 11 (or trimming faction decks to 8) is a **REBALANCE** of `decks.json`/starter, not a doc fix. Operator decision required. *(refines contradiction-1)*
3. **Surgical per-building raid (`AK_MODES.raid` win-condition)** -- v1 runs a plain board match labeled RAID; the "defender's base layout = battlefield" mechanic is unbuilt. *(Div-3)*
4. **The whole AK_2D_3D extraction loop** -- backpack tiers, secure slots, "YOU GOT JACKED" death/retrieval, Doc Wattson infirmary, tool crafting, builder queue, crew-shared hub instances, betrayal log. V2+. *(per-system table, DSGN ONLY)*
5. **Breeding (The Kennel)**, **Fortress + wood/stone/metal materials economy**, **bot living-world LLM flavor (ak-flavor)** -- all DSGN/partial. *(per-system table)*
6. **Deploy the `ak-raid` + `ak-trading` edge fns** -- client done, edge fns spec-only/not-deployed (SERVER-PENDING).

---

## CRYPTO / PARITY RE-CHECK (post-edit)
Every A/B/C edit is a label, copy, status-banner, or fn-name-in-a-doc change. **None** add a `gems` grant, field $BCARDD/ALK as loot/reward/utility, alter a shield currency, make a Mythic tradeable, or change a gem to do more than skip a timer. The audit's CRYPTO/PARITY PASS (all 8 waves) remains valid. Supabase target unchanged (`mfghdobptredxxhbjwyz`).
