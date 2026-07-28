/* ALLEY KINGZ -- GARAGE CAMERA (cinematic turntable). AK-CAM 2026-07-18.
 *
 * The vehicle sits still and the camera walks a slow circle around it, three-quarter
 * high, framed so the silhouette fills the same share of frame whether it is a moped
 * or a box truck. That last part is the whole trick: P.frameDistance() solves the
 * orbit radius from the subject's bounding radius and the FOV, so nothing is ever
 * half a screen away or clipping the near plane.
 *
 * Drag scrubs the turntable and pauses the auto-spin; let go and it eases back into
 * the drift after a beat, which is the showroom feel (never dead, never fighting you).
 *
 * Spotlight framing = a three-point rig described in PURE DATA (key/fill/rim, each an
 * angle offset from the current camera azimuth plus an intensity). Because the lights
 * are defined RELATIVE to the camera, the rim stays on the silhouette edge through the
 * whole rotation instead of sliding off at the back of the turn. When THREE is present
 * the rig is instantiated as real lights; when it is absent lights() still returns the
 * same data, so a 2D or CSS presentation can drive a gradient with it.
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

  var SPIN = 0.22;                 // rad/s auto turntable (a full lap in ~28s)
  var PHI = 1.15;                  // rad: the three-quarter-high showroom angle
  var FOV = 35;                    // long-ish lens: flatter, more product-shot
  var RESUME_AFTER = 1.6;          // s of no touch before the drift eases back in
  var g = null, cam3 = null, idle = 0, rig = null;

  /* Three-point rig, angles RELATIVE to the camera azimuth (radians). */
  var RIG = [
    { id: 'key',  dTheta: -0.60, dPhi: -0.35, color: 0xfff2d0, intensity: 1.65, dist: 1.8 },
    { id: 'fill', dTheta:  1.15, dPhi:  0.10, color: 0x9fb6ff, intensity: 0.55, dist: 2.2 },
    { id: 'rim',  dTheta:  Math.PI * 0.92, dPhi: -0.20, color: 0xe8c55a, intensity: 2.10, dist: 1.6 }
  ];

  function enter(env) {
    var s = env.state, o = env.opts || {};
    var sub = o.subject || {};
    s.focus.x = +sub.x || 0; s.focus.y = +sub.y || 0; s.focus.z = +sub.z || 0;
    s.theta = (o.theta != null) ? o.theta : -Math.PI / 4;
    s.phi = P.clampPolar((o.phi != null) ? o.phi : PHI, 0.35, 1.45);
    s.tilt = P.tilt({ deg: 0 });
    var aspect = (env.vp.w && env.vp.h) ? (env.vp.w / env.vp.h) : 1;
    s.dist = P.frameDistance((sub.radius != null ? sub.radius : 1.6), (o.fov || FOV), aspect, o.pad || 1.18);
    idle = RESUME_AFTER;
    g = G.create({ tapSlop: 8 });
    rig = null;

    if (env.three) {
      var T = env.three;
      cam3 = new T.PerspectiveCamera((o.fov || FOV), aspect, 0.05, 500);
      rig = RIG.map(function (L) {
        var l = new T.PointLight(L.color, L.intensity, 0, 2);
        if (o.scene && o.scene.add) o.scene.add(l);
        return { def: L, light: l };
      });
      apply(env);
    } else { cam3 = null; }        // documented no-op: turntable state still advances
  }

  function exit(env) {
    if (rig && env.opts && env.opts.scene && env.opts.scene.remove) {
      rig.forEach(function (r) { try { env.opts.scene.remove(r.light); } catch (_e) {} });
    }
    g = null; cam3 = null; rig = null;
  }

  /* The rig as plain data, camera-relative resolved to WORLD positions. Callable with
   * or without THREE, which is what makes the framing testable headless. */
  function lights(env) {
    var s = env.state, out = [];
    for (var i = 0; i < RIG.length; i++) {
      var L = RIG[i];
      var e = P.orbitEye({
        theta: s.theta + L.dTheta,
        phi: P.clampPolar(s.phi + L.dPhi, 0.05, Math.PI / 2 - 0.02),
        dist: s.dist * L.dist,
        focus: s.focus
      });
      out.push({ id: L.id, x: e.x, y: e.y, z: e.z, color: L.color, intensity: L.intensity });
    }
    return out;
  }

  function apply(env) {
    var s = env.state;
    if (cam3) {
      var e = P.orbitEye(s);
      cam3.position.set(e.x, e.y, e.z);
      cam3.lookAt(s.focus.x, s.focus.y, s.focus.z);
      if (env.vp.w && env.vp.h) { cam3.aspect = env.vp.w / env.vp.h; cam3.updateProjectionMatrix(); }
    }
    if (rig) {
      var pos = lights(env);
      for (var i = 0; i < rig.length && i < pos.length; i++) rig[i].light.position.set(pos[i].x, pos[i].y, pos[i].z);
    }
  }

  function update(dt, env) {
    var s = env.state;
    idle += dt;
    if (idle >= RESUME_AFTER) {
      // ease the drift back in over the first half-second instead of snapping to speed
      var ramp = P.clamp((idle - RESUME_AFTER) / 0.5, 0, 1);
      s.theta += SPIN * ramp * dt;
    }
    apply(env);
  }

  function pointer(e, env) {
    if (!g) return;
    var v = g.feed(e), s = env.state;
    if (v.kind === 'drag') { s.theta -= v.dx * 0.008; idle = 0; }
    else if (v.kind === 'pinch') { s.dist = P.clamp(s.dist / v.scale, 0.6, 60); idle = 0; }
    else if (v.kind === 'wheel') { s.dist = P.clamp(s.dist / v.scale, 0.6, 60); idle = 0; }
  }

  function render(g2d, env) { return; }

  /* Re-frame for a different subject without leaving the mode (swap vehicles). */
  function frame(env, subject) {
    var s = env.state, sub = subject || {};
    s.focus.x = +sub.x || 0; s.focus.y = +sub.y || 0; s.focus.z = +sub.z || 0;
    var aspect = (env.vp.w && env.vp.h) ? (env.vp.w / env.vp.h) : 1;
    s.dist = P.frameDistance((sub.radius != null ? sub.radius : 1.6), FOV, aspect, 1.18);
    return s.dist;
  }

  return {
    id: 'garage', dim: '3d', needsThree: false,
    enter: enter, exit: exit, update: update, render: render, pointer: pointer,
    lights: lights, frame: frame, camera3: function () { return cam3; },
    SPIN: SPIN, FOV: FOV
  };
});
