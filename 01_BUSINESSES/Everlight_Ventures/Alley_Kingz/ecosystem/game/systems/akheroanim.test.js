/* game/systems/akheroanim.test.js -- headless proof for AK_HEROANIM.
 * AK-HEROANIM-TEST 2026-07-20   run: node systems/akheroanim.test.js
 *
 * WHAT THIS CAN AND CANNOT PROVE
 * The interesting half of this module (does model-viewer's mixer keep ticking?) is a BROWSER
 * fact and was measured in chromium on e5 -- see the sweep table in akheroanim.js's header. What
 * IS provable without a DOM is the arithmetic those browser findings drove, and that arithmetic
 * is where a silent regression would hide:
 *
 *   1. keepAlive() geometry. The measured rule is absolute: one pixel of overlap keeps the mixer
 *      alive, zero pixels freezes it. So the ONLY thing that matters is that keepAlive never
 *      leaves the rect fully outside, and never moves a rect that was already touching. An
 *      off-by-one here silently reintroduces the exact freeze the module exists to prevent, and
 *      it would not throw -- it would just look like the original bug.
 *   2. smooth() hysteresis. Starts must be instant (a held start that lags is a worse bug than
 *      the one being fixed) and stops must be held long enough to swallow threshold chatter.
 *
 * The module is a browser IIFE that assigns window.AK_HEROANIM and reads requestAnimationFrame,
 * performance and document at load, so it is run inside a node `vm` context holding a minimal
 * fake window. That also proves the file is loadable with NO game present -- which is what
 * happens if the <script> tag ever lands above hub3d.js.
 *
 * Exit code 0 = pass, 1 = fail.
 */
'use strict';

var fs = require('fs');
var path = require('path');
var vm = require('vm');

var fails = 0, checks = 0;
function ok(cond, msg) {
  checks++;
  if (!cond) { fails++; console.log('  FAIL  ' + msg); }
  else console.log('  ok    ' + msg);
}

/* ---- minimal browser shim -------------------------------------------------------------------
 * requestAnimationFrame is a no-op that never re-arms, so loading the module does not spawn an
 * endless loop in node. performance.now is driven by a clock WE control, which is what makes the
 * hysteresis test deterministic instead of sleep-based and flaky. */
var sandbox = {
  innerWidth: 900,
  innerHeight: 1500,
  requestAnimationFrame: function () { return 0; },
  setInterval: function () { return 0; },
  clearInterval: function () {},
  performance: { now: function () { return sandbox.__clock; } },
  document: { querySelectorAll: function () { return []; } },
  console: console,
  __clock: 1000
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, 'akheroanim.js'), 'utf8'), sandbox,
                { filename: 'akheroanim.js' });
var A = sandbox.AK_HEROANIM;
function setClock(ms) { sandbox.__clock = ms; }

console.log('AK_HEROANIM headless proof');
console.log('--------------------------');
ok(!!A, 'module loads with no game present and exports an object');
ok(typeof A._keepAlive === 'function', 'exposes _keepAlive test seam');
ok(typeof A._smooth === 'function', 'exposes _smooth test seam');
ok(A.isInstalled() === false, 'does not claim installed when there is no window.__hero3d');

/* ---- 1. keepAlive geometry ---------------------------------------------------------------- */
console.log('\nkeepAlive() -- the rect must never end up fully outside the viewport');

// a fake element carrying only the style numbers hub3d writes (px strings, as in hub3d.js:216-219)
function el(l, t, w, h) {
  return { style: { left: l + 'px', top: t + 'px', width: w + 'px', height: h + 'px' } };
}
function rectOf(e) {
  return { l: parseFloat(e.style.left), t: parseFloat(e.style.top),
           w: parseFloat(e.style.width), h: parseFloat(e.style.height) };
}
// the SAME predicate the browser sweep used: does the rect touch the viewport at all?
function touches(r, vw, vh) {
  return r.l < vw && (r.l + r.w) > 0 && r.t < vh && (r.t + r.h) > 0;
}

var VW = 900, VH = 1500;
var W = 72, H = 120;   // element size from the browser sweep (live valid boot measured 79x132 at r=23)

// cases that are already on screen must be left EXACTLY alone -- clamping a visible hero would
// visibly teleport him, which is a worse bug than the one being fixed.
[[414, 690, 'dead centre'], [0, 690, 'flush left'], [-36, 690, 'half off left'],
 [-71, 690, 'one pixel on (the measured boundary case)'], [828, 690, 'flush right'],
 [864, 690, 'half off right'], [414, 1499, 'one pixel on at the bottom']
].forEach(function (c) {
  var e = el(c[0], c[1], W, H);
  var before = rectOf(e);
  var moved = A._keepAlive(e);
  var after = rectOf(e);
  ok(moved === false && after.l === before.l && after.t === before.t,
     'leaves a touching rect untouched: ' + c[2] + ' (left=' + c[0] + ')');
});

