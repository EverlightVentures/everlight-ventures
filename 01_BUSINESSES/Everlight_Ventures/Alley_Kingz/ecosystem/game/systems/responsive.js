/* ==========================================================================
   ALLEY KINGZ // THE RESPONSIVE SHELL  (AK-RESPONSIVE 2026-07-11)
   The single "how big is this screen, and how do I draw crisp on it?" module.
   PURE LOGIC + one opt-in DOM writer -- zero UI of its own, zero load-time side
   effects beyond defining window.AK_RESPONSIVE. It reads the live CSS viewport
   (NOT screen.width), classifies the device into a TIER, and hands the rest of
   the game two things:
     1. a TIER + a font/spacing SCALE it can drive CSS from (data-ak-tier +
        --ak-scale on <html>), and
     2. fitCanvas() -- the crisp-render helper that mirrors the game's existing
        DPR idiom (Math.min(2,dpr) + ctx.setTransform) so ALL current draw code,
        which works in CSS px, renders sharp on high-DPR / foldable screens.

   Design contract (why this file exists):
   - HEADLESS-SAFE: zero load-time DOM, zero top-level window/document reads.
     Every access is guarded; on a node harness (no window) it degrades to safe
     neutral defaults and never throws.
   - OPT-IN CANVAS: the game already sizes its own <canvas> (index.html resize(),
     game.html resize()). fitCanvas() is a TOOL the wire lanes call where they
     choose. This module NEVER auto-hijacks a canvas on load -- breaking canvas
     sizing = a black screen.
   - DPR CAPPED AT 2: high-DPR phones report dpr 3+; a 3x backing store is a perf
     tax with no visible gain at phone sizes, so fitCanvas caps at 2 (matches the
     existing `DPR=Math.min(2,devicePixelRatio||1)` in index.html:449).
   - NO RANDOMNESS, NO TIMERS AT LOAD: onChange() is the only place listeners get
     wired, and only when the caller asks.

   Include order: anywhere in <head>/<body>; it depends on nothing. CSS that wants
   to respond reads it via [data-ak-tier="compact"] selectors + var(--ak-scale).
     <script src="systems/responsive.js"></script>

   TIER breakpoints (CSS viewport width, px -- from the device research):
     compact      <= 380     small / older phones          scale 0.90
     standard     381 - 438  the modern phone baseline      scale 1.00
     comfortable  439 - 520  large phones (Pro Max / Ultra) scale 1.06
     wide         521 - 639  phablet / small tablet portrait scale 1.12
     fold         >= 640     unfolded foldable / tablet      scale 1.20

   Public API on window.AK_RESPONSIVE:
     detect(vwOverride?) -> { vw, vh, dpr, tier, scale, orientation, ar, fold }
     apply(info?)        -> info  (writes data-ak-tier + --ak-vw + --ak-scale on <html>)
     fitCanvas(canvas, ctx, cssW, cssH) -> effectiveScale (min(dpr,2)); OPT-IN
     onChange(cb)        -> unsubscribe fn  (debounced resize/orient/fold, re-runs detect+apply)
     tier()  -> string   scale() -> number   info() -> detect()
     BREAKPOINTS         -> { compact, standard, comfortable, wide }  (upper bounds)
   ========================================================================== */
