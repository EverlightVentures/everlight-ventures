/* ALLEY KINGZ -- camera probe. AK-CAM 2026-07-18.  Run:  node game/systems/cameras/_probe.js
 *
 * Every assertion below is checked against code EXTRACTED FROM THE SHIPPING FILES,
 * never against a stand-in written for the test:
 *   game.html:2896   warpScreen()           the arena's real perspective warp
 *   game.html:2845   scaleX/scaleY/toX/toY  the battler's real linear camera
 *   index.html:3091  wx/wy                  the hub's real world-to-screen pair
 * extract() slices those exact source spans out of the .html files, wraps each in a
 * throwaway CommonJS module under os.tmpdir(), and require()s it. So the probe runs
 * the ORIGINAL code, and if anyone edits those originals this probe starts failing
 * instead of quietly drifting.
 */
'use strict';
var fs = require('fs'), path = require('path'), os = require('os');
var HERE = __dirname, GAME = path.resolve(HERE, '../..');
var TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'ak-cam-extract-'));

var P  = require('./Projection.js');
var CM = require('./CameraManager.js');
var RPG = require('./RPGCamera.js');
var BATTLE = require('./BattleCamera.js');
var BUILDER = require('./BuilderCamera.js');
var GARAGE = require('./GarageCamera.js');
var FPS = require('./FPSCamera.js');

var pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS  ' + name + (detail ? '   ' + detail : '')); }
  else { fail++; console.log('  FAIL  ' + name + (detail ? '   ' + detail : '')); }
}
function near(a, b, eps) { return Math.abs(a - b) <= (eps || 1e-9); }

/* ---------- extract the REAL functions out of the REAL files ---------- */
/* WINDOWED read, not readFileSync: game.html is 648 KB and index.html 436 KB, and
 * holding both as strings alongside the loaded modules segfaults node under this
 * repo's proot userland. So scan for the marker in 64 KB chunks and lift only a few
 * KB around the hit. Same real bytes, a fraction of the memory. */
function window_(file, marker, span) {
  var fd = fs.openSync(path.join(GAME, file), 'r');
  var CH = 65536, buf = Buffer.alloc(CH), carry = '', base = 0, at = -1, pos = 0, n;
  try {
    while ((n = fs.readSync(fd, buf, 0, CH, pos)) > 0) {
      var s = carry + buf.toString('utf8', 0, n);
      var i = s.indexOf(marker);
      if (i >= 0) { at = base + i; break; }
      base += s.length - marker.length;          // overlap so a chunk-split marker still hits
      carry = s.slice(s.length - marker.length);
      pos += n;
    }
    if (at < 0) throw new Error('marker not found in ' + file + ': ' + marker);
    var win = Buffer.alloc(span);
    var got = fs.readSync(fd, win, 0, span, at);
    return win.toString('utf8', 0, got);
  } finally { fs.closeSync(fd); }
}
/* Pull a source span, wrap it as a factory module, require it back. No eval. */
function extract(name, src, re, args, ret, file) {
  var m = src.match(re);
  if (!m) throw new Error('extract failed in ' + file + ' for ' + name);
  var body = 'module.exports = function (' + args.join(', ') + ') {\n' + m[0] + '\nreturn ' + ret + ';\n};\n';
  var f = path.join(TMP, name + '.js');
  fs.writeFileSync(f, body, 'utf8');
  return { fn: require(f), src: m[0] };
}

var gameHtml = window_('game.html', 'function warpScreen(X, Y){', 1200) + '\n/*SPLIT*/\n'
             + window_('game.html', 'function scaleX(){', 900);
var indexHtml = window_('index.html', 'wx:function(x){return x-cam.x;}', 400);

var exWarp = extract('warp', gameHtml, /function warpScreen\(X, Y\)\{[\s\S]*?\n  \}/,
  ['canvas', 'TILT2_SIN', 'TILT2_COS', 'PERSP2_PX'], 'warpScreen', 'game.html');
