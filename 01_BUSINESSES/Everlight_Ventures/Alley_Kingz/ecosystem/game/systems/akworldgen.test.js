/* ALLEY KINGZ -- headless harness for AK_WORLDGEN's SCENE LAYER.  AK-WORLDGEN 2026-07-19
 * Run: node systems/akworldgen.test.js
 *
 * WHY A SECOND TEST FILE
 * ----------------------
 * `node systems/akworldgen.js` proves the PURE CORE: layout, keep-outs, walkability, determinism,
 * draw-call arithmetic. It proves nothing at all about the half of the module that touches THREE,
 * and that half is where this repo's signature failure lives. AK_BLDMASS has shipped a complete
 * parapet/cornice/roof-AC pass since it was written and has NEVER RENDERED A PIXEL, because
 * nothing ever called decorate(). Eleven more modules sit in systems/ with no script tag. A pure
 * core that passes its own tests while the scene layer silently no-ops would be that same bug with
 * a green tick next to it.
 *
 * So this file stands up a FAKE THREE and a FAKE AK_WORLD3D and drives the real tick() through a
 * real district build, a district change, and a teardown, then asserts on what actually landed in
 * the scene graph and in the peer lanes' registries. The fake is deliberately dumb -- it records
 * calls and geometry parameters and nothing else. It is not a renderer and does not pretend to be.
 * What it can prove is the only thing in doubt: that the wiring is connected end to end.
 */
'use strict';

var L = [], fails = 0;
function say(cond, msg) { L.push((cond ? '  PASS  ' : '  FAIL  ') + msg); if (!cond) fails++; }
function line(s) { L.push(s); }

// ============================================================================================
// FAKE THREE. Only the surface world3d.js/bldmass.js/akworldgen.js actually touch.
// BoxGeometry MUST expose .parameters -- AK_BLDMASS.decorate reads geometry.parameters.width/
// height/depth and returns null without them, which would make a "decorated" city quietly plain.
// ============================================================================================
var disposed = { geo: 0, mat: 0 };

function Vec3(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; }
Vec3.prototype.set = function (x, y, z) { this.x = x; this.y = y; this.z = z; return this; };

function Obj3D() { this.children = []; this.parent = null; this.userData = {}; this.visible = true; this.position = new Vec3(); }
Obj3D.prototype.add = function (o) { o.parent = this; this.children.push(o); return this; };
Obj3D.prototype.remove = function (o) {
  var i = this.children.indexOf(o);
  if (i >= 0) { this.children.splice(i, 1); o.parent = null; }
  return this;
};

var THREE = {
  BoxGeometry: function (w, h, d) {
    this.type = 'BoxGeometry';
    this.parameters = { width: w, height: h, depth: d };
    this.attributes = {};
    this.dispose = function () { disposed.geo++; };
    // bldmass merges via toNonIndexed() + attributes.position/normal. Emit a real 36-vertex box so
    // the merge path executes for real instead of bailing early.
    var self = this;
    this.toNonIndexed = function () {
      var n = 36, px = [], nx = [];
      for (var i = 0; i < n; i++) { px.push(0, 0, 0); nx.push(0, 1, 0); }
      return {
        attributes: {
          position: { count: n, getX: function () { return 0; }, getY: function () { return 0; }, getZ: function () { return 0; } },
          normal: { count: n, getX: function () { return 0; }, getY: function () { return 1; }, getZ: function () { return 0; } }
        },
        dispose: function () { disposed.geo++; },
        _src: self
      };
    };
  },
  BufferGeometry: function () {
    this.type = 'BufferGeometry';
    this.attributes = {};
    this.setAttribute = function (k, v) { this.attributes[k] = v; return this; };
    this.dispose = function () { disposed.geo++; };
  },
  Float32BufferAttribute: function (arr, item) { this.array = arr; this.itemSize = item; this.count = arr.length / item; },
  MeshLambertMaterial: function (o) {
    o = o || {};
    this.type = 'MeshLambertMaterial';
    this.color = { hex: o.color || 0, getHex: function () { return this.hex; } };
    this.vertexColors = !!o.vertexColors;
    this.dispose = function () { disposed.mat++; };
  },
  Mesh: function (g, m) { Obj3D.call(this); this.geometry = g; this.material = m; },
  Group: function () { Obj3D.call(this); }
};
THREE.Mesh.prototype = Object.create(Obj3D.prototype);
THREE.Group.prototype = Object.create(Obj3D.prototype);

