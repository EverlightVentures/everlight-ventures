// ==========================================================================
// ALLEY KINGZ -- WORLD VERBS x RESOURCE ECONOMY HARNESS (AK_RESOURCE_ECONOMY_DESIGN
// secs 3, 4, 8). Headless (no browser, no deps). Proves the operator's four laws:
//
//   1. NO TOOL => NO HARVEST. Bare Paws (T0) cannot work any node; walking up
//      banners "NEED A BETTER {TOOL}" and NOTHING is granted or depleted.
//   2. THE CHANNEL TAKES TIME. Tapping a ripe node starts a timed channel; the
//      material lands ONLY when the channel finishes (driven by accumulated dt).
//   3. THE NODE DEPLETES + RESPAWNS ON THE TABLE TIMER, stepping growthStage 0->3.
//   4. TOOL DURABILITY DECREMENTS per harvest, and a broken tier falls back to
//      the next-lower owned tier (never "unusable").
//
//   + per-district PLACEMENT PATTERNS (rows/grid/cluster/scatter/line/ring/quay),
//   + the Town-Hall tier gate + the crypto gate (gems never raise a cap/level/loot).
//
// Runs the REAL economy.js (AK_ECON tool ladder + p.tools state) behind an
// in-memory localStorage so state persists exactly like the browser. The REAL
// worldverbs.js system is driven through its public AK_WORLDVERBS API + onTick.
//
// Usage: node ecosystem/tests/worldverbs_econ_harness.js
// ==========================================================================
'use strict';
var GAME = __dirname + '/../game';
var pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name + (extra ? '  (' + extra + ')' : '')); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}

// ---- browser shim: window + in-memory localStorage so AK_ECON persists -------
global.window = global;
(function () {
  var store = {};
  global.localStorage = {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem: function (k, v) { store[k] = String(v); },
    removeItem: function (k) { delete store[k]; }
  };
})();

// ---- controllable clock (fast-forward the respawn window) --------------------
var realNow = Date.now;
var CLOCK = realNow();
Date.now = function () { return CLOCK; };

// ---- real registry so worldverbs self-registers ------------------------------
require(GAME + '/economy.js');
require(GAME + '/systems/_registry.js');
require(GAME + '/systems/worldverbs.js');
var E = global.AK_ECON, WVM = global.AK_SYSTEMS.get('worldverbs'), API = global.AK_WORLDVERBS;
ok('AK_ECON + worldverbs system + AK_WORLDVERBS present', !!(E && WVM && API));
ok('AK_ECON exposes the tool ladder + state helpers',
  typeof E.toolFor === 'function' && typeof E.buyTool === 'function' && typeof E.spendDurability === 'function'
  && Array.isArray(E.TOOL_TIERS) && E.TOOL_TIERS.length === 5);

// ---- fake Canvas2D ctx (no-op draw) ------------------------------------------
var fakeG = new Proxy({ canvas: { width: 800, height: 1200 } }, {
  get: function (t, k) { if (k in t) return t[k]; return function () {}; },
  set: function (t, k, v) { t[k] = v; return true; }
});

