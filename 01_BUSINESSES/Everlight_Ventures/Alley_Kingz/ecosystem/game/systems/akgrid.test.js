/* game/systems/akgrid.test.js -- headless proof for AK_GRID.
 * AK-GRID-TEST 2026-07-19   run: node systems/akgrid.test.js
 *
 * WHY A SEPARATE FILE FROM selfTest()
 * -----------------------------------
 * akgrid.js:662 selfTest() is an in-module smoke check and it ships to the browser, so it can
 * only assert things the module already believes. The two assertions that actually protect the
 * project are CROSS-FILE and cannot live inside akgrid.js:
 *
 *   1. MIRROR-vs-basegrid drift. akgrid.js:186 MIRROR is a fallback copy of basegrid.js:125
 *      FOOTPRINTS. Two hand-maintained copies of a 24-entry table is a drift bomb: the day
 *      someone widens MORTAR to 4x4 in one file and not the other, buildings land half a cell
 *      off and the symptom surfaces as a rendering bug three systems away. This file requires
 *      BOTH modules and compares them key-for-key, so drift fails a test instead of shipping.
 *      (akgrid.js's own header claimed this test existed. It did not. Now it does.)
 *
 *   2. buildmode snap() interop. The whole compatibility contract is "even footprints survive
 *      buildmode.js:467 snap() unchanged". That is a claim about ANOTHER file's arithmetic, so
 *      it is re-derived here from the literal formula rather than trusted.
 *
 * Plus the round-trip property test the lane brief asked for, run over 4 origins x 1000+ cells
 * rather than the handful selfTest() covers.
 *
 * No DOM, no three.js, no network. Exit code 0 = pass, 1 = fail.
 */
'use strict';

var path = require('path');
var GRID = require(path.join(__dirname, 'akgrid.js'));

/* basegrid is loaded for the DRIFT CHECK only. */
var BASEGRID = null;
try {
  BASEGRID = require(path.join(__dirname, 'basegrid.js'));
} catch (e) {
  console.log('  (note) basegrid.js not requireable: ' + e.message);
}

var checks = 0, fails = [];
function ok(cond, label) {
  checks++;
  if (!cond) fails.push(label);
}
function eq(a, b, label) {
  ok(a === b, label + '  (got ' + a + ', want ' + b + ')');
}
function near(a, b, label, eps) {
  eps = eps == null ? 1e-9 : eps;
  ok(Math.abs(a - b) <= eps, label + '  (got ' + a + ', want ' + b + ')');
}
function section(name) { console.log('\n-- ' + name); }

/* ====================================================================== *
 * 1. ROUND TRIP -- worldToGrid(gridToWorld(c)) === c
 * ====================================================================== *
 * The property the lane brief names explicitly. Run across several ORIGINS, because an
 * origin-dependent bug is exactly the one that survives a single-origin test: with
 * originX=0 a sign error in the subtraction is invisible.
 */
section('round trip: worldToGrid(gridToWorld(c)) === c');
var ORIGINS = [
  { originX: 0,    originY: 0 },
  { originX: 64,   originY: 128 },
  { originX: 640,  originY: 448 },   // the shape fitToDistrict lands on for 1700x1300
  { originX: -256, originY: -64 }    // negative origin: floor() vs trunc() trap
];
var rtFails = 0, rtCells = 0;
for (var oi = 0; oi < ORIGINS.length; oi++) {
  GRID.configure({ cols: 40, rows: 40, originX: ORIGINS[oi].originX, originY: ORIGINS[oi].originY });
  for (var gy = -6; gy < 26; gy++) {
    for (var gx = -6; gx < 26; gx++) {
      var w = GRID.gridToWorld(gx, gy);
      var back = GRID.worldToGrid(w.x, w.y);
      rtCells++;
      if (back.gx !== gx || back.gy !== gy) rtFails++;
    }
  }
}
console.log('   cells exercised: ' + rtCells + ' across ' + ORIGINS.length + ' origins');
eq(rtFails, 0, 'round-trip failures over ' + rtCells + ' cells');

/* Negative coords are the reason worldToGrid uses floor() and not trunc()/round(). Prove it. */
GRID.configure({ originX: 0, originY: 0 });
var negCell = GRID.worldToGrid(-1, -1);
eq(negCell.gx, -1, 'world (-1,-1) floors into cell -1 (not 0)');
eq(negCell.gy, -1, 'world (-1,-1) floors into cell -1 on y');

