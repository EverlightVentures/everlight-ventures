# Alley Kingz -- Deep-Dive Gap Audit (Prototype vs Spec)

**Date:** 2026-06-03
**Auditor:** Lucrex (Hive deep-dive)
**Question answered:** what must be filled before pushing a public playtest beta of the web prototype?
**Measured against:** `spec/PRD_V2.md`, `spec/05_DATA_MODEL.md`, `spec/PACK_RIP_OUTCOME_MODEL.md`, `MONETIZATION_UX_REWRITE.md`, `ecosystem/MASTER_BUILD_PLAN.md`, `ECOSYSTEM_ARCHITECTURE.md`
**Inventoried:** `ecosystem/game/{index.html, engine.js, canon.js}` + `ecosystem/game/assets/` + `ecosystem/data/cards.json`

> Honesty note up front: the live build is a SINGLE-MATCH playable combat prototype. It is not the
> game described in PRD_V2 Section "MVP definition" (line 11: "100-level PvE ladder + ranked PvP +
> deck builder + shop + social login + cloud save"). The prototype's own header (`engine.js` lines
> 8-14) and `ARCADE_MOUNT.md` already say this. This audit makes the gap exact.

> One structural caveat: PRD_V2 describes a CAR/CREW roster (Muscle Car, Lowrider, classes
> Street/Cartel/Tech, "NOS Bottles"). The locked 2026-06-03 canon (`MASTER_BUILD_PLAN` section 1,
> `cards.json` meta) replaced that with DOGS-PILOT-RIGS: 48 dogs, 4 factions (Boneguard Crew /
> Zoomie Syndicate / Leashbreak Tactix / K9 Circuitry), rarities Mythic/Legendary/Epic/Rare/Common.
> Where the two disagree, the dog canon wins for ROSTER and the PRD wins for SYSTEMS (ladder,
> economy, monetization, screens). This audit measures the prototype against both layers and flags
> where the PRD text itself is now stale and should be reconciled.

---

## 1. ARENA RECONCILIATION

**Spec requirement (PRD_V2 Section 4.2, "Ladder Arenas"):** 10 named NOS-Bottle ladder arenas, each
with a threshold and zone flavor:

| # | Arena | NOS Bottles | Built? |
|---|-------|------------|--------|
| 1 | The Lot | 0 (starting area, rusted cars) | NO |
| 2 | Strip Run | 400 (neon drag strip) | NO |
| 3 | Parking Structure | 800 | NO |
| 4 | The Blocks | 1200 | NO |
| 5 | Interchange | 1600 | NO |
| 6 | The Yard | 2000 (industrial salvage) | partial (see map) |
| 7 | Neon District | 2600 (downtown nightlife) | partial (see map) |
| 8 | Embassy Row | 3200 | NO |
| 9 | The Penthouse | 4400 | NO |
| 10 | Empire State | 5000+ (league play) | NO |

**What actually exists:** exactly 3 generic arena backgrounds plus 6 tower decals
(`assets/arena/arena_a_neon_night.png`, `arena_b_golden_industrial.png`, `arena_c_rain_docks.png`;
`assets/arena/towers/<arena>_{king,princess}.png`). They were named by the art generator
(`art/generate_icons.py` ARENAS list / `art/ART_PROMPT_PACK.md` section 5), NOT by the PRD ladder.

