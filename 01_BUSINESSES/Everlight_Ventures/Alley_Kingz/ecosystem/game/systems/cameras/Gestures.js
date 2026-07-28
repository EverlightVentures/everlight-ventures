/* ALLEY KINGZ -- AK_GESTURE: drag + pinch state machine shared by the camera modes.
 * AK-CAM 2026-07-18.
 *
 * Pure state over duck-typed pointer events {type, pointerId, clientX, clientY} plus
 * an optional wheel {type:'wheel', deltaY, clientX, clientY}. No DOM, no listeners --
 * the modes are handed events by AK_CTX.overlay.open's onPointer (index.html:3134) or
 * by the host, exactly like worldmap.js:682's WM.ptrs/WM.pinch does its own tracking.
 * Factored out so all 5 modes share ONE gesture implementation instead of five.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.AK_GESTURE = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function () {
  'use strict';

  function create(opts) {
    opts = opts || {};
    var ptrs = {}, n = 0, pinch = null, moved = 0;
    var TAP_SLOP = (typeof opts.tapSlop === 'number') ? opts.tapSlop : 8;

    function ids() { var k = [], p; for (p in ptrs) if (ptrs.hasOwnProperty(p)) k.push(p); return k; }
    function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
    function mid(a, b) { return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; }

    /* Feed one event. Returns a verb the mode acts on, never null:
     *   {kind:'none'}
     *   {kind:'drag',  dx, dy, x, y}
     *   {kind:'pinch', scale, dx, dy, cx, cy}   scale is RELATIVE to the last frame
     *   {kind:'tap',   x, y}                    only when the finger barely moved
     *   {kind:'wheel', scale, x, y} */
    function feed(e) {
      if (!e) return { kind: 'none' };
      var t = e.type, id = (e.pointerId == null ? 'm' : String(e.pointerId));
      var x = +e.clientX || 0, y = +e.clientY || 0;

      if (t === 'wheel') {
        var dy = +e.deltaY || 0;
        return { kind: 'wheel', scale: Math.exp(-dy * (opts.wheelRate || 0.0016)), x: x, y: y };
      }
      if (t === 'pointerdown' || t === 'touchstart' || t === 'mousedown') {
        if (!ptrs[id]) n++;
        ptrs[id] = { x: x, y: y, x0: x, y0: y };
        moved = 0;
        if (n === 2) { var k = ids(); pinch = { d: dist(ptrs[k[0]], ptrs[k[1]]), c: mid(ptrs[k[0]], ptrs[k[1]]) }; }
        return { kind: 'none' };
      }
      if (t === 'pointermove' || t === 'touchmove' || t === 'mousemove') {
        var p = ptrs[id]; if (!p) return { kind: 'none' };
        var ddx = x - p.x, ddy = y - p.y;
        p.x = x; p.y = y;
        moved += Math.abs(ddx) + Math.abs(ddy);
        if (n >= 2 && pinch) {
          var k2 = ids(); if (k2.length < 2) return { kind: 'none' };
          var a = ptrs[k2[0]], b = ptrs[k2[1]];
          var d2 = dist(a, b), c2 = mid(a, b);
          var sc = pinch.d > 0.5 ? (d2 / pinch.d) : 1;
          var out = { kind: 'pinch', scale: sc, dx: c2.x - pinch.c.x, dy: c2.y - pinch.c.y, cx: c2.x, cy: c2.y };
          pinch.d = d2; pinch.c = c2;
          return out;
        }
        return { kind: 'drag', dx: ddx, dy: ddy, x: x, y: y };
      }
      if (t === 'pointerup' || t === 'pointercancel' || t === 'touchend' || t === 'mouseup') {
        var q = ptrs[id];
        if (q) { delete ptrs[id]; n = Math.max(0, n - 1); }
        if (n < 2) pinch = null;
        if (q && moved <= TAP_SLOP) return { kind: 'tap', x: q.x, y: q.y };
        return { kind: 'none' };
      }
      return { kind: 'none' };
    }

    function reset() { ptrs = {}; n = 0; pinch = null; moved = 0; }
    function count() { return n; }
    return { feed: feed, reset: reset, count: count };
  }

  return { create: create };
});