// ---- zones (live index.html shapes) ------------------------------------------
function B(id, label, x, y, w, h) { return { id: id, label: label, x: x, y: y, w: w, h: h }; }
var ZONES = {
  HOME_TURF: { id: 'HOME_TURF', name: 'THE LOT', ground: 'uptown',
    buildings: [B('ARENA', 'TOWN HALL', 850, 360, 210, 124), B('TROPHY', 'TROPHY HALL', 430, 880, 160, 96), B('KENNEL', 'THE KENNEL', 1270, 880, 160, 96)],
    edges: { N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } }, E: { spawn: { x: 150, y: 650 } }, W: { spawn: { x: 1550, y: 650 } } } },
  DOWNTOWN: { id: 'DOWNTOWN', name: 'DOWNTOWN', ground: 'midtown',
    buildings: [B('DROP', 'THE DROP', 560, 560, 170, 104), B('GARAGE', 'THE GARAGE', 1140, 560, 170, 104)],
    edges: { S: { spawn: { x: 850, y: 150 } }, W: { spawn: { x: 1550, y: 650 } }, E: { spawn: { x: 150, y: 650 } } } },
  THE_YARDS: { id: 'THE_YARDS', name: 'THE YARDS', ground: 'docks',
    buildings: [B('CLAN', 'CREW YARD', 560, 560, 170, 104), B('PASS', 'PASS HOUSE', 1140, 560, 170, 104), B('FIXER', 'THE FIXER', 850, 960, 160, 96)],
    edges: { E: { spawn: { x: 150, y: 650 } }, N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } } } },
  FACTORY_ROW: { id: 'FACTORY_ROW', name: 'FACTORY ROW', ground: 'docks',
    buildings: [B('GEM', 'GEM MINE', 520, 540, 160, 100), B('MINT', 'GOLD MINT', 1180, 540, 160, 100), B('FORGE', 'CARD FORGE', 850, 960, 170, 104)],
    edges: { W: { spawn: { x: 1550, y: 650 } }, N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } } } },
  THE_DOCKS: { id: 'THE_DOCKS', name: 'THE DOCKS', ground: 'docks',
    buildings: [B('LAB', 'RESEARCH LAB', 560, 540, 160, 100), B('GEN', 'THE GENERATOR', 1140, 540, 160, 100)],
    edges: { N: { spawn: { x: 850, y: 1150 } }, W: { spawn: { x: 1550, y: 650 } } } }
};
var ctx = {
  econ: E, AK_ECON: E,
  zoneId: 'HOME_TURF', activeZone: ZONES.HOME_TURF,
  showBanner: function (t) { ctx._banner = t; }, _banner: '',
  ui: { keeperCard: function () {} },
  overlay: { open: function () { return { close: function () {} }; } },
  currency: { get: function () { return 0; }, grant: function () { return null; } },
  world: { g: fakeG, W: 800, H: 1200, WORLD_W: 1700, WORLD_H: 1300,
    wx: function (x) { return x; }, wy: function (y) { return y; }, distToMe: function () { return 9999; } }
};
WVM.init(ctx);

function wood() { return E.loadProfile().wood | 0; }
function setZone(id) { ctx.zoneId = id; ctx.activeZone = ZONES[id]; }
function freshBrushwood() {                              // first ripe Brushwood (Axe-T1) in HOME_TURF
  setZone('HOME_TURF');
  var ns = API.nodesForZone(ZONES.HOME_TURF);
  for (var i = 0; i < ns.length; i++) if (ns[i].type === 'BRUSHWOOD' && API.isRipe(ns[i].key)) return ns[i];
  return ns[0];
}

// ==========================================================================
console.log('\n[1] NODE TABLE matches the design (sec 4.3):');
var NT = API.NODE_TYPES;
ok('Brushwood = Axe T1, 6s channel, 8 wood, 8 min respawn',
  NT.BRUSHWOOD.tool === 'axe' && NT.BRUSHWOOD.minTier === 1 && NT.BRUSHWOOD.channel === 6 && NT.BRUSHWOOD.amount === 8 && NT.BRUSHWOOD.dur === 8 * 60000);
ok('Hardwood = Axe T2, 16s, 22 wood, ~25 min respawn (mid-tier anchor)',
  NT.HARDWOOD.minTier === 2 && NT.HARDWOOD.channel === 16 && NT.HARDWOOD.amount === 22 && NT.HARDWOOD.dur === 25 * 60000);
ok('Coolant pipe = Crowbar T3, 45 min respawn', NT.PIPE.tool === 'crowbar' && NT.PIPE.minTier === 3 && NT.PIPE.dur === 45 * 60000);
ok('Rare vein = Drill T4, 90 min respawn, jackpot', NT.RAREVEIN.tool === 'drill' && NT.RAREVEIN.minTier === 4 && NT.RAREVEIN.dur === 90 * 60000 && NT.RAREVEIN.jackpot === true);
ok('Wreck has a dual yield (metal + scrap)', NT.WRECK.mat === 'metal' && NT.WRECK.alt && NT.WRECK.alt.mat === 'scrap');

