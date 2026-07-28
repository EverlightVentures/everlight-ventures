/* ALLEY KINGZ -- AK_PROJ: the PURE MATH CORE behind every camera mode.
 * AK-CAM 2026-07-18.
 *
 * Zero DOM, zero globals, zero side effects. Safe to require() in node for tests
 * (tests/ probes load it exactly like tests/tilt2_probe.js loads the arena warp).
 *
 * WHY THIS FILE EXISTS
 * The hub, the battler and the world map each grew their OWN camera:
 *   hub      index.html:3089   wx(x)=x-cam.x, wy(y)=y-cam.y        (translate only)
 *   battler  engine.js:1406    camera {offX,offY,zoom} + an 18deg tilt (game.html:2861)
 *   worldmap systems/worldmap.js:682  WM {cam:{x,y}, scale} pinch/pan
 * All three are the SAME transform with different fields filled in. This module is
 * that one transform, factored so a mode only supplies state, never math.
 *
 * THE TWO-STAGE MODEL (this is the whole design, and it is the repo's own proven one)
 *   stage 1  LINEAR / SEPARABLE   world -> screen via k*x+tx and k*y+ty.
 *            Separable means wx(x) needs only x and wy(y) needs only y, which is
 *            exactly what AK_CTX.world.wx/wy promise and what all 15 plugin systems
 *            call in pairs. Pan and zoom live here and cost the plugins nothing.
 *   stage 2  PROJECTIVE / POST    screen -> screen perspective warp, applied AFTER
 *            stage 1, either as one GPU CSS transform on the canvas or per draw-point
 *            for billboarded sprites. Non-separable math CANNOT live in wx/wy (screen
 *            x would depend on world y), so it rides here instead. game.html:2870
 *            reached the same conclusion independently: "warpScreen() is a PURE
 *            screen-space map applied AFTER the linear camera stage (toX/toY)".
 * warp()/unwarp() below are the arena's REAL shipping math (game.html:2896 forward,
 * game.html:5232 inverse), lifted verbatim and parameterised on W/H/tilt.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;   // node / probes
  if (root) root.AK_PROJ = api;                                             // browser
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function () {
  'use strict';

  var DEG = Math.PI / 180;
  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  /* ---- STATE ------------------------------------------------------------- *
   * One shape every mode fills in. Defaults are the hub's exact identity:
   * k=1, tx=ty=0, no rotation, no tilt -> wx(x)===x, so a camera that has not
   * been touched renders byte-identically to today. */
  function state(o) {
    o = o || {};
    return {
      k:    num(o.k, 1),            // zoom on x (stage 1)
      // ky exists because the arena is genuinely NON-uniform: game.html:2845 scales x by
      // canvas.width/ARENA_W and y by canvas.height/ARENA_H. Collapsing them to one k
      // would stretch the board on any aspect that is not exactly ARENA_W:ARENA_H.
      // Defaults to k, so every uniform mode can ignore it entirely.
      ky:   num(o.ky, num(o.k, 1)),  // zoom on y (stage 1)
      tx:   num(o.tx, 0),           // screen translate x (stage 1); hub uses -cam.x
      ty:   num(o.ty, 0),           // screen translate y (stage 1); hub uses -cam.y
      quarter: (num(o.quarter, 0) % 4 + 4) % 4,   // iso yaw in 90deg snaps (builder)
      theta: num(o.theta, 0),       // azimuth radians (orbit modes)
      phi:   num(o.phi, 1.0),       // polar radians from +Y (orbit modes)
      dist:  num(o.dist, 10),       // orbit radius (orbit modes)
      focus: { x: num(o.focus && o.focus.x, 0), y: num(o.focus && o.focus.y, 0), z: num(o.focus && o.focus.z, 0) },
      tilt:  tilt(o.tilt)
    };
  }

  function tilt(t) {
    t = t || {};
    var deg = num(t.deg, 0);
    return { on: !!(t.on !== false && deg > 0), deg: deg, persp: num(t.persp, 1100), sin: Math.sin(deg * DEG), cos: Math.cos(deg * DEG) };
  }

  /* ---- STAGE 1: separable linear world->screen ---------------------------- *
   * These two ARE the drop-in replacement for AK_CTX.world.wx/wy. With the hub's
   * live state (k=1, tx=-cam.x) they return x-cam.x, bit for bit. */
  function ky(s) { return (typeof s.ky === 'number' && isFinite(s.ky) && s.ky !== 0) ? s.ky : s.k; }
  function wx(s, x) { return x * s.k + s.tx; }
  function wy(s, y) { return y * ky(s) + s.ty; }
  function unwx(s, sx) { return (sx - s.tx) / s.k; }
  function unwy(s, sy) { return (sy - s.ty) / ky(s); }

  /* Center the camera on a world point inside a w-by-h viewport (pan helper). */
  function lookAt(s, worldX, worldY, w, h) {
    s.tx = w / 2 - worldX * s.k;
    s.ty = h / 2 - worldY * ky(s);
    return s;
  }

  /* Zoom about a fixed SCREEN anchor (pinch focal point stays put under the fingers).
   * Solves for tx/ty so unwx/unwy of the anchor are invariant across the zoom change.
   * ky rides the SAME ratio as k, so a non-uniform camera keeps its aspect through a pinch. */
  function zoomAt(s, newK, anchorSX, anchorSY) {
    var wxp = unwx(s, anchorSX), wyp = unwy(s, anchorSY);
    var ratio = (s.k !== 0) ? (newK / s.k) : 1;
    s.k = newK;
    s.ky = ky(s) * ratio;
    s.tx = anchorSX - wxp * s.k;
    s.ty = anchorSY - wyp * s.ky;
    return s;
  }

  /* ---- STAGE 2: projective post-warp (the REAL arena math) ---------------- *
   * Pivot at bottom-center (W/2, H). Identity at the bottom edge (v=0 -> w=1),
   * far rows recede and shrink. game.html:2896 verbatim, W/H/tilt parameterised. */
  function warp(X, Y, W, H, t) {
    if (!t || !t.on) return { x: X, y: Y, scale: 1 };
    var u = X - W / 2, vlin = Y - H;
    var w = 1 - vlin * t.sin / t.persp;
    var sc = 1 / w;
    return { x: u * sc + W / 2, y: vlin * t.cos * sc + H, scale: sc };
  }

  /* Exact closed-form inverse. game.html:5232 verbatim (same degenerate-ray guard). */
  function unwarp(Xw, Yw, W, H, t) {
    if (!t || !t.on) return { x: Xw, y: Yw };
    var U = Xw - W / 2, V = Yw - H;
    var den = t.cos + V * t.sin / t.persp;
    var vlin = den > 0.05 ? V / den : V;
    var w = 1 - vlin * t.sin / t.persp;
    return { x: U * w + W / 2, y: vlin + H };
  }

  /* The CSS the host applies when it wants stage 2 for FREE on the whole canvas
   * (game.html B1 path, GPU composited, zero per-frame cost). Pure string builder. */
  function tiltCss(t) {
    if (!t || !t.on) return { transform: 'none', transformOrigin: '50% 100%' };
    return { transform: 'perspective(' + t.persp + 'px) rotateX(' + t.deg + 'deg)', transformOrigin: '50% 100%' };
  }

  /* ---- ISOMETRIC (builder mode, Clash of Clans) --------------------------- *
   * 2:1 iso with the yaw quantised to 90deg snaps. Exact inverse below. */
  var QUARTER = [ [1, 0, 0, 1], [0, -1, 1, 0], [-1, 0, 0, -1], [0, 1, -1, 0] ];   // rot matrices for q=0..3

  function rotQ(x, y, q) {
    var m = QUARTER[((q % 4) + 4) % 4];
    return { x: m[0] * x + m[1] * y, y: m[2] * x + m[3] * y };
  }
  function unrotQ(x, y, q) {
    var m = QUARTER[((q % 4) + 4) % 4];                 // inverse of a rotation is its transpose
    return { x: m[0] * x + m[2] * y, y: m[1] * x + m[3] * y };
  }

  function iso(s, x, y, z) {
    var r = rotQ(x, y, s.quarter), h = num(z, 0);
    return {
      x: (r.x - r.y) * s.k + s.tx,
      y: (r.x + r.y) * s.k * 0.5 - h * s.k + s.ty,
      depth: r.x + r.y                                   // painter's-algorithm sort key
    };
  }

  /* Screen -> world on the ground plane (z=0). Exact inverse of iso(). */
  function unIso(s, sx, sy) {
    var a = (sx - s.tx) / s.k;                           // rx - ry
    var b = (sy - s.ty) / (s.k * 0.5);                   // rx + ry
    return unrotQ((a + b) / 2, (b - a) / 2, s.quarter);
  }

  /* ---- ORBIT (RPG third-person, garage turntable) -------------------------- *
   * phi is polar from +Y: 0 = straight down the pole, PI/2 = horizon. */
  function orbitEye(s) {
    var sp = Math.sin(s.phi);
    return {
      x: s.focus.x + s.dist * sp * Math.cos(s.theta),
      y: s.focus.y + s.dist * Math.cos(s.phi),
      z: s.focus.z + s.dist * sp * Math.sin(s.theta)
    };
  }
  function clampPolar(phi, lo, hi) { return clamp(phi, num(lo, 0.15), num(hi, Math.PI / 2 - 0.05)); }

  /* Distance that frames a sphere of `radius` in a vertical-FOV camera. Used by the
   * garage turntable so any vehicle, big or small, fills the same share of frame. */
  function frameDistance(radius, fovDeg, aspect, pad) {
    var f = num(fovDeg, 35) * DEG, a = num(aspect, 1), r = Math.max(0.0001, num(radius, 1));
    var dV = r / Math.sin(f / 2);
    var hFov = 2 * Math.atan(Math.tan(f / 2) * Math.max(0.0001, a));
    var dH = r / Math.sin(hFov / 2);
    return Math.max(dV, dH) * num(pad, 1.15);
  }

  /* ---- SMOOTHING --------------------------------------------------------- */
  function lerp(a, b, t) { return a + (b - a) * clamp(t, 0, 1); }
  /* Framerate-independent exponential approach. rate = how much of the gap closes per second. */
  function damp(a, b, rate, dt) { return b + (a - b) * Math.exp(-num(rate, 8) * num(dt, 0)); }
  function shortAngle(from, to) {                       // wrapped angular delta, -PI..PI
    var d = (to - from) % (Math.PI * 2);
    if (d > Math.PI) d -= Math.PI * 2;
    if (d < -Math.PI) d += Math.PI * 2;
    return d;
  }
  function dampAngle(a, b, rate, dt) { return a + shortAngle(a, b) * (1 - Math.exp(-num(rate, 8) * num(dt, 0))); }

  return {
    DEG: DEG, clamp: clamp, lerp: lerp, damp: damp, dampAngle: dampAngle, shortAngle: shortAngle,
    state: state, tilt: tilt, ky: ky,
    wx: wx, wy: wy, unwx: unwx, unwy: unwy, lookAt: lookAt, zoomAt: zoomAt,
    warp: warp, unwarp: unwarp, tiltCss: tiltCss,
    iso: iso, unIso: unIso, rotQ: rotQ, unrotQ: unrotQ,
    orbitEye: orbitEye, clampPolar: clampPolar, frameDistance: frameDistance
  };
});
