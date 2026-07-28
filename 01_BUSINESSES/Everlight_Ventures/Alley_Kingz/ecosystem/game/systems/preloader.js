/* ==========================================================================
   ALLEY KINGZ // THE PRELOADER  (AK-PRELOAD 2026-07-11)
   A branded, instant, self-contained LOADING SCREEN + an image warm-cache.
   Two jobs:
     1. Paint a gold-cyberpunk noir loading overlay the instant it is asked to
        (pure CSS/inline -- NO external assets in the overlay itself, so it never
        waits on the very art it is loading), and
     2. Preload the mode's CRITICAL art, keep the decoded Images alive in a cache
        (prevents GC + primes the HTTP cache), then quietly warm the rest in the
        background. Videos are NOT preloaded here -- they stream.

   The golden rule: NEVER HANG. Every image settles on load OR error OR an ~8s
   per-image timeout, so a dead CDN url can never freeze the screen. When ALL
   critical images settle, the overlay fades out and opts.onReady fires.

   Design contract:
   - HEADLESS-SAFE: zero load-time DOM, zero top-level document reads. If Image
     is unavailable (node harness) EVERY method degrades to a safe no-op and
     load()/ensure() resolve immediately -- onReady fires right away, never hangs.
   - SELF-CONTAINED OVERLAY: the loading screen is drawn from inline CSS (deep
     black, Everlight gold, a CSS crown, an animated bar) and built with DOM
     nodes (no innerHTML). It borrows NO images; fonts are optional (falls back
     to serif) so first paint is instant.
   - NON-DESTRUCTIVE: it builds its OWN #ak-preload overlay on show(). It does
     NOT touch the hub's existing #loadscreen (menu_bg.mp4) -- the two can coexist.
   - DECODED-CACHE: get(url) hands draw code the decoded Image so a mode can blit
     art it just preloaded with no second network trip.

   Include order: anywhere; it depends on nothing. The wire lanes decide when to
   call load()/ensure().
     <script src="systems/preloader.js"></script>

   Public API on window.AK_PRELOAD:
     load(manifest, opts)  manifest = { critical:[url], warm:[url] }
                           opts = { onReady(res), onProgress(p), timeout?, ui? }
                           -> Promise (resolves after critical settle; onReady too)
     ensure(urls)          -> Promise resolves when those urls are cached (immediate if warm)
     get(url)              -> decoded Image if cached & ok, else null
     progress()            -> { done, total, pct }
     show() / hide()       manual overlay control (guarded no-ops when headless)
     FLAVORS               the rotating dog-street flavor lines
   ========================================================================== */