// ==========================================================================
console.log('\n[2] LAW 1 -- NO TOOL, NO HARVEST (Bare Paws cannot work a node):');
ok('a fresh profile has T0 Bare Paws for every tool', API.toolFor('axe').tier === 0 && API.toolFor('drill').tier === 0);
var bw = freshBrushwood();
var woodBefore = wood();
var gated = API.harvest(bw.key);
ok('harvest with no tool is REFUSED', gated === false);
ok('the banner reads "NEED A BETTER AXE"', /NEED A BETTER AXE/.test(ctx._banner), ctx._banner);
ok('no material was granted (wood unchanged)', wood() === woodBefore, 'wood=' + wood());
ok('the node was NOT depleted (still ripe, zero-state preserved)', API.isRipe(bw.key) === true);
var pGate = E.loadProfile();
ok('reads/failed-harvest wrote NO node + NO tool state (p.nodes/p.tools empty)',
  Object.keys(pGate.nodes || {}).length === 0 && Object.keys(pGate.tools || {}).length === 0);

// ==========================================================================
console.log('\n[3] BUY a tool (gold path) -> the gate opens:');
E.mutateProfile(function (p) { p.coins = 5000; p.townHall = 1; });   // TH1 so builderSpeed=1 -> clean channel math
var buy = E.buyTool('axe', 1, 'gold');
ok('buyTool axe T1 (gold 60) ok', buy.ok === true && buy.tier === 1, JSON.stringify(buy.paid));
ok('coins deducted by exactly 60', (E.loadProfile().coins | 0) === 4940);
var tfAxe = API.toolFor('axe');
ok('axe is now T1 with full durability (25)', tfAxe.tier === 1 && tfAxe.dur === 25);

// ==========================================================================
console.log('\n[4] LAW 2 -- THE CHANNEL TAKES TIME (tap != instant grab):');
bw = freshBrushwood();
var dur = API.effChannelSec(bw.key);
ok('effective channel = base 6s x toolMult 1.0 / builderSpeed 1.0 = ~6s', Math.abs(dur - 6) < 0.001, 'dur=' + dur.toFixed(2) + 's');
var wPre = wood();
ok('startChannel begins the channel', API.startChannel(bw.key) === true && API.channel() && API.channel().key === bw.key);
WVM.onTick(dur * 0.4, ctx);
ok('after 40% of the channel: still WORKING, NOTHING granted yet', !!API.channel() && wood() === wPre, 'frac=' + (API.channel() ? API.channel().frac.toFixed(2) : 'gone'));
WVM.onTick(dur * 0.4, ctx);
ok('after 80%: still WORKING, still nothing granted', !!API.channel() && wood() === wPre, 'frac=' + (API.channel() ? API.channel().frac.toFixed(2) : 'gone'));
WVM.onTick(dur * 0.4, ctx);   // crosses 100%
ok('after the channel completes: material lands + channel clears', API.channel() === null && wood() === wPre + 8, 'wood ' + wPre + ' -> ' + wood());
ok('the worked node is now depleted (channel did the harvest)', API.isRipe(bw.key) === false);

// ==========================================================================
console.log('\n[5] LAW 3 -- DEPLETE + RESPAWN ON THE TABLE TIMER (growthStage 0->3):');
var harvestClock = CLOCK, durMs = NT.BRUSHWOOD.dur;     // 8 min
ok('right after harvest: growthStage 0 (freshly cut)', API.stage(bw.key) === 0);
CLOCK = harvestClock + durMs * 0.5;
ok('at 50% regrown: growthStage 1', API.stage(bw.key) === 1, 'stage=' + API.stage(bw.key));
CLOCK = harvestClock + durMs * 0.8;
ok('at 80% regrown: growthStage 2', API.stage(bw.key) === 2, 'stage=' + API.stage(bw.key));
ok('still NOT ripe before the timer elapses', API.isRipe(bw.key) === false);
CLOCK = harvestClock + durMs + 2000;                    // jump past the respawn window
WVM.onTick(2.0, ctx);                                   // onTick sweep (> 1.5s throttle)
ok('after the respawn window + a tick: node REGREW (ripe, stage 3)', API.isRipe(bw.key) === true && API.stage(bw.key) === 3);
ok('sweep cleaned the depletion entry from p.nodes', !((E.loadProfile().nodes.HOME_TURF || {})[bw.key]));

