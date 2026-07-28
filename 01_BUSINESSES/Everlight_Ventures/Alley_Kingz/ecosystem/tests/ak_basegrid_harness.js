// ==========================================================================
// ALLEY KINGZ -- BASE GRID + INVENTORY EDITING HARNESS   (AK-BASEGRID 2026-07-18)
// ==========================================================================
// Proves the game/systems/basegrid.js DATA + RULES layer headless, against the
// REAL game/economy.js (real ensureShape, real loadProfile/mutateProfile, real
// localStorage persistence via a shim) and the REAL game/systems/buildmode.js
// STRUCT catalog. No invented mocks of the code under test.
//
//   1. world <-> tile round-trip is exact for every footprint parity
//   2. occupancy() is built from a REAL p.builds[] fixture written by the REAL
//      AK_ECON.mutateProfile, and the tile map matches the placements
//   3. canPlace accepts a legal drop and REJECTS overlap / bounds / clearance /
//      adjacency with the right reason
//   4. the tray flow: remove into inventory, clear the WHOLE base, rebuild from
//      the tray -- nothing lost, grouped by type and level
//   5. moveAll into a wall is rejected ATOMICALLY (zero half-applied writes)
//   6. rotateAll 90deg about the board center, 4x = identity
//   7. layout slots save/load/list through mutateProfile
//   8. scout view hides traps
//   9. zero-state: reading the module writes nothing to the profile
//
// Usage: node ecosystem/tests/ak_basegrid_harness.js
// ==========================================================================
'use strict';
var ROOT = __dirname + '/../game';
global.window = global;

var pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name + (extra ? '  (' + extra + ')' : '')); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}
function head(s) { console.log('\n=== ' + s + ' ==='); }

