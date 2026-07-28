// ==========================================================================
// ALLEY KINGZ -- DARK WAR WORLD-MAP NODE HARNESS (#3, Agent B)  -- no browser
// Proves, headless (mock Canvas2D ctx, no DOM):
//   1. worldmap.js loads + registers + exposes window.AKWorldMap.
//   2. TARGETS LOAD -- worldTargets() yields VALID AK_RAIDSCENE targets in the
//      shared shape {name,crew,faction,layout:[{type,x,y,hp,maxHp}],coreHp,
//      trophies,reward:{gold,scrap,wood,stone,metal}} -- soft/material ONLY,
//      no gems/$BCARDD -- in BOTH the degrade path (local canon crews) AND the
//      preferred path (window.AK_RAIDSCENE.targets(), including partial data
//      that normalizeTarget must repair + token-strip).
//   3. THE MAP BUILDS -- placeTerritories() scatters home + N enemy territories.
//   4. THE HANDOFF -- the crew MARCH, driven through the REAL overlay onFrame
//      loop to completion, calls window.AK_RAIDSCENE.launch(target) with a valid
//      target (end-to-end: startMarch -> animate -> api.close -> onClose ->
//      launchRaidScene -> AK_RAIDSCENE.launch).
//   5. DEGRADE -- with no AK_RAIDSCENE, the same launch falls back to the live
//      battler raid (ctx.battle.launch mode:'raid') so the march still works.
// Usage: node ecosystem/tests/worldmap_darkwar_harness.js
// ==========================================================================
'use strict';

var GAME_DIR = __dirname + '/../game';
global.window = global;                       // worldmap.js falls back to globalThis

var fails = [], passes = 0;
function ok(cond, msg) { if (cond) { passes++; console.log('  PASS  ' + msg); } else { fails.push(msg); console.log('  FAIL  ' + msg); } }

// ---- mock Canvas2D context (every method = no-op; gradients + measureText real-ish)
function mockG() {
  var grad = { addColorStop: function () {} };
  return new Proxy({}, {
    get: function (t, p) {
      if (p === 'measureText') return function () { return { width: 12 }; };
      if (p === 'createLinearGradient' || p === 'createRadialGradient') return function () { return grad; };
      if (p in t) return t[p];
      return function () {};
    },
    set: function (t, p, v) { t[p] = v; return true; }
  });
}

// ---- a fake AK_CTX (only what worldmap.js touches) -----------------------
function makeProfile() { return { coins: 9000, scrap: {}, raid: { shieldUntil: 0, revenge: [] }, baseLayout: {} }; }
function makeCards() {
  var names = ['Tank Pug', 'Stonejaw', 'Neon Whippet', 'Turbo Jack', 'Firewall', 'Laser Beagle', '$BCARDD'];
  var m = {}; names.forEach(function (n, i) { m[n] = { cardNumber: String(1000 + i), id: String(1000 + i) }; }); return m;
}
function B(id, label, col, x, y, w, h) { return { id: id, label: label, col: col, x: x, y: y, w: w, h: h }; }
function makeZones() {
  return {
    HOME_TURF: { id: 'HOME_TURF', name: 'THE LOT', gx: 1, gy: 1, locked: false,
      buildings: [B('ARENA', 'TOWN HALL', '#e8c55a', 850, 360, 210, 124), B('TROPHY', 'TROPHY HALL', '#ffd76b', 430, 880, 160, 96)] },
    DOWNTOWN: { id: 'DOWNTOWN', name: 'DOWNTOWN', gx: 1, gy: 0, locked: false,
      buildings: [B('DROP', 'THE DROP', '#ff8fae', 560, 560, 170, 104)] },
    THE_OVERLOOK: { id: 'THE_OVERLOOK', name: 'THE OVERLOOK', gx: 0, gy: 0, locked: true, barrierLabel: 'POLICE CHECKPOINT', buildings: [] }
  };
}
var battleIntents = [];
function makeCtx() {
  var profile = makeProfile(), cards = makeCards(), ZONES = makeZones();
  return {
    ZONES: ZONES, zoneId: 'HOME_TURF', activeZone: ZONES.HOME_TURF,
    me: { x: 850, y: 650, r: 22 }, cam: { x: 0, y: 0 },
    cards: function () { return cards; },
    showBanner: function () {},
    econ: {
      loadProfile: function () { return profile; },
      mutateProfile: function (fn) { try { fn(profile); } catch (e) {} return profile; },
      townHallLevel: function () { return 4; }
    },
    battle: { launch: function (o) { battleIntents.push(o); } },
    currency: { get: function () { return 0; }, grant: function () { return null; } },
    world: { WORLD_W: 1700, WORLD_H: 1300, W: 390, H: 780,
      wx: function (x) { return x; }, wy: function (y) { return y; },
      distToMe: function () { return 9999; }, addRoamer: function (s) { return s; }, removeRoamer: function () {}, roamers: function () { return []; } },
    overlay: { open: function (spec) {
      var api = { g: mockG(), vp: { w: 390, h: 780, dpr: 1 }, _closed: false,
        close: function (res) { if (api._closed) return; api._closed = true; if (spec.onClose) spec.onClose(res); } };
      lastOverlay = { spec: spec, api: api }; return api;
    } }
  };
}
var lastOverlay = null;