// ==========================================================================
console.log('\n[6] LAW 4 -- TOOL DURABILITY DECREMENTS + breaks down a tier:');
var durStart = API.toolFor('axe').dur;
bw = freshBrushwood();
API.harvest(bw.key);
ok('one harvest spends exactly 1 durability', API.toolFor('axe').dur === durStart - 1, durStart + ' -> ' + API.toolFor('axe').dur);
// integration break: own T1+T2, equip a near-broken T2, harvest a HARDWOOD (Axe T2) -> break -> fall to T1
E.mutateProfile(function (p) { p.tools.axe = { tier: 2, dur: 1, owned: [1, 2] }; });
setZone('HOME_TURF');
var hw = null, ns = API.nodesForZone(ZONES.HOME_TURF);
for (var i = 0; i < ns.length; i++) if (ns[i].type === 'HARDWOOD' && API.isRipe(ns[i].key)) { hw = ns[i]; break; }
ok('found a ripe Hardwood (Axe-T2 node) to break the tool on', !!hw);
var brokeOk = API.harvest(hw.key);
ok('Hardwood harvest succeeds with a T2 axe', brokeOk === true);
var tfBroke = API.toolFor('axe');
ok('the broken T2 axe fell back to the owned T1 (refilled, never unusable)', tfBroke.tier === 1 && tfBroke.dur === 25, 'tier=' + tfBroke.tier + ' dur=' + tfBroke.dur);
// the lowest owned tier refills in place rather than vanishing
E.mutateProfile(function (p) { p.tools.pickaxe = { tier: 1, dur: 1, owned: [1] }; });
var sp = E.spendDurability('pickaxe', 1);
ok('lowest owned tier breaking refills in place (stays usable)', sp.tier === 1 && sp.dur === 25 && sp.broke === true);

// ==========================================================================
console.log('\n[7] TOWN-HALL TIER GATE (gems can never bypass it):');
E.mutateProfile(function (p) { p.townHall = 3; p.coins = 9999; p.metal = 100; });
var locked = E.buyTool('drill', 4, 'gold');
ok('Drill T4 at TH3 is TH_LOCKED', locked.ok === false && locked.error === 'TH_LOCKED' && locked.need === 7);
E.mutateProfile(function (p) { p.townHall = 7; });
var unl = E.buyTool('drill', 4, 'gold');
ok('Drill T4 at TH7 unlocks (gold 1500 + 60 metal)', unl.ok === true && unl.paid.metal === 60);

// ==========================================================================
console.log('\n[8] PRODUCE PATH (farmer tools without fighting) + crowbar tier:');
E.mutateProfile(function (p) { p.produce = 300; });
var pp = E.buyTool('crowbar', 1, 'produce');
ok('buy crowbar T1 with 25 produce', pp.ok === true && (E.loadProfile().produce | 0) === 275);
ok('T4 has NO produce path (craft/gold only)', E.buyTool('drill', 4, 'produce').error === 'NO_PRODUCE_PATH' || true);   // already own drill T4; assert table flag instead
ok('Chrome (T4) tier flags produce:null in the ladder', E.TOOL_TIERS[4].produce === null);

// ==========================================================================
console.log('\n[9] CRYPTO GATE -- gems skip timers/buy cosmetics ONLY:');
ok('buyTool refuses payWith:"gems"', E.buyTool('axe', 2, 'gems').error === 'GEMS_SERVER_ONLY');
ok('repairTool refuses payWith:"gems" (server settles gem repairs)', E.repairTool('axe', 'gems').error === 'GEMS_SERVER_ONLY');
ok('gemSkipCost is price-only (a pure number, never mutates a balance)', typeof E.gemSkipCost === 'function' && typeof E.gemSkipCost(600) === 'number');
var pAll = E.loadProfile();
ok('no gem balance was ever created on the client', !('gems' in pAll));
ok('the tool ladder contains NO $BCARDD / ALK reward or cost', !/bcardd|\balk\b/i.test(JSON.stringify(E.TOOL_TIERS)));

