/* ALLEY KINGZ -- AK_CLUTTER INTEGRATION PROOF.  AK-CLUTTER 2026-07-19.
 *
 * WHY THIS FILE EXISTS SEPARATELY FROM akclutter.js selfTest()
 * -----------------------------------------------------------
 * `node systems/akclutter.js` proves the MODULE works: the planner places correctly, the templates
 * merge under real three, buildFields() produces InstancedMeshes, teardown frees them. Every one of
 * those checks calls into AK_CLUTTER directly.
 *
 * That is exactly the shape of proof that has been wrong four times on this project. A module can
 * pass its own unit tests perfectly and still render nothing, because NOTHING IN THE GAME CALLS IT.
 * AK_BLDMASS is the standing example: bldmass.js is loaded by index.html, defines window.AK_BLDMASS,
 * has a working merge, and a repo-wide grep for callers returns two hits, both inside itself. Its
 * parapets and water tanks have never rendered a pixel.
 *
 * So this file does not call AK_CLUTTER at all. It stands up the REAL host dispatch chain --
 * systems/_registry.js, the same file index.html loads at line 422 -- evaluates akinstance.js and
 * akclutter.js as BROWSER SCRIPTS into that global (no require(), no module.exports path, so the
 * self-registration branch that only runs when `root.document` exists is the branch under test),
 * and then drives them the way index.html:3328 akTickSystems does: AK_SYSTEMS.initAll(ctx) once,
 * then AK_SYSTEMS.tickAll(dt, ctx) per frame.
 *
 * If the props appear in the scene at the end of that, the wiring is real. If they do not, the lane
 * is dead on arrival no matter how green the unit tests are.
 *
 * Run: `node systems/akclutter.test.js`
 * NO em-dashes anywhere in this file (hook law, use --).
 */
'use strict';

var fs = require('fs');
var vm = require('vm');
var path = require('path');

var HERE = __dirname;
var lines = [], ok = true;

function chk(label, cond, got) {
  if (!cond) ok = false;
  lines.push((cond ? 'PASS ' : 'FAIL ') + label + (got !== undefined ? ('  got=' + got) : ''));
}
function eq(label, a, b) {
  var pass = a === b;
  if (!pass) ok = false;
  lines.push((pass ? 'PASS ' : 'FAIL ') + label + '  got=' + a + ' want=' + b);
}

import('../assets/vendor/three.module.min.js').then(function (THREE) {
  run(THREE);
  lines.forEach(function (l) { console.log(l); });
  console.log(ok ? 'ALL PASS' : 'FAILURES PRESENT');
  process.exit(ok ? 0 : 1);
}, function (e) {
  console.log('vendor three not importable: ' + (e && e.message));
  process.exit(1);
});

