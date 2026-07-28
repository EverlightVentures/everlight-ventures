/* AK-FACADE integration harness -- `node systems/akfacade.test.js`
 *
 * The pure-core selfTest inside akfacade.js proves the MATH. This proves the WIRING, which
 * on this project is the part that has failed four times: a module that registers, ticks,
 * and writes nothing. So this harness runs the REAL _registry.js, the REAL akfacade.js, and
 * a fake THREE + fake AK_WORLD3D scene, then asserts that material slots 2 and 4 actually
 * received maps with the right repeat/offset -- i.e. that a pixel would have changed.
 *
 * It deliberately drives the module ONLY through AK_SYSTEMS.tickAll(), the same entry point
 * index.html:3328 -> _registry.js:22 uses. Nothing here calls dressBuilding directly, because
 * a test that bypasses the host dispatch would prove nothing about integration.
 */
'use strict';
var path = require('path');
var HERE = __dirname;

var fails = [], checks = 0;
function ok(c, m) { checks++; if (!c) fails.push(m); }
function near(a, b, m, eps) { checks++; if (!(Math.abs(a - b) <= (eps || 1e-9))) fails.push(m + ' (got ' + a + ' want ' + b + ')'); }

/* ---------- fake THREE, only the surface akfacade touches ---------- */
function V2(x, y) { this.x = x || 0; this.y = y || 0; }
V2.prototype.set = function (x, y) { this.x = x; this.y = y; return this; };

function FakeTex(w, h) {
  this.image = { width: w, height: h };
  this.repeat = new V2(1, 1); this.offset = new V2(0, 0);
  this.wrapS = null; this.wrapT = null; this.colorSpace = null;
  this.needsUpdate = false; this.clones = 0;
}
FakeTex.prototype.clone = function () {
  var t = new FakeTex(this.image.width, this.image.height);
  t.colorSpace = this.colorSpace;
  t.__master = this;           // so the test can prove clones share a master (one decode)
  this.clones++;
  return t;
};

function FakeColor(v) { this.value = v; }
FakeColor.prototype.set = function (v) { this.value = v; return this; };

function FakeMat(col) { this.color = new FakeColor(col); this.map = null; this.needsUpdate = false; this.transparent = false; this.alphaTest = 0; }

// Texture dimensions per URL, taken from the REAL files on disk (measured with Pillow).
var DISK = {
  'assets/hub/town_hall_cut.png': [1024, 1024],
  'assets/hub/kennel.png': [1248, 1824],
  'assets/hub/trophy.png': [1248, 1824],
  'assets/hub/drop.png': [1248, 1824],
  'assets/hub/roofs/roof_tar.png': [256, 256],
  'assets/hub/roofs/roof_gravel.png': [256, 256],
  'assets/hub/roofs/roof_corrugated.png': [256, 256],
  'assets/hub/roofs/roof_asphalt.png': [256, 256]
};

var loadCount = {};     // url -> how many times the LOADER was hit (cache proof)
var loadersMade = 0;

function FakeLoader() { loadersMade++; }
FakeLoader.prototype.load = function (url, onOk, onProg, onErr) {
  loadCount[url] = (loadCount[url] || 0) + 1;
  var d = DISK[url];
  // Synchronous callback keeps the harness deterministic; akfacade never assumes async.
  if (d) onOk(new FakeTex(d[0], d[1]));
  else if (onErr) onErr(new Error('404 ' + url));
};

var THREE = {
  TextureLoader: FakeLoader,
  SRGBColorSpace: 'srgb',
  RepeatWrapping: 1000,
  ClampToEdgeWrapping: 1001
};

/* ---------- fake host: window + AK_SYSTEMS + AK_THREE + AK_WORLD3D ---------- */
global.window = global;
global.console = console;
require(path.join(HERE, '_registry.js'));          // the REAL registry
ok(typeof global.AK_SYSTEMS === 'object', 'real _registry.js loaded');

global.AK_THREE = { ok: function () { return true; }, get: function () { return THREE; } };