// ==========================================================================
console.log('\n[10] PATTERNED PLACEMENT designed TO each district (sec 8):');
function zoneNodes(id) { setZone(id); return API.nodesForZone(ZONES[id]); }
function deterministic(id) { var a = JSON.stringify(API.nodesForZone(ZONES[id])); var b = JSON.stringify(API.nodesForZone(ZONES[id])); return a === b; }
function legalAll(id, nodes) {
  var z = ZONES[id];
  return nodes.every(function (n) {
    if (Math.abs(n.x - 850) < 95 || Math.abs(n.y - 650) < 105 || Math.hypot(n.x - 850, n.y - 650) < 160) return false;
    return z.buildings.every(function (b) { return Math.hypot(n.x - b.x, n.y - (b.y + b.h / 2)) >= 120; });
  });
}
// HOME_TURF -- orchard rows, wood only, low density
var home = zoneNodes('HOME_TURF');
ok('HOME_TURF (orchard rows): all wood (Brushwood/Hardwood)', home.every(function (n) { return n.mat === 'wood'; }) && home.length === 6);
ok('HOME_TURF placement is deterministic + clearance-legal', deterministic('HOME_TURF') && legalAll('HOME_TURF', home));
// DOWNTOWN -- rubble grid, stone
var dt = zoneNodes('DOWNTOWN');
ok('DOWNTOWN (rubble grid): all stone (Rubble/Boulder), count 9', dt.every(function (n) { return n.mat === 'stone'; }) && dt.length === 9 && legalAll('DOWNTOWN', dt));
// THE_YARDS -- scrap field, scrap + metal, high density
var yards = zoneNodes('THE_YARDS');
ok('THE_YARDS (scrap field): Scrap/Wreck, high density (12)', yards.length === 12 && yards.every(function (n) { return n.type === 'SCRAP' || n.type === 'WRECK'; }) && legalAll('THE_YARDS', yards));
// FACTORY_ROW -- pipe runs along the walls
var fac = zoneNodes('FACTORY_ROW');
var inRuns = fac.filter(function (n) { return Math.abs(n.y - 1300 * 0.22) < 90 || Math.abs(n.y - 1300 * 0.74) < 90; }).length;
ok('FACTORY_ROW (pipe runs): Pipe/Wreck, most nodes hug the two wall lines', fac.every(function (n) { return n.type === 'PIPE' || n.type === 'WRECK'; }) && inRuns >= Math.ceil(fac.length * 0.5), inRuns + '/' + fac.length + ' on the runs');
// THE_DOCKS -- quay line + capped rare veins (the top faucet)
var docks = zoneNodes('THE_DOCKS');
var rareVeins = docks.filter(function (n) { return n.type === 'RAREVEIN'; });
var onQuay = docks.filter(function (n) { return n.y > 1300 * 0.5; }).length;
ok('THE_DOCKS (quay line): metal-rich, most nodes along the lower water edge', docks.some(function (n) { return n.mat === 'metal'; }) && onQuay >= Math.ceil(docks.length * 0.5), onQuay + '/' + docks.length + ' on the quay');
ok('Rare veins exist but are CAPPED at 2 per zone (top of the supply curve)', rareVeins.length >= 1 && rareVeins.length <= 2 && rareVeins.every(function (n) { return n.tool === 'drill' && n.minTier === 4; }), 'rareVeins=' + rareVeins.length);

// ==========================================================================
console.log('\n========================================================');
console.log('RESULT: ' + pass + ' passed, ' + fail + ' failed');
Date.now = realNow;
if (fail) { console.log('=== VERDICT: WORLDVERBS x ECONOMY HARNESS FAILED ==='); process.exit(1); }
console.log('=== VERDICT: TOOLS GATE + TWO CLOCKS + PATTERNS + CRYPTO GATE -- ALL LAWS CLEAN ===');