// ============================================================================================
// FAKE HOST. window + AK_THREE gate + AK_WORLD3D._state + a stub AK_SYSTEMS registry.
// ============================================================================================
var scene = new THREE.Group();
var W3STATE = { scene: scene, blds: [], zoneId: null, camera: {}, proj: null };

var registered = [];
var lodRegistrations = [], streamAdds = [], streamRemoves = 0;

var win = {
  document: { fake: true },
  navigator: { hardwareConcurrency: 8 },
  devicePixelRatio: 2,
  AK_THREE: { ok: function () { return true; }, get: function () { return THREE; } },
  AK_WORLD3D: { _state: W3STATE, isOn: function () { return true; } },
  AK_SYSTEMS: { register: function (m) { registered.push(m); return true; } },
  AK_LOD: {
    register: function (mesh, o) { lodRegistrations.push({ mesh: mesh, o: o }); return true; }
  },
  AK_STREAM: {
    add: function (obj, x, y, tag, w) { var h = { obj: obj, x: x, y: y, tag: tag, w: w }; streamAdds.push(h); return h; },
    remove: function () { streamRemoves++; return true; }
  },
  AK_COLLISION: {
    obstaclesFor: function (z) { return (z && z.id === 'HOME_TURF') ? [{ type: 'rect', x: 1466, y: 280, w: 52, h: 560 }] : []; }
  }
};
global.window = win;

// bldmass.js assigns to window.AK_BLDMASS at load, so window must exist first.
require('./bldmass.js');
win.AK_BLDMASS = global.window.AK_BLDMASS;
var WG = require('./akworldgen.js');

// ============================================================================================
// FIXTURES -- the two real districts, from index.html ZONES.
// ============================================================================================
var HOME_TURF = {
  id: 'HOME_TURF',
  buildings: [
    { id: 'ARENA', x: 850, y: 360, w: 210, h: 124 }, { id: 'TROPHY', x: 430, y: 880, w: 160, h: 96 },
    { id: 'KENNEL', x: 1270, y: 880, w: 160, h: 96 }, { id: 'INFIRMARY', x: 1270, y: 500, w: 160, h: 96 }],
  edges: { N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } }, E: { spawn: { x: 150, y: 650 } }, W: { spawn: { x: 1550, y: 650 } } }
};
var THE_DOCKS = {
  id: 'THE_DOCKS',
  buildings: [{ id: 'LAB', x: 560, y: 540, w: 160, h: 100 }, { id: 'GEN', x: 1140, y: 540, w: 160, h: 100 }],
  edges: { N: { spawn: { x: 850, y: 1150 } }, W: { spawn: { x: 1550, y: 650 } } }
};
function ctxFor(z) { return { activeZone: z, world: { WORLD_W: 1700, WORLD_H: 1300 }, me: { x: 850, y: 650 } }; }

line('================================================================');
line(WG.version() + ' -- SCENE LAYER harness');
line('================================================================');

