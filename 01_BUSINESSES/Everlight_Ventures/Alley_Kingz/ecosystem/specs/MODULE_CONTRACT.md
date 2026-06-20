# ALLEY KINGZ -- PLUG-IN MODULE CONTRACT (`AK_SYSTEMS`)
**Lead Architect spec. Handed verbatim to 8 parallel implementers.**
Date: 2026-06-20 | Owner: Lead Architect (Hive) | Status: CONTRACT LOCKED
Grounds: `AK_MASTER_GAME_DESIGN_SYNTHESIS.md` (14-game fusion) + the LIVE repo
(`game/index.html` hub, `game/engine.js` battler, `game/economy.js` `AK_ECON`,
`game/shop/shop.js`, `game/social.js`, `data/cards.json` 106 cards, `game/handlers_data.js`).

---

## 0. THE PRIME DIRECTIVE (why this contract exists)

8 waves -- **production, missions, encounters, raid, seasons, trading, arcade, modes** --
build IN PARALLEL with **ZERO merge conflicts**. The mechanism:

1. **The shared host files are edited EXACTLY ONCE, up front, by the Lead** (Section 6: the
   Bootstrap). After that commit lands, **no wave ever touches** `index.html`, `economy.js`,
   `engine.js`, or `game.html`.
2. **Every wave adds exactly ONE new file:** `game/systems/<id>.js`. It self-registers into
   `window.AK_SYSTEMS` at load. Plus, if it has a server need, ONE new dir under
   `supabase/functions/<fn>/` and ONE new migration `supabase/migrations/<ts>_<id>.sql`.
3. **All new player-state lives behind falsy-default fields** added in the SINGLE consolidated
   `ensureShape` block (Section 6.B). A zero-state profile stays byte-identical in shape.

Two files touched by two people = a conflict. Under this contract, each wave touches a
disjoint set of brand-new files. The host never changes again.

### HARD RULES (inherited, non-negotiable)
- **2.5D Canvas2D. NEVER fork the battler.** Alternate combat = `AK.newMatch(deck,{mode})`. Light
  mini-games = `ctx.overlay.open(...)` (a fresh Canvas2D layer). Add NO engine primitives.
- **Crypto gate:** soft-currency / cosmetic ONLY. Gems skip **TIMERS only**. **NO `$BCARDD`/`ALK`
  in any utility, trade, or reward.** `ctx.currency.grant('gems',...)` is a hard no-op -- gems are
  **server-only**.
- **New economy state = falsy-default via `mutateProfile`.** Empty `{}` / `0` defaults only.
- **Reuse the 106 cards + 6 handlers BY NAME** as every unit / bot / stock item / target / roamer.
  Never invent generic placeholders. Resolve via `ctx.cards()` (= `AK.getCards()`).
- **Theme:** gritty gold cyberpunk dog-gang street culture. **"crew" never "clan."**

---

## 1. THE REGISTRY -- `window.AK_SYSTEMS` + the module shape

`AK_SYSTEMS` is defined by the Lead in `game/systems/_registry.js` (loaded FIRST, before any
module). Modules call `AK_SYSTEMS.register(mod)` at load. The host calls the dispatch methods.

### 1.1 Registry API (host-owned, do not modify)
```js
window.AK_SYSTEMS = (function () {
  var list = [], byId = {};
  function warn(id, e){ try{ console.warn('[AK_SYSTEMS]', id, e); }catch(_){} }
  return {
    // module self-registration (load-time). Dupe id or bad shape = ignored.
    register: function (m) {
      if (!m || typeof m !== 'object' || !m.id || byId[m.id]) return false;
      byId[m.id] = m; list.push(m); return true;
    },
    get:  function (id) { return byId[id] || null; },
    all:  function () { return list.slice(); },
    // ---- host dispatch (called by the hub only) ----
    initAll: function (ctx) { list.forEach(function (m) { try { m.init && m.init(ctx); } catch (e) { warn(m.id, e); } }); },
    enterBuilding: function (b, ctx) {            // first module to claim wins
      for (var i = 0; i < list.length; i++) { try { if (list[i].onEnterBuilding && list[i].onEnterBuilding(b, ctx) === true) return true; } catch (e) { warn(list[i].id, e); } }
      return false;
    },
    tickAll: function (dt, ctx) { for (var i = 0; i < list.length; i++) { try { list[i].onTick && list[i].onTick(dt, ctx); } catch (e) { warn(list[i].id, e); } } },
    drawAll: function (ctx)     { for (var i = 0; i < list.length; i++) { try { list[i].onDrawWorld && list[i].onDrawWorld(ctx); } catch (e) { warn(list[i].id, e); } } }
  };
})();
```

### 1.2 The standard module shape (what each wave SHIPS)
```js
AK_SYSTEMS.register({
  id: 'production',                       // REQUIRED. unique. MUST equal the filename stem.
  init:           function (ctx) {},      // OPTIONAL
  onEnterBuilding:function (b, ctx) { return false; }, // OPTIONAL -> return true to OWN the interior
  onTick:         function (dt, ctx) {},  // OPTIONAL
  onDrawWorld:    function (ctx) {}        // OPTIONAL
});
```

### 1.3 Exact signatures + WHEN each fires