function run(THREE) {
  lines.push('--- host dispatch chain (real systems/_registry.js) ---');

  /* The sandbox stands in for the browser global. `document` is the flag every module in this
   * repo uses to decide whether it is in a page or in node (akinstance.js:962, akclutter.js
   * publishes on `root.document`), so a bare object with a document is enough to select the
   * browser branch -- which is the branch that self-registers, and therefore the branch worth
   * testing. */
  var sandbox = {
    console: console,
    document: { createElement: function () { return {}; } },
    navigator: { hardwareConcurrency: 8 },
    devicePixelRatio: 2,
    performance: { now: function () { return Date.now(); } },
    setTimeout: setTimeout, clearTimeout: clearTimeout,
    location: { search: '' },
    // three_boot.js is not loaded here, so publish the gate the modules actually read.
    AK_THREE: { ok: function () { return true; }, get: function () { return THREE; } },
    THREE: THREE
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);

  function loadScript(rel) {
    var src = fs.readFileSync(path.join(HERE, rel), 'utf8');
    vm.runInContext(src, sandbox, { filename: rel });
  }

  // Load order mirrors index.html exactly: registry first, then akinstance, then akclutter.
  loadScript('_registry.js');
  chk('AK_SYSTEMS registry is up', !!sandbox.AK_SYSTEMS);

  loadScript('akinstance.js');
  loadScript('akclutter.js');

  chk('akclutter.js published window.AK_CLUTTER', !!sandbox.AK_CLUTTER);
  chk('akinstance.js published window.AK_INSTANCE', !!sandbox.AK_INSTANCE);

  /* THE CHECK THIS FILE EXISTS FOR. Not "does the module work" but "did it get into the list the
   * hub iterates". _registry.js register() silently returns false on a duplicate id or a bad
   * shape, so a module can fail to register with zero console output. */
  var ids = sandbox.AK_SYSTEMS.all().map(function (m) { return m.id; });
  chk('akclutter IS REGISTERED in AK_SYSTEMS', ids.indexOf('akclutter') >= 0, ids.join(','));
  var mod = sandbox.AK_SYSTEMS.get('akclutter');
  chk('the registered module exposes an onTick the host can call', !!(mod && typeof mod.onTick === 'function'));
  chk('akinstance registered too (this lane renders through it)', ids.indexOf('akinstance') >= 0);
  // Registration ORDER matters: AK_INSTANCE's tick re-attaches and GCs fields, and it must see the
  // district in the same frame we planned it.
  chk('akinstance registers BEFORE akclutter', ids.indexOf('akinstance') < ids.indexOf('akclutter'),
    ids.indexOf('akinstance') + ' < ' + ids.indexOf('akclutter'));

  lines.push('--- driving it the way index.html does ---');

  // The scene world3d.js would own. AK_INSTANCE reads AK_WORLD3D._state.scene and attaches there;
  // neither module ever constructs a Scene or a renderer of its own (ONE RENDERER LAW).
  var scene = new THREE.Scene();
  sandbox.AK_WORLD3D = { _state: { scene: scene, zoneId: 'HOME_TURF' } };

  // AK_CTX as index.html builds it, reduced to the fields these modules read.
  var zone = {
    id: 'HOME_TURF', name: 'THE LOT',
    buildings: [
      { id: 'ARENA', x: 850, y: 360, w: 210, h: 124 },
      { id: 'TROPHY', x: 430, y: 880, w: 160, h: 96 },
      { id: 'KENNEL', x: 1270, y: 880, w: 160, h: 96 },
      { id: 'INFIRMARY', x: 1270, y: 500, w: 160, h: 96 }
    ]
  };
  var ctx = {
    zoneId: 'HOME_TURF', activeZone: zone,
    world: { WORLD_W: 1700, WORLD_H: 1300 },
    me: { x: 850, y: 650, r: 23 }
  };

  var before = countInstanced(scene);
  eq('scene starts empty of instanced meshes', before, 0);

  sandbox.AK_SYSTEMS.initAll(ctx);
  chk('initAll did not seize the scene (async boot discipline)', countInstanced(scene) === 0);

  /* tick() polls at ~7Hz (frames & 7), so a single tick legitimately does nothing. Drive a real
   * run of frames like the rAF loop at index.html:2442 would. */
  for (var f = 0; f < 40; f++) sandbox.AK_SYSTEMS.tickAll(0.016, ctx);

  var meshes = countInstanced(scene);
  chk('THE HOST TICK BUILT THE PROP FIELDS -- props are in the live scene', meshes > 0, meshes + ' InstancedMeshes');

  var diag = sandbox.AK_CLUTTER.diag();
  chk('diag reports no swallowed errors', diag.errors === 0, diag.errors + (diag.lastError ? (' last=' + diag.lastError) : ''));
  chk('diag reports a built district', diag.built === true && diag.zone === 'HOME_TURF', diag.zone);
  chk('diag prop count is in the hundreds', diag.props >= 300, diag.props);
  eq('every field is one draw call', diag.drawCallsActual, meshes);
  chk('draw calls beat naive by >20x', diag.drawCallsNaive / diag.drawCallsActual > 20,
    diag.drawCallsNaive + ' naive -> ' + diag.drawCallsActual + ' actual');

  var instances = 0;
  scene.traverse(function (o) { if (o.isInstancedMesh) instances += o.count; });
  eq('every planned prop is a live instance in the scene', instances, diag.props);

  lines.push('--- district change (the poll, not an event) ---');

  /* enterZone (index.html:1354) mutates activeZone and fires nothing. Both modules poll. Swap the
   * district under them mid-run and prove HOME_TURF's props do not end up standing in THE_DOCKS --
   * that is a real bug class here, called out in akinstance.js's own load-order comment. */
  var docks = {
    id: 'THE_DOCKS', name: 'THE DOCKS',
    buildings: [
      { id: 'LAB', x: 560, y: 540, w: 160, h: 100 },
      { id: 'GEN', x: 1140, y: 540, w: 160, h: 100 }
    ]
  };
  ctx.zoneId = 'THE_DOCKS'; ctx.activeZone = docks;
  sandbox.AK_WORLD3D._state.zoneId = 'THE_DOCKS';
  for (f = 0; f < 40; f++) sandbox.AK_SYSTEMS.tickAll(0.016, ctx);

  var d2 = sandbox.AK_CLUTTER.diag();
  chk('rebuilt for the new district', d2.zone === 'THE_DOCKS' && d2.built === true, d2.zone);
  var stale = 0;
  scene.traverse(function (o) {
    if (o.isInstancedMesh && String(o.name || '').indexOf('HOME_TURF') >= 0) stale++;
  });
  eq('NO HOME_TURF props left standing in THE_DOCKS', stale, 0);
  chk('the new district has its own props in the scene', countInstanced(scene) > 0, countInstanced(scene));
  chk('still no swallowed errors after a district swap', d2.errors === 0, d2.errors + (d2.lastError ? (' last=' + d2.lastError) : ''));

  lines.push('--- graceful degradation (a failed subsystem must not take the 2D game down) ---');

  /* Rule 5 on this project: degrade gracefully, but do NOT swallow errors silently. Kill the
   * instancer under the module and prove tickAll keeps running and the failure is visible. */
  var savedInstance = sandbox.AK_INSTANCE;
  sandbox.AK_CLUTTER.teardown();
  sandbox.AK_INSTANCE = null;
  var threw = false;
  try { for (f = 0; f < 40; f++) sandbox.AK_SYSTEMS.tickAll(0.016, ctx); } catch (e) { threw = true; }
  chk('no AK_INSTANCE: the host tick still completes without throwing', !threw);
  chk('and the module reports itself unbuilt rather than pretending', sandbox.AK_CLUTTER.diag().built === false);
  sandbox.AK_INSTANCE = savedInstance;

  var savedW3 = sandbox.AK_WORLD3D;
  sandbox.AK_WORLD3D = null;
  threw = false;
  try { for (f = 0; f < 16; f++) sandbox.AK_SYSTEMS.tickAll(0.016, ctx); } catch (e) { threw = true; }
  chk('no world3d scene: the host tick still completes without throwing', !threw);
  sandbox.AK_WORLD3D = savedW3;

  // And it recovers once the preconditions come back, which is the real-world case: world3d boots
  // three asynchronously and the first few hundred frames genuinely have no scene.
  for (f = 0; f < 40; f++) sandbox.AK_SYSTEMS.tickAll(0.016, ctx);
  chk('recovers and rebuilds once the scene is back', sandbox.AK_CLUTTER.diag().built === true);

  lines.push('--- quality knob through the public API ---');
  var full = sandbox.AK_CLUTTER.diag().props;
  sandbox.AK_CLUTTER.setQuality(0.45);
  for (f = 0; f < 40; f++) sandbox.AK_SYSTEMS.tickAll(0.016, ctx);
  var low = sandbox.AK_CLUTTER.diag();
  chk('setQuality(0.45) rebuilds with fewer props', low.props < full, low.props + ' < ' + full);
  chk('and fewer draw calls', low.drawCallsActual <= diag.drawCallsActual, low.drawCallsActual);
  chk('low quality still renders something real', low.props > 100, low.props);

  lines.push('--- headline ---');
  lines.push('  registered id            : akclutter');
  lines.push('  call site                : _registry.js tickAll -> index.html akTickSystems');
  lines.push('  props in the live scene  : ' + instances);
  lines.push('  draw calls               : ' + diag.drawCallsActual + ' (naive ' + diag.drawCallsNaive + ')');
}

function countInstanced(scene) {
  var n = 0;
  scene.traverse(function (o) { if (o.isInstancedMesh) n++; });
  return n;
}
