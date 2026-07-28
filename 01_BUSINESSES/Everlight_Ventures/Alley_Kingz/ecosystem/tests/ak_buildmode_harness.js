// ==========================================================================
// ALLEY KINGZ -- BUILDERS + GARDENS HARNESS (AK_RESOURCE_ECONOMY_DESIGN secs 5+6)
// ==========================================================================
// Proves, headless (no DOM, controllable clock), the buildmode.js economy layer
// against the design LAW, loading the REAL economy.js + _registry.js + buildmode.js
// (a localStorage shim makes the real AK_ECON persist in-process):
//
//   1. builderCap(TH) == the sec 5.1 cap table  [1,1,2,2,3,3,4,4,5,6]
//   2. builderSpeed(cardLvl,TH) matches the sec 5.3 grid; assigning a HIGHER-LEVEL
//      card to a builder raises the speed multiplier (-> shorter build time)
//   3. a build job CONSUMES a builder + completes ONLY on its timer (place is no
//      longer instant; a second build is refused while the only builder is busy;
//      advancing the clock past the timer finishes it + frees the builder + the
//      wall becomes a real obstacle)
//   4. a GARDEN grows through stages then YIELDS produce on harvest (flat trickle gone)
//   5. a builder on task 'tend' auto-harvests a ripe bed -> banks produce
//   6. gem-skip ladder (sec 7.3) + free <=2min auto-finish + parity (a paid skip
//      never fabricates gems with no server)
//   7. ZERO-STATE BYTE-IDENTICAL: init + ticks with no player action write nothing
//
// Usage: node ecosystem/tests/ak_buildmode_harness.js
// ==========================================================================
'use strict';
var ROOT = __dirname + '/../game';
global.window = global;

var pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name + (extra ? '  (' + extra + ')' : '')); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}
function near(a, b, eps) { return Math.abs(a - b) <= (eps == null ? 0.01 : eps); }