// ---- validity check for an AK_RAIDSCENE target ---------------------------
var REWARD_KEYS = ['gold', 'scrap', 'wood', 'stone', 'metal'];
var BANNED = ['gems', 'gem', 'ALK', 'alk', 'bcardd', 'BCARDD', '$BCARDD'];
function validTarget(t, tag) {
  if (!t || typeof t !== 'object') { ok(false, tag + ': target is an object'); return; }
  ok(typeof t.name === 'string' && t.name.length > 0, tag + ': name string');
  ok(typeof t.crew === 'string' && t.crew.length > 0, tag + ': crew string');
  ok(typeof t.faction === 'string' && t.faction.length > 0, tag + ': faction string');
  ok(typeof t.coreHp === 'number' && t.coreHp > 0, tag + ': coreHp number > 0');
  ok(typeof t.trophies === 'number', tag + ': trophies number');
  ok(Array.isArray(t.layout) && t.layout.length > 0, tag + ': layout is non-empty array');
  var layoutOK = Array.isArray(t.layout) && t.layout.every(function (s) {
    return s && typeof s.type === 'string' && typeof s.x === 'number' && typeof s.y === 'number'
      && typeof s.hp === 'number' && typeof s.maxHp === 'number';
  });
  ok(layoutOK, tag + ': every layout entry has {type,x,y,hp,maxHp}');
  ok(t.reward && typeof t.reward === 'object', tag + ': reward object');
  var rewOK = t.reward && REWARD_KEYS.every(function (k) { return typeof t.reward[k] === 'number'; });
  ok(rewOK, tag + ': reward has numeric gold/scrap/wood/stone/metal');
  var clean = t.reward && BANNED.every(function (k) { return !(k in t.reward); });
  ok(clean, tag + ': reward carries NO gems/ALK/$BCARDD (crypto gate)');
}

// ==========================================================================
// LOAD
// ==========================================================================
require(GAME_DIR + '/systems/_registry.js');          // sets window.AK_SYSTEMS (required for the overlay/API section)
require(GAME_DIR + '/systems/worldmap.js');           // registers + exposes AK_COLLISION + AKWorldMap

ok(!!global.AK_COLLISION, 'AK_COLLISION exported');
ok(!!global.AKWorldMap && typeof global.AKWorldMap.openWorld === 'function', 'window.AKWorldMap.openWorld exists');
ok(global.AK_SYSTEMS.get('worldmap') != null, 'worldmap registered in AK_SYSTEMS');

var WM = global.AKWorldMap;
var ctx = makeCtx();

// ==========================================================================
// TEST 2a -- TARGETS LOAD (degrade path: no AK_RAIDSCENE -> local canon crews)
// ==========================================================================
console.log('\n[2a] degrade-path targets (local canon war-crews):');
delete global.AK_RAIDSCENE;
var degradeTs = WM._targets(ctx);
ok(Array.isArray(degradeTs) && degradeTs.length >= 3, 'degrade yields >=3 targets (got ' + (degradeTs ? degradeTs.length : 0) + ')');
if (degradeTs && degradeTs.length) { validTarget(degradeTs[0], 'degrade[0]'); validTarget(degradeTs[degradeTs.length - 1], 'degrade[last]'); }

// ==========================================================================
// TEST 2b -- PREFERRED path (window.AK_RAIDSCENE.targets()) + normalize/repair
// ==========================================================================
console.log('\n[2b] preferred-path targets (AK_RAIDSCENE.targets(), partial data repaired):');
var launched = [];
global.AK_RAIDSCENE = {
  // intentionally PARTIAL + token-tainted -> normalizeTarget must repair + strip
  targets: function () {
    return [
      { name: 'Crypt Kings', crew: 'Boneguard Crew', faction: 'boneguard_crew', tier: 3,
        reward: { gold: 700, gems: 99, '$BCARDD': 5 } },                 // missing layout/coreHp; tainted reward
      { name: 'Grid Pack', crew: 'K9 Circuitry', faction: 'k9_circuitry', tier: 2,
        layout: [{ type: 'METAL', x: 850, y: 650, hp: 1200, maxHp: 1200 }], coreHp: 2200,
        reward: { gold: 400, scrap: 4, wood: 40, stone: 20, metal: 10 } } // already complete
    ];
  },
  launch: function (t) { launched.push(t); }
};
var prefTs = WM._targets(ctx);
ok(Array.isArray(prefTs) && prefTs.length === 2, 'preferred path returns the 2 partner targets');
if (prefTs && prefTs.length) {
  validTarget(prefTs[0], 'partner[0]-repaired');
  validTarget(prefTs[1], 'partner[1]-complete');
  ok(prefTs[0].layout.length > 0, 'partner[0]: missing layout was rebuilt from structure vocab');
  ok(typeof prefTs[0].coreHp === 'number', 'partner[0]: missing coreHp was filled');
  ok(!('gems' in prefTs[0].reward) && !('$BCARDD' in prefTs[0].reward), 'partner[0]: gems + $BCARDD STRIPPED from reward');
}

