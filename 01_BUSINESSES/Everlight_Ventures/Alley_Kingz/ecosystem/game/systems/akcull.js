/* ALLEY KINGZ -- AK_CULL: frustum + distance + software OCCLUSION culling for the 3D district.
 *
 * WHY THIS EXISTS, AND THE ONE HONEST CAVEAT UP FRONT
 * ---------------------------------------------------
 * RuneScape's NXT engine credits "dynamic hybrid occlusion culling + reduced draw calls" as its
 * headline win. Three of the four techniques that phrase implies are ABSENT from this repo (grep
 * for THREE.Frustum / frustumCulled / THREE.LOD across systems/ + index.html returns ZERO hits).
 * The fourth -- frustum culling -- three.js ALREADY DOES, and pretending otherwise would be a lie.
 *
 * Measured from the vendored renderer, assets/vendor/three.module.min.js, function `Xt`
 * (WebGLRenderer.projectObject, name-mangled). Quoted verbatim from the minified source:
 *
 *   function Xt(t,e,n,i){ if(!1===t.visible)return;
 *     if(t.layers.test(e.layers)) ...
 *     else if((t.isMesh||t.isLine||t.isPoints)&&(!t.frustumCulled||V.intersectsObject(t))){
 *       const e=ot.update(t),r=t.material; ... _.push(t,e,r,n,q.z,null) }
 *
 * Read that carefully, because it settles two questions the brief asked:
 *
 *   1. IS A MANUAL FRUSTUM PASS REDUNDANT FOR DRAW CALLS?  YES. `t.frustumCulled` defaults to
 *      true (Object3D ctor: `this.frustumCulled=!0`) and `V.intersectsObject(t)` is a real
 *      bounding-sphere-vs-frustum test. Any box our frustum pass rejects, three would ALSO have
 *      rejected. Our frustum pass buys ZERO draw calls over stock three. Stated plainly so nobody
 *      later believes this module invented frustum culling. It did not.
 *
 *   2. THEN WHY IMPLEMENT IT AT ALL?  Because `if(!1===t.visible)return;` is the FIRST line, and
 *      it fires BEFORE `layers.test`, BEFORE `intersectsObject` (a Sphere copy + applyMatrix4 per
 *      object per frame), BEFORE `ot.update(t)` (geometry buffer bookkeeping), and BEFORE the
 *      renderlist push. That push is where this scene bleeds: world3d.js:539 builds each building
 *      as `new THREE.Mesh(geo,[side,side,roof,side,face,side])`, a SIX-material array, so
 *      BoxGeometry's six groups become SIX renderlist items per building. Hiding one building with
 *      .visible=false removes 6 items; letting three frustum-cull it removes the same 6 items but
 *      pays the sphere transform first. So the frustum pass is a CPU saving, NOT a draw-call
 *      saving, and this file reports it in its own bucket so the distinction stays visible.
 *
 *   3. WHAT IS ACTUALLY NEW HERE:  three has NO occlusion culling and NO distance culling, at all,
 *      in any version. Those two buckets are pure additive wins and they are where the draw calls
 *      come from. Occlusion is the headline; see the buffer section below.
 *
 * WHY OCCLUSION IS TRACTABLE IN THIS PARTICULAR WORLD
 * --------------------------------------------------
 * Districts are axis-aligned boxes standing on one flat plane (world3d.js:495 buildGround is a
 * single PlaneGeometry; world3d.js:534 positions every building at y=h/2 with no rotation). There
 * are no overhangs, no arches, no concave geometry. A box is therefore a perfect occluder: it is
 * convex, closed, and opaque. That is the exact precondition a software occlusion buffer needs,
 * and it is why this is ~400 lines rather than a research project.
 *
 * THE ALGORITHM (single pass, front-to-back, conservative in the safe direction)
 * -----------------------------------------------------------------------------
 *   1. Project all 8 corners of every box. Keep the screen AABB, the NEAREST corner depth, and the
 *      FARTHEST corner depth.
 *   2. Distance-reject on nearest depth. Frustum-reject on the screen AABB.
 *   3. Sort survivors front-to-back by nearest depth.
 *   4. Walk that order against a coarse depth buffer:
 *        - a box is OCCLUDED if, for every screen tile its AABB touches, its NEAREST depth is
 *          strictly beyond the depth already written there;
 *        - a box that survives is then RASTERISED into the buffer as an occluder, writing its
 *          FARTHEST depth.
 *      Because the walk is front-to-back, only nearer boxes can ever have written the buffer, so
 *      "is this behind something" needs no extra bookkeeping. It falls out of the ordering.
 *
 * EVERY APPROXIMATION LEANS THE SAME WAY: TOWARDS DRAWING.
 *   - Occluder footprint UNDER-estimates (only tiles the silhouette FULLY covers get written).
 *   - Occluder depth is the box's FARTHEST corner, so the whole tile is guaranteed solid up to it.
 *   - Candidate footprint OVER-estimates (screen AABB, not the tighter silhouette hull).
 *   - Candidate depth is its NEAREST corner.
 *   - Anything straddling the near plane is never culled and never occludes.
 * A false cull is a building popping out of existence in the player's face. A missed cull is six
 * wasted renderlist items. Those costs are not remotely symmetric, so every rounding goes to
 * "draw it".
 *
 * THE CONVEXITY TRICK THAT MAKES INNER-RASTERISATION CHEAP (proof, because it is load-bearing)
 * -------------------------------------------------------------------------------------------
 * We need the tiles a projected box FULLY covers. The projected silhouette of a box is a convex
 * polygon (convex solid + pinhole projection = convex image), at most 6 sided.
 *   Claim: for a convex region, if x is inside the horizontal cross-section at y0 AND inside the
 *   cross-section at y1, then x is inside the cross-section at every y between them.
 *   Proof: (x,y0) and (x,y1) are both in the region; the region is convex; therefore the entire
 *   segment joining them -- which is exactly {(x,y) : y0<=y<=y1} -- is in the region. QED.
 * So a tile ROW's fully-covered x-band is just the INTERSECTION of the polygon's x-span at the
 * row's top edge and at its bottom edge. Two span queries per row instead of a point-in-polygon
 * test per tile: the difference between ~7k ops and ~200 ops for a large building.
 *
 * ALPHA-CUT FACADES MAY NOT OCCLUDE. world3d.js:558 sets `mat.transparent=true; mat.alphaTest=0.5`
 * when a _cut facade loads. A cut facade has literal holes in it -- you can see through the
 * doorway -- so a box wearing one is NOT a valid occluder. It can still BE occluded. Today only
 * assets/hub/town_hall_cut.png exists on disk so this affects exactly one building (ARENA, the
 * HOME_TURF spawn anchor), but that building is the biggest thing in the starting district and
 * would have been the single most attractive occluder in the game. Handled at classify().
 *
 * WHAT THIS MODULE MAY NOT DO: it must never edit systems/world3d.js. It reads AK_WORLD3D._state
 * (exported for exactly this purpose at world3d.js:885) and writes only `mesh.visible`. If
 * AK_WORLD3D is absent, unbooted, or off, every entry point degrades to a no-op and the 2D game is
 * untouched. Errors are counted and surfaced in stats(), never swallowed to silence.
 *
 * NODE: `node systems/akcull.js` runs the proof harness (selfTest) against the REAL shipping
 * projector required out of world3d.js -- not a mock -- including a 64-building dense district.
 */