/* Cell boundaries belong to the HIGHER cell. A pointer-pick must not flip-flop at the seam. */
eq(GRID.worldToGrid(64, 64).gx, 1, 'x=64 (exact seam) resolves to cell 1');
eq(GRID.worldToGrid(63.999, 0).gx, 0, 'x just under the seam stays in cell 0');

/* ====================================================================== *
 * 2. FOOTPRINT MATH -- anchorToWorld <-> worldToAnchor
 * ====================================================================== */
section('footprint math: anchor <-> world inverses');
var fpFails = 0, fpCases = 0;
for (var gw = 1; gw <= 6; gw++) {
  for (var gh = 1; gh <= 6; gh++) {
    for (var ay = -4; ay < 14; ay++) {
      for (var ax = -4; ax < 14; ax++) {
        var c = GRID.anchorToWorld(ax, ay, gw, gh);
        var a = GRID.worldToAnchor(c.x, c.y, gw, gh);
        fpCases++;
        if (a.gx !== ax || a.gy !== ay) fpFails++;
      }
    }
  }
}
console.log('   anchor cases exercised: ' + fpCases + ' (footprints 1x1..6x6)');
eq(fpFails, 0, 'anchor round-trip failures over ' + fpCases + ' cases');

/* A 1x1 footprint IS a cell. If these ever diverge the two conversions are not one system. */
var oneOff = 0;
for (var q = 0; q < 200; q++) {
  var qx = (q % 20) - 5, qy = Math.floor(q / 20) - 5;
  var g1 = GRID.gridToWorld(qx, qy), a1 = GRID.anchorToWorld(qx, qy, 1, 1);
  if (g1.x !== a1.x || g1.y !== a1.y) oneOff++;
}
eq(oneOff, 0, 'anchorToWorld(gx,gy,1,1) identical to gridToWorld over 200 cells');

/* Parity: even footprints centre ON the 64 lattice, odd ones on lattice+32. This is the
 * documented split (akgrid.js snapsClean) and the reason odd pieces must not go through
 * buildmode.place(). Re-derive it rather than trust the flag. */
GRID.configure({ originX: 0, originY: 0 });
near(GRID.anchorToWorld(3, 3, 2, 2).x % 64, 0,  '2x2 centre lands on the 64 lattice');
near(GRID.anchorToWorld(3, 3, 4, 4).x % 64, 0,  '4x4 centre lands on the 64 lattice');
near(GRID.anchorToWorld(3, 3, 1, 1).x % 64, 32, '1x1 centre lands on lattice+32');
near(GRID.anchorToWorld(3, 3, 3, 3).x % 64, 32, '3x3 centre lands on lattice+32');
ok(GRID.snapsClean('HUT') === true,       'snapsClean(HUT 2x2) is true');
ok(GRID.snapsClean('WALL') === false,     'snapsClean(WALL 1x1) is false');
ok(GRID.snapsClean('TOWER') === false,    'snapsClean(TOWER 3x3) is false');
ok(GRID.snapsClean('TOWNHALL') === true,  'snapsClean(TOWNHALL 4x4) is true');

/* ====================================================================== *
 * 3. buildmode.js snap() INTEROP -- the actual compatibility contract
 * ====================================================================== *
 * buildmode.js:467, quoted verbatim:  function snap(v){ return Math.round(v / GRID) * GRID; }
 * Re-implemented here from the literal source line. If an even-footprint centre is not a
 * fixed point of snap(), then a structure placed by the builder and the same structure
 * written by AK_GRID.put() sit half a cell apart -- silently, forever.
 */
section('buildmode snap() interop (GRID = 64)');
function buildmodeSnap(v) { return Math.round(v / 64) * 64; }
var snapDrift = 0, snapOdd = 0;
for (var s = 0; s < 24; s++) {
  var evenC = GRID.anchorToWorld(s, s, 2, 2);
  if (buildmodeSnap(evenC.x) !== evenC.x) snapDrift++;
  var oddC = GRID.anchorToWorld(s, s, 1, 1);
  if (buildmodeSnap(oddC.x) === oddC.x) snapOdd++;   // odd centres must NOT be fixed points
}
eq(snapDrift, 0, 'even footprints are fixed points of buildmode snap()');
eq(snapOdd, 0, 'odd footprints are NOT fixed points (documented parity split holds)');

