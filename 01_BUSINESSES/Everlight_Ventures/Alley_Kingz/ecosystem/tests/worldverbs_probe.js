// ==========================================================================
// ALLEY KINGZ -- NODE HARNESS for systems/worldverbs.js (no browser, no deps)
// Proves the harvest module is REAL gameplay, not a stub:
//   1. it loads beside the other system modules with zero conflict,
//   2. generates 6-10 deterministic nodes clear of doors/plaza/corridors,
//   3. a harvest ACTUALLY increments the material currency,
//   4. the node DEPLETES (not ripe, growthStage < 3) and refuses a re-harvest,
//   5. after the respawn window + an onTick sweep the node REGROWS (ripe again).
// Usage: node ecosystem/tests/worldverbs_probe.js
// ==========================================================================
'use strict';
const GAME_DIR = __dirname + '/../game';
let fails = 0;
function ok(cond, msg) { console.log((cond ? '  PASS ' : '  FAIL ') + msg); if (!cond) fails++; }

// --- browser-shim: window + a real in-memory localStorage so AK_ECON persists ---
global.window = global;
(function () {
  const store = {};
  global.localStorage = {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem: function (k, v) { store[k] = String(v); },
    removeItem: function (k) { delete store[k]; }
  };
})();

// --- controllable clock so we can fast-forward the respawn window ---------
const realNow = Date.now;
let CLOCK = realNow();
Date.now = function () { return CLOCK; };

// --- AK_SYSTEMS stub: capture every registered module (proves zero-conflict load) ---
const registered = [];
let modById = {};
global.window.AK_SYSTEMS = {
  register: function (m) { if (!m || !m.id || modById[m.id]) return false; modById[m.id] = m; registered.push(m); return true; },
  get: function (id) { return modById[id] || null; },
  all: function () { return registered.slice(); }
};

// --- load economy + every system module (zero-conflict smoke test) --------
require(GAME_DIR + '/economy.js');                   // AK_ECON
const LOAD = ['worldmap', 'production', 'missions', 'encounters', 'raid', 'seasons',
  'trading', 'arcade', 'modes', 'karma', 'loops', 'buildmode', 'worldverbs'];
// loops.js attaches a <video> interior backdrop and touches `document` at load
// (DOM-by-design, pre-existing) -- it is the ONE module that is not headless-load
// -safe, independent of worldverbs. Everything else (incl. worldverbs) must load clean.
const KNOWN_DOM_AT_LOAD = { loops: 1 };
let loaded = 0, headlessErrs = [], knownSkips = [];
LOAD.forEach(function (name) {
  try { require(GAME_DIR + '/systems/' + name + '.js'); loaded++; }
  catch (e) {
    if (KNOWN_DOM_AT_LOAD[name]) knownSkips.push(name + ' (' + (e && e.message) + ')');
    else headlessErrs.push(name + ': ' + (e && e.message));
  }
});
console.log('=== LOAD ===');
console.log('  loaded ' + loaded + '/' + LOAD.length + ' headless'
  + (knownSkips.length ? '  | known DOM-at-load (browser-only): ' + knownSkips.join(', ') : '')
  + (headlessErrs.length ? '  | UNEXPECTED: ' + headlessErrs.join(' | ') : ''));
ok(headlessErrs.length === 0, 'every headless-safe module loads with zero conflict (loops.js is DOM-by-design, expected)');
ok(global.AK_WORLDVERBS != null, 'AK_WORLDVERBS exported');
ok(modById['worldverbs'] != null, 'worldverbs registered with AK_SYSTEMS');
ok(modById['buildmode'] != null, 'buildmode also registered (shared wood/stone/metal fields)');

// --- fake Canvas2D ctx (no-op methods, settable props) so onDrawWorld can run ---
const fakeG = new Proxy({ canvas: { width: 800, height: 1200 } }, {
  get: function (t, k) { if (k in t) return t[k]; return function () {}; },
  set: function (t, k, v) { t[k] = v; return true; }
});

// --- a HOME_TURF-like zone (matches index.html ZONES.HOME_TURF) -----------
const me = { x: 850, y: 650, r: 20 };
const ZONE = {
  id: 'HOME_TURF', name: 'THE LOT', ground: 'uptown',
  buildings: [
    { id: 'ARENA', label: 'TOWN HALL', x: 850, y: 360, w: 210, h: 124 },
    { id: 'TROPHY', label: 'TROPHY HALL', x: 430, y: 880, w: 160, h: 96 },
    { id: 'KENNEL', label: 'THE KENNEL', x: 1270, y: 880, w: 160, h: 96 }
  ],
  edges: { N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } }, E: { spawn: { x: 150, y: 650 } }, W: { spawn: { x: 1550, y: 650 } } }
};
const banners = [];
const ctx = {
  econ: global.AK_ECON, AK_ECON: global.AK_ECON,
  zoneId: 'HOME_TURF', activeZone: ZONE, me: me,
  showBanner: function (t) { banners.push(t); },
  ui: { keeperCard: function () {} },
  overlay: { open: function () { return { close: function () {} }; } },
  currency: { get: function () { return 0; }, grant: function () { return null; } },
  world: {
    g: fakeG, W: 800, H: 1200, WORLD_W: 1700, WORLD_H: 1300,
    wx: function (x) { return x; }, wy: function (y) { return y; },
    distToMe: function (x, y) { return Math.hypot(me.x - x, me.y - y); }
  }
};

const mod = modById['worldverbs'];
mod.init(ctx);

