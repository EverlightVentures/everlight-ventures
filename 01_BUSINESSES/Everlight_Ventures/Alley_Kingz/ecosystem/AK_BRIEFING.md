# ALLEY KINGZ -- BRIEFING PACKET

**Read this file first.** It is the entry point for the attached bundle. Everything below was
verified by reading the actual code and data on 2026-07-18, not summarized from older docs. Where a
claim is unverified or in progress, it says so.

Live build: **https://alleykingz.online** (open it on a phone; it is mobile-web first, no install).

---

## 1. WHAT THE GAME IS

Alley Kingz is a mobile-web game about dog gangs running city blocks. It is currently one Canvas2D
codebase (`game/index.html`, ~4,300 lines, plus `game/systems/*.js`) with a 3D hero layer overlaid on
top, mid-migration toward full 3D.

It is deliberately several games sharing one state:

- **RPG hub** -- you walk a district as a real character, enter buildings, take jobs
- **Collectible roster** -- 106 dog cards, real exotic breeds, each with stats, an ability, and a rig
- **Tower defense / battle** -- the card game layer (`game.html`)
- **Raids** -- asynchronous, server-authoritative, raid a real player's base snapshot
- **Base building** -- Town Hall, producers, upgrades, fortifications
- **Story mode "Crown Bloodline"** -- a gritty clan saga, 6 arcs, comic panels, voiced
- **Arcade minigames, encounters, trading, marketplace, crew/clan social layer**

Tone is adult street-noir. Not a kids game.

## 2. WHAT IS VERIFIED REAL (counted on disk, 2026-07-18)

The narrative content is the single biggest asset and it is **not** aspirational:

| Asset | Verified |
|---|---|
| Card roster | **106 cards**, complete across 4 separate files with **zero** name/breed/faction/rarity mismatches |
| Story books | **106**, every one carrying codename, publicHook, coreWound, definingChoice, secretTruth |
| Taglines + bios | **106**, byte-identical between `cards_lore.js` and `card_roster.json` |
| Comic panels | **387 real JPEGs**, ~115 MB (not stubs; smallest is 115 KB) |
| Voice lines | **114 mp3s**, covering **100%** of the roster |
| Bosses | **12**, with 60 panel prompts |
| War rigs | **20** defined in `art/rig_bible.json` |
| 3D heroes | **2 live GLBs** -- $BCARDD (13 MB) and Jagged (19 MB), both animated (idle/walk/run) |

For context: Clash Royale deliberately shipped **no** campaign. This project has more finished
narrative than any of its benchmark competitors had at launch.

## 3. THE TWO-AXIS IDENTITY MODEL (migrated 2026-07-18)

This was the biggest data inconsistency in the project and it is now resolved. Previously two
taxonomies described the same 106 dogs and 101 of them disagreed, with the token "BONEGUARD" meaning
different things on each side.

Every card now carries **both**, with no shared token between them:

- **`crew`** -- where the dog is FROM (origin block). 8 crews:
  MUTT$ 34, NIGHTSHIFT 23, SNAKE EYES 15, K-CLUB 10, SCRAPJAW 8, ASHLINE 7, CROWN LOT 5, RUST HALO 4
- **`class`** -- what he FIELDS (the deck axis). 4 factions:
  Leashbreak Tactix 28, Boneguard Crew 26, Zoomie Syndicate 26, K9 Circuitry 26

The old colliding crew name BONEGUARD was renamed **CROWN LOT**. Cross-axis token collisions: zero.

**In progress:** the operator's directive is that the 8 crews BECOME the factions, each fielding an
11-card deck. That requires **21 new cards** (K-CLUB +1, SCRAPJAW +3, ASHLINE +4, CROWN LOT +6,
RUST HALO +7), each with full art prompt, story, lore, and bond entries. That build is underway.

## 4. HONEST STATE: WHAT WORKS AND WHAT IS A FACADE

This section exists so nobody assumes. All of it is code-verified.

**Progression math is sound.** ~3,700 gold/hour for an active player; the next Town Hall level is
about 2 hours of real play. Nothing is unreachable. Active players out-earn idle 8-18x.

**But the feedback layer lies, and that is why it reads as broken:**

- **9 of 11 perk buildings do nothing when upgraded.** Only GARAGE and FIXER have any effect.
- The Town Hall panel promises "Crew size" and "Base grid" increases that **have zero consumers**.
- Raid and Watch duty reporters have **zero call sites**, so 2 of 3 dailies, 2 of 3 weeklies and
  2 keys/week can never be claimed.
- **Gems are decorative** -- never granted anywhere; the HUD shows a dash forever.
- Crew wars are **dark**: tables deployed and client built, but the `ak-crew` edge function is
  missing `war-status`, `war-start`, `war-battle`. The UI honestly degrades to "wars open soon".