// ---- 1. SELF-REGISTRATION ------------------------------------------------------------------
line('');
line('[1] SELF-REGISTRATION with AK_SYSTEMS');
var mod = null;
for (var i = 0; i < registered.length; i++) if (registered[i].id === 'akworldgen') mod = registered[i];
say(!!mod, 'registered with AK_SYSTEMS under id "akworldgen"');
say(!!(mod && typeof mod.onTick === 'function'), 'exposes an onTick the registry can drive');
say(!!(mod && typeof mod.init === 'function'), 'exposes an init');
if (mod && mod.init) { mod.init(ctxFor(HOME_TURF)); }
say(WG.config.density > 0 && WG.config.density <= 1, 'init set an auto density: ' + WG.config.density);
WG.setDensity(1.0);   // pin it so the counts below are comparable with the pure-core test

// ---- 2. THE BUILD --------------------------------------------------------------------------
line('');
line('[2] BUILD  (drive the REAL onTick the way _registry.js tickAll would)');

// world3d publishes its zone id only after ITS OWN rebuild finishes. Before that, akworldgen must
// build nothing -- this is the handshake the header describes, and it is asserted, not assumed.
W3STATE.zoneId = null;
mod.onTick(0.016, ctxFor(HOME_TURF));
say(scene.children.length === 0, 'builds NOTHING while world3d has not published a zone id yet');

W3STATE.zoneId = 'HOME_TURF';
var ticks = 0;
while (WG._state.queue.length || !WG._state.built) {
  mod.onTick(0.016, ctxFor(HOME_TURF));
  if (++ticks > 500) break;
}
var plan = WG.plan();
say(!!plan, 'a plan exists after the build');
say(WG._state.built, 'the build completed in ' + ticks + ' ticks at budget ' + WG.config.buildBudget +
    ' (' + plan.structures.length + ' structures)');
say(ticks > 1, 'the build was BUDGETED across frames, not dumped into one (a one-frame build is a phone stall)');
say(WG._state.errors === 0, 'zero errors during the build' + (WG._state.errors ? ' -- ' + WG._state.lastErr : ''));

// ---- 3. WHAT ACTUALLY LANDED IN THE SCENE GRAPH --------------------------------------------
line('');
line('[3] SCENE GRAPH  (the "code nothing calls" check -- did meshes really get added?)');
var meshes = WG.meshes();
say(meshes.length === plan.structures.length,
    'one mesh per planned structure: ' + meshes.length + ' / ' + plan.structures.length);

var inScene = 0, directChild = 0;
for (i = 0; i < meshes.length; i++) {
  if (scene.children.indexOf(meshes[i]) >= 0) inScene++;
  if (meshes[i].parent === scene) directChild++;
}
say(inScene === meshes.length, 'every mesh is in world3d\'s scene (' + inScene + '/' + meshes.length + ')');
say(directChild === meshes.length,
    'every mesh is a DIRECT child of the scene, not nested in a Group -- world3d setZone tears ' +
    'down by scene.remove(m) and a Group would make that a silent no-op');

// The 1-material rule. This is the whole draw-call argument, so it gets asserted rather than
// asserted-in-a-comment.
var arrayMats = 0, geoOk = 0;
for (i = 0; i < meshes.length; i++) {
  if (meshes[i].material && meshes[i].material.length) arrayMats++;
  if (meshes[i].geometry && meshes[i].geometry.parameters) geoOk++;
}
say(arrayMats === 0, 'zero meshes use a material ARRAY -- a 6-slot array would cost 6 render items ' +
    'per box to draw one flat colour (' + arrayMats + ' offenders)');
say(geoOk === meshes.length, 'every geometry exposes .parameters, which is what AK_BLDMASS.decorate needs');

// Position contract: world3d places buildings at (b.x, h/2, b.y) -- hub y maps to three z.
var posOk = 0;
for (i = 0; i < meshes.length; i++) {
  var s = plan.structures[i];
  if (Math.abs(meshes[i].position.x - s.x) < 1e-9 &&
      Math.abs(meshes[i].position.y - s.h / 2) < 1e-9 &&
      Math.abs(meshes[i].position.z - s.y) < 1e-9) posOk++;
}
say(posOk === meshes.length, 'every mesh sits at (x, h/2, y) -- the same hub-y-to-three-z mapping ' +
    'world3d uses, or the generated city would float on a different plane (' + posOk + '/' + meshes.length + ')');

