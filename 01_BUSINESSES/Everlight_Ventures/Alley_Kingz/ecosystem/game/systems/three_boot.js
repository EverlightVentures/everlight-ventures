/*
 * three_boot.js -- AK-THREE 2026-07-18: the guarded Three.js bootstrapper (window.AK_THREE)
 *
 * Three.js was NOT in this repo. The 3D world, the FPS view and the isometric builder were all
 * blocked on it. assets/vendor/model-viewer.min.js bundles its OWN private copy of three and
 * does NOT expose a THREE global, so nothing outside model-viewer could touch it.
 *
 * Self-hosted, pinned, NO CDN -- the exact model-viewer pattern. A CDN failing silently is what
 * caused the fallback bug that got model-viewer vendored in the first place.
 *   assets/vendor/three.module.min.js   r160.1 ESM build,      655 KB
 *   assets/vendor/OrbitControls.js      r160.1 addon,           30 KB
 *   assets/vendor/GLTFLoader.js         r160.1 addon,          106 KB
 *   assets/vendor/BufferGeometryUtils.js  GLTFLoader's own dep,  31 KB
 *
 * The addons ship from examples/jsm, where every import is the bare specifier 'three'. There is
 * no import map (index.html is owned by another lane), so each bare specifier was rewritten to
 * './three.module.min.js' and GLTFLoader's '../utils/BufferGeometryUtils.js' to './...' for the
 * flat vendor dir. That is the ONLY edit made to the upstream files. Re-pinning a new version
 * means redoing exactly those two rewrites.
 *
 * WHY NO ?v= CACHE-BUSTER ON THE VENDOR URLS (do not "fix" this):
 * OrbitControls.js imports './three.module.min.js' as a bare relative path. A module is keyed in
 * the browser module map BY URL, query string included. Put ?v=r160 on the core here and
 * OrbitControls pulls a SECOND, separate copy: ~1.3 MB down the wire on a phone, two independent
 * class identities, and every instanceof / Vector3 check silently false across the boundary. The
 * files are content-pinned and immutable, so they never need busting. Keep both URLs query-free.
 *
 * Loader contract -- NEVER THROWS, NEVER REJECTS. A missing or broken vendor file resolves to
 * null and ok() stays false, so every 3D consumer can ship BEFORE the asset lands:
 *
 *   AK_THREE.ready()  -> Promise, resolves THREE or null. Loads once, every caller shares the
 *                        one in-flight promise. Safe to await from anywhere, any number of times.
 *   AK_THREE.get()    -> THREE or null, synchronous. null until ready() has resolved.
 *   AK_THREE.ok()     -> bool. true only once three is actually loaded and usable.
 *   AK_THREE.THREE    -> the SAME namespace as a plain property, null until loaded. Kept because
 *                        modes.js threeLib() (systems/modes.js:1006) prefers B.THREE before it
 *                        falls back to B.get(). Mirror of get(), never a second copy.
 *   AK_THREE.addon(n) -> Promise, resolves an addon export or null. 'OrbitControls', 'GLTFLoader'.
 *   AK_THREE.loadGLB(url, onLoad, onErr) -> the optional GLB hook world3d.js buildHero() probes
 *                        (systems/world3d.js:409). onLoad gets the raw gltf object, so callers
 *                        read glb.scene. Never throws; onErr fires if the loader is unavailable.
 *   AK_THREE.budget() -> the live WebGL context budget (see below).
 *
 * Every consumer does: AK_THREE.ready().then(function(T){ if(!T) return draw2D(); ...3D... })
 * and keeps its 2D path alive. Same degrade discipline as hub3d's .active guard and the
 * __ak3d pool returning false past its cap.
 *
 * ---------------------------------------------------------------------------------------------
 * WEBGL CONTEXT BUDGET -- the device target is a PHONE. READ THIS BEFORE NEW A WebGLRenderer.
 *
 * A WebGL context is not free and it is not garbage collected on a timer. Mobile browsers start
 * SILENTLY DROPPING the oldest live context somewhere around 8, and GPU memory is the real wall
 * well before that count (hub3d's own note: bcardd 13 MB, jagged 19 MB per GLB).
 *
 * What is already spending the budget on the hub screen:
 *   1  model-viewer  hero, pinned          (hub3d.js, window.__hero3d)
 *   4  model-viewer  pooled allies         (hub3d.js UNIT_CAP = 4, window.__ak3d)
 *   -- 5 live contexts at full pool, deliberately leaving headroom.
 * Not contexts but still GPU memory, so they count against the same wall:
 *   8  pooled <video> elements             (cardfx.js POOL_MAX = 8)
 *   2  transient video overlays            (cardfx.js OVERLAY_MAX = 2)
 *   1  the hub's own Canvas2D
 *
 * CEILING FOR THREE: ONE WebGLRenderer for the entire game. Not one per mode. The 3D world, the
 * FPS view and the isometric builder are MUTUALLY EXCLUSIVE modes (real-life logic law: every
 * mode exits to the district map), so they must hand the same renderer around and swap
 * scene + camera, never each construct their own. 5 model-viewer contexts + 1 three renderer
 * = 6, which is inside the ~8 wall with room for a transient. Two three renderers plus a full
 * ally pool is 7 and starts evicting the hero mid-raid.
 *
 * HOW TO COEXIST WITH MODEL-VIEWER:
 *   - three_boot deliberately owns NO renderer and creates NO canvas. It is a loader only, so it
 *     costs 0 contexts until a consumer builds one. Loading three is always safe.
 *   - THE SHARED RENDERER LIVES AT window.AK_R3D. world3d.js already publishes and reuses that
 *     global, so every other lane reads it before constructing anything: if AK_R3D is there, use
 *     it. Whichever lane boots first owns creation, nobody builds a second, and the owner is the
 *     only one that may dispose() it.
 *   - On entering a full-3D mode, drop the model-viewer ally pool first: window.__ak3d.on = false
 *     plus its clear path frees up to 4 contexts. Restore on exit to the district map.
 *   - The hero model-viewer can stay live (1 context) alongside the three renderer.
 *   - Always set renderer.setPixelRatio(Math.min(devicePixelRatio, 2)). A phone at DPR 3 renders
 *     2.25x the pixels for no visible gain and is the fastest way to thermal-throttle the device.
 *   - On teardown call renderer.dispose() and drop the reference. Losing the reference without
 *     dispose() leaks the context until the browser evicts it, which shows up as the hero
 *     randomly going black much later and reads as an unrelated bug.
 *
 * budget() reports this live so lanes read one source of truth instead of hardcoding 5.
 * ---------------------------------------------------------------------------------------------
 *
 * Plain JS, headless-safe (node --check clean, requireable in node -- ok() returns false), zero
 * load-time DOM or global access. Builds no DOM at all, ever. NO em-dashes (hook law, use --).
 */