/* The origin invariant: an off-lattice origin breaks that fixed-point property, so configure()
 * must refuse it. This is the "silent half-cell drift" guard in akgrid.js assertAligned(). */
var before = GRID.config().originX;
GRID.configure({ originX: 30, originY: 30 });
eq(GRID.config().originX, before, 'configure() REFUSES an origin that is not 0 mod 64');
GRID.configure({ originX: 128, originY: 128 });
eq(GRID.config().originX, 128, 'configure() ACCEPTS an on-lattice origin');
GRID.configure({ originX: 0, originY: 0 });

/* ====================================================================== *
 * 4. MIRROR DRIFT -- akgrid MIRROR vs basegrid FOOTPRINTS
 * ====================================================================== */
section('footprint table drift: akgrid MIRROR vs basegrid FOOTPRINTS');
if (!BASEGRID || !BASEGRID.FOOTPRINTS) {
  console.log('   SKIPPED -- basegrid.FOOTPRINTS unavailable');
} else {
  var BG = BASEGRID.FOOTPRINTS;
  /* Compare THROUGH the public API with delegation disabled, which is the behaviour that
   * actually matters: what a page WITHOUT basegrid.js loaded would compute. */
  GRID.configure({ basegrid: false });
  var keys = Object.keys(BG), drift = 0, k, i;
  for (i = 0; i < keys.length; i++) {
    k = keys[i];
    var mine = GRID.footprint(k, 0);
    if (mine.gw !== BG[k].w || mine.gh !== BG[k].h) {
      drift++;
      console.log('   DRIFT ' + k + ': akgrid ' + mine.gw + 'x' + mine.gh + ' vs basegrid ' + BG[k].w + 'x' + BG[k].h);
    }
    if (GRID.catOf(k) !== BG[k].cat) {
      drift++;
      console.log('   DRIFT ' + k + ' cat: akgrid ' + GRID.catOf(k) + ' vs basegrid ' + BG[k].cat);
    }
  }
  console.log('   compared ' + keys.length + ' footprint keys');
  eq(drift, 0, 'zero drift between akgrid MIRROR and basegrid FOOTPRINTS');
  /* Every basegrid key must be KNOWN to akgrid -- a missing key silently becomes 1x1. */
  var missing = 0;
  for (i = 0; i < keys.length; i++) if (!GRID.known(keys[i])) missing++;
  eq(missing, 0, 'every basegrid footprint key is known to akgrid (no silent 1x1 fallback)');
  GRID.configure({ basegrid: null });
}

/* Unknown type must fall back to 1x1 rather than throw -- a renderer asking about a type from
 * a future catalog should degrade, not crash the frame. */
var unk = GRID.footprint('NOT_A_REAL_TYPE_XYZ', 0);
eq(unk.gw, 1, 'unknown type falls back to 1x1 (w)');
eq(unk.gh, 1, 'unknown type falls back to 1x1 (h)');
ok(GRID.known('NOT_A_REAL_TYPE_XYZ') === false, 'known() reports false for an unknown type');

/* ====================================================================== *
 * 5. ROTATION
 * ====================================================================== */
section('rotation: odd rot swaps the long axis');
var gate0 = GRID.footprint('GATE', 0);   // 2x1
var gate1 = GRID.footprint('GATE', 1);
var gate2 = GRID.footprint('GATE', 2);
var gate3 = GRID.footprint('GATE', 3);
eq(gate0.gw + 'x' + gate0.gh, '2x1', 'GATE rot 0 is 2x1');
eq(gate1.gw + 'x' + gate1.gh, '1x2', 'GATE rot 1 swaps to 1x2');
eq(gate2.gw + 'x' + gate2.gh, '2x1', 'GATE rot 2 is 2x1 again');
eq(gate3.gw + 'x' + gate3.gh, '1x2', 'GATE rot 3 swaps to 1x2');

/* ====================================================================== *
 * 6. RECORD SCHEMA PURITY -- the JSON-safe contract
 * ====================================================================== */
section('record schema: pure data, JSON-safe');
var rec = GRID.makeRecord({ id: 'r1', type: 'HUT', gx: 4, gy: 5, rot: 0, level: 2, district: 'HOME_TURF' });
eq(rec.gw, 2, 'makeRecord derives gw from the footprint table');
eq(rec.gh, 2, 'makeRecord derives gh from the footprint table');
ok(GRID.validate(rec).ok === true, 'validate() accepts a well-formed record');
ok(GRID.isPure(rec) === true, 'isPure() confirms no DOM / three.js handles on the record');

