/* ALLEY KINGZ -- BUILDER CAMERA (isometric, Clash of Clans). AK-CAM 2026-07-18.
 *
 * Pan with one finger, pinch or wheel to zoom, rotate in 90deg SNAPS only. Snapped
 * rotation is what keeps a base-builder legible: every building stays axis-aligned to
 * the grid at all four yaws, so art never needs an off-angle variant and tap targets
 * stay square.
 *
 * The grid math is P.iso/P.unIso, which are exact inverses, so a tap round-trips to
 * the same tile it was drawn on at any zoom, pan or quarter turn. That is the property
 * a placement UI lives or dies on, and it is proven with real numbers in _probe.js.
 *
 * Pan/zoom deliberately mirror worldmap.js:682's WM {cam:{x,y}, scale} feel so the
 * two map surfaces read as one game; the difference is that WM's cam is bespoke and
 * this one is the shared CamState every other mode also speaks.
 */
(function (root, factory) {
  var isNode = (typeof module === 'object' && module.exports);
  var CM = isNode ? require('./CameraManager.js') : (root && root.AK_CAMERAS);
  var G  = isNode ? require('./Gestures.js')      : (root && root.AK_GESTURE);
  var P  = (CM && CM.P) || (root && root.AK_PROJ);
  var mode = factory(P, G, root);
  if (CM && CM.register) CM.register(mode);
  if (isNode) module.exports = mode;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function (P, G, root) {
  'use strict';

  var K_MIN = 0.35, K_MAX = 3.2;
  var SNAP_RATE = 9;                    // rad/s-ish damping toward the target quarter
  var g = null, spin = null;            // gesture tracker, {from, to, t} snap animation

  function enter(env) {
    var s = env.state, o = env.opts || {};
    s.k = P.clamp(o.k != null ? o.k : 1, K_MIN, K_MAX);
    s.quarter = ((o.quarter | 0) % 4 + 4) % 4;
    s.tilt = P.tilt({ deg: 0 });        // iso IS the projection; no stage-2 warp
    s.theta = s.quarter * Math.PI / 2;  // continuous angle, damped toward the snap
    spin = null;
    g = G.create({ tapSlop: 9 });
    if (o.center) centerOn(env, o.center.x, o.center.y);
    else if (env.vp.w && env.vp.h) { s.tx = env.vp.w / 2; s.ty = env.vp.h / 2; }
  }

  function exit() { g = null; spin = null; }

  /* Put a WORLD tile at the middle of the screen. Solves tx/ty from the iso forward
   * map with the translate zeroed, so it is exact at any quarter and any zoom. */
  function centerOn(env, wxp, wyp) {
    var s = env.state, w = env.vp.w || 0, h = env.vp.h || 0;
    if (!(w > 0 && h > 0)) return s;
    var zero = { k: s.k, tx: 0, ty: 0, quarter: s.quarter };
    var p = P.iso(zero, wxp, wyp, 0);
    s.tx = w / 2 - p.x; s.ty = h / 2 - p.y;
    return s;
  }

  /* 90deg snap turn. Keeps the tile under screen-center pinned so the base does not
   * fly off when you rotate. */
  function rotate(env, dir) {
    var s = env.state, w = env.vp.w || 0, h = env.vp.h || 0;
    var keep = (w > 0 && h > 0) ? P.unIso(s, w / 2, h / 2) : null;
    var from = s.theta;
    s.quarter = ((s.quarter + (dir < 0 ? -1 : 1)) % 4 + 4) % 4;
    spin = { from: from, to: s.quarter * Math.PI / 2, t: 0 };
    if (keep) centerOn(env, keep.x, keep.y);
    return s.quarter;
  }

  function update(dt, env) {
    var s = env.state;
    if (spin) {                          // cosmetic easing of the continuous angle only;
      s.theta = P.dampAngle(s.theta, spin.to, SNAP_RATE, dt);   // s.quarter already snapped
      if (Math.abs(P.shortAngle(s.theta, spin.to)) < 0.002) { s.theta = spin.to; spin = null; }
    }
  }

  function pointer(e, env) {
    if (!g) return null;
    var v = g.feed(e), s = env.state;
    if (v.kind === 'drag') { s.tx += v.dx; s.ty += v.dy; }
    else if (v.kind === 'pinch') {
      P.zoomAt(s, P.clamp(s.k * v.scale, K_MIN, K_MAX), v.cx, v.cy);
      s.tx += v.dx; s.ty += v.dy;        // two-finger pan rides along with the pinch
    } else if (v.kind === 'wheel') {
      P.zoomAt(s, P.clamp(s.k * v.scale, K_MIN, K_MAX), v.x, v.y);
    } else if (v.kind === 'tap') {
      return { kind: 'tile', tile: P.unIso(s, v.x, v.y) };   // caller places/selects here
    }
    return null;
  }

  function render(g2d, env) { return; }   // the build surface owns its own draw

  return {
    id: 'builder', dim: '2d', needsThree: false,
    enter: enter, exit: exit, update: update, render: render, pointer: pointer,
    rotate: rotate, centerOn: centerOn, K_MIN: K_MIN, K_MAX: K_MAX
  };
});