// ---- 4. AK_BLDMASS -- the module that never rendered a pixel --------------------------------
line('');
line('[4] AK_BLDMASS  (this repo\'s canonical dead-code case -- prove we actually call it)');
var wantDeco = plan.stats.decorated;
say(WG._state.details.length === wantDeco,
    'decorate() returned a real detail mesh for every deco kind: ' + WG._state.details.length + ' / ' + wantDeco);
var detInScene = 0;
for (i = 0; i < WG._state.details.length; i++) if (WG._state.details[i].parent === scene) detInScene++;
say(detInScene === WG._state.details.length, 'every detail mesh is in the scene (' + detInScene + ')');
var flagged = 0;
for (i = 0; i < meshes.length; i++) if (meshes[i].userData.akMassed) flagged++;
say(flagged === meshes.length,
    'every mesh carries userData.akMassed so aklod adoptReal will not double-decorate it ' +
    '(two merges on one box = z-fighting plus a wasted draw call)');

// ---- 5. PEER LANE REGISTRATION --------------------------------------------------------------
line('');
line('[5] PEER LANES  (AK_CULL via blds, AK_LOD via register(), AK_STREAM via add())');
var inBlds = 0;
for (i = 0; i < meshes.length; i++) if (W3STATE.blds.indexOf(meshes[i]) >= 0) inBlds++;
say(inBlds === meshes.length,
    'every mesh is in AK_WORLD3D._state.blds -- akcull sync() reads that array and it is the ' +
    'lane\'s ONLY intake (' + inBlds + '/' + meshes.length + ')');
say(lodRegistrations.length === meshes.length,
    'every mesh went through AK_LOD.register() -- NOT via blds, because aklod sync() caches on ' +
    'the blds array identity and would never see a push (' + lodRegistrations.length + ')');
var lodWithDetail = 0;
for (i = 0; i < lodRegistrations.length; i++) if (lodRegistrations[i].o && lodRegistrations[i].o.detail) lodWithDetail++;
say(lodWithDetail === wantDeco, 'the detail mesh was handed to AK_LOD so it can drop it past T0 (' + lodWithDetail + ')');
say(streamAdds.length === meshes.length + wantDeco,
    'every mesh and every detail mesh was parked in AK_STREAM\'s chunk index (' + streamAdds.length + ')');

// ---- 6. DISTRICT CHANGE ---------------------------------------------------------------------
line('');
line('[6] DISTRICT CHANGE  (the poll handshake, and no leaks)');
var beforeMeshes = meshes.length, beforeDetails = WG._state.details.length;
var beforeSceneKids = scene.children.length;
// Snapshot the OLD district's objects by identity. Counting "children carrying the akWorldGen
// flag" after the flip does NOT work and the first cut of this test got it wrong: the same tick
// that tears the old district down also pumps the first budgeted batch of the NEW one, so the
// flagged-children count comes back at buildBudget*2 and looks exactly like a leak.
var oldObjs = WG.meshes().concat(WG._state.details);
disposed.geo = 0; disposed.mat = 0; streamRemoves = 0;

// Simulate world3d.js setZone: it replaces blds with a FRESH array and publishes the new zone id.
W3STATE.zoneId = 'THE_DOCKS';
W3STATE.blds = [];
mod.onTick(0.016, ctxFor(THE_DOCKS));

say(WG._state.meshes.length === 0 || WG._state.zoneId === 'THE_DOCKS',
    'the zone flip was detected and acted on');
say(streamRemoves === beforeMeshes + beforeDetails,
    'every AK_STREAM handle was released (' + streamRemoves + ' / ' + (beforeMeshes + beforeDetails) + ')');
say(disposed.mat > 0, 'materials were disposed on teardown (' + disposed.mat + ') -- world3d setZone ' +
    'disposes geometry only, so materials are ours to free or they accumulate over nine districts');

