/* ALLEY KINGZ -- RPG CAMERA (third-person orbit, WoW style). AK-CAM 2026-07-18.
 *
 * Drag to orbit, pinch or wheel to zoom, polar angle clamped so you can never flip
 * under the ground or stare straight down the hero's head.
 *
 * DEGRADED (no THREE) IS STILL USEFUL, and that is deliberate: the orbit state keeps
 * running and the stage-1 projection keeps FOLLOWING the hero, so with AK_CAMERAS
 * bridged onto AK_CTX.world.wx/wy this mode is a working 2D follow-cam for the
 * existing Canvas2D hub today, with zoom, before Three.js is ever added. When THREE
 * lands, the same theta/phi/dist drive a real PerspectiveCamera and nothing else moves.
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

  var PHI_MIN = 0.30, PHI_MAX = 1.42;         // rad: ~17deg above horizon .. ~81deg, never under the floor
  var DIST_MIN = 3.5, DIST_MAX = 26;
  var ORBIT_RATE = 0.006;                     // rad per px of drag
  var ZOOM_2D_MIN = 0.55, ZOOM_2D_MAX = 2.6;  // stage-1 k range used by the 2D fallback

  var g = null, cam3 = null, tgt = null;      // gesture tracker, THREE camera, smoothed focus

  function hero(env) {
    // real hero position: the hub's own player, else whatever the caller pinned
    var c = env.ctx;
    try { if (c && c.world && c.world.g && c.world.g.me) return c.world.g.me; } catch (_e) {}
    return (env.opts && env.opts.target) || { x: 0, y: 0, z: 0 };
  }

  function enter(env) {
    var s = env.state;
    s.theta = (env.opts.theta != null) ? env.opts.theta : -Math.PI / 2;
    s.phi   = P.clampPolar((env.opts.phi != null) ? env.opts.phi : 1.05, PHI_MIN, PHI_MAX);
    s.dist  = P.clamp((env.opts.dist != null) ? env.opts.dist : 11, DIST_MIN, DIST_MAX);
    s.tilt  = P.tilt({ deg: 0 });               // stage 2 off: the orbit IS the perspective
    if (!(s.k > 0)) s.k = 1;
    g = G.create({ tapSlop: 8 });
    var h = hero(env); tgt = { x: h.x || 0, y: h.y || 0, z: h.z || 0 };
    s.focus.x = tgt.x; s.focus.y = tgt.y; s.focus.z = tgt.z;

    if (env.three) {
      var T = env.three, w = env.vp.w || 1, hgt = env.vp.h || 1;
      cam3 = new T.PerspectiveCamera(55, w / Math.max(1, hgt), 0.1, 4000);
      applyThree(env);
    } else { cam3 = null; }                     // documented no-op: state still live
  }

  function exit() { g = null; cam3 = null; tgt = null; }

  function applyThree(env) {
    if (!cam3) return;
    var s = env.state, e = P.orbitEye(s);
    cam3.position.set(e.x, e.y, e.z);
    cam3.lookAt(s.focus.x, s.focus.y, s.focus.z);
    if (env.vp.w && env.vp.h) { cam3.aspect = env.vp.w / env.vp.h; cam3.updateProjectionMatrix(); }
  }

  function update(dt, env) {
    var s = env.state, h = hero(env);
    // follow the hero with framerate-independent damping (no snap on a teleport spike)
    tgt = tgt || { x: 0, y: 0, z: 0 };
    tgt.x = P.damp(tgt.x, h.x || 0, 9, dt);
    tgt.y = P.damp(tgt.y, h.y || 0, 9, dt);
    tgt.z = P.damp(tgt.z, h.z || 0, 9, dt);
    s.focus.x = tgt.x; s.focus.y = tgt.y; s.focus.z = tgt.z;

    // STAGE 1 stays live in BOTH paths. This is what keeps the 15 bridged plugin
    // systems centred on the hero, with zoom, whether or not THREE exists.
    var w = env.vp.w || 0, hgt = env.vp.h || 0;
    if (w && hgt) P.lookAt(s, tgt.x, tgt.y, w, hgt);
    applyThree(env);
  }

  function zoomBy(env, mul, ax, ay) {
    var s = env.state;
    s.dist = P.clamp(s.dist / mul, DIST_MIN, DIST_MAX);          // pinch out = closer
    var k = P.clamp(s.k * mul, ZOOM_2D_MIN, ZOOM_2D_MAX);
    if (env.vp.w && env.vp.h) P.zoomAt(s, k, (ax == null ? env.vp.w / 2 : ax), (ay == null ? env.vp.h / 2 : ay));
    else s.k = k;
  }

  function pointer(e, env) {
    if (!g) return;
    var v = g.feed(e), s = env.state;
    if (v.kind === 'drag') {
      s.theta += v.dx * ORBIT_RATE;
      s.phi = P.clampPolar(s.phi - v.dy * ORBIT_RATE, PHI_MIN, PHI_MAX);
    } else if (v.kind === 'pinch') {
      zoomBy(env, v.scale, v.cx, v.cy);
    } else if (v.kind === 'wheel') {
      zoomBy(env, v.scale, v.x, v.y);
    }
  }

  function render(g2d, env) {
    // 3D draw belongs to the host renderer once THREE is present (env.camera3 is the
    // camera to feed it). Nothing to paint here in the 2D path: the bridged wx/wy
    // already moved the whole existing hub render onto this camera.
    if (!env.three) return;
  }

  return {
    id: 'rpg', dim: '3d', needsThree: false,      // false: the 2D fallback is real, not a stub
    enter: enter, exit: exit, update: update, render: render, pointer: pointer,
    camera3: function () { return cam3; },
    limits: { PHI_MIN: PHI_MIN, PHI_MAX: PHI_MAX, DIST_MIN: DIST_MIN, DIST_MAX: DIST_MAX }
  };
});
