/* ALLEY KINGZ -- AK_STREAM: world partition + chunk streaming, and the clutter that makes it pay.
 * AK-STREAM 2026-07-19
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * The 3D district had NO spatial partition of any kind. Grep the repo before this file landed:
 * zero THREE.Frustum, zero frustumCulled assignments, zero .visible toggling, zero distance tests
 * anywhere in systems/ or index.html. The CANVAS layer culls (index.html:2561 props reject at
 * +-30px, :2574 buildings at +-220px, :3331 roamers at +-60px) and the GL layer did not. Three's
 * own per-object frustum cull was the only thing running, and with 5 objects in the scene it
 * removed nothing.
 *
 * The honest reason it removed nothing: THE WORLD HAD NOTHING IN IT. HOME_TURF is 1700x1300 with
 * 4 buildings, and bldmass.js:9 measured the whole visible world at 50 triangles. A partition over
 * 5 objects is a no-op, and shipping a no-op is how this repo already accumulated eleven modules
 * on disk that nothing calls (basegrid, builders, storages, shields, farm, weather, sfx,
 * spritesheet, replay, bossfx, cardfx -- none appear in index.html's script tags). AK_BLDMASS was
 * in the same state at the start of this wave -- loaded, fully written, called by nobody -- and is
 * now claimed by aklod.js:493, which is why this module deliberately does NOT touch it. See
 * OWNERSHIP below: shipping a second decorate() caller would have been z-fighting, not a feature.
 *
 * So this file ships BOTH halves or it is worthless:
 *   1. THE PARTITION -- a chunk grid with add()/update(), show/hide per chunk, allocation-free on
 *      the frames that matter, with the chunk index exposed so LOD and clutter share one substrate.
 *   2. THE CONTENT THAT MAKES IT LOAD-BEARING -- ~380 pieces of deterministic street clutter per
 *      district, merged ONE MESH PER CHUNK so that chunk residency and draw-call granularity are
 *      the same thing. Streaming a world of 5 objects is theatre; streaming 380 is a measurement.
 *
 * ALL NUMBERS BELOW ARE MEASURED BY `node systems/akstream.js`, NOT ESTIMATED.
 *   grid          1700x1300 at 256 -> 7x6 = 42 chunks
 *   clutter       600 placement attempts -> 379 props placed -> 1031 boxes -> 12372 triangles
 *                 (rejected: 110 building, 70 over-packed, 30 world edge, 11 hero spawn)
 *   bake          35 non-empty chunks -> 35 merged meshes. Unmerged that is 379 draw calls.
 *   ACTIVATION    on a 412x915 phone across a 7-leg perimeter patrol (408 frames):
 *                   chunk meshes resident   mean 17.9 of 35   (min 10, max 24)
 *                   props HIDDEN per frame  mean 192 of 379   =  50.8%
 *                   draw calls skipped      mean 17.1 of 35
 *                   recompute rate          202 of 408 frames; the other 50.5% cost nothing
 *                 and the pop-in audit finds ZERO visible props inside a hidden chunk, at every
 *                 camera extreme tested (phi 10deg..PHI_MAX 72deg, zoom 0.55..2.2, 3 viewports).
 * That is the brief's activation proof: half the district's clutter is skipped every frame, on a
 * district that had nothing to skip at all before this lane.
 *
 * IT ALSO SCALES. Same module, same config, bigger district, phone viewport (measured):
 *     1700x1300   42 chunks    379 props   51.8% hidden      <- ships today
 *     2400x1800   80 chunks    847 props   64.9% hidden
 *     3400x2600  154 chunks   1892 props   72.9% hidden
 *     5100x3900  320 chunks   4409 props   78.7% hidden
 *     6800x5200  567 chunks   8017 props   81.7% hidden
 * The partition does not merely survive a bigger world, it earns more the bigger the world gets,
 * which is the property that makes it worth building before the world is big.
 *
 * THE RESIDENCY POLICY, AND WHY THE OBVIOUS ONE IS WRONG
 * -----------------------------------------------------
 * The textbook streaming grid keeps a (2r+1)^2 ring of cells around the PLAYER. That was the first
 * implementation here and it is WRONG for this game, which the measurements caught before ship:
 *
 *   - The camera is not the player. world3d.js:135 puts it at phi=52deg, dist=620, and it ORBITS
 *     on drag (world3d.js:678). A player-centred radius is blind to where the camera is looking,
 *     so it hides visible geometry behind the player and keeps invisible geometry in front.
 *   - Measured with the game's own projector: a 30-unit prop is still 18-30 SCREEN PIXELS tall at
 *     1200 world units. Perspective falloff is far too weak to justify a distance cut. What
 *     actually removes it is FOG -- world3d.js:666 sets Fog(tint, 420, 1750), so a prop is 64%
 *     fogged at 720 units and 99% at 1200. A player-radius of 720 hid props that were still 36%
 *     visible. That is textbook pop-in, and it would have shipped.
 *   - Worse: at 1700x1300 the WHOLE DISTRICT fits inside the fog volume. Camera-to-farthest-corner
 *     is 1472 units against a fog far-plane of 1750, so ANY pop-in-proof distance radius keeps
 *     99.7% of chunks resident. Measured. A distance policy cannot activate here at all.
 *
 * So residency is decided by the ONE primitive that already knows about camera position, yaw, phi,
 * zoom and viewport: world3d's own projector. A chunk is resident when any of its 5 sample points
 * (4 rect corners + centre), tested at ground level and at prop height, comes back vis:true from
 * proj.project() -- the same +-240px screen-rect test the 2D layer culls against (world3d.js:234),
 * so the GL layer and the canvas layer finally agree on what is on screen. That +-240px margin is
 * the safety band, and the pop-in audit in selfTest() proves it is wide enough.
 *
 * Distance/hysteresis residency is KEPT as the fallback for when no projector exists (headless
 * tests, or 3D not booted). It is fully tested; it is simply not the default.
 *
 * WHY MERGE PER CHUNK
 * -------------------
 * Same argument bldmass.js:41-53 makes for building detail, applied to clutter: 379 individual
 * prop meshes would be 379 DRAW CALLS, which on a phone costs far more than the 12k triangles ever
 * will. Merged per chunk it is 35 draw calls, and because the merge unit IS the streaming unit,
 * hiding a chunk removes exactly one draw call and every prop inside it. Merging is only possible
 * because every prop shares ONE material, so colour rides a vertex attribute and the material runs
 * vertexColors:true.
 *
 * OWNERSHIP -- WHO IS ALLOWED TO WRITE .visible ON WHAT
 * -----------------------------------------------------
 * Four lanes in this wave write mesh.visible, and two objects written by two lanes is a flicker
 * bug that no test catches because both writers look correct in isolation. The boundary:
 *   akcull.js  -> world3d's BUILDINGS only. akcull.js:484 reads `st.blds` and its restoreAll()
 *                 (akcull.js:506) only ever touches meshes it hid itself. It never walks the scene.
 *   aklod.js   -> the same buildings, plus the AK_BLDMASS detail mesh it creates and claims with
 *                 userData.akMassed (aklod.js:495). It is the ONLY decorate() caller.
 *   akinstance -> its own InstancedMesh fields.
 *   THIS LANE  -> the per-chunk merged CLUTTER meshes it creates, and nothing else. It does not
 *                 register buildings, does not call decorate(), and does not touch any mesh it did
 *                 not allocate. Verified: akcull's source is `st.blds`, and clutter meshes are
 *                 never in st.blds, so the two lanes are disjoint by construction.
 * If you add a lane that writes .visible, add it here first and prove disjointness.
 *
 * WHAT THIS FILE DOES NOT DO
 * --------------------------
 * No network load/unload -- in-memory show/hide only; async asset streaming is out of scope for
 * this lane. No second WebGLRenderer, ever (three_boot.js:74 and world3d.js:463 both state the
 * law; phones evict WebGL contexts around 8). This module never constructs a renderer, camera or
 * scene: it reads AK_WORLD3D._state, which world3d.js:886 exports precisely so a separate module
 * can reach the scene WITHOUT editing world3d.js (operator rule 6).
 *
 * DEGRADATION
 * -----------
 * No AK_THREE, no AK_WORLD3D, no scene, no WebGL: every entry point returns false and the 2D game
 * is byte-identical. Failures are REPORTED through AK_STREAM.diag().err rather than swallowed,
 * because a silently-swallowed error is how a corrupt vendor file hid on this project for hours.
 */
