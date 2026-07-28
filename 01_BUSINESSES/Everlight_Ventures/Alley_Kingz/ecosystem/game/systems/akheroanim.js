/* ALLEY KINGZ -- AK_HEROANIM: make the dog WALK, not slide.  AK-HEROANIM 2026-07-20.
 *
 * OPERATOR: "the dog drifts across the ground with no foot animation or weight."
 *
 * WHAT THIS IS *NOT*
 * It is not a clip-index fix. That was the obvious suspect and it is WRONG, so it is written down
 * here to stop the next person re-deriving it. Measured live in chromium on e5 against the real
 * bcardd.glb:
 *     availableAnimations = ["NlaTrack","NlaTrack.001", ... ,"NlaTrack.013"]   (14, all generic)
 *     while walking, mv.animationName === "NlaTrack.010"   <- hub3d's walk index 10, correct
 *     while still,   mv.animationName === "NlaTrack.002"   <- hub3d's idle index 2,  correct
 * model-viewer does select clips by NAME, but hub3d already converts index -> name in pickClips()
 * (hub3d.js:113-129, `nm[iWalk]`), so the right clip really is bound. The live site serves that
 * same mapping (hub3d.js md5 d3dea9bc, verified against https://alleykingz.online/systems/hub3d.js).
 * DO NOT "fix" CLIP_BY_MODEL. The clip is right; the clip's CLOCK is the problem.
 *
 * THE ACTUAL FAULT -- model-viewer stops the animation clock when the element leaves the viewport.
 * hub3d pins the hero with position:fixed and writes left/top from his SCREEN position every frame
 * (hub3d.js:216-219). model-viewer drives its mixer off an IntersectionObserver, so the instant that
 * rect stops touching the viewport the mixer stops being ticked. MEASURED, one variable at a time,
 * hub3d disabled, element parked at fixed offsets, clock sampled over 900ms (element 72x120,
 * viewport 900x1500):
 *       left=  414  dead centre            inVP=true   clock 0.691 -> 2.291   ADVANCING
 *       left=    0  flush to the left edge inVP=true   clock 1.116 -> 0.191   ADVANCING (wrapped)
 *       left=  -36  half off the left      inVP=true   clock 0.991 -> 0.216   ADVANCING (wrapped)
 *       left=  -71  ONE PIXEL still on     inVP=true   clock 1.433 -> 0.741   ADVANCING (wrapped)
 *       left=  -90  fully off the left     inVP=false  clock 1.941 -> 1.941   *** FROZEN ***
 *       left=  920  fully off the right    inVP=false  clock 0.016 -> 0.016   *** FROZEN ***
 *       top = 1520  fully off the bottom   inVP=false  clock 0.016 -> 0.016   *** FROZEN ***
 * One pixel of overlap is enough. Zero pixels freezes it dead. There is no partial-credit zone.
 *
 * WHY THAT READS AS "SLIDING" RATHER THAN "GONE": the freeze is SILENT. hub3d sets .active=true
 * purely from `ready` (hub3d.js:239), never from whether the element is really on screen, and
 * index.html:2864 hides the 2D fallback body with globalAlpha=0 whenever .active is true. So a
 * frozen hero keeps his last pose, keeps getting dragged around by left/top, and the 2D dog that
 * would have covered for him stays suppressed. A statue on a conveyor belt. It also PERSISTS: the
 * mixer resumes from the exact frame it stopped on, so one trip past the screen edge leaves him
 * mid-stride for as long as he stays there.
 *
 * SECOND FAULT -- rebind thrash. hub3d only rebinds when the clip name changes (hub3d.js:241), but
 * assigning mv.animationName RESTARTS the action at t=0 (measured: walk clock 1.3s -> flip to idle
 * for 50ms -> flip back -> clock reads ~0.0, it does not resume). The flag driving that is
 * avMoving = (_mv > 0.2) at index.html:2587 -- a BARE THRESHOLD on per-frame displacement with no
 * hysteresis. me.spd is 300 px/s (index.html:891) = 5 px/frame at 60fps, so 0.2 px/frame trips at
 * 4% of full speed: a light thumb on the stick, a collision slide along a wall, or AK_PATHWALK's
 * centre-line assist nudging me.x all sit right on top of it. Every chatter costs a full restart,
 * and a 2.4s walk cycle restarted every few frames never gets past its first frames -- the legs
 * twitch in place and the body never takes weight. Exactly "no foot animation or weight".
 *
 * THE FIX, in the two places it belongs:
 *   1. KEEP-ALIVE  after hub3d has written left/top, if the rect has gone FULLY outside the
 *      viewport, slide it back to leave KEEP_IN px on screen. The hero is off-screen either way so
 *      nothing moves visually, but the mixer keeps ticking and he is mid-stride when he returns.
 *   2. HYSTERESIS  debounce moving/running before hub3d sees them, so threshold chatter cannot
 *      restart the cycle. Starts are instant (0ms) -- the walk must begin the frame he steps off.
 *      Stops are held. Never restarts a clip hub3d already has bound.
 *   3. STALL WATCHDOG  belt and braces. If the clock is bit-identical for STALL_MS while a clip is
 *      bound and unpaused, re-issue play(). Catches anything the two rules above did not.
 *
 * WHY A WRAPPER AND NOT AN EDIT TO hub3d.js: hub3d.js is owned by a single Wire phase and has been
 * corrupted before by concurrent editors. Everything here works by wrapping window.__hero3d.pos,
 * so integration is ONE <script> tag and hub3d.js is not touched.
 */