| Hook | Signature | Fires | Contract |
|------|-----------|-------|----------|
| `init` | `init(ctx)` | **Once**, by `AK_SYSTEMS.initAll(ctx)`, after the DOM is ready, `AK_ECON` is present, and **all** modules are registered. Order = registration order = `<script>` load order. | Read profile, seed roamers, cache refs. **No per-frame work.** Idempotent (may be skipped on `game.html`). |
| `onEnterBuilding` | `onEnterBuilding(b, ctx) -> boolean` | **Synchronously** inside the hub's `enterInterior(b)`, BEFORE the default keeper card renders. | Return `true` ONLY for a building id you OWN (Section 4 table). On `true`: you MUST have already called `ctx.ui.keeperCard(...)` to render the interior; the host shows the panel + stops (no default keeper, no `'soon'`). Return `false`/`undefined` to pass. **Must be fast + synchronous.** |
| `onTick` | `onTick(dt, ctx)` | **Once per rAF** in the hub `loop()`, ONLY when `state==='IN_ZONE' && !interiorOpen && !entering`. `dt` = seconds, pre-clamped to `<= 0.05`. | Move/age your state. Roamers registered via `ctx.world.addRoamer` are updated by the host automatically -- use `onTick` only for module-global logic (clocks, spawn cadence, night cycle). Freezes during interiors / transitions / overlays. |
| `onDrawWorld` | `onDrawWorld(ctx)` | **Once per rAF** in the hub `draw()`, in **WORLD space**, AFTER props + buildings, BEFORE the player avatar + FX vignette. | Draw with `ctx.world.g` using `ctx.world.wx/wy`. **Cull off-screen.** **Always `save()`/`restore()`** -- never leave canvas state dirty. Roamers draw automatically; use this for indicators/overlays only. |

> The battler (`game.html`) loads `_registry.js` + `modes.js` only, and **never calls
> `initAll`/`tickAll`/`drawAll`** -- so `onEnterBuilding/onTick/onDrawWorld` are hub-only. The
> `modes` wave's engine-facing half lives in `window.AK_MODES` (Section 3.8), which DOES run on
> `game.html`. Design `modes.js` to be safe in both pages (Section 3.8).

---

## 2. THE `ctx` OBJECT (built ONCE by the hub; same ref to `init` + every hook)

The host builds `ctx` once and stores it as `window.AK_CTX`. Live fields (`me`, `cam`,
`activeZone`) are exposed as getters or live references so reads are always current.

> Naming note: inside `index.html` the canvas 2D context is the existing `const ctx`. To avoid
> collision, the **module context is `AK_CTX`** (your hook parameter is named `ctx`), and the raw
> canvas 2D context is reached via **`ctx.world.g`**. Never assume a bare `ctx` is a canvas.

```js
window.AK_CTX = {
  // ---------- engine + economy handles ----------
  AK_ECON: window.AK_ECON,          // the atomic state kernel (alias: ctx.econ)
  econ:    window.AK_ECON,
  AK:      window.AK,               // engine handle (getCards, STARTER_DECK_NAMES, newMatch ...)
  cards:   function(){ return (window.AK && AK.getCards && AK.getCards()) || {}; }, // name -> card def (106)

  // ---------- live world reads (REQUIRED by spec) ----------
  ZONES:   ZONES,                   // the full 9-grid zone table
  get activeZone(){ return activeZone; },   // live -- reassigned on zone change
  get zoneId(){ return activeZone.id; },
  me:      me,                      // live player {x,y,r,...} (mutated in place)
  cam:     cam,                     // live camera {x,y} (mutated in place)

  // ---------- banner ----------
  showBanner: function(text, secs){ showBanner(text, secs); },  // secs default 1.6

  // ---------- (a) own a building interior ----------
  ui: { keeperCard: function(opts){ /* Section 2.a */ } },

  // ---------- (b) world roamer entities ----------
  world: { /* g, cam, W/H, WORLD_W/H, wx, wy, addRoamer, removeRoamer, roamers, distToMe -- Section 2.b */ },

  // ---------- (c) launch the battler with a mode ----------
  battle: { launch: function(o){ /* Section 2.c */ } },

  // ---------- (d) soft currency ----------
  currency: { get: function(kind, rarity){}, grant: function(kind, amount, rarity){} }, // Section 2.d

  // ---------- (e) full-screen Canvas2D overlay (mini-game / light mode) ----------
  overlay: { open: function(spec){ /* returns api -> Section 2.e */ } }
};
```

### 2.a `ctx.ui.keeperCard(opts)` -- own a building's interior
Call this from inside your `onEnterBuilding` when you claim the building. It renders into the
existing `#interior` DOM (`#int-place / #int-glyph / #int-name / #int-line / #int-btns / #int-bg`)
and shows the panel. The host wires `interiorOpen/interiorB` after you return `true`. A `LEAVE`
button (wired to the host `exitInterior()`) is appended automatically.
```js
ctx.ui.keeperCard({
  place:       'GEM MINE',                 // header line (defaults to b.label)
  glyph:       '⛏️',             // emoji keeper glyph
  name:        'Prospector Pip',           // keeper name (reuse KEEPERS where one exists)
  line:        'Rich veins today, partner. Haul ready.',
  interiorArt: 'assets/interiors/gem_mine.png', // optional bg; falls back to a gradient
  buttons: [                               // 0..3 action buttons (primary=gold, else=ghost)
    { label: 'COLLECT 240 GOLD', primary: true, disabled: false,
      onClick: function(ctx){ /* do work; re-call keeperCard to refresh */ } },
    { label: 'UPGRADE (500 g)',  primary: false, onClick: function(ctx){} }
  ]
});
```
- Re-call `keeperCard` any time to re-render (e.g. after a collect).
- `onClick(ctx)` receives the module ctx. To close, call nothing (LEAVE) or do your action then
  re-render. The host owns close (`exitInterior` repositions the player off the door).