// Two real buildings from index.html ZONES: ARENA (the cut one) and KENNEL (full-bleed).
// world3d.js:525-539 shape: h = max(90, b.h*1.65), depth = b.h*0.72, 6-slot material array.
function mkBuilding(id, w, bh, col) {
  var h = Math.max(90, bh * 1.65), d = bh * 0.72;
  var side = new FakeMat(col), roof = new FakeMat(col), face = new FakeMat(0xffffff);
  return {
    userData: { akId: id },
    geometry: { parameters: { width: w, height: h, depth: d } },
    material: [side, side, roof, side, face, side],
    __side: side, __roof: roof, __face: face, __h: h, __d: d, __w: w
  };
}

var arena = mkBuilding('ARENA', 210, 124, 0xe8c55a);
var kennel = mkBuilding('KENNEL', 160, 96, 0xb6f06b);
var trophy = mkBuilding('TROPHY', 160, 96, 0xffd76b);

global.AK_WORLD3D = { _state: { booted: true, scene: {}, zoneId: 'HOME_TURF', blds: [arena, kennel, trophy] } };

require(path.join(HERE, 'akfacade.js'));           // the module under test
ok(typeof global.AK_FACADE === 'object', 'AK_FACADE published on window');

// Prove it self-registered with the host, and did NOT claim an interior.
var reg = global.AK_SYSTEMS.get('akfacade');
ok(!!reg, 'akfacade self-registered with AK_SYSTEMS');
ok(reg && typeof reg.onTick === 'function', 'exposes onTick');
ok(reg && !reg.onEnterBuilding, 'claims NO interior (would swallow real ones, _registry.js:18)');

// Pure core still green inside the harness.
var st = global.AK_FACADE.selfTest();
ok(st.pass, 'pure-core selfTest passes (' + st.checks + ' checks)');

/* ---------- DRIVE IT THE WAY THE HUB DOES ---------- */
ok(arena.__face.map === null && arena.__roof.map === null, 'buildings start undressed');
global.AK_SYSTEMS.tickAll(0.016, {});              // <-- the ONLY thing that runs the module

/* ---------- assert real pixels would change ---------- */
ok(arena.__face.map !== null, 'ARENA facade map written to slot 4');
ok(arena.__roof.map !== null, 'ARENA roof map written to slot 2');
ok(kennel.__face.map !== null, 'KENNEL facade map written to slot 4');
ok(kennel.__roof.map !== null, 'KENNEL roof map written to slot 2');
ok(arena.__side.map === null, 'side material slots 0/1/3/5 left ALONE (shared instance)');
ok(kennel.__side.map === null, 'KENNEL side material untouched');

// The cut file is preferred for ARENA and gets alphaTest; the full-bleed one does not.
ok(loadCount['assets/hub/town_hall_cut.png'] === 1, 'ARENA loaded the _cut file');
ok(!loadCount['assets/hub/town_hall.png'], 'ARENA never requested the uncut original (no 404 round-trip)');
ok(arena.__face.transparent === true && arena.__face.alphaTest === 0.5, 'cut facade uses alphaTest 0.5 (depth-correct silhouette)');
ok(kennel.__face.transparent === false, 'full-bleed facade stays opaque');
ok(!loadCount['assets/hub/kennel_cut.png'], 'KENNEL never requests a _cut that is not on disk');

// THE ASPECT FIX -- the sampled sub-rect must match the face aspect exactly.
var kt = kennel.__face.map;
var kFaceA = kennel.__w / kennel.__h;
near((1248 * kt.repeat.x) / (1824 * kt.repeat.y), kFaceA, 'KENNEL facade sampled aspect == face aspect');
near(kt.repeat.x, 1, 'KENNEL keeps full texture width');
ok(kt.repeat.y < 0.7, 'KENNEL crops height (repeat.y ' + kt.repeat.y.toFixed(4) + ')');
near(kt.offset.y, (1 - kt.repeat.y) / 2, 'KENNEL crop centred');
ok(kt.wrapS === THREE.ClampToEdgeWrapping, 'facade wrap is ClampToEdge (repeat<1 would mirror art)');
ok(kt.colorSpace === 'srgb', 'facade colorSpace = SRGBColorSpace');

