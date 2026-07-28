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
      // AK-INTBG 2026-06-20 (#9): the menu_bg.mp4 interior backdrop is scoped to the TOWN HALL ONLY.
      // index.html exposes window.akInteriorWantsVideo() (true only for the ARENA / Town Hall interior);
      // every other building shows its OWN static interior art (no video). Absent hook => play (back-compat).
      var wantVid = (typeof window.akInteriorWantsVideo === "function") ? !!window.akInteriorWantsVideo() : true;
      if (shown && wantVid) AKLoops.play("interior"); else AKLoops.pause("interior");
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

  // ==========================================================================
  // P9 -- VARIABLE-RATIO REVEAL CINEMATIC  (the Scrap Crate open + generic
  //        reward-reveal). The dopamine spike from AK_CAPTIVATION_PLAN P9.
  //
  //   WHAT IT IS: a suspense BUILD (the crate rumbles, a rarity ticker climbs,
  //   the gold ring tightens) that pays off in a CRACK + burst SPIKE. The
  //   "variable-ratio" feel is in the PRESENTATION ONLY -- the suspense length
  //   and an occasional near-miss overshoot vary open-to-open, but the reveal
  //   ALWAYS lands on the TRUE rarity the caller passes in.
  //
  //   PARITY HARD-LAW: this is a pure PRESENTATION layer. It NEVER grants,
  //   spends, mutates the profile, or touches gems. The caller (shop.js
  //   openLocalChest / a crate button) decides the reward deterministically via
  //   AK_ECON, then hands us the result to ANIMATE. Zero state -> zero-state is
  //   byte-identical, nothing pay-to-win.
  //
  //   DETERMINISTIC-BY-TIME: the only randomness is the cosmetic suspense
  //   flavor, seeded from the local-PT clock (replay the same instant -> same
  //   show). It affects NO gameplay outcome, so it cannot break parity.
  //
  //   60fps CHEAP-ANDROID: GPU-only CSS animations (transform/opacity), a tiny
  //   handful of setTimeout phase beats (no rAF, no per-frame JS), the spark
  //   burst is capped (14), DOM is built once + the stage is reused. The shared
  //   menu_bg.mp4 backdrop rides the CinematicLoop budget (priority 10, screen
  //   blend, low opacity) -- still well under budget 3.
  //
  //   REDUCED-MOTION / KILL-SWITCH SAFE: if reduced-motion, the loops kill
  //   switch, or a reveal is already running, we SKIP the cinematic and deliver
  //   the reward instantly (the reward is never stranded). Tap-to-skip cracks
  //   it early -- a crate open must never block input the player initiated.
  //
  //   HOOK (for the integration pass -- shop/crate calls this):
  //     AKLoops.reveal({
  //       kind:     "crate" | "reward",        // crate = Scrap Crate, reward = generic payout
  //       tier:     "wood".."diamond" | sku,   // optional -> picks the crate label
  //       rarity:   "Common".."Mythic",        // the TRUE top rarity -> drives the glow + landed flicker
  //       title:    "SCRAP CRATE",             // optional label override
  //       subtitle: "the Fence pries the lid", // optional flavor line override (canon)
  //       onReveal: fn,   // fired AT the spike -- the caller renders the real cards now (showReveal)
  //       onDone:   fn,   // fired after the cinematic dissolves
  //       seed:     n     // optional explicit cosmetic seed (default: local-PT clock)
  //     }) -> { skip:fn }
  //     AKLoops.revealCrate(tier, rarity, onReveal, onDone)  // convenience
  //     window.AKReveal(opts)                                // documented thin alias
  // ==========================================================================
  var RV_GOLD = "#D4AF37";
  var RV_ORDER = ["Common", "Rare", "Epic", "Legendary", "Mythic"];
  // mirrors engine.js RARITY_COL (Mythic = crown gold). Local copy -- loops.js is standalone.
  var RV_RARITY_COL = { Common: "#4A4A55", Rare: "#00BFFF", Epic: "#C1440E", Legendary: "#E6B800", Mythic: "#D4AF37" };
  // canon crate labels (shop SKUs + earned tiers) -- no Kimi generics.
  var RV_CRATE_LABEL = {
    wood: "SCRAP CRATE", bronze: "BRONZE CRATE", silver: "SILVER CRATE", gold: "GOLD CRATE", diamond: "DIAMOND CRATE",
    chest_scrap_crate: "SCRAP CRATE", chest_crew: "CREW CHEST", chest_chop_shop: "CHOP-SHOP CRATE", chest_kingpin: "KINGPIN CRATE"
  };
  // canon flavor lines (the Fence, the nine districts, the clans, the Old Pack).
  var RV_FLAVOR = [
    "the Fence pries the lid",
    "word runs the nine districts",
    "Boneguard muscle hauled it in",
    "Zoomie Syndicate runners clocked it",
    "the Old Pack is watching",
    "King of the Block money"
  ];

  var RV = { busy: false, root: null, bg: null, stage: null, skip: null, css: false, timers: [], _skip: null };

  // cosmetic-only seed, anchored to the local clock (PT for the operator).
  // Replay the same instant -> the same show. Changes NO state -> parity-safe.
  function rvSeed(explicit) {
    if (typeof explicit === "number" && isFinite(explicit)) return explicit >>> 0;
    var n = Date.now();
    return (n ^ (n >>> 9) ^ 0x9E3779B9) >>> 0;
  }
  // mulberry32 -- a deterministic PRNG for the COSMETIC suspense only.
  function rvRng(a) {
    a = a >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function rvAfter(ms, fn) { var t = setTimeout(fn, ms); RV.timers.push(t); return t; }
  function rvClearTimers() { RV.timers.forEach(function (t) { clearTimeout(t); }); RV.timers = []; }
  function rvEl(cls, parent) { var d = document.createElement("div"); if (cls) d.className = cls; if (parent) parent.appendChild(d); return d; }
  // safe clear -- detach children one by one (no innerHTML / no untrusted markup).
  function rvClear(node) { if (!node) return; while (node.firstChild) node.removeChild(node.firstChild); }

  function rvInjectCSS() {
    if (RV.css) return;
    RV.css = true;
    var css =
      '#ak-reveal{position:fixed;inset:0;z-index:100003;display:none;align-items:center;justify-content:center;' +
      'opacity:0;transition:opacity .22s ease;overflow:hidden;-webkit-tap-highlight-color:transparent;' +
      'background:radial-gradient(120% 90% at 50% 42%,rgba(212,175,55,.10),rgba(4,4,6,0) 60%),rgba(4,4,6,.93);}' +
      '#ak-reveal.on{opacity:1;}' +
      '#ak-reveal .rv-bg{position:absolute;inset:0;z-index:0;pointer-events:none;}' +
      '#ak-reveal .rv-stage{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;' +
      'gap:14px;width:100%;max-width:480px;padding:20px;text-align:center;}' +
      '#ak-reveal .rv-flav{font:italic 600 13px "Playfair Display",serif;letter-spacing:.04em;color:#c9a84c;opacity:.9;}' +
      '#ak-reveal .rv-tick{font:800 30px Cinzel,serif;letter-spacing:.12em;text-transform:uppercase;' +
      'color:var(--rt,#4A4A55);text-shadow:0 0 18px var(--rt,#4A4A55);min-height:36px;transition:color .08s linear;}' +
      '#ak-reveal .rv-box{position:relative;width:128px;height:128px;}' +
      '#ak-reveal .rv-crate{position:absolute;inset:0;border-radius:16px;' +
      'background:linear-gradient(160deg,#15140e,#0a0a0a 62%);border:2px solid var(--rv,#D4AF37);' +
      'box-shadow:0 0 0 1px rgba(212,175,55,.25),inset 0 0 28px -8px var(--rv,#D4AF37),0 0 36px -10px var(--rv,#D4AF37);' +
      'will-change:transform;}' +
      '#ak-reveal.build .rv-crate{animation:akrvShake .5s ease-in-out infinite;}' +
      '#ak-reveal .rv-crate.crack{animation:akrvCrack .45s ease-out forwards;}' +
      '#ak-reveal .rv-seam{position:absolute;left:8px;right:8px;top:50%;height:2px;transform:translateY(-1px);' +
      'background:var(--rv,#D4AF37);box-shadow:0 0 8px var(--rv,#D4AF37);opacity:.8;}' +
      '#ak-reveal .rv-ring{position:absolute;inset:-22px;border-radius:50%;border:2px solid var(--rv,#D4AF37);' +
      'opacity:0;pointer-events:none;will-change:transform,opacity;}' +
      '#ak-reveal.build .rv-ring{animation:akrvRing 1s ease-out infinite;}' +
      '#ak-reveal .rv-flash{position:absolute;inset:0;z-index:2;pointer-events:none;opacity:0;' +
      'background:radial-gradient(circle at 50% 50%,#fff,var(--rv,#D4AF37) 30%,transparent 70%);}' +
      '#ak-reveal .rv-flash.go{animation:akrvFlash .6s ease-out forwards;}' +
      '#ak-reveal .rv-spark{position:absolute;left:50%;top:50%;width:8px;height:8px;border-radius:50%;' +
      'background:var(--rv,#D4AF37);box-shadow:0 0 8px var(--rv,#D4AF37);opacity:0;pointer-events:none;will-change:transform,opacity;}' +
      '#ak-reveal .rv-spark.go{animation:akrvBurst .7s ease-out forwards;}' +
      '#ak-reveal .rv-land{font:900 40px Cinzel,serif;letter-spacing:.14em;text-transform:uppercase;' +
      'color:var(--rv,#D4AF37);text-shadow:0 0 26px var(--rv,#D4AF37);opacity:0;}' +
      '#ak-reveal .rv-land.go{animation:akrvSlam .5s cubic-bezier(.2,1.3,.4,1) forwards;}' +
      '#ak-reveal .rv-sub{font:600 12px Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#8a8472;}' +
      '#ak-reveal .rv-skip{position:absolute;bottom:18px;right:18px;z-index:3;font:600 11px Inter,sans-serif;' +
      'letter-spacing:.1em;text-transform:uppercase;color:#6f6a5c;pointer-events:none;}' +
      '@keyframes akrvShake{0%,100%{transform:translate3d(0,0,0) rotate(0)}25%{transform:translate3d(-2px,1px,0) rotate(-1.5deg)}50%{transform:translate3d(2px,-1px,0) rotate(1.5deg)}75%{transform:translate3d(-1px,2px,0) rotate(-1deg)}}' +
      '@keyframes akrvCrack{0%{transform:scale(1)}35%{transform:scale(1.18)}100%{transform:scale(2.2);opacity:0}}' +
      '@keyframes akrvRing{0%{transform:scale(1.25);opacity:0}40%{opacity:.7}100%{transform:scale(.7);opacity:0}}' +
      '@keyframes akrvFlash{0%{opacity:0;transform:scale(.4)}30%{opacity:.95}100%{opacity:0;transform:scale(1.6)}}' +
      '@keyframes akrvBurst{0%{transform:translate3d(0,0,0) scale(1);opacity:1}100%{transform:translate3d(var(--tx,0),var(--ty,0),0) scale(.3);opacity:0}}' +
      '@keyframes akrvSlam{0%{transform:scale(1.7);opacity:0}60%{opacity:1}100%{transform:scale(1);opacity:1}}' +
      '@media (prefers-reduced-motion: reduce){#ak-reveal *{animation:none !important}}';
    try {
      var st = document.createElement("style");
      st.id = "ak-rv-css";
      st.textContent = css;
      (document.head || document.documentElement).appendChild(st);
    } catch (_e) {}
  }

  function rvEnsureRoot() {
    if (RV.root) return RV.root;
    rvInjectCSS();
    var root = document.createElement("div"); root.id = "ak-reveal";
    RV.bg = rvEl("rv-bg", root);
    RV.stage = rvEl("rv-stage", root);
    RV.skip = rvEl("rv-skip", root); RV.skip.textContent = "tap to crack";
    root.addEventListener("click", function () { if (RV._skip) RV._skip(); });
    try { document.body.appendChild(root); } catch (_e) {}
    RV.root = root;
    // the one shared menu_bg.mp4 rides the CinematicLoop (priority 10 so the
    // spike is never evicted; screen-blended low opacity = atmosphere not focus).
    try { AKLoops.mount("reveal", RV.bg, { opacity: 0.30, blend: "screen", zIndex: 0, priority: 10 }); } catch (_e) {}
    return root;
  }

  // ---- CHEST-OPEN viral share hook -------------------------------------
  // After a HIGH-rarity crate reveal lands (Epic or better), offer a
  // shareable clip through the viral share card (viral.js MEDIA.chest).
  // Fully guarded: AK_VIRAL is OPTIONAL (silent no-op when the system is
  // absent) and this NEVER blocks or delays the reveal. Throttled with a
  // simple timestamp so a lucky streak of pulls cannot spam the card.
  var RV_SHARE_GAP_MS = 180000;   // 3 min -- at most one share per few minutes
  var _rvShareAt = 0;
  function rvShareBigPull(rarity) {
    try {
      if (RV_ORDER.indexOf(rarity) < 2) return;            // Epic+ only (skip Common/Rare)
      var now = Date.now();
      if (now - _rvShareAt < RV_SHARE_GAP_MS) return;      // throttle: once per few minutes
      _rvShareAt = now;
      if (window.AK_VIRAL && AK_VIRAL.shareMoment) {
        AK_VIRAL.shareMoment("chest", { title: "LOOT PULLED", sub: "Cracked a " + rarity + " from the vault" });
      }
    } catch (_e) {}
  }

  /* reveal(opts) -- run the variable-ratio crate/reward cinematic. See the
     header block above for the opts contract. Returns { skip } so the caller
     can fast-forward (e.g. a second tap). Reward delivery (onReveal) is
     guaranteed exactly once even on reduced-motion / busy / error paths. */
  AKLoops.reveal = function (opts) {
    opts = opts || {};
    var onReveal = (typeof opts.onReveal === "function") ? opts.onReveal : null;
    var onDone = (typeof opts.onDone === "function") ? opts.onDone : null;
    var rarity = (RV_ORDER.indexOf(opts.rarity) >= 0) ? opts.rarity : "Common";
    var kind = (opts.kind === "reward") ? "reward" : "crate";

    // FAST PATH -- reduced-motion / kill-switch / already running / no DOM:
    // deliver the reward instantly so it is NEVER stranded, no cinematic.
    if (!AKLoops.enabled || reduceMotion() || userDisabled() || RV.busy ||
        typeof document === "undefined" || !document.body) {
      if (onReveal) setTimeout(function () { try { onReveal(); } catch (_e) {} }, 0);
      if (onDone) setTimeout(function () { try { onDone(); } catch (_e) {} }, 0);
      return { skip: function () {} };
    }

    RV.busy = true;
    var fired = false, doned = false;
    function fireReveal() { if (fired) return; fired = true; if (onReveal) { try { onReveal(); } catch (_e) {} } }
    function fireDone() { if (doned) return; doned = true; if (onDone) { try { onDone(); } catch (_e) {} } }

    var rng = rvRng(rvSeed(opts.seed));
    var col = RV_RARITY_COL[rarity] || RV_GOLD;

    rvEnsureRoot();
    rvClearTimers();
    var root = RV.root, stage = RV.stage;
    rvClear(stage);                             // lazy: rebuild stage each run (bg video + skip persist)
    root.style.setProperty("--rv", RV_GOLD);    // crate stays neutral gold until the spike (no spoiler)
    root.classList.remove("on"); root.classList.remove("build");
    root.style.pointerEvents = "";
    root.style.display = "flex";

    var title = opts.title || (kind === "crate" ? (RV_CRATE_LABEL[opts.tier] || "SCRAP CRATE") : "STREET PAYOUT");
    var flav = opts.subtitle || RV_FLAVOR[Math.floor(rng() * RV_FLAVOR.length)];

    var flavEl = rvEl("rv-flav", stage); flavEl.textContent = flav;
    var tick = rvEl("rv-tick", stage); tick.textContent = title; tick.style.setProperty("--rt", RV_GOLD);
    var box = rvEl("rv-box", stage);
    rvEl("rv-ring", box);
    var crate = rvEl("rv-crate", box); rvEl("rv-seam", crate);
    var flash = rvEl("rv-flash", box);
    var land = rvEl("rv-land", stage);
    var sub = rvEl("rv-sub", stage);
    RV.skip.style.display = ""; RV.skip.textContent = "tap to crack";

    try { AKLoops.play("reveal"); } catch (_e) {}
    rvAfter(20, function () { root.classList.add("on"); root.classList.add("build"); });

    // ---- variable-ratio rarity ticker -----------------------------------
    // climbs Common -> ... and (sometimes) teases ONE tier above the real
    // reward, then SNAPS back. Always ends on the TRUE rarity -- cosmetic only.
    var trueIdx = RV_ORDER.indexOf(rarity);
    var overshoot = (trueIdx < 4 && rng() < 0.5) ? 1 : 0;
    var ceil = Math.min(4, trueIdx + overshoot);
    var steps = [];
    for (var i = 0; i <= ceil; i++) steps.push(RV_ORDER[i]);
    if (steps[steps.length - 1] !== rarity) steps.push(rarity);   // snap back / safety: always end true
    var baseGap = 150 + Math.floor(rng() * 90);                   // 150..240ms -> variable suspense
    var si = 0;
    function tickStep() {
      if (si >= steps.length) { rvSpike(); return; }
      var r = steps[si++];
      tick.textContent = r.toUpperCase();
      tick.style.setProperty("--rt", RV_RARITY_COL[r] || RV_GOLD);
      rvAfter(Math.max(70, baseGap - si * 16), tickStep);          // accelerando -> tension
    }
    rvAfter(360, tickStep);                                        // a lead-in beat, then the climb

    // ---- the SPIKE (dopamine hit) ----------------------------------------
    function rvSpike() {
      if (fired) return;
      rvClearTimers();
      root.classList.remove("build");
      root.style.setProperty("--rv", col);     // crate + burst snap to the TRUE rarity color
      tick.style.opacity = "0";
      crate.classList.add("crack");
      flash.classList.add("go");
      var N = 14;                               // capped spark burst (60fps budget)
      for (var s = 0; s < N; s++) {
        var sp = rvEl("rv-spark", box);
        var ang = (s / N) * Math.PI * 2 + rng() * 0.4;
        var dist = 70 + Math.floor(rng() * 46);
        sp.style.setProperty("--tx", (Math.cos(ang) * dist).toFixed(1) + "px");
        sp.style.setProperty("--ty", (Math.sin(ang) * dist).toFixed(1) + "px");
        sp.classList.add("go");
      }
      land.textContent = rarity.toUpperCase();
      land.classList.add("go");
      sub.textContent = (kind === "crate" ? "the haul is yours" : "claimed");
      RV.skip.style.display = "none";
      root.style.pointerEvents = "none";        // taps now reach what onReveal mounts (the card grid)
      fireReveal();                             // caller renders the real cards UNDER the dissolving flash
      rvAfter(820, rvClose);                    // hold the spike, then dissolve
    }

    function rvClose() {
      root.classList.remove("on");              // fade the overlay -> reveals the grid behind
      rvAfter(300, function () {
        root.style.display = "none";
        root.style.pointerEvents = "";
        rvClear(stage);                         // free spark/label nodes (bg video persists in rv-bg)
        try { AKLoops.stop("reveal"); } catch (_e) {}
        RV.busy = false;
        fireDone();
        if (kind === "crate") rvShareBigPull(rarity);   // CHEST-OPEN: offer a shareable clip on big pulls (guarded)
      });
    }

    // master safety -- never let a stalled chain strand the reward.
    rvAfter(4200, function () { if (!fired) rvSpike(); });

    RV._skip = function () { if (!fired) rvSpike(); };
    return { skip: RV._skip };
  };

  /* revealCrate(tier, rarity, onReveal, onDone) -- convenience for the crate UI. */
  AKLoops.revealCrate = function (tier, rarity, onReveal, onDone) {
    return AKLoops.reveal({ kind: "crate", tier: tier, rarity: rarity, onReveal: onReveal, onDone: onDone });
  };

  window.AKLoops = AKLoops;
  window.CinematicLoop = window.CinematicLoop || CinematicLoop;
  // documented thin alias for the shop/crate integration pass.
  window.AKReveal = function (opts) { return AKLoops.reveal(opts); };
})();