### 2.b `ctx.world.*` -- world roamer entities (Pokemon symbol-encounter pattern)
```js
ctx.world.g            // the hub canvas 2D context (draw here in onDrawWorld / roamer.draw)
ctx.world.cam          // live cam {x,y}
ctx.world.W, ctx.world.H               // screen px
ctx.world.WORLD_W, ctx.world.WORLD_H   // active-zone bounds (ZW=1700, ZH=1300)
ctx.world.wx(x), ctx.world.wy(y)       // world -> screen
ctx.world.distToMe(x, y)               // px distance player -> world point
ctx.world.addRoamer(spec) -> handle    // register a roamer (host updates + draws it)
ctx.world.removeRoamer(handle)
ctx.world.roamers() -> array

// roamer spec:
{ id:'stray_rosco_1', zone:'HOME_TURF',   // host updates/draws ONLY when zone===activeZone.id (omit = all zones)
  x:900, y:700, r:18,
  update:function(dt, self, ctx){ /* move self.x/self.y; check ctx.world.distToMe */ },
  draw:  function(g, self, ctx){ /* g is the canvas ctx; self auto-culled off-screen */ } }
```
The host auto-updates roamers in `loop()` (under the same `IN_ZONE && !interiorOpen` gate as
`onTick`) and auto-draws them in `draw()` (culled), so a simple roamer needs no `onTick`/
`onDrawWorld` of its own.

### 2.c `ctx.battle.launch(o)` -- launch the battler with a mode (NEVER fork it)
Writes a handoff blob + navigates to `game.html` (which reads it and calls `AK.newMatch(deck,{mode})`).
The hub round-trip preserves your zone + spot (`doEnter` sets `ak_returning`).
```js
ctx.battle.launch({
  mode:      'survival',          // -> AK.newMatch opts.mode (Section 3.8 / 6.C). omit/'convoy' = default run
  deck:      ['$BCARDD', ...],    // optional deck-name array; omit = player's active deck
  city: 3, level: 7, diffOffset: 0,        // optional world difficulty passthrough
  nemesis:   { card:'0002', name:'Jagged', tier:2 }, // optional fielded rival (engine AK-NEMESIS)
  handler:   'handler_mender',    // optional commander override
  label:     'SURVIVAL'           // banner text during the fade
});
```

### 2.d `ctx.currency.*` -- read / grant soft currency (gems are SERVER-ONLY)
```js
ctx.currency.get('gold')                  // -> p.coins
ctx.currency.get('scrap','Epic')          // -> p.scrap.Epic
ctx.currency.get('keys'|'fragments'|'sp'|'bones')
ctx.currency.grant('gold', 240)           // p.coins += 240  (returns the saved profile)
ctx.currency.grant('scrap', 4, 'Rare')    // -> AK_ECON.addScrap('Rare',4)
ctx.currency.grant('keys', 1)             // -> AK_ECON.addKeys
ctx.currency.grant('fragments', 5)        // -> AK_ECON.addFragments (auto-forges keys 10->1)
ctx.currency.grant('sp', 2) | grant('bones', 10)
ctx.currency.grant('gems', ...)           // HARD NO-OP -> returns null. gems are server-only.
```
Implemented over `AK_ECON.mutateProfile / addScrap / addKeys / addFragments`. One atomic write each.
Never write `gems`, `$BCARDD`, or `ALK`.

### 2.e `ctx.overlay.open(spec)` -- full-screen Canvas2D overlay (mini-game / light mode)
A fresh fullscreen canvas at `z-index:40` (above `#interior`=12, below `#loadscreen`=50). The host
freezes the hub (sets `state='TRANSITIONING'`) so movement/ticks/roamers pause underneath, runs a
private rAF, routes pointer events, and restores the hub on close.
```js
var api = ctx.overlay.open({
  id: 'arcade_dash',
  onFrame:  function(g, dt, vp, api){ /* g=2D ctx; vp={w,h,dpr}; draw your frame */ },
  onPointer:function(evt, api){ /* pointerdown|move|up */ },
  onClose:  function(result){ /* teardown / grant rewards via ctx.currency */ }
});
// api: { g, vp:{w,h,dpr}, close(result) }   -- call api.close(result) to exit (restores the hub)
```
Reuses Canvas2D only. Does NOT touch the battler. Use for arcade games, capture mini-games, trade
UIs, raid target pickers -- anything that is not a full lane battle.

---

## 3. THE 8 WAVES (key, responsibility, hooks, fields, server)

> **Ownership is disjoint by design.** Each wave owns exactly the entry points below. No two
> modules claim the same building id or the same profile field. Cards/handlers are referenced
> BY NAME from `ctx.cards()` -- never re-stat, never placeholder.

### 3.1 `production` -- offline-accrual producer buildings (Clash builder huts / Sunflower gather)
- **Responsibility:** the 5 producer buildings accrue soft currency offline; keeper lets you
  collect + upgrade. Visible per-building level (the hub already draws `LV[...]`).
- **Owns interiors (onEnterBuilding):** `GEM` (gems? NO -> produces **gold/keys** as a gem-mine
  flavored gold node), `MINT` (gold), `FORGE` (scrap), `LAB` (sp), `GEN` (keys/fragments). Map each
  to its existing `KEEPERS` entry (Prospector Pip / Banker Bones / Sparks / Doc Wattson / Volt).
  **Gems are never produced** (server-only).
- **Hooks:** `onEnterBuilding` (the 5 ids) + `onDrawWorld` (a "ready to collect" pip over a
  building when `stored>0`). `init` to backfill timestamps.