**Closest spec mapping (best-fit, not 1:1):**
- `arena_a_neon_night` -> **Neon District** (#7, downtown nightlife, magenta neon on wet asphalt)
- `arena_b_golden_industrial` -> **The Yard** (#6, industrial salvage, rust/brick warm tones)
- `arena_c_rain_docks` -> closest to **Interchange/Embassy waterfront**; no clean PRD slot (the
  docks theme is not in the PRD ladder at all -- it is a generator invention)

**FLAG (the critical one):** **"The Lot" (the 0-NOS starting arena, rusted cars) DOES NOT EXIST.**
That is the arena a brand-new tester must boot into. Worse, the engine only ever renders ONE arena:
`index.html` line 313 hardcodes `const ACTIVE_ARENA = 'arena_a_neon_night'`. So today every match,
for every tester, happens in a high-tier neon downtown board. There is no arena progression, no arena
switching code, and the two other PNGs that exist (`arena_b`, `arena_c`) are never shown.

**Verdict:** the prototype ships the WRONG arena for a first-time player. A beta tester at 0 NOS
should see The Lot (gritty, rusted, low-stakes), and instead sees the glossy endgame board.

**Recommended fix (cheap, beta-blocking):**
1. Generate **The Lot** as the boot arena + its 2 tower decals (Leonardo pipeline, prompt below).
   Re-anchor the engine to boot into it (`ACTIVE_ARENA = 'arena_the_lot'`).
2. Rename/re-anchor the generator's `ARENAS` list to the PRD names so future arenas map cleanly:
   `arena_a_neon_night` -> `arena_07_neon_district`, `arena_b_golden_industrial` -> `arena_06_the_yard`.
   Keep the 3 existing renders, just rename + tag with the NOS threshold.
3. Generate the next low tiers a tester actually climbs through next: **Strip Run (400)** and
   **Parking Structure (800)**. The Blocks/Interchange and up can wait for full-game.
4. For beta, an arena does not need to "unlock" -- it only needs to be the RIGHT-LOOKING board for a
   newcomer (The Lot). Arena-by-NOS switching is a NICE-TO-HAVE, not a beta-blocker.

---

## 2. DEFAULT vs CUSTOM INVENTORY

Every visible element, classed as CUSTOM ART (done) | PLACEHOLDER (procedural/CSS, looks default) |
MISSING.

| Element | Status | Detail / spec cite |
|---|---|---|
| **Unit icons** | CUSTOM (41 of 48) | `assets/units/NNNN_slug.png` count = 41. 7 missing (see below). Card art = unit portrait per memory note + `index.html` line 327 preloader. |
| **Tower skins** | CUSTOM (but only 1 arena) | 6 decals exist; only the `arena_a_neon_night` pair is wired (`ACTIVE_ARENA`). Other 4 never load. PRD_V2 4.2. |
| **Arena background** | CUSTOM (wrong tier) | 3 exist, 1 wired, none is The Lot. See Section 1. |
| **Card faces (in hand)** | PARTIAL | Hand renders the unit PNG inside a rarity-colored CSS frame (`engine.js` RARITY_COL; `index.html` ~line 827). There is NO designed card face per PRD_V2 9.1 (chrome/gold/teal border by type, CREW/SPELL/STRUCTURE badge, stat bars HP/DMG/SPD, rarity gemstone). It is a portrait in a colored box, not a "Pokemon/garage stat card." |
| **Start screen** | PLACEHOLDER | CSS only: "AK" text crest, gradient title, Play button (`index.html` 220-228). No logo art, no key art, no hero dog. |
| **Result screen** | PLACEHOLDER | CSS text VICTORY/DEFEAT/DRAW (`index.html` 258-268). No win/lose art, no reward animation, no NOS delta, no chest. PRD_V2 1.1 (3-crown bonus) / 4.1 (NOS gain-loss) not represented. |
| **Energy / elixir bar** | PLACEHOLDER | CSS bar + pips (`index.html` #energybar #energyfill #energypips). PRD calls it the NOS-tank with "liquid NOS animation, bubbles" (9.2) -- not built; it is a flat fill bar. |
| **HP bars (units + towers)** | PLACEHOLDER | Procedural canvas bars (`index.html` drawUnit/drawTower). Functional, generic. PRD 9.2 "red glow under 30%" for HQ Van not implemented as art. |
| **Buttons / UI chrome** | PLACEHOLDER (on-brand) | CSS, gold-on-vanta, matches palette (PAL in engine.js + PRD 9.3 colors). Looks intentional, not broken. |
| **Fonts** | PARTIAL | Inter + Cinzel/serif loaded; PRD 9.3 asks for "Bebas Neue or similar" bold condensed urban. Current is clean but not the urban display face. |
| **Crowns / timer / topbar** | PLACEHOLDER (on-brand) | CSS text (`index.html` 232-236). Fine for beta. |
| **Projectiles / particles / muzzle / slash** | CUSTOM (procedural, good) | Fully coded weapon-FX system per weaponType (engine.js doAttack/launchProjectile). This is the prototype's strongest layer -- reads as designed, not default. |
| **SFX** | PLACEHOLDER (synth) | WebAudio oscillator tones only (engine.js sfx()). PRD Section 8 wants engine revs, crashes, sirens, hip-hop music -- NONE of that exists; it is beeps. |
| **Music** | MISSING | PRD 8.2 (battle / double-elixir / overtime / menu tracks) -- none. |

**The 7 missing unit icons** (all the K9 Circuitry tail): 0038 Circuit Retriever (Epic), 0039 Nova
Shepherd (Epic), 0043 Chrome Airedale (Rare), 0044 Beacon Basset (Rare), 0046 Flux Pomeranian
(Common), 0047 **Rail Terrier** (Common), 0048 **Pixel Pug** (Common).

**Beta-critical inside that list:** **Rail Terrier (0047)** is in the STARTER DECK
(`engine.js` STARTER_DECK_NAMES) and **Pixel Pug (0048)** is the unit the `spawn` ability summons
(`engine.js` spawnDrone). Both appear in the FIRST match a tester plays, and both have NO portrait --
they fall back to a blank/glyph tile. These two must be generated before any playtest.

---

## 3. STORE / SHOP / ECONOMY ASSETS NEEDED (per PRD Section 5)

The shop is NOT built (no shop screen exists -- Section 4 below). But the ART for the economy can be
generated now so it is ready. None of the following exist today:

| Asset | Spec cite | Status |
|---|---|---|
| **NOS Bottle canister icon** (orange/blue) -- the trophy/ladder unit | PRD 4.1 | MISSING |
| **Fuel icon** (soft currency, gold analog) | PRD 5.1 | MISSING |
| **Gears icon** (mid/season currency) | PRD 5.1 | MISSING |
| **Gems icon** (hard/IAP, purple) | PRD 5.1 + MONETIZATION_UX 4 (Gem Purple #7B2FF7) | MISSING |
| **Chest art, tiered** (free/silver/gold/legendary chests) | PRD 1 loop ("Chest Unlock") + 05_DATA_MODEL ChestType | MISSING |
| **Crew Pass banner** ($9.99/35d reward track) | PRD 5.2 #1 | MISSING (note: MONETIZATION_UX renames this to "Master Pass $14.99/mo" arcade-wide -- reconcile) |
| **Starter Pack banner** ($4.99 one-time) | PRD 5.2 #4 | MISSING |
| **Revival Pack banner** ($2.99, fires on 5-loss streak) | PRD 5.2 #3 | MISSING |
| **Cosmetic shop tiles** (car/rig skins, arena themes, emotes) | PRD 5.2 #6 | MISSING |
| **League badges** (Bronze Crew -> Silver -> Gold -> Platinum -> Diamond -> The Council -> Alley King) | PRD 4.3 | MISSING (7 badges) |
| **Win / Lose / Reward screen art** | PRD 1.1, 9.x | MISSING (currently CSS text) |
| **Deck-builder UI** (frame, slots, filter chips, synergy meter) | PRD Section 6 | MISSING |
| **Chop Shop UI** (merge two dupes -> random new) | PRD 5.2 #5 | MISSING |

**Conflict to resolve (cite):** PRD 5.2 says **Crew Pass $9.99/35 days** (per-game). `MONETIZATION_UX_REWRITE.md`
(sections 1-2) supersedes that with an arcade-wide **Master Pass $14.99/mo** + optional **Alley Kingz
Pass $4.99/mo**. Lock one before any pass art is generated, or you generate the wrong banner.

---

## 4. UI / FEATURE GAPS for a web beta

PRD_V2 MVP (line 11) vs what is live:

| MVP feature | Spec cite | Live status |
|---|---|---|
| **100-level PvE ladder** | PRD Section 3 | MISSING. No level map, no level select, no difficulty scaling wired (the scaling algorithm in 3.1 / 05_DATA_MODEL is spec-only). |
| **Ranked PvP** | PRD line 11 | MISSING. No netcode, no matchmaking. AI is a scripted single opponent (`engine.js` updateAI). |
| **Deck builder** | PRD Section 6 | MISSING. Deck is a hardcoded 8-name STARTER_DECK; no builder screen, no filter/sort, no synergy meter, no deck slots. |
| **Shop** | PRD Section 5 | MISSING. No shop screen at all. |
| **Social login** | PRD 7.1 | MISSING. No auth. |
| **Cloud save** | PRD 7.2 | MISSING. No persistence -- state resets every reload. |
| **NOS-Bottle ladder + progression** | PRD Section 4 | MISSING. No NOS counter, no gain/loss on result, no arena promotion. |
| **Currencies (Fuel/Gears/Gems)** | PRD 5.1 | MISSING. No currency tracked anywhere in client. |
| **Chests / rewards** | PRD 1 loop | MISSING. |
| **Card upgrades** | PRD 2.2 (upgradeMultiplier) + `game/UPGRADE_SPEC.md` | MISSING from the live build. |
| **HQ Van game-over** | PRD 1.2 / 1.3 / 05_DATA_MODEL HQVanState | PARTIAL. King tower (Alpha Den) death ends the match (`engine.js` checkWin/checkTowerDeath), but there is no "YOUR CREW IS DOWN" van-explosion screen, no siren, no 30% red-glow. The MECHANIC exists; the spec's signature MOMENT does not. |
| **3-min match / double elixir / overtime** | PRD 1.1 | PARTIAL. 150s match + energy doubles in the last 40s (`engine.js` MATCH_TIME / update rate). No sudden-death overtime, no double-elixir visual cue. |
| **Two lanes + bridges + king-locked-until-princess** | (genre) | DONE and solid (`engine.js` findTarget/moveToward/lane logic). |

**What IS playable today (the honest positive):** one full 1-match demo -- start screen -> 3s
countdown -> live lane combat vs a scripted AI in one arena, with the real 48-card canon stats,
energy economy, abilities firing as a categorized effect set, weapon-typed projectiles, screen shake,
crown logic, and a win/lose/draw result. It runs with zero build step from any static host
(`ARCADE_MOUNT.md`). It is a genuinely fun COMBAT TOY, not the full game.

---

## 4b. META-GAME GAPS (the Clash-Royale layer -- ALL NOT-BUILT)

The combat prototype is the FIGHT. The "meta-game" is everything that wraps the fight (PRD_V2
Section 1.0 loop: `Login -> Daily Rewards -> Pick Deck -> Battle -> Post-match NOS -> Chest ->
Upgrade -> Repeat`). The full design is in `ecosystem/META_GAME_BUILD_PLAN.md`; here is the gap
status. **None of the six systems exist in the live build.**

| # | Meta system | Spec cite | Status | Effort (honest) |
|---|---|---|---|---|
| 1 | **Card levels + upgrade economy** (L1-10, dupes + Fuel, +10%/lvl HP+DMG linear) | PRD_V2 2.2 / 05_DATA_MODEL `upgradeMultiplier` / `UPGRADE_SPEC.md` | NOT BUILT | THIS WEEK (1-2 days; engine reads `card.hp/dmg` so it is a stat multiply, no combat rewrite) |
| 2 | **Accounts + cloud save** (Google OAuth via Supabase Auth) | PRD_V2 7.1 / 7.2 / 05_DATA_MODEL PlayerData | NOT BUILT (state resets every reload) | THIS WEEK (2-3 days; reuses Supabase Auth + existing `/auth` + `player_accounts`) |
| 3 | **Economy + shop + Stripe** (Fuel/Gears/Gems; gem packs, pass, starter/revival packs) | PRD_V2 5.1 / 5.2 / MONETIZATION_UX_REWRITE | NOT BUILT | LATER (~3-4 days build, multi-week responsibly -- legal-gated) |
| 4 | **Player profile + marketplace** (NOS, league badge, collection, stats; buy cards/currency) | PRD_V2 4.1 / 4.3 / ECOSYSTEM_ARCHITECTURE 6 | NOT BUILT | THIS WEEK profile read-view (1-2 days); LATER marketplace link |
| 5 | **PvE arena ladder** (10 NOS arenas, difficulty scales via `setDifficulty(0-9)`) | PRD_V2 4.2 / engine.js line 272, 921 | NOT BUILT | THIS WEEK (1-2 days code; needs arena ART -- The Lot etc.) |
| 6 | **Ranked PvP** (NOS-bracket matchmaking + server-authoritative netcode) | PRD_V2 line 11 | NOT BUILT (AI is a scripted single opponent) | LATER, LAST (multi-week to multi-month -- the heaviest piece by far) |

**The keystone:** System 2 (accounts + cloud save). Card levels (1) and the ladder (5) are
meaningless without a place to save them. Build accounts first.

**The engine already helps with two of the six:**
- **Card levels (1)** are a one-line transform -- the engine reads base stats off the canon card
  object (`engine.js` ~line 301: `this.maxHp=card.hp; this.dmg=card.dmg`), so feeding it
  `card.hp * levelMult(level)` needs no combat-loop change.
- **The PvE ladder (5)** is mostly wiring -- `AK.setDifficulty(0-9)` (engine.js line 272/921) is
  already keyed "The Lot ... Empire State," so each of the 10 PRD arenas maps 1:1 to a difficulty
  index. The hard part (AI scaling) is done.

**Honest line in the sand:** accounts + payments are NOT a same-day build done responsibly. Accounts
become the source of truth for all player state and touch PII -- they get a Supabase migration, RLS
policies, and a tested save/restore path, not a Friday hack. Payments add live Stripe + three legal
gates (ECOSYSTEM_ARCHITECTURE section 8) on top. Treat Phase W (the spine) as a week and Phase L
(money + crypto + ranked) as multi-week, gated work.

---

## 5. PRIORITIZED PUNCH-LIST

### Bucket A -- MUST-HAVE before a public playtest beta (makes it not look broken/default)

1. **Generate the 7 missing unit icons**, prioritizing **Rail Terrier (0047)** and **Pixel Pug
   (0048)** -- both appear in the first match (starter deck + drone spawn) and currently render blank.
   *Generatable via existing Leonardo pipeline* (`art/generate_icons.py --only 0047` etc.; prompts in
   `art/ART_PROMPT_PACK.md`). Cost: ~150 free Leonardo tokens/day covers all 7. (Spec: PRD 2.5 / cards.json)
2. **Generate "The Lot" arena + its 2 tower decals and boot into it** (`index.html` line 313). Today
   testers spawn in the endgame neon board, which is wrong for a 0-NOS newcomer. *Generatable via
   Leonardo* (add an `arena_the_lot` entry to the generator's ARENAS list, prompt:
   "rusted-out junkyard lot, cracked concrete, dead street lamps, two side bridges, three tower pads
   per side, gold #D4AF37 tower pads, gritty low-tier, hyper-real PBR, vanta-black sky"). Then one
   line of code to re-anchor `ACTIVE_ARENA`. (Spec: PRD 4.2)
3. **Real start-screen key art + logo** (replace the "AK" CSS crest). A single hero image of $BCARDD
   in his rig sells the game in the first 2 seconds. *Generatable via Leonardo/Seedance.* (Spec: PRD 9)
4. **NOS delta on the result screen** ("+30 NOS" / "-22 NOS") even if it is purely cosmetic and not
   persisted yet -- it makes a match feel like it mattered. *Code only* (small edit to showResult in
   `index.html`). Pair with a NOS-canister icon (*Leonardo*). (Spec: PRD 4.1)
5. **Replace synth-beep SFX with at least deploy / hit / tower-down / win-lose samples.** The current
   oscillator tones read as "unfinished." Even 6 free CC0 samples lift perceived polish hugely. *Asset
   sourcing + small code wire-up* (engine.js sfx()). (Spec: PRD Section 8)

(Honorable mention, A-/B: a proper card-face frame with stat bars per PRD 9.1. Bigger design lift;
the portrait-in-a-colored-box is passable for a combat-only beta, so it sits at the A/B boundary.)

### Bucket B -- NICE-TO-HAVE soon (after beta validates the loop)

- Arena-by-NOS switching (wire the 3 existing + The Lot to NOS tiers). *Code.*
- Strip Run + Parking Structure arenas. *Leonardo.*
- Designed card faces with HP/DMG/SPD stat bars + rarity gemstone + type badge (PRD 9.1). *Design + code.*
- HQ Van "YOUR CREW IS DOWN" explosion + siren moment (PRD 1.2-1.3). *Code + 1 art/SFX.*
- Sudden-death overtime + double-elixir visual cue (PRD 1.1). *Code.*
- Liquid-NOS animated energy bar (PRD 9.2). *Code.*
- Currency icons (Fuel/Gears/Gems) + chest art, ready for when the meta-game lands. *Leonardo.*

### Bucket C -- FULL-GAME LATER (post-beta, real product)

- 100-level PvE ladder + level map + difficulty scaling (PRD Section 3, algorithm already specced).
- Deck builder with filter/sort/synergy meter + deck slots (PRD Section 6).
- Shop + Crew/Master Pass + Starter/Revival packs + cosmetics + Chop Shop (PRD Section 5 /
  MONETIZATION_UX_REWRITE) -- and the pack-rip legal posture (`PACK_RIP_OUTCOME_MODEL.md` -- Rich's
  A/B/C decision is still BLANK; do not ship paid packs until it is signed).
- Social login + cloud save (PRD Section 7).
- Ranked PvP netcode + matchmaking.
- League badges (PRD 4.3), card upgrades (`UPGRADE_SPEC.md`), $BCARDD / Solana NFT mint hooks
  (`MASTER_BUILD_PLAN` Phases 3-5).
- Music tracks (PRD 8.2).

---

## 6. READY-TO-PUSH ASSESSMENT

**Is it web-testable today?** Yes, technically. It is a self-contained static build (index.html +
canon.js + engine.js, zero npm) that runs from any static host or an iframe per `ARCADE_MOUNT.md`,
and the core combat is genuinely fun. But it should NOT be pushed to a public playtest as-is, for two
visible-in-the-first-30-seconds reasons:
1. Two starter-relevant cards (Rail Terrier, Pixel Pug) render with NO portrait.
2. Every tester is dropped into the glossy endgame Neon District board instead of The Lot, and the
   start screen is a CSS "AK" placeholder with no key art.

**Minimum gap-fill to push a playtest (Bucket A, ~1 focused day):** generate the 7 missing icons
(prioritize 0047 + 0048), generate + wire The Lot as the boot arena, drop in real start-screen key
art, add a cosmetic NOS delta on the result screen, and swap synth beeps for a handful of real
samples. Everything in Bucket A except the SFX is generatable via the existing Leonardo pipeline plus
small code edits -- no new architecture.

**What testers must be told it is:** "An early COMBAT PROTOTYPE -- one live match against an AI to
test the feel of the lanes, the dogs, the rigs, and the abilities. No progression, no shop, no
accounts, no save yet. We want feedback on whether the FIGHT feels good." The build already self-labels
"Early prototype. Not financial advice." -- keep that, and add the combat-prototype framing so no one
expects a ladder, a shop, or a saved profile.

---

## 7. RE-BUCKETED PUNCH-LIST: TODAY / THIS WEEK / LATER

The earlier Buckets A/B/C are scoped to the ART for a combat beta. This section re-buckets the WHOLE
product (combat + the six meta-game systems from section 4b) by honest delivery window. It is the
operator-facing answer to "what actually ships when."

### (A) SHIPS TODAY -- the free combat prototype, no accounts, no payments
- The single-match combat toy, deployed to web. Zero backend. Reuses the static
  `index.html/engine.js/canon.js` + Cloudflare Pages + the vantaris `/play/*` mount pattern.
- Gap-fill first per section 5 Bucket A: generate the 2 blank starter icons (Rail Terrier 0047 +
  Pixel Pug 0048), generate + boot into The Lot arena, real start-screen key art, cosmetic NOS
  delta, a handful of real SFX samples.
- Framed honestly as a COMBAT PROTOTYPE (section 6). **Effort: hours.**

### (B) THIS WEEK -- the spine (accounts + cloud save + card levels + PvE ladder)
- **Accounts + cloud save** (section 4b #2) -- Google OAuth via Supabase Auth, reusing the existing
  `/auth` page + `player_accounts`. The keystone.
- **Card levels** (section 4b #1) -- L1-10, +10%/lvl HP+DMG linear, dupes + Fuel. One stat-multiply
  transform on the canon card before the match; engine unchanged.
- **PvE arena ladder** (section 4b #5) -- 10 NOS arenas wired to `setDifficulty(0-9)`; NOS up/down on
  result; rewards per arena. (Code is ~1-2 days; the BLOCKER is arena ART, still MISSING.)
- **Player profile read-view** (section 4b #4) -- render NOS, league badge, collection, stats.
- **Effort: ~1 focused week. Explicitly NOT a same-day build -- accounts are the source of truth and
  get a Supabase migration + RLS + a tested save/restore path.**

### (C) LATER -- shop/Stripe, NFT marketplace, ranked PvP (gated)
- **Shop + Stripe** (section 4b #3) -- gem packs, the pass, starter/revival packs, cosmetics-only
  guardrail. Reuses the live `verify-arcade-purchase` backbone. **Blocked on:** the Crew-Pass
  ($9.99/35d, PRD_V2 5.2) vs Master-Pass ($14.99/mo, MONETIZATION_UX_REWRITE) conflict + legal
  sign-off on live payments + the PACK_RIP_OUTCOME_MODEL A/B/C decision (still BLANK). Multi-week.
- **$BCARDD on-ramp + NFT marketplace** (section 4b #4 marketplace) -- `verify-bcardi-onramp`,
  wallet-connect, Tensor/Magic Eden listing in $BCARDD. **Blocked on:** the full Phase-3 Metaplex
  mint (MASTER_BUILD_PLAN) + Legal Gates 1-3 (ECOSYSTEM_ARCHITECTURE 8).
- **Ranked PvP** (section 4b #6) -- matchmaking + authoritative server + netcode + server-side match
  validation. **The heaviest build by far; LAST. Multi-week to multi-month.** Ship single-player
  first, prove the loop is fun, then invest in netcode.

> **The same-day caveat, stated plainly:** accounts + payments are NOT a responsible same-day build.
> Accounts touch PII and become the source of truth for all player state. Payments add live Stripe +
> three legal gates. Anyone promising "accounts and a shop by tonight" is promising a liability, not a
> product. The fastest RESPONSIBLE path is: combat toy today -> the spine this week -> money + crypto +
> ranked later, behind the gates.

---

## 8. PHASED ROADMAP (honest sequencing + infra reused per phase)

| Phase | When | What ships | Existing infra reused | Gated on |
|---|---|---|---|---|
| **T -- TODAY** | hours | Free combat prototype to web (no accounts/payments) | static build, Cloudflare Pages, vantaris `/play/*` | nothing (gap-fill section 5 Bucket A first) |
| **W -- THIS WEEK** | ~1 week | Accounts + cloud save + card levels + PvE ladder + profile | Supabase Auth + Google OAuth + `/auth` + `player_accounts`; engine stat-read + `setDifficulty` | arena art (Leonardo) for the ladder |
| **L1 -- LATER** | multi-week | Shop + Stripe (gem packs, pass, starter/revival, cosmetics) | `verify-arcade-purchase`, Stripe live, `game_currencies`/`game_passes` | pass-name conflict + legal sign-off on payments |
| **L2 -- LATER** | multi-week | $BCARDD on-ramp + NFT marketplace link | $BCARDD coin, Metaplex mint pipeline, Tensor/Magic Eden | full Phase-3 mint + Legal Gates 1-3 |
| **L3 -- LATER, LAST** | multi-week to multi-month | Ranked PvP (matchmaking + authoritative netcode) | Supabase Realtime for matchmaking | a dedicated game server + netcode (the big lift) |

Full system-by-system design, data models, and effort estimates: `ecosystem/META_GAME_BUILD_PLAN.md`.

---

*Audited 2026-06-03. Sources: PRD_V2.md, 05_DATA_MODEL.md, PACK_RIP_OUTCOME_MODEL.md,
MONETIZATION_UX_REWRITE.md, MASTER_BUILD_PLAN.md, and a line-level read of
ecosystem/game/{index.html, engine.js, canon.js} + assets/ + data/cards.json. Nothing in this audit
is projected -- every "MISSING" was confirmed absent from the live files.*