(function (global) {
  "use strict";

  // ---- tunables ------------------------------------------------------------
  // Upper bound of each tier (inclusive). fold = anything above `wide`.
  var BREAKPOINTS = { compact: 380, standard: 438, comfortable: 520, wide: 639 };
  var SCALE = { compact: 0.9, standard: 1.0, comfortable: 1.06, wide: 1.12, fold: 1.2 };
  var DPR_CAP = 2;             // never build a backing store denser than 2x
  var DEBOUNCE_MS = 160;       // resize/orient coalesce window

  // ---- small guarded helpers ----------------------------------------------
  function num(v, d) { return (typeof v === "number" && isFinite(v)) ? v : d; }
  function clampN(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function docEl() {
    try { return (global.document && global.document.documentElement) || null; }
    catch (_) { return null; }
  }

  // Live CSS viewport WIDTH (px). window.innerWidth is the CSS layout width and
  // is the correct signal (NOT screen.width, which is the physical panel and is
  // wrong under browser zoom / split-screen / foldable postures). Falls back to
  // documentElement.clientWidth, then 0 (headless -> neutral default downstream).
  function readVW(g) {
    try {
      if (g && typeof g.innerWidth === "number" && g.innerWidth > 0) return g.innerWidth;
      var d = g && g.document && g.document.documentElement;
      if (d && d.clientWidth > 0) return d.clientWidth;
    } catch (_) {}
    return 0;
  }
  function readVH(g) {
    try {
      if (g && typeof g.innerHeight === "number" && g.innerHeight > 0) return g.innerHeight;
      var d = g && g.document && g.document.documentElement;
      if (d && d.clientHeight > 0) return d.clientHeight;
    } catch (_) {}
    return 0;
  }

  // vw -> tier string. A non-positive vw (headless / unknown) resolves to the
  // "standard" 1.0 baseline so nothing scales weirdly before the DOM reports a
  // real width.
  function tierFor(vw) {
    var v = num(vw, 0);
    if (v <= 0) return "standard";
    if (v <= BREAKPOINTS.compact) return "compact";
    if (v <= BREAKPOINTS.standard) return "standard";
    if (v <= BREAKPOINTS.comfortable) return "comfortable";
    if (v <= BREAKPOINTS.wide) return "wide";
    return "fold";
  }

  // Fold heuristic: true when the viewport looks like an unfolded book-style
  // foldable or a tablet in portrait. Three signals, any one wins:
  //   a) tier is already `fold` (>= 640 CSS px wide), the dominant case;
  //   b) unusually wide AND near-square aspect (an unfolded inner display);
  //   c) the experimental viewport-segments media query reports 2 segments.
  function foldHeuristic(g, vw, vh, ar, tier) {
    if (tier === "fold") return true;
    if (vw >= 560 && ar >= 0.72 && ar <= 1.5) return true;
    try {
      if (g && typeof g.matchMedia === "function") {
        var mq = g.matchMedia("(horizontal-viewport-segments: 2)");
        if (mq && mq.matches) return true;
      }
    } catch (_) {}
    return false;
  }

  // ---- detect --------------------------------------------------------------
  // Pure read. Optional vwOverride lets callers/tests classify an explicit width
  // without touching the DOM; omitted -> reads the live CSS viewport.
  function detect(vwOverride) {
    var g = global;
    var vw = num(vwOverride, 0) || readVW(g);
    var vh = readVH(g);
    var dpr = num(g && g.devicePixelRatio, 1);
    if (!(dpr > 0)) dpr = 1;                         // raw dpr (uncapped); fitCanvas applies the cap
    var tier = tierFor(vw);
    var ar = vh > 0 ? vw / vh : 0;                   // aspect ratio (w/h)
    var orientation = (vw && vh) ? (vw >= vh ? "landscape" : "portrait") : "portrait";
    var fold = foldHeuristic(g, vw, vh, ar, tier);
    return {
      vw: vw, vh: vh, dpr: dpr, tier: tier,
      scale: SCALE[tier] || 1, orientation: orientation, ar: ar, fold: fold
    };
  }

  // ---- apply ---------------------------------------------------------------
  // Writes the classification onto <html> so CSS can respond:
  //   [data-ak-tier="comfortable"] { ... }      and      font-size: calc(14px * var(--ak-scale));
  // Guarded: on a headless harness docEl() is null and this is a no-op that still
  // returns the info object.
  function apply(info) {
    var d = (info && info.tier) ? info : detect();
    var de = docEl();
    if (de) {
      try { de.setAttribute("data-ak-tier", d.tier); } catch (_) {}
      try {
        if (de.style && de.style.setProperty) {
          de.style.setProperty("--ak-vw", (d.vw || 0) + "px");
          de.style.setProperty("--ak-scale", String(d.scale || 1));
        }
      } catch (_) {}
    }
    return d;
  }

  // ---- fitCanvas (the crux) ------------------------------------------------
  // OPT-IN. Sizes a canvas backing store to the capped device pixel ratio and
  // pre-scales the 2D context so ALL existing draw code -- which is written in
  // CSS px -- renders crisp without changing a single draw call. This is exactly
  // the idiom already used inline in index.html/game.html, factored out so the
  // wire lanes can share it. Returns the effective scale (min(dpr,2)).
  //
  //   canvas.width  = round(cssW * s)   backing store, s = min(dpr, 2)
  //   canvas.height = round(cssH * s)
  //   canvas.style.{width,height} = css px   (display size stays in CSS px)
  //   ctx.setTransform(s,0,0,s,0,0)          (1 unit = 1 CSS px, drawn at s density)
  //
  // If cssW/cssH are omitted or non-positive, falls back to the canvas's current
  // clientWidth/clientHeight so a CSS-laid-out canvas can be fit with just
  // fitCanvas(canvas, ctx). Fully guarded; a bad canvas/ctx returns 1 and no-ops.
  function fitCanvas(canvas, ctx, cssW, cssH) {
    var s = clampN(num(global.devicePixelRatio, 1), 1, DPR_CAP);
    if (!canvas) return s;
    var w = num(cssW, 0), h = num(cssH, 0);
    if (w <= 0) { try { w = num(canvas.clientWidth, 0); } catch (_) {} }
    if (h <= 0) { try { h = num(canvas.clientHeight, 0); } catch (_) {} }
    if (w <= 0 || h <= 0) return s;                 // nothing to size against yet
    try { canvas.width = Math.round(w * s); canvas.height = Math.round(h * s); } catch (_) {}
    try {
      if (canvas.style) { canvas.style.width = w + "px"; canvas.style.height = h + "px"; }
    } catch (_) {}
    try { if (ctx && typeof ctx.setTransform === "function") ctx.setTransform(s, 0, 0, s, 0, 0); } catch (_) {}
    return s;
  }

  // ---- onChange ------------------------------------------------------------
  // Debounced re-classify on resize / orientationchange / visualViewport resize
  // / fold media-query flip. Re-runs detect()+apply() then hands the caller the
  // fresh info. Returns an unsubscribe fn. No-ops (returns a no-op unsubscribe)
  // when the environment has no event surface.
  function onChange(cb) {
    if (typeof cb !== "function") return function () {};
    var g = global, offs = [], t = null;

    function fire() {
      try { if (t) clearTimeout(t); } catch (_) {}
      try {
        t = setTimeout(function () {
          t = null;
          var info = apply(detect());
          try { cb(info); } catch (_) {}
        }, DEBOUNCE_MS);
      } catch (_) {
        // no setTimeout -> run immediately (best effort)
        var info2 = apply(detect());
        try { cb(info2); } catch (_e) {}
      }
    }

    function on(target, ev) {
      try {
        if (target && typeof target.addEventListener === "function") {
          target.addEventListener(ev, fire);
          offs.push(function () { try { target.removeEventListener(ev, fire); } catch (_) {} });
        }
      } catch (_) {}
    }

    on(g, "resize");
    on(g, "orientationchange");
    try { if (g.visualViewport) on(g.visualViewport, "resize"); } catch (_) {}

    // fold flip (crossing into the `fold` tier)
    try {
      if (typeof g.matchMedia === "function") {
        var mq = g.matchMedia("(min-width:" + (BREAKPOINTS.wide + 1) + "px)");
        if (mq) {
          if (typeof mq.addEventListener === "function") {
            mq.addEventListener("change", fire);
            offs.push(function () { try { mq.removeEventListener("change", fire); } catch (_) {} });
          } else if (typeof mq.addListener === "function") { // Safari < 14
            mq.addListener(fire);
            offs.push(function () { try { mq.removeListener(fire); } catch (_) {} });
          }
        }
      }
    } catch (_) {}

    return function unsubscribe() {
      for (var i = 0; i < offs.length; i++) { try { offs[i](); } catch (_) {} }
      offs.length = 0;
      try { if (t) clearTimeout(t); } catch (_) {}
      t = null;
    };
  }

  // ---- getters -------------------------------------------------------------
  function tier() { return detect().tier; }
  function scale() { return detect().scale; }
  function info() { return detect(); }

  // ---- export (the ONLY load-time side effect) -----------------------------
  global.AK_RESPONSIVE = {
    detect: detect,
    apply: apply,
    fitCanvas: fitCanvas,
    onChange: onChange,
    tier: tier,
    scale: scale,
    info: info,
    BREAKPOINTS: BREAKPOINTS,
    SCALE: SCALE,
    DPR_CAP: DPR_CAP
  };

})(typeof window !== "undefined" ? window : (typeof globalThis !== "undefined" ? globalThis : this));