var at = arena.__face.map;
near((1024 * at.repeat.x) / (1024 * at.repeat.y), arena.__w / arena.__h, 'ARENA facade sampled aspect == face aspect');

// Roofs: repeat wrapping, integer tile counts, white tint so gravel is not building-coloured.
var kr = kennel.__roof.map;
ok(kr.wrapS === THREE.RepeatWrapping && kr.wrapT === THREE.RepeatWrapping, 'roof wrap is RepeatWrapping');
ok(kr.repeat.x === (kr.repeat.x | 0) && kr.repeat.y === (kr.repeat.y | 0), 'roof repeat integral');
ok(kr.repeat.x >= 1 && kr.repeat.y >= 1, 'roof repeat >= 1');
ok(kennel.__roof.color.value === 0xffffff, 'roof tint cleared to white (else gravel is building-coloured)');
ok(kr.colorSpace === 'srgb', 'roof colorSpace = SRGBColorSpace');

// Roof choice is seeded, so it must equal what the pure core predicts for that id.
ok(kennel.userData.akRoofKind === global.AK_FACADE.roofKindFor('KENNEL'), 'roof kind matches seeded pick');

/* ---------- idempotence: a tick storm must not re-dress ---------- */
var before = global.AK_FACADE.stats().dressed;
for (var i = 0; i < 60; i++) global.AK_SYSTEMS.tickAll(0.016, {});
ok(global.AK_FACADE.stats().dressed === before, '60 more ticks dress nothing new (guard holds)');

/* ---------- THE CACHE CLAIM, MEASURED ---------- */
// TROPHY and one of the others must collide on a roof URL somewhere across 3 buildings;
// whatever the picks, no roof URL may be fetched twice.
var roofFetches = 0, roofUrls = 0, u;
for (u in loadCount) if (u.indexOf('/roofs/') >= 0) { roofUrls++; roofFetches += loadCount[u]; }
ok(roofFetches === roofUrls, 'every roof URL fetched exactly once (' + roofFetches + ' fetches / ' + roofUrls + ' urls)');
ok(loadersMade === 1, 'ONE TextureLoader constructed total, not one per district (got ' + loadersMade + ')');

/* ---------- THE CLOBBER RACE ----------
 * Simulate world3d.js:548 winning the race: it writes its OWN uncorrected texture (repeat
 * left at 1,1 -> the 1.48x stretch) into the same slot AFTER we already dressed. The next
 * tick must put ours back, or the fix silently reverts in normal play. */
var ourFacadeTex = kennel.__face.map;
var ourRoofTex = kennel.__roof.map;
var world3dTex = new FakeTex(1248, 1824);        // fresh load, repeat still 1,1
kennel.__face.map = world3dTex;                  // <- world3d clobbers us
kennel.__roof.map = new FakeTex(256, 256);
ok(kennel.__face.map !== ourFacadeTex, 'clobber applied (precondition)');
near(kennel.__face.map.repeat.y, 1, 'the clobbering texture is the STRETCHED one');

var reBefore = global.AK_FACADE.stats().reasserts;
global.AK_SYSTEMS.tickAll(0.016, {});
ok(global.AK_FACADE.stats().reasserts > reBefore, 'reassert fired after the clobber');
ok(kennel.__face.map === ourFacadeTex, 'our aspect-corrected facade texture restored');
ok(kennel.__roof.map === ourRoofTex, 'our roof texture restored');
near((1248 * kennel.__face.map.repeat.x) / (1824 * kennel.__face.map.repeat.y), kFaceA,
  'aspect correct again after the race');

// And once settled it must stop doing work -- a permanent per-frame write would be a leak.
var reSteady = global.AK_FACADE.stats().reasserts;
for (var s = 0; s < 30; s++) global.AK_SYSTEMS.tickAll(0.016, {});
ok(global.AK_FACADE.stats().reasserts === reSteady, '30 clean ticks reassert nothing (pointer compare only)');