- **Falsy fields:** `prod: {}` -- `{ "<BUILDINGID>": { lvl, lastCollect, stored } }`.
- **Server:** **NONE** (gold/scrap/sp/keys are already 100% client-side in `economy.js`; accrual is
  deterministic from `lastCollect` + level). Future: optional `ak-production`.

### 3.2 `missions` -- daily/weekly + story mission chains (Monopoly GO goal-gradient)
- **Responsibility:** keeper-given mission list with claim buttons; goal-gradient nudges.
- **Owns interior:** `FIXER` ("THE FIXER" / Hit List, in THE_YARDS). Keeper card lists active
  missions + `CLAIM` buttons.
- **Hooks:** `onEnterBuilding` (`FIXER`). Light/none `onTick`.
- **Falsy fields:** `missions: {}` -- local cache only.
- **Server:** **REUSE `ak-quests`** (the LIVE edge fn). Read/claim via `window.AKQuests` and report
  progress via `AKQuests.reportEvent(name, n)` (already wired in `social.js`). Add NO new edge fn
  for v1.

### 3.3 `encounters` -- wild dog-breed roamers (Pokemon symbol encounters)
- **Responsibility:** visible wild dogs (cards BY NAME) wander zones; walk into one -> capture
  mini-game or a battle. Avoidable (symbol-encounter, not random).
- **Owns interior:** NONE. Pure roamers + overlay.
- **Hooks:** `onTick` (spawn cadence + despawn), roamers via `ctx.world.addRoamer` (move + proximity
  -> `ctx.overlay.open` capture mini-game OR `ctx.battle.launch({mode:'encounter', nemesis:<card>})`),
  `onDrawWorld` (a "!" alert when the player is detected).
- **Falsy fields:** `captures: {}` (`cardName -> count`), `encSeed: 0` (deterministic spawn cursor).
- **Server:** **NONE** v1 (capture chance client-rolled below an HP threshold; grants a card copy
  via `AK_ECON.addCopy`). Wild units = real cards (weight toward Common/Rare; Mythics never roam).

### 3.4 `raid` -- async base raids + night defense (Clash raid / Whiteout night / Boom Beach bots)
- **Responsibility:** raid bot bases (snapshot-as-bot, decks BY NAME); night-defense alert when
  strays attack; shield + 24h revenge window.
- **Owns interior:** NONE. Entry via a roamer ("rival crew scout" that drives through your zone)
  -> tap -> `ctx.overlay.open` raid-target picker. Night alerts via `ctx.showBanner` + an overlay.
- **Hooks:** `onTick` (day/night clock + scout spawn cadence + shield/revenge expiry),
  `onDrawWorld` (night tint pip / scout), roamer for the scout.
- **Falsy fields:** `raid: { shieldUntil:0, lastRaid:0, revenge:[] }`.
- **Server:** **NEW edge fn `ak-raid`** -- server-authoritative: serve a bot-base snapshot, resolve
  raid outcome, deliver loot via the **`ak_grants` server-authoritative grant pattern** (same as
  `ak-crew` grants in `social.js`). Soft-currency loot only.

### 3.5 `seasons` -- live-ops chapters + season track + leaderboard (Monopoly GO event cadence)
- **Responsibility:** 6-week chapters, Marks currency (cosmetic-only), seasonal leaderboard
  (crew-vs-crew), claim track.
- **Owns interior:** `TROPHY` ("TROPHY HALL", HOME_TURF). Keeper card = season track + Marks + claim
  + leaderboard view.
- **Hooks:** `onEnterBuilding` (`TROPHY`). `init` to roll the active chapter id.
- **Falsy fields:** `season: { id:'', marks:0, claimed:[] }`. **Marks are cosmetic-only**
  (parity-safe; never buy power).
- **Server:** **REUSE `ak-pass`** for the season reward track/tiers. Optional **NEW `ak-season`**
  for the crew leaderboard only. No power sold.

### 3.6 `trading` -- player barter post (Sunflower Land trade; keeper "Switch the Broker")
- **Responsibility:** soft-currency + **card-copy** + cosmetic barter between players. **NEVER
  `$BCARDD`/`ALK`.** Dupe-proof.
- **Owns interior:** NONE. Entry via a walking broker roamer ("Switch the Broker," OL'SCRAPS NPC
  pattern) -> `ctx.overlay.open` trade UI. Stock = real card names from `ctx.cards()`.
- **Hooks:** roamer + `onTick` (broker walk path + offer cooldown).
- **Falsy fields:** `trades: { sent:[], cooldownUntil:0 }`.
- **Server:** **NEW edge fn `ak-trade`** -- **server-authoritative escrow** (validate both sides,
  prevent dupes, deliver via the `ak_grants` pattern). Card copies + soft currency + cosmetics
  ONLY. Server hard-rejects any `$BCARDD`/`ALK` line.

### 3.7 `arcade` -- bite-size Canvas2D mini-games (Monopoly-GO variable-reward side loop)
- **Responsibility:** a menu of quick mini-games (dog-themed); soft-currency payouts with
  per-day anti-farm caps (mirror `LOOT_TABLE` cap philosophy).
- **Owns interior:** `ARCADE` ("THE ARCADE", THE_STRIP). Keeper card lists games -> each launches
  `ctx.overlay.open`.
- **Hooks:** `onEnterBuilding` (`ARCADE`).
- **Falsy fields:** `arcade: {}` (`gameId -> { best, plays, lastReward }`).
- **Server:** **NONE** v1 (local best scores; capped soft-currency rewards via `ctx.currency`).
  Future: optional `ak-arcade` leaderboard.