- Dailies/weeklies are **gated behind Google sign-in**, and auth sits at stage 2 of a 7-step
  first-run sequence -- i.e. an auth wall before the hook, on a platform whose main advantage is
  zero install friction.
- **Save-loss risk:** progression is one localStorage blob. Signed out + cache clear = total
  unrecoverable loss, with no export/import. First sign-in overwrites local with cloud
  unconditionally. Save failures are swallowed silently.
- A **12-step tutorial overlay** (`ak-tut-root`, z-index 9000) sits on top for new players.

**Fixed and shipped 2026-07-17/18** (all live-verified on the edge):
hero ring/aura removed under the 3D hero; a collision corner-wedge that froze the player against
obstacles ("invisible wall"); 3D hero facing; walk-cycle speed decoupling (a light thumb-roll played
a full-speed walk while barely moving -- the "stuck walk"); five producer buildings mislabeled
"COMING SOON" while fully working; producer facade levels that lied; `juice.js` 404ing on the live
site; hero-switching so the 3D model follows the selected runner.

## 5. ARCHITECTURE NOTES A NEW READER WILL GET WRONG

- **The camera centers the player** (`cam.x = me.x - W/2`). The hero holding screen-center while the
  world scrolls is correct, not a bug. This has been misdiagnosed from video twice.
- **Districts are a deliberate 3x3 Stardew-style grid** of 9 discrete zones, each 1550x1150, swapped
  in place with an opposite-edge spawn rule. The black fade plus gold particle wall on transition is
  an authored cinematic (`transition_wipe.mp4`), specced by the operator, not a loading-screen bug.
  It already prints the district identity card ("THE YARDS / The Rusted City / SCRAP district").
- **Two builds share the repo:** `index.html` is the hub/RPG; `game.html` is the battler. Some
  systems only load on one side.
- Cosmetics DO charge correctly through the catalog path (gold check, server ack, debit, grant). The
  cosmetic *parts* price ladder, separately, has no buy path.

## 6. THE COMPETITIVE READ

Benchmarked against Clash Royale, Clash of Clans, Brawl Stars, League of Legends, World of Warcraft,
Fortnite, and Dark War Survival (researched from design teardowns and developer sources).

**The gaps are mostly wiring, not building:**

1. The cosmetic parts register has no buy path
2. Crate timers exist (3 slots, 15min-24h) with **zero notification code** -- the timer fires into
   the void, and timer-plus-callback is the entire Clash appointment engine
3. The first session is auth-gated before the hook
4. The reward moment is flat: 5 chest tiers share 1 animation, a variable-ratio rarity ticker is
   written but unconnected, and a 26 KB sound engine idles at 6 boss-only call sites
5. Crew wars are three server actions away from working

**The unfair advantage:** more finished narrative than any benchmark had at launch, a real
server-authoritative async raid loop that scales at any population, web-first zero-install
distribution, and `viral.js` (every big moment mints a 9:16 clip with a `?ref=` invite, zero backend).

**Recommended spine:** pace the 30-day loop on **story chapters, not ranked ladders**. A weekly story
beat works identically at 12 players and at 120,000. Ranked ladders, rotating modes, and live events
all need population the game does not have yet.

## 7. WHAT IS IN THIS BUNDLE

- `docs/` -- design bibles, canon, specs, economy and taxonomy design, the state-of-the-game and
  incorporation matrix, the 2D-to-3D concept, and the migration workflow
- `data/` -- the actual card data: all 106 cards, lore, story books, bonds, rigs, roster art prompts
- `code_samples/` -- a few representative system files so the architecture is legible without the
  full repo

**Not included, deliberately:** the art and model binaries. 387 comic panels are ~115 MB and the two
hero GLBs are 13 MB and 19 MB, which will not survive email. See the live site for those.

## 8. OPEN DECISIONS (owner: Rich Gee / Everlight Ventures)

1. **8 crews become the factions**, each needing an 11-card deck -- 21 new cards in production.
2. **Town Hall as a level cap** (Clash rule: TH sets the ceiling, buildings are still upgraded
   individually, materials interlock) -- being built now.
3. **Map loot labeling and gathering** (wood/stone/iron/scrap feeding a fence tier ladder) -- being
   built now.
4. **3D map and buildings**, and a Clash-of-Clans-style 2D builder mode sharing one state with the
   3D world -- specced in `RENDER_MODE_CANON.md`, not yet built.
5. **Seamless open world** vs the current discrete district grid -- a real design ambition, costed as
   a multi-week rewrite, not a bug fix.

---

*Prepared 2026-07-18. Everlight Ventures. Questions about anything in section 4 should be checked
against the code before acting -- this project has a documented history of docs drifting ahead of
implementation, which is exactly why that section exists.*