/* ---------- district swap: fresh meshes must get dressed again ---------- */
var lab = mkBuilding('LAB', 160, 100, 0x7fc8ff);
var gen = mkBuilding('GEN', 160, 100, 0xffce6b);
DISK['assets/hub/research_lab.png'] = [1248, 1824];
DISK['assets/hub/power_gen.png'] = [1248, 1824];
global.AK_WORLD3D._state.zoneId = 'THE_DOCKS';
global.AK_WORLD3D._state.blds = [lab, gen];
global.AK_SYSTEMS.tickAll(0.016, {});
ok(lab.__face.map !== null && gen.__face.map !== null, 'district swap re-dresses the new buildings');
ok(lab.__roof.map !== null, 'district swap dresses new roofs');

// The cache must survive the swap -- this is the whole point of gotcha #4.
var roofFetches2 = 0;
for (u in loadCount) if (u.indexOf('/roofs/') >= 0) roofFetches2 += loadCount[u];
var roofUrls2 = 0;
for (u in loadCount) if (u.indexOf('/roofs/') >= 0) roofUrls2++;
ok(roofFetches2 === roofUrls2, 'after a district swap roof PNGs STILL fetched once each (world3d refetches all of them here)');
ok(loadersMade === 1, 'still one loader after the swap');

/* ---------- robustness: nothing may throw the 2D game down ---------- */
var ringBox = { userData: { akId: 'RING1', akLodRing: true }, geometry: { parameters: { width: 100, height: 100, depth: 100 } }, material: new FakeMat(0x222222) };
var noGeo = { userData: { akId: 'ARENA' }, material: [new FakeMat(1), new FakeMat(1), new FakeMat(1), new FakeMat(1), new FakeMat(1), new FakeMat(1)] };
var noId = mkBuilding('', 160, 96, 0x111111); noId.userData = {};
var flatLod = mkBuilding('DROP', 170, 104, 0xff8fae);
var savedArray = flatLod.material;
flatLod.material = new FakeMat(0xff8fae);         // aklod.js:450 has swapped it to tier T2
flatLod.userData.akFacadeMats = savedArray;       // ...but we captured the array earlier

global.AK_WORLD3D._state.zoneId = 'EDGE';
global.AK_WORLD3D._state.blds = [ringBox, noGeo, noId, flatLod];
var threw = null;
try { global.AK_SYSTEMS.tickAll(0.016, {}); } catch (e) { threw = e; }
ok(!threw, 'malformed meshes do not throw (' + (threw && threw.message) + ')');
ok(ringBox.material.map === null, 'aklod ring box skipped (single material, no facade art)');
ok(savedArray[4].map !== null, 'LOD-swapped building dressed through the CAPTURED array, not mesh.material');
ok(flatLod.material.map === null, 'the flat far-material was NOT written (would be lost on tier flip)');

/* ---------- no scene at all: total no-op ---------- */
global.AK_WORLD3D = null;
var threw2 = null;
try { global.AK_SYSTEMS.tickAll(0.016, {}); } catch (e2) { threw2 = e2; }
ok(!threw2, 'no AK_WORLD3D -> silent no-op, 2D game unaffected');

global.AK_THREE = { ok: function () { return false; }, get: function () { return null; } };
var threw3 = null;
try { global.AK_SYSTEMS.tickAll(0.016, {}); } catch (e3) { threw3 = e3; }
ok(!threw3, 'no WebGL -> silent no-op');

/* ---------- report ---------- */
console.log('[akfacade.test] ' + (fails.length ? 'FAIL' : 'PASS') + ' -- ' + checks + ' checks, ' + fails.length + ' failed');
for (var f = 0; f < fails.length; f++) console.log('   x ' + fails[f]);
console.log('    stats:', JSON.stringify(global.AK_FACADE.stats()));
console.log('    loader hits:', JSON.stringify(loadCount));
process.exit(fails.length ? 1 : 0);