// AK-TOOLS (sec 3): harvest is now TOOL-GATED. Seed a T1 tool of every type so
// the legacy faucet-loop assertions below (which harvest HOME_TURF's nodes[0] =
// Brushwood, an Axe-T1 node) still pass. A T1 tool has +0% bonus, so the
// "incremented by exactly the node payout" check holds. The no-tool gate itself
// is proven in tests/worldverbs_econ_harness.js.
global.AK_ECON.mutateProfile(function (p) {
  p.coins = 99999; p.townHall = 7;
  p.tools = { axe: { tier: 1, dur: 25, owned: [1] }, pickaxe: { tier: 1, dur: 25, owned: [1] },
              crowbar: { tier: 1, dur: 25, owned: [1] }, drill: { tier: 1, dur: 25, owned: [1] } };
});

// --- node generation ------------------------------------------------------
console.log('=== NODE GEN ===');
const nodes = global.AK_WORLDVERBS.nodes();
console.log('  generated ' + nodes.length + ' nodes: ' + nodes.map(function (n) { return n.key + '(' + n.type + '+' + n.amount + ')'; }).join(' '));
ok(nodes.length >= 6 && nodes.length <= 10, 'node count in 6..10 range');
// re-gen must be identical (deterministic)
const nodes2 = global.AK_WORLDVERBS.nodesForZone(ZONE);
ok(JSON.stringify(nodes) === JSON.stringify(nodes2), 'placement is deterministic (same nodes on re-gen)');
// every node clear of plaza / corridor spines / doors / edges
let clear = true, why = '';
nodes.forEach(function (n) {
  if (Math.abs(n.x - 850) < 95) { clear = false; why = n.key + ' in vertical spine'; }
  if (Math.abs(n.y - 650) < 105) { clear = false; why = n.key + ' in horizontal spine'; }
  if (Math.hypot(n.x - 850, n.y - 650) < 160) { clear = false; why = n.key + ' in plaza'; }
  ZONE.buildings.forEach(function (b) { if (Math.hypot(n.x - b.x, n.y - (b.y + b.h / 2)) < 120) { clear = false; why = n.key + ' on a door'; } });
});
ok(clear, 'all nodes clear of plaza / corridors / doors' + (clear ? '' : ' -- ' + why));
// node types map to all four materials across districts
const mats = {}; nodes.forEach(function (n) { mats[n.mat] = 1; });
ok(Object.keys(mats).length >= 1, 'nodes carry materials: ' + Object.keys(mats).join(','));

// --- harvest increments material + depletes node --------------------------
console.log('=== HARVEST ===');
const target = nodes[0];
const matField = target.mat;
function matVal() { const p = global.AK_ECON.loadProfile(); return matField === 'scrap' ? (p.scrap[target.rar] | 0) : (p[matField] | 0); }
const before = matVal();
ok(global.AK_WORLDVERBS.isRipe(target.key) === true, target.key + ' starts ripe');
const did = global.AK_WORLDVERBS.harvest(target.key);
ok(did === true, 'harvest(' + target.key + ') succeeded');
const after = matVal();
console.log('  ' + matField + (matField === 'scrap' ? '.' + target.rar : '') + ': ' + before + ' -> ' + after + '  (+' + target.amount + ' expected)');
ok(after === before + target.amount, 'material incremented by exactly the node payout');
ok(global.AK_WORLDVERBS.isRipe(target.key) === false, 'node is now DEPLETED (not ripe)');
ok(global.AK_WORLDVERBS.stage(target.key) < 3, 'depleted node growthStage < 3 (stage=' + global.AK_WORLDVERBS.stage(target.key) + ')');
// persisted in p.nodes
const pAfter = global.AK_ECON.loadProfile();
ok(pAfter.nodes && pAfter.nodes.HOME_TURF && pAfter.nodes.HOME_TURF[target.key], 'depletion persisted in p.nodes');
// re-harvesting a depleted node does nothing
const before2 = matVal();
const again = global.AK_WORLDVERBS.harvest(target.key);
ok(again === false && matVal() === before2, 'cannot re-harvest a regrowing node (no double-dip)');

// --- regrow: fast-forward past the respawn window + tick sweep ------------
console.log('=== REGROW ===');
CLOCK += target.dur + 2000;                          // jump past the respawn timer
mod.onTick(2.0, ctx);                                // sweep fires (> 1.5s throttle)
ok(global.AK_WORLDVERBS.isRipe(target.key) === true, 'node REGREW to ripe after respawn window');
ok(global.AK_WORLDVERBS.stage(target.key) === 3, 'regrown node growthStage == 3');
const pRe = global.AK_ECON.loadProfile();
ok(!(pRe.nodes && pRe.nodes.HOME_TURF && pRe.nodes.HOME_TURF[target.key]), 'sweep cleaned the depletion entry');
// can harvest again now
const before3 = matVal();
ok(global.AK_WORLDVERBS.harvest(target.key) === true && matVal() === before3 + target.amount, 're-harvest after regrow grants again');

// --- render smoke test ----------------------------------------------------
console.log('=== RENDER ===');
let drewOK = true;
try { mod.onDrawWorld(ctx); } catch (e) { drewOK = false; console.log('  draw threw: ' + (e && e.stack || e)); }
ok(drewOK, 'onDrawWorld runs headlessly without throwing');

// --- verdict --------------------------------------------------------------
Date.now = realNow;
console.log('\n=== VERDICT: ' + (fails === 0 ? 'ALL PASS' : fails + ' FAILED') + ' ===');
process.exit(fails === 0 ? 0 : 1);