(function (global) {
  "use strict";

  // ---- brand + tunables ----------------------------------------------------
  var GOLD_HI = "#e8c55a";
  var GOLD_LO = "#c9a84c";
  var GOLD_BRIGHT = "#f0d98a";
  var INK = "#050507";
  var Z = 2147482000;                 // very high; sits above game chrome
  var IMG_TIMEOUT_MS = 8000;          // per-image cap -> settle even if the CDN never answers
  var FADE_MS = 600;                  // overlay fade-out (matches CSS transition below)
  var FLAVOR_MS = 1600;               // rotate the flavor line

  var FLAVORS = [
    "WAKING THE BLOCK...",
    "COUNTING THE CROWNS...",
    "LACING UP THE RUNNERS...",
    "UNCHAINING THE DOGS...",
    "LIGHTING THE ALLEYS...",
    "TIGHTENING THE CREW...",
    "STACKING THE BONES...",
    "MINTING THE STREETS..."
  ];

  // ---- environment guards --------------------------------------------------
  function doc() { try { return global.document || null; } catch (_) { return null; } }
  function hasImage() { try { return typeof global.Image === "function"; } catch (_) { return false; } }
  function PromiseCtor() { try { return global.Promise || (typeof Promise !== "undefined" ? Promise : null); } catch (_) { return null; } }
  function num(v, d) { return (typeof v === "number" && isFinite(v)) ? v : d; }
  function arr(v) { return Object.prototype.toString.call(v) === "[object Array]" ? v.slice() : []; }
  function defer(fn, ms) { try { return setTimeout(fn, num(ms, 0)); } catch (_) { try { fn(); } catch (__) {} return null; } }

  // ---- cache (url -> { url, img, state }) ----------------------------------
  // state: "loading" | "ok" | "fail" | "timeout" | "skip"(headless).
  // Keeping the Image ref alive here prevents the browser from GC-ing the decode
  // and keeps the HTTP cache primed for the real <img>/drawImage that follows.
  var _cache = (function () {
    try { if (typeof Map === "function") return new Map(); } catch (_) {}
    var o = {};
    return {
      get: function (k) { return o[k]; },
      set: function (k, v) { o[k] = v; return this; },
      has: function (k) { return Object.prototype.hasOwnProperty.call(o, k); }
    };
  })();
  var _pending = {};                  // url -> in-flight Promise (dedupe)
  var _prog = { done: 0, total: 0 };

  function progress() {
    var t = _prog.total, d = _prog.done;
    return { done: d, total: t, pct: t > 0 ? Math.max(0, Math.min(100, Math.round(d / t * 100))) : 100 };
  }

  // ---- load a single url; ALWAYS resolves (never rejects) ------------------
  function loadOne(url, timeoutMs) {
    var Pr = PromiseCtor();
    if (!Pr) {                        // no Promise at all -> best-effort, hand back a thenable stub
      var s = _cache.get(url) || { url: url, img: null, state: hasImage() ? "loading" : "skip" };
      _cache.set(url, s);
      return { then: function (cb) { try { cb && cb(s); } catch (_) {} return this; }, "catch": function () { return this; } };
    }
    var ex = _cache.get(url);
    if (ex && ex.state && ex.state !== "loading") return Pr.resolve(ex);   // already settled
    if (_pending[url]) return _pending[url];                                // already in flight
    if (!hasImage()) {                                                      // headless -> skip, resolve now
      var stub = { url: url, img: null, state: "skip" };
      _cache.set(url, stub);
      return Pr.resolve(stub);
    }
    var p = new Pr(function (resolve) {
      var entry = { url: url, img: null, state: "loading" };
      _cache.set(url, entry);
      var settled = false, timer = null;
      function settle(state) {
        if (settled) return; settled = true;
        try { if (timer) clearTimeout(timer); } catch (_) {} timer = null;
        entry.state = state;
        try { delete _pending[url]; } catch (_) {}
        resolve(entry);
      }
      var img;
      try { img = new global.Image(); } catch (_) { settle("fail"); return; }
      entry.img = img;                                       // keep the ref (GC + HTTP-cache prime)
      try { img.onload = function () { settle("ok"); }; } catch (_) {}
      try { img.onerror = function () { settle("fail"); }; } catch (_) {}
      try { timer = setTimeout(function () { settle("timeout"); }, num(timeoutMs, IMG_TIMEOUT_MS)); } catch (_) {}
      try { img.src = url; } catch (_) { settle("fail"); }   // assigning src kicks the fetch
    });
    _pending[url] = p;
    return p;
  }

  // ---- get / ensure --------------------------------------------------------
  function get(url) {
    try { var e = _cache.get(url); return (e && e.img && e.state === "ok") ? e.img : null; }
    catch (_) { return null; }
  }

  // Resolve once every url in the list is cached (loads any missing; immediate
  // for already-warm ones). A mode calls this to gate rendering on its art.
  function ensure(urls) {
    var Pr = PromiseCtor();
    var list = arr(urls);
    if (!Pr) { list.forEach(function (u) { loadOne(u); }); return { then: function (cb) { try { cb && cb([]); } catch (_) {} return this; }, "catch": function () { return this; } }; }
    if (!hasImage() || !list.length) return Pr.resolve([]);
    return Pr.all(list.map(function (u) { return loadOne(u); }));
  }

  // ==========================================================================
  // BRANDED OVERLAY -- gold-cyberpunk noir, pure CSS/inline, built on show()
  // ==========================================================================
  var _el = null, _fill = null, _pct = null, _flav = null, _flavTimer = null, _shown = false, _cssIn = false;

  var CSS =
    "#ak-preload{position:fixed;inset:0;z-index:" + Z + ";display:flex;flex-direction:column;" +
      "align-items:center;justify-content:center;background:" + INK + ";" +
      "background:radial-gradient(120% 90% at 50% 42%,#141017 0%," + INK + " 62%,#020204 100%);" +
      "opacity:1;transition:opacity " + (FADE_MS / 1000) + "s ease;" +
      "font-family:'Cinzel','Playfair Display',Georgia,serif;-webkit-font-smoothing:antialiased;" +
      "-webkit-tap-highlight-color:transparent;color:" + GOLD_HI + ";overflow:hidden;}" +
    "#ak-preload.akpl-hide{opacity:0;pointer-events:none;}" +
    // faint scanline vignette for the cyberpunk noir feel (cheap, no assets)
    "#ak-preload::before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.22;" +
      "background:repeating-linear-gradient(0deg,rgba(232,197,90,.06) 0 1px,transparent 1px 3px);}" +
    "#ak-preload .akpl-stage{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;padding:0 22px;text-align:center;}" +
    // the crown -- a CSS-clipped gold silhouette with a soft glow, no image
    "#ak-preload .akpl-crown{width:76px;height:52px;margin-bottom:14px;" +
      "background:linear-gradient(180deg," + GOLD_BRIGHT + "," + GOLD_LO + " 78%);" +
      "clip-path:polygon(0% 100%,0% 34%,20% 56%,34% 20%,50% 46%,66% 20%,80% 56%,100% 34%,100% 100%);" +
      "-webkit-clip-path:polygon(0% 100%,0% 34%,20% 56%,34% 20%,50% 46%,66% 20%,80% 56%,100% 34%,100% 100%);" +
      "filter:drop-shadow(0 0 12px rgba(232,197,90,.55)) drop-shadow(0 3px 6px rgba(0,0,0,.6));" +
      "animation:akplCrown 2.6s ease-in-out infinite;}" +
    "#ak-preload .akpl-word{font-weight:800;font-size:34px;letter-spacing:.10em;color:" + GOLD_HI + ";" +
      "text-shadow:0 2px 14px rgba(0,0,0,.8),0 0 26px rgba(232,197,90,.35);line-height:1;}" +
    "#ak-preload .akpl-sub{margin-top:6px;font-family:'Inter',system-ui,sans-serif;font-weight:700;" +
      "font-size:10px;letter-spacing:.42em;color:" + GOLD_LO + ";text-transform:uppercase;opacity:.85;}" +
    "#ak-preload .akpl-track{position:relative;margin-top:22px;width:min(64vw,300px);height:6px;border-radius:4px;" +
      "background:rgba(201,168,76,.16);box-shadow:inset 0 0 0 1px rgba(201,168,76,.28);overflow:hidden;}" +
    "#ak-preload .akpl-fill{height:100%;width:0%;border-radius:4px;" +
      "background:linear-gradient(90deg," + GOLD_LO + "," + GOLD_BRIGHT + ");" +
      "box-shadow:0 0 12px rgba(232,197,90,.6);transition:width .45s ease-out;}" +
    "#ak-preload .akpl-meta{margin-top:12px;display:flex;gap:12px;align-items:center;" +
      "font-family:'Inter',system-ui,sans-serif;font-weight:700;font-size:11px;letter-spacing:.06em;}" +
    "#ak-preload .akpl-pct{color:" + GOLD_BRIGHT + ";min-width:34px;text-align:right;}" +
    "#ak-preload .akpl-flav{color:" + GOLD_LO + ";opacity:.85;letter-spacing:.10em;}" +
    "@keyframes akplCrown{0%,100%{transform:translateY(0);filter:drop-shadow(0 0 12px rgba(232,197,90,.5)) drop-shadow(0 3px 6px rgba(0,0,0,.6));}" +
      "50%{transform:translateY(-3px);filter:drop-shadow(0 0 20px rgba(232,197,90,.85)) drop-shadow(0 3px 6px rgba(0,0,0,.6));}}" +
    "@media (prefers-reduced-motion:reduce){#ak-preload .akpl-crown{animation:none;}}";

  function injectCss(d) {
    if (_cssIn) return;
    try {
      var head = d.head || d.getElementsByTagName("head")[0] || d.body;
      if (!head) return;
      var st = d.createElement("style");
      st.id = "ak-preload-css";
      st.type = "text/css";
      st.appendChild(d.createTextNode(CSS));
      head.appendChild(st);
      _cssIn = true;
    } catch (_) {}
  }

  // Build the overlay entirely from DOM nodes + textContent (no innerHTML).
  function mk(d, tag, cls, text) {
    var e = d.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function buildOverlay() {
    var d = doc();
    if (!d || !d.body || typeof d.createElement !== "function") return null;
    injectCss(d);
    var wrap;
    try {
      wrap = mk(d, "div", null, null);
      wrap.id = "ak-preload";
      wrap.setAttribute("role", "progressbar");
      wrap.setAttribute("aria-label", "Loading Alley Kingz");

      var stage = mk(d, "div", "akpl-stage", null);
      stage.appendChild(mk(d, "div", "akpl-crown", null));
      stage.appendChild(mk(d, "div", "akpl-word", "ALLEY KINGZ"));
      stage.appendChild(mk(d, "div", "akpl-sub", "Rule the Block"));

      var track = mk(d, "div", "akpl-track", null);
      track.appendChild(mk(d, "div", "akpl-fill", null));
      stage.appendChild(track);

      var meta = mk(d, "div", "akpl-meta", null);
      meta.appendChild(mk(d, "span", "akpl-pct", "0%"));
      meta.appendChild(mk(d, "span", "akpl-flav", FLAVORS[0]));
      stage.appendChild(meta);

      wrap.appendChild(stage);
      d.body.appendChild(wrap);
    } catch (_) { return null; }
    return wrap;
  }

  function q(el, sel) { try { return el && el.querySelector ? el.querySelector(sel) : null; } catch (_) { return null; } }

  function show() {
    if (_shown) return;
    var el = _el || buildOverlay();
    if (!el) return;                  // headless -> silently no-op
    _el = el;
    _fill = q(el, ".akpl-fill");
    _pct = q(el, ".akpl-pct");
    _flav = q(el, ".akpl-flav");
    try { el.classList.remove("akpl-hide"); } catch (_) {}
    try { el.style.display = "flex"; el.style.opacity = "1"; } catch (_) {}
    _shown = true;
    startFlavor();
  }

  function hide() {
    stopFlavor();
    _shown = false;
    if (!_el) return;
    var el = _el;
    try { el.classList.add("akpl-hide"); } catch (_) {}
    defer(function () { try { if (el && el.style) el.style.display = "none"; } catch (_) {} }, FADE_MS + 60);
  }

  function setBar(done, total) {
    var pct = total > 0 ? Math.max(0, Math.min(100, Math.round(done / total * 100))) : 100;
    try { if (_fill && _fill.style) _fill.style.width = pct + "%"; } catch (_) {}
    try { if (_pct) _pct.textContent = pct + "%"; } catch (_) {}
  }

  function startFlavor() {
    stopFlavor();
    var i = 0;
    setFlav(FLAVORS[0]);
    try {
      _flavTimer = setInterval(function () {
        i = (i + 1) % FLAVORS.length;
        setFlav(FLAVORS[i]);
      }, FLAVOR_MS);
    } catch (_) {}
  }
  function stopFlavor() { try { if (_flavTimer) clearInterval(_flavTimer); } catch (_) {} _flavTimer = null; }
  function setFlav(t) { try { if (_flav) _flav.textContent = t; } catch (_) {} }

  // ==========================================================================
  // LOAD -- preload critical (with the bar), reveal on settle, warm in the bg
  // ==========================================================================
  function load(manifest, opts) {
    opts = opts || {};
    manifest = manifest || {};
    var Pr = PromiseCtor();
    var critical = arr(manifest.critical);
    var warm = arr(manifest.warm);
    var onReady = typeof opts.onReady === "function" ? opts.onReady : null;
    var onProgress = typeof opts.onProgress === "function" ? opts.onProgress : null;
    var timeoutMs = num(opts.timeout, IMG_TIMEOUT_MS);
    var wantUi = opts.ui !== false;                 // overlay shows by default

    function fireReady(res) { if (onReady) { try { onReady(res); } catch (_) {} } }

    // Headless OR no Promise OR no Image -> resolve immediately, NEVER hang.
    if (!Pr || !hasImage()) {
      _prog.total = 0; _prog.done = 0;
      var res0 = { ok: true, headless: true, done: 0, total: 0 };
      fireReady(res0);
      return Pr ? Pr.resolve(res0) : { then: function (cb) { try { cb && cb(res0); } catch (_) {} return this; }, "catch": function () { return this; } };
    }

    if (wantUi) show();
    _prog.total = critical.length;
    _prog.done = 0;
    setBar(0, critical.length);
    if (onProgress) { try { onProgress(progress()); } catch (_) {} }

    function bump() {
      _prog.done++;
      setBar(_prog.done, _prog.total);
      if (onProgress) { try { onProgress(progress()); } catch (_) {} }
    }

    var criticalPromises = critical.map(function (u) {
      return loadOne(u, timeoutMs).then(function (entry) { bump(); return entry; });
    });
    var settleAll = criticalPromises.length ? Pr.all(criticalPromises) : Pr.resolve([]);

    return settleAll.then(function (results) {
      if (wantUi) { setBar(1, 1); hide(); }         // snap to 100% then fade out
      fireReady({ ok: true, results: results, done: _prog.done, total: _prog.total });
      // warm the rest AFTER critical, low priority, no bar. Never blocks onReady.
      if (warm.length) {
        defer(function () { warm.forEach(function (u) { loadOne(u, timeoutMs); }); }, 0);
      }
      return { ok: true, results: results, done: _prog.done, total: _prog.total };
    });
  }

  // ---- export (the ONLY load-time side effect) -----------------------------
  global.AK_PRELOAD = {
    load: load,
    ensure: ensure,
    get: get,
    progress: progress,
    show: show,
    hide: hide,
    FLAVORS: FLAVORS
  };

})(typeof window !== "undefined" ? window : (typeof globalThis !== "undefined" ? globalThis : this));