// ==========================================================================
// TEST 3 -- THE MAP BUILDS (placeTerritories scatters home + enemies)
// ==========================================================================
console.log('\n[3] map builds (placeTerritories):');
var placed = WM._placeTerritories(ctx);
ok(Array.isArray(placed) && placed.length === prefTs.length, 'one territory placed per target (' + placed.length + ')');
ok(WM._state._home && typeof WM._state._home.wx === 'number', 'home territory positioned on the war map');
var inBounds = placed.every(function (p) { return p.wx >= 0 && p.wx <= 2600 && p.wy >= 0 && p.wy <= 1900 && p.target; });
ok(inBounds, 'every enemy territory is in-bounds + carries a .target');

// ==========================================================================
// TEST 4 -- DIRECT HANDOFF: launchRaidScene -> AK_RAIDSCENE.launch(valid target)
// ==========================================================================
console.log('\n[4] direct handoff (launchRaidScene -> AK_RAIDSCENE.launch):');
launched.length = 0;
var aTarget = placed[0].target;
WM._launch(ctx, aTarget);
ok(launched.length === 1, 'AK_RAIDSCENE.launch was called exactly once');
ok(launched[0] === aTarget, 'launch received the SAME target object');
validTarget(launched[0], 'launched-target');

// ==========================================================================
// TEST 5 -- FULL march->launch through the REAL overlay onFrame loop
// ==========================================================================
console.log('\n[5] end-to-end crew march -> launch (driven through onFrame):');
launched.length = 0;
WM.openWorld(ctx);                                   // opens the overlay in the Dark War tier
ok(!!lastOverlay && typeof lastOverlay.spec.onFrame === 'function', 'world overlay opened with an onFrame');
// pick the first territory + kick off the march exactly like tapping MARCH
var terr = WM._state.wterr[0];
ok(!!terr, 'a marchable territory exists');
WM._startMarch(ctx, terr, lastOverlay.api);
ok(!!WM._state.march, 'march started');
// drive frames (dt=0.1) until the march completes + the handoff fires
var frames = 0;
while (frames < 80 && launched.length === 0) {
  lastOverlay.spec.onFrame(lastOverlay.api.g, 0.1, lastOverlay.api.vp, lastOverlay.api);
  frames++;
}
ok(launched.length === 1, 'march completed -> AK_RAIDSCENE.launch fired once (after ' + frames + ' frames)');
ok(launched[0] === terr.target, 'launch received this territory\'s target');
if (launched[0]) validTarget(launched[0], 'march-launched-target');
ok(WM._state.march === null, 'march state cleared after handoff');
ok(lastOverlay.api._closed === true, 'world overlay closed during the handoff');

// ==========================================================================
// TEST 6 -- DEGRADE: no AK_RAIDSCENE -> march falls back to the battler raid
// ==========================================================================
console.log('\n[6] degrade handoff (no AK_RAIDSCENE -> ctx.battle.launch mode:raid):');
delete global.AK_RAIDSCENE;
battleIntents.length = 0;
var degTarget = WM._toTarget(ctx, { id: 'wc_x', name: 'Marrow Syndicate', cls: 'Boneguard Crew', faction: 'boneguard_crew', tier: 2, accent: '#e8c55a' });
WM._launch(ctx, degTarget);
ok(battleIntents.length === 1, 'battler raid launched as fallback');
ok(battleIntents.length && battleIntents[0].mode === 'raid', 'fallback launch used mode:"raid"');

// ==========================================================================
console.log('\n========================================================');
console.log('RESULT: ' + passes + ' passed, ' + fails.length + ' failed');
if (fails.length) { console.log('=== VERDICT: DARK WAR HARNESS FAILED ==='); fails.forEach(function (f) { console.log('   - ' + f); }); process.exit(1); }
console.log('=== VERDICT: DARK WAR WORLD MAP -- BUILD + TARGETS + MARCH->LAUNCH ALL CLEAN ===');