var strays = 0, inBldsStill = 0;
for (i = 0; i < oldObjs.length; i++) {
  if (oldObjs[i].parent) strays++;
  if (W3STATE.blds.indexOf(oldObjs[i]) >= 0) inBldsStill++;
}
say(strays === 0, 'ZERO of the old district\'s ' + oldObjs.length +
    ' objects are still parented in the scene (' + strays + ' strays, scene was ' + beforeSceneKids + ' children)');
say(inBldsStill === 0, 'ZERO of the old district\'s meshes are still in blds -- a stale entry there ' +
    'would make akcull project a mesh that no longer renders (' + inBldsStill + ')');
var t2 = 0;
while (WG._state.queue.length || !WG._state.built) { mod.onTick(0.016, ctxFor(THE_DOCKS)); if (++t2 > 500) break; }
say(WG.plan() && WG.plan().zoneId === 'THE_DOCKS', 'the new district planned: ' + (WG.plan() && WG.plan().zoneId));
say(WG.meshes().length === WG.plan().structures.length,
    'the new district built ' + WG.meshes().length + ' meshes');
say(WG._state.errors === 0, 'still zero errors after a district swap');

// ---- 7. DEGRADE GRACEFULLY -------------------------------------------------------------------
line('');
line('[7] GRACEFUL DEGRADATION  (a background city must never take the 2D game down)');
WG.teardown();
var prevW3 = win.AK_WORLD3D;

win.AK_WORLD3D = undefined;
var threw = false;
try { mod.onTick(0.016, ctxFor(HOME_TURF)); } catch (e) { threw = true; }
say(!threw, 'onTick with NO AK_WORLD3D returns quietly instead of throwing');
win.AK_WORLD3D = prevW3;

var prevThree = win.AK_THREE;
win.AK_THREE = { ok: function () { return false; }, get: function () { return null; } };
threw = false;
try { mod.onTick(0.016, ctxFor(HOME_TURF)); } catch (e) { threw = true; }
say(!threw, 'onTick with the THREE gate CLOSED returns quietly (2D still owns the frame)');
win.AK_THREE = prevThree;

// A broken AK_BLDMASS must cost us the parapets, not the city.
var prevBM = win.AK_BLDMASS;
win.AK_BLDMASS = { decorate: function () { throw new Error('synthetic bldmass failure'); } };
W3STATE.zoneId = 'HOME_TURF'; W3STATE.blds = [];
var errsBefore = WG._state.errors;
t2 = 0;
while (WG._state.queue.length || !WG._state.built) { mod.onTick(0.016, ctxFor(HOME_TURF)); if (++t2 > 500) break; }
say(WG.meshes().length > 0, 'a throwing AK_BLDMASS still leaves a full city standing (' + WG.meshes().length + ' meshes)');
say(WG._state.details.length === 0, 'no detail meshes were created from the broken decorator');
say(WG._state.errors > errsBefore,
    'the failure was COUNTED into diag().errors (' + (WG._state.errors - errsBefore) + ') rather than ' +
    'swallowed -- silent degradation is how a corrupt vendor file hid on this project for hours');
win.AK_BLDMASS = prevBM;

// ---- 8. DIAG ---------------------------------------------------------------------------------
line('');
line('[8] DIAG');
var d = WG.diag();
say(typeof d.structures === 'number' && typeof d.errors === 'number', 'diag() reports structures and errors');
line('        ' + JSON.stringify({
  zone: d.zone, built: d.built, structures: d.structures, meshes: d.meshes, details: d.details,
  drawCallsNaive: d.drawCallsNaive, density: d.density, errors: d.errors, peers: d.peers
}));

line('');
line(fails ? 'FAILURES PRESENT: ' + fails : 'ALL PASS');
L.forEach(function (l) { console.log(l); });
process.exit(fails ? 1 : 0);
