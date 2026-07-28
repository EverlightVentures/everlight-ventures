/* ALLEY KINGZ -- AK_CAMERAS: one game state, many render modes.
 * AK-CAM 2026-07-18.
 *
 * THE ROUTER IS NOT NEW. AK_CTX.overlay.open(spec) (index.html:3122) already does
 * fullscreen-surface + own RAF + state save/restore + close(res), and 5 systems ride
 * it. This manager reuses that contract instead of competing with it: a camera mode
 * that asks for {overlay:true} IS an overlay, driven by overlay.open's own RAF, and
 * closes through the same api.close(). Modes that do NOT ask for an overlay run
 * INLINE: the host's existing loop calls AK_CAMERAS.update/render, which is how the
 * hub camera keeps working with zero new surfaces.
 *
 * TRANSITIONS ARE NOT NEW either. akPlayTransition('transition_wipe') (index.html:2053)
 * plus assets/cinematics/transition_wipe{,_rev,_glitch}.mp4 already ship. switch()
 * fires that stinger and cross-fades under it; when the helper is absent (node, or a
 * page that has not defined it) the fade still runs and the switch still completes.
 *
 * SINGLE-RENDERER GUARANTEE
 * Exactly one mode is ever `_active`. render()/update() dispatch through the manager
 * and nowhere else, switch() is re-entrancy guarded, and exit() of the outgoing mode
 * is awaited before enter() of the incoming one. A mode that tries to draw after
 * exit has no surface to draw on because the manager stopped calling it.
 *
 * THREE.JS IS NOT IN THE REPO. Every 3D mode degrades to a DOCUMENTED no-op when
 * THREE is absent: it still keeps its full math state (theta/phi/dist/focus), still
 * accepts input, still reports state() to the bridge, and simply renders nothing.
 * env.degraded is true so the host can keep painting the 2D fallback. To add it:
 *   1. download three.min.js and drop it at game/assets/vendor/three.min.js
 *      (same folder + same serving story as assets/vendor/model-viewer.min.js)
 *   2. index.html gets ONE tag before the camera scripts, matching line 428's idiom:
 *      <script src="assets/vendor/three.min.js?v=350"></script>
 *   3. nothing else changes. hasThree() flips true, degraded flips false, the 3D
 *      modes build their scene on next enter(). No API in this folder moves.
 * Do NOT scavenge the copy bundled inside model-viewer.min.js: it is a private
 * ES-module build, not exposed as window.THREE, and pinning to it would couple the
 * cameras to model-viewer's internal version.
 */