### 3.8 `modes` -- alternate battler win-conditions (reuse `newMatch`; the ML/Brawl mode matrix)
- **Responsibility:** define alternate battler modes (e.g. `survival`, `gulag` 1v1, `street`,
  `worldrt`) as **win-condition overlays on the EXISTING engine** -- never a new combat loop.
- **Owns interior:** `STREET` ("THE STREET", THE_STRIP). Keeper card = mode picker -> each calls
  `ctx.battle.launch({ mode })`.
- **Hooks (hub half):** `onEnterBuilding` (`STREET`).
- **Engine half (runs on `game.html`):** populate **`window.AK_MODES`** -- this is what the engine
  seam reads (Section 6.C). One entry per mode:
  ```js
  window.AK_MODES = window.AK_MODES || {};
  window.AK_MODES.survival = {
    setup:   function(game){ /* once, after newMatch builds game. Set counters on game.* */ },
    checkEnd:function(game, dt){ /* return {result:'win'|'lose'|'draw', stars?, cleanSweep?} or null */ },
    hud:     function(game){ return 'WAVE 3/10'; }   // optional HUD string
  };
  ```
  `setup`/`checkEnd` use ONLY existing engine state (`game.units`, `game.time`, `game.player/
  opponent.crowns/towers`, `game.stats`). Set `game.stars`/`game.cleanSweep` so the EXISTING reward
  + chest path (`AK_ECON.rollChestTier` reads `g.cleanSweep/g.stars/g.time`) pays out -- add NO new
  reward primitive.
- **Falsy fields:** `modes: {}` (`modeId -> { wins, losses, best }`).
- **Server:** **NONE** (modes are battler variants; rewards ride the live `grantMatchRewards`/chest
  path).
- **`modes.js` must be safe on BOTH pages:** wrap the hub-side `AK_SYSTEMS.register({...})` in
  `if (window.AK_SYSTEMS) {...}`, but register `window.AK_MODES` entries **unconditionally** (so
  they exist when `game.html` runs the engine, where `initAll` is never called).

### 3.9 Wave summary table
| Key | Owns interior | Roamer/Overlay | Falsy field(s) | Server |
|-----|---------------|----------------|----------------|--------|
| `production` | GEM, MINT, FORGE, LAB, GEN | -- | `prod:{}` | none |
| `missions` | FIXER | -- | `missions:{}` | reuse `ak-quests` |
| `encounters` | -- | roamers + overlay | `captures:{}`, `encSeed:0` | none v1 |
| `raid` | -- | roamer + overlay | `raid:{shieldUntil,lastRaid,revenge}` | NEW `ak-raid` (`ak_grants`) |
| `seasons` | TROPHY | -- | `season:{id,marks,claimed}` | reuse `ak-pass` (+opt `ak-season`) |
| `trading` | -- | broker roamer + overlay | `trades:{sent,cooldownUntil}` | NEW `ak-trade` (escrow) |
| `arcade` | ARCADE | overlay | `arcade:{}` | none v1 |
| `modes` | STREET | `ctx.battle.launch` | `modes:{}` + `window.AK_MODES` | none |

Shared sink added once: **`bones: 0`** (soulbound skill currency; production/missions/raid may grant
it, skill trees spend it).

---

## 4. BUILDING-OWNERSHIP MAP (canon -- prevents logical collisions)

The hub's zones/buildings live in `index.html` (a shared, frozen file). Modules CANNOT add
buildings; they CLAIM existing ones via `onEnterBuilding`. Each claimable building is owned by
exactly one wave:

| Zone | Building id | Current url | Owner wave | Notes |
|------|-------------|-------------|-----------|-------|
| HOME_TURF | `ARENA` | `game.html` | (host) | Main game. Untouched. |
| HOME_TURF | `TROPHY` | `soon` | **seasons** | season track + leaderboard |
| HOME_TURF | `KENNEL` | `shop#handlers` | (shop) | handlers. Untouched. |
| DOWNTOWN | `DROP`, `GARAGE` | `shop` | (shop) | Untouched. |
| NEON_HEIGHTS | `WARD`, `ARCH` | `shop` | (shop) | Untouched. |
| THE_YARDS | `CLAN` | `shop#crew2` | (social) | crews/chat. Untouched. |
| THE_YARDS | `PASS` | `shop#pass2` | (shop) | Alley Pass. Untouched. |
| THE_YARDS | `FIXER` | `shop#hit2` | **missions** | Hit List |
| FACTORY_ROW | `GEM`, `MINT`, `FORGE` | `soon` | **production** | gold / gold / scrap |
| THE_STRIP | `STREET` | `shop#street` | **modes** | mode picker |
| THE_STRIP | `ARCADE` | `soon` | **arcade** | mini-games |
| THE_DOCKS | `LAB`, `GEN` | `soon` | **production** | sp / keys |

`encounters`, `raid`, `trading` use roamers + overlays (no building) -- zero contention. A module
MUST return `false` from `onEnterBuilding` for any building it does not own.

---

