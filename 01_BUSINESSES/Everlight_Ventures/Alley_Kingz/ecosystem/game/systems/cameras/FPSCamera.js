/* ALLEY KINGZ -- FPS CAMERA (first person, eye level). AK-CAM 2026-07-18.
 *
 * Eye at the hero's head height, yaw/pitch from drag (or pointer-lock movementX/Y),
 * pitch hard-clamped just short of straight up and straight down so the horizon can
 * never roll over.
 *
 * WEAPON IN VIEW SPACE is the part that matters and the part people get wrong. The
 * weapon does NOT live in the world and get chased by the camera; it is pinned to a
 * fixed offset in the camera's OWN basis (right/up/forward), so it is rock steady in
 * frame no matter where you look. weaponBasis() returns that basis plus the resolved
 * world position, so a host can either parent a THREE model to the camera (the cheap
 * path) or place it in world space at the returned transform (needed if the weapon
 * has to cast into the same shadow map as the level).
 *
 * Sway and bob are added in view space too: they perturb the OFFSET, never the camera,
 * so the crosshair stays exactly where the player aimed while the gun breathes.
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

  var PITCH_MAX = 1.50;            // rad, just under 90deg: never gimbal over the top
  var LOOK_RATE = 0.0032;          // rad per px
  var EYE_H = 1.62;                // m, eye height above the hero's feet
  var FOV = 72;
  var WEAP = { right: 0.28, up: -0.22, fwd: 0.55 };    // view-space weapon anchor
  var g = null, cam3 = null, bob = 0, sway = { x: 0, y: 0 };

  function hero(env) {
    var c = env.ctx;
    try { if (c && c.world && c.world.g && c.world.g.me) return c.world.g.me; } catch (_e) {}
    return (env.opts && env.opts.target) || { x: 0, y: 0, z: 0 };
  }

  function enter(env) {
    var s = env.state, o = env.opts || {};
    s.theta = (o.yaw != null) ? o.yaw : 0;
    s.phi = 0;                                  // reuse phi as PITCH here (0 = level horizon)
    s.dist = 0;                                 // first person: the eye IS the focus
    s.tilt = P.tilt({ deg: 0 });
    var h = hero(env);
    s.focus.x = h.x || 0; s.focus.y = (h.y || 0); s.focus.z = h.z || 0;
    bob = 0; sway.x = 0; sway.y = 0;
    g = G.create({ tapSlop: 6 });
    if (env.three) {
      cam3 = new env.three.PerspectiveCamera((o.fov || FOV), (env.vp.w && env.vp.h) ? env.vp.w / env.vp.h : 1, 0.05, 3000);
      apply(env);
    } else { cam3 = null; }                     // documented no-op: look state still live
  }

  function exit() { g = null; cam3 = null; }

  /* Camera basis from yaw/pitch. Right-handed, +Y up, forward is -Z at yaw 0.
   * up is exactly cross(right, fwd), which stays unit-length and orthogonal at EVERY
   * pitch including straight up and straight down. (An earlier draft special-cased
   * cos(pitch)===0 here and got the pole wrong; _probe.js section 8 now asserts
   * orthonormality across the full pitch range so that cannot come back.) */
  function basis(yaw, pitch) {
    var cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    return {
      fwd:   { x: sy * cp, y: sp, z: -cy * cp },
      right: { x: cy, y: 0, z: sy },
      up:    { x: -sy * sp, y: cp, z: cy * sp }
    };
  }

  function eye(env) {
    var s = env.state, h = hero(env);
    return { x: h.x || 0, y: (h.y || 0) + EYE_H, z: h.z || 0 };
  }

  /* View-space weapon transform resolved to world. offset is in the camera basis, so
   * it is invariant under look: this is the definition of "weapon in view space". */
  function weaponBasis(env, offset) {
    var s = env.state, b = basis(s.theta, s.phi), e = eye(env);
    var o = offset || WEAP;
    var rx = o.right + sway.x, uy = o.up + sway.y + Math.sin(bob) * 0.012, fz = o.fwd;
    return {
      basis: b,
      pos: {
        x: e.x + b.right.x * rx + b.up.x * uy + b.fwd.x * fz,
        y: e.y + b.right.y * rx + b.up.y * uy + b.fwd.y * fz,
        z: e.z + b.right.z * rx + b.up.z * uy + b.fwd.z * fz
      },
      yaw: s.theta, pitch: s.phi, offset: { right: rx, up: uy, fwd: fz }
    };
  }

  function apply(env) {
    if (!cam3) return;
    var s = env.state, e = eye(env), b = basis(s.theta, s.phi);
    cam3.position.set(e.x, e.y, e.z);
    cam3.lookAt(e.x + b.fwd.x, e.y + b.fwd.y, e.z + b.fwd.z);
    if (env.vp.w && env.vp.h) { cam3.aspect = env.vp.w / env.vp.h; cam3.updateProjectionMatrix(); }
  }

  function update(dt, env) {
    var s = env.state, h = hero(env);
    var mv = Math.hypot((h.vx || 0), (h.vy || 0), (h.vz || 0));
    bob += dt * (4 + mv * 1.4);
    // sway eases back to centre whenever the look stops moving
    sway.x = P.damp(sway.x, 0, 6, dt);
    sway.y = P.damp(sway.y, 0, 6, dt);
    s.focus.x = h.x || 0; s.focus.y = h.y || 0; s.focus.z = h.z || 0;
    apply(env);
  }

  function pointer(e, env) {
    if (!g) return;
    var s = env.state;
    // pointer-lock path: the browser hands deltas directly, no drag state needed
    if (e && (e.movementX != null || e.movementY != null) && root && root.document && root.document.pointerLockElement) {
      look(env, e.movementX || 0, e.movementY || 0);
      return;
    }
    var v = g.feed(e);
    if (v.kind === 'drag') look(env, v.dx, v.dy);
  }

  function look(env, dx, dy) {
    var s = env.state;
    s.theta += dx * LOOK_RATE;
    s.phi = P.clamp(s.phi - dy * LOOK_RATE, -PITCH_MAX, PITCH_MAX);
    sway.x = P.clamp(sway.x - dx * 0.00035, -0.05, 0.05);     // gun lags the turn a hair
    sway.y = P.clamp(sway.y + dy * 0.00035, -0.05, 0.05);
  }

  function render(g2d, env) { return; }

  return {
    id: 'fps', dim: '3d', needsThree: false,
    enter: enter, exit: exit, update: update, render: render, pointer: pointer,
    weaponBasis: weaponBasis, basis: basis, eye: eye, look: look,
    camera3: function () { return cam3; },
    PITCH_MAX: PITCH_MAX, EYE_H: EYE_H, WEAP: WEAP
  };
});
