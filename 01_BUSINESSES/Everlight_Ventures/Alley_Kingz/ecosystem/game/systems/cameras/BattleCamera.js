/* ALLEY KINGZ -- BATTLE CAMERA (fixed orthographic, Clash Royale). AK-CAM 2026-07-18.
 *
 * FIXED by design: no orbit, no player zoom, no pan during play. The arena is a
 * readable board, and a board the player can rotate stops being readable. pointer()
 * returns without touching state so a stray drag can never nudge the framing.
 *
 * This mode does NOT invent a look. It ADOPTS the battler's shipping camera:
 *   engine.js:1406  camera {offX, offY, zoom}   (the section-pan / identity-by-default cam)
 *   game.html:2861  TILT_DEG 18, PERSP_PX 1100  (the arena recession)
 * adopt() maps that struct straight onto CamState, so the two cannot drift apart:
 * offX/offY/zoom become stage 1, the 18deg tilt becomes stage 2, and screenToWorld()
 * inherits the arena's exact closed-form un-projection for deploy taps.
 *
 * "~45 degrees" is the Clash-Royale READ, not a literal 45deg rotateX. The shipping
 * arena gets that read from an 18deg perspective recession over a 2:1-ish board, which
 * is why DEG defaults to the arena's real 18 rather than a number that would not match
 * the pixels players already see. Pass {deg:45} to enter() if a mode wants the steeper
 * look; the math is identical either way.
 */
(function (root, factory) {
  var isNode = (typeof module === 'object' && module.exports);
  var CM = isNode ? require('./CameraManager.js') : (root && root.AK_CAMERAS);
  var P  = (CM && CM.P) || (root && root.AK_PROJ);
  var mode = factory(P, root);
  if (CM && CM.register) CM.register(mode);
  if (isNode) module.exports = mode;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function (P, root) {
  'use strict';

  var DEG = 18, PERSP = 1100;                  // game.html:2861 TILT2_DEG / PERSP2_PX
  var ARENA_W = 1000, ARENA_H = 1800;          // logical board; overridden via opts.arena

  function enter(env) {
    var s = env.state, o = env.opts || {};
    var aw = (o.arena && o.arena.w) || ARENA_W, ah = (o.arena && o.arena.h) || ARENA_H;
    s.tilt = P.tilt({ deg: (o.deg != null ? o.deg : DEG), persp: (o.persp != null ? o.persp : PERSP) });
    s.quarter = 0; s.theta = 0; s.phi = 0;
    fit(env, aw, ah);
    if (o.camera) adopt(env, o.camera, aw, ah);   // take the battler's live cam if handed one
    env._arena = { w: aw, h: ah };
  }

  /* Fit the whole board in the viewport (letterboxed), which is the identity framing
   * the battler ships with when camera.zoom === 1. */
  function fit(env, aw, ah) {
    var s = env.state, w = env.vp.w || 0, h = env.vp.h || 0;
    if (!(w > 0 && h > 0)) { s.k = s.ky = 1; s.tx = 0; s.ty = 0; return s; }
    s.k = s.ky = Math.min(w / aw, h / ah);       // letterbox fit is UNIFORM by definition
    s.tx = (w - aw * s.k) / 2;
    s.ty = (h - ah * s.k) / 2;
    return s;
  }

  /* engine.js camera {offX,offY,zoom} -> CamState. The battler's own map (game.html:2847)
   *   toX(gx) = (gx - offX) * scaleX() * zoom,  scaleX() = canvas.width / ARENA_W
   *   toY(gy) = (gy - offY) * scaleY() * zoom,  scaleY() = canvas.height / ARENA_H
   * expands to k*gx + tx with k = scaleX*zoom and tx = -offX*k, and the same on y with
   * scaleY. EXACT, not an approximation -- proven against the extracted real toX/toY in
   * _probe.js. This is why CamState carries a separate ky. */
  function adopt(env, cam, aw, ah) {
    var s = env.state, w = env.vp.w || 0, h = env.vp.h || 0;
    var a = (env._arena && env._arena.w) || aw || ARENA_W;
    var b = (env._arena && env._arena.h) || ah || ARENA_H;
    var sx = w > 0 ? w / a : 1, sy = h > 0 ? h / b : 1;
    var z = (cam && cam.zoom > 0) ? cam.zoom : 1;
    s.k  = sx * z;
    s.ky = sy * z;
    s.tx = -((cam && cam.offX) || 0) * s.k;
    s.ty = -((cam && cam.offY) || 0) * s.ky;
    return s;
  }

  function update(dt, env) {
    // FIXED means fixed: the only thing that moves is a resize refit.
    var a = env._arena || { w: ARENA_W, h: ARENA_H };
    if (env.vp.w && env.vp.h && !(env.opts && env.opts.camera)) fit(env, a.w, a.h);
  }

  function pointer(e, env) { return; }           // no player camera control during play

  function render(g, env) { return; }            // the battler owns its own draw

  function exit(env) { env._arena = null; }

  return {
    id: 'battle', dim: '2d', needsThree: false,
    enter: enter, exit: exit, update: update, render: render, pointer: pointer,
    fit: fit, adopt: adopt, DEG: DEG, PERSP: PERSP
  };
});
