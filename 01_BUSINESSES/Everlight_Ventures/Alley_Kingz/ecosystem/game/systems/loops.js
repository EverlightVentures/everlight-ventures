/* ALLEY KINGZ -- systems/loops.js  (AK-LOOPS 2026-06-20)
   CinematicLoop manager -- per ALLEY_KINGZ_DEEP_DIVE_SYNTHESIS Part 2 ("VIDEO / MP4").
   Turns flat static panels into a "breathing" world: a looping, muted, low-opacity
   video backdrop blended (mix-blend-mode) behind the menus/keeper-card surfaces.

   HARD LAW: menu_bg.mp4 is the ONLY video asset in the build. This manager reuses
   that one file for every surface -- it NEVER invents new video files.

   DESIGN (faithful to the synthesis manager):
     - register/play/pause, budget=3 concurrent (mobile cap), priority eviction.
     - every video: muted + playsInline + loop  (no autoplay restriction, iOS-safe).
     - low opacity + mix-blend-mode  (atmosphere, not focus -- blends into the art).
     - pointer-events:none, GPU-friendly, paused when its surface is hidden.

   PERF (the $100-Android law): at most ~2 of these ever play at once (interior OR
   shop), well under the budget of 3; paused on document-hidden and reduced-motion;
   one operator kill-switch (localStorage ak_loops_off=1) for low-end devices.
   The heavy loadscreen video (#ls-vid) is left to index.html -- not double-managed.

   WIRING: self-sufficient with only a <script src="systems/loops.js"> tag.
     - As an AK_SYSTEMS module it attaches the #interior backdrop on init.
     - A MutationObserver on #interior's display drives play/pause automatically,
       so it works no matter which wave module "claims" the building.
     - Explicit API (window.AKLoops) is also exposed for index.html / shop.js hooks.
*/
(function () {
  "use strict";

  // The one and only video asset. Reused for every cinematic loop surface.
  var MENU_BG = "assets/ui/menu_bg.mp4";

  function reduceMotion() {
    try { return !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches); }
    catch (_e) { return false; }
  }
  function userDisabled() {
    try { return localStorage.getItem("ak_loops_off") === "1"; } catch (_e) { return false; }
  }

  // ---- the manager -------------------------------------------------------
  function CinematicLoop() {
    this.loops  = {};   // id -> { video, opts, priority }
    this.active = {};   // id -> true (currently playing)
    this.budget = 3;    // max concurrent videos (mobile)
    this.enabled = !reduceMotion() && !userDisabled();
    this._suspended = {}; // ids paused by a visibility/disable sweep, to resume
  }

  /* register(id, opts) -- create (once) the <video> for a surface and return it.
     opts: { src, opacity=0.45, blend='screen', zIndex=1, priority=0 } */
  CinematicLoop.prototype.register = function (id, opts) {
    if (this.loops[id]) return this.loops[id].video;
    opts = opts || {};
    var v = document.createElement("video");
    v.src = opts.src || MENU_BG;
    v.loop = true;            v.setAttribute("loop", "");
    v.muted = true;           v.setAttribute("muted", "");   // CRITICAL: muted = no autoplay block
    v.defaultMuted = true;
    v.playsInline = true;     v.setAttribute("playsinline", ""); // iOS requirement
    v.preload = "metadata";
    v.setAttribute("aria-hidden", "true");
    v.setAttribute("tabindex", "-1");
    try { v.disablePictureInPicture = true; v.disableRemotePlayback = true; } catch (_e) {}
    v.style.cssText =
      "position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;" +
      "opacity:" + (opts.opacity != null ? opts.opacity : 0.45) + ";" +
      "mix-blend-mode:" + (opts.blend || "screen") + ";" +
      "pointer-events:none;z-index:" + (opts.zIndex != null ? opts.zIndex : 1) + ";";
    this.loops[id] = { video: v, opts: opts, priority: opts.priority || 0 };
    return v;
  };

  /* mount(id, parent, opts) -- register if needed + attach to a container.
     opts.first=true inserts as the FIRST child (backmost layer). idempotent. */
  CinematicLoop.prototype.mount = function (id, parent, opts) {
    opts = opts || {};
    var v = this.register(id, opts);
    if (parent && v.parentNode !== parent) {
      if (opts.first && parent.firstChild) parent.insertBefore(v, parent.firstChild);
      else parent.appendChild(v);
    }
    return v;
  };

  CinematicLoop.prototype.get = function (id) {
    var l = this.loops[id]; return l ? l.video : null;
  };
  CinematicLoop.prototype.isActive = function (id) { return !!this.active[id]; };

  // evict the lowest-priority active loop to make room (budget guard)
  CinematicLoop.prototype._evict = function () {
    var ids = Object.keys(this.active);
    if (ids.length < this.budget) return;
    var self = this;
    ids.sort(function (a, b) { return (self.loops[a].priority) - (self.loops[b].priority); });
    this.pause(ids[0]);
  };

  CinematicLoop.prototype.play = function (id) {
    if (!this.enabled) return;
    var l = this.loops[id]; if (!l) return;
    if (this.active[id]) return;
    if (Object.keys(this.active).length >= this.budget) this._evict();
    try {
      var p = l.video.play();
      if (p && p.catch) p.catch(function (e) { try { console.log("[AK-LOOPS] play blocked:", id, e && e.name); } catch (_e) {} });
    } catch (_e) {}
    this.active[id] = true;
  };

  CinematicLoop.prototype.pause = function (id) {
    var l = this.loops[id]; if (!l) return;
    try { l.video.pause(); } catch (_e) {}
    delete this.active[id];
  };

  CinematicLoop.prototype.stop = function (id) {
    this.pause(id);
    var l = this.loops[id]; if (l) try { l.video.currentTime = 0; } catch (_e) {}
  };

  CinematicLoop.prototype.pauseAll = function () {
    var self = this; Object.keys(this.active).forEach(function (id) { self.pause(id); });
  };

  /* setEnabled(false) parks every loop (low-end kill switch); true resumes. */
  CinematicLoop.prototype.setEnabled = function (on) {
    on = !!on;
    if (on === this.enabled) return;
    this.enabled = on;
    if (!on) this.pauseAll();
  };

  // ---- singleton ---------------------------------------------------------
  var AKLoops = new CinematicLoop();

  // Pause loops while the tab/app is backgrounded; resume what was playing.
  try {
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        AKLoops._suspended = {};
        Object.keys(AKLoops.active).forEach(function (id) { AKLoops._suspended[id] = true; });
        AKLoops.pauseAll();
      } else if (AKLoops.enabled) {
        Object.keys(AKLoops._suspended).forEach(function (id) { AKLoops.play(id); });
        AKLoops._suspended = {};
      }
    });
  } catch (_e) {}

  // ---- INTERIOR backdrop wiring (the #int-bg surface) --------------------
  // The keeper interior (#interior) currently shows a STATIC #int-bg (art or a
  // radial gradient) behind #int-card. We add a looping menu_bg.mp4 layer that
  // sits ABOVE #int-bg (z-index 1) but BELOW #int-card (z-index 2) -- screen-
  // blended low-opacity so the static art still reads, but the backdrop breathes.
  // Idempotent + driven by a MutationObserver so it works regardless of which
  // wave module claims the building.
  var _intObserver = null;
  function attachInterior() {
    var interior = document.getElementById("interior");
    if (!interior) return false;
    // mount the loop (above #int-bg [auto z], below #int-card [z 2])
    AKLoops.mount("interior", interior, { opacity: 0.5, blend: "screen", zIndex: 1, priority: 5 });
    // play/pause from the panel's own display toggle
    function sync() {
      var shown = getComputedStyle(interior).display !== "none";
      if (shown) AKLoops.play("interior"); else AKLoops.pause("interior");
    }
    if (!_intObserver) {
      try {
        _intObserver = new MutationObserver(sync);
        _intObserver.observe(interior, { attributes: true, attributeFilter: ["style", "class"] });
      } catch (_e) {}
    }
    sync();
    return true;
  }
  AKLoops.attachInterior = attachInterior;

  /* attachShop(rootEl) -- mount the backdrop into the Chop Shop overlay (.akshop).
     Called by shop.js's ensureRoot(); play/pause via AKLoops.play/pause('shop'). */
  AKLoops.attachShop = function (rootEl) {
    if (!rootEl) return null;
    return AKLoops.mount("shop", rootEl, { opacity: 0.4, blend: "screen", zIndex: 0, priority: 4, first: true });
  };

  // ---- registration / boot ----------------------------------------------
  // As an AK_SYSTEMS module: attach the interior backdrop on host init.
  // (No onEnterBuilding -> it never "claims" a building; purely additive.)
  if (window.AK_SYSTEMS && AK_SYSTEMS.register) {
    AK_SYSTEMS.register({ id: "loops", init: function () { attachInterior(); } });
  }
  // Self-init fallback (when AK_SYSTEMS is absent or initAll already ran).
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attachInterior);
  } else {
    attachInterior();
  }

  window.AKLoops = AKLoops;
  window.CinematicLoop = window.CinematicLoop || CinematicLoop;
})();