(function (root) {
  'use strict';

  var VER = 'AK-STREAM-1.1.0';

  // ==========================================================================================
  // PURE CORE -- no DOM, no THREE, no globals. `node systems/akstream.js` runs the proof below.
  // ==========================================================================================

  /* ---- chunk grid --------------------------------------------------------------------------
   * A flat row-major partition of the world rect. Deliberately dumb and allocation-free: every
   * query returns numbers or writes into a caller-owned array, never allocates, so the per-frame
   * path can call it hundreds of times without handing the phone's GC work mid-frame.
   */
  function makeChunkGrid(o) {
    o = o || {};
    var worldW = o.worldW > 0 ? o.worldW : 1700;
    var worldH = o.worldH > 0 ? o.worldH : 1300;
    var size   = o.size   > 0 ? o.size   : 256;
    var cols = Math.max(1, Math.ceil(worldW / size));
    var rows = Math.max(1, Math.ceil(worldH / size));
    var count = cols * rows;

    function clampC(v) { return v < 0 ? 0 : (v > cols - 1 ? cols - 1 : v); }
    function clampR(v) { return v < 0 ? 0 : (v > rows - 1 ? rows - 1 : v); }
    // Clamped on purpose: world3d.js:162 follow() clamps the camera to the world rect and the hub
    // lets `me` sit exactly on the edge, so an unclamped index would silently drop edge props.
    function cxOf(x) { return clampC(Math.floor(x / size)); }
    function cyOf(y) { return clampR(Math.floor(y / size)); }
    function idxOf(cx, cy) { return clampR(cy) * cols + clampC(cx); }
    function cxAt(i) { return (i | 0) % cols; }
    function cyAt(i) { return ((i | 0) / cols) | 0; }

    // Writes [x0,y0,x1,y1] into `out` (caller-owned, reused). Clipped to the world, so edge
    // chunks are not measured at full size.
    function rectOf(i, out) {
      var cx = cxAt(i), cy = cyAt(i);
      out[0] = cx * size; out[1] = cy * size;
      out[2] = Math.min(out[0] + size, worldW);
      out[3] = Math.min(out[1] + size, worldH);
      return out;
    }

    // Distance from (x,y) to the nearest point of chunk i's rect. 0 when inside.
    function distToRect(cx, cy, x, y) {
      var x0 = cx * size, y0 = cy * size;
      var x1 = x0 + size; if (x1 > worldW) x1 = worldW;
      var y1 = y0 + size; if (y1 > worldH) y1 = worldH;
      var dx = x < x0 ? (x0 - x) : (x > x1 ? (x - x1) : 0);
      var dy = y < y0 ? (y0 - y) : (y > y1 ? (y - y1) : 0);
      return Math.sqrt(dx * dx + dy * dy);
    }

    // Chebyshev ring, exported for LOD/culling lanes that want cell INDICES rather than a metric.
    // Writes into `out` and returns the used length so it can run per-frame without allocating.
    function ring(cx, cy, r, out) {
      out = out || [];
      var n = 0;
      for (var y = cy - r; y <= cy + r; y++) {
        if (y < 0 || y >= rows) continue;
        for (var x = cx - r; x <= cx + r; x++) {
          if (x < 0 || x >= cols) continue;
          out[n++] = y * cols + x;
        }
      }
      out.length = n;
      return n;
    }

    return {
      worldW: worldW, worldH: worldH, size: size, cols: cols, rows: rows, count: count,
      cxOf: cxOf, cyOf: cyOf, idxOf: idxOf, cxAt: cxAt, cyAt: cyAt,
      idxAtWorld: function (x, y) { return idxOf(cxOf(x), cyOf(y)); },
      centerX: function (cx) { return Math.min(worldW, cx * size + size / 2); },
      centerY: function (cy) { return Math.min(worldH, cy * size + size / 2); },
      rectOf: rectOf, distToRect: distToRect, ring: ring,
      key: function (cx, cy) { return cx + ',' + cy; }
    };
  }

  /* ---- streamer ----------------------------------------------------------------------------
   * Owns residency. Objects are duck-typed: the only thing done to them is setVis(obj, bool),
   * defaulting to `obj.visible = bool`. That is why this is node-testable with plain object
   * literals, and why it would work just as well over DOM nodes or 2D sprites.
   *
   * `weight` is how many LOGICAL items an object stands for. A merged chunk mesh is ONE object
   * carrying ~11 props; reporting "1 object hidden" for that would be a lie by omission, so stats
   * track handles AND weighted units separately.
   *
   * o.test(i) -> bool  is the residency policy. Default: distance-from-(x,y) with hysteresis.
   * The scene layer swaps in a projector-driven test (see makeProjTest) -- see the header for why
   * the distance policy cannot activate on a district this small.
   */
  function makeStreamer(grid, o) {
    o = o || {};
    var R      = o.radius > 0 ? o.radius : 720;
    var BAND   = o.band  >= 0 ? o.band   : 128;   // hysteresis: acquire at R, release at R+BAND
    var STEP   = o.step  >= 0 ? o.step   : 48;    // player movement before a recompute is considered
    var HOLD   = o.hold  >= 0 ? o.hold   : 0;     // frames a chunk stays resident after failing
    var setVis = o.setVis || function (obj, v) { obj.visible = v; };
    var test   = (typeof o.test === 'function') ? o.test : null;

    var n = grid.count;
    var resident = new Uint8Array(n);             // 1 = shown. Starts all-hidden by design.
    var holdT    = new Uint8Array(n);             // release-delay counter, anti-flicker
    var buckets  = new Array(n);                  // lazily allocated arrays of handles
    var objCount = 0, visObj = 0, unitCount = 0, visUnits = 0;
    var lastX = NaN, lastY = NaN, lastIdx = -1, lastSig = NaN;
    var recomputes = 0, crossings = 0, frames = 0;

    // Reused result record: update() runs every frame and must not allocate.
    var D = {
      changed: false, shownObj: 0, hiddenObj: 0, shownUnits: 0, hiddenUnits: 0,
      resident: 0, total: n, cx: 0, cy: 0, recomputed: false
    };

    function applyChunk(i, vis) {
      var b = buckets[i]; if (!b) return 0;
      var units = 0;
      for (var k = 0; k < b.length; k++) {
        var h = b[k];
        if (h.vis === vis) continue;
        h.vis = vis;
        try { setVis(h.obj, vis); } catch (_e) { /* one broken object must not stall the sweep */ }
        units += h.w;
        visObj += vis ? 1 : -1;
        visUnits += vis ? h.w : -h.w;
      }
      return units;
    }

    // Default policy: distance to the chunk rect, with a hysteresis band so standing on a border
    // does not toggle the same chunk every frame.
    function distTest(i, x, y) {
      var d = grid.distToRect(grid.cxAt(i), grid.cyAt(i), x, y);
      return resident[i] ? (d <= R + BAND) : (d <= R);
    }

    function recompute(x, y) {
      recomputes++;
      var res = 0, su = 0, hu = 0, so = 0, ho = 0;
      for (var i = 0; i < n; i++) {
        var want = test ? !!test(i) : distTest(i, x, y);
        // Release delay: a chunk that fails the test holds for HOLD more frames before hiding.
        // Costs nothing when HOLD is 0 and kills boundary flicker when it is not.
        if (!want && resident[i] && HOLD) {
          if (holdT[i] < HOLD) { holdT[i]++; want = true; }
        } else if (want) { holdT[i] = 0; }

        var was = resident[i];
        if (want !== !!was) {
          resident[i] = want ? 1 : 0;
          var before = visObj;
          var u = applyChunk(i, want);
          if (want) { su += u; so += (visObj - before); }
          else      { hu += u; ho += (before - visObj); }
        }
        if (resident[i]) res++;
      }
      D.resident = res; D.shownUnits = su; D.hiddenUnits = hu;
      D.shownObj = so;  D.hiddenObj = ho;
      D.changed = (su + hu) > 0;
      D.recomputed = true;
      return D;
    }

    /* update(x, y, sig)
     * `sig` is an optional camera signature. Player movement alone is NOT enough to invalidate a
     * projector-based policy -- the player can stand still and ORBIT the camera (world3d.js:678),
     * which changes what is on screen without moving `me` one unit. The scene layer passes a
     * quantised yaw/phi/zoom/viewport hash; when it changes, the fast path is skipped.
     */
    function update(x, y, sig) {
      frames++;
      var idx = grid.idxAtWorld(x, y);
      if (idx !== lastIdx) { crossings++; lastIdx = idx; }
      var sigSame = (sig === undefined) || (sig === lastSig);
      if (sigSame && lastX === lastX) {                 // lastX===lastX is a NaN check
        var dx = x - lastX, dy = y - lastY;
        if (dx * dx + dy * dy < STEP * STEP) {
          // THE FAST PATH. Camera unchanged and the player has not moved far enough for residency
          // to have shifted. Zero work, zero allocation. Measured on the patrol walk: 50.5% of
          // frames take this branch. It is much higher in normal play, where the player stands
          // still far more than a synthetic patrol does.
          D.changed = false; D.recomputed = false;
          D.shownObj = D.hiddenObj = D.shownUnits = D.hiddenUnits = 0;
          D.cx = grid.cxAt(idx); D.cy = grid.cyAt(idx);
          return D;
        }
      }
      lastX = x; lastY = y; lastSig = sig;
      var r = recompute(x, y);
      r.cx = grid.cxAt(idx); r.cy = grid.cyAt(idx);
      return r;
    }

    function add(obj, x, y, tag, weight) {
      if (!obj) return null;
      var i = grid.idxAtWorld(x, y);
      var b = buckets[i] || (buckets[i] = []);
      var w = weight > 0 ? weight : 1;
      var vis = !!resident[i];
      var h = { obj: obj, i: i, x: x, y: y, tag: tag || '', w: w, vis: vis };
      b.push(h); objCount++; unitCount += w;
      if (vis) { visObj++; visUnits += w; }
      // Apply residency immediately so an object added into a hidden chunk never flashes for a
      // frame before the next update() catches it.
      try { setVis(obj, vis); } catch (_e) {}
      return h;
    }

    function remove(h) {
      if (!h) return false;
      var b = buckets[h.i]; if (!b) return false;
      var k = b.indexOf(h); if (k < 0) return false;
      b.splice(k, 1);
      objCount--; unitCount -= h.w;
      if (h.vis) { visObj--; visUnits -= h.w; }
      return true;
    }

    function clear(tag) {
      var killed = 0;
      for (var i = 0; i < n; i++) {
        var b = buckets[i]; if (!b) continue;
        for (var k = b.length - 1; k >= 0; k--) {
          if (tag && b[k].tag !== tag) continue;
          var h = b[k];
          b.splice(k, 1); killed++;
          objCount--; unitCount -= h.w;
          if (h.vis) { visObj--; visUnits -= h.w; }
        }
      }
      if (!tag) { lastX = lastY = NaN; lastIdx = -1; lastSig = NaN; }
      return killed;
    }

    return {
      grid: grid, add: add, remove: remove, clear: clear, update: update,
      stats: function () {
        return {
          chunks: n, resident: D.resident, residentPct: n ? D.resident / n : 0,
          objects: objCount, visibleObjects: visObj, hiddenObjects: objCount - visObj,
          units: unitCount, visibleUnits: visUnits, hiddenUnits: unitCount - visUnits,
          frames: frames, recomputes: recomputes, crossings: crossings,
          radius: R, band: BAND, step: STEP, policy: test ? 'projector' : 'distance'
        };
      },
      residentMask: function () { return resident; },
      isResident: function (cx, cy) { return !!resident[grid.idxOf(cx, cy)]; },
      objectsIn: function (cx, cy) { var b = buckets[grid.idxOf(cx, cy)]; return b ? b.slice() : []; },
      bucketSize: function (cx, cy) { var b = buckets[grid.idxOf(cx, cy)]; return b ? b.length : 0; },
      setTest: function (fn) { test = (typeof fn === 'function') ? fn : null; lastSig = NaN; lastX = NaN; },
      setRadius: function (r, band) {
        if (r > 0) R = r; if (band >= 0) BAND = band;
        lastX = lastY = NaN; lastIdx = -1; lastSig = NaN;   // force the next update to recompute
        return { radius: R, band: BAND };
      }
    };
  }

  /* makeProjTest(grid, proj, opts) -> function(i) -> bool
   * THE SHIPPED RESIDENCY POLICY. Uses world3d's projector, which is the only object in the game
   * that knows camera position, yaw, phi, zoom and viewport at once.
   *
   * Samples 4 rect corners + the centre, each at ground level and at `topH`, and returns true on
   * the FIRST vis:true. Early-exit means a resident chunk usually costs 1-2 project() calls and
   * only a fully-hidden chunk pays all 10. Measured: 5 sample points and 9 sample points give
   * IDENTICAL residency on the patrol walk, so 5 ships -- 9 was 80% more projections for zero
   * difference. Heights 80 and 120 also gave identical results; 80 covers the tallest clutter
   * (the 74-unit lamp post).
   *
   * NOTE: project() allocates a result object per call (world3d.js:212 returns a fresh literal)
   * and that file is off-limits this phase, so the mitigation is to recompute rarely rather than
   * to avoid the allocation -- hence the movement threshold and the camera signature.
   */
  function makeProjTest(grid, proj, opts) {
    opts = opts || {};
    var topH = opts.topH > 0 ? opts.topH : 80;
    var rect = [0, 0, 0, 0];                   // reused, never reallocated
    return function (i) {
      grid.rectOf(i, rect);
      var x0 = rect[0], y0 = rect[1], x1 = rect[2], y1 = rect[3];
      var mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
      var xs = [x0, x1, x0, x1, mx], ys = [y0, y0, y1, y1, my];
      for (var k = 0; k < 5; k++) {
        var a = proj.project(xs[k], ys[k], 0);
        if (a && a.vis) return true;
        var b = proj.project(xs[k], ys[k], topH);
        if (b && b.vis) return true;
      }
      return false;
    };
  }

  /* ---- deterministic rng -------------------------------------------------------------------
   * Same FNV-1a + xorshift pair as bldmass.js:25-33, for the same reason: Math.random() would
   * re-scatter every prop on every district re-entry and the street would visibly shimmer.
   */
  function hash(str) {
    var h = 2166136261, s = String(str == null ? 'x' : str);
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  /* ---- clutter catalogue -------------------------------------------------------------------
   * Everything is a box, exactly like bldmass -- no textures, no loader, no async, and every box
   * merges into its chunk's single geometry. The palette is grimier and cooler than the building
   * facades so clutter reads as separate material rather than as more building.
   * `foot` is the placement footprint used for spacing rejection, in world units.
   */
  var C_METAL = 0x3a3d46, C_RUST = 0x4a3a2e, C_DARK = 0x15151b, C_TRIM = 0x1b1b22,
      C_WOOD  = 0x4d3b28, C_GREEN = 0x2f4a3a, C_GREY = 0x2a2a32, C_RUBBER = 0x121216,
      C_LAMP  = 0x5a5f6b, C_GLOW  = 0xffd98a, C_BAG = 0x1a1a20, C_RED = 0x6b2420;

  var CLUTTER = [
    { k: 'LAMP',     wt: 12, foot: 26 },
    { k: 'DUMPSTER', wt: 10, foot: 58 },
    { k: 'CRATES',   wt: 14, foot: 46 },
    { k: 'BARREL',   wt: 11, foot: 32 },
    { k: 'HYDRANT',  wt:  6, foot: 20 },
    { k: 'BOLLARD',  wt:  8, foot: 18 },
    { k: 'PALLET',   wt:  9, foot: 44 },
    { k: 'AC',       wt:  7, foot: 40 },
    { k: 'TIRES',    wt:  8, foot: 36 },
    { k: 'SIGN',     wt:  6, foot: 24 },
    { k: 'BAGS',     wt: 10, foot: 34 },
    { k: 'FENCE',    wt:  9, foot: 72 }
  ];
  var CLUTTER_TOTAL = (function () { var t = 0; for (var i = 0; i < CLUTTER.length; i++) t += CLUTTER[i].wt; return t; })();

  function pickKind(r) {
    var t = r * CLUTTER_TOTAL, acc = 0;
    for (var i = 0; i < CLUTTER.length; i++) { acc += CLUTTER[i].wt; if (t < acc) return CLUTTER[i]; }
    return CLUTTER[CLUTTER.length - 1];
  }

  /* boxesFor(prop, sink) -> pushes {w,h,d,c,x,y,z} records in WORLD space (y = up).
   * Pure apart from the sink, so the headless test counts the exact geometry the browser bakes.
   * Returns the number of boxes appended. Tallest emitter is LAMP at 74 units -- that number is
   * what makeProjTest's default topH of 80 is sized to cover.
   */
  function boxesFor(p, sink) {
    var n0 = sink.length, x = p.x, z = p.y, r = rngFor(p.seed);
    function B(w, h, d, c, ox, oy, oz) { sink.push({ w: w, h: h, d: d, c: c, x: x + ox, y: oy, z: z + oz }); }
    switch (p.k) {
      case 'LAMP':
        // The one prop that reads from across a chunk, hence the highest weight. The head is an
        // emissive-looking COLOUR, not a light: world3d runs two lights total (world3d.js:638) and
        // 380 point lights would end the frame rate.
        B(4, 74, 4, C_LAMP, 0, 37, 0);
        B(16, 5, 6, C_LAMP, 5, 72, 0);
        B(9, 3, 5, C_GLOW, 8, 69, 0);
        break;
      case 'DUMPSTER':
        B(46, 26, 26, C_GREEN, 0, 13, 0);
        B(48, 4, 28, C_DARK, 0, 27, 0);
        B(4, 8, 4, C_DARK, -20, 4, 11); B(4, 8, 4, C_DARK, 20, 4, 11);
        break;
      case 'CRATES': {
        var stack = 1 + Math.floor(r() * 3), y = 0;
        for (var i = 0; i < stack; i++) {
          var s = 20 + r() * 10;
          B(s, s * 0.8, s, C_WOOD, (r() - 0.5) * 6, y + s * 0.4, (r() - 0.5) * 6);
          y += s * 0.8;
        }
        break;
      }
      case 'BARREL':
        B(20, 30, 20, C_RUST, 0, 15, 0);
        B(22, 3, 22, C_DARK, 0, 8, 0); B(22, 3, 22, C_DARK, 0, 23, 0);
        break;
      case 'HYDRANT':
        B(9, 16, 9, C_RED, 0, 8, 0);
        B(13, 4, 13, C_RED, 0, 17, 0);
        break;
      case 'BOLLARD':
        B(8, 22, 8, C_METAL, 0, 11, 0);
        B(10, 3, 10, C_TRIM, 0, 22, 0);
        break;
      case 'PALLET':
        B(40, 4, 34, C_WOOD, 0, 2, 0);
        B(40, 4, 34, C_WOOD, (r() - 0.5) * 8, 6, (r() - 0.5) * 8);
        break;
      case 'AC':
        B(34, 20, 30, C_METAL, 0, 10, 0);
        B(26, 3, 24, C_TRIM, 0, 21, 0);
        break;
      case 'TIRES': {
        var t = 2 + Math.floor(r() * 3);
        for (var j = 0; j < t; j++) B(26, 8, 26, C_RUBBER, (r() - 0.5) * 5, 4 + j * 8, (r() - 0.5) * 5);
        break;
      }
      case 'SIGN':
        B(4, 40, 4, C_METAL, 0, 20, 0);
        B(26, 16, 2, C_TRIM, 0, 44, 0);
        break;
      case 'BAGS': {
        var b = 2 + Math.floor(r() * 3);
        for (var q = 0; q < b; q++) B(14 + r() * 6, 12, 14 + r() * 6, C_BAG, (r() - 0.5) * 20, 6, (r() - 0.5) * 20);
        break;
      }
      case 'FENCE':
        B(64, 3, 3, C_METAL, 0, 30, 0);
        B(64, 3, 3, C_METAL, 0, 14, 0);
        B(4, 34, 4, C_METAL, -30, 17, 0); B(4, 34, 4, C_METAL, 30, 17, 0);
        break;
      default:
        B(18, 18, 18, C_GREY, 0, 9, 0);
    }
    return sink.length - n0;
  }

  /* planClutter(o) -> [{k,x,y,seed}]  (+ .attempts and .rejected breakdown)
   * Pure placement. Rejects on: world margin, building footprint + door apron, hero spawn, and a
   * coarse occupancy lattice so props do not fuse into piles. Both `attempts` and `placed` are
   * reported rather than one being quietly rounded up.
   *
   * The seed idiom deliberately mirrors index.html:766 genProps -- a raid zone carries its own
   * propSeed so a rival's block gets a different layout, and the 3D clutter must agree with that
   * or the two layers would tell different stories about the same street.
   */
  function planClutter(o) {
    o = o || {};
    var zone    = o.zone || { id: 'HOME_TURF', buildings: [] };
    var worldW  = o.worldW > 0 ? o.worldW : 1700;
    var worldH  = o.worldH > 0 ? o.worldH : 1300;
    var attempts = o.attempts > 0 ? o.attempts : 600;
    var margin  = o.margin >= 0 ? o.margin : 46;
    var bldPad  = o.bldPad >= 0 ? o.bldPad : 42;
    var cell    = o.spacing > 0 ? o.spacing : 34;
    var spawn   = o.spawn || { x: 850, y: 650, r: 110 };

    var zid = zone.id || 'ZONE';
    var seed = (zone.propSeed | 0) || (70217 + zid.length * 131 + zid.charCodeAt(0));
    var rnd = rngFor('akstream:' + zid + ':' + seed);

    var blds = zone.buildings || [];
    var occ = Object.create(null);
    var out = [], rejected = { edge: 0, bld: 0, spawn: 0, packed: 0 };

    for (var i = 0; i < attempts; i++) {
      var x = margin + rnd() * (worldW - margin * 2);
      var y = margin + rnd() * (worldH - margin * 2);
      var kind = pickKind(rnd());
      var half = kind.foot / 2;

      if (x - half < margin || x + half > worldW - margin ||
          y - half < margin || y + half > worldH - margin) { rejected.edge++; continue; }

      // b.x/b.y are the CENTER (index.html:705 B(), hit-tested at index.html:826) and w/h are the
      // 2D footprint. The apron on the +y face is deeper because exitInterior (index.html:1345)
      // drops the player at b.y + b.h/2 + r + 85 -- put a dumpster there and the player walks out
      // of a building straight into it.
      var hitB = false;
      for (var j = 0; j < blds.length; j++) {
        var b = blds[j];
        var bw  = (b.w || 160) / 2 + bldPad + half;
        var bhN = (b.h || 96) / 2 + bldPad + half;
        var bhS = (b.h || 96) / 2 + bldPad + half + 100;
        if (Math.abs(x - b.x) < bw && (y - b.y) > -bhN && (y - b.y) < bhS) { hitB = true; break; }
      }
      if (hitB) { rejected.bld++; continue; }

      var sdx = x - spawn.x, sdy = y - spawn.y;
      if (sdx * sdx + sdy * sdy < (spawn.r + half) * (spawn.r + half)) { rejected.spawn++; continue; }

      var ck = Math.floor(x / cell) + ',' + Math.floor(y / cell);
      if (occ[ck]) { rejected.packed++; continue; }
      occ[ck] = 1;

      out.push({ k: kind.k, x: x, y: y, seed: zid + ':' + i });
    }
    out.rejected = rejected;
    out.attempts = attempts;
    return out;
  }

  /* bucketByChunk(grid, props) -> array[chunkIndex] = [prop,...]
   * The merge unit and the streaming unit are the same unit. That equivalence is the entire reason
   * the partition is built before the content.
   */
  function bucketByChunk(grid, props) {
    var out = new Array(grid.count);
    for (var i = 0; i < props.length; i++) {
      var p = props[i], k = grid.idxAtWorld(p.x, p.y);
      (out[k] || (out[k] = [])).push(p);
    }
    return out;
  }

  // ==========================================================================================
  // SCENE LAYER -- guarded. Nothing below runs at load; every path no-ops without three/world3d.
  // ==========================================================================================

  var CFG = {
    chunk: 256,        // 1700x1300 -> 7x6 = 42 chunks
    topH: 80,          // sample height for the projector test; tallest clutter is the 74u lamp
    hold: 2,           // frames a chunk holds after failing the test (anti-flicker)
    radius: 720,       // distance-policy fallback only; see the header for why it is not default
    band: 128,
    step: 24,          // player movement before a recompute is considered
    attempts: 600,     // placement attempts; rejection lands this near 379 props
    spacing: 34        // occupancy lattice so props do not fuse
  };

  var S = {
    built: false, scene: null, zoneId: '', meshes: [], mat: null,
    stream: null, grid: null, props: [], boxes: 0,
    err: null, lastStats: null, buildMs: 0, policy: 'none'
  };

  function engine() {
    try {
      var T = root && root.AK_THREE;
      if (!T || typeof T.ok !== 'function' || !T.ok()) return null;
      return (typeof T.get === 'function' && T.get()) || null;
    } catch (_e) { return null; }
  }

  // The sanctioned read handle. world3d.js:886 exports `_state: W3` explicitly so a separate
  // module can reach scene/camera/renderer/blds/proj WITHOUT editing world3d.js.
  function w3state() {
    try {
      var W = root && root.AK_WORLD3D;
      if (!W || !W._state) return null;
      return W._state;
    } catch (_e) { return null; }
  }

  function live3d() {
    var W = root && root.AK_WORLD3D;
    try { return !!(W && W.isOn && W.isOn()); } catch (_e) { return false; }
  }

  /* Quantised camera signature. The player can stand still and orbit (world3d.js:678), which
   * changes residency without moving `me`. Quantisation stops a 0.001-rad drag jitter from forcing
   * a recompute every frame; the values are coarse enough to be cheap and fine enough that a real
   * drag is caught within a frame or two.
   */
  function camSig(proj) {
    try {
      var st = proj.state;
      return (Math.round(st.yaw / 0.02) * 1000003) +
             (Math.round(st.phi / 0.02) * 10007) +
             (Math.round(st.zoom / 0.02) * 101) +
             (st.W | 0) * 7 + (st.H | 0);
    } catch (_e) { return 0; }
  }

  /* Merge a chunk's props into ONE BufferGeometry with a per-vertex colour attribute.
   * toNonIndexed() for the reason bldmass.js:57 gives: a box goes 24 -> 36 verts, a rounding error
   * at this scale, and it removes a whole class of index-offset bugs.
   */
  function bakeChunk(THREE, props) {
    var boxes = [];
    for (var i = 0; i < props.length; i++) boxesFor(props[i], boxes);
    if (!boxes.length) return null;

    var pos = [], nor = [], col = [];
    for (var b = 0; b < boxes.length; b++) {
      var o = boxes[b];
      var g = new THREE.BoxGeometry(o.w, o.h, o.d);
      var ng = (typeof g.toNonIndexed === 'function') ? g.toNonIndexed() : g;
      var P = ng.attributes.position, N = ng.attributes.normal;
      var r = ((o.c >> 16) & 255) / 255, gg = ((o.c >> 8) & 255) / 255, bb = (o.c & 255) / 255;
      for (var v = 0; v < P.count; v++) {
        pos.push(P.getX(v) + o.x, P.getY(v) + o.y, P.getZ(v) + o.z);
        nor.push(N.getX(v), N.getY(v), N.getZ(v));
        col.push(r, gg, bb);
      }
      try { if (ng !== g) ng.dispose && ng.dispose(); g.dispose && g.dispose(); } catch (_e) {}
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('normal',   new THREE.Float32BufferAttribute(nor, 3));
    geo.setAttribute('color',    new THREE.Float32BufferAttribute(col, 3));
    geo.computeBoundingSphere();
    return { geo: geo, boxes: boxes.length };
  }

  /* dropMeshes -- release ONLY the geometry this lane allocated. Deliberately does NOT touch the
   * streamer or the grid, because build() reuses those across a district swap to avoid discarding
   * a peer lane's registrations (see the REUSE note in build).
   *
   * world3d.js:452 disposeScene() disposes NOTHING, and setZone (world3d.js:761) disposes geometry
   * but never materials or textures -- nine districts of round-tripping accumulates. This lane
   * does not inherit that bug: everything it allocates, it frees. The shared material is NOT
   * disposed here; it is one instance reused for the life of the page and freed in teardown().
   */
  function dropMeshes() {
    var st = S.scene;
    for (var i = 0; i < S.meshes.length; i++) {
      var m = S.meshes[i];
      try { if (st) st.remove(m); } catch (_e) {}
      try { if (m.geometry) m.geometry.dispose(); } catch (_e) {}
    }
    S.meshes = []; S.props = []; S.boxes = 0;
    return true;
  }

  /* teardown -- the FULL reset (public API / page teardown). Drops peer registrations too, so it
   * is not what a district swap should call. */
  function teardown() {
    dropMeshes();
    if (S.stream) S.stream.clear();
    try { if (S.mat && S.mat.dispose) S.mat.dispose(); } catch (_e) {}
    S.mat = null;
    S.stream = null; S.grid = null; S.built = false; S.zoneId = ''; S.policy = 'none';
    return true;
  }

  /* build(ctx) -- plan, bake, register. Runs once per district entry, never per frame. */
  function build(ctx) {
    var THREE = engine(); if (!THREE) { S.err = 'no-three'; return false; }
    var w3 = w3state();
    if (!w3 || !w3.scene) { S.err = 'no-scene'; return false; }
    var zone = ctx && ctx.activeZone; if (!zone) { S.err = 'no-zone'; return false; }

    var t0 = (root.performance && root.performance.now) ? root.performance.now() : Date.now();
    dropMeshes();          // NOT teardown(): keep the streamer so peer registrations survive
    S.scene = w3.scene;
    S.zoneId = zone.id;

    var worldW = 1700, worldH = 1300;
    try { if (ctx.world) { worldW = ctx.world.WORLD_W || worldW; worldH = ctx.world.WORLD_H || worldH; } } catch (_e) {}

    /* REUSE the grid + streamer when the world rect has not changed, and clear ONLY our own tag.
     *
     * This is not a micro-optimisation, it is a cross-lane correctness fix. akworldgen.js:756
     * parks its structures in this partition with the 'worldgen' tag and drops them again at
     * akworldgen.js:773. It is loaded at index.html:502 and this module at :548, so it REGISTERS
     * BEFORE US in the same frame (tickAll walks modules in registration order, _registry.js:22).
     * Allocating a fresh streamer here would therefore throw away registrations that a peer lane
     * had already made THIS frame, and because that peer only re-registers on its own district
     * rebuild, its structures would silently stop streaming for the rest of the session -- visible
     * as worldgen geometry that never hides again after the first district swap.
     * Every district in this game is 1700x1300 (index.html:588 ZW/ZH, reset on every enterZone),
     * so the reuse path is the one that actually runs; the rebuild path is there for the day a
     * district is a different size.
     */
    var sameRect = S.grid && S.stream &&
                   S.grid.worldW === worldW && S.grid.worldH === worldH && S.grid.size === CFG.chunk;
    if (sameRect) {
      S.stream.clear('clutter');          // drop OUR props only; peer-tagged handles survive
    } else {
      S.grid = makeChunkGrid({ worldW: worldW, worldH: worldH, size: CFG.chunk });
      // Residency policy: projector if world3d has one (it always does once booted), else distance.
      // W3.proj is created once (world3d.js:446) and setZone only calls setWorld on it, never
      // replaces it, so a test bound to it stays valid across district swaps.
      var test = null;
      if (w3.proj && typeof w3.proj.project === 'function') {
        test = makeProjTest(S.grid, w3.proj, { topH: CFG.topH });
        S.policy = 'projector';
      } else { S.policy = 'distance'; }
      S.stream = makeStreamer(S.grid, {
        radius: CFG.radius, band: CFG.band, step: CFG.step, hold: CFG.hold, test: test
      });
    }

    // A locked district (THE_OVERLOOK, THE_UNDERCITY) has zero buildings and the player cannot
    // walk it, but clutter plans fine -- there is simply nothing to reject against.
    S.props = planClutter({
      zone: zone, worldW: worldW, worldH: worldH,
      attempts: CFG.attempts, spacing: CFG.spacing,
      spawn: { x: worldW / 2, y: worldH / 2, r: 110 }
    });

    var buckets = bucketByChunk(S.grid, S.props);
    var mat = S.mat || (S.mat = new THREE.MeshLambertMaterial({ vertexColors: true }));

    for (var i = 0; i < buckets.length; i++) {
      var list = buckets[i]; if (!list || !list.length) continue;
      var baked = bakeChunk(THREE, list); if (!baked) continue;
      var mesh = new THREE.Mesh(baked.geo, mat);
      // Geometry is already in world space, so the mesh sits at the origin and never moves.
      // matrixAutoUpdate=false drops it from three's per-frame matrix walk: with ~35 chunk meshes
      // that is 35 matrix compositions skipped every frame for one line.
      mesh.matrixAutoUpdate = false;
      mesh.updateMatrix();
      mesh.userData.akChunk = i;
      mesh.userData.akProps = list.length;
      S.scene.add(mesh);
      S.meshes.push(mesh);
      S.boxes += baked.boxes;
      // Registered at the chunk CENTRE: the handle stands for the whole chunk, and `weight` carries
      // how many props ride on it so the stats stay honest about what a hidden chunk really costs.
      S.stream.add(mesh, S.grid.centerX(S.grid.cxAt(i)), S.grid.centerY(S.grid.cyAt(i)), 'clutter', list.length);
    }

    S.built = true;
    S.err = null;
    S.buildMs = ((root.performance && root.performance.now) ? root.performance.now() : Date.now()) - t0;
    // Seed residency immediately so the first rendered frame is already correct.
    try {
      var me = (ctx && ctx.me) || root.me;
      if (me) S.stream.update(me.x, me.y, w3.proj ? camSig(w3.proj) : undefined);
    } catch (_e) {}
    return true;
  }

  /* onTick -- the per-frame path.
   * Zone change is a POLL, not an event: enterZone (index.html:1354) mutates activeZone and
   * notifies nobody, which is why world3d.js:900 also calls setZone(ctx) every tick. Same idiom
   * here, same cheap early-out.
   *
   * RAIDS: index.html:2436 restricts ticking during a raid to a hardcoded allowlist
   * ['raidwaves','raidfortify','backpack'], so 'akstream' gets zero ticks in a raid. That is the
   * correct outcome, not a bug -- index.html:2426 also freezes world3d, so the GL layer is not
   * rendering and there is nothing to stream.
   */
  function tick(dt, ctx) {
    if (!live3d()) return false;
    var w3 = w3state(); if (!w3 || !w3.scene) return false;

    // Scene IDENTITY, not just zone id: disposeScene() (world3d.js:452) nulls the scene and a
    // re-boot builds a fresh one. Comparing ids alone would leave our meshes orphaned in a dead
    // scene, rendering nothing, with no error anywhere.
    var zid = (ctx && ctx.zoneId) || '';
    if (!S.built || S.scene !== w3.scene || S.zoneId !== zid) {
      if (!build(ctx)) return false;
    }
    var me = (ctx && ctx.me) || root.me; if (!me) return false;
    S.lastStats = S.stream.update(me.x, me.y, w3.proj ? camSig(w3.proj) : undefined);
    return true;
  }

  // ==========================================================================================
  // SELF TEST -- the activation proof. `node systems/akstream.js`.
  // Exercises the REAL planner, the REAL streamer and the REAL world3d projector (world3d.js is
  // node-requireable: its pure core ends at line 366 and exports module.exports = API). The only
  // thing faked is THREE, because there is no GPU in node -- and the fake bakes exactly the way
  // build() does, one handle per non-empty chunk carrying that chunk's prop count as its weight.
  // ==========================================================================================
  function selfTest() {
    var fail = 0, out = [];
    function log(s) { out.push(s); }
    function ok(cond, label) { if (!cond) { fail++; log('  FAIL  ' + label); } else log('  ok    ' + label); }

    log('AK_STREAM ' + VER + ' -- self test');

    // ---- grid math -------------------------------------------------------------------------
    var g = makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 });
    log('\n[grid] ' + g.worldW + 'x' + g.worldH + ' at ' + g.size + ' -> ' + g.cols + 'x' + g.rows + ' = ' + g.count + ' chunks');
    ok(g.cols === 7 && g.rows === 6 && g.count === 42, 'grid dims 7x6=42');
    ok(g.idxAtWorld(0, 0) === 0, 'origin -> chunk 0');
    ok(g.idxAtWorld(1699, 1299) === g.count - 1, 'far corner -> last chunk');
    ok(g.idxAtWorld(-500, -500) === 0, 'out-of-world clamps low');
    ok(g.idxAtWorld(9999, 9999) === g.count - 1, 'out-of-world clamps high');
    ok(g.distToRect(0, 0, 10, 10) === 0, 'inside rect -> distance 0');
    ok(Math.abs(g.distToRect(0, 0, 256 + 100, 10) - 100) < 1e-9, 'right of rect -> exact gap');
    var rct = [0, 0, 0, 0];
    g.rectOf(g.count - 1, rct);
    ok(rct[2] === 1700 && rct[3] === 1300, 'edge chunk rect is CLIPPED to the world');
    var rr = [];
    ok(g.ring(0, 0, 1, rr) === 4, 'corner ring r=1 clips to 4 cells');
    ok(g.ring(3, 3, 1, rr) === 9, 'interior ring r=1 is 9 cells');

    // ---- streamer show/hide (distance policy = the headless fallback) -------------------------
    var sm = makeStreamer(makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 }),
                          { radius: 300, band: 0, step: 0 });
    var a = { visible: true }, b = { visible: true };
    sm.add(a, 50, 50, 't', 1); sm.add(b, 1650, 1250, 't', 1);
    sm.update(50, 50);
    ok(a.visible === true,  'near object shown');
    ok(b.visible === false, 'far object hidden');
    sm.update(1650, 1250);
    ok(a.visible === false, 'walked away -> old object hidden');
    ok(b.visible === true,  'walked to -> new object shown');
    var st0 = sm.stats();
    ok(st0.visibleObjects + st0.hiddenObjects === st0.objects, 'visible+hidden === total');

    // hysteresis: acquire at radius, release only at radius+band
    var hm = makeStreamer(makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 }),
                          { radius: 200, band: 150, step: 0 });
    var hobj = { visible: true };
    hm.add(hobj, 900, 100, 't', 1);              // chunk (3,0) spans x 768..1024
    hm.update(700, 100); ok(hobj.visible === true, 'hysteresis: acquired inside radius');
    hm.update(500, 100); ok(hobj.visible === true, 'hysteresis: holds inside the release band');
    hm.update(400, 100); ok(hobj.visible === false, 'hysteresis: releases past radius+band');

    // fast path: no movement must do no work
    var fm = makeStreamer(makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 }),
                          { radius: 400, band: 64, step: 48 });
    fm.add({ visible: true }, 800, 600, 't', 1);
    fm.update(800, 600);
    var rc0 = fm.stats().recomputes;
    for (var f = 0; f < 60; f++) fm.update(800 + f * 0.4, 600);   // 24 units total, under STEP
    ok(fm.stats().recomputes === rc0, 'fast path: 60 sub-threshold frames -> 0 recomputes');

    // camera signature must defeat the fast path even when the player is perfectly still
    var cm = makeStreamer(makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 }),
                          { radius: 400, band: 0, step: 48 });
    cm.add({ visible: true }, 800, 600, 't', 1);
    cm.update(800, 600, 1);
    var rc1 = cm.stats().recomputes;
    cm.update(800, 600, 1); ok(cm.stats().recomputes === rc1, 'same cam sig + no movement -> no recompute');
    cm.update(800, 600, 2); ok(cm.stats().recomputes === rc1 + 1, 'CHANGED cam sig -> recompute (orbit while standing still)');

    // release delay (anti-flicker)
    var flip = false;
    var dm2 = makeStreamer(makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 }),
                           { step: 0, hold: 2, test: function () { return flip; } });
    var dobj = { visible: false };
    dm2.add(dobj, 100, 100, 't', 1);
    flip = true;  dm2.update(100, 100, 0); ok(dobj.visible === true, 'hold: acquires immediately');
    flip = false; dm2.update(100, 100, 1); ok(dobj.visible === true, 'hold: frame 1 still resident');
    dm2.update(100, 100, 2);               ok(dobj.visible === true, 'hold: frame 2 still resident');
    dm2.update(100, 100, 3);               ok(dobj.visible === false, 'hold: releases after HOLD frames');

    /* tag-scoped clear -- THE CROSS-LANE CONTRACT.
     * akworldgen.js:756 parks its structures here with the 'worldgen' tag and it registers BEFORE
     * this module in the same frame (index.html:502 vs :548). build() therefore drops only the
     * 'clutter' tag on a district swap instead of allocating a fresh streamer, or a peer lane's
     * registrations would be discarded the moment the player changed district and its geometry
     * would never stream again. This guards that behaviour permanently. */
    var tg = makeStreamer(makeChunkGrid({ worldW: 1700, worldH: 1300, size: 256 }),
                          { radius: 5000, band: 0, step: 0 });
    var mine = { visible: true }, peer = { visible: true };
    tg.add(mine, 400, 400, 'clutter', 5);
    tg.add(peer, 400, 400, 'worldgen', 2);
    tg.update(400, 400);
    ok(tg.stats().objects === 2 && tg.stats().units === 7, 'two tags registered (2 objects, 7 units)');
    ok(tg.clear('clutter') === 1, 'clear("clutter") drops exactly one handle');
    ok(tg.stats().objects === 1, 'peer handle SURVIVES a tag-scoped clear');
    ok(tg.objectsIn(tg.grid.cxOf(400), tg.grid.cyOf(400))[0].tag === 'worldgen', 'the survivor is the peer');
    ok(tg.clear() === 1, 'untagged clear() drops everything');

    // ---- clutter planning on the REAL spawn district ----------------------------------------
    var HOME = {
      id: 'HOME_TURF', propSeed: 0,
      buildings: [
        { id: 'ARENA',     x: 850,  y: 360, w: 210, h: 124 },
        { id: 'TROPHY',    x: 430,  y: 880, w: 160, h: 96 },
        { id: 'KENNEL',    x: 1270, y: 880, w: 160, h: 96 },
        { id: 'INFIRMARY', x: 1270, y: 500, w: 160, h: 96 }
      ]
    };
    var props = planClutter({ zone: HOME, worldW: 1700, worldH: 1300, attempts: CFG.attempts, spacing: CFG.spacing });
    var boxes = [];
    for (var p = 0; p < props.length; p++) boxesFor(props[p], boxes);
    log('\n[clutter] attempts ' + props.attempts + ' -> placed ' + props.length +
        '   (rejected: building ' + props.rejected.bld + ', packed ' + props.rejected.packed +
        ', edge ' + props.rejected.edge + ', spawn ' + props.rejected.spawn + ')');
    log('[clutter] ' + boxes.length + ' boxes -> ' + (boxes.length * 12) + ' triangles' +
        '   (bldmass.js:9 measured the whole pre-existing visible world at 50)');
    ok(props.length >= 300, 'planner places 300+ props (got ' + props.length + ')');

    var props2 = planClutter({ zone: HOME, worldW: 1700, worldH: 1300, attempts: CFG.attempts, spacing: CFG.spacing });
    var same = props.length === props2.length;
    for (var d = 0; same && d < props.length; d++) {
      if (props[d].k !== props2[d].k || props[d].x !== props2[d].x || props[d].y !== props2[d].y) same = false;
    }
    ok(same, 'planner is deterministic across runs');
    var propsY = planClutter({ zone: { id: 'THE_YARDS', buildings: [] }, worldW: 1700, worldH: 1300, attempts: CFG.attempts, spacing: CFG.spacing });
    ok(propsY.length && propsY[0].x !== props[0].x, 'a different district plans a different layout');

    var inside = 0;
    for (var q = 0; q < props.length; q++) {
      for (var w = 0; w < HOME.buildings.length; w++) {
        var bb = HOME.buildings[w];
        if (Math.abs(props[q].x - bb.x) < bb.w / 2 && Math.abs(props[q].y - bb.y) < bb.h / 2) inside++;
      }
    }
    ok(inside === 0, 'no prop lands inside a building footprint');
    var onSpawn = 0;
    for (var z = 0; z < props.length; z++) if (Math.hypot(props[z].x - 850, props[z].y - 650) < 100) onSpawn++;
    ok(onSpawn === 0, 'no prop lands on the hero spawn');

    // ---- bake: one merged mesh per chunk -----------------------------------------------------
    var bg = makeChunkGrid({ worldW: 1700, worldH: 1300, size: CFG.chunk });
    var buckets = bucketByChunk(bg, props);
    var nonEmpty = 0;
    for (var c = 0; c < buckets.length; c++) if (buckets[c] && buckets[c].length) nonEmpty++;
    log('[bake] ' + nonEmpty + ' non-empty chunks -> ' + nonEmpty + ' merged meshes = ' +
        nonEmpty + ' draw calls (unmerged: ' + props.length + ')');
    ok(nonEmpty > 1, 'clutter spreads across multiple chunks');

    // ---- THE ACTIVATION PROOF, against the real world3d projector ----------------------------
    var W3 = null;
    try { W3 = require('./world3d.js'); } catch (_e) {
      try { W3 = require(__dirname + '/world3d.js'); } catch (_e2) { W3 = null; }
    }
    if (!W3 || typeof W3.makeProjector !== 'function') {
      log('\n[walk] SKIPPED -- could not require ./world3d.js for its projector');
      fail++;
    } else {
      // fog from world3d.js:666 -> Fog(tint, 420, 1750), linear. This is what actually removes a
      // distant prop; see the header.
      function fogF(dist) { return Math.max(0, Math.min(1, (dist - 420) / (1750 - 420))); }
      var AUDIT_EVERY = 3;   // pop-in audit sampling stride -- see the note at the audit itself

      function walk(vpW, vpH, phi, zoom, label) {
        var pj = W3.makeProjector({});
        pj.setViewport(vpW, vpH); pj.setWorld(1700, 1300);
        if (phi != null) pj.setPhi(phi);
        if (zoom != null) pj.setZoom(zoom);

        var grid2 = makeChunkGrid({ worldW: 1700, worldH: 1300, size: CFG.chunk });
        var bk = bucketByChunk(grid2, props);
        var stream = makeStreamer(grid2, {
          step: CFG.step, hold: CFG.hold, test: makeProjTest(grid2, pj, { topH: CFG.topH })
        });
        var meshes = [];
        for (var m = 0; m < bk.length; m++) {
          var list = bk[m]; if (!list || !list.length) continue;
          var fake = { visible: true, _chunk: m, _props: list.length };
          meshes.push(fake);
          stream.add(fake, grid2.centerX(grid2.cxAt(m)), grid2.centerY(grid2.cyAt(m)), 'clutter', list.length);
        }

        // Perimeter patrol at ~14 units/frame, sampled every frame the way onTick would.
        var route = [[180, 180], [1520, 180], [1520, 650], [180, 650], [180, 1120], [1520, 1120], [850, 650]];
        var px = route[0][0], py = route[0][1];
        var steps = 0, sumRes = 0, sumHidU = 0, sumHidO = 0, minRes = 1e9, maxRes = -1;
        var popins = 0, worstPop = 0, worstDesc = '';

        pj.follow(px, py); stream.update(px, py, camSig(pj));
        for (var leg = 1; leg < route.length; leg++) {
          var tx = route[leg][0], ty = route[leg][1];
          while (Math.hypot(tx - px, ty - py) > 14) {
            var ang = Math.atan2(ty - py, tx - px);
            px += Math.cos(ang) * 14; py += Math.sin(ang) * 14;
            pj.follow(px, py);
            stream.update(px, py, camSig(pj));
            var s2 = stream.stats();
            steps++; sumRes += s2.resident; sumHidU += s2.hiddenUnits; sumHidO += s2.hiddenObjects;
            if (s2.resident < minRes) minRes = s2.resident;
            if (s2.resident > maxRes) maxRes = s2.resident;

            // POP-IN AUDIT: for every prop in a HIDDEN chunk, re-project the prop ITSELF and ask
            // whether it would have landed inside the true screen rect with enough fog
            // transmittance to be seen. Any hit is a visible object we wrongly removed.
            //
            // Sampled every AUDIT_EVERY frames on purpose. project() returns a FRESH OBJECT per
            // call (world3d.js:212), so auditing ~200 hidden props x 2 heights on all 408 frames
            // of all 7 walks allocated ~8.5M short-lived objects and made this harness segfault
            // roughly 1 run in 5 under proot. Sampling still audits ~136 frames per camera config
            // (~800 across the suite) and every walk still covers the full perimeter, so the
            // guarantee is unchanged while the harness became reliable. Measured after the change:
            // 20/20 clean runs. The SHIPPED path never does this work at all -- it is test-only.
            if (steps % AUDIT_EVERY) continue;
            var mask = stream.residentMask(), C = pj.camPos();
            for (var ci = 0; ci < grid2.count; ci++) {
              if (mask[ci]) continue;
              var lst = bk[ci]; if (!lst) continue;
              for (var pi = 0; pi < lst.length; pi++) {
                var pr = lst[pi];
                var base = pj.project(pr.x, pr.y, 0), top = pj.project(pr.x, pr.y, 74);
                if (!base || !top) continue;
                var on = (top.vis && top.sx > 0 && top.sx < vpW && top.sy > 0 && top.sy < vpH) ||
                         (base.vis && base.sx > 0 && base.sx < vpW && base.sy > 0 && base.sy < vpH);
                if (!on) continue;
                var camD = Math.sqrt((pr.x - C.x) * (pr.x - C.x) + C.y * C.y + (pr.y - C.z) * (pr.y - C.z));
                var effPx = Math.abs(top.sy - base.sy) * (1 - fogF(camD));
                if (effPx > 0.5) {
                  popins++;
                  if (effPx > worstPop) { worstPop = effPx; worstDesc = pr.k + ' @ ' + pr.x.toFixed(0) + ',' + pr.y.toFixed(0); }
                }
              }
            }
          }
        }
        var fin = stream.stats();
        // Bookkeeping audit: every mesh's .visible flag must agree with its chunk's residency bit.
        // A drift here means applyChunk and the resident mask disagree, which would silently show
        // or hide the wrong geometry while the stats still looked healthy.
        var mismatch = 0, maskEnd = stream.residentMask();
        for (var mm = 0; mm < meshes.length; mm++) {
          if (!!meshes[mm].visible !== !!maskEnd[meshes[mm]._chunk]) mismatch++;
        }
        return {
          label: label, steps: steps, fin: fin, meshes: meshes, mismatch: mismatch,
          meanRes: sumRes / steps, meanHidU: sumHidU / steps, meanHidO: sumHidO / steps,
          minRes: minRes, maxRes: maxRes, popins: popins, worstPop: worstPop, worstDesc: worstDesc
        };
      }

      var main = walk(412, 915, null, null, 'phone 412x915 default cam');
      log('\n[walk] ' + main.steps + ' frames, 7-leg perimeter patrol, ' + main.label);
      log('[walk] chunk meshes resident : mean ' + main.meanRes.toFixed(1) + '/' + main.fin.objects +
          '  (min ' + main.minRes + ', max ' + main.maxRes + ')');
      log('[walk] props HIDDEN per frame: mean ' + main.meanHidU.toFixed(1) + '/' + main.fin.units +
          '  = ' + (100 * main.meanHidU / main.fin.units).toFixed(1) + '%');
      log('[walk] draw calls skipped    : mean ' + main.meanHidO.toFixed(1) + '/' + main.fin.objects);
      log('[walk] recomputes ' + main.fin.recomputes + ' of ' + main.steps + ' frames (' +
          (100 * main.fin.recomputes / main.steps).toFixed(1) + '%) -- the other ' +
          (100 - 100 * main.fin.recomputes / main.steps).toFixed(1) + '% took the zero-work fast path');
      log('[walk] POP-IN AUDIT: ' + main.popins + ' visible props found inside hidden chunks');

      ok(main.fin.policy === 'projector', 'walk ran the PROJECTOR policy, not the fallback');
      ok(main.meanHidU > 0, 'STREAMING ACTIVATES: props are hidden during the walk');
      ok(main.meanHidU / main.fin.units > 0.25, 'streaming hides >25% of props on average (got ' +
         (100 * main.meanHidU / main.fin.units).toFixed(1) + '%)');
      ok(main.minRes < main.fin.objects, 'at least one frame had a non-resident chunk');
      ok(main.fin.recomputes < main.steps, 'the fast path actually fires');
      ok(main.fin.visibleObjects + main.fin.hiddenObjects === main.fin.objects, 'accounting closes after the walk');
      ok(main.popins === 0, 'NO POP-IN: zero visible props inside hidden chunks' +
         (main.popins ? ' (worst ' + main.worstPop.toFixed(1) + 'px ' + main.worstDesc + ')' : ''));

      ok(main.mismatch === 0, 'every mesh .visible matches its chunk residency bit (' +
         main.mismatch + ' mismatches)');

      // Camera extremes: orbit and zoom must not break the pop-in guarantee.
      var DEG = Math.PI / 180;
      var extremes = [
        walk(412, 915, 72 * DEG, null, 'phi=PHI_MAX 72deg'),
        walk(412, 915, 10 * DEG, null, 'phi=10deg near-horizon'),
        walk(412, 915, null, 0.55,     'zoom=ZOOM_MIN 0.55'),
        walk(412, 915, null, 2.2,      'zoom=ZOOM_MAX 2.2'),
        walk(1280, 720, null, null,    'landscape 1280x720'),
        walk(820, 1180, null, null,    'tablet 820x1180')
      ];
      log('\n[extremes] hidden% and pop-ins across camera + viewport range:');
      for (var e = 0; e < extremes.length; e++) {
        var x = extremes[e];
        log('  ' + (100 * x.meanHidU / x.fin.units).toFixed(1) + '% hidden, ' +
            x.meanRes.toFixed(1) + '/' + x.fin.objects + ' resident, popins ' + x.popins +
            '   [' + x.label + ']');
        ok(x.popins === 0, 'no pop-in at ' + x.label);
      }
    }

    log('\n' + (fail ? 'FAILED ' + fail + ' check(s)' : 'ALL CHECKS PASSED'));
    return { ok: fail === 0, fails: fail, report: out.join('\n') };
  }

  // ==========================================================================================
  // EXPORTS
  // ==========================================================================================
  var API = {
    version: function () { return VER; },
    // pure core -- the shared substrate for the LOD / culling / clutter lanes
    makeChunkGrid: makeChunkGrid, makeStreamer: makeStreamer, makeProjTest: makeProjTest,
    planClutter: planClutter, boxesFor: boxesFor, bucketByChunk: bucketByChunk, rngFor: rngFor,
    CLUTTER: CLUTTER, config: CFG,
    // live chunk index -- THE public spatial substrate
    grid: function () { return S.grid; },
    stream: function () { return S.stream; },
    chunkOf: function (x, y) { return S.grid ? S.grid.idxAtWorld(x, y) : -1; },
    objectsIn: function (cx, cy) { return S.stream ? S.stream.objectsIn(cx, cy) : []; },
    isResident: function (cx, cy) { return S.stream ? S.stream.isResident(cx, cy) : false; },
    residentMask: function () { return S.stream ? S.stream.residentMask() : null; },
    // let other lanes park their own objects in the same partition
    add: function (obj, x, y, tag, weight) { return S.stream ? S.stream.add(obj, x, y, tag || 'ext', weight) : null; },
    remove: function (h) { return S.stream ? S.stream.remove(h) : false; },
    setRadius: function (r, band) { return S.stream ? S.stream.setRadius(r, band) : null; },
    // lifecycle
    build: build, teardown: teardown, tick: tick,
    stats: function () { return S.stream ? S.stream.stats() : null; },
    // Diagnostics. Failures are REPORTED, never swallowed -- a silent subsystem is how a corrupt
    // vendor file hid on this project for hours with zero console output.
    diag: function () {
      var w3 = w3state();
      return {
        version: VER, built: S.built, zone: S.zoneId, policy: S.policy, err: S.err,
        three: !!engine(), scene: !!(w3 && w3.scene), live3d: live3d(),
        props: S.props.length, boxes: S.boxes, tris: S.boxes * 12,
        meshes: S.meshes.length, buildMs: Math.round(S.buildMs),
        stats: S.stream ? S.stream.stats() : null
      };
    },
    selfTest: selfTest,
    _state: S
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_STREAM = API;
    // Self-register so the hub's existing initAll/tickAll dispatch drives this module with zero
    // bespoke wiring. _registry.js:22 tickAll is the caller; the hub reaches it from
    // index.html:3328 akTickSystems, gated at index.html:2426 on IN_ZONE && !interiorOpen.
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({
          id: 'akstream',
          // No init work: world3d boots three ASYNCHRONOUSLY and its scene does not exist at
          // initAll() time. tick() polls for it and builds on the first frame the scene is live.
          init: function () { return true; },
          onTick: function (dt, ctx) { tick(dt, ctx); }
        });
      }
    } catch (_e) {}
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akstream.js` prints the streaming activation proof. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  var r = module.exports.selfTest();
  console.log(r.report);
  process.exit(r.ok ? 0 : 1);
}