## 5. MODULE SKELETON (copy this to start `game/systems/<id>.js`)
```js
/* game/systems/<id>.js -- AK_SYSTEMS module. Headless-safe, additive, no shared-file edits. */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;          // hub-only modules bail on pages without the registry

  function profile(ctx){ return ctx.econ ? ctx.econ.loadProfile() : null; }

  global.AK_SYSTEMS.register({
    id: '<id>',                            // MUST equal the filename stem
    init: function (ctx) { /* read profile, seed roamers; no per-frame work */ },
    onEnterBuilding: function (b, ctx) {
      if (b.id !== '<MY_BUILDING_ID>') return false;   // claim ONLY what Section 4 assigns
      ctx.ui.keeperCard({ place: b.label, glyph: '🐕', name: '...', line: '...',
        buttons: [ { label: '...', onClick: function (c) { /* c.currency.grant(...) ; re-render */ } } ] });
      return true;                          // host shows the panel + suppresses the default keeper
    },
    onTick: function (dt, ctx) { /* clocks / spawn cadence */ },
    onDrawWorld: function (ctx) { var g = ctx.world.g; /* cull + save/restore */ }
  });
})(typeof window !== 'undefined' ? window : globalThis);
```

---

## 6. THE BOOTSTRAP (shared-file edits -- LEAD-OWNED, landed ONCE, before any wave starts)

These are the ONLY edits to shared files. After this commit, **waves touch none of them.** Each is
listed exactly once.

### 6.A `game/index.html` (the hub) -- 5 edits
**(A1) Load the registry + the 8 modules** -- immediately after line 73 `<script src="economy.js"></script>`:
```html
<script src="systems/_registry.js"></script>
<script src="systems/production.js"></script>
<script src="systems/missions.js"></script>
<script src="systems/encounters.js"></script>
<script src="systems/raid.js"></script>
<script src="systems/seasons.js"></script>
<script src="systems/trading.js"></script>
<script src="systems/arcade.js"></script>
<script src="systems/modes.js"></script>
```
(`_registry.js` first so each module self-registers on load.)