// cases fully outside must be pulled back to touching
[[-90, 690, 'fully off left'], [920, 690, 'fully off right'], [414, 1520, 'fully off bottom'],
 [414, -130, 'fully off top'], [-500, -400, 'off both top-left'], [2000, 3000, 'far off bottom-right'],
 [1203, 592, 'the real frozen reading from the invalid-boot run']
].forEach(function (c) {
  var e = el(c[0], c[1], W, H);
  ok(!touches(rectOf(e), VW, VH), 'precondition: ' + c[2] + ' really is fully outside');
  var moved = A._keepAlive(e);
  var after = rectOf(e);
  ok(moved === true, 'clamped: ' + c[2]);
  ok(touches(after, VW, VH),
     '  -> now touches the viewport (left=' + after.l + ' top=' + after.t + ')');
  ok(isFinite(after.l) && isFinite(after.t), '  -> and wrote finite numbers, not NaN');
});

// garbage in must not produce NaN out -- hub3d writes these values as strings, and a NaN left/top
// would park the hero at position:fixed;left:NaNpx, which browsers resolve to 0 and would
// teleport him to the corner.
[[el(NaN, 10, W, H), 'NaN left'], [el(10, 10, 0, 0), 'zero size'],
 [{ style: {} }, 'empty style'], [null, 'null element']
].forEach(function (c) {
  var moved;
  try { moved = A._keepAlive(c[0]); } catch (e2) { moved = 'THREW: ' + e2.message; }
  ok(moved === false, 'refuses garbage without throwing or writing: ' + c[1]);
});

/* ---- 2. smooth() hysteresis ---------------------------------------------------------------- */
console.log('\nsmooth() -- instant starts, held stops');

A._setHolds(180, 220);   // the shipped values, restated so the test fails if they are edited away

setClock(10000);
ok(A._smooth(false, false) === false, 'still -> not moving');
ok(A._smooth(true, false) === true, 'first moving frame passes through INSTANTLY (no start lag)');

// one dropped frame mid-walk (avMoving = _mv > 0.2 chattering) must not reach hub3d
setClock(10016); ok(A._smooth(false, false) === true, 'a single dropped frame at +16ms is swallowed');
setClock(10032); ok(A._smooth(false, false) === true, 'still swallowed at +32ms');
setClock(10100); ok(A._smooth(false, false) === true, 'still swallowed at +100ms');
setClock(10179); ok(A._smooth(false, false) === true, 'still held at +179ms (just inside STOP_HOLD_MS=180)');
setClock(10181); ok(A._smooth(false, false) === false, 'a REAL stop is reported at +181ms (just past the hold)');

// the hold must re-arm on every moving frame, not run from the first one
setClock(20000); A._smooth(true, false);
setClock(20150); ok(A._smooth(true, false) === true, 'moving again at +150ms');
setClock(20300); ok(A._smooth(false, false) === true, 'hold restarts from the LAST moving frame');
setClock(20331); ok(A._smooth(false, false) === false, 'and expires 180ms after THAT one');

// running must never be reported while not moving. hub3d picks run only when moving is true
// (hub3d.js:240), but a stale running flag surviving a stop would bind the run clip to an idle dog.
setClock(30000); A._smooth(true, true);
ok(A.state().running === true, 'running passes through while moving');
setClock(30500); A._smooth(false, false);
ok(A.state().moving === false, 'stopped after the hold');
ok(A.state().running === false, 'running is forced false once moving is false');

/* ---- 3. diag surface ------------------------------------------------------------------------ */
console.log('\ndiag()');
var d = A.diag();
ok(d.clamps > 0, 'diag counts the clamps this test triggered (' + d.clamps + ')');
ok(d.chatterSwallowed > 0, 'diag counts swallowed chatter frames (' + d.chatterSwallowed + ')');
ok(d.tunables.KEEP_IN >= 1, 'KEEP_IN is at least the 1px the browser sweep proved is required');
ok(d.tunables.STOP_HOLD_MS >= 100 && d.tunables.STOP_HOLD_MS <= 600,
   'STOP_HOLD_MS stays between "swallows frame chatter" and "under one 600ms footfall"');

console.log('\n--------------------------');
console.log(fails ? ('FAILED ' + fails + '/' + checks) : ('PASSED ' + checks + '/' + checks));
process.exit(fails ? 1 : 0);