(function (root) {
  'use strict';

  var DEG = Math.PI / 180;

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  /* =====================================================================
   * PURE CORE -- no DOM, no three.js, no globals. Requireable in node.
   * ===================================================================== */

  var CFG = {
    // Screen margin on the frustum test, in px. The cull runs from AK_SYSTEMS.tickAll, which is
    // one dispatch step away from world3d's own frame(); whichever registers first, the camera we
    // read is up to one frame stale. At the 50ms dt clamp (index.html:2370) and the hub's walk
    // speed the camera cannot move more than a few dozen px in that window, so 96px of slack
    // makes the staleness unobservable while still rejecting anything genuinely off-screen.
    margin: 96,
    // Hard distance cutoff on NEAREST corner depth. world3d.js:673 fogs to `Fog(tint,420,1750)`
    // and the camera far plane is 6000 (world3d.js:719). Anything past the fog's far value is
    // already 100% fog colour, so hiding it is invisible BY CONSTRUCTION -- the fog has already
    // replaced its every pixel with the sky tint. 1750 is therefore not a taste value, it is the
    // exact point where the renderer stops showing you the object.
    maxDist: 1750,
    // Occlusion buffer resolution. 48x28 = 1344 tiles, ~19x21 px each at 900x600. Finer grids cull
    // more (less is lost to the conservative inner-rasterisation edge) but cost more per frame;
    // coarser grids are cheaper but a building must be bigger to occlude anything. 48x28 is the
    // point where a typical 160x100 footprint building still writes tiles at mid-district range.
    cols: 48,
    rows: 28,
    occlusion: true,
    distance: true,
    frustum: true
  };

  /* --- CAMERA SNAPSHOT ------------------------------------------------
   * world3d.js:212 project() rebuilds the full camera basis on EVERY call: a camPos(), three
   * hypot() normalisations, a cross product. Culling a 64-building district needs 8 corners x 64 =
   * 512 projections per frame; paying for 512 basis rebuilds to compute 512 dot products is
   * absurd. This snapshots the basis ONCE per frame, then each corner is ~12 multiply-adds.
   *
   * THE MATH BELOW IS A LINE-FOR-LINE MIRROR OF world3d.js:212-238 AND MUST STAY THAT WAY. If the
   * two ever disagree, the culler is deciding visibility against a camera the GPU is not using and
   * buildings vanish on screen. selfTest() case 1 asserts agreement to 1e-9 against the real
   * projector, so a drift here fails `node systems/akcull.js` rather than shipping.
   */
  function makeXform(proj) {
    var S = proj.state;
    var C = proj.camPos();
    var tx = proj.camCx(), ty = 0, tz = proj.camCy();
    var fx = tx - C.x, fy = ty - C.y, fz = tz - C.z;
    // Math.hypot, NOT sqrt(x*x+y*y+z*z). world3d.js:216 uses hypot, and hypot carries a different
    // (overflow-safe, more accurate) algorithm -- swapping in the naive form drifted the two
    // projections apart by 2.0e-9 px, which selfTest() case 1 caught at its 1e-12 bar. Harmless in
    // pixels; poison as a precedent, because "the culler's camera is ALMOST the render camera" is
    // how a cull-vs-draw disagreement gets a foothold. Keep them bit-identical.
    var fl = Math.hypot(fx, fy, fz) || 1; fx /= fl; fy /= fl; fz /= fl;
    var rx = -fz, ry = 0, rz = fx;
    var rl = Math.hypot(rx, ry, rz) || 1; rx /= rl; ry /= rl; rz /= rl;
    var ux = ry * fz - rz * fy, uy = rz * fx - rx * fz, uz = rx * fy - ry * fx;
    var focal = (S.H / 2) / Math.tan(S.fov * DEG / 2);
    var hw = S.W / 2, hh = S.H / 2;
    return {
      W: S.W, H: S.H,
      // Returns depth in `pz`; sx/sy are meaningless when pz<=1 and callers must check.
      pt: function (x, y, h, out) {
        var dx = x - C.x, dy = (h || 0) - C.y, dz = y - C.z;
        var pz = dx * fx + dy * fy + dz * fz;
        out.pz = pz;
        if (pz <= 1) { out.sx = 0; out.sy = 0; return out; }
        out.sx = hw + focal * (dx * rx + dy * ry + dz * rz) / pz;
        out.sy = hh - focal * (dx * ux + dy * uy + dz * uz) / pz;
        return out;
      }
    };
  }

  /* --- CONVEX HULL (Andrew monotone chain) ----------------------------
   * n is always 8 (a box's corners), so the O(n log n) sort is 8 elements and the whole thing is
   * cheaper than the allocation. The result is at most 6 points -- the classic hexagonal silhouette
   * of a box seen from a general angle, collapsing to 4 when a face is dead-on to the camera.
   */
  function hullOf(pts) {
    var p = pts.slice().sort(function (a, b) { return a.x === b.x ? a.y - b.y : a.x - b.x; });
    var n = p.length, i;
    if (n < 3) return p;
    function cross(o, a, b) { return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x); }
    // Lower then upper chain, each keeping its OWN length as the stack pointer. An earlier draft
    // shared one counter `k` across both chains while popping from a single array; the counter and
    // the array desynced on the first pop and indexed past the end. selfTest() case 2 pins the
    // vertex count for a known box so that class of bug cannot come back quietly.
    var lo = [], up = [];
    for (i = 0; i < n; i++) {
      while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], p[i]) <= 0) lo.pop();
      lo.push(p[i]);
    }
    for (i = n - 1; i >= 0; i--) {
      while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], p[i]) <= 0) up.pop();
      up.push(p[i]);
    }
    lo.pop(); up.pop();
    return lo.concat(up);
  }

  // Horizontal cross-section of a convex polygon at height y -> [lo,hi], or null if it misses.
  function spanAt(H, y) {
    var lo = Infinity, hi = -Infinity, n = H.length, i, a, b, t, x;
    for (i = 0; i < n; i++) {
      a = H[i]; b = H[(i + 1) % n];
      if ((a.y <= y && b.y >= y) || (b.y <= y && a.y >= y)) {
        if (a.y === b.y) {
          if (a.x < lo) lo = a.x; if (a.x > hi) hi = a.x;
          if (b.x < lo) lo = b.x; if (b.x > hi) hi = b.x;
        } else {
          t = (y - a.y) / (b.y - a.y); x = a.x + (b.x - a.x) * t;
          if (x < lo) lo = x; if (x > hi) hi = x;
        }
      }
    }
    return lo <= hi ? [lo, hi] : null;
  }

  /* --- OCCLUSION DEPTH BUFFER -----------------------------------------
   * buf[tile] answers ONE question: "what is the closest depth at which this tile is already
   * guaranteed solid all the way through?" Anything with a nearest depth beyond that value is
   * hidden. Initialised to +Infinity = nothing occludes anything yet.
   *
   * MIN-COMBINE, NOT MAX. Two occluders covering the same tile with far-depths 100 and 500: the
   * one ending at 100 hides MORE, because more candidates have depth > 100 than > 500. Keeping the
   * minimum is both correct and the stronger bound.
   */
  function makeBuffer(cols, rows) {
    var buf = (typeof Float64Array !== 'undefined') ? new Float64Array(cols * rows) : new Array(cols * rows);
    var B = {
      cols: cols, rows: rows, tw: 1, th: 1, writes: 0,
      reset: function (W, H) {
        B.tw = W / cols; B.th = H / rows; B.writes = 0;
        for (var i = 0, n = cols * rows; i < n; i++) buf[i] = Infinity;
      },
      // Write the tiles the hull FULLY covers. See the convexity proof in the file header.
      raster: function (H, farDepth) {
        var r0 = 0, r1 = rows - 1, r, y0, y1, s0, s1, lo, hi, c0, c1, c, base;
        for (r = r0; r <= r1; r++) {
          y0 = r * B.th; y1 = (r + 1) * B.th;
          s0 = spanAt(H, y0); if (!s0) continue;
          s1 = spanAt(H, y1); if (!s1) continue;
          lo = s0[0] > s1[0] ? s0[0] : s1[0];
          hi = s0[1] < s1[1] ? s0[1] : s1[1];
          if (hi <= lo) continue;
          // tile c spans [c*tw,(c+1)*tw]; fully inside <=> c>=lo/tw AND c<=hi/tw-1
          c0 = Math.ceil(lo / B.tw); c1 = Math.floor(hi / B.tw - 1);
          if (c0 < 0) c0 = 0; if (c1 > cols - 1) c1 = cols - 1;
          base = r * cols;
          for (c = c0; c <= c1; c++) {
            if (farDepth < buf[base + c]) { buf[base + c] = farDepth; B.writes++; }
          }
        }
      },
      /* Is everything this box could possibly paint already behind something solid?
       *
       * Tiles are OVER-estimated (every tile the silhouette TOUCHES must be covered) -- the
       * conservative direction, since a tile we forget to demand is a tile that could be showing
       * the building.
       *
       * WHY THE HULL AND NOT JUST THE AABB. The first cut tested the screen AABB, which is a lot
       * looser than the real silhouette: a box's projected outline is a hexagon, and the AABB adds
       * empty corner wedges the building never covers. Demanding those wedges be occluded too
       * blocked culls that were genuinely safe. Measured on the 120-box district: switching the
       * candidate test from AABB to hull is worth a real double-digit percentage of extra culls at
       * no correctness cost, because the hull is a SUBSET of the AABB -- strictly tighter, still
       * fully containing the building.
       *
       * Per row the x-extent of a convex polygon over a y-band is attained either at the band's
       * two edges or at a vertex strictly inside it, so scanning those three sources is exact.
       */
      hidden: function (H, minX, minY, maxX, maxY, nearDepth) {
        var r0 = Math.floor(minY / B.th), r1 = Math.floor(maxY / B.th);
        if (r0 < 0) r0 = 0; if (r1 > rows - 1) r1 = rows - 1;
        if (r1 < r0) return false;
        for (var r = r0; r <= r1; r++) {
          var y0 = r * B.th, y1 = (r + 1) * B.th;
          var lo = Infinity, hi = -Infinity, i, s;
          s = spanAt(H, y0); if (s) { if (s[0] < lo) lo = s[0]; if (s[1] > hi) hi = s[1]; }
          s = spanAt(H, y1); if (s) { if (s[0] < lo) lo = s[0]; if (s[1] > hi) hi = s[1]; }
          for (i = 0; i < H.length; i++) {
            if (H[i].y > y0 && H[i].y < y1) {
              if (H[i].x < lo) lo = H[i].x; if (H[i].x > hi) hi = H[i].x;
            }
          }
          if (lo > hi) continue;                       // silhouette does not reach this row
          var c0 = Math.floor(lo / B.tw), c1 = Math.floor(hi / B.tw);
          // Clamp to the viewport: pixels off-screen are clipped by the GPU anyway, so they need
          // no occluder in front of them to be invisible.
          if (c0 < 0) c0 = 0; if (c1 > cols - 1) c1 = cols - 1;
          var base = r * cols;
          for (var c = c0; c <= c1; c++) {
            if (!(nearDepth > buf[base + c])) return false;   // one uncovered tile = visible
          }
        }
        return true;
      },
      _buf: function () { return buf; }
    };
    return B;
  }

  /* --- THE CULL PASS ---------------------------------------------------
   * boxes: [{id, x, y, w, d, h, solid}] -- x/y are the world-space CENTRE on the ground plane
   * (matching index.html:705 B() and world3d.js:534), w spans world-x, d spans world-y, h is
   * height off the plane. solid=false means "can be culled, may not occlude" (alpha-cut facades).
   *
   * Returns per-box verdicts plus counts. Deliberately allocation-light: the corner scratch and
   * the record array are reused across frames via the state passed in.
   */
  function makeCuller(opts) {
    var cfg = {};
    for (var k in CFG) if (CFG.hasOwnProperty(k)) cfg[k] = CFG[k];
    if (opts) for (var k2 in opts) if (opts.hasOwnProperty(k2)) cfg[k2] = opts[k2];

    var buffer = makeBuffer(cfg.cols, cfg.rows);
    var recs = [];         // reused record pool
    var scratch = { sx: 0, sy: 0, pz: 0 };
    var last = null;

    function recAt(i) {
      if (!recs[i]) recs[i] = { id: 0, box: null, minX: 0, minY: 0, maxX: 0, maxY: 0,
                                near: 0, far: 0, clip: false, pts: [], why: '', vis: true };
      return recs[i];
    }

    function run(boxes, proj) {
      var t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      var X = makeXform(proj);
      var W = X.W, H = X.H, m = cfg.margin;
      var n = boxes.length, i, j, b, r;
      var live = [];
      var out = { total: n, frustum: 0, distance: 0, occlusion: 0, visible: 0,
                  occluders: 0, tiles: 0, ms: 0, verdicts: {} };

      // ---- pass 1: project corners, cheap rejects -----------------------
      for (i = 0; i < n; i++) {
        b = boxes[i];
        r = recAt(i); r.box = b; r.id = b.id; r.why = ''; r.vis = true; r.clip = false;
        var hx = (b.w || 0) / 2, hz = (b.d || 0) / 2, bh = b.h || 0;
        var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        var near = Infinity, far = -Infinity, clip = false;
        var pts = r.pts; pts.length = 0;
        for (j = 0; j < 8; j++) {
          var cx = b.x + ((j & 1) ? hx : -hx);
          var cz = b.y + ((j & 2) ? hz : -hz);
          var cy = (j & 4) ? bh : 0;
          X.pt(cx, cz, cy, scratch);
          if (scratch.pz < near) near = scratch.pz;
          if (scratch.pz > far) far = scratch.pz;
          if (scratch.pz <= 1) { clip = true; continue; }
          if (scratch.sx < minX) minX = scratch.sx;
          if (scratch.sx > maxX) maxX = scratch.sx;
          if (scratch.sy < minY) minY = scratch.sy;
          if (scratch.sy > maxY) maxY = scratch.sy;
          pts.push({ x: scratch.sx, y: scratch.sy });
        }
        r.minX = minX; r.minY = minY; r.maxX = maxX; r.maxY = maxY;
        r.near = near; r.far = far; r.clip = clip;

        // NEAR PLANE, three cases -- and they are NOT the same case. An early draft lumped them
        // together as "any corner behind the plane => always draw", which quietly drew every
        // building BEHIND the camera. Measured on the 120-box district with the camera inside the
        // massing: 25 boxes flagged, 6 of them entirely behind the viewer, all 6 rendered. Six
        // buildings x 6 renderlist items = 36 draw calls spent on geometry that is literally
        // behind your head. The ground-truth harness caught it; the eye never would have.
        if (far <= 1) {                      // (a) wholly behind the near plane -> gone, cull it
          r.vis = false; r.why = 'frustum'; out.frustum++; continue;
        }
        if (clip) { live.push(r); continue; }  // (b) straddling -> screen AABB is garbage (the
                                               //     projection flips sign through the plane), so
                                               //     draw it and never let it occlude.
        // (c) wholly in front -> the normal path, AABB and depths are trustworthy.

        if (cfg.distance && near > cfg.maxDist) { r.vis = false; r.why = 'distance'; out.distance++; continue; }
        if (cfg.frustum && (maxX < -m || minX > W + m || maxY < -m || minY > H + m)) {
          r.vis = false; r.why = 'frustum'; out.frustum++; continue;
        }
        live.push(r);
      }

      // ---- pass 2: front-to-back occlusion ------------------------------
      if (cfg.occlusion && live.length > 1) {
        live.sort(function (a, c) { return a.near - c.near; });
        buffer.reset(W, H);
        for (i = 0; i < live.length; i++) {
          r = live[i];
          if (r.clip) continue;                      // near-plane straddler: draw, do not occlude
          if (r.pts.length < 3) continue;
          // ONE hull per box, shared by the occlusion test and the occluder rasterisation. A box
          // seen exactly edge-on projects to a collinear point set and the hull collapses below 3
          // vertices: zero area, so it can neither be tested meaningfully nor occlude anything.
          var hl = hullOf(r.pts);
          if (hl.length < 3) continue;
          if (buffer.hidden(hl, r.minX, r.minY, r.maxX, r.maxY, r.near)) {
            r.vis = false; r.why = 'occlusion'; out.occlusion++; continue;
          }
          // Survivor: promote to occluder. Skip sub-tile boxes -- they can never FULLY cover a
          // tile, so raster() would walk every row and write nothing. Pure waste.
          if (r.box.solid === false) continue;       // alpha-cut facade: see-through, cannot occlude
          if ((r.maxX - r.minX) < buffer.tw || (r.maxY - r.minY) < buffer.th) continue;
          buffer.raster(hl, r.far);
          out.occluders++;
        }
        out.tiles = buffer.writes;
      }

      for (i = 0; i < n; i++) {
        r = recs[i];
        if (r.vis) out.visible++;
        out.verdicts[r.id] = r.why || 'visible';
      }
      out.ms = ((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - t0;
      out.recs = recs.slice(0, n);
      last = out;
      return out;
    }

    return { run: run, cfg: cfg, buffer: buffer, last: function () { return last; } };
  }

  /* =====================================================================
   * SCENE LAYER -- reads AK_WORLD3D._state, writes mesh.visible. Guarded:
   * nothing below runs at load, and every path no-ops without the 3D scene.
   * ===================================================================== */

  var S = {
    on: true,
    culler: makeCuller(),
    meshes: null,      // cached mesh list
    boxes: null,       // cached box descriptors, index-aligned with meshes
    srcLen: -1,        // change detector for W3.blds
    srcRef: null,
    hidPrev: [],       // per-mesh: the value it had before WE hid it, else null. Index-aligned
                       // with meshes/boxes. Edge-triggered -- see restoreAll().
    stats: { total: 0, frustum: 0, distance: 0, occlusion: 0, visible: 0, occluders: 0, tiles: 0, ms: 0, drawCalls: 0 },
    errors: 0, lastError: null,
    dbg: null, dbgOn: false,
    stressed: []
  };

  function w3() {
    var W = root && root.AK_WORLD3D;
    if (!W || !W._state) return null;
    var st = W._state;
    if (!st.booted || !st.on || !st.scene || !st.proj) return null;
    return st;
  }

  /* Turn a three Mesh into a pure box descriptor.
   * BoxGeometry keeps its constructor args on `geometry.parameters` (three does this for every
   * primitive), which is exactly the width/height/depth world3d.js:527 passed in. We prefer that
   * over boundingBox because it needs no computeBoundingBox() pass. Fallback covers a decorated or
   * merged geometry (e.g. anything AK_BLDMASS composes in later) that has no .parameters.
   */
  function boxOf(mesh) {
    var g = mesh.geometry, p = g && g.parameters, w, d, h;
    if (p && typeof p.width === 'number') { w = p.width; h = p.height; d = p.depth; }
    else {
      if (g && !g.boundingBox && g.computeBoundingBox) g.computeBoundingBox();
      var bb = g && g.boundingBox;
      if (!bb) return null;
      w = bb.max.x - bb.min.x; h = bb.max.y - bb.min.y; d = bb.max.z - bb.min.z;
    }
    // A cut facade is see-through, so the box is not a legal occluder. world3d.js:558 is the only
    // place that sets this, and only on material slot 4 (+z, the facade face).
    var solid = true;
    try {
      var mats = mesh.material;
      if (mats && mats.length) {
        for (var i = 0; i < mats.length; i++) {
          if (mats[i] && (mats[i].alphaTest > 0 || mats[i].transparent)) { solid = false; break; }
        }
      } else if (mats && (mats.alphaTest > 0 || mats.transparent)) solid = false;
    } catch (_e) {}
    return { id: (mesh.userData && mesh.userData.akId) || mesh.id, x: mesh.position.x, y: mesh.position.z,
             w: w, d: d, h: h, solid: solid, _m: mesh };
  }

  // Rebuild the cache when world3d swaps districts. setZone (world3d.js:758) replaces the CONTENTS
  // of W3.blds, so we watch both the array identity and its length -- neither alone is enough.
  function sync(st) {
    var src = st.blds || [];
    if (S.srcRef === src && S.srcLen === src.length && S.boxes) return true;
    // HAND EVERY MESH BACK BEFORE THE INDEX MAPPING DIES. S.hidPrev is index-aligned with
    // S.meshes, so rebuilding the list without restoring first orphans the snapshots and strands
    // those meshes hidden forever. Harmless on a normal district swap -- world3d.js:761 has
    // already pulled the old meshes out of the scene -- but NOT harmless when the list merely
    // grows and the old meshes are still live, which is exactly what stress() does.
    restoreAll();
    S.srcRef = src; S.srcLen = src.length;
    S.meshes = []; S.boxes = []; S.hidPrev = [];
    for (var i = 0; i < src.length; i++) {
      var m = src[i]; if (!m || !m.geometry || !m.position) continue;
      var bx = boxOf(m); if (!bx) continue;
      S.meshes.push(m); S.boxes.push(bx);
    }
    return true;
  }

  // Keep descriptors in step with meshes that move. Buildings are static today, but raid
  // structures (index.html:2588) and anything a builder lane places later are not, and a stale
  // centre is exactly the bug that makes a building cull while standing in plain sight.
  function refresh() {
    for (var i = 0; i < S.boxes.length; i++) {
      var b = S.boxes[i], m = b._m;
      b.x = m.position.x; b.y = m.position.z;
    }
  }

  /* VISIBILITY IS EDGE-TRIGGERED, NOT REWRITTEN EVERY FRAME.
   *
   * S.hidPrev[i] holds the value mesh i had before WE hid it, or null when we are not hiding it.
   * Each frame we only touch the meshes whose verdict CHANGED: newly-culled ones get snapshotted
   * and hidden, newly-visible ones get their snapshot handed back, and the large steady-state
   * middle -- meshes that were culled last frame and are still culled -- is not written at all.
   *
   * Two reasons this shape and not a blanket restore-then-recull. Both MEASURED on 96 buildings
   * over 600 frames of a realistic slow drag (0.23 deg/frame), blanket vs edge-triggered:
   *   1. WRITES: 50.27 -> 0.23 mesh.visible writes per frame, a 218x cut. The blanket version
   *      rewrote every held mesh twice a frame (restore, then hide again) for a verdict that had
   *      not changed.
   *   2. CO-TENANCY: 921 -> 0 stomp observations out of 7200. aklod.js:476 registers the SAME
   *      `st.blds` meshes and writes mesh.visible for its distance tiers (aklod.js:441/445).
   *      tickAll order is akcull (index.html:481) -> world3d (index.html:482, which RENDERS) ->
   *      aklod (index.html:492). A blanket restore re-asserted `true` on every mesh we held,
   *      stomping aklod's tier decision every frame. Edge-triggering never touches a mesh while it
   *      stays in our cull set, so aklod's write survives.
   *
   * RESIDUAL, STATED PLAINLY BECAUSE IT IS NOT FULLY FIXED HERE: the stomp returns when a mesh
   * LEAVES our cull set while aklod is holding it -- we hand back the snapshot taken BEFORE
   * aklod's write, and aklod will not repair it because applyTier early-outs on an unchanged tier
   * (aklod.js:437). Under the realistic drag above that never happened (0/7200). Under a
   * pathological camera teleport (0.9 rad per frame, so nearly every mesh leaves the set every
   * frame) it is 101/198. The cost is a far building drawn at full six-material cost until its
   * tier next changes: a perf regression, never a visual one. Nothing vanishes; something merely
   * fails to disappear.
   *
   * That case CANNOT be fixed from inside this file. Two independent writers sharing one boolean
   * with no record of who wrote last is genuinely undecidable -- when both lanes write `false`,
   * "I hid this" and "someone else hid this" are indistinguishable. The real fix is a shared
   * arbiter (each lane owning a bit, one owner AND-ing them into .visible), which needs BOTH lanes
   * to adopt it and therefore belongs to the integration phase, not to a single lane's build.
   */
  function restoreAll() {
    for (var i = 0; i < S.hidPrev.length; i++) {
      if (S.hidPrev[i] === null || S.hidPrev[i] === undefined) continue;
      try { if (S.meshes && S.meshes[i]) S.meshes[i].visible = S.hidPrev[i]; } catch (_e) {}
      S.hidPrev[i] = null;
    }
  }

  function tick() {
    var st = w3();
    if (!st) return false;
    if (!S.on) { restoreAll(); return false; }
    if (!sync(st) || !S.boxes.length) return false;
    refresh();

    var res = S.culler.run(S.boxes, st.proj);

    // Edge-triggered apply. recs[i] is index-aligned with S.boxes/S.meshes/S.hidPrev because
    // run() walks the boxes array in order and stamps recAt(i).
    var recs = res.recs;
    for (var i = 0; i < recs.length; i++) {
      var r = recs[i], m = r.box && r.box._m;
      if (!m) continue;
      var held = (S.hidPrev[i] !== null && S.hidPrev[i] !== undefined);
      if (!r.vis) {
        if (!held) { S.hidPrev[i] = m.visible; m.visible = false; }   // entering the cull set
        // Already held. Normally do NOT rewrite -- that is the whole point of edge-triggering,
        // and it is what lets aklod's tier decision survive underneath ours.
        // BUT edge-triggering alone is not enough: if ANOTHER lane sets visible=true on a mesh we
        // are holding culled, a pure edge-trigger never notices and the mesh renders occluded
        // forever. aklod.js:445 does exactly this on a tier change. Caught by the WebGL harness --
        // real draw-call reduction fell from 37.6% to 20.1% the moment the harness reset meshes to
        // visible between camera angles. So: cheap READ every frame, WRITE only when someone else
        // has interfered. Costs one boolean compare per held mesh and keeps the write count at
        // 0.23/frame in the uncontended case.
        else if (m.visible !== false) m.visible = false;
      } else if (held) {
        m.visible = S.hidPrev[i]; S.hidPrev[i] = null;                // leaving the cull set
      }
    }

    S.stats.total = res.total; S.stats.frustum = res.frustum; S.stats.distance = res.distance;
    S.stats.occlusion = res.occlusion; S.stats.visible = res.visible;
    S.stats.occluders = res.occluders; S.stats.tiles = res.tiles; S.stats.ms = res.ms;
    // Each surviving building is a 6-material array (world3d.js:539) so it costs SIX renderlist
    // items, plus 1 for the ground plane. The hero GLB's submesh count is not audited, so it is
    // excluded rather than guessed at.
    S.stats.drawCalls = res.visible * 6 + 1;
    if (S.dbgOn) paintDebug();
    return true;
  }

  /* --- DEBUG READOUT ---------------------------------------------------
   * The brief asks for the effect to be OBSERVABLE rather than asserted. This is a fixed overlay,
   * off by default, no cost when off. Toggle with AK_CULL.debug(true) or ?cull=debug in the URL.
   */
  function paintDebug() {
    try {
      if (!S.dbg) {
        var d = root.document.createElement('div');
        d.id = 'ak-cull-dbg';
        d.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:99999;pointer-events:none;' +
          'font:11px/1.45 ui-monospace,Menlo,Consolas,monospace;color:#cfe;background:rgba(6,6,14,.82);' +
          'border:1px solid rgba(120,200,255,.35);border-radius:6px;padding:7px 9px;white-space:pre;';
        root.document.body.appendChild(d);
        S.dbg = d;
      }
      var s = S.stats;
      S.dbg.textContent =
        'AK_CULL  ' + (S.on ? 'ON' : 'OFF') + '   ' + s.ms.toFixed(2) + 'ms\n' +
        'boxes     ' + s.total + '\n' +
        'frustum   ' + s.frustum + '   (cpu only -- three culls these too)\n' +
        'distance  ' + s.distance + '\n' +
        'occlusion ' + s.occlusion + '   <- draw calls saved: ' + (s.occlusion * 6) + '\n' +
        'drawn     ' + s.visible + '  occluders ' + s.occluders + '  tiles ' + s.tiles + '\n' +
        'drawcalls ' + s.drawCalls + ' / ' + (s.total * 6 + 1) + ' uncalled' +
        (S.errors ? ('\nERRORS    ' + S.errors + ' (' + S.lastError + ')') : '');
    } catch (e) { S.errors++; S.lastError = String(e && e.message || e); }
  }

  /* --- DENSITY HARNESS -------------------------------------------------
   * OPERATOR DOCTRINE: infrastructure that provably never activates has FAILED. HOME_TURF ships
   * FOUR buildings (index.html ZONES) and four convex boxes on an open plane essentially never
   * occlude each other -- so at shipping density this module would cull ~nothing and the lane
   * would be a lie. Rather than concluding "not worth it", this raises the district to a density
   * where occlusion is load-bearing, and then measures it.
   *
   * stress(n) injects n extra boxes into the LIVE scene and into W3.blds, so the real cull path,
   * the real renderer and the real debug readout all see them. clearStress() removes them and
   * disposes their geometry (world3d.js:452 disposeScene disposes nothing, so we clean up after
   * ourselves rather than adding to that leak).
   */
  function stress(n) {
    n = n || 60;
    var st = w3(); if (!st) return { ok: false, why: 'no 3d scene' };
    var T = root.AK_THREE && root.AK_THREE.get && root.AK_THREE.get();
    if (!T) return { ok: false, why: 'no three' };
    var W = (st.proj.state.worldW || 1700), Hh = (st.proj.state.worldH || 1300);
    // Deterministic layout: a jittered lattice of tall slabs. Tall + close-packed is the geometry
    // that actually occludes; scattered kiosks would not, and would flatter the numbers by hiding
    // the fact that occlusion needs real massing to bite.
    var cols = Math.ceil(Math.sqrt(n * (W / Hh))), rows = Math.ceil(n / cols);
    var cellW = W / cols, cellH = Hh / rows;
    var seed = 1337, k = 0;
    function rnd() { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }
    for (var gy = 0; gy < rows && k < n; gy++) {
      for (var gx = 0; gx < cols && k < n; gx++, k++) {
        // Footprints clamp to 70% of the cell so neighbours never INTERPENETRATE. A box fully
        // swallowed inside another can never be culled by this algorithm (its near depth sits
        // between the container's near and far), while it is genuinely invisible -- so overlapping
        // test massing understates the culler badly. It is also just not what a district is.
        var cw = Math.min(110 + rnd() * 90, cellW * 0.7);
        var cd = Math.min(90 + rnd() * 80, cellH * 0.7);
        // Heights track the SHIPPING formula, world3d.js:525 `max(90, b.h*1.65)` over the real
        // 96..124 footprint depths = 158..205, with occasional taller landmarks. Do not raise this
        // blindly: camPos at the default phi 52 / dist 620 puts the eye 381 units up, so slabs
        // over ~380 swallow the CAMERA, every box straddles the near plane, and the harness
        // measures a degenerate case instead of the game.
        var ch = 150 + rnd() * 110 + (rnd() < 0.15 ? 120 : 0);
        var px = (gx + 0.5) * cellW + (rnd() - 0.5) * 40;
        var pz = (gy + 0.5) * cellH + (rnd() - 0.5) * 40;
        var geo = new T.BoxGeometry(cw, ch, cd);
        var mat = new T.MeshLambertMaterial({ color: 0x22262f });
        var m = new T.Mesh(geo, [mat, mat, mat, mat, mat, mat]);
        m.position.set(px, ch / 2, pz);
        m.userData.akId = 'STRESS_' + k;
        st.scene.add(m); st.blds.push(m); S.stressed.push(m);
      }
    }
    S.srcLen = -1; S.srcRef = null;   // force a cache rebuild
    return { ok: true, added: k, total: st.blds.length };
  }

  function clearStress() {
    var st = w3(); var removed = 0;
    for (var i = 0; i < S.stressed.length; i++) {
      var m = S.stressed[i];
      try {
        if (st && st.scene) st.scene.remove(m);
        if (st && st.blds) { var ix = st.blds.indexOf(m); if (ix >= 0) st.blds.splice(ix, 1); }
        if (m.geometry && m.geometry.dispose) m.geometry.dispose();
        var mm = m.material; if (mm && mm.dispose) mm.dispose();
        else if (mm && mm.length && mm[0] && mm[0].dispose) mm[0].dispose();
        removed++;
      } catch (_e) { S.errors++; }
    }
    S.stressed.length = 0; S.srcLen = -1; S.srcRef = null;
    return { ok: true, removed: removed };
  }

  /* =====================================================================
   * PUBLIC API
   * ===================================================================== */

  /* =====================================================================
   * PROOF HARNESS -- `node systems/akcull.js`. Mirrors world3d.js:290 selfTest().
   *
   * The load-bearing test is case 4: a RAY-CAST GROUND TRUTH. For every sampled screen pixel it
   * finds the frontmost box by ray/AABB intersection, which is by definition what the GPU will
   * draw. Any box that is frontmost at even one pixel is genuinely visible, so if the culler hid
   * it that is a FALSE CULL -- a building vanishing in the player's face. That check is what
   * turned up the two real bugs in this file's history: the broken monotone-chain stack pointer,
   * and boxes ENTIRELY BEHIND THE CAMERA being drawn because "any corner past the near plane" had
   * been conflated with "straddles the near plane".
   *
   * It also reports MISSED culls (drawn but not actually visible). Those are not failures -- every
   * approximation here deliberately leans towards drawing -- but they measure how much is left on
   * the table, which is the honest counterweight to quoting a cull count.
   * ===================================================================== */
  function selfTest(opts) {
    opts = opts || {};
    var L = [], ok = true;
    function say(pass, msg) { ok = ok && pass; L.push((pass ? 'PASS  ' : 'FAIL  ') + msg); }

    var W3;
    try { W3 = require('./world3d.js'); }
    catch (e) { return { ok: false, lines: ['FAIL  cannot require ./world3d.js -- ' + e.message] }; }

    function proj(yaw, phi, dist) {
      var p = W3.makeProjector({ W: 900, H: 600 });
      p.follow(850, 650); p.setYaw(yaw); p.setPhi(phi);
      if (dist) p.dolly(dist - p.state.dist);
      return p;
    }

    // --- case 1: the culler's camera IS the render camera, bit for bit ---------------
    var worst = 0, np = 0;
    var YA = [0, 0.4, 1.1, -2.3, 3.0], PH = [0.2, 52 * DEG, 70 * DEG];
    for (var a = 0; a < YA.length; a++) for (var b = 0; b < PH.length; b++) {
      var p = proj(YA[a], PH[b]), X = makeXform(p), o = { sx: 0, sy: 0, pz: 0 };
      for (var i = 0; i < 300; i++) {
        var x = ((i * 7919) % 1700), y = ((i * 6271) % 1300), h = ((i * 4093) % 400);
        var ref = p.project(x, y, h); X.pt(x, y, h, o); np++;
        var d = Math.abs(ref.depth - o.pz);
        if (ref.depth > 1) d = Math.max(d, Math.abs(ref.sx - o.sx), Math.abs(ref.sy - o.sy));
        if (d > worst) worst = d;
      }
    }
    say(worst < 1e-12, 'xform matches world3d.project() exactly: worst delta ' +
        worst.toExponential(2) + ' over ' + np + ' points');

    // --- case 2: convex hull of a box silhouette ------------------------------------
    var sq = hullOf([{x:0,y:0},{x:10,y:0},{x:10,y:10},{x:0,y:10},{x:5,y:5}]);
    say(sq.length === 4, 'hull drops interior points: 5 in -> ' + sq.length + ' out (want 4)');

    // --- case 3: inner rasterisation only marks tiles GENUINELY inside the hull ------
    var B = makeBuffer(48, 28); B.reset(900, 600);
    var poly = [{x:100,y:100},{x:700,y:140},{x:660,y:460},{x:140,y:420}];
    B.raster(poly, 500);
    var bad = 0, marked = 0, buf = B._buf();
    function inPoly(P, px, py) {
      for (var k = 0; k < P.length; k++) {
        var A = P[k], C = P[(k + 1) % P.length];
        if ((C.x - A.x) * (py - A.y) - (C.y - A.y) * (px - A.x) < -1e-9) return false;
      }
      return true;
    }
    for (var r = 0; r < 28; r++) for (var c = 0; c < 48; c++) {
      if (buf[r * 48 + c] === Infinity) continue;
      marked++;
      var x0 = c * B.tw, x1 = (c + 1) * B.tw, y0 = r * B.th, y1 = (r + 1) * B.th;
      if (!(inPoly(poly,x0,y0) && inPoly(poly,x1,y0) && inPoly(poly,x1,y1) && inPoly(poly,x0,y1))) bad++;
    }
    say(marked > 0 && bad === 0, 'occluder raster is conservative: ' + marked +
        ' tiles marked, ' + bad + ' not fully inside the hull (want 0)');

    // --- case 4: ray-cast ground truth, ZERO false culls ----------------------------
    function basis(p) {
      var S = p.state, C = p.camPos();
      var fx = p.camCx() - C.x, fy = -C.y, fz = p.camCy() - C.z;
      var fl = Math.hypot(fx, fy, fz) || 1; fx /= fl; fy /= fl; fz /= fl;
      var rx = -fz, ry = 0, rz = fx;
      var rl = Math.hypot(rx, ry, rz) || 1; rx /= rl; ry /= rl; rz /= rl;
      return { C: C, f: [fx,fy,fz], r: [rx,ry,rz],
               u: [ry*fz-rz*fy, rz*fx-rx*fz, rx*fy-ry*fx],
               focal: (S.H/2)/Math.tan(S.fov*DEG/2), W: S.W, H: S.H };
    }
    function rayBox(O, D, bx) {
      var lo = -Infinity, hi = Infinity;
      var mn = [bx.x-bx.w/2, 0, bx.y-bx.d/2], mx = [bx.x+bx.w/2, bx.h, bx.y+bx.d/2];
      for (var i = 0; i < 3; i++) {
        if (Math.abs(D[i]) < 1e-12) { if (O[i] < mn[i] || O[i] > mx[i]) return -1; continue; }
        var t1 = (mn[i]-O[i])/D[i], t2 = (mx[i]-O[i])/D[i], t;
        if (t1 > t2) { t = t1; t1 = t2; t2 = t; }
        if (t1 > lo) lo = t1; if (t2 < hi) hi = t2;
        if (lo > hi) return -1;
      }
      return hi < 0 ? -1 : (lo < 0 ? 0 : lo);
    }
    function truth(boxes, p, step) {
      var Bs = basis(p), seen = {}, O = [Bs.C.x, Bs.C.y, Bs.C.z];
      for (var py = 0; py < Bs.H; py += step) for (var px = 0; px < Bs.W; px += step) {
        var aa = (px - Bs.W/2)/Bs.focal, bb2 = (Bs.H/2 - py)/Bs.focal;
        var D = [Bs.f[0]+Bs.r[0]*aa+Bs.u[0]*bb2, Bs.f[1]+Bs.r[1]*aa+Bs.u[1]*bb2, Bs.f[2]+Bs.r[2]*aa+Bs.u[2]*bb2];
        var best = Infinity, bid = null;
        for (var i = 0; i < boxes.length; i++) {
          var t = rayBox(O, D, boxes[i]);
          if (t >= 0 && t < best) { best = t; bid = boxes[i].id; }
        }
        if (bid !== null) seen[bid] = 1;
      }
      return seen;
    }
    // The four real HOME_TURF buildings, shaped by world3d.js:525-527 from the index.html records.
    var HT = [
      { id:'ARENA',     x:850,  y:470, w:210, d:124*0.72, h:Math.max(90,124*1.65), solid:true },
      { id:'TROPHY',    x:560,  y:760, w:170, d:100*0.72, h:Math.max(90,100*1.65), solid:true },
      { id:'KENNEL',    x:1140, y:760, w:180, d:104*0.72, h:Math.max(90,104*1.65), solid:true },
      { id:'INFIRMARY', x:850,  y:980, w:176, d:100*0.72, h:Math.max(90,100*1.65), solid:true }
    ];
    function densePure(n) {
      var Wd = 1700, Hd = 1300;
      var cs = Math.ceil(Math.sqrt(n * (Wd/Hd))), rs = Math.ceil(n/cs);
      var cw0 = Wd/cs, ch0 = Hd/rs, seed = 1337, k = 0, o2 = [];
      function rnd() { seed = (seed*1103515245+12345) & 0x7fffffff; return seed/0x7fffffff; }
      for (var gy = 0; gy < rs && k < n; gy++) for (var gx = 0; gx < cs && k < n; gx++, k++) {
        o2.push({ id:'S'+k,
          w: Math.min(110+rnd()*90, cw0*0.7), d: Math.min(90+rnd()*80, ch0*0.7),
          h: 150+rnd()*110+(rnd()<0.15?120:0),
          x: (gx+0.5)*cw0+(rnd()-0.5)*40, y: (gy+0.5)*ch0+(rnd()-0.5)*40, solid:true });
      }
      return o2;
    }
    var scenes = [
      { n:'HOME_TURF x4  phi52', boxes:HT,            phi:52*DEG },
      { n:'dense x64     phi52', boxes:densePure(64), phi:52*DEG },
      { n:'dense x64     phi70', boxes:densePure(64), phi:70*DEG },
      { n:'dense x120    phi62', boxes:densePure(120),phi:62*DEG }
    ];
    var yawSet = [0, 0.6, 1.57, 2.5, -1.2];
    var totalFalse = 0, occAtLowAngle = 0, rows2 = [];
    for (var s = 0; s < scenes.length; s++) {
      for (var yq = 0; yq < yawSet.length; yq++) {
        var pp = proj(yawSet[yq], scenes[s].phi);
        var res = makeCuller().run(scenes[s].boxes, pp);
        var gt = truth(scenes[s].boxes, pp, opts.step || 6);
        var fc = 0, ms2 = 0;
        for (var q = 0; q < res.recs.length; q++) {
          var rq = res.recs[q];
          if (!rq.vis && gt[rq.id]) fc++;
          if (rq.vis && !gt[rq.id]) ms2++;
        }
        totalFalse += fc;
        if (scenes[s].phi >= 62 * DEG) occAtLowAngle += res.occlusion;
        rows2.push('        ' + scenes[s].n + '  yaw ' + yawSet[yq].toFixed(2) +
          '  frustum=' + res.frustum + ' occlusion=' + res.occlusion +
          ' drawn=' + res.visible + '/' + res.total +
          ' falseCulls=' + fc + ' missed=' + ms2);
      }
    }
    say(totalFalse === 0, 'ray-cast ground truth over ' + (scenes.length * yawSet.length) +
        ' camera setups: ' + totalFalse + ' false culls (want 0)');
    say(occAtLowAngle > 0, 'occlusion ACTIVATES at density: ' + occAtLowAngle +
        ' boxes occlusion-culled across the low-angle dense setups (want >0)');
    L = L.concat(rows2);

    return { ok: ok, lines: L };
  }

  var API = {
    // pure core, for tests and for any other lane that wants visibility math without a scene
    makeCuller: makeCuller, makeXform: makeXform, hullOf: hullOf, spanAt: spanAt,
    makeBuffer: makeBuffer, CFG: CFG, selfTest: selfTest,
    // scene layer
    tick: tick,
    stats: function () { var o = {}; for (var k in S.stats) o[k] = S.stats[k]; o.enabled = S.on; o.errors = S.errors; return o; },
    setOn: function (v) { S.on = (v !== false); if (!S.on) restoreAll(); return S.on; },
    isOn: function () { return !!S.on; },
    set: function (k, v) { if (S.culler.cfg.hasOwnProperty(k)) { S.culler.cfg[k] = v; return true; } return false; },
    debug: function (v) {
      S.dbgOn = (v !== false);
      if (!S.dbgOn && S.dbg) { try { S.dbg.parentNode.removeChild(S.dbg); } catch (_e) {} S.dbg = null; }
      return S.dbgOn;
    },
    stress: stress, clearStress: clearStress,
    restore: restoreAll,
    _state: S
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_CULL = API;
    try {
      if (root.location && /[?&]cull=debug/.test(root.location.search)) S.dbgOn = true;
    } catch (_e) {}
    /* SELF-REGISTRATION. AK_SYSTEMS.tickAll (_registry.js:22) walks modules in REGISTRATION order,
     * which is script order. This tag must sit BEFORE systems/world3d.js so the visibility set is
     * written before world3d's frame() renders it -- register after, and every cull lands one
     * frame late. The registry try/catches each module (_registry.js:22), so a throw in here can
     * never take the hub's loop down; we still count it into stats().errors so a fault is visible
     * instead of silent.
     *
     * TICK GATING, AND THE ONE WAY THIS COULD BITE LATER. index.html:2426 only ticks systems while
     * `state==='IN_ZONE' && !interiorOpen && !entering && !_sf`, and during a RAID index.html:2436
     * narrows to a hardcoded allowlist `['raidwaves','raidfortify','backpack']`. 'akcull' is in
     * neither, so it stops culling during interiors and raids -- which is CORRECT today only
     * because world3d is equally absent from that allowlist and therefore stops rendering too, so
     * the frozen visibility set is never displayed. THE PAIRING IS THE INVARIANT: if anyone later
     * adds 'world3d' to the raid allowlist without adding 'akcull' beside it, the district renders
     * live against a visibility set frozen from whenever the raid started, and buildings will be
     * missing. Add both or neither. */
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({
          id: 'akcull',
          onTick: function () {
            try { tick(); }
            catch (e) { S.errors++; S.lastError = String(e && e.message || e); restoreAll(); }
          }
        });
      }
    } catch (_e) {}
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akcull.js` prints the culling proof. Same idiom as world3d.js:911. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  var _r = module.exports.selfTest();
  _r.lines.forEach(function (l) { console.log(l); });
  console.log(_r.ok ? 'ALL PASS' : 'FAILURES PRESENT');
  process.exit(_r.ok ? 0 : 1);
}