/* A record must survive a JSON round trip byte-identical -- that is what "save file safe" means. */
var json = JSON.stringify(rec);
var revived = JSON.parse(json);
eq(JSON.stringify(revived), json, 'record survives JSON.stringify -> parse unchanged');

/* Impurity must be DETECTED, not silently accepted. Simulate a caller stapling a mesh on. */
var dirty = GRID.makeRecord({ id: 'r2', type: 'HUT', gx: 0, gy: 0, district: 'HOME_TURF' });
dirty.meta = dirty.meta || {};
dirty.meta.mesh = { isMesh: true, geometry: {}, material: {} };
ok(GRID.isPure(dirty) === false, 'isPure() REJECTS a record carrying a three.js-shaped object');

/* Geometry helpers agree with each other. */
GRID.configure({ originX: 0, originY: 0 });
var r3 = GRID.makeRecord({ id: 'r3', type: 'HUT', gx: 2, gy: 3, district: 'HOME_TURF' });
var b3 = GRID.bounds(r3), c3 = GRID.center(r3);
near(b3.cx, c3.x, 'bounds().cx agrees with center().x');
near(b3.cy, c3.y, 'bounds().cy agrees with center().y');
eq(b3.w, 128, 'a 2x2 record is 128 world units wide');
eq(GRID.cellsOf(r3).length, 4, 'a 2x2 record occupies exactly 4 cells');
ok(GRID.containsCell(r3, 2, 3) === true,  'containsCell finds the anchor cell');
ok(GRID.containsCell(r3, 4, 3) === false, 'containsCell rejects a cell outside the footprint');

/* Overlap detection -- the placement rule everything else leans on. */
var oA = GRID.makeRecord({ id: 'a', type: 'HUT', gx: 0, gy: 0, district: 'D' });
var oB = GRID.makeRecord({ id: 'b', type: 'HUT', gx: 1, gy: 1, district: 'D' });
var oC = GRID.makeRecord({ id: 'c', type: 'HUT', gx: 2, gy: 2, district: 'D' });
ok(GRID.overlaps(oA, oB) === true,  'overlapping 2x2 records are detected');
ok(GRID.overlaps(oA, oC) === false, 'flush-adjacent 2x2 records do NOT overlap');

/* key/unkey must interop verbatim with basegrid's occupancy maps. */
var kk = GRID.key(7, 9), un = GRID.unkey(kk);
eq(un.gx, 7, 'key/unkey round-trips gx');
eq(un.gy, 9, 'key/unkey round-trips gy');
if (BASEGRID && BASEGRID.key) {
  eq(GRID.key(7, 9), BASEGRID.key(7, 9), 'akgrid key() is byte-identical to basegrid key()');
}

/* ====================================================================== *
 * 7. PERSISTENCE BRIDGE -- fromBuild / toBuild against the REAL entry shape
 * ====================================================================== *
 * The entry literal below is copied verbatim from buildmode.js:614. If this test drifts from
 * that line, the bridge is converting a shape the game does not actually store.
 */
section('persistence bridge: p.builds[] <-> record');
GRID.configure({ originX: 0, originY: 0, district: 'HOME_TURF' });
var now = 1721400000000;
var entry = {
  type: 'HUT', x: 320, y: 384, hp: 500, maxHp: 500, zone: 'HOME_TURF', t: now,
  uc: { slot: 0, t0: now, dur: 60000 }
};
var fromE = GRID.fromBuild(entry);
eq(fromE.type, 'HUT', 'fromBuild carries type');
eq(fromE.district, 'HOME_TURF', 'fromBuild maps zone -> district');
eq(fromE.gw, 2, 'fromBuild derives the 2x2 footprint');
var backE = GRID.toBuild(fromE);
near(backE.x, entry.x, 'toBuild restores x exactly');
near(backE.y, entry.y, 'toBuild restores y exactly');
eq(backE.zone, entry.zone, 'toBuild restores zone');
eq(backE.hp, entry.hp, 'toBuild preserves hp (rode through meta)');
eq(backE.maxHp, entry.maxHp, 'toBuild preserves maxHp');
eq(backE.t, entry.t, 'toBuild preserves the placement timestamp');
eq(JSON.stringify(backE.uc), JSON.stringify(entry.uc), 'toBuild preserves the uc build-crew block');
ok(backE.rot === undefined, 'falsy-default: rot is NOT written when zero (zero-state stays byte-identical)');
ok(backE.gid === undefined, 'falsy-default: a synthesised id is NOT persisted as gid');

