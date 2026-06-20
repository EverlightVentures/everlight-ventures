# ALLEY KINGZ -- `AK_SYSTEMS` WAVE INTEGRATION SPEC
**Role: Integrator + QA gate.** One bootstrap commit wires the 8 disjoint wave
modules into the live repo. Verbatim, minimal, real-anchor edits below.

Date: 2026-06-20 | Owner: Integrator (Hive) | Status: READY TO LAND
Grounds: `specs/MODULE_CONTRACT.md` + the LIVE repo (`game/index.html`,
`game/economy.js`, `game/engine.js`, `game/game.html`, `game/canon.js`,
`game/systems/*.js`). All 8 modules read end-to-end; anchors re-verified against
the CURRENT files (the contract's line numbers had drifted by a few lines).

---

## 0. QA SUMMARY (read this first)

**Parse gate:** all 8 modules pass `node --check`. node v20.19.4.

**Combined co-registration (headless harness, mock `AK_SYSTEMS` per Contract 1.1 +
mock `AK_ECON`):**
```
REGISTERED: production,missions,encounters,raid,seasons,trading,arcade,modes   (8/8, no dup-id reject, no load throw)
AK_MODES keys: survival,encounter,openWorldMoba,openGulag,routeEncounter
AK_ARCADE? true   AKSeasons? true   AKTrading? true   AKRaid? (set in init -> true after initAll)
ENTER GEM   -> owned by 'production'
ENTER FIXER -> owned by 'missions'
ENTER ARENA -> false  (correctly UNCLAIMED -> falls through to the host default keeper)
init + 5x(tick+draw) on a fresh profile: no module throws
roamers seeded: switch_the_broker (trading), + raid scout / encounter strays spawn on their cadence
```
**Ownership is disjoint and correct** -- no two modules claim the same building id;
every module returns `false` for buildings it does not own.

**Zero-state byte-identity: PASS** (with one read-only-hygiene note). `economy.js
loadProfile()` returns a **fresh `JSON.parse`** every call, then `ensureShape`. So
the only init-time profile touch (`missions.init` -> `ms(p)` normalizing
`p.missions` to `{active:null,done:[],offerIdx:0}`) mutates a **throwaway** object
and is **never `saveProfile`'d** -> the persisted profile is byte-identical until the
player acts. No fix required; see QA-7.

**The one true integration gap:** `ctx.battle.launch` navigates to
`game.html?intent=1`, but game.html's existing autostart only handles `?go=match`
(and routes through `playBtn`, which may open the World Map, not a direct match),
and `startMatch()` never forwards `mode` to `AK.newMatch`. Section 6.D fixes all
three. **Without 6.D, every overlay-vs-engine handoff (encounter street-fight, raid,
survival, gulag-COLLIDE) silently lands on the lobby instead of the match.**

---

## A. `game/index.html` -- THE HUB (5 edits, Lead-owned, land ONCE)

Confirmed current anchors: economy.js `:73`; `enterInterior` `:201`; `loop()` `:236`
with `draw();...requestAnimationFrame(loop);` on `:269`; `wx/wy` `:271`; `draw()`
`:272` with `const X=wx(me.x),Y=wy(me.y);` on `:308`; bottom `requestAnimationFrame(loop);`
`:385`. No pre-existing `AK_SYSTEMS`/`AK_CTX`/`systems/` reference in the file (zero
collision risk).

### A1 -- load the registry + the 8 modules (after `:73`)
Immediately AFTER line 73 `<script src="economy.js"></script>` (and, per QA-4,
ALSO add `canon.js` so `ctx.cards()` + `akCardArtRel` resolve the real 106 cards):
```html
<script src="canon.js"></script>                <!-- QA-4: gives window.CANON_CARDS + akCardArtRel; without it cards/art fall back to per-module embeds -->
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
`_registry.js` must load FIRST so each module self-registers on load.
**`game/systems/_registry.js` does not exist yet** -- the Lead must create it with the
exact `window.AK_SYSTEMS` IIFE from Contract 1.1 (the 8 modules all guard on
`if(!global.AK_SYSTEMS)return;`, so until it lands they are inert no-ops).

### A2 -- build `AK_CTX` once + `initAll` (before `:385`)
Immediately BEFORE line 385 `requestAnimationFrame(loop);`, paste the full
`window.AK_CTX = {...}` from Contract Section 2 with the helper bodies from Contract
6.A (the helpers close over the hub's existing `me/cam/W/H/WORLD_W/WORLD_H/activeZone/
ZONES/showBanner/doEnter/exitInterior/ctx/state/spawnGrace/interiorOpen/interiorB`,
all confirmed present), then append:
```js
window.AK_CTX._roamers = [];
function akTickSystems(dt){ if(!window.AK_SYSTEMS)return; AK_SYSTEMS.tickAll(dt, AK_CTX);
  var rs=AK_CTX._roamers; for(var i=0;i<rs.length;i++){ var r=rs[i]; if(r.zone && r.zone!==activeZone.id) continue; try{ r.update&&r.update(dt,r,AK_CTX);}catch(_e){} } }
function akDrawSystems(){ if(!window.AK_SYSTEMS)return; var rs=AK_CTX._roamers;
  for(var i=0;i<rs.length;i++){ var r=rs[i]; if(r.zone&&r.zone!==activeZone.id)continue; var X=r.x-cam.x,Y=r.y-cam.y; if(X<-60||X>W+60||Y<-60||Y>H+60)continue; try{ r.draw&&r.draw(ctx,r,AK_CTX);}catch(_e){} }
  AK_SYSTEMS.drawAll(AK_CTX); }
try{ if(window.AK_SYSTEMS) AK_SYSTEMS.initAll(AK_CTX); }catch(_e){}
```
- `addRoamer`/`removeRoamer`/`roamers` in the Contract-6.A `world` helper MUST push
  to **`AK_CTX._roamers`** (the same array the two functions above iterate). The
  Contract-6.A body already does this -- keep it verbatim.
- The `world` helper exposes `get g(){return ctx;}` -- this is the **canvas 2D
  context** (`const ctx` declared in the hub). Modules read it as `ctx.world.g`.
  Do not rename; `AK_CTX` is the module context, `ctx` stays the canvas.

### A3 -- `enterInterior(b)` claim seam (`:201`)
Line 201 is a single physical line:
`function enterInterior(b){ if(interiorOpen)return; interiorOpen=true; interiorB=b; var k=keeperFor(b);`
Split it so the claim seam runs BEFORE the default keeper:
```js
function enterInterior(b){ if(interiorOpen)return;
  if(window.AK_SYSTEMS && window.AK_CTX && AK_SYSTEMS.enterBuilding(b, AK_CTX)){ interiorOpen=true; interiorB=b; return; }
  interiorOpen=true; interiorB=b; var k=keeperFor(b);
```
A claiming module has already called `ctx.ui.keeperCard(...)` (which sets
`#interior` to `display:flex`) before returning `true`; the seam then sets the
flags and bails -- the host's default keeper + the `'soon'`/`url` branch are skipped.
`exitInterior()` (`:214`) already clears `interiorOpen` and lands the player off the
door, so module interiors close exactly like native ones.

### A4 -- `loop()` tick seam (before `:269`)
Inside `loop(now)`, immediately BEFORE line 269 `draw();drawFX(dt);drawRadar();requestAnimationFrame(loop);`:
```js
  if(state==='IN_ZONE' && !interiorOpen && !entering) akTickSystems(dt);
```
(`state`, `interiorOpen`, `entering` are all in scope -- confirmed `:200`/`:110`/`:200`.)

### A5 -- `draw()` world seam (before `:308`)
Inside `draw()`, immediately BEFORE line 308 `const X=wx(me.x),Y=wy(me.y);` (i.e.
after the ground/props/buildings/NPC/off-screen-arrow block, before the player
avatar): 
```js
  akDrawSystems();
```
The hub draws everything in **screen space** via explicit `wx()/wy()` math (no
canvas camera translate), so roamer/`onDrawWorld` draws using `ctx.world.wx/wy` land
correctly, and full-screen screen-space washes (raid night tint, seasons grade) are
correct as written.

---

## B. `game/economy.js` -- `ensureShape` consolidated falsy-default block (1 edit)

`ensureShape(p)` is at `:72`; its `return p;` is at `:91`. Insert the Contract-6.B
block immediately BEFORE `:91 return p;`. Verbatim:
```js
    // === AK_SYSTEMS consolidated falsy-default fields (8 waves; zero-state stays byte-identical) ===
    if (typeof p.bones !== "number" || !isFinite(p.bones)) p.bones = 0;                 // shared soulbound skill currency
    if (!p.prod     || typeof p.prod     !== "object") p.prod = {};                     // production: buildingId -> {lvl,lastCollect,stored}
    if (!p.missions || typeof p.missions !== "object") p.missions = {};                 // missions:   local cache (server = ak-quests)
    if (!p.captures || typeof p.captures !== "object") p.captures = {};                 // encounters: cardName -> capture count
    if (typeof p.encSeed !== "number" || !isFinite(p.encSeed)) p.encSeed = 0;           // encounters: deterministic spawn cursor
    if (!p.raid     || typeof p.raid     !== "object") p.raid = { shieldUntil:0, lastRaid:0, revenge:[] };
    if (!p.season   || typeof p.season   !== "object") p.season = { id:"", marks:0, claimed:[] }; // marks = cosmetic-only
    if (!p.trades   || typeof p.trades   !== "object") p.trades = { sent:[], cooldownUntil:0 };
    if (!p.arcade   || typeof p.arcade   !== "object") p.arcade = {};                   // arcade:     gameId -> {best,plays,lastReward}
    if (!p.modes    || typeof p.modes    !== "object") p.modes = {};                    // modes:      modeId -> {wins,losses,best}
```
**Field-usage audit vs. the modules (all 10 fields consumed exactly as declared, no
extras):** `prod{}` (production), `missions{}` (missions; lazily extends to
`{active,done,offerIdx}` -- all falsy), `captures{}`+`encSeed:0` (encounters),
`raid{shieldUntil,lastRaid,revenge}` (raid; lazily adds `defenseNight`/`lastDefenseAt`
-- both falsy-by-absence), `season{id,marks,claimed}` (seasons; lazily adds
`checkIn`/`winMarks` -- falsy-by-absence), `trades{sent,cooldownUntil}` (trading),
`arcade{}` (arcade; internal `_meta` daily ledger), `modes{}` (modes), `bones:0`
(shared sink granted by missions/raid/arcade/modes; spent by the handler Bones
trees). All empty `{}`/`0` -> a fresh profile is shape-identical, no migration.

The existing `p.townHall` (`:89`) is the meta-gate missions (`th_lv2`) and trading
(`MIN_TH`) read; `p.copies`/`p.owned` (`:87`/`:75`) are what trading + encounters
read/write via `addCopy`. All already present -- the block adds nothing that
collides.

---

## C. `game/engine.js` -- the mode win-check seam (4 micro-touches, NO new primitives)

`engine.js` is an IIFE closed over `global = window` (`:4605`), so `global.AK_MODES`
resolves. `newMatch` `:1373`; `convoyMode: true,` `:1397`; the in-`newMatch`
`computeAiCurve();` `:1442` (NOT the re-anchor at `:1741`); `update`'s
`if(game.time<=0 && game.phase==='live') endMatch();` `:2659`; `endMatch` `:3966`
with the crown/tiebreak block `:3969-:3976`.

### C1 -- in `newMatch` (`:1397`), replace `convoyMode: true,` with:
```js
    mode:       (opts.mode || 'convoy'),
    convoyMode: (opts.mode == null || opts.mode === 'convoy'),
    modeImpl:   (global.AK_MODES && opts.mode && global.AK_MODES[opts.mode]) || null,
```
`opts` is already normalized at `:1374` and `opts.nemesis` is already fielded via
`nemesisFromOpts`/`nemesisIntoDeck` (`:1382-1383`) -- modes/encounters/raid pass
`nemesis` and it already works.

### C2 -- in `newMatch`, immediately AFTER `:1442 computeAiCurve();` (the FIRST one):
```js
  if(game.modeImpl && game.modeImpl.setup){ try{ game.modeImpl.setup(game); }catch(_e){} }
```

### C3 -- in `update(dt)`, immediately BEFORE `:2659 if(game.time<=0 && game.phase==='live') endMatch();`:
```js
  if(game.modeImpl && game.modeImpl.checkEnd && game.phase==='live'){
    var _mr=game.modeImpl.checkEnd(game, dt);
    if(_mr){ if(_mr.result)game.result=_mr.result; if(typeof _mr.stars==='number')game.stars=_mr.stars; if(_mr.cleanSweep)game.cleanSweep=true; endMatch(); }
  }
```

### C4 -- in `endMatch()`, wrap the crown/tiebreak computation so a mode-preset result wins.
Change `:3969-:3976` so the whole block runs only when `game.result` is empty:
```js
  if(!game.result){
    if(game.player.crowns>game.opponent.crowns) game.result='win';
    else if(game.opponent.crowns>game.player.crowns) game.result='lose';
    else {
      const pct = ts=>{ let hp=0,mx=0; ts.forEach(t=>{ mx+=t.maxHp; if(!t.destroyed) hp+=t.hp; }); return mx? hp/mx : 0; };
      const ph=pct(game.player.towers), oh=pct(game.opponent.towers);
      game.result = ph>oh?'win':oh>ph?'lose':'draw';
    }
  }
```
`game.result` is `''` (falsy) for normal + convoy matches (set at `:1393`) -> recompute
as today. For mode-driven ends, C3 set it truthy -> honored. The existing convoy
guards (`:3960 if(game.convoyMode) return;` etc.) are untouched.

> **Byte-identity proof:** a normal call (`AK.newMatch(deck, {...no mode...})`) ->
> `opts.mode` undefined -> `convoyMode:true`, `modeImpl:null` -> C2/C3 are no-ops,
> C4 recomputes from crowns exactly as before. The LIVE game (game.html `:5040`)
> passes no `mode`, so it is unchanged.

---

## D. `game/game.html` -- THE BATTLER PAGE (3 edits) -- **THE INTEGRATION-CRITICAL WAVE**

Confirmed: includes block `:2097-:2113` (`canon.js` `:2097` ... `engine.js` `:2106`
... `lobby.js` `:2113`); the launcher is **`function startMatch(opts)`** with its
`AK.newMatch(...)` call at `:5040-:5045`; there is an EXISTING `?go=match` autostart
at `:5277` that merely `playBtn.click()`s (and `playBtn` may route to
`window.__akPlayWorld()` = the World Map, `:5271`).

### D1 -- load the registry + modes engine half (before `:2106 engine.js`)
Add immediately BEFORE line 2106 `<script src="engine.js?v=...">`:
```html
<script src="systems/_registry.js?v=1781486888"></script>
<script src="systems/modes.js?v=1781486888"></script>
```
Only these two. `modes.js` registers `window.AK_MODES` **unconditionally** (outside
its `if(global.AK_SYSTEMS)` guard), so the engine seam (C1) sees the win-condition
modes even though `initAll` never runs on game.html. (`_registry.js` here is inert --
`initAll/enterBuilding` are never called on the battler -- but harmless, and keeps
`modes.js`'s hub-half `register()` consistent.)

### D2a -- forward `mode` in `startMatch` (the ONE missing field)
In the `AK.newMatch(...)` opts object (`:5041-:5045`), add `mode` (the launcher
ALREADY forwards `nemesis`, `city`, `level`, `diffOffset`, `startSection`, `handler`
-- only `mode` is missing). Change the object to include:
```js
        mode: (opts && opts.mode) || undefined,
```
Absent `opts.mode` -> `undefined` -> engine convoy run, byte-identical to today.

### D2b -- consume the launch intent on boot (NEW block; THE FIX)
`ctx.battle.launch` (Contract 6.A `battle.launch`) writes `localStorage.ak_match_intent`
and navigates to `game.html?intent=1`. The existing `?go=match` block does NOT read
that intent and routes through `playBtn`. Add a dedicated, self-contained autostart
that reads the intent and calls `startMatch(...)` DIRECTLY. Place it right after the
`?go=match` block (`:5283`), mirroring its gate-wait pattern:
```js
  // AK-INTENT 2026-06-20: the walkable hub's ctx.battle.launch writes ak_match_intent
  // + navigates to ?intent=1. Read it, wait for the lobby + loading gate, then fire
  // startMatch() DIRECTLY with the intent's mode/world/nemesis (bypasses playBtn so a
  // mode launch never detours to the World Map). One-shot; clears the intent.
  try{
    var _akIntent=null; try{ _akIntent=JSON.parse(localStorage.getItem('ak_match_intent')||'null'); }catch(_e){ _akIntent=null; }
    if(_akIntent && (/[?&]intent=1/.test(location.search) || true)){
      try{ localStorage.removeItem('ak_match_intent'); }catch(_e){}
      var _iTries=0, _iIv=setInterval(function(){ _iTries++;
        var sp=document.getElementById('startscreen'), gate=document.getElementById('akpl');
        var gateGone=!gate || gate.classList.contains('hidden') || (gate.style && gate.style.display==='none');
        if((sp && gateGone) || _iTries>50){ clearInterval(_iIv);
          try{
            startMatch({ mode:_akIntent.mode, nemesis:_akIntent.nemesis||null,
              city:_akIntent.city, level:_akIntent.level, diffOffset:_akIntent.diffOffset,
              startSection:_akIntent.startSection, handler:_akIntent.handler });
          }catch(_e){}
        }
      }, 200);
    }
  }catch(_e){}
```
- Keep `ctx.battle.launch` targeting `game.html?intent=1` (Contract 6.A as written).
  The block triggers on the presence of `ak_match_intent` (the `||true` makes it
  robust if a future caller forgets the query param), so the hub round-trip
  (`ak_returning`/`ak_hub_pos` set by `doEnter`) still restores the hub spot on
  return -- unchanged.
- If `_akIntent.deck` is ever set, also pass it as the first `startMatch`/`newMatch`
  arg; today `battle.launch` callers omit `deck`, so `activeDeckNames()` (the
  player's real deck) is used -- correct.

> After D2: `mode:'encounter'/'survival'` run the `AK_MODES` win-conditions;
> `mode:'raid'` (no `AK_MODES.raid` yet) runs a plain non-convoy single-board match
> labeled RAID -- graceful, byte-safe (see QA-5).

---

## E. SERVER EDGE FUNCTIONS (deploy LATER -- every module degrades gracefully today)

Live fns present: `ak-chat, ak-cosmetics, ak-crew, ak-pass, ak-quests`. Live
migrations: social_layer, grants_donations, alley_pass, quests, cosmetics,
spend_gems_rpc. The `ak_grants` server-authoritative grant rail (claim via
`AKSocial.claimGrants`) is the delivery pattern all new fns must reuse.

### E1 -- `ak-quests` / `ak-pass` wiring (REUSE, no new fn)
- **missions** reads/claims the LIVE Hit List via `AKQuests`/`ak-quests` + pays out
  via `AKSocial.claimGrants` (`ak_grants`), and reports local-delivery progress via
  `AKQuests.reportEvent`. **Requires the hub to load `ak_account.js` + `quests.js` +
  `social.js`** for the in-place claim; ABSENT them (current hub state) it degrades
  to navigating to `shop/shop.html#hit2` (writes `ak_hub_zone/pos/returning` like
  `doEnter`). No new fn. (See QA-4 for the optional hub-script add.)
- **encounters** reports captures via `AKQuests.reportEvent('captures',1)` if present.
- **seasons** reuses `ak-pass` (track via `AKPass.open`) and `ak-crew {action:'list'}`
  (the leaderboard is REAL today, crews ranked by trophies). No new fn for v1.

### E2 -- `ak-raid` (NEW; raid wave) -- server-authoritative, `ak_grants` delivery
- Client calls are stubbed in `raid.js` `callAkRaid()` -> `'ak-raid'` (degrades to
  `{ok:false}` -> local mulberry32 bot bases, local gold shields, PvE auto-turrets).
- Actions: `targets` (serve `ak_bot_bases` snapshot list); `resolve` (apply surgical
  per-building damage, deliver soft-currency loot via `ak_grants`, revenge +50%);
  `buy-shield` (gem tiers ONLY -- Fortress Dome 80 / Panic 160 -- since gems are
  server-only); `reinforce` (validate crew + cooldown for night defense).
- NEW table `ak_bot_bases` (faction, tier, roster card-names, per-building levels,
  loot, deterministic seed; push a 24h `revenge` row into the victim's
  `raid.revenge` on an offline loss). NEW migration `<ts>_raid.sql` (RLS forced,
  anon read-only, writes via the fn only). **Server must hard-reject any
  `$BCARDD`/`ALK` loot line.**

### E3 -- `ak-trading` (NEW; trading wave) -- server-authoritative escrow, `ak_grants` delivery
- **Contract manifest names it `ak-trade`; the module calls `ak-trading`.** Pick ONE
  name and use it in BOTH the fn dir and `trading.js` `TRADE_FN` (`:32`). The full
  spec (table `ak_trade_listings`, migration, and actions `list/post/accept/cancel/
  mine/claim-grants`) is embedded verbatim at the bottom of `trading.js` (`:649-:713`)
  -- deploy that.
- Client deducts on deposit and the server only ever GRANTS (never trusts a client
  to mint); a failed call refunds client-side. Server `FORBID` re-enforces:
  `kind='gems'` OR `rarity='Mythic'` OR `card_id ~* '\$|bcardd|alk'`; `DAILY<=5`;
  `BAND` match. **Cross-wave: the escrow MUST consult `p.captures` to keep
  capture-origin copies non-tradeable** (encounters marked this `// TODO-SERVER`).

### E4 -- optional, NOT required for MVP
`ak-season` (dedicated season-scoped crew board; seasons falls back to `ak-crew`),
`ak-cosmetics {action:'season-unlock'}` (seasons records unlocks locally until then),
`ak-arcade` (leaderboard; arcade is local-best today), `ak-production` (leaderboard;
production is fully client-deterministic). None block the playable game.

---

## F. DEPLOY ORDER, PLAYABLE MILESTONES, PER-WAVE VERIFICATION

**Landing model:** the 8 module files are disjoint and co-registration is verified,
so they land in ONE bootstrap commit alongside Sections A-D (+ create `_registry.js`).
**Verify in this order** (production is the smoke test that proves the whole rail):

| # | Wave | Server now? | Playable milestone after bootstrap |
|---|------|-------------|------------------------------------|
| 1 | **production** | none | Walk into GEM/MINT/FORGE (FACTORY_ROW) or LAB/GEN (THE_DOCKS) -> keeper card -> COLLECT accrues gold/scrap/keys/fragments, UPGRADE spends gold, a "ready" pip floats over a loaded building. **This proves A1-A5 + B end to end.** |
| 2 | **arcade** | none | Walk into ARCADE (THE_STRIP) -> Joystick Jonah -> BONE DIG / ALLEY DASH / WHACK-A-STRAY play in an overlay; gold+bones pay out under the 500g/20b daily cap. |
| 3 | **modes** | none | Walk into STREET (THE_STRIP) -> WORLD MOBA / GULAG / STREET ENCOUNTER overlays play to a result + record into `p.modes`. (Engine-side survival/encounter need D1+C.) |
| 4 | **missions** | reuse ak-quests | Walk into FIXER (THE_YARDS) -> Marrow gives a delivery; grind it; TURN IN consumes inputs, pays gold/scrap/keys/BONES, surfaces the next job; FIXER "!" pip pulls you back. |
| 5 | **seasons** | reuse ak-pass/ak-crew | Walk into TROPHY (HOME_TURF) -> Goldie -> daily Marks check-in, Seasonal Stall cosmetics, live crew leaderboard, Pass entry; the world wears the chapter tint. |
| 6 | **encounters** | none | Wild dogs roam each zone (REAL cards, names + art via canon.js); walk in -> leash mini-game (capture -> soulbound copy) or STREET FIGHT (-> battler, needs D). |
| 7 | **raid** | NEW ak-raid (stub-OK) | Day: a rival-crew scout drives through -> WAR MAP (raid/shield/revenge). Night: siege beacon on THE LOT -> tower-defense overlay. Gold shields settle locally; gem shields show "coming soon". |
| 8 | **trading** | NEW ak-trading (stub-OK) | "Switch the Broker" patrols THE_YARDS -> walk up -> barter post (BOARD/POST/MINE). Offline today: board says "offline", POST/ACCEPT refund in full (nothing lost). |

### Per-wave verification checklist
For **every** wave, run all three:
1. **Parse gate:** `node --check game/systems/<id>.js` -> must print nothing (OK).
2. **Headless logic (the 2 economy-touching gates):**
   - run `node /tmp/ak_qa2.js`-style harness (mock `AK_SYSTEMS` per Contract 1.1 +
     mock `AK_ECON`); assert: the wave registers its `id`; `enterBuilding(<its
     building>)` returns its id and `enterBuilding({id:'ARENA'})` returns `false`;
     `init`+`onTick`+`onDrawWorld` run with no throw; and **a fresh profile is
     byte-identical after init+tick+draw** (the gate for production/missions/
     encounters/seasons/raid/arcade/modes that write profile state).
   - For **modes** additionally: feed a fake `game` (`{player:{crowns,towers:[{type:'king',hp,destroyed}]},opponent:{crowns},time}`) into `AK_MODES.survival.checkEnd`/`.encounter.checkEnd` and assert win/lose/null verdicts.
3. **Live marker grep (after the build ships):**
   - `curl -s https://alleykingz.online/index.html | grep -c 'systems/<id>.js'` -> `1`
   - `curl -s https://alleykingz.online/index.html | grep -c 'AK_CTX'` -> `>=1`
   - `curl -s https://alleykingz.online/game.html | grep -c 'systems/modes.js'` -> `1`
   - **Verify in a REAL browser (Playwright on e5), not just the node harness** (per
     the AK-SOLE-DEPLOYER + judged-by-feel laws): enter each building, confirm the
     keeper/overlay renders and a collect/play actually moves the currency.
   - Deploy ONLY via e5 `~/ak_deploy` -> `ship.sh` (stamps `?v=timestamp`). The phone
     is dev. One chat deploys AK.

---

## G. ADVERSARIAL QA -- risks, conflicts, and zero-state findings

**QA-1 (BLOCKER until D lands) -- the launch-intent handoff is not wired.**
`ctx.battle.launch` -> `game.html?intent=1`, but game.html's only autostart keys on
`?go=match` and routes through `playBtn` (which can open the World Map). And
`startMatch` never forwards `mode`. **Result without Section 6.D: every overlay->engine
handoff (encounter STREET FIGHT, raid, survival, gulag COLLIDE) lands on the lobby,
not the match.** Fix = D1+D2a+D2b. This is the single most important integration edit;
do not ship the waves without it.

**QA-2 (must reconcile) -- edge-fn name mismatch.** `trading.js` calls **`ak-trading`**
(`:32`); the contract manifest + file list say **`ak-trade`**. They must match the
deployed dir name. Recommendation: deploy the dir as `ak-trading` (the module's
literal) to avoid editing a frozen wave file, OR change `TRADE_FN` once. Pick one,
write it in both places, before the server lands. (Client is harmless until then --
all calls degrade to offline + refund.)

**QA-3 (cross-wave server dependency) -- capture dupes.** `encounters.grantCapture`
flags `// TODO-SERVER`: the `ak-trading` escrow MUST reject trading copies whose only
provenance is `p.captures`. Today both are client-side and trading is offline, so no
real dupe risk yet, but **`ak-trading` and `ak-raid` must both consult `p.captures`/
server inventory when they go live.** Track as a server-launch gate.

**QA-4 (degraded-but-safe) -- the hub loads only `economy.js` today.** Without
`canon.js`, `window.AK`/`CANON_CARDS`/`akCardArtRel` are absent on the hub, so
`ctx.cards()` is `{}` and: encounters/modes/trading fall back to their REAL-name
embeds (small subset, no art -> glyph/letter tokens), arcade dogs render as glyphs.
**All degrade gracefully (verified: encounters uses `CANON_CARDS` fallback, modes
fetches `../data/cards.json`, trading fetches it too).** A1 adds `canon.js` to fix
art + the full 106-card pool on the hub. For the LIVE missions Hit List + claim-in-
place, also add `ak_account.js`+`quests.js`+`social.js` to the hub (optional; missions
degrades to the shop surface without them). Adding `engine.js`+`handlers_data.js`
+ an `AK.init()` call would make `ctx.cards()` the full engine index, but is NOT
required and adds hub weight -- canon.js alone is the recommended minimum.

**QA-5 (acceptable MVP gap) -- `mode:'raid'` has no `AK_MODES.raid`.** raid.js launches
`battle.launch({mode:'raid'})`; with no win-condition entry, C1 sets
`convoyMode:false, modeImpl:null` -> a plain non-convoy single-board match labeled
RAID, ending via the C4 crown/tiebreak path. Playable and byte-safe. A future
`AK_MODES.raid` (base layout = battlefield) is the upgrade. Flagging so no one expects
surgical base-raid mechanics in v1.

**QA-6 (perf watch, NOT a blocker) -- per-frame full-screen draws + shadowBlur.**
Per the on-device-perf memory note (shadowBlur glut), audit on a real phone:
- **seasons.onDrawWorld** runs EVERY frame in EVERY zone: a `globalCompositeOperation
  ='soft-light'` full-screen `fillRect` (alpha .55) + ~22 ambient particles. Composite
  full-screen fills are the single heaviest item here. It is save/restore balanced and
  uses NO shadowBlur (good), but consider caching the wash or gating it to a lower
  cadence if FPS dips. Also note this is a VISIBLE world change with no player action
  (see QA-7).
- **raid.onDrawWorld** full-screen night tint `fillRect` (alpha up to .5) every frame
  at night -- fine, but it stacks under seasons' wash at night.
- **production pip (shadowBlur 14)**, **missions pip (shadowBlur 14)**, **trading broker
  ring (shadowBlur 10)** -- each ≤2 elements, cheap; keep (operator vetoed stripping
  glows -- pre-render to a sprite if a phone profile shows cost).

**QA-7 (zero-state -- PASS, with a hygiene note).** With the REAL `loadProfile()`
(fresh `JSON.parse` every call, confirmed `:93-:97`), the persisted profile is
byte-identical after `initAll`+ticks+draws on a fresh profile -- nothing is
`saveProfile`'d until the player acts. The only init-time touch is `missions.init`
calling `ms(p)` (the shape-normalizer) on a loaded profile, which mutates a throwaway
object that is discarded -> no persistence. **No fix required.** Hygiene note: an
`init` hook should treat the loaded profile as read-only; missions could read
`p.missions` defensively instead of via `ms(p)`. Benign because all `ms()` defaults
are falsy (`null/[]/0`).

**QA-8 (deliberate divergence, compliant) -- production resource mapping.** Contract
3.1's EXAMPLE maps GEM->gold, LAB->sp; the module maps GEM->Rare scrap, MINT->gold,
FORGE->key fragments (auto-forge 10->1 key), LAB->Epic scrap, GEN->keys + a rate boost.
Every output is soft-currency, gem-free, `$BCARDD`/`ALK`-free -> all HARD RULES hold.
The keeper names match `KEEPERS` exactly (Prospector Pip / Banker Bones / Sparks /
Doc Wattson / Volt -- verified). Accept as-is; just don't expect the example mapping.

**QA-9 (DOM z-index sanity) -- two waves inject DOM panels above the overlay.**
seasons `#ak-season` (z 47) and trading `#ak-trade` (z 46) sit ABOVE the overlay
canvas (z 40) and BELOW `#loadscreen` (z 50), per contract. Both build their DOM via
an XSS-safe `mk()` (textContent only, no innerHTML) -- verified. They open the
overlay first (freezes the hub) then layer the DOM panel on top; close tears both
down. No conflict with `#interior` (z 12). Confirm `#loadscreen`/`#interior`
z-indexes in the live CSS during browser verification.

**QA-10 (crypto/parity -- PASS across all 8).** No module ever grants `gems`
(`ctx.currency.grant('gems')` is a host no-op -- confirmed in the A2 helper). No
`$BCARDD`/`ALK` appears in any reward/trade/utility: the only occurrences are (a)
flavor strings, (b) `$BCARDD` as a Mythic faction-pool/jackpot SPRITE that is never
fielded as loot (raid caps defenders at Legendary; encounters/arcade exclude Mythics
from spawns/whacks), and (c) hard-block regexes in trading (`/\$|bcardd|alk/i`). Gems
appear only as raid's server-routed shield tiers (Fortress/Panic) which degrade to
"coming soon" offline. Marks (seasons) are cosmetic-only. "crew" not "clan" throughout
(the sole "Clan Yard" string is the literal `index.html` building label, not module
copy). **Parity holds.**

**QA-11 (headless-safety -- PASS).** Every module guards `if(!global.AK_SYSTEMS)return;`
(except modes, which intentionally registers `AK_MODES` unconditionally and wraps its
`AK_SYSTEMS.register` in `if(global.AK_SYSTEMS)`), has no top-level DOM/localStorage,
and routes all storage through `AK_ECON`. Loading all 8 in node threw nothing.

---

## H. FILE MANIFEST (what this commit lands)
```
specs/WAVE_INTEGRATION.md                 (this file -- Integrator)
game/systems/_registry.js                 (Lead: CREATE from Contract 1.1 -- DOES NOT EXIST YET)
game/systems/{production,missions,encounters,raid,seasons,trading,arcade,modes}.js   (8 waves -- present, parse-clean, co-register clean)
-- shared-file edits (Sections A-D), landed ONCE --
game/index.html      (A1 scripts + A2 AK_CTX/initAll + A3 enterInterior seam + A4 loop tick + A5 draw world)  + canon.js (QA-4)
game/economy.js      (B: 10-field ensureShape block before :91 return p;)
game/engine.js       (C1 mode/convoyMode/modeImpl @:1397 + C2 setup @:1442 + C3 checkEnd @:2659 + C4 endMatch wrap @:3969)
game/game.html       (D1 _registry+modes before :2106 + D2a mode in startMatch @:5041 + D2b intent autostart after :5283)
-- deploy LATER, all degrade gracefully --
supabase/functions/ak-raid/   + supabase/migrations/<ts>_raid.sql        (E2)
supabase/functions/ak-trading/ (or ak-trade) + supabase/migrations/<ts>_trading.sql   (E3; spec embedded in trading.js)
reuse: ak-quests, ak-pass, ak-crew, ak-cosmetics (E1/E4)
```
Eight disjoint wave files, one bootstrap, one new host file (`_registry.js`). The
host never changes again. Land it, smoke-test production, then verify down the list.