**(A2) Build `AK_CTX` once + `initAll`** -- just before line 385 `requestAnimationFrame(loop);`, paste
the full `window.AK_CTX = {...}` from Section 2 (with the helper bodies below), then:
```js
window.AK_CTX._roamers = [];
function akTickSystems(dt){ if(!window.AK_SYSTEMS)return; AK_SYSTEMS.tickAll(dt, AK_CTX);
  var rs=AK_CTX._roamers; for(var i=0;i<rs.length;i++){ var r=rs[i]; if(r.zone && r.zone!==activeZone.id) continue; try{ r.update&&r.update(dt,r,AK_CTX);}catch(_e){} } }
function akDrawSystems(){ if(!window.AK_SYSTEMS)return; var rs=AK_CTX._roamers;
  for(var i=0;i<rs.length;i++){ var r=rs[i]; if(r.zone&&r.zone!==activeZone.id)continue; var X=r.x-cam.x,Y=r.y-cam.y; if(X<-60||X>W+60||Y<-60||Y>H+60)continue; try{ r.draw&&r.draw(ctx,r,AK_CTX);}catch(_e){} }
  AK_SYSTEMS.drawAll(AK_CTX); }
try{ if(window.AK_SYSTEMS) AK_SYSTEMS.initAll(AK_CTX); }catch(_e){}
```
Helper bodies for `AK_CTX` (all close over the hub's existing `me/cam/W/H/WORLD_W/WORLD_H/
activeZone/ZONES/showBanner/doEnter/exitInterior/ctx`):
```js
// (a) ui.keeperCard
ui:{ keeperCard:function(o){ o=o||{}; var $=function(id){return document.getElementById(id);};
  $('int-place').textContent=o.place||(interiorB&&interiorB.label)||'BUILDING';
  $('int-glyph').textContent=o.glyph||'🐕'; $('int-name').textContent=o.name||'The Keeper';
  $('int-line').textContent=o.line||''; var bg=$('int-bg');
  if(o.interiorArt){ bg.style.backgroundImage="url('"+o.interiorArt+"')"; } else { bg.style.backgroundImage=''; bg.style.background='radial-gradient(circle at 50% 35%, #1a1510, #08080c)'; }
  var btns=$('int-btns'); btns.replaceChildren();
  (o.buttons||[]).forEach(function(b){ var el=document.createElement('button'); el.textContent=b.label;
    el.style.cssText=(b.primary!==false)?'flex:2;background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:none;border-radius:10px;padding:13px 0;font-weight:900;font-size:14px;letter-spacing:.03em;':'flex:1;background:none;border:1px solid rgba(201,168,76,.45);color:#b9a76a;border-radius:10px;padding:13px 0;font-weight:700;font-size:12px;';
    if(b.disabled){ el.disabled=true; el.style.filter='grayscale(.65)'; el.style.opacity='.55'; } else el.onclick=function(){ try{ b.onClick&&b.onClick(AK_CTX); }catch(_e){} };
    btns.appendChild(el); });
  var lv=document.createElement('button'); lv.textContent='LEAVE'; lv.style.cssText='flex:1;background:none;border:1px solid rgba(201,168,76,.45);color:#b9a76a;border-radius:10px;padding:13px 0;font-weight:700;font-size:12px;'; lv.onclick=function(){ exitInterior(); }; btns.appendChild(lv);
  document.getElementById('interior').style.display='flex'; } },
// (b) world
world:{ get g(){return ctx;}, get cam(){return cam;}, get W(){return W;}, get H(){return H;},
  get WORLD_W(){return WORLD_W;}, get WORLD_H(){return WORLD_H;},
  wx:function(x){return x-cam.x;}, wy:function(y){return y-cam.y;},
  distToMe:function(x,y){return Math.hypot(me.x-x,me.y-y);},
  addRoamer:function(s){ s=s||{}; AK_CTX._roamers.push(s); return s; },
  removeRoamer:function(h){ var i=AK_CTX._roamers.indexOf(h); if(i>=0)AK_CTX._roamers.splice(i,1); },
  roamers:function(){ return AK_CTX._roamers; } },
// (c) battle.launch
battle:{ launch:function(o){ o=o||{}; try{ localStorage.setItem('ak_match_intent', JSON.stringify({
    mode:o.mode||'convoy', deck:o.deck||null, city:o.city, level:o.level, diffOffset:o.diffOffset,
    nemesis:o.nemesis||null, handler:o.handler||null, returnZone:activeZone.id })); }catch(_e){}
  doEnter('game.html?intent=1', o.label||(o.mode?(String(o.mode).toUpperCase()+' MATCH'):'BATTLE')); } },
// (d) currency
currency:{ get:function(kind,rar){ var e=AK_CTX.econ; if(!e)return 0; var p=e.loadProfile(); switch(kind){
    case 'gold': case 'coins': return p.coins|0; case 'scrap': return (p.scrap&&p.scrap[rar]|0)||0;
    case 'keys': return p.keys|0; case 'fragments': return p.fragments|0; case 'sp': return p.sp|0; case 'bones': return p.bones|0; default: return 0; } },
  grant:function(kind,amt,rar){ var e=AK_CTX.econ; if(!e)return null; amt=amt|0; if(kind==='gems')return null;
    if(kind==='scrap')return e.addScrap(rar,amt); if(kind==='keys')return e.addKeys(amt); if(kind==='fragments')return e.addFragments(amt);
    return e.mutateProfile(function(p){ if(kind==='gold'||kind==='coins')p.coins=Math.max(0,(p.coins|0)+amt); else if(kind==='sp')p.sp=Math.max(0,(p.sp|0)+amt); else if(kind==='bones')p.bones=Math.max(0,(p.bones|0)+amt); }); } },
// (e) overlay.open
overlay:{ open:function(spec){ spec=spec||{}; var ov=document.createElement('canvas'); ov.id='ak-ov';
  ov.style.cssText='position:fixed;inset:0;z-index:40;background:#06060a;touch-action:none;'; var g=ov.getContext('2d');
  var dpr=Math.min(2,window.devicePixelRatio||1); function fit(){ ov.width=innerWidth*dpr; ov.height=innerHeight*dpr; g.setTransform(dpr,0,0,dpr,0,0);} fit(); addEventListener('resize',fit); document.body.appendChild(ov);
  var prev=state; state='TRANSITIONING'; var raf=0,last=performance.now(),alive=true;
  var api={ g:g, vp:{ get w(){return innerWidth;}, get h(){return innerHeight;}, dpr:dpr },
    close:function(res){ if(!alive)return; alive=false; cancelAnimationFrame(raf); removeEventListener('resize',fit); try{ov.remove();}catch(_e){} state=prev; spawnGrace=0.5; try{ spec.onClose&&spec.onClose(res);}catch(_e){} } };
  function frame(now){ if(!alive)return; var dt=Math.min(.05,(now-last)/1000); last=now; try{ spec.onFrame&&spec.onFrame(g,dt,api.vp,api);}catch(_e){} raf=requestAnimationFrame(frame);} 
  if(spec.onPointer)['pointerdown','pointermove','pointerup'].forEach(function(t){ ov.addEventListener(t,function(e){ try{spec.onPointer(e,api);}catch(_e){}}); });
  raf=requestAnimationFrame(frame); return api; } }
```

**(A3) `enterInterior(b)` claim seam** -- at the top of `enterInterior` (line 201), right after
`if(interiorOpen)return;`:
```js
if(window.AK_SYSTEMS && window.AK_CTX && AK_SYSTEMS.enterBuilding(b, AK_CTX)){ interiorOpen=true; interiorB=b; return; }
```

**(A4) `loop()` tick seam** -- inside `loop(now)` (line 236), immediately before `draw();` (line 269):
```js
if(state==='IN_ZONE' && !interiorOpen && !entering) akTickSystems(dt);
```

**(A5) `draw()` world seam** -- inside `draw()`, right before `const X=wx(me.x)` (line 308, i.e. after
the buildings/NPC/arrow block, before the player avatar):
```js
akDrawSystems();
```

### 6.B `game/economy.js` -- 1 edit (the consolidated falsy-default block)
Inside `ensureShape(p)`, immediately before `return p;` (line 91):
```js
// === AK_SYSTEMS consolidated falsy-default fields (8 waves; zero-state stays byte-identical) ===
if (typeof p.bones !== "number" || !isFinite(p.bones)) p.bones = 0;                 // shared soulbound skill currency
if (!p.prod     || typeof p.prod     !== "object") p.prod = {};                     // production:  buildingId -> {lvl,lastCollect,stored}
if (!p.missions || typeof p.missions !== "object") p.missions = {};                 // missions:    local cache (server = ak-quests)
if (!p.captures || typeof p.captures !== "object") p.captures = {};                 // encounters:  cardName -> capture count
if (typeof p.encSeed !== "number" || !isFinite(p.encSeed)) p.encSeed = 0;           // encounters:  deterministic spawn cursor
if (!p.raid     || typeof p.raid     !== "object") p.raid = { shieldUntil:0, lastRaid:0, revenge:[] };
if (!p.season   || typeof p.season   !== "object") p.season = { id:"", marks:0, claimed:[] }; // marks = cosmetic-only
if (!p.trades   || typeof p.trades   !== "object") p.trades = { sent:[], cooldownUntil:0 };
if (!p.arcade   || typeof p.arcade   !== "object") p.arcade = {};                   // arcade:      gameId -> {best,plays,lastReward}
if (!p.modes    || typeof p.modes    !== "object") p.modes = {};                    // modes:       modeId -> {wins,losses,best}
```
(All empty `{}` / `0` -> a fresh profile is shape-identical; no migration, no behavior change.)

### 6.C `game/engine.js` -- the mode win-check seam (3 micro-touches, NO new primitives)
**(C1)** In `newMatch` (line ~1397), replace `convoyMode: true,` with:
```js
mode:       (opts.mode || 'convoy'),
convoyMode: (opts.mode == null || opts.mode === 'convoy'),
modeImpl:   (global.AK_MODES && opts.mode && global.AK_MODES[opts.mode]) || null,
```
**(C2)** In `newMatch`, just after `computeAiCurve();` (line 1442):
```js
if(game.modeImpl && game.modeImpl.setup){ try{ game.modeImpl.setup(game); }catch(_e){} }
```
**(C3)** In `update(dt)`, immediately before `if(game.time<=0 && game.phase==='live') endMatch();`
(line 2659):
```js
if(game.modeImpl && game.modeImpl.checkEnd && game.phase==='live'){
  var _mr=game.modeImpl.checkEnd(game, dt);
  if(_mr){ if(_mr.result)game.result=_mr.result; if(typeof _mr.stars==='number')game.stars=_mr.stars; if(_mr.cleanSweep)game.cleanSweep=true; endMatch(); }
}
```
**(C4)** In `endMatch()` (line 3966), wrap the crown/tower result computation (lines 3969-3976) so a
mode-preset result is honored: change `if(game.player.crowns>...)` to run only `if(!game.result){ ...existing computation... }`.
> A `convoy` run is byte-identical (`opts.mode` absent -> `convoyMode:true`, `modeImpl:null`, the seam
> is a no-op). `AK_MODES` is populated by `systems/modes.js` on `game.html`.

### 6.D `game/game.html` (battler page) -- 2 edits (consume the launch intent + load mode impls)
**(D1)** Add to the script includes near line 2102 (the handler-roster comment block, BEFORE
`engine.js`):
```html
<script src="systems/_registry.js"></script>
<script src="systems/modes.js"></script>
```
(Only these two -- `modes.js` registers `window.AK_MODES` for the engine; the others are hub-only.)

**(D2)** In the match launcher, immediately before the `AK.newMatch(...)` call (line ~5040), read +
clear the intent and pass `mode` through:
```js
var _intent=null; try{ _intent=JSON.parse(localStorage.getItem('ak_match_intent')||'null'); localStorage.removeItem('ak_match_intent'); }catch(_e){}
```
then add to the `AK.newMatch(...)` opts object:
```js
mode: (_intent && _intent.mode) || undefined,
```
(and, if present, prefer `_intent.deck/city/level/diffOffset/nemesis/handler`). Absent intent ->
`mode:undefined` -> default convoy run, byte-identical to today.

---

## 7. INTEGRATION INVARIANTS (every wave must pass these)
1. **Headless-safe:** no top-level DOM/`localStorage` at module load; all storage via `AK_ECON`
   (which is already try/catch-wrapped). Loading your file in the node harness must not throw.
2. **Zero-state identity:** with a fresh profile, your fields default to `{}`/`0` and your module
   does nothing visible until the player acts.
3. **No shared-file edits.** If you think you need to edit `index.html`/`economy.js`/`engine.js`/
   `game.html`, you are wrong -- request a `ctx` helper from the Lead instead.
4. **Canvas hygiene:** every `onDrawWorld`/roamer `draw`/overlay `onFrame` is `save()`/`restore()`
   balanced and culls off-screen.
5. **Reuse by name:** units/bots/stock/targets/roamers are real cards from `ctx.cards()` and real
   handlers from `window.AK_HANDLERS`. No generic art, no invented characters.
6. **Crypto/parity:** soft-currency + cosmetic only; `grant('gems')` is a no-op; no `$BCARDD`/`ALK`
   anywhere in utility/trade/reward; gems (server-only) skip TIMERS only.
7. **Crew, never clan.** Gritty gold cyberpunk dog-gang voice in all keeper lines + copy.
8. **Server pattern:** new edge fns (`ak-raid`, `ak-trade`, optional `ak-season`) are
   server-authoritative and deliver through the `ak_grants` grant pattern (see `social.js`
   `applyGrant`/`claim-grants`). Reuse `ak-quests`/`ak-pass` where the table says so.

---

## 8. FILE MANIFEST (what lands where -- disjoint per wave)
```
specs/MODULE_CONTRACT.md                 (this file -- Lead)
game/systems/_registry.js                (Lead, bootstrap)
game/systems/production.js               (wave 1)
game/systems/missions.js                 (wave 2)   + reuse supabase/functions/ak-quests
game/systems/encounters.js               (wave 3)
game/systems/raid.js                     (wave 4)   + supabase/functions/ak-raid + migrations/<ts>_raid.sql
game/systems/seasons.js                  (wave 5)   + reuse ak-pass [+opt ak-season + migration]
game/systems/trading.js                  (wave 6)   + supabase/functions/ak-trade + migrations/<ts>_trade.sql
game/systems/arcade.js                   (wave 7)
game/systems/modes.js                    (wave 8)   (also loaded by game.html for window.AK_MODES)
-- shared files edited ONCE by the Lead (Section 6): index.html, economy.js, engine.js, game.html --
```
Eight waves, eight disjoint new files, one bootstrap commit. No two people edit the same file.
That is the whole contract.