/* Garden fields (crop/plantedAt/wx/em) must survive -- buildmode writes them and a lossy
 * bridge would wipe a player's planted crop. */
var garden = { type: 'GARDEN', x: 32, y: 32, hp: 60, maxHp: 60, zone: 'HOME_TURF', t: now,
               crop: 'kush', plantedAt: now, wx: 3, em: 1 };
var gBack = GRID.toBuild(GRID.fromBuild(garden));
eq(gBack.crop, 'kush',     'garden crop survives the bridge');
eq(gBack.plantedAt, now,   'garden plantedAt survives the bridge');
eq(gBack.wx, 3,            'garden wx survives the bridge');
eq(gBack.em, 1,            'garden em survives the bridge');

/* Rotation persists only when non-zero, and survives when it is. */
var rotEntry = { type: 'GATE', x: 96, y: 128, hp: 100, maxHp: 100, zone: 'HOME_TURF', t: now, rot: 1 };
var rBack = GRID.toBuild(GRID.fromBuild(rotEntry));
eq(rBack.rot, 1, 'non-zero rot IS persisted');

/* OFF-LATTICE HONESTY. A 1x1 written by buildmode's snap() sits ON the lattice, which is NOT a
 * legal 1x1 anchor centre -- so converting it MOVES it by 32 units. The module must flag that
 * instead of quietly relocating a player's wall. */
var offEntry = { type: 'WALL', x: 640, y: 640, hp: 40, maxHp: 40, zone: 'HOME_TURF', t: now };
var offRec = GRID.fromBuild(offEntry);
ok(offRec.meta && offRec.meta._offLattice, 'a snap()-placed 1x1 is FLAGGED as off-lattice');
var offBack = GRID.toBuild(offRec);
ok(offBack.x !== offEntry.x, 'writing it back would indeed move it -- the flag is warranted');
near(Math.abs(offBack.x - offEntry.x), 32, 'the move is exactly half a cell');
/* The _offLattice marker itself must NOT leak into the save file. */
ok(offBack._offLattice === undefined, 'underscore meta keys are stripped on the way back to p.builds');

/* ====================================================================== *
 * 8. HUB BUILDING BRIDGE + the measured off-lattice claim in the header
 * ====================================================================== *
 * akgrid.js's header asserts "of the 18 hub buildings, ZERO sit on the 64 lattice". That is a
 * measured claim about index.html ZONES data, so MEASURE it here instead of believing it.
 */
section('hub ZONES buildings: the measured off-lattice claim');
var fs = require('fs');
var html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
var reB = /B\(\s*'([A-Z_]+)'\s*,\s*'[^']*'\s*,\s*'#[0-9a-fA-F]+'\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,\s*(\d+)/g;
var hub = [];
html.replace(reB, function (whole, id, bx, by, bw, bh) {
  hub.push({ id: id, x: +bx, y: +by, w: +bw, h: +bh });
  return whole;
});
console.log('   parsed ' + hub.length + ' hub buildings out of index.html ZONES');
ok(hub.length >= 15, 'found the hub building table in index.html (>=15 entries)');
var onLattice = 0;
for (var hb = 0; hb < hub.length; hb++) {
  if (hub[hb].x % 64 === 0 && hub[hb].y % 64 === 0) onLattice++;
}
console.log('   hub buildings sitting exactly on the 64 lattice: ' + onLattice + ' / ' + hub.length);
eq(onLattice, 0, 'header claim holds: ZERO hub buildings are on the 64 lattice');

/* Because they are all off-lattice, fromZoneBuilding must quantise AND admit it. Otherwise a
 * 3D district that round-trips its buildings through the grid would shove every one of them. */
if (GRID.fromZoneBuilding && hub.length) {
  var zrec = GRID.fromZoneBuilding(hub[0], 'HOME_TURF');
  ok(!!zrec, 'fromZoneBuilding produces a record for a hub building');
  ok(GRID.isPure(zrec) === true, 'a hub-derived record is still pure data');
}

/* ====================================================================== *
 * 9. ALIGNMENT PREDICATE
 * ====================================================================== */