// ---- localStorage shim so the REAL economy.js persists across calls ---------
var STORE = {};
global.localStorage = {
  getItem: function (k) { return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
  setItem: function (k, v) { STORE[k] = String(v); },
  removeItem: function (k) { delete STORE[k]; }
};

// ---- load the REAL modules --------------------------------------------------
require(ROOT + '/economy.js');
require(ROOT + '/systems/_registry.js');            // so buildmode registers
require(ROOT + '/systems/buildmode.js');            // for the REAL STRUCT catalog
var BG = require(ROOT + '/systems/basegrid.js');

var ECON = global.AK_ECON;
ok('real AK_ECON loaded', !!(ECON && ECON.loadProfile && ECON.mutateProfile));
ok('real AK_BUILDMODE STRUCT loaded', !!(global.AK_BUILDMODE && global.AK_BUILDMODE.STRUCT),
   'types=' + Object.keys(global.AK_BUILDMODE.STRUCT || {}).length);
ok('basegrid is the REAL module export', BG === global.AK_BASEGRID);

BG.configure({ econ: ECON, zone: 'HOME_TURF', cols: 40, rows: 40, tile: 64, originX: 0, originY: 0 });

// ==========================================================================
head('1. WORLD <-> TILE ROUND-TRIP (both footprint parities)');
// ==========================================================================
(function () {
  var cases = [
    ['WALL', 1, 1], ['TOWER', 3, 3], ['HUT', 2, 2], ['TOWNHALL', 4, 4], ['GATE', 2, 1]
  ];
  var allExact = true, report = [];
  cases.forEach(function (c) {
    var type = c[0];
    for (var rot = 0; rot < 4; rot++) {
      for (var tx = 0; tx <= 36; tx += 7) {
        for (var ty = 0; ty <= 36; ty += 11) {
          var w = BG.tileToWorld(type, tx, ty, rot);
          var back = BG.worldToTile(type, w.x, w.y, rot);
          if (back.tx !== tx || back.ty !== ty) { allExact = false; report.push(type + ' rot' + rot + ' ' + tx + ',' + ty); }
        }
      }
    }
    var f = BG.footprint(type, 0);
    ok('footprint ' + type + ' = ' + c[1] + 'x' + c[2], f.w === c[1] && f.h === c[2]);
  });
  ok('tile -> world -> tile is EXACT for every case', allExact, report.slice(0, 3).join(' '));

  // parity is real and reported, not hidden
  ok('snapsClean(HUT 2x2) true  -> buildmode.place() snap is a no-op', BG.snapsClean('HUT', 0) === true,
     'center=' + BG.tileToWorld('HUT', 4, 4, 0).x + ' (64 lattice)');
  ok('snapsClean(WALL 1x1) false -> must be written by basegrid, not place()', BG.snapsClean('WALL', 0) === false,
     'center=' + BG.tileToWorld('WALL', 4, 4, 0).x + ' (lattice+32)');

  // tolerant inverse: a legacy 64-lattice center still resolves to a tile
  var legacy = BG.worldToTile('WALL', 640, 640, 0);
  ok('legacy 64-lattice center resolves to a tile', Number.isInteger(legacy.tx) && Number.isInteger(legacy.ty),
     'x640 -> tx' + legacy.tx);

  // rot parity matches buildmode's rotSwap exactly
  var g0 = BG.footprint('GATE', 0), g1 = BG.footprint('GATE', 1);
  ok('odd rot swaps w<->h (matches buildmode rotSwap)', g0.w === g1.h && g0.h === g1.w, '2x1 -> 1x2');
})();

// ==========================================================================
head('2. OCCUPANCY FROM A REAL p.builds[] FIXTURE');
// ==========================================================================
// Written through the REAL AK_ECON.mutateProfile, in buildmode's exact entry shape.
var FIXTURE = [
  { type: 'TOWNHALL', tx: 18, ty: 18, rot: 0 },   // 4x4 core, gap 1
  { type: 'HUT',      tx: 10, ty: 10, rot: 0 },   // 2x2
  { type: 'HUT',      tx: 13, ty: 10, rot: 0 },   // 2x2
  { type: 'TOWER',    tx: 24, ty: 12, rot: 0 },   // 3x3
  { type: 'STORAGE_GOLD', tx: 8, ty: 20, rot: 0 },// 3x3
  { type: 'WALL',     tx: 16, ty: 16, rot: 0 },   // 1x1
  { type: 'WALL',     tx: 17, ty: 16, rot: 0 },   // 1x1 flush neighbour, legal
  { type: 'TRAP_BOMB',tx: 22, ty: 22, rot: 0 }    // 1x1 hidden
];
(function () {
  ECON.mutateProfile(function (p) {
    p.builds = [];
    FIXTURE.forEach(function (f) {
      var w = BG.tileToWorld(f.type, f.tx, f.ty, f.rot);
      var e = { type: f.type, x: w.x, y: w.y, hp: 200, maxHp: 200, zone: 'HOME_TURF', t: 1700000000000 };
      if (f.rot) e.rot = f.rot;
      p.builds.push(e);                                   // buildmode's EXACT schema
    });
  });
  var p = ECON.loadProfile();
  ok('fixture written to the real p.builds[]', p.builds.length === FIXTURE.length, p.builds.length + ' entries');
  ok('entries carry buildmode fields (type,x,y,hp,maxHp,zone,t)',
     ['type', 'x', 'y', 'hp', 'maxHp', 'zone', 't'].every(function (k) { return p.builds[0][k] !== undefined; }));

  var occ = BG.occupancy();
  var expectTiles = FIXTURE.reduce(function (n, f) { var fp = BG.footprint(f.type, f.rot); return n + fp.w * fp.h; }, 0);
  ok('occupancy cell count matches placements', occ.count === FIXTURE.length, occ.count + '/' + FIXTURE.length);
  ok('occupancy tile count = sum of footprints', Object.keys(occ.map).length === expectTiles,
     Object.keys(occ.map).length + ' tiles, expected ' + expectTiles);
  ok('no entries fell off the board', occ.offGrid.length === 0);

  // spot-check: the Town Hall really owns all 16 of its tiles
  var thAll = true;
  for (var j = 0; j < 4; j++) for (var i = 0; i < 4; i++) {
    var c = occ.map[BG.key(18 + i, 18 + j)];
    if (!c || c.type !== 'TOWNHALL') thAll = false;
  }
  ok('TOWNHALL owns all 16 of its tiles', thAll);
  ok('a tile just outside TOWNHALL is free', !occ.map[BG.key(22, 18)]);

  console.log('\n  --- TILE MAP (rows 8..26, cols 6..30) ---');
  var full = BG.tileMap().split('\n');
  for (var r = 8; r <= 26; r++) console.log('  ' + String(r).padStart(2) + ' ' + full[r].slice(6, 31));
  console.log('  legend  T=core h=hut D=defense S=storage #=wall ^=trap -=free');
})();

// ==========================================================================
head('3. canPlace -- ACCEPT + EVERY REJECTION REASON');
// ==========================================================================
(function () {
  var a = BG.canPlace('HUT', 4, 4, 0);
  ok('legal drop on empty ground accepted', a.ok === true, 'tiles=' + a.tiles.length);

  var b = BG.canPlace('HUT', 10, 10, 0);
  ok('exact overlap REJECTED', b.ok === false && b.reason === 'SPOT_TAKEN', b.reason + ' vs ' + (b.at && b.at.type));

  var c = BG.canPlace('TOWER', 19, 19, 0);
  ok('partial overlap on TOWNHALL REJECTED', c.ok === false, c.reason);

  var d = BG.canPlace('HUT', 11, 10, 0);
  ok('1-tile-offset overlap REJECTED (not just exact match)', d.ok === false && d.reason === 'SPOT_TAKEN', d.reason);

  var e1 = BG.canPlace('TOWNHALL', 38, 4, 0);
  ok('off the right edge REJECTED (4x4 at tx38 needs 38..41)', e1.ok === false && e1.reason === 'OUT_OF_BOUNDS', e1.reason);
  var e2 = BG.canPlace('WALL', -1, 5, 0);
  ok('negative tile REJECTED', e2.ok === false && e2.reason === 'OUT_OF_BOUNDS', e2.reason);
  var e3 = BG.canPlace('TOWNHALL', 36, 36, 0);
  ok('exactly flush to the far corner ACCEPTED (36..39 of 40)', e3.ok === true);

  // clearance: TOWNHALL declares gap 1, so nothing may sit flush against it
  var f1 = BG.canPlace('WALL', 17, 18, 0);       // flush to TH left edge (TH starts tx18)
  ok('flush against TOWNHALL REJECTED by its gap:1', f1.ok === false && f1.reason === 'NEEDS_CLEARANCE', f1.reason + ' gap=' + f1.gap);
  var f2 = BG.canPlace('WALL', 16, 18, 0);       // one tile further out
  ok('one tile clear of TOWNHALL ACCEPTED', f2.ok === true);

  // walls have gap 0, so flush walls are legal (this is the CoC rule)
  var g1 = BG.canPlace('WALL', 18, 16, 0);
  ok('wall flush beside a wall ACCEPTED (gap 0)', g1.ok === true);

  // adjacency: GATE must touch a wall
  var h1 = BG.canPlace('GATE', 4, 30, 0);
  ok('GATE with no wall nearby REJECTED', h1.ok === false && h1.reason === 'NEEDS_ADJACENT', h1.reason + ' need=' + (h1.need || []).join(','));
  // NOTE: GATE at (16,17) is correctly rejected -- it lands 1 tile from the TOWNHALL at
  // (18,18), whose gap:1 outranks the gate's own gap:0. Proves neighbour gaps are honoured.
  var h1b = BG.canPlace('GATE', 16, 17, 0);
  ok('GATE beside a wall but inside TOWNHALL gap REJECTED', h1b.ok === false && h1b.reason === 'NEEDS_CLEARANCE', h1b.reason);
  var h2 = BG.canPlace('GATE', 15, 17, 0);       // touches WALL(16,16), clear of the TOWNHALL ring
  ok('GATE touching a wall ACCEPTED', h2.ok === true, h2.reason || 'ok');

  var i1 = BG.canPlace('NOT_A_THING', 5, 5, 0);
  ok('unknown type REJECTED', i1.ok === false && i1.reason === 'BAD_TYPE');

  // exclude: a piece being dragged must not collide with the copy it is leaving
  var occNo = BG.occupancy(null, null, { exclude: 1 });   // idx 1 = HUT at 10,10
  var j1 = BG.canPlace('HUT', 10, 10, 0, { occ: occNo });
  ok('dragging a piece onto its own tiles ACCEPTED via exclude', j1.ok === true);

  var hl = BG.highlight('HUT', 10, 10, 0);
  ok('highlight() reports invalid for the renderer', hl.ok === false && hl.tiles.length === 4,
     'world box ' + hl.world.w + 'x' + hl.world.h);
})();

// ==========================================================================
head('4. INVENTORY TRAY -- remove, clear the whole base, rebuild');
// ==========================================================================
(function () {
  var before = ECON.loadProfile().builds.length;

  // find the TOWER index in the real array
  var idx = ECON.loadProfile().builds.findIndex(function (b) { return b.type === 'TOWER'; });
  var r = BG.toInventory(idx);
  ok('toInventory removes ONE structure into the tray', r.ok === true && !!r.iid, r.type + ' -> ' + r.iid);
  var p1 = ECON.loadProfile();
  ok('p.builds shrank by exactly 1', p1.builds.length === before - 1, p1.builds.length);
  ok('p.baseTray grew by exactly 1', (p1.baseTray || []).length === 1);
  ok('tray item kept hp/maxHp (nothing lost)', p1.baseTray[0].hp === 200 && p1.baseTray[0].maxHp === 200);
  ok('tray item has NO x/y/zone (placed OR trayed, never both)',
     p1.baseTray[0].x === undefined && p1.baseTray[0].y === undefined && p1.baseTray[0].zone === undefined);
  ok('the TOWER tiles are now free', !BG.occupancy().map[BG.key(24, 12)]);

  // THE KEY MOVE: clear the entire base into the tray in one pass
  var cl = BG.clearAll();
  var p2 = ECON.loadProfile();
  ok('clearAll emptied the zone', p2.builds.filter(function (b) { return b.zone === 'HOME_TURF'; }).length === 0,
     'moved=' + cl.moved);
  ok('every structure survived in the tray', p2.baseTray.length === FIXTURE.length,
     p2.baseTray.length + ' of ' + FIXTURE.length);
  ok('empty board occupancy is empty', BG.occupancy().count === 0);

  var inv = BG.inventory();
  // 8 structures collapse into 6 stacks (2 HUTs stack, 2 WALLs stack)
  ok('inventory groups by type and level', inv.total === FIXTURE.length && inv.groups.length === 6,
     inv.groups.map(function (g) { return g.type + 'x' + g.count; }).join(' '));
  var hutG = inv.groups.filter(function (g) { return g.type === 'HUT'; })[0];
  ok('the two HUTs stack into one group of 2', !!hutG && hutG.count === 2 && hutG.lvl === 1);

  // rebuild from scratch in a DIFFERENT arrangement, proving nothing was lost
  var placedBack = 0, rejected = 0;
  BG.inventory().groups.forEach(function (g) {
    g.iids.forEach(function (iid) {
      var t = BG.footprint(g.type, 0), put = false;
      for (var ty = 2; ty < 36 && !put; ty += Math.max(2, t.h + 1)) {
        for (var tx = 2; tx < 36 && !put; tx += Math.max(2, t.w + 1)) {
          var res = BG.fromInventory(iid, tx, ty, 0);
          if (res.ok) { placedBack++; put = true; }
        }
      }
      if (!put) rejected++;
    });
  });
  var p3 = ECON.loadProfile();
  ok('every trayed structure was placed back', placedBack === FIXTURE.length && rejected === 0,
     placedBack + ' placed, ' + rejected + ' stuck');
  ok('tray is empty again', p3.baseTray.length === 0);
  ok('p.builds is whole again', p3.builds.length === FIXTURE.length);
  ok('rebuilt entries are buildmode-shaped (zone + world x/y restored)',
     p3.builds.every(function (b) { return b.zone === 'HOME_TURF' && isFinite(b.x) && isFinite(b.y) && b.maxHp === 200; }));
  ok('rebuilt occupancy is consistent (no overlap slipped through)',
     Object.keys(BG.occupancy().map).length === FIXTURE.reduce(function (n, f) { var fp = BG.footprint(f.type, 0); return n + fp.w * fp.h; }, 0));

  var bad = BG.fromInventory('i9999', 5, 5, 0);
  ok('fromInventory on a missing item REJECTED', bad.ok === false && bad.error === 'NO_ITEM');
})();

// ==========================================================================
head('5. moveAll -- ATOMIC REJECTION INTO A WALL');
// ==========================================================================
(function () {
  // deterministic layout hugging the left/top edge so a shift walks into the wall
  ECON.mutateProfile(function (p) {
    p.builds = [];
    [['TOWNHALL', 0, 0], ['HUT', 6, 2], ['WALL', 5, 8], ['TOWER', 10, 10]].forEach(function (f) {
      var w = BG.tileToWorld(f[0], f[1], f[2], 0);
      p.builds.push({ type: f[0], x: w.x, y: w.y, hp: 200, maxHp: 200, zone: 'HOME_TURF', t: 1700000000000 });
    });
  });
  function snapshot() {
    return ECON.loadProfile().builds.map(function (b) { return b.type + '@' + b.x + ',' + b.y; }).join(' | ');
  }
  var before = snapshot();
  console.log('  before: ' + before);

  var okMove = BG.moveAll(3, 3);
  ok('legal moveAll(+3,+3) applied', okMove.ok === true && okMove.moved === 4, 'moved=' + okMove.moved);
  var afterGood = ECON.loadProfile().builds.map(function (b) { return BG.entryTile(b); });
  ok('every anchor shifted by exactly +3,+3',
     afterGood[0].tx === 3 && afterGood[0].ty === 3 && afterGood[3].tx === 13 && afterGood[3].ty === 13,
     'TH now ' + afterGood[0].tx + ',' + afterGood[0].ty);

  BG.moveAll(-3, -3);   // back to the edge
  var atWall = snapshot();
  ok('moved back to the edge', atWall === before);

  // NOW walk into the wall: TOWNHALL is at tx0, so -1 pushes it to -1 (out of bounds)
  var dry = BG.moveAll(-1, 0, { dryRun: true });
  ok('dryRun pre-check catches the wall', dry.ok === false && dry.error === 'OUT_OF_BOUNDS', dry.error + ' on ' + dry.type);

  var bad = BG.moveAll(-1, 0);
  ok('moveAll into the wall REJECTED', bad.ok === false && bad.error === 'OUT_OF_BOUNDS', bad.error);
  ok('moveAll reported ZERO pieces moved', bad.moved === 0);
  var after = snapshot();
  ok('ATOMIC: not one structure moved (byte-identical layout)', after === before);
  console.log('  after rejected move: ' + after);
  ok('the far pieces did NOT slide either (no half-apply)',
     ECON.loadProfile().builds[3].x === BG.tileToWorld('TOWER', 10, 10, 0).x);

  // and the same on the far edge. After +25 the TOWER 3x3 anchors at (35,35) -> spans
  // 35..37 of 40, so +2 is still LEGAL (proved below) and only +4 runs off the board.
  BG.moveAll(25, 25);
  var edge = snapshot();
  var legalEdge = BG.moveAll(2, 0);
  ok('a shift that still fits ACCEPTED at the far edge', legalEdge.ok === true, 'TOWER 37..39 of 40');
  BG.moveAll(-2, 0);
  var bad2 = BG.moveAll(4, 0);
  ok('moveAll off the FAR edge REJECTED', bad2.ok === false && bad2.error === 'OUT_OF_BOUNDS', bad2.error + ' on ' + bad2.type);
  ok('far-edge rejection is ATOMIC too', snapshot() === edge);
  BG.moveAll(-25, -25);
})();

// ==========================================================================
head('6. rotateAll -- 90deg about the board center');
// ==========================================================================
(function () {
  ECON.mutateProfile(function (p) {
    p.builds = [];
    [['TOWNHALL', 2, 2, 0], ['HUT', 10, 4, 0], ['GATE', 20, 30, 0], ['WALL', 35, 8, 0]].forEach(function (f) {
      var w = BG.tileToWorld(f[0], f[1], f[2], f[3]);
      var e = { type: f[0], x: w.x, y: w.y, hp: 200, maxHp: 200, zone: 'HOME_TURF', t: 1700000000000 };
      if (f[3]) e.rot = f[3];
      p.builds.push(e);
    });
  });
  function tiles() {
    return ECON.loadProfile().builds.map(function (b) { var a = BG.entryTile(b); return b.type + ':' + a.tx + ',' + a.ty + 'r' + (b.rot || 0); }).join(' ');
  }
  var t0 = tiles();
  console.log('  rot0: ' + t0);
  var r1 = BG.rotateAll(1);
  ok('rotateAll(cw) applied', r1.ok === true && r1.moved === 4);
  console.log('  rot1: ' + tiles());
  // TOWNHALL 4x4 at (2,2) on a 40 board -> CW -> (40-2-4, 2) = (34,2)
  var th = BG.entryTile(ECON.loadProfile().builds[0]);
  ok('TOWNHALL(2,2) 4x4 -> CW -> (34,2)', th.tx === 34 && th.ty === 2, th.tx + ',' + th.ty);
  ok('rotated pieces stay on the board', BG.occupancy().offGrid.length === 0);
  BG.rotateAll(1); BG.rotateAll(1); BG.rotateAll(1);
  ok('4x rotateAll(cw) returns to the identity layout', tiles() === t0, tiles() === t0 ? 'exact' : tiles());

  var back = BG.rotateAll(1); BG.rotateAll(-1);
  ok('rotateAll(ccw) undoes rotateAll(cw)', tiles() === t0);

  var sq = BG.config();
  ok('square board required for rotateAll', sq.cols === sq.rows);
  BG.configure({ cols: 40, rows: 30 });
  var nonsq = BG.rotateAll(1);
  ok('non-square board REJECTED (rotation is not a bijection there)', nonsq.ok === false && nonsq.error === 'NON_SQUARE_GRID');
  BG.configure({ cols: 40, rows: 40 });
})();

// ==========================================================================
head('7. LAYOUT SLOTS -- all through AK_ECON.mutateProfile');
// ==========================================================================
(function () {
  var save = BG.saveLayout('WAR');
  ok('saveLayout wrote a slot', save.ok === true && save.builds === 4, 'builds=' + save.builds);
  ok('slot lives on the real profile', !!ECON.loadProfile().baseLayouts['HOME_TURF/WAR']);

  BG.moveAll(2, 2);
  BG.saveLayout('FARM');
  var list = BG.listLayouts();
  ok('listLayouts sees both slots', list.used === 2 && list.slots.length === 2,
     list.slots.map(function (s) { return s.name + '(' + s.builds + ')'; }).join(' '));
  ok('slot cap exposed', list.max === 8);

  var warTiles;
  BG.loadLayout('WAR');
  warTiles = ECON.loadProfile().builds.map(function (b) { var a = BG.entryTile(b); return a.tx + ',' + a.ty; }).join(' ');
  BG.loadLayout('FARM');
  var farmTiles = ECON.loadProfile().builds.map(function (b) { var a = BG.entryTile(b); return a.tx + ',' + a.ty; }).join(' ');
  ok('WAR and FARM are genuinely different layouts', warTiles !== farmTiles, 'WAR ' + warTiles.slice(0, 20) + ' / FARM ' + farmTiles.slice(0, 20));
  BG.loadLayout('WAR');
  ok('loading WAR restores it exactly',
     ECON.loadProfile().builds.map(function (b) { var a = BG.entryTile(b); return a.tx + ',' + a.ty; }).join(' ') === warTiles);
  ok('a loaded layout is buildmode-shaped',
     ECON.loadProfile().builds.every(function (b) { return b.zone === 'HOME_TURF' && isFinite(b.x) && b.maxHp === 200; }));

  ok('missing slot REJECTED', BG.loadLayout('NOPE').ok === false);
  ok('deleteLayout removes it', BG.deleteLayout('FARM').ok === true && BG.listLayouts().used === 1);

  // a mid-build job must block a layout swap so no builder slot is orphaned
  ECON.mutateProfile(function (p) { p.builds[0].uc = { slot: 0, t0: Date.now(), dur: 999999 }; });
  ok('loadLayout REFUSED while a builder is mid-job', BG.loadLayout('WAR').error === 'BUILDERS_BUSY');
  ok('toInventory REFUSED on an under-construction build', BG.toInventory(0).error === 'UNDER_CONSTRUCTION');
  ECON.mutateProfile(function (p) { delete p.builds[0].uc; });
})();

// ==========================================================================
head('8. SCOUT VIEW -- traps hidden from the attacker');
// ==========================================================================
(function () {
  ECON.mutateProfile(function (p) {
    p.builds = [];
    [['TOWNHALL', 10, 10], ['TOWER', 16, 10], ['TRAP_BOMB', 15, 15], ['TRAP_SPIKE', 16, 15], ['WALL', 9, 9]].forEach(function (f) {
      var w = BG.tileToWorld(f[0], f[1], f[2], 0);
      p.builds.push({ type: f[0], x: w.x, y: w.y, hp: 200, maxHp: 200, zone: 'HOME_TURF', t: 1700000000000 });
    });
  });
  var sv = BG.scoutView();
  ok('scout view drops the traps', sv.visible.length === 3 && sv.hiddenCount === 2,
     'visible=' + sv.visible.map(function (v) { return v.type; }).join(',') + ' hidden=' + sv.hiddenCount);
  ok('scout view keeps the real total', sv.total === 5);
  var ownerMap = BG.tileMap(), scoutMap = BG.tileMap(null, null, { scout: true });
  ok('owner map shows trap glyphs', ownerMap.indexOf('^') >= 0);
  ok('scout map shows NO trap glyphs', scoutMap.indexOf('^') < 0);
  console.log('  owner rows 9..16:  ' + ownerMap.split('\n').slice(9, 17).map(function (r) { return r.slice(8, 20); }).join(' | '));
  console.log('  scout rows 9..16:  ' + scoutMap.split('\n').slice(9, 17).map(function (r) { return r.slice(8, 20); }).join(' | '));
})();

// ==========================================================================
head('9. ZERO-STATE + CATALOG AUDIT');
// ==========================================================================
(function () {
  STORE = {};
  global.localStorage.getItem = function (k) { return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; };
  var fresh = JSON.stringify(ECON.loadProfile());
  // pure reads only
  BG.occupancy(); BG.canPlace('HUT', 3, 3, 0); BG.inventory(); BG.scoutView(); BG.listLayouts(); BG.tileMap();
  BG.tileToWorld('HUT', 1, 1, 0); BG.worldToTile('HUT', 100, 100, 0); BG.footprint('TOWER', 1);
  var after = JSON.stringify(ECON.loadProfile());
  ok('ZERO-STATE: reading basegrid wrote nothing to the profile', fresh === after);
  ok('p.baseTray / p.baseLayouts are falsy-default (not created on read)',
     ECON.loadProfile().baseTray === undefined && ECON.loadProfile().baseLayouts === undefined);

  var aud = BG.catalogAudit();
  ok('catalogAudit ran against the REAL buildmode STRUCT', aud.ok === true);
  console.log('  types whose buildmode collision box overflows their tile footprint:');
  if (!aud.rows.filter(function (r) { return r.status === 'PIXEL_OVERFLOW'; }).length) console.log('    (none)');
  aud.rows.filter(function (r) { return r.status === 'PIXEL_OVERFLOW'; }).forEach(function (r) {
    console.log('    ' + r.type.padEnd(12) + ' have ' + r.have.cw + 'x' + r.have.ch + '  want <= ' + r.want.cw + 'x' + r.want.ch);
  });
})();

// ==========================================================================
head('10. INTEGRATION -- the AK_SYSTEMS registry path the script tag creates');
// ==========================================================================
// This is the exact chain index.html produces: _registry.js loads, buildmode.js
// registers, basegrid.js registers, then the hub calls AK_SYSTEMS host dispatch.
// Proves the one-line <script> include is sufficient for a real consumer to reach
// this module. index.html is owned by another lane, so it is NOT edited here.
(function () {
  var mod = global.AK_SYSTEMS.get('basegrid');
  ok('basegrid self-registered with the REAL AK_SYSTEMS registry', !!mod, 'id=' + (mod && mod.id));
  ok('registry also holds buildmode (load order proven)', !!global.AK_SYSTEMS.get('buildmode'));
  ok('registered module exposes init (the host dispatch entry)', !!(mod && typeof mod.init === 'function'));

  // the REAL ctx surface the hub builds (AK_CTX), same fields buildmode.init reads
  var ZONES = { HOME_TURF: { id: 'HOME_TURF', name: 'THE LOT', buildings: [] } };
  var ctx = {
    econ: ECON, AK_ECON: ECON,
    zoneId: 'HOME_TURF', ZONES: ZONES, activeZone: ZONES.HOME_TURF,
    world: { WORLD_W: 1700, WORLD_H: 1300, distToMe: function () { return 0; } },
    me: { x: 850, y: 650 }, showBanner: function () {}
  };
  BG.configure({ cols: 40, rows: 40, originX: 0, originY: 0, zone: 'ELSEWHERE' });
  mod.init(ctx);                                   // EXACTLY what AK_SYSTEMS.initAll dispatches
  var c = BG.config();
  ok('init() adopted the hub zone from ctx', c.zone === 'HOME_TURF', c.zone);
  ok('init() fit the board inside the real world (1700x1300)',
     c.cols === c.rows && c.cols * c.tile <= 1300 && c.cols >= 18, c.cols + 'x' + c.rows + ' tiles @' + c.tile + 'px');
  ok('init() snapped the origin to the 64 lattice (stays coherent with buildmode snap)',
     c.originX % 64 === 0 && c.originY % 64 === 0, 'origin ' + c.originX + ',' + c.originY);
  ok('the fitted board sits inside the world bounds',
     c.originX >= 0 && c.originY >= 0 && c.originX + c.cols * c.tile <= 1700 && c.originY + c.rows * c.tile <= 1300);

  // and placements still round-trip on the fitted board
  var w = BG.tileToWorld('HUT', 3, 3, 0), back = BG.worldToTile('HUT', w.x, w.y, 0);
  ok('round-trip still exact after fitToWorld', back.tx === 3 && back.ty === 3, 'world ' + w.x + ',' + w.y);
  ok('a placement on the fitted board is inside the zone', w.x > 0 && w.x < 1700 && w.y > 0 && w.y < 1300);
})();

console.log('\n==========================================');
console.log('  PASS ' + pass + '   FAIL ' + fail);
console.log('==========================================');
process.exit(fail ? 1 : 0);