var realWarp = exWarp.fn({ width: 1080, height: 1920 }, Math.sin(18 * Math.PI / 180), Math.cos(18 * Math.PI / 180), 1100);

var exArena = extract('arena', gameHtml, /function scaleX\(\)\{[\s\S]*?function toY\(gy\)\{[^\n]*\n/,
  ['canvas', 'ARENA_W', 'ARENA_H', 'cam'], '{ toX: toX, toY: toY }', 'game.html');
var ARENA_CAM = { offX: 0, offY: 0, zoom: 1 };
var realArena = exArena.fn({ width: 1080, height: 1920 }, 1000, 1800, function () { return ARENA_CAM; });

// the hub match is an object-literal FRAGMENT (index.html:3091), so it wraps as a
// literal rather than as statements. Same lift, different envelope.
var exHub = (function () {
  var m = indexHtml.match(/wx:function\(x\)\{return x-cam\.x;\}, wy:function\(y\)\{return y-cam\.y;\}/);
  if (!m) throw new Error('extract failed in index.html for hub wx/wy');
  var f = path.join(TMP, 'hub.js');
  fs.writeFileSync(f, 'module.exports = function (cam) { return ({ ' + m[0] + ' }); };\n', 'utf8');
  return { fn: require(f), src: m[0] };
})();
var HUB_CAM = { x: 0, y: 0 };
var realHub = exHub.fn(HUB_CAM);

console.log('EXTRACTED from shipping source (' + TMP + '):');
console.log('  game.html  warpScreen  ' + exWarp.src.split('\n').length + ' lines');
console.log('  game.html  toX/toY     ' + exArena.src.split('\n').length + ' lines');
console.log('  index.html wx/wy       ' + exHub.src.length + ' chars:  ' + exHub.src);

/* ---------- 1. warp matches the shipping arena EXACTLY ---------- */
console.log('\n[1] Projection.warp vs the REAL game.html warpScreen (1080x1920 backing px)');
var W = 1080, H = 1920, T = P.tilt({ deg: 18, persp: 1100 });
var wCases = [[540, 1920], [540, 0], [0, 960], [1080, 400], [137, 1733], [960, 12]];
var worst = 0;
wCases.forEach(function (c) {
  var mine = P.warp(c[0], c[1], W, H, T), real = realWarp(c[0], c[1]);
  var d = Math.max(Math.abs(mine.x - real.x), Math.abs(mine.y - real.y), Math.abs(mine.scale - real.scale));
  if (d > worst) worst = d;
  console.log('    (' + c[0] + ',' + c[1] + ') -> mine (' + mine.x.toFixed(4) + ',' + mine.y.toFixed(4) + ') scale ' + mine.scale.toFixed(6) +
              '  | real (' + real.x.toFixed(4) + ',' + real.y.toFixed(4) + ') scale ' + real.scale.toFixed(6));
});
ok('warp is bit-for-bit the shipping arena math', worst === 0, 'max abs delta = ' + worst);

/* ---------- 2. unwarp is an exact inverse ---------- */
console.log('\n[2] unwarp round-trip (the deploy-tap inverse)');
var rtWorst = 0;
wCases.forEach(function (c) {
  var f = P.warp(c[0], c[1], W, H, T), b = P.unwarp(f.x, f.y, W, H, T);
  var d = Math.max(Math.abs(b.x - c[0]), Math.abs(b.y - c[1]));
  if (d > rtWorst) rtWorst = d;
  console.log('    (' + c[0] + ',' + c[1] + ') -> warp -> unwarp -> (' + b.x.toFixed(9) + ',' + b.y.toFixed(9) + ')  err ' + d.toExponential(2));
});
ok('unwarp(warp(p)) === p', rtWorst < 1e-9, 'max err = ' + rtWorst.toExponential(3));
var idf = P.warp(500, 900, W, H, P.tilt({ deg: 0 }));
ok('tilt off is identity', idf.x === 500 && idf.y === 900 && idf.scale === 1);

/* ---------- 3. the hub identity: bridged wx/wy === original wx/wy ---------- */
console.log('\n[3] stage-1 vs the REAL index.html wx/wy');
HUB_CAM.x = 412.5; HUB_CAM.y = -97.25;
var hubState = P.state({ k: 1, tx: -HUB_CAM.x, ty: -HUB_CAM.y });
var hWorst = 0;
[[0, 0], [1000, 250], [-333.5, 1024.75], [77, -18]].forEach(function (c) {
  var mx = P.wx(hubState, c[0]), my = P.wy(hubState, c[1]);
  var rx = realHub.wx(c[0]), ry = realHub.wy(c[1]);
  var d = Math.max(Math.abs(mx - rx), Math.abs(my - ry));
  if (d > hWorst) hWorst = d;
  console.log('    world(' + c[0] + ',' + c[1] + ') -> mine (' + mx + ',' + my + ')  real (' + rx + ',' + ry + ')');
});
ok('k=1,tx=-cam.x reproduces the hub exactly', hWorst === 0, 'max delta = ' + hWorst);

/* ---------- 4. BattleCamera.adopt vs the REAL toX/toY ---------- */
console.log('\n[4] BattleCamera.adopt vs the REAL game.html toX/toY (non-uniform 1080x1920 over 1000x1800)');
ARENA_CAM = { offX: 120, offY: 340, zoom: 1.25 };
var bEnv = { state: P.state({}), opts: {}, vp: { w: 1080, h: 1920 }, _arena: { w: 1000, h: 1800 } };
BATTLE.adopt(bEnv, ARENA_CAM, 1000, 1800);
var bWorst = 0;
[[0, 0], [500, 900], [1000, 1800], [237.5, 1444.25]].forEach(function (c) {
  var mx = P.wx(bEnv.state, c[0]), my = P.wy(bEnv.state, c[1]);
  var rx = realArena.toX(c[0]), ry = realArena.toY(c[1]);
  var d = Math.max(Math.abs(mx - rx), Math.abs(my - ry));
  if (d > bWorst) bWorst = d;
  console.log('    arena(' + c[0] + ',' + c[1] + ') -> mine (' + mx.toFixed(4) + ',' + my.toFixed(4) + ')  real (' + rx.toFixed(4) + ',' + ry.toFixed(4) + ')');
});
ok('adopt() reproduces toX/toY exactly (this is why ky exists)', bWorst < 1e-9, 'max delta = ' + bWorst.toExponential(3));
var uni = P.state({ k: 0.6 });
ok('ky defaults to k for uniform modes', P.ky(uni) === 0.6);

/* ---------- 5. iso / unIso exact inverse at all 4 quarters ---------- */
console.log('\n[5] BuilderCamera grid round-trip, all 4 snap yaws');
var iWorst = 0;
for (var q = 0; q < 4; q++) {
  var st = P.state({ k: 1.7, tx: 311, ty: -42, quarter: q });
  [[0, 0], [12, -7], [-40.5, 33.25], [128, 128]].forEach(function (c) {
    var s2 = P.iso(st, c[0], c[1], 0), back = P.unIso(st, s2.x, s2.y);
    var d = Math.max(Math.abs(back.x - c[0]), Math.abs(back.y - c[1]));
    if (d > iWorst) iWorst = d;
  });
  var probe = P.iso(st, 10, 0, 0);
  console.log('    q=' + q + '  tile(10,0) -> screen (' + probe.x.toFixed(3) + ',' + probe.y.toFixed(3) + ')  depth ' + probe.depth.toFixed(2));
}
ok('unIso(iso(tile)) === tile at every quarter', iWorst < 1e-9, 'max err = ' + iWorst.toExponential(3));
var zst = P.state({ k: 2, tx: 0, ty: 0, quarter: 1 });
ok('height raises a tile on screen', P.iso(zst, 5, 5, 3).y < P.iso(zst, 5, 5, 0).y,
   'z=3 y=' + P.iso(zst, 5, 5, 3).y.toFixed(2) + ' vs z=0 y=' + P.iso(zst, 5, 5, 0).y.toFixed(2));

/* ---------- 6. zoomAt keeps the pinch anchor pinned ---------- */
console.log('\n[6] zoomAt anchor invariance (pinch focal point must not slide)');
var zs = P.state({ k: 1, ky: 1, tx: -200, ty: -50 });
var ax = 360, ay = 640;
var beforeW = { x: P.unwx(zs, ax), y: P.unwy(zs, ay) };
P.zoomAt(zs, 2.4, ax, ay);
var afterW = { x: P.unwx(zs, ax), y: P.unwy(zs, ay) };
console.log('    world under anchor before (' + beforeW.x.toFixed(6) + ',' + beforeW.y.toFixed(6) + ')  after (' + afterW.x.toFixed(6) + ',' + afterW.y.toFixed(6) + ')');
ok('world point under the anchor is invariant', near(beforeW.x, afterW.x, 1e-9) && near(beforeW.y, afterW.y, 1e-9));
var ns = P.state({ k: 1.08, ky: 1.0667 });
var aspect0 = ns.k / ns.ky; P.zoomAt(ns, 3.24, 100, 100);
ok('non-uniform aspect survives a pinch', near(aspect0, ns.k / ns.ky, 1e-12), 'aspect ' + aspect0.toFixed(9) + ' -> ' + (ns.k / ns.ky).toFixed(9));

/* ---------- 7. orbit + polar clamp + framing ---------- */
console.log('\n[7] orbit math');
var os2 = P.state({ theta: 0, phi: Math.PI / 2, dist: 10, focus: { x: 0, y: 0, z: 0 } });
var eye = P.orbitEye(os2);
console.log('    theta 0, phi 90deg, dist 10 -> eye (' + eye.x.toFixed(6) + ',' + eye.y.toFixed(6) + ',' + eye.z.toFixed(6) + ')');
ok('horizon orbit sits at radius on the ground plane', near(Math.hypot(eye.x, eye.z), 10, 1e-9) && near(eye.y, 0, 1e-9));
os2.phi = 0.0001;
ok('phi near 0 is overhead', near(P.orbitEye(os2).y, 10, 1e-6), 'y=' + P.orbitEye(os2).y.toFixed(6));
ok('clampPolar floors at the RPG min', P.clampPolar(-5, RPG.limits.PHI_MIN, RPG.limits.PHI_MAX) === RPG.limits.PHI_MIN);
ok('clampPolar ceils at the RPG max', P.clampPolar(99, RPG.limits.PHI_MIN, RPG.limits.PHI_MAX) === RPG.limits.PHI_MAX);
var d1 = P.frameDistance(1.0, 35, 1, 1.15), d2 = P.frameDistance(3.0, 35, 1, 1.15);
console.log('    frameDistance r=1 -> ' + d1.toFixed(4) + '   r=3 -> ' + d2.toFixed(4) + '   ratio ' + (d2 / d1).toFixed(6));
ok('framing distance is linear in subject radius', near(d2 / d1, 3, 1e-9));

/* ---------- 8. FPS weapon really is in VIEW space ---------- */
console.log('\n[8] FPS weapon view-space invariance');
var fpsEnv = { state: P.state({}), opts: { target: { x: 5, y: 0, z: -2 } }, vp: { w: 800, h: 600 }, three: null, ctx: null, degraded: false };
FPS.enter(fpsEnv);
var seen = [], resid = 0, orth = 0;
[[0, 0], [900, 0], [900, 300], [-1500, -200]].forEach(function (mv) {
  FPS.look(fpsEnv, mv[0], mv[1]);
  var wb = FPS.weaponBasis(fpsEnv, { right: 0.28, up: -0.22, fwd: 0.55 });
  var e = FPS.eye(fpsEnv), b = wb.basis;
  var vx = wb.pos.x - e.x, vy = wb.pos.y - e.y, vz = wb.pos.z - e.z;
  // project the eye->weapon vector back onto the camera basis. THE invariant: it must
  // come back as the offset that was placed, at any yaw/pitch. (Compared against
  // wb.offset, not the raw input, because sway/bob deliberately perturb the offset --
  // that perturbation is itself defined in view space and must survive the round-trip.)
  var pr = vx * b.right.x + vy * b.right.y + vz * b.right.z;
  var pu = vx * b.up.x    + vy * b.up.y    + vz * b.up.z;
  var pf = vx * b.fwd.x   + vy * b.fwd.y   + vz * b.fwd.z;
  resid = Math.max(resid, Math.abs(pr - wb.offset.right), Math.abs(pu - wb.offset.up), Math.abs(pf - wb.offset.fwd));
  // orthonormality of the basis itself, checked at every pitch we visit
  [b.fwd, b.right, b.up].forEach(function (v) { orth = Math.max(orth, Math.abs(Math.hypot(v.x, v.y, v.z) - 1)); });
  orth = Math.max(orth,
    Math.abs(b.fwd.x * b.right.x + b.fwd.y * b.right.y + b.fwd.z * b.right.z),
    Math.abs(b.fwd.x * b.up.x + b.fwd.y * b.up.y + b.fwd.z * b.up.z),
    Math.abs(b.right.x * b.up.x + b.right.y * b.up.y + b.right.z * b.up.z));
  seen.push({ pos: wb.pos });
  console.log('    yaw ' + fpsEnv.state.theta.toFixed(4) + ' pitch ' + fpsEnv.state.phi.toFixed(4) +
              ' -> world (' + wb.pos.x.toFixed(4) + ',' + wb.pos.y.toFixed(4) + ',' + wb.pos.z.toFixed(4) +
              ')  view (r ' + pr.toFixed(9) + ', u ' + pu.toFixed(9) + ', f ' + pf.toFixed(9) + ')');
});
ok('weapon resolves to its EXACT view-space offset at any look angle', resid < 1e-9, 'max residual = ' + resid.toExponential(3));
ok('the camera basis is orthonormal at every pitch', orth < 1e-12, 'max deviation = ' + orth.toExponential(3));
ok('weapon world position DOES move with the look',
   !near(seen[0].pos.x, seen[2].pos.x, 1e-6) || !near(seen[0].pos.z, seen[2].pos.z, 1e-6));
// pole check: the basis must stay orthonormal even looking straight up / straight down
[Math.PI / 2, -Math.PI / 2, 0].forEach(function (p) {
  var b2 = FPS.basis(0.77, p), dev = Math.abs(Math.hypot(b2.up.x, b2.up.y, b2.up.z) - 1);
  ok('up is unit-length at pitch ' + p.toFixed(4), dev < 1e-12, 'dev = ' + dev.toExponential(2));
});
// with sway settled, the offset the caller asked for is honoured verbatim
for (var wsi = 0; wsi < 60; wsi++) FPS.update(0.1, fpsEnv);
var settled = FPS.weaponBasis(fpsEnv, { right: 0.28, up: -0.22, fwd: 0.55 });
console.log('    settled offset: right ' + settled.offset.right.toFixed(6) + ' fwd ' + settled.offset.fwd.toFixed(6));
ok('sway decays back to the requested offset', near(settled.offset.right, 0.28, 1e-6));
FPS.look(fpsEnv, 0, -1e6);
ok('pitch clamps below vertical', Math.abs(fpsEnv.state.phi) <= FPS.PITCH_MAX, 'phi=' + fpsEnv.state.phi.toFixed(4));

/* ---------- 9. manager: exactly one mode renders ---------- */
console.log('\n[9] CameraManager single-active guarantee');
var log = [];
['probeA', 'probeB'].forEach(function (id) {
  CM.register({ id: id, dim: '2d',
    enter: function () { log.push('enter:' + id); },
    exit:  function () { log.push('exit:' + id); },
    update: function () { log.push('tick:' + id); },
    render: function () { log.push('draw:' + id); } });
});
ok('all 5 shipped modes registered', ['rpg', 'battle', 'builder', 'garage', 'fps'].every(function (m) { return !!CM.get(m); }), CM.list().join(','));
CM.switch('probeA', { fade: false });
CM.update(0.016); CM.render(null);
CM.switch('probeB', { fade: false });
CM.update(0.016); CM.render(null);
console.log('    ' + log.join('  '));
ok('switch exits the old mode before entering the new',
   log.indexOf('exit:probeA') > -1 && log.indexOf('exit:probeA') < log.indexOf('enter:probeB'));
ok('only the active mode ticks and draws',
   log.filter(function (l) { return l === 'tick:probeA'; }).length === 1 &&
   log.filter(function (l) { return l === 'draw:probeB'; }).length === 1 &&
   log.indexOf('draw:probeA') === log.lastIndexOf('draw:probeA'));
ok('active() reports the live mode', CM.active() === 'probeB');
CM.stop();
ok('stop() leaves nothing active', CM.active() === null);
ok('unknown mode is refused, not crashed', CM.switch('nope', { fade: false }) === null);

/* ---------- 10. the migration seam: bridge() moves the plugin systems ---------- */
console.log('\n[10] bridge() over the REAL AK_CTX.world.wx/wy');
HUB_CAM.x = 250; HUB_CAM.y = 100;
var ctx = { world: realHub, overlay: null };
var origX = ctx.world.wx(1000), origY = ctx.world.wy(500);
CM.attach(ctx);
CM.bridge(ctx);
ok('bridged with no active camera falls through to the original', ctx.world.wx(1000) === origX, 'wx(1000) = ' + ctx.world.wx(1000));
CM.register({ id: 'probeHub', dim: '2d', enter: function (env) {
  env.state.k = 1; env.state.ky = 1; env.state.tx = -HUB_CAM.x; env.state.ty = -HUB_CAM.y; } });
CM.switch('probeHub', { fade: false });
console.log('    identity camera:  wx(1000) = ' + ctx.world.wx(1000) + '   (original ' + origX + ')');
ok('identity camera is pixel-identical through the bridge', ctx.world.wx(1000) === origX && ctx.world.wy(500) === origY);
P.zoomAt(CM.state(), 2, 180, 320);
console.log('    after zoomAt(2x @180,320):  wx(1000) = ' + ctx.world.wx(1000).toFixed(3) + '   wy(500) = ' + ctx.world.wy(500).toFixed(3));
ok('zoom reaches the plugins through wx/wy', ctx.world.wx(1000) !== origX);
ok('the pinch anchor holds through the bridge', near(CM.screenToWorld(180, 320, 800, 1200).x, 180 + HUB_CAM.x, 1e-9),
   'screenToWorld(180) = ' + CM.screenToWorld(180, 320, 800, 1200).x.toFixed(6));
CM.unbridge();
ok('unbridge restores the original functions exactly', ctx.world.wx === realHub.wx && ctx.world.wx(1000) === origX);
CM.stop();

/* ---------- 11. 3D modes degrade to a documented no-op ---------- */
console.log('\n[11] no-THREE degradation (THREE is not in the repo yet)');
ok('hasThree() is false here', CM.hasThree() === false);
var gEnv = { state: P.state({}), opts: { subject: { x: 0, y: 0, z: 0, radius: 2.2 } }, vp: { w: 900, h: 1600 }, three: null, ctx: null, degraded: false };
GARAGE.enter(gEnv);
var th0 = gEnv.state.theta;
GARAGE.update(2.0, gEnv); GARAGE.update(2.0, gEnv);
var lts = GARAGE.lights(gEnv);
console.log('    dist ' + gEnv.state.dist.toFixed(4) + '  theta ' + th0.toFixed(4) + ' -> ' + gEnv.state.theta.toFixed(4) + '  lights ' + lts.map(function (l) { return l.id; }).join('/'));
ok('turntable keeps spinning with no renderer', gEnv.state.theta > th0);
ok('framing solved a real distance', gEnv.state.dist > 2.2 && isFinite(gEnv.state.dist));
ok('the 3-point rig resolves without THREE', lts.length === 3 && lts.every(function (l) { return isFinite(l.x) && isFinite(l.y) && isFinite(l.z); }));
ok('camera3() is null with no THREE', GARAGE.camera3() === null);
var rEnv = { state: P.state({}), opts: { target: { x: 40, y: 60 } }, vp: { w: 800, h: 1200 }, three: null, ctx: null, degraded: false };
RPG.enter(rEnv); RPG.update(0.5, rEnv); RPG.update(0.5, rEnv);
console.log('    RPG 2D fallback: k=' + rEnv.state.k + ' tx=' + rEnv.state.tx.toFixed(2) + ' ty=' + rEnv.state.ty.toFixed(2) + ' focus=(' + rEnv.state.focus.x.toFixed(2) + ',' + rEnv.state.focus.y.toFixed(2) + ')');
ok('RPG still produces a usable 2D follow transform',
   near(P.wx(rEnv.state, rEnv.state.focus.x), 400, 1e-6) && near(P.wy(rEnv.state, rEnv.state.focus.y), 600, 1e-6));

/* ---------- 12. builder gestures ---------- */
console.log('\n[12] BuilderCamera gestures');
var buEnv = { state: P.state({}), opts: {}, vp: { w: 720, h: 1280 }, three: null, ctx: null, degraded: false };
BUILDER.enter(buEnv);
var q0 = buEnv.state.quarter;
var c1 = P.unIso(buEnv.state, 360, 640);
BUILDER.rotate(buEnv, 1);
var c2 = P.unIso(buEnv.state, 360, 640);
console.log('    quarter ' + q0 + ' -> ' + buEnv.state.quarter + '   centre tile (' + c1.x.toFixed(4) + ',' + c1.y.toFixed(4) + ') -> (' + c2.x.toFixed(4) + ',' + c2.y.toFixed(4) + ')');
ok('rotate advances one 90deg snap', buEnv.state.quarter === (q0 + 1) % 4);
ok('rotate pins the tile under screen centre', near(c1.x, c2.x, 1e-9) && near(c1.y, c2.y, 1e-9));
var tx0 = buEnv.state.tx;
BUILDER.pointer({ type: 'pointerdown', pointerId: 1, clientX: 100, clientY: 100 }, buEnv);
BUILDER.pointer({ type: 'pointermove', pointerId: 1, clientX: 160, clientY: 130 }, buEnv);
ok('one-finger drag pans', near(buEnv.state.tx, tx0 + 60, 1e-9), 'tx ' + tx0.toFixed(2) + ' -> ' + buEnv.state.tx.toFixed(2));
ok('a moved finger is a pan, not a tap',
   BUILDER.pointer({ type: 'pointerup', pointerId: 1, clientX: 160, clientY: 130 }, buEnv) === null);
BUILDER.pointer({ type: 'pointerdown', pointerId: 2, clientX: 300, clientY: 500 }, buEnv);
var tap2 = BUILDER.pointer({ type: 'pointerup', pointerId: 2, clientX: 300, clientY: 500 }, buEnv);
ok('a still finger returns the tile it hit', !!(tap2 && tap2.kind === 'tile' && isFinite(tap2.tile.x)),
   tap2 ? ('tile ' + tap2.tile.x.toFixed(3) + ',' + tap2.tile.y.toFixed(3)) : 'none');
var k0 = buEnv.state.k;
BUILDER.pointer({ type: 'wheel', deltaY: -240, clientX: 360, clientY: 640 }, buEnv);
ok('wheel zooms in', buEnv.state.k > k0, k0.toFixed(4) + ' -> ' + buEnv.state.k.toFixed(4));
BUILDER.pointer({ type: 'wheel', deltaY: -1e6, clientX: 360, clientY: 640 }, buEnv);
ok('zoom clamps at K_MAX', buEnv.state.k === BUILDER.K_MAX, 'k=' + buEnv.state.k);

/* ---------- 13. battle camera refuses player input ---------- */
console.log('\n[13] BattleCamera is FIXED');
var baEnv = { state: P.state({}), opts: {}, vp: { w: 1080, h: 1920 }, three: null, ctx: null, degraded: false };
BATTLE.enter(baEnv);
var snap = JSON.stringify(baEnv.state);
BATTLE.pointer({ type: 'pointerdown', pointerId: 1, clientX: 10, clientY: 10 }, baEnv);
BATTLE.pointer({ type: 'pointermove', pointerId: 1, clientX: 400, clientY: 900 }, baEnv);
BATTLE.pointer({ type: 'wheel', deltaY: -500, clientX: 500, clientY: 500 }, baEnv);
console.log('    tilt ' + baEnv.state.tilt.deg + 'deg persp ' + baEnv.state.tilt.persp + '  k ' + baEnv.state.k.toFixed(6));
ok('drag/pinch/wheel cannot move the battle camera', JSON.stringify(baEnv.state) === snap);
ok('battle tilt matches the shipping arena (18deg / 1100px)', baEnv.state.tilt.deg === 18 && baEnv.state.tilt.persp === 1100);

/* ---------- 14. the BROWSER path (script tags), not just the node path ---------- *
 * Sections 1-13 exercise the CommonJS branch. Production loads these as <script> tags,
 * which takes the OTHER branch of every module header (root.AK_PROJ instead of
 * require). Run the real files in a bare vm context with NO `module` defined, in the
 * exact order the index.html tags would, and confirm the globals wire themselves up. */
console.log('\n[14] browser <script> load order (no CommonJS, real files, vm sandbox)');
var vm = require('vm');
var sandbox = { console: console, Math: Math, Date: Date, isFinite: isFinite, performance: { now: Date.now } };
sandbox.window = sandbox; sandbox.globalThis = sandbox;
var ctxVm = vm.createContext(sandbox);
var ORDER = ['Projection.js', 'Gestures.js', 'CameraManager.js',
             'RPGCamera.js', 'BattleCamera.js', 'BuilderCamera.js', 'GarageCamera.js', 'FPSCamera.js'];
ORDER.forEach(function (f) { vm.runInContext(fs.readFileSync(path.join(HERE, f), 'utf8'), ctxVm, { filename: f }); });
console.log('    globals: ' + ['AK_PROJ', 'AK_GESTURE', 'AK_CAMERAS'].map(function (g) { return g + '=' + (typeof sandbox[g]); }).join('  '));
console.log('    registered: ' + sandbox.AK_CAMERAS.list().join(','));
ok('all three globals attach in browser mode',
   typeof sandbox.AK_PROJ === 'object' && typeof sandbox.AK_GESTURE === 'object' && typeof sandbox.AK_CAMERAS === 'object');
ok('all 5 modes self-register via script tags',
   ['rpg', 'battle', 'builder', 'garage', 'fps'].every(function (m) { return !!sandbox.AK_CAMERAS.get(m); }));
ok('browser-mode manager sees no THREE and no DOM', sandbox.AK_CAMERAS.hasThree() === false);
sandbox.AK_CAMERAS.switch('builder', { fade: false });
ok('a switch works with no document present', sandbox.AK_CAMERAS.active() === 'builder');
ok('browser-mode math agrees with node-mode math',
   sandbox.AK_PROJ.warp(137, 1733, 1080, 1920, sandbox.AK_PROJ.tilt({ deg: 18, persp: 1100 })).x
   === P.warp(137, 1733, 1080, 1920, T).x);
sandbox.AK_CAMERAS.stop();

try { fs.rmSync(TMP, { recursive: true, force: true }); } catch (_e) {}
console.log('\n' + (fail === 0 ? 'ALL GREEN' : 'FAILURES PRESENT') + ':  ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