section('isAligned: distinguishes a clean round trip from a quantisation');
GRID.configure({ originX: 0, originY: 0 });
var alignedC = GRID.anchorToWorld(5, 5, 2, 2);
ok(GRID.isAligned(alignedC.x, alignedC.y, 2, 2) === true, 'a legal 2x2 centre reports aligned');
ok(GRID.isAligned(alignedC.x + 7, alignedC.y, 2, 2) === false, 'a centre 7 units off reports NOT aligned');

/* ====================================================================== *
 * 10. WRITE PATH -- ensureIds / put / patch / remove against a fake profile
 * ====================================================================== *
 * These are the only functions that MUTATE player data, so they get exercised against a
 * stand-in AK_ECON rather than trusted. The centres below are hand-derived from the anchor
 * formula ((gx + gw/2) * cell) -- an earlier draft of this test asserted 352 for a 3x3 at
 * (5,5) using the 1x1 formula and the MODULE was right, not the test. Keeping the derivation
 * inline so the next reader checks the arithmetic instead of the intuition.
 */
section('write path: ensureIds / put / patch / remove');
var FAKE = { builds: [ { type: 'HUT', x: 320, y: 384, hp: 500, maxHp: 500, zone: 'HOME_TURF', t: 1 } ] };
var FAKE_ECON = {
  loadProfile: function () { return FAKE; },
  mutateProfile: function (fn) { fn(FAKE); return FAKE; }
};
GRID.configure({ econ: FAKE_ECON, originX: 0, originY: 0, district: 'HOME_TURF', cols: 40, rows: 40 });

GRID.ensureIds('HOME_TURF');
ok(!!FAKE.builds[0].gid, 'ensureIds() stamps a stable gid (array index is not an identity)');

var putRec = GRID.makeRecord({ type: 'TOWER', gx: 5, gy: 5, district: 'HOME_TURF', id: 't1' });
GRID.put(putRec);
eq(FAKE.builds.length, 2, 'put() appends to p.builds');
eq(FAKE.builds[1].type, 'TOWER', 'put() writes the type');
eq(FAKE.builds[1].zone, 'HOME_TURF', 'put() writes the zone');
eq(FAKE.builds[1].x, (5 + 3 / 2) * 64, 'put() writes the 3x3 centre from the anchor formula');
eq(FAKE.builds[1].y, (5 + 3 / 2) * 64, 'put() writes the 3x3 centre on y');

GRID.patch('t1', { gx: 8, gy: 2 }, 'HOME_TURF');
var movedRec = null;
for (var mi = 0; mi < FAKE.builds.length; mi++) if (FAKE.builds[mi].gid === 't1') movedRec = FAKE.builds[mi];
ok(!!movedRec, 'patch() keeps the record findable by gid');
if (movedRec) {
  eq(movedRec.x, (8 + 3 / 2) * 64, 'patch() relocates x to the new anchor centre');
  eq(movedRec.y, (2 + 3 / 2) * 64, 'patch() relocates y to the new anchor centre');
}
eq(GRID.list('HOME_TURF').length, 2, 'list() sees both structures');

GRID.remove('t1', 'HOME_TURF');
eq(FAKE.builds.length, 1, 'remove() splices the entry out');
eq(FAKE.builds[0].type, 'HUT', 'remove() took the right one');
/* Neighbour integrity: none of the above may disturb an untouched structure. */
eq(FAKE.builds[0].x, 320, 'the untouched HUT was not moved by any write');
eq(FAKE.builds[0].hp, 500, 'the untouched HUT kept its hp');
GRID.configure({ econ: null });

/* ====================================================================== *
 * 11. The module's own selfTest must also pass (it ships to the browser)
 * ====================================================================== */
section('module selfTest()');
var st = GRID.selfTest({ quiet: true });
ok(st && st.ok === true, 'akgrid.selfTest() passes (' + (st ? st.checks : 0) + ' internal checks)');

/* ====================================================================== */
console.log('\n========================================');
if (fails.length) {
  console.log('FAIL -- ' + fails.length + ' of ' + checks + ' checks failed:');
  for (var f = 0; f < fails.length; f++) console.log('  x ' + fails[f]);
  process.exit(1);
} else {
  console.log('PASS -- ' + checks + ' checks, 0 failures');
  console.log('  round-trip cells: ' + rtCells + ' | anchor cases: ' + fpCases);
  process.exit(0);
}