// ---- localStorage shim so the REAL economy.js persists across calls ----------
var STORE = {};
global.localStorage = {
  getItem: function (k) { return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
  setItem: function (k, v) { STORE[k] = String(v); },
  removeItem: function (k) { delete STORE[k]; }
};

// ---- controllable clock (buildmode + economy read Date.now()) ----------------
var NOW = 1700000000000;
var _RealDate = Date;
global.Date.now = function () { return NOW; };
function advance(ms) { NOW += ms; }

// ---- mock Canvas2D (every method no-op; draw paths must not throw) -----------
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

// ---- card index (factionId drives faction-affinity bonus) --------------------
function makeCards() {
  return {
    'Balboa':         { name: 'Balboa', factionId: 'boneguard_crew', rarity: 'Epic' },
    'Grit Bulldog':   { name: 'Grit Bulldog', factionId: 'boneguard_crew', rarity: 'Rare' },
    'Leash Runner':   { name: 'Leash Runner', factionId: 'leashbreak_tactix', rarity: 'Rare' }   // produce-affinity faction
  };
}

// ---- mock ctx (mirrors index.html AK_CTX surface buildmode uses) -------------
var banners = [];
function makeCtx(AK_ECON) {
  var ZONES = { HOME_TURF: { id: 'HOME_TURF', name: 'THE LOT', ground: 'uptown', buildings: [] } };
  var g = mockG();
  return {
    AK_ECON: AK_ECON, econ: AK_ECON,
    cards: function () { return makeCards(); },
    ZONES: ZONES, zoneId: 'HOME_TURF', activeZone: ZONES.HOME_TURF,
    me: { x: 850, y: 650, r: 22 }, cam: { x: 0, y: 0 },
    showBanner: function (t) { banners.push(t); },
    world: {
      g: g, W: 390, H: 780, WORLD_W: 1700, WORLD_H: 1300,
      wx: function (x) { return x; }, wy: function (y) { return y; }, distToMe: function () { return 0; }
    },
    currency: { get: function () { return 0; }, grant: function () { return null; } }
  };
}

// ==========================================================================
// LOAD (real order: registry -> economy -> buildmode)
// ==========================================================================
require(ROOT + '/systems/_registry.js');
require(ROOT + '/economy.js');
require(ROOT + '/systems/buildmode.js');

ok('AK_ECON loaded (real economy.js)', !!(global.AK_ECON && AK_ECON.mutateProfile));
ok('AK_BUILDMODE registered', !!(global.AK_BUILDMODE && AK_BUILDMODE.builderCap && AK_BUILDMODE.assignBuilder));
ok('AK_SYSTEMS has buildmode module', !!(global.AK_SYSTEMS && AK_SYSTEMS.get('buildmode')));

var BMOD = AK_SYSTEMS.get('buildmode');
var ctx = makeCtx(global.AK_ECON);
global.AK_CTX = ctx;
AK_SYSTEMS.initAll(ctx);
function tick(seconds) { AK_SYSTEMS.tickAll(seconds == null ? 0.05 : seconds, ctx); }
function P() { return AK_ECON.loadProfile(); }

// helper: set profile fields
function setProfile(fn) { AK_ECON.mutateProfile(fn); AK_BUILDMODE.refresh(); }

// ==========================================================================
// (1) BUILDER CAP TABLE  (sec 5.1)
// ==========================================================================
console.log('\n[1] builder cap per Town Hall (sec 5.1 cap TABLE: 1,1,2,2,3,3,4,4,5,6):');
var CAP_EXPECT = [1, 1, 2, 2, 3, 3, 4, 4, 5, 6];   // TH1..TH10
var capOk = true, capStr = [];
for (var th = 1; th <= 10; th++) { var c = AK_BUILDMODE.builderCap(th); capStr.push('TH' + th + '=' + c); if (c !== CAP_EXPECT[th - 1]) capOk = false; }
ok('builderCap matches the design table', capOk, capStr.join(' '));

// ==========================================================================
// (2) BUILDER SPEED GRID  (sec 5.2 / 5.3) + assigning a higher-level card
// ==========================================================================
console.log('\n[2] builderSpeed grid + higher-level dog = faster:');
ok('builderSpeed(1,1) == 1.00', near(AK_BUILDMODE.builderSpeed(1, 1), 1.00));
ok('builderSpeed(5,5) == 1.58', near(AK_BUILDMODE.builderSpeed(5, 5), 1.584, 0.005), AK_BUILDMODE.builderSpeed(5, 5).toFixed(3));
ok('builderSpeed(10,10) == 2.49', near(AK_BUILDMODE.builderSpeed(10, 10), 2.494, 0.005), AK_BUILDMODE.builderSpeed(10, 10).toFixed(3));
ok('higher card level raises the multiplier', AK_BUILDMODE.builderSpeed(10, 5) > AK_BUILDMODE.builderSpeed(1, 5));

// give the player materials + TH5 (cap 3) + an owned, leveled dog
setProfile(function (p) {
  p.coins = 5000; p.wood = 200; p.stone = 200; p.metal = 200;
  p.townHall = 5; p.builds_seeded = 1;
  p.owned = ['Balboa', 'Grit Bulldog', 'Leash Runner'];
  p.cardLvls = { 'Balboa': 5, 'Grit Bulldog': 1, 'Leash Runner': 3 };
});
// assign a Lv5 dog to builder slot 0, then measure the build time vs an unmanned baseline
var unmannedDur = AK_BUILDMODE.baseBuildMs(AK_BUILDMODE.STRUCT.WALL) / AK_BUILDMODE.builderSpeed(1, 5);
var lvl5Dur = AK_BUILDMODE.baseBuildMs(AK_BUILDMODE.STRUCT.WALL) / AK_BUILDMODE.builderSpeed(5, 5);
ok('a Lv5 builder builds a wall faster than an unmanned slot', lvl5Dur < unmannedDur, Math.round(lvl5Dur) + 'ms < ' + Math.round(unmannedDur) + 'ms');
var asg = AK_BUILDMODE.assignBuilder(0, 'Balboa', 'build', 'HOME_TURF');
ok('assignBuilder(slot0, Balboa) ok', asg.ok && P().crew['0'].card === 'Balboa');
ok('assign rejects a card the player does not own', !AK_BUILDMODE.assignBuilder(0, 'Ghost Dog', 'build').ok);
ok('assign rejects a slot beyond the TH cap (slot 5 @ TH5 cap=3)', !AK_BUILDMODE.assignBuilder(5, 'Balboa', 'build').ok);

// ==========================================================================
// (3) BUILD JOB CONSUMES A BUILDER + COMPLETES ON ITS TIMER
// ==========================================================================
console.log('\n[3] placement is a timed builder job (not instant):');
// drop to TH1 so cap == 1 (one builder) to prove the throttle
setProfile(function (p) { p.townHall = 1; p.crew = {}; p.builds = []; });
var st0 = AK_BUILDMODE.builderState();
ok('TH1 -> 1 builder slot, 1 free', st0.cap === 1 && st0.free === 1);

var placed = AK_BUILDMODE.place('WALL', 850, 1000);
var pb = P();
ok('place() pushed an UNDER-CONSTRUCTION wall (b.uc set, not instant)', placed && pb.builds.length === 1 && !!pb.builds[0].uc, 'dur=' + (pb.builds[0].uc.dur) + 'ms');
ok('the build consumed the only builder (0 free)', AK_BUILDMODE.builderState().free === 0);
var wallDur = pb.builds[0].uc.dur;

// a second build must be refused -- all builders busy
banners.length = 0;
var placed2 = AK_BUILDMODE.place('STONE', 850, 1100);
ok('second build refused while the only builder is busy', !placed2 && P().builds.length === 1 && banners.indexOf('ALL BUILDERS BUSY') >= 0);

// not done before the timer
advance(wallDur - 1000); tick(0.05);
ok('still under construction 1s before timer', !!P().builds[0].uc);
ok('builder still busy', AK_BUILDMODE.builderState().free === 0);

// completes exactly when the timer elapses (onTick reconcile)
advance(2000); tick(0.05);
var done = P();
ok('build COMPLETES on its timer (b.uc cleared)', !done.builds[0].uc);
ok('builder freed after completion (1 free again)', AK_BUILDMODE.builderState().free === 1);

// now a second build is allowed
ok('a new build is allowed once the builder is free', AK_BUILDMODE.place('STONE', 850, 1100));

// ==========================================================================
// (4) GARDEN GROW CYCLE -> PRODUCE  (sec 6)
// ==========================================================================
console.log('\n[4] garden plant -> grow stages -> harvest -> produce:');
// fresh slate, TH1, finish any pending job so a builder is free to build the bed
setProfile(function (p) { p.townHall = 1; p.crew = {}; p.builds = []; p.produce = 0; p.coins = 5000; });
ok('place a GARDEN bed', AK_BUILDMODE.place('GARDEN', 700, 700));
var bedDur = P().builds[0].uc.dur;
advance(bedDur + 100); tick(0.05);
ok('garden bed finished building', !P().builds[0].uc);

// plant Catnip (TH1, 2min, +3 produce, 5g seed)
var plant = AK_BUILDMODE.plantGarden(0, 'catnip');
var gb = P().builds[0];
ok('planted Catnip (b.crop + b.plantedAt set, 5g seed spent)', plant.ok && gb.crop === 'catnip' && gb.plantedAt === NOW && P().coins === 4995);
ok('stage 0 right after planting', AK_BUILDMODE.gardenStage(P().builds[0]) === 0 && !AK_BUILDMODE.gardenRipe(P().builds[0]));

advance(60000); // half of 120s
ok('stage advances to 2 at the half-way mark', AK_BUILDMODE.gardenStage(P().builds[0]) === 2 && !AK_BUILDMODE.gardenRipe(P().builds[0]));

// not ripe yet -> harvest refused
ok('harvest refused before ripe', !AK_BUILDMODE.harvestGarden(0, null).ok);

advance(60000); // full 120s -> ripe
ok('garden ripe at grow-time', AK_BUILDMODE.gardenRipe(P().builds[0]));
var harv = AK_BUILDMODE.harvestGarden(0, null);
ok('harvest yields +3 produce (Catnip table)', harv.ok && harv.produce === 3 && P().produce === 3);
ok('bed reset to empty after harvest (crop cleared)', !P().builds[0].crop && !P().builds[0].plantedAt);

// TH gate: Pumpkin needs TH2
ok('plant refused when crop is TH-locked (Pumpkin @ TH1)', !AK_BUILDMODE.plantGarden(0, 'pumpkin').ok);

// faction affinity: a leashbreak dog gives +10% (corn 9 -> round(9.9)=10)
ok('faction affinity is a +10% produce edge (Leash Runner on corn: 9 -> 10)',
  (function () { setProfile(function (p) { p.builds[0].crop = 'corn'; p.builds[0].plantedAt = NOW - CORN_GROW(); });
    var r = AK_BUILDMODE.harvestGarden(0, 'Leash Runner'); return r.ok && r.produce === 10; })());
function CORN_GROW() { return AK_BUILDMODE.CROPS.corn.grow; }

// ==========================================================================
// (5) BUILDER ON 'tend' AUTO-HARVESTS A RIPE BED
// ==========================================================================
console.log('\n[5] a builder on task=tend auto-harvests a ripe bed:');
setProfile(function (p) {
  p.townHall = 5; p.coins = 5000; p.produce = 0; p.builds = []; p.crew = {};
  // a pre-built (complete) garden bed with a ripe Catnip already in it
  p.builds.push({ type: 'GARDEN', x: 700, y: 700, hp: 0, maxHp: 0, zone: 'HOME_TURF', t: NOW, crop: 'catnip', plantedAt: NOW - 130000 });
});
ok('bed is ripe and produce starts at 0', AK_BUILDMODE.gardenRipe(P().builds[0]) && P().produce === 0);
// station builder slot 1 on 'tend' (slot 0 stays free for builds)
AK_BUILDMODE.assignBuilder(1, 'Grit Bulldog', 'tend', 'HOME_TURF');
ok('tend slot is STATIONED (occupies a builder)', AK_BUILDMODE.builderState().stationed === 1);
// drive ticks past the tend period (3s / builderSpeed) -> it harvests
var prevProduce = P().produce;
for (var t5 = 0; t5 < 30; t5++) { tick(0.5); }
ok('tend auto-harvested the ripe bed -> produce banked', P().produce > prevProduce, 'produce=' + P().produce);

// ==========================================================================
// (6) GEM-SKIP LADDER (sec 7.3) + free <=2min finish + parity guard
// ==========================================================================
console.log('\n[6] gem-skip ladder + free auto-finish + crypto parity:');
// SHARED CONTRACT unit = SECONDS remaining (design sec 7.3): 2m->0, 10m->2, 30m->5, 1h->9, 4h->24, 12h->60, 24h->100
var ladder = [[60, 0], [120, 0], [600, 2], [1800, 5], [3600, 9], [14400, 24], [43200, 60], [86400, 100]];
var ladderOk = true, ls = [];
ladder.forEach(function (pair) { var got = AK_BUILDMODE.gemSkipCost(pair[0]); ls.push(pair[0] + 's->' + got); if (got !== pair[1]) ladderOk = false; });
ok('gemSkipCost ladder matches the design table (seconds)', ladderOk, ls.join(' '));

// free band: a freshly-placed 30s wall has <=2min remaining -> skip is FREE -> instant
setProfile(function (p) { p.townHall = 1; p.crew = {}; p.builds = []; });
AK_BUILDMODE.place('WALL', 900, 1000);
var slot = P().builds[0].uc.slot;
var freeSkip = AK_BUILDMODE.skipBuildJob(slot);
ok('a <=2min job skips FREE (auto-finish) -> built instantly', freeSkip.ok && freeSkip.free === true && !P().builds[0].uc && AK_BUILDMODE.builderState().free === 1);

// paid band parity: inject a long (6h) job; with no server gem ledger the skip must NOT complete it
var SIXH = 21600000;   // 6h -> design ladder <=12h band -> 60 gems
setProfile(function (p) {
  p.townHall = 1; p.crew = { '0': { card: null, task: 'build', started: NOW, dur: SIXH } };
  p.builds = [{ type: 'WALL', x: 900, y: 1200, hp: 200, maxHp: 200, zone: 'HOME_TURF', t: NOW, uc: { slot: 0, t0: NOW, dur: SIXH } }];
});
var paidSkip = AK_BUILDMODE.skipBuildJob(0);
ok('a paid gem-skip is SERVER-gated (never fabricates gems client-side)', !paidSkip.ok && paidSkip.error === 'SERVER_REQUIRED' && paidSkip.cost === 60 && !!P().builds[0].uc, 'cost=' + paidSkip.cost);
ok('ctx.currency.grant("gems") stays a no-op', ctx.currency.grant('gems', 999) === null);

// ==========================================================================
// (7) ZERO-STATE BYTE-IDENTICAL  (no player action -> no profile writes)
// ==========================================================================
console.log('\n[7] zero-state byte-identical (init + ticks write nothing):');
// brand-new profile, freshly shaped by the REAL economy.js
STORE = {}; AK_BUILDMODE.refresh();
var freshA = JSON.stringify(AK_ECON.loadProfile());     // ensureShape applied
// re-init + run many ticks with NO player action
AK_SYSTEMS.initAll(ctx);
for (var z = 0; z < 20; z++) { tick(0.1); advance(50); }
var freshB = JSON.stringify(AK_ECON.loadProfile());
ok('no crew/produce/uc/crop written by init+tick on a fresh profile', freshA === freshB, freshA === freshB ? 'identical' : 'DIFF');
var freshObj = AK_ECON.loadProfile();
// economy.js ensureShape owns p.produce (default 0) + p.tools; buildmode must add NOTHING --
// no p.crew, no build.uc, no crop -- until the player assigns/builds/plants.
ok('buildmode writes no p.crew (and produce stays at the economy default 0)', freshObj.crew === undefined && (freshObj.produce | 0) === 0);

// ==========================================================================
console.log('\n==========================================================');
console.log('  ' + pass + ' passed, ' + fail + ' failed');
console.log('==========================================================');
process.exit(fail ? 1 : 0);