(function () {
  'use strict';

  // Document-base relative, exactly like index.html's model-viewer tag. Both query-free (see above).
  var SRC_CORE = 'assets/vendor/three.module.min.js';
  var PIN = 'r160.1';

  // Addon FILENAMES only. They resolve against whatever dir the core came from, so overriding
  // the core path moves the addons with it instead of leaving them pointed at the old dir.
  // GLTFLoader pulls ./BufferGeometryUtils.js itself, out of that same dir.
  var ADDONS = { OrbitControls: 'OrbitControls.js', GLTFLoader: 'GLTFLoader.js' };

  var THREE = null;      // the resolved namespace, null until loaded
  var coreP = null;      // the ONE in-flight core load, shared by every caller
  var addonP = {};       // one in-flight promise per addon name

  // The only environment probe. Guarded so require() in node is inert and cannot throw.
  function live() {
    return typeof window !== 'undefined' && typeof document !== 'undefined';
  }

  // Consumers may override the vendor path before first ready() (tests, a moved asset dir).
  //
  // AK-SPECIFIER-FIX 2026-07-19: THE BUG THAT KEPT 3D DEAD. SRC_CORE was returned raw as
  // 'assets/vendor/three.module.min.js', with no leading './'. A specifier that does not start with
  // '/', './' or '../' is a BARE specifier, and bare specifiers are NOT resolved against the
  // document base -- they require an import map, and this page has none. So dynamic import() threw
  // "Failed to resolve module specifier" every time, the catch below resolved null, coreP memoized
  // that null forever, and AK_THREE.ok() returned false for the life of the page. Silently: the
  // rejection is swallowed by design, so there was never a console error, and the browser never
  // even REQUESTED the vendor file. Measured in-page:
  //     import('assets/vendor/three.module.min.js')   -> TypeError, no network request
  //     import('./assets/vendor/three.module.min.js') -> ok, 416 exports, REVISION 160
  // Resolving to an ABSOLUTE url against document.baseURI fixes it and is immune to base drift
  // (a plain './' prefix 404'd in one probe run, which is why this does not just prepend './').
  function coreUrl() {
    var raw = (live() && window.AK_THREE_SRC) || SRC_CORE;
    try {
      var base = (typeof document !== 'undefined' && document.baseURI) ||
                 (typeof location !== 'undefined' && location.href) || '';
      return base ? new URL(raw, base).href : raw;
    } catch (_e) { return raw; }
  }

  // The dir the core loaded from, trailing slash kept. Addons ride along with it.
  function addonUrl(name) {
    var u = coreUrl(), i = u.lastIndexOf('/');
    return (i === -1 ? '' : u.slice(0, i + 1)) + ADDONS[name];
  }

  // Load the vendor ESM once. Resolves THREE or null, never rejects, never throws.
  // import() from a classic script resolves against the DOCUMENT base url, which is game/,
  // so these paths line up with index.html's own relative script srcs.
  function loadCore() {
    if (coreP) return coreP;
    coreP = new Promise(function (res) {
      if (!live()) return res(null);            // node / worker: no DOM, stay null and quiet
      var p;
      try { p = import(coreUrl()); }            // a parser without dynamic import lands here
      catch (e) { return res(null); }
      if (!p || typeof p.then !== 'function') return res(null);
      p.then(function (ns) {
        if (!ns || !ns.WebGLRenderer) return res(null);   // wrong file / partial fetch
        THREE = ns;
        API.THREE = ns;                         // plain-property mirror, see the API block above

        // Publish the global some three code and every tutorial expects, but never clobber an
        // existing one. model-viewer keeps its own private copy and is untouched by this.
        try { if (!window.THREE) window.THREE = ns; } catch (e) {}
        res(ns);
      }, function () { res(null); });           // 404, MIME reject, parse error -- all degrade
    });
    return coreP;
  }

  // Addons import three themselves via a relative path, so the core must be up first or the
  // browser would fetch a second copy on its own terms.
  function loadAddon(name) {
    if (addonP[name]) return addonP[name];
    addonP[name] = loadCore().then(function (T) {
      if (!T || !ADDONS[name] || !live()) return null;
      var p;
      try { p = import(addonUrl(name)); }
      catch (e) { return null; }
      if (!p || typeof p.then !== 'function') return null;
      return p.then(function (ns) { return (ns && ns[name]) || null; }, function () { return null; });
    });
    return addonP[name];
  }

  var API = {
    pin: PIN,
    THREE: null,                                // set on load, mirror of get()
    ready: function () { return loadCore(); },
    get: function () { return THREE; },
    ok: function () { return !!THREE; },
    addon: function (name) { return loadAddon(String(name || '')); },

    // GLB hook. onLoad receives the raw gltf, so callers read glb.scene (world3d.js:412 already
    // does `glb && (glb.scene || glb)`). Swallows every failure into onErr, never throws.
    loadGLB: function (url, onLoad, onErr) {
      function fail(e) { try { if (typeof onErr === 'function') onErr(e || null); } catch (_e) {} }
      loadAddon('GLTFLoader').then(function (GL) {
        if (!GL) return fail(null);             // vendor file missing -> caller keeps its 2D path
        try {
          new GL().load(String(url || ''),
            function (g) { try { if (typeof onLoad === 'function') onLoad(g); } catch (_e) {} },
            null,
            fail);
        } catch (e) { fail(e); }
      }, fail);
    },

    // Live context accounting. Reads hub3d's real pool when it exists rather than restating
    // constants that could drift. See the budget block above for what the numbers mean.
    budget: function () {
      var pool = (live() && window.__ak3d) || null;
      var heroOn = !!(live() && window.__hero3d);
      var allyCap = (pool && pool.cap) || 0;
      var allyOn = !!(pool && pool.on);
      return {
        ceiling: 8,                                        // mobile starts evicting around here
        modelViewer: (heroOn ? 1 : 0) + (allyOn ? allyCap : 0),
        threeRenderers: 1,                                 // the hard cap. ONE, shared by all modes.
        heroLive: heroOn,
        allyPoolOn: allyOn,
        allyCap: allyCap
      };
    }
  };

  if (live()) window.AK_THREE = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})();