(function (root, factory) {
  var PROJ = (typeof module === 'object' && module.exports)
    ? require('./Projection.js')
    : (root && root.AK_PROJ);
  var api = factory(PROJ, root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.AK_CAMERAS = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function (P, root) {
  'use strict';

  var HAS_DOM = !!(root && root.document && root.document.createElement);
  var modes = {}, order = [];
  var _active = null;          // the ONE live mode record, or null
  var _switching = false;
  var _ctx = null;             // AK_CTX once bridged
  var _bridged = null;         // saved original wx/wy so unbridge() is exact
  var FADE_MS = 260;

  function warn(id, e) { try { if (root && root.console) root.console.warn('[AK_CAMERAS]', id, e); } catch (_e) {} }
  function hasThree() { return !!(root && root.THREE); }
  function now() { return (root && root.performance && root.performance.now) ? root.performance.now() : Date.now(); }

  /* ---- mode registry ------------------------------------------------------ *
   * A mode is {id, dim:'2d'|'3d', needsThree, enter(env), exit(env), update(dt,env),
   * render(g,env), pointer(e,env)}. Every hook is optional. */
  function register(m) {
    if (!m || typeof m !== 'object' || !m.id || modes[m.id]) return false;
    modes[m.id] = m; order.push(m.id); return true;
  }
  function get(id) { return modes[id] || null; }
  function list() { return order.slice(); }

  /* ---- the shared env handed to every hook -------------------------------- */
  function makeEnv(mode, opts) {
    var st = P.state(opts && opts.state);
    return {
      id: mode.id,
      ctx: _ctx,                                  // AK_CTX when bridged, else null
      opts: opts || {},
      state: st,                                  // the CamState the bridge reads
      three: hasThree() ? root.THREE : null,
      degraded: !!(mode.needsThree && !hasThree()),
      vp: { w: 0, h: 0, dpr: 1 },
      overlay: null,                              // filled when running as an overlay
      P: P
    };
  }

  /* ---- cross-fade --------------------------------------------------------- *
   * A z-37 curtain (just under akPlayTransition's z-38 video, so the stinger reads
   * ON TOP of the fade) that goes opaque, lets the swap happen behind it, then
   * clears. Headless: no DOM, so the callbacks fire straight through. */
  function curtain(half, done) {
    if (!HAS_DOM) { try { half(); } catch (e) { warn('curtain', e); } try { done && done(); } catch (e2) { warn('curtain', e2); } return; }
    var d = root.document;
    var el = d.createElement('div');
    el.setAttribute('data-ak-cam-fade', '1');
    el.style.cssText = 'position:fixed;inset:0;z-index:37;background:#06060a;opacity:0;pointer-events:none;transition:opacity ' + FADE_MS + 'ms ease;';
    d.body.appendChild(el);
    // force a style flush so the 0 -> 1 transition actually animates
    try { void el.offsetWidth; } catch (_e) {}
    el.style.opacity = '1';
    root.setTimeout(function () {
      try { half(); } catch (e) { warn('curtain-half', e); }
      el.style.opacity = '0';
      root.setTimeout(function () {
        try { el.remove(); } catch (_e2) {}
        try { done && done(); } catch (e3) { warn('curtain-done', e3); }
      }, FADE_MS);
    }, FADE_MS);
  }

  function stinger(name) {
    if (!root || typeof root.akPlayTransition !== 'function') return;
    try { root.akPlayTransition(name || 'transition_wipe'); } catch (_e) {}
  }

  /* ---- teardown ----------------------------------------------------------- */
  function stop(res) {
    if (!_active) return;
    var rec = _active;
    _active = null;                               // clear FIRST: no hook can render after this
    try { rec.mode.exit && rec.mode.exit(rec.env); } catch (e) { warn(rec.mode.id, e); }
    if (rec.env.overlay) { try { rec.env.overlay.close(res); } catch (_e) {} rec.env.overlay = null; }
  }

  /* ---- switch ------------------------------------------------------------- *
   * AK_CAMERAS.switch('rpg', {overlay:true, transition:'transition_wipe', state:{...}})
   * Returns the env of the incoming mode (already entered when synchronous, i.e.
   * when opts.fade === false or there is no DOM). */
  function switchTo(id, opts) {
    opts = opts || {};
    var mode = modes[id];
    if (!mode) { warn('switch', 'unknown mode ' + id); return null; }
    if (_switching) { warn('switch', 'ignored re-entrant switch to ' + id); return null; }
    if (_active && _active.mode.id === id && !opts.force) return _active.env;

    _switching = true;
    var env = makeEnv(mode, opts);

    function swap() {
      stop({ reason: 'switch', to: id });
      if (opts.overlay && _ctx && _ctx.overlay && _ctx.overlay.open) {
        // reuse the EXISTING fullscreen router: its RAF drives update+render,
        // its close() restores hub state exactly as it does for the 5 current users.
        env.overlay = _ctx.overlay.open({
          onFrame: function (g, dt, vp, oapi) {
            env.vp.w = vp.w; env.vp.h = vp.h; env.vp.dpr = vp.dpr;
            if (_active && _active.env === env) { tickOne(_active, dt); drawOne(_active, g); }
            env._oapi = oapi;
          },
          onPointer: function (e) { if (_active && _active.env === env) pointer(e); },
          onClose: function (res) { if (_active && _active.env === env) { _active = null; try { mode.exit && mode.exit(env); } catch (er) { warn(id, er); } } if (opts.onClose) opts.onClose(res); }
        });
      }
      _active = { mode: mode, env: env, t0: now() };
      try { mode.enter && mode.enter(env); } catch (e) { warn(id, e); }
      _switching = false;
    }

    if (opts.fade === false || !HAS_DOM) { swap(); return env; }
    stinger(opts.transition || 'transition_wipe');
    curtain(swap, opts.onReady || null);
    return env;                                   // entered on the far side of the fade
  }

  /* ---- per-frame dispatch (INLINE modes; overlay modes get it from overlay.open) */
  function tickOne(rec, dt) { try { rec.mode.update && rec.mode.update(dt, rec.env); } catch (e) { warn(rec.mode.id, e); } }
  function drawOne(rec, g) { if (rec.env.degraded) return; try { rec.mode.render && rec.mode.render(g, rec.env); } catch (e) { warn(rec.mode.id, e); } }

  function update(dt) { if (_active && !_active.env.overlay) tickOne(_active, dt); }
  function render(g) { if (_active && !_active.env.overlay) drawOne(_active, g); }
  function pointer(e) { if (_active) { try { _active.mode.pointer && _active.mode.pointer(e, _active.env); } catch (er) { warn(_active.mode.id, er); } } }

  function active() { return _active ? _active.mode.id : null; }
  function env() { return _active ? _active.env : null; }
  function camState() { return _active ? _active.env.state : null; }

  /* ---- THE MIGRATION SEAM ------------------------------------------------- *
   * AK_CTX.world.wx/wy (index.html:3089-3091) is ALREADY the camera interface every
   * plugin draws through. bridge() swaps those two functions for the active camera's
   * stage-1 projection. That single swap moves all 15 plugin systems onto the new
   * camera at once: pan and zoom start working in every system that draws with
   * wx()/wy(), with no edit to any of them.
   *
   * SAFETY: with no active mode, or with a mode whose state is the hub identity
   * (k=1, tx=-cam.x), wx(x) returns x-cam.x, which is byte-identical to the original.
   * So bridging is a no-op until something actually moves the camera.
   *
   * WHY ZOOM AND NOT TILT: wx/wy are separable by contract (wx sees only x). Pan and
   * zoom are separable, so they ride here for free. Perspective is NOT separable, so
   * it rides the stage-2 post-warp instead -- see warpPoint()/tiltCss() below and the
   * long note at the top of Projection.js. */
  function bridge(ctx) {
    if (!ctx || !ctx.world || _bridged) return false;
    _ctx = ctx;
    _bridged = { wx: ctx.world.wx, wy: ctx.world.wy };
    ctx.world.wx = function (x) { var s = camState(); return s ? P.wx(s, x) : _bridged.wx(x); };
    ctx.world.wy = function (y) { var s = camState(); return s ? P.wy(s, y) : _bridged.wy(y); };
    return true;
  }
  function unbridge() {
    if (!_ctx || !_bridged) return false;
    _ctx.world.wx = _bridged.wx; _ctx.world.wy = _bridged.wy;
    _bridged = null; return true;
  }
  function attach(ctx) { _ctx = ctx; return _ctx; }     // wire AK_CTX without touching wx/wy

  /* ---- stage 2 helpers exposed to hosts + billboarded systems -------------- */
  function warpPoint(sx, sy, w, h) {
    var s = camState();
    if (!s) return { x: sx, y: sy, scale: 1 };
    return P.warp(sx, sy, w, h, s.tilt);
  }
  function unwarpPoint(sx, sy, w, h) {
    var s = camState();
    if (!s) return { x: sx, y: sy };
    return P.unwarp(sx, sy, w, h, s.tilt);
  }
  function tiltCss() { var s = camState(); return P.tiltCss(s ? s.tilt : null); }

  /* Screen -> world through BOTH stages, in the right order (unwarp, then unlinear).
   * This is what a tap handler calls. Identity when tilt is off. */
  function screenToWorld(sx, sy, w, h) {
    var s = camState(); if (!s) return { x: sx, y: sy };
    var u = P.unwarp(sx, sy, w, h, s.tilt);
    return { x: P.unwx(s, u.x), y: P.unwy(s, u.y) };
  }

  return {
    register: register, get: get, list: list,
    'switch': switchTo, switchTo: switchTo, stop: stop,
    update: update, render: render, pointer: pointer,
    active: active, env: env, state: camState,
    bridge: bridge, unbridge: unbridge, attach: attach,
    warpPoint: warpPoint, unwarpPoint: unwarpPoint, tiltCss: tiltCss, screenToWorld: screenToWorld,
    hasThree: hasThree, P: P, FADE_MS: FADE_MS
  };
});