window.AK_HEROANIM = (function (root) {
  'use strict';

  var ENABLED = true;

  /* ---- tunables, all derived from the measurements in the header ---- */

  // px of the element to keep inside the viewport when it would otherwise be fully outside.
  // The sweep shows ONE pixel of overlap is already enough to keep the mixer ticking; 3 buys
  // margin against sub-pixel rounding and devicePixelRatio without ever being visible (the hero
  // is off-screen by definition whenever this clamp fires).
  var KEEP_IN = 3;

  // Hysteresis. Starting is free -- flipping idle->walk when he steps off is exactly what we want,
  // and it can only happen once per stop. Stopping is what needs holding: avMoving trips at 4% of
  // full speed, so it chatters at frame rate (16ms) whenever he is slow, wall-sliding, or being
  // nudged by AK_PATHWALK. 180ms swallows ~11 frames of that. It stays well under one footfall --
  // the bcardd walk clip runs ~2.4s for 2 strides, so a foot plants about every 600ms -- which is
  // why a genuine stop still reads as a stop and not as a dog moonwalking to a halt.
  var STOP_HOLD_MS  = 180;
  // walk<->run swaps a whole cycle for another whole cycle, so it is more jarring than idle->walk
  // and gets a slightly longer hold. Sprint is entered deliberately (double-tap stick or Shift,
  // index.html:2564), so a little extra latency costs nothing.
  var RUN_HOLD_MS   = 220;

  // A bit-identical clock for this long means the mixer is not being ticked. At 60fps a live clip
  // moves ~16ms per frame, so 400ms of no change is ~25 dead frames -- far past any GC pause or
  // scheduling hiccup, and still fast enough that the player never registers the stall.
  var STALL_MS      = 400;
  // Watchdog cadence. Every 8th rAF (~133ms at 60fps) keeps it off the hot path -- the same
  // "cheap loop beside the render" shape hub3d already uses for hideLoop/unitLoop.
  var WATCH_EVERY   = 8;

  /* ---- state ---- */
  var _mv = null;               // the hero <model-viewer>, resolved lazily
  var _wrapped = false;
  var _lastMovingT = 0;         // ms of the last frame the raw flag said "moving"
  var _lastRunT    = 0;
  var _outMoving = false, _outRunning = false;
  var _clockVal = -1, _clockAt = 0;   // stall detector
  var _tick = 0;
  var _diag = { calls: 0, clamps: 0, chatterSwallowed: 0, stalls: 0, revives: 0,
                lastClamp: '', lastAnim: '', lastClock: 0 };

  function now() { try { return performance.now(); } catch (_e) { return Date.now(); } }

  /* The hero element. hub3d builds it lazily on the first pos() call and never exposes it, so we
   * find it by the one stable discriminator in the file: the hero is z-index 3 (hub3d.js:168) and
   * every pooled crew unit is z-index 2 (hub3d.js:285). Re-resolve if it is torn out of the DOM. */
  function heroEl() {
    if (_mv && _mv.isConnected) return _mv;
    _mv = null;
    try {
      var all = document.querySelectorAll('model-viewer');
      for (var i = 0; i < all.length; i++) {
        if (all[i].style && all[i].style.zIndex === '3') { _mv = all[i]; break; }
      }
      if (!_mv && all.length === 1) _mv = all[0];   // only one on stage = it is the hero
    } catch (_e) { _mv = null; }
    return _mv;
  }

  /* KEEP-ALIVE. Read the numbers hub3d just wrote as strings rather than calling
   * getBoundingClientRect(): the rect would force a synchronous layout flush every frame, which on
   * a phone at 60fps is a real cost to pay for information we already have. Only writes back when
   * the value actually changes. */
  function keepAlive(el) {
    if (!el || !el.style) return false;
    var s = el.style;
    var L = parseFloat(s.left), T = parseFloat(s.top);
    var W = parseFloat(s.width), H = parseFloat(s.height);
    if (!isFinite(L) || !isFinite(T) || !isFinite(W) || !isFinite(H) || W <= 0 || H <= 0) return false;
    var vw = root.innerWidth || 0, vh = root.innerHeight || 0;
    if (vw <= 0 || vh <= 0) return false;
    var nL = L, nT = T, why = '';
    // fully past an edge => pull back so KEEP_IN px stay inside. Anything even partly on screen is
    // left EXACTLY where hub3d put it; the sweep proves 1px of overlap already keeps the mixer alive.
    if (L + W <= 0)      { nL = KEEP_IN - W; why += 'L'; }
    else if (L >= vw)    { nL = vw - KEEP_IN; why += 'R'; }
    if (T + H <= 0)      { nT = KEEP_IN - H; why += 'T'; }
    else if (T >= vh)    { nT = vh - KEEP_IN; why += 'B'; }
    if (nL === L && nT === T) return false;
    if (nL !== L) s.left = nL + 'px';
    if (nT !== T) s.top  = nT + 'px';
    _diag.clamps++; _diag.lastClamp = why;
    return true;
  }

  /* HYSTERESIS. Rising edge passes straight through; falling edge is held. */
  function smooth(rawMoving, rawRunning) {
    var t = now();
    if (rawMoving) _lastMovingT = t;
    if (rawRunning) _lastRunT = t;
    var m = rawMoving || (t - _lastMovingT) < STOP_HOLD_MS;
    var r = rawRunning || (t - _lastRunT) < RUN_HOLD_MS;
    if (!rawMoving && m) _diag.chatterSwallowed++;   // a stop hub3d never got to act on
    r = r && m;                                      // running only means anything while moving
    _outMoving = m; _outRunning = r;
    return m;
  }

  /* STALL WATCHDOG. currentTime loops, so "went backwards" is normal and must NOT count as a
   * stall -- only a value that has not changed AT ALL for STALL_MS does. */
  function watch() {
    if (!ENABLED) return;
    var el = heroEl();
    if (!el) return;
    var c;
    try { c = el.currentTime; } catch (_e) { return; }
    if (typeof c !== 'number' || !isFinite(c)) return;
    _diag.lastClock = c;
    try { _diag.lastAnim = el.animationName || ''; } catch (_e) {}
    var t = now();
    if (c !== _clockVal) { _clockVal = c; _clockAt = t; return; }
    if (!_clockAt) { _clockAt = t; return; }
    if ((t - _clockAt) < STALL_MS) return;
    // clock is dead. If it is dead because we are off-screen, keepAlive on the next pos() will fix
    // it; re-issuing play() covers a mixer that was left paused or an action that never started.
    _diag.stalls++;
    try {
      if (el.paused || _outMoving || _diag.lastAnim) { el.play(); _diag.revives++; }
    } catch (_e) {}
    _clockAt = t;
  }

  (function watchLoop() {
    try { if ((++_tick % WATCH_EVERY) === 0) watch(); } catch (_e) {}
    try { requestAnimationFrame(watchLoop); } catch (_e) {}
  })();

  /* ---- install: wrap __hero3d.pos ----------------------------------------------------------
   * index.html:2836 calls window.__hero3d.pos(X,Y,avMoving,faceDir,me.r*ds,faceAngle,running).
   * We debounce args 3 and 7, hand the rest through untouched, then keep-alive the element hub3d
   * just repositioned. Idempotent -- a second install() is a no-op. */
  function install() {
    if (_wrapped) return true;
    var H = root.__hero3d;
    if (!H || typeof H.pos !== 'function') return false;
    var orig = H.pos;
    H.pos = function (x, y, moving, faceDir, r, faceAngle, running) {
      if (!ENABLED) return orig.apply(this, arguments);
      _diag.calls++;
      var m = smooth(!!moving, !!running);
      var out;
      try { out = orig.call(this, x, y, m, faceDir, r, faceAngle, _outRunning); }
      catch (_e) { out = undefined; }
      // AFTER hub3d has written left/top for this frame -- ordering matters, a rAF-based clamp
      // would race the draw and clamp last frame's position.
      try { keepAlive(heroEl()); } catch (_e2) {}
      return out;
    };
    _wrapped = true;
    return true;
  }

  // hub3d.js is included at index.html:597 and defines window.__hero3d at parse time, so a script
  // tag placed after it installs on the first try. The retry exists so load ORDER is not a
  // correctness requirement -- if this file ever ends up above hub3d.js it still lands.
  if (!install()) {
    var tries = 0;
    var iv = setInterval(function () {
      if (install() || ++tries > 200) { try { clearInterval(iv); } catch (_e) {} }
    }, 50);
  }

  var api = {
    id: 'akheroanim',
    init: function () { install(); }
  };
  if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api);

  return {
    install: install,
    isInstalled: function () { return _wrapped; },
    setEnabled: function (b) { ENABLED = !!b; return ENABLED; },
    isEnabled: function () { return ENABLED; },
    el: heroEl,
    // live readout, and the thing the proof harness samples
    state: function () {
      var el = heroEl(), a = '', c = 0, p = null;
      try { if (el) { a = el.animationName || ''; c = el.currentTime || 0; p = !!el.paused; } } catch (_e) {}
      return { anim: a, clock: c, paused: p, moving: _outMoving, running: _outRunning,
               installed: _wrapped, enabled: ENABLED };
    },
    diag: function () {
      return { calls: _diag.calls, clamps: _diag.clamps, lastClamp: _diag.lastClamp,
               chatterSwallowed: _diag.chatterSwallowed, stalls: _diag.stalls, revives: _diag.revives,
               anim: _diag.lastAnim, clock: _diag.lastClock,
               installed: _wrapped, enabled: ENABLED,
               tunables: { KEEP_IN: KEEP_IN, STOP_HOLD_MS: STOP_HOLD_MS, RUN_HOLD_MS: RUN_HOLD_MS,
                           STALL_MS: STALL_MS } };
    },
    // test seam: the pure hysteresis rule, so it can be checked without a browser
    _smooth: smooth,
    _setHolds: function (stopMs, runMs) { STOP_HOLD_MS = stopMs; RUN_HOLD_MS = runMs; },
    _keepAlive: keepAlive
  };
})(window);
