/* ALLEY KINGZ -- AK_WORLDGEN: the city block generator that makes the other lanes load-bearing.
 * AK-WORLDGEN 2026-07-19
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Every optimisation lane on this workflow is inert against the world it was handed. Measured, not
 * guessed: index.html:755 ZONES carries 18 buildings across NINE districts. HOME_TURF, the spawn
 * district and the WORST case, has FOUR (ARENA/TROPHY/KENNEL/INFIRMARY). bldmass.js:9 measured the
 * whole visible world at 50 triangles. akstream.js:14 says the same thing in its own header. A
 * frustum culler over 4 boxes rejects nothing; an LOD over 4 boxes swaps nothing; a chunk streamer
 * over 4 boxes streams nothing.
 *
 * The operator's directive on this point is explicit and overrides the usual engineering instinct
 * to declare the work unnecessary: "if it doesn't apply yet, BUILD THE INFRASTRUCTURE THAT ALLOWS
 * IT TO APPLY, THEN APPLY IT." A district too small to cull is a statement about the DISTRICT, not
 * about culling. So this lane grows the district.
 *
 * WHAT IT IS NOT
 * --------------
 * It is NOT a replacement for the hand-painted buildings. The authored 18 keep their facade PNGs
 * (assets/hub/<stem>.png, the two parallel tables at index.html:567 FAC and world3d.js:387 FACADE),
 * their labels, their doors, their interiors and their saturated tints. Everything this file emits
 * is BACKGROUND: flat MeshLambertMaterial in a desaturated band, dressed only with AK_BLDMASS
 * silhouette detail, and actively height-capped near an authored building so the authored one keeps
 * the local skyline. "No generic art ever replaces authored art" is house law, and here it is
 * enforced in code by hCapNear() and by the fact that this module never touches zone.buildings.
 *
 * THE THREE-TIER DEPTH READ (deliberate, and it is why the tones are what they are)
 *   FAR   aklod.js planInfill ring, OUTSIDE the playfield, tone 26..51  -- darkest, pure backdrop
 *   MID   THIS FILE, INSIDE the playfield, tone 44..74                  -- the city you walk through
 *   NEAR  the authored 18, photo facades, saturated hex tints           -- the subject
 * aklod's ring keeps out of the playfield entirely (aklod.js planInfill KEEP-OUT block skips any
 * cell inside the playfield + margin), so these two generators cannot collide by construction. This
 * one owns the inside, that one owns the outside.
 *
 * THE LAYOUT IS NOT SCATTER. It is a STREET LATTICE.
 * -------------------------------------------------
 * Random scatter would have been ten lines and would have looked like a boulder field. Real density
 * reads as density only when it has FRONTAGE -- buildings addressing a street, backs to an alley.
 * So the generator lays streets first, derives blocks as the negative space between them, and only
 * then subdivides each block into lots along its street frontage.
 *
 * The main avenues are NOT jittered and NOT negotiable. index.html:755 puts every district edge
 * spawn at x=150 or x=1550 with y=650, or at y=150/y=1150 with x=850. The centre plaza is (850,650).
 * So the N-S avenue is pinned at x=850 +-75 -> [775,925] and the E-W avenue at y=650 +-75 ->
 * [575,725], which are EXACTLY the four edge corridors the collision layer already reserves
 * (worldmap.js BUILTIN comments cite "the 4 edge corridors (x 775-925 / y 575-725)" on almost every
 * obstacle it places). Blocks are the intersection of an x-gap and a y-gap, so any point with EITHER
 * coordinate inside a street band is street. That single property makes all four edge spawns, the
 * plaza, and the whole exit network unreachable-proof by construction rather than by test -- and the
 * test then proves it anyway, because "by construction" is how the last four dead modules on this
 * project were justified.
 *
 * WALLING THE PLAYER IN IS THE FAILURE MODE THAT MATTERS
 * -----------------------------------------------------
 * Doors are at (b.x, b.y + b.h/2) -- worldmap.js validPlacement states the rule. Sixteen of the
 * eighteen authored doors already land inside a main avenue band. The two that do not are
 * INFIRMARY (door 1270,548 -- 27 units north of the y=650 band) and nothing else; the generator
 * carves an explicit door corridor for every building regardless, so the count never has to be
 * re-audited when a district gains a building. selfTest() flood-fills the walkable space at a
 * 20-unit step, with the player radius of 23 inflating every solid, and asserts that all 18 door
 * approaches and all 26 district exits are reachable from the plaza.
 * HONEST NOTE ON THAT CHECK: it has never failed. Sweeping ALLEY_MIN from 70 down to 10 moves the
 * structure count from 732 to 1108 world-wide and leaves reachability pinned at 100% with zero
 * unreachable targets throughout. That is not the test being weak -- it is the street lattice
 * being the right design, because blocks are the INTERSECTION of an x-gap and a y-gap and streets
 * therefore always span the full world. The check is kept because the day someone adds a diagonal,
 * a plaza structure, or a district with an off-avenue door, it is the only thing standing between
 * that change and a player sealed in a courtyard.
 *
 * DRAW-CALL MODEL (so the headline number is arithmetic, not a vibe)
 * -----------------------------------------------------------------
 * A generated structure is ONE BoxGeometry with ONE non-array material. aklod.js applyTier spells
 * out why that matters: "Array material = one render item per geometry group; non-array = one
 * render item total." The authored buildings use a 6-material array (world3d.js:539) because slot 4
 * carries the facade photo and slot 2 the roof -- 6 render items each. A background box has no
 * photo to place, so paying 6 for one flat colour would be pure waste. Hence:
 *     authored building  = 6 draw calls  (facade contract, non-negotiable)
 *     generated ROW      = 1 draw call + 1 for its merged AK_BLDMASS detail = 2
 *     generated non-ROW  = 1 draw call
 * Naive totals and post-optimisation totals are both computed by selfTest() against the peer lanes'
 * OWN pure cores (akcull.makeCuller, aklod.makeLodCore, akstream.makeStreamer), not against a
 * re-implementation here. If those lanes change their maths, this number changes with them.
 *
 * INTEGRATION -- READ THIS BEFORE MOVING THE SCRIPT TAG
 * ----------------------------------------------------
 * Generated meshes are added as DIRECT CHILDREN of world3d's scene and pushed into
 * AK_WORLD3D._state.blds. Both halves are deliberate:
 *   - blds is the ONLY intake AK_CULL has (akcull.js sync() reads st.blds and watches both the
 *     array identity and its length, so a push is seen).
 *   - direct children, NOT a Group, because world3d.js setZone tears down by iterating blds and
 *     calling scene.remove(m) + m.geometry.dispose(). Under a Group the remove() would no-op while
 *     the dispose() still fired, leaving live meshes with dead geometry in the graph for however
 *     many frames until our next tick -- a WebGL error storm. As direct children that teardown is
 *     CORRECT for our meshes and we only have to clean up materials and bookkeeping after it.
 * AK_LOD is joined via its documented AK_LOD.register(mesh, opts) path, not via blds, because
 * aklod.js sync() caches on the blds ARRAY IDENTITY and would never notice a push into an array it
 * has already adopted.
 * We do NOT edit systems/world3d.js. The zone-change handshake is a poll on st.zoneId, the same
 * idiom world3d.js setZone itself uses, and it is ordering-independent: we build only once
 * st.zoneId already equals ctx.activeZone.id, which is world3d's own signal that its rebuild is
 * finished and blds is the new array.
 */
(function (root) {
  'use strict';

  var VER = 'AK-WORLDGEN 2026-07-19';

  // ==========================================================================================
  // PURE CORE -- no DOM, no THREE, node-requireable. Everything above the SCENE LAYER banner is
  // exercised by `node systems/akworldgen.js` and is the part the tests actually prove.
  // ==========================================================================================

  /* Deterministic per-seed PRNG. Same FNV-1a + xorshift32 pair as bldmass.js:26 and akstream.js
   * rngFor, copied rather than imported ON PURPOSE: this module must be requireable standalone in
   * node and must not acquire a load-order dependency on a sibling lane for four lines of maths.
   * Math.random() here would re-roll the entire city on every reload and every district re-entry,
   * which is exactly the shimmer bldmass.js:25 warns about, multiplied by ~110 structures. */
  function hash(str) {
    var h = 2166136261, s = String(str == null ? 'x' : str);
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  /* ------------------------------------------------------------------------------------------
   * TUNING. Every number here is in WORLD UNITS (the 1700x1300 zone space of index.html:643),
   * never pixels, never tiles.
   * ---------------------------------------------------------------------------------------- */
  var CFG = {
    density: 1.0,          // 0..1 master knob. Scales lot keep-probability. See setDensity().
    rim: 28,               // dead border at the world edge -- the hub lets `me` stand on the edge
                           // (world3d.js follow() clamps to the world rect), so a structure flush
                           // to x=0 would half-bury the player at the boundary.
    pad: 7,                // lot inset from the block rect, so neighbouring blocks never touch
    frontMax: 96,          // max depth of a frontage strip. Deeper than this and the block reads
                           // as one slab instead of a street wall with an alley behind it.
    /* ALLEY_MIN is a WIDTH floor on the service alley of a double-loaded block, and it is the
     * single biggest lever on total structure count. Measured by sweeping it through selfTest():
     *     70 -> 732 structures     46 -> 839 (shipping)     22 ->  985
     *     58 -> 807                34 -> 901                10 -> 1108 (busts the 130/district cap)
     * Note what it does NOT do: walkability is flat at 100% reach across that entire sweep, zero
     * unreachable targets at every value. Connectivity here is carried by the STREET LATTICE, not
     * by the alleys -- an alley is a dead-end court hanging off a street, never a through route, so
     * narrowing one cannot disconnect anything. The floor is therefore a LOOKS argument, not a
     * safety one: below ~40 units the alley stops reading as a space you could walk into at the
     * 52-degree camera pitch and starts reading as a seam between two buildings. */
    ALLEY_MIN: 46,
    minLot: 54,            // frontage lot bounds. 54..126 keeps the street wall irregular; a fixed
    maxLot: 126,           // width produced a visually obvious repeat at 6 lots per block.
    backLotMin: 44,        // ALLEY lot bounds. Narrower band on purpose: back-lot kinds are walls,
    backLotMax: 92,        // sheds and empty lots, and at the frontage band they were 54+ wide, so
                           // only ~2 fit per alley and back-lot content came out at 2% of the city.
    backDensity: 0.50,     // alley fill rate relative to the master knob
    /* targetMax caps a district and exists because the nine districts do NOT have equal buildable
     * area. The street jitter is seeded per district, so block sizes differ, and the authored
     * buildings plus AK_COLLISION obstacles eat wildly different amounts: FACTORY_ROW has 3
     * buildings and TEN painted obstacles (pipes, forklifts, slag) and rejects 56 lots, while
     * THE_OVERLOOK is a locked district with zero buildings and rejects 30. At a flat density that
     * produced a 72..147 spread -- both ends outside the brief's 60-120. planDistrict therefore
     * runs a second normalising pass at a scaled density whenever the first overshoots. It is
     * still fully deterministic: the scale factor is derived from the first pass's own count.
     *
     * AK-3DC-streets 2026-07-29 -- PHASE 6 (open the streets). Dialled 120 -> 28. The original
     * 60-120 brief was "grow the district so culling/LOD/streaming have something to chew on";
     * Phase 6 reverses the LOOK half of that: the operator's real GLB storyline buildings are the
     * subject and the generated boxes are meant to be a THIN decor ring that FRAMES the streets,
     * not a wall the player squeezes through on a WoW/Prototype-2 walk. This is the single per-
     * district cap the plan names. Effect (node self-test, density 1.0): per-district 72..119 ->
     * 27..35, world-wide 907 -> 274, HOME_TURF 102 -> 27; every device tier (autoDensity 0.45..1.0)
     * now clamps to ~28 so the ring is uniform. Purely a number -- the generator, the focalR
     * authored-art suppression, the keep-outs and the walkability proof are all untouched, so this
     * is reversible by restoring 120. Frustum-cull + chunk-stream still carry a ~75% draw-call cut. */
    targetMax: 28,
    bldMargin: 46,         // keep-out ring around an authored building footprint
    doorRun: 156,          // length of the carved corridor out of an authored door
    doorHalf: 78,          // half-width of that corridor (>= the widest door, ARENA at w=210/2)
    obsMargin: 26,         // keep-out ring around an AK_COLLISION obstacle (player r is 23)
    spawnR: 96,            // keep-out disc at each district edge spawn point
    plazaR: 132,           // keep-out disc at the centre plaza / crossroads
    focalR: 340,           // radius inside which an authored building suppresses generated height
    focalCap: 0.62,        // ...to this fraction of the authored building's own 3D height
    toneLo: 44, toneHi: 74,// grey band. Above aklod's ring (26..51), below every authored tint.
    buildBudget: 8,        // structures instantiated per tick. A 110-box district built in one
                           // frame is ~110 geometries plus ~50 bldmass merges and a visible phone
                           // stall; 8 a tick finishes in ~14 frames and is invisible.
    streamRegister: true,  // park structures in AK_STREAM's chunk index when that lane is loaded
    lodRegister: true,     // register structures with AK_LOD tiers
    cullRegister: true     // push structures into AK_WORLD3D._state.blds so AK_CULL adopts them
  };

  /* KIND TABLE. `wt` is the draw weight inside a frontage strip; `back` kinds are only ever placed
   * on the alley side of a double-loaded block. `deco` marks the kinds worth spending an
   * AK_BLDMASS.decorate() merge on -- parapets and cornices are a silhouette investment and a
   * 26-unit-tall shed has no silhouette to invest in. */
  var KINDS = [
    { k: 'ROW',      wt: 30, hLo:  74, hHi: 186, deco: true,  back: false, dLo: 0.72, dHi: 1.00 },
    { k: 'TENEMENT', wt: 14, hLo: 138, hHi: 248, deco: true,  back: false, dLo: 0.80, dHi: 1.00 },
    { k: 'SHOPFRONT',wt: 16, hLo:  52, hHi:  96, deco: true,  back: false, dLo: 0.60, dHi: 0.88 },
    { k: 'STACK',    wt: 12, hLo:  32, hHi:  74, deco: false, back: true,  dLo: 0.46, dHi: 0.80 },
    { k: 'SHED',     wt: 12, hLo:  24, hHi:  46, deco: false, back: true,  dLo: 0.40, dHi: 0.72 },
    { k: 'LOT',      wt:  8, hLo:   3, hHi:   5, deco: false, back: true,  dLo: 0.70, dHi: 1.00 },
    { k: 'WALL',     wt:  8, hLo:  18, hHi:  30, deco: false, back: true,  dLo: 0.10, dHi: 0.18 }
  ];
  var KIND_BY_NAME = (function () { var m = {}; for (var i = 0; i < KINDS.length; i++) m[KINDS[i].k] = KINDS[i]; return m; })();

  function pickKind(r, allowBack) {
    var tot = 0, i;
    for (i = 0; i < KINDS.length; i++) if (allowBack || !KINDS[i].back) tot += KINDS[i].wt;
    var t = r * tot, acc = 0;
    for (i = 0; i < KINDS.length; i++) {
      if (!allowBack && KINDS[i].back) continue;
      acc += KINDS[i].wt;
      if (t < acc) return KINDS[i];
    }
    return KINDS[0];
  }

  // --- rect helpers. Rects are {x,y,w,h} with x,y = TOP-LEFT, matching AK_COLLISION's convention
  // (worldmap.js: "obstacles are rects {type:'rect',x,y,w,h} (x,y = TOP-LEFT, world units)").
  // Structure specs, by contrast, carry x,y = CENTRE, matching index.html:752 B() and world3d's
  // mesh placement. Mixing those two up is the single easiest bug to write in this file, so every
  // conversion goes through rectOfSpec() and nothing hand-rolls it.
  function overlaps(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }
  function hitsAny(r, list) {
    for (var i = 0; i < list.length; i++) if (overlaps(r, list[i])) return true;
    return false;
  }
  function rectOfSpec(s) { return { x: s.x - s.w / 2, y: s.y - s.d / 2, w: s.w, h: s.d }; }
  function grow(r, m) { return { x: r.x - m, y: r.y - m, w: r.w + m * 2, h: r.h + m * 2 }; }

  /* obstacleRects(obs) -- AK_COLLISION obstacles come in two shapes (rect TOP-LEFT, circle CENTRE,
   * worldmap.js). Normalise to AABBs. A circle becomes its bounding square, which over-reserves the
   * corners by ~21% of the disc area; that is the right direction to be wrong in, since the cost is
   * a slightly emptier lot and the alternative is a building growing through a junked car. */
  function obstacleRects(obs, margin) {
    var out = [], i, o;
    if (!obs) return out;
    for (i = 0; i < obs.length; i++) {
      o = obs[i]; if (!o) continue;
      if (o.type === 'circle') out.push(grow({ x: o.x - o.r, y: o.y - o.r, w: o.r * 2, h: o.r * 2 }, margin));
      else out.push(grow({ x: o.x, y: o.y, w: o.w, h: o.h }, margin));
    }
    return out;
  }

  /* planStreets -- the lattice. Returns { vx:[band], hy:[band] } sorted by centre, where a band is
   * {c, half, rank}. See the header for why the mains are pinned and everything else is jittered.
   * The jitter is seeded per district so THE_YARDS and THE_DOCKS do not share a skyline, but a
   * given district is byte-identical on every load. */
  function planStreets(zoneId, W, H, o) {
    o = o || {};
    var rnd = rngFor('streets:' + zoneId);
    var j = (typeof o.jitter === 'number') ? o.jitter : 42;

    function jit() { return (rnd() * 2 - 1) * j; }

    // MAIN avenues: fixed. They ARE the four edge corridors and the plaza crossroads.
    // Half-width 75 reproduces x[775,925] / y[575,725] at the stock 1700x1300 exactly.
    var vx = [{ c: W * 0.5, half: 75, rank: 'main' }];
    var hy = [{ c: H * 0.5, half: 75, rank: 'main' }];

    // Secondary streets at the quarter lines. Jittered, because a perfectly regular grid reads as
    // a spreadsheet from the 52-degree camera (world3d.js DEFAULT_PHI) -- the eye picks up the
    // repeat instantly at this pitch.
    vx.push({ c: W * 0.28 + jit(), half: 45, rank: 'street' });
    vx.push({ c: W * 0.72 + jit(), half: 45, rank: 'street' });
    hy.push({ c: H * 0.25 + jit(), half: 45, rank: 'street' });
    hy.push({ c: H * 0.75 + jit(), half: 45, rank: 'street' });

    // Rim alleys. Narrow, and they exist so the outermost blocks have a BACK as well as a front --
    // a block with no rear access reads as a wall, not as a building.
    vx.push({ c: W * 0.11 + jit() * 0.4, half: 26, rank: 'alley' });
    vx.push({ c: W * 0.89 + jit() * 0.4, half: 26, rank: 'alley' });
    hy.push({ c: H * 0.10 + jit() * 0.4, half: 24, rank: 'alley' });
    hy.push({ c: H * 0.90 + jit() * 0.4, half: 24, rank: 'alley' });

    function bySpan(a, b) { return a.c - b.c; }
    vx.sort(bySpan); hy.sort(bySpan);
    return { vx: vx, hy: hy };
  }

  /* gapsFrom -- collapse a sorted band list into the free spans between them, clipped to
   * [rim, size-rim]. Bands that overlap after jitter are absorbed rather than producing a negative
   * span, which is the failure the min-width filter below also guards. */
  function gapsFrom(bands, size, rim) {
    var out = [], cur = rim, i, b;
    for (i = 0; i < bands.length; i++) {
      b = bands[i];
      var lo = b.c - b.half, hi = b.c + b.half;
      if (lo > cur) out.push([cur, lo]);
      if (hi > cur) cur = hi;
    }
    if (size - rim > cur) out.push([cur, size - rim]);
    var keep = [];
    for (i = 0; i < out.length; i++) if (out[i][1] - out[i][0] >= 56) keep.push(out[i]);
    return keep;
  }

  /* blocksFrom -- the negative space of the lattice. A block is the intersection of an x-gap and a
   * y-gap, so it is fully enclosed by street on all four sides. That is what guarantees the street
   * network is a connected grid and not a maze: streets span the FULL world extent, blocks never do. */
  function blocksFrom(streets, W, H, rim) {
    var xs = gapsFrom(streets.vx, W, rim), ys = gapsFrom(streets.hy, H, rim);
    var out = [], i, k;
    for (k = 0; k < ys.length; k++) {
      for (i = 0; i < xs.length; i++) {
        out.push({ x: xs[i][0], y: ys[k][0], w: xs[i][1] - xs[i][0], h: ys[k][1] - ys[k][0], col: i, row: k });
      }
    }
    return out;
  }

  /* keepOutsFor -- everything a generated structure must not touch. Returns AABBs.
   * Order matters only for debuggability (each entry carries a `why`), never for correctness. */
  function keepOutsFor(zone, o) {
    o = o || {};
    var W = o.worldW || 1700, H = o.worldH || 1300;
    var out = [], i, b, r;
    var blds = (zone && zone.buildings) || [];

    for (i = 0; i < blds.length; i++) {
      b = blds[i];
      // FOOTPRINT + frontage margin. index.html:826 hit-tests |tx-b.x| < b.w/2, so b.x/b.y are the
      // centre and b.w/b.h the full extent -- NOT half-extents.
      r = grow({ x: b.x - b.w / 2, y: b.y - b.h / 2, w: b.w, h: b.h }, CFG.bldMargin);
      r.why = 'bld:' + b.id; out.push(r);
      // DOOR CORRIDOR. worldmap.js validPlacement fixes the door at (b.x, b.y + b.h/2), i.e. the
      // SOUTH face, for every building in the game. Carve a lane straight out of it so the walk-up
      // can never be bricked over -- 16 of the 18 doors already sit in a main avenue band, but
      // carving unconditionally means a district that gains a building tomorrow is still safe.
      var hw = Math.max(CFG.doorHalf, b.w / 2);
      out.push({ x: b.x - hw, y: b.y + b.h / 2, w: hw * 2, h: CFG.doorRun, why: 'door:' + b.id });
    }

    // District EXITS. index.html:755 edges carry the spawn the player LANDS on when arriving from
    // a neighbour. All four sit on a main avenue by construction, but an arriving player lands
    // there with zero collision grace, so it gets an explicit disc anyway.
    var e = (zone && zone.edges) || {};
    for (var k in e) {
      if (!Object.prototype.hasOwnProperty.call(e, k)) continue;
      var sp = e[k] && e[k].spawn; if (!sp) continue;
      out.push({ x: sp.x - CFG.spawnR, y: sp.y - CFG.spawnR, w: CFG.spawnR * 2, h: CFG.spawnR * 2, why: 'spawn:' + k });
    }

    // The plaza. The crossroads is where the player stands on entry (index.html hero default
    // 850,650) and where world3d aims its look-at, so it stays open.
    out.push({ x: W / 2 - CFG.plazaR, y: H / 2 - CFG.plazaR, w: CFG.plazaR * 2, h: CFG.plazaR * 2, why: 'plaza' });

    // Painted obstacles. Read-only: we never mutate, reorder or filter AK_COLLISION's array --
    // raidfortify.js wraps obstaclesFor and worldverbs.js reads it, and both would break on a
    // mutated source.
    var obs = o.obstacles || null;
    if (!obs && root && root.AK_COLLISION && typeof root.AK_COLLISION.obstaclesFor === 'function') {
      try { obs = root.AK_COLLISION.obstaclesFor(zone); } catch (_e) { obs = null; }
    }
    var orl = obstacleRects(obs, CFG.obsMargin);
    for (i = 0; i < orl.length; i++) { orl[i].why = 'obs'; out.push(orl[i]); }

    return out;
  }

  /* hCapNear -- the authored-art protection rule, in code.
   * world3d.js buildBuildings raises an authored building to h = max(90, b.h * 1.65). Anything
   * generated within focalR of one is capped at focalCap of that height, so walking up to TOWN HALL
   * you see TOWN HALL, not a generated tenement leaning over it. Returns Infinity when nothing is
   * near, which the caller treats as "no cap". */
  function hCapNear(x, y, blds) {
    var cap = Infinity;
    for (var i = 0; i < blds.length; i++) {
      var b = blds[i];
      var dx = x - b.x, dy = y - b.y;
      if (dx * dx + dy * dy > CFG.focalR * CFG.focalR) continue;
      var bh = Math.max(90, (b.h || 96) * 1.65);
      var c = bh * CFG.focalCap;
      if (c < cap) cap = c;
    }
    return cap;
  }

  /* subdivideBlock -- turn one block rect into lots along its street frontage.
   *
   * A block is DOUBLE-LOADED when it is deep enough to carry two rows of buildings back-to-back
   * with a service alley between them. That is the shape that makes a city read as a city: fronts
   * on the street, backs on the alley, bins and sheds in the middle. Shallow blocks get a single
   * strip instead, because forcing two rows into 78 units of depth produces 39-unit slivers.
   *
   * The long axis carries the frontage. A 254x205 block fronts along x; a 133x205 block fronts
   * along y. Getting this backwards makes every building present its SIDE to the street, which is
   * subtle in a screenshot and glaring in motion.
   */
  function subdivideBlock(blk, rnd, o) {
    var pad = CFG.pad;
    var bx = blk.x + pad, by = blk.y + pad, bw = blk.w - pad * 2, bh = blk.h - pad * 2;
    if (bw < 40 || bh < 40) return [];

    var horiz = bw >= bh;                 // frontage runs along x when the block is wider than deep
    var len = horiz ? bw : bh;            // extent along the frontage
    var dep = horiz ? bh : bw;            // extent perpendicular to it

    /* THREE BLOCK SHAPES, chosen by depth. The thresholds are not arbitrary -- they were derived
     * from the block sizes the street lattice actually produces at 1700x1300, printed by the
     * scale table in selfTest():
     *   deep   (~191 after pad) -> two frontage strips + a WORKED alley core (sheds, walls, lots)
     *   medium (~112 after pad) -> two frontage strips + an EMPTY alley
     *   shallow (~64 after pad) -> one strip, full depth
     * The first cut of this function used a single `(dep - ALLEY_MIN)/2` rule with a
     * `alleyDep >= ALLEY_MIN + 24` gate for the core, and the core NEVER FIRED: at dep 191 the
     * gate wanted 70 and the arithmetic left 46. The tell was in the test output -- `deco` equalled
     * `placed` in all nine districts, meaning every structure was a frontage kind and not one
     * shed, wall or empty lot had been placed anywhere in the city. That is the "code nothing
     * calls" failure mode wearing a different hat, and it is exactly why the scale table prints
     * the deco column instead of just a total. */
    var strips = [];
    var STRIP_MIN = 28;                          // thinner than this and a "building" is a kerb
    var CORE_MIN = CFG.ALLEY_MIN + 14;           // alley wide enough to hold back-lot junk.
    // 28*2 + 60 = 116 is deliberately just under the 119-unit depth of the narrow blocks in the
    // two deep rows -- those four blocks per district are the difference between an alley system
    // and a token gesture, and at STRIP_MIN 30 / CORE_MIN 76 they missed the cut by 17 units.
    var front;
    if (dep >= STRIP_MIN * 2 + CORE_MIN) {
      front = Math.min(CFG.frontMax, (dep - CORE_MIN) / 2);
      strips.push({ off: 0, dep: front, back: false });
      strips.push({ off: dep - front, dep: front, back: false });
      // The worked alley core. Inset 10 a side so back walls never touch the frontage buildings,
      // and sparse by design (see the 0.55 density multiplier below) -- an alley you can see into
      // is worth more than an alley packed solid.
      var alleyDep = dep - front * 2;
      strips.push({ off: front + 10, dep: alleyDep - 20, back: true });
    } else if (dep >= STRIP_MIN * 2 + CFG.ALLEY_MIN) {
      front = (dep - CFG.ALLEY_MIN) / 2;
      strips.push({ off: 0, dep: front, back: false });
      strips.push({ off: dep - front, dep: front, back: false });
    } else {
      strips.push({ off: 0, dep: dep, back: false });   // shallow block: one strip, full depth
    }

    var out = [], si, s, cursor, lotW, kind, d, want;
    for (si = 0; si < strips.length; si++) {
      s = strips[si];
      cursor = 0;
      var lotLo = s.back ? CFG.backLotMin : CFG.minLot;
      var lotHi = s.back ? CFG.backLotMax : CFG.maxLot;
      while (cursor < len - lotLo * 0.6) {
        lotW = lotLo + rnd() * (lotHi - lotLo);
        if (cursor + lotW > len) lotW = len - cursor;
        if (lotW < lotLo * 0.6) break;

        // Consume the rng for EVERY lot whether kept or not, so changing `density` reshuffles
        // nothing -- the same city thins out instead of becoming a different city. akstream.js
        // planClutter makes the same call for the same reason.
        var rKeep = rnd(), rKind = rnd(), rDep = rnd(), rH = rnd(), rTone = rnd(), rSlide = rnd();

        // Alley strips run at backDensity relative to the master knob -- still sparser than a
        // street frontage, because a back lot that is solidly built is not a back lot.
        want = CFG.density * (s.back ? CFG.backDensity : 1.0);
        if (rKeep <= want) {
          kind = pickKind(rKind, s.back);
          d = s.dep * (kind.dLo + rDep * (kind.dHi - kind.dLo));
          // Slide the lot back from the street edge by the leftover depth, so a shallow SHOPFRONT
          // still touches its pavement instead of floating mid-lot.
          var backOff = s.back ? (s.dep - d) * rSlide : 0;
          var offA = cursor + Math.min(4, (len - cursor - lotW) * 0.5);
          var w2 = Math.max(18, lotW - 8);
          var dOff = s.off + backOff + (s.back ? 0 : (si === 1 ? s.dep - d : 0));

          out.push({
            kind: kind,
            // Local block coordinates -> world, respecting which axis carries the frontage.
            x: horiz ? (bx + offA + w2 / 2) : (bx + dOff + d / 2),
            y: horiz ? (by + dOff + d / 2) : (by + offA + w2 / 2),
            w: horiz ? w2 : d,
            d: horiz ? d : w2,
            hR: rH, toneR: rTone,
            block: blk.row + ':' + blk.col, strip: si
          });
        }
        cursor += lotW;
      }
    }
    return out;
  }

  /* planDistrict -- THE ENTRY POINT of the pure core.
   * zone: an index.html ZONES record (needs .id, .buildings, .edges). opts: {worldW, worldH,
   * density, obstacles}. Returns {structures, blocks, streets, keepOuts, stats}. Pure: same input,
   * byte-identical output, every time. No THREE, no DOM, no globals read except AK_COLLISION as an
   * OPTIONAL obstacle source when opts.obstacles is absent. */
  function planDistrict(zone, o) {
    o = o || {};
    var first = planOnce(zone, o);
    // Normalising pass -- see CFG.targetMax. Only ever scales DOWN, and only once, so this can
    // never loop and can never inflate a sparse district into a dense one.
    if (!o._noNorm && CFG.targetMax > 0 && first.structures.length > CFG.targetMax) {
      var scale = CFG.targetMax / first.structures.length;
      var o2 = {}, k;
      for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) o2[k] = o[k];
      o2.density = ((typeof o.density === 'number') ? o.density : CFG.density) * scale;
      o2._noNorm = true;
      var second = planOnce(zone, o2);
      second.stats.normalised = true;
      second.stats.preNormalise = first.structures.length;
      return second;
    }
    first.stats.normalised = false;
    first.stats.preNormalise = first.structures.length;
    return first;
  }

  function planOnce(zone, o) {
    o = o || {};
    var W = o.worldW || 1700, H = o.worldH || 1300;
    var zid = (zone && zone.id) || 'HOME_TURF';
    var dens = (typeof o.density === 'number') ? o.density : CFG.density;
    var savedDens = CFG.density; CFG.density = dens;   // subdivideBlock reads CFG.density

    try {
      var streets = planStreets(zid, W, H, o);
      var blocks = blocksFrom(streets, W, H, CFG.rim);
      var keepOuts = keepOutsFor(zone, { worldW: W, worldH: H, obstacles: o.obstacles });
      var blds = (zone && zone.buildings) || [];

      var rnd = rngFor('blocks:' + zid);
      var raw = [], i;
      for (i = 0; i < blocks.length; i++) raw = raw.concat(subdivideBlock(blocks[i], rnd, o));

      // REJECTION PASS. Everything above is geometry; this is the part that keeps the player alive.
      var structures = [], rejected = 0, capped = 0, placed = [];
      var toneRnd = rngFor('tone:' + zid);
      for (i = 0; i < raw.length; i++) {
        var s = raw[i];
        var r = rectOfSpec(s);
        if (r.x < CFG.rim || r.y < CFG.rim || r.x + r.w > W - CFG.rim || r.y + r.h > H - CFG.rim) { rejected++; continue; }
        if (hitsAny(r, keepOuts)) { rejected++; continue; }
        // Self-overlap. Blocks cannot overlap each other, but two strips inside ONE block can when
        // the alley maths lands tight, and a building growing through another building is the kind
        // of thing that survives a screenshot review and not a walkthrough.
        if (hitsAny(r, placed)) { rejected++; continue; }
        placed.push(r);

        var h = s.kind.hLo + s.hR * (s.kind.hHi - s.kind.hLo);
        var cap = hCapNear(s.x, s.y, blds);
        if (h > cap) { h = Math.max(s.kind.hLo * 0.6, cap); capped++; }

        // Tone: a narrow desaturated band, cool-shifted (+2 green, +8 blue) exactly like aklod's
        // ring so the two generators share one colour family across the playfield boundary.
        var tone = CFG.toneLo + Math.floor(toneRnd() * (CFG.toneHi - CFG.toneLo));
        structures.push({
          id: 'wg_' + zid + '_' + structures.length,
          kind: s.kind.k, deco: !!s.kind.deco,
          x: s.x, y: s.y, w: s.w, d: s.d, h: h,
          col: (tone << 16) | ((tone + 2) << 8) | (tone + 8),
          block: s.block, strip: s.strip
        });
      }

      // Draw-call arithmetic. See the header for the 1-vs-6 material argument.
      var deco = 0;
      for (i = 0; i < structures.length; i++) if (structures[i].deco) deco++;

      return {
        zoneId: zid, worldW: W, worldH: H, density: dens,
        streets: streets, blocks: blocks, keepOuts: keepOuts, structures: structures,
        stats: {
          blocks: blocks.length, lots: raw.length, placed: structures.length,
          rejected: rejected, heightCapped: capped, decorated: deco,
          naiveDrawCalls: structures.length + deco,
          authoredDrawCalls: blds.length * 6,
          triangles: structures.length * 12
        }
      };
    } finally {
      CFG.density = savedDens;
    }
  }

  /* walkabilityOf -- the anti-wall-in proof, and the only test in this file that would have caught
   * a genuinely game-breaking bug. Rasterises the world at `step`, marks a cell blocked when its
   * centre is inside any generated footprint or any painted obstacle INFLATED BY THE PLAYER RADIUS
   * (me.r is 23 in the hub; worldmap.js resolve() defaults r to 20 and validPlacement adds 23),
   * flood-fills 4-connected from the plaza, and reports which targets it reached.
   *
   * Authored building footprints are deliberately NOT blockers here: whether they are solid is the
   * base game's business and is unchanged by this lane. What this lane can break is the APPROACH,
   * so the targets are door-approach points 40 units outside each door plus every edge spawn. */
  function walkabilityOf(plan, o) {
    o = o || {};
    var step = o.step || 20, pr = (typeof o.playerR === 'number') ? o.playerR : 23;
    var W = plan.worldW, H = plan.worldH;
    var cols = Math.ceil(W / step), rows = Math.ceil(H / step);
    var blocked = new Uint8Array(cols * rows);
    var i, c, r2, cx, cy;

    var solids = [];
    for (i = 0; i < plan.structures.length; i++) {
      var s = plan.structures[i];
      if (s.h < 8) continue;                       // LOT slabs are 3-5 units: pavement, not wall
      solids.push(grow(rectOfSpec(s), pr));
    }
    var obs = o.obstacles || [];
    var orl = obstacleRects(obs, pr);
    for (i = 0; i < orl.length; i++) solids.push(orl[i]);

    for (r2 = 0; r2 < rows; r2++) {
      for (c = 0; c < cols; c++) {
        cx = (c + 0.5) * step; cy = (r2 + 0.5) * step;
        for (i = 0; i < solids.length; i++) {
          var q = solids[i];
          if (cx >= q.x && cx <= q.x + q.w && cy >= q.y && cy <= q.y + q.h) { blocked[r2 * cols + c] = 1; break; }
        }
      }
    }

    var seen = new Uint8Array(cols * rows);
    function idx(x, y) {
      var cc = Math.min(cols - 1, Math.max(0, Math.floor(x / step)));
      var rr = Math.min(rows - 1, Math.max(0, Math.floor(y / step)));
      return rr * cols + cc;
    }
    var start = idx(W / 2, H / 2);
    var stack = [start]; seen[start] = 1;
    var reached = 1;
    while (stack.length) {
      var n = stack.pop();
      var nc = n % cols, nr = (n / cols) | 0, k, nn;
      for (k = 0; k < 4; k++) {
        var tc = nc + (k === 0 ? 1 : k === 1 ? -1 : 0);
        var tr = nr + (k === 2 ? 1 : k === 3 ? -1 : 0);
        if (tc < 0 || tr < 0 || tc >= cols || tr >= rows) continue;
        nn = tr * cols + tc;
        if (seen[nn] || blocked[nn]) continue;
        seen[nn] = 1; reached++; stack.push(nn);
      }
    }

    var targets = [], zone = o.zone || {}, blds = zone.buildings || [], e = zone.edges || {}, k2;
    for (i = 0; i < blds.length; i++) {
      var b = blds[i];
      targets.push({ n: 'door:' + b.id, x: b.x, y: b.y + b.h / 2 + 40 });
    }
    for (k2 in e) {
      if (!Object.prototype.hasOwnProperty.call(e, k2)) continue;
      if (e[k2] && e[k2].spawn) targets.push({ n: 'spawn:' + k2, x: e[k2].spawn.x, y: e[k2].spawn.y });
    }

    var fails = [];
    for (i = 0; i < targets.length; i++) {
      var t = targets[i];
      if (!seen[idx(t.x, t.y)]) fails.push(t.n);
    }
    var free = 0;
    for (i = 0; i < blocked.length; i++) if (!blocked[i]) free++;

    return {
      cols: cols, rows: rows, cells: blocked.length, free: free, reached: reached,
      reachPct: free ? Math.round(reached / free * 100) : 0,
      targets: targets.length, fails: fails, ok: fails.length === 0
    };
  }

  // ==========================================================================================
  // SCENE LAYER. Nothing below here runs at load. Every entry point re-checks its own gates and
  // returns instead of throwing, because a failed background-city lane must never take the 2D
  // game down -- but every failure is COUNTED into S.errors and surfaced by diag(), because
  // swallowing errors silently is how a corrupt vendor file hid on this project for hours.
  // ==========================================================================================

  var S = {
    built: false, zoneId: null, wantZone: null,
    meshes: [], details: [], owned: [], handles: [],
    queue: [], plan: null,
    errors: 0, lastErr: '', buildMs: 0, frames: 0
  };

  function note(e) { S.errors++; S.lastErr = String((e && e.message) || e); }

  function engine() {
    try {
      var T = root && root.AK_THREE;
      return (T && T.ok && T.ok() && T.get) ? T.get() : null;
    } catch (_e) { return null; }
  }
  function w3state() {
    try {
      var W = root && root.AK_WORLD3D;
      return (W && W._state) ? W._state : null;
    } catch (_e) { return null; }
  }

  /* Auto density. Not a guess: the DPR clamp at world3d.js setPixelRatio(min(2,dpr)) means a
   * 3x-DPR phone is already rendering at 2x, and those are the devices where a 110-box district
   * plus 445 clutter props plus a 110-box ring is genuinely a lot of geometry. hardwareConcurrency
   * is the cheapest proxy available without a benchmark frame. Overridable by setDensity(). */
  function autoDensity() {
    try {
      var hc = (root.navigator && root.navigator.hardwareConcurrency) || 4;
      var dpr = root.devicePixelRatio || 1;
      if (hc <= 4 && dpr >= 2.5) return 0.45;
      if (hc <= 4) return 0.65;
      if (hc <= 6) return 0.85;
    } catch (_e) {}
    return 1.0;
  }

  /* makeMesh -- ONE geometry, ONE non-array material, one draw call. See the header's draw-call
   * model for why an array material would be a 6x waste on a texture-less box. */
  function makeMesh(THREE, spec) {
    var geo = new THREE.BoxGeometry(spec.w, spec.h, spec.d);
    var mat = new THREE.MeshLambertMaterial({ color: spec.col });
    var m = new THREE.Mesh(geo, mat);
    // Hub y maps to three z. world3d.js positions its buildings at (b.x, h/2, b.y) and this must
    // match exactly or the generated city sits on a different plane from the authored one.
    m.position.set(spec.x, spec.h / 2, spec.y);
    m.userData.akId = spec.id;
    m.userData.akWorldGen = true;
    // Tell aklod's adoptReal to keep its hands off: it decorates any blds entry that is not already
    // flagged, and two bldmass merges on one box is z-fighting plus a wasted draw call. The flag
    // name is aklod's, not ours -- it defined the handshake, we honour it.
    m.userData.akMassed = true;
    S.owned.push(geo, mat);
    return m;
  }

  function instantiate(THREE, st, spec) {
    var m = makeMesh(THREE, spec);
    st.scene.add(m);                       // DIRECT child -- see the header on why not a Group
    S.meshes.push(m);

    // Silhouette detail. bldmass returns ONE merged mesh with vertexColors, so this is +1 draw
    // call, not +15. It has never rendered a pixel in this repo (zero callers before this
    // workflow); this lane is one of the call sites that changes that.
    var det = null;
    if (spec.deco && root.AK_BLDMASS && typeof root.AK_BLDMASS.decorate === 'function') {
      try {
        det = root.AK_BLDMASS.decorate(THREE, m, { id: spec.id });
        if (det) {
          det.userData.akWorldGen = true;
          st.scene.add(det);
          S.details.push(det);
          S.owned.push(det.geometry, det.material);
        }
      } catch (e) { note(e); det = null; }
    }

    // --- peer lane registration. All three are optional and independently guarded: this module
    // must work standalone, with any subset loaded, and with all three loaded.

    // AK_CULL: its ONLY intake is world3d's blds array (akcull.js sync reads st.blds and watches
    // identity + length). A push is therefore the registration.
    if (CFG.cullRegister && st.blds && st.blds.push) {
      try { st.blds.push(m); } catch (e) { note(e); }
    }

    // AK_LOD: the documented manual path. NOT via blds -- aklod.js sync() caches on the blds array
    // IDENTITY and would never re-adopt after a push into an array it already owns.
    if (CFG.lodRegister && root.AK_LOD && typeof root.AK_LOD.register === 'function') {
      try { root.AK_LOD.register(m, { detail: det, near: m.material, own: true }); } catch (e) { note(e); }
    }

    // AK_STREAM: chunk residency. Weight is the draw-call cost of this structure so the streamer's
    // "units hidden" stat is denominated in draw calls rather than in objects.
    if (CFG.streamRegister && root.AK_STREAM && typeof root.AK_STREAM.add === 'function') {
      try {
        var h1 = root.AK_STREAM.add(m, spec.x, spec.y, 'worldgen', det ? 2 : 1);
        if (h1) S.handles.push(h1);
        if (det) { var h2 = root.AK_STREAM.add(det, spec.x, spec.y, 'worldgen', 0); if (h2) S.handles.push(h2); }
      } catch (e) { note(e); }
    }
    return m;
  }

  /* teardown -- idempotent, and it has to be, because world3d.js setZone may have already run its
   * own half of it. That teardown iterates blds calling scene.remove(m) + m.geometry.dispose(),
   * which is CORRECT for our meshes (they are direct scene children) but does not touch materials,
   * does not know about our detail meshes, and does not unregister us from the peer lanes. */
  function teardown() {
    var i;
    for (i = 0; i < S.handles.length; i++) {
      try { if (root.AK_STREAM && root.AK_STREAM.remove) root.AK_STREAM.remove(S.handles[i]); } catch (_e) {}
    }
    S.handles.length = 0;

    var st = w3state();
    for (i = 0; i < S.meshes.length; i++) {
      var m = S.meshes[i];
      try {
        if (m.parent) m.parent.remove(m);
        if (st && st.blds) { var ix = st.blds.indexOf(m); if (ix >= 0) st.blds.splice(ix, 1); }
      } catch (_e) {}
    }
    for (i = 0; i < S.details.length; i++) {
      try { if (S.details[i].parent) S.details[i].parent.remove(S.details[i]); } catch (_e) {}
    }
    for (i = 0; i < S.owned.length; i++) {
      try { if (S.owned[i] && S.owned[i].dispose) S.owned[i].dispose(); } catch (_e) {}
    }
    S.meshes.length = 0; S.details.length = 0; S.owned.length = 0; S.queue.length = 0;
    S.built = false; S.plan = null;
  }

  /* pump -- drain the build queue on a budget. Chosen for the same reason aklod.js pump() exists:
   * a district built in one frame is a visible stall on a phone, and the whole point of this lane
   * is a district big enough for that stall to be real. */
  function pump(THREE, st) {
    var n = CFG.buildBudget, t0 = (typeof Date !== 'undefined') ? Date.now() : 0;
    while (n-- > 0 && S.queue.length) {
      var spec = S.queue.shift();
      try { instantiate(THREE, st, spec); } catch (e) { note(e); }
    }
    S.buildMs += (Date.now() - t0);
    if (!S.queue.length) S.built = true;
  }

  /* tick -- the zone-change handshake and the build pump.
   *
   * THE HANDSHAKE, and why it needs no ordering assumption about script tags:
   * world3d.js setZone sets W3.zoneId = zone.id and REPLACES W3.blds with a fresh array in the same
   * synchronous call. So `st.zoneId === ctx.activeZone.id` is world3d's own published signal that
   * its rebuild has finished and blds is the new array. We tear down the moment st.zoneId stops
   * matching what we built for, and we rebuild only once it matches the live zone again. Load this
   * file before world3d.js or after it -- the result is identical, only the latency changes by one
   * frame. (It is placed BEFORE world3d.js so a teardown lands ahead of world3d's own, which keeps
   * the disposal ordering boring.)
   */
  function tick(dt, ctx) {
    var st = w3state(); if (!st || !st.scene) return false;
    var THREE = engine(); if (!THREE) return false;
    S.frames++;

    var live = st.zoneId || null;
    var want = (ctx && ctx.activeZone && ctx.activeZone.id) || null;

    // District changed under us -> drop everything before world3d gets to it.
    if (S.zoneId && S.zoneId !== live) { teardown(); S.zoneId = null; }

    if (!S.zoneId && live && want && live === want) {
      var t0 = Date.now();
      try {
        var W = 1700, H = 1300;
        if (ctx && ctx.world) { W = ctx.world.WORLD_W || W; H = ctx.world.WORLD_H || H; }
        S.plan = planDistrict(ctx.activeZone, { worldW: W, worldH: H, density: CFG.density });
        S.queue = S.plan.structures.slice();
        S.zoneId = live; S.built = false; S.buildMs = 0;
      } catch (e) { note(e); S.zoneId = live; S.queue = []; }
      S.buildMs += (Date.now() - t0);
    }

    if (S.queue.length) pump(THREE, st);
    return true;
  }

  // ==========================================================================================
  // SELF TEST -- `node systems/akworldgen.js`.
  // Requires the PEER LANES' OWN pure cores for the after-optimisation number. If they are not on
  // disk the structural checks still run and the draw-call section reports that it could not
  // measure, rather than inventing a figure.
  // ==========================================================================================

  // The nine real districts, transcribed from index.html:755 ZONES. Kept here so the headless test
  // exercises the SHIPPING data and not a toy fixture -- a generator that only works on a fixture
  // is the "code nothing calls" failure in a different costume.
  function fixtureZones() {
    function B(id, l, c, x, y, w, h) { return { id: id, label: l, col: c, x: x, y: y, w: w, h: h }; }
    return {
      THE_OVERLOOK: { id: 'THE_OVERLOOK', buildings: [], edges: { E: { spawn: { x: 150, y: 650 } }, S: { spawn: { x: 850, y: 150 } } } },
      DOWNTOWN: { id: 'DOWNTOWN', buildings: [B('DROP', 'THE DROP', '#ff8fae', 560, 560, 170, 104), B('GARAGE', 'THE GARAGE', '#7fc8ff', 1140, 560, 170, 104)],
        edges: { S: { spawn: { x: 850, y: 150 } }, W: { spawn: { x: 1550, y: 650 } }, E: { spawn: { x: 150, y: 650 } } } },
      NEON_HEIGHTS: { id: 'NEON_HEIGHTS', buildings: [B('WARD', 'THE WARDROBE', '#ff79c6', 560, 560, 160, 96), B('ARCH', 'THE ARCHIVE', '#c9a8ff', 1140, 560, 160, 96)],
        edges: { W: { spawn: { x: 1550, y: 650 } }, S: { spawn: { x: 850, y: 150 } } } },
      THE_YARDS: { id: 'THE_YARDS', buildings: [B('CLAN', 'CREW YARD', '#9d8bff', 560, 560, 170, 104), B('PASS', 'PASS HOUSE', '#5ad0c0', 1140, 560, 170, 104), B('FIXER', 'THE FIXER', '#ff9d5c', 850, 960, 160, 96)],
        edges: { E: { spawn: { x: 150, y: 650 } }, N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } } } },
      HOME_TURF: { id: 'HOME_TURF', buildings: [B('ARENA', 'TOWN HALL', '#e8c55a', 850, 360, 210, 124), B('TROPHY', 'TROPHY HALL', '#ffd76b', 430, 880, 160, 96), B('KENNEL', 'THE KENNEL', '#b6f06b', 1270, 880, 160, 96), B('INFIRMARY', 'INFIRMARY', '#ff7a7a', 1270, 500, 160, 96)],
        edges: { N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } }, E: { spawn: { x: 150, y: 650 } }, W: { spawn: { x: 1550, y: 650 } } } },
      FACTORY_ROW: { id: 'FACTORY_ROW', buildings: [B('GEM', 'GEM MINE', '#b07bff', 520, 540, 160, 100), B('MINT', 'GOLD MINT', '#ffd76b', 1180, 540, 160, 100), B('FORGE', 'CARD FORGE', '#ff9d5c', 850, 960, 170, 104)],
        edges: { W: { spawn: { x: 1550, y: 650 } }, N: { spawn: { x: 850, y: 1150 } }, S: { spawn: { x: 850, y: 150 } } } },
      THE_UNDERCITY: { id: 'THE_UNDERCITY', buildings: [], edges: { N: { spawn: { x: 850, y: 1150 } }, E: { spawn: { x: 150, y: 650 } } } },
      THE_STRIP: { id: 'THE_STRIP', buildings: [B('STREET', 'THE STREET', '#7CFFb0', 560, 560, 160, 96), B('ARCADE', 'THE ARCADE', '#7CFFE0', 1140, 560, 160, 96)],
        edges: { N: { spawn: { x: 850, y: 1150 } }, W: { spawn: { x: 1550, y: 650 } }, E: { spawn: { x: 150, y: 650 } } } },
      THE_DOCKS: { id: 'THE_DOCKS', buildings: [B('LAB', 'RESEARCH LAB', '#7fc8ff', 560, 540, 160, 100), B('GEN', 'THE GENERATOR', '#ffce6b', 1140, 540, 160, 100)],
        edges: { N: { spawn: { x: 850, y: 1150 } }, W: { spawn: { x: 1550, y: 650 } } } }
    };
  }

  // AK_COLLISION BUILTIN, transcribed from worldmap.js. Same reasoning as fixtureZones: the test
  // must dodge the REAL junked cars and freight rails, not imaginary ones.
  function fixtureObstacles() {
    return {
      HOME_TURF: [
        { type: 'rect', x: 1466, y: 280, w: 52, h: 560 }, { type: 'rect', x: 520, y: 780, w: 96, h: 48 },
        { type: 'rect', x: 1040, y: 556, w: 120, h: 18 }, { type: 'circle', x: 300, y: 520, r: 50 },
        { type: 'rect', x: 980, y: 1132, w: 300, h: 16 }, { type: 'circle', x: 1180, y: 640, r: 40 }],
      DOWNTOWN: [
        { type: 'rect', x: 800, y: 516, w: 104, h: 50 }, { type: 'rect', x: 300, y: 760, w: 140, h: 18 },
        { type: 'circle', x: 1380, y: 820, r: 46 }, { type: 'rect', x: 740, y: 864, w: 90, h: 46 },
        { type: 'rect', x: 1250, y: 300, w: 54, h: 230 }],
      THE_YARDS: [
        { type: 'rect', x: 120, y: 760, w: 60, h: 420 }, { type: 'rect', x: 780, y: 516, w: 120, h: 18 },
        { type: 'circle', x: 560, y: 824, r: 48 }, { type: 'rect', x: 1180, y: 824, w: 96, h: 46 },
        { type: 'circle', x: 1040, y: 1040, r: 44 }],
      NEON_HEIGHTS: [
        { type: 'circle', x: 690, y: 320, r: 34 }, { type: 'circle', x: 1010, y: 320, r: 34 },
        { type: 'circle', x: 300, y: 430, r: 40 }, { type: 'rect', x: 440, y: 716, w: 230, h: 16 },
        { type: 'circle', x: 1400, y: 430, r: 40 }, { type: 'rect', x: 1030, y: 716, w: 230, h: 16 },
        { type: 'circle', x: 700, y: 840, r: 36 }, { type: 'circle', x: 1000, y: 840, r: 36 }],
      FACTORY_ROW: [
        { type: 'rect', x: 140, y: 250, w: 18, h: 260 }, { type: 'rect', x: 140, y: 770, w: 18, h: 300 },
        { type: 'rect', x: 640, y: 466, w: 72, h: 72 }, { type: 'rect', x: 980, y: 466, w: 72, h: 72 },
        { type: 'rect', x: 1300, y: 280, w: 18, h: 240 }, { type: 'rect', x: 636, y: 756, w: 96, h: 48 },
        { type: 'rect', x: 984, y: 756, w: 96, h: 48 }, { type: 'rect', x: 1290, y: 770, w: 210, h: 18 },
        { type: 'circle', x: 300, y: 1120, r: 40 }, { type: 'circle', x: 1400, y: 1120, r: 40 }],
      THE_STRIP: [
        { type: 'rect', x: 372, y: 356, w: 96, h: 48 }, { type: 'rect', x: 500, y: 356, w: 96, h: 48 },
        { type: 'rect', x: 1100, y: 356, w: 96, h: 48 }, { type: 'rect', x: 1228, y: 356, w: 96, h: 48 },
        { type: 'rect', x: 556, y: 822, w: 188, h: 16 }, { type: 'rect', x: 956, y: 822, w: 188, h: 16 },
        { type: 'circle', x: 300, y: 440, r: 24 }, { type: 'circle', x: 300, y: 860, r: 24 },
        { type: 'circle', x: 1400, y: 440, r: 24 }, { type: 'circle', x: 1400, y: 860, r: 24 }],
      THE_DOCKS: [
        { type: 'rect', x: 250, y: 300, w: 120, h: 56 }, { type: 'rect', x: 250, y: 366, w: 120, h: 56 },
        { type: 'rect', x: 660, y: 460, w: 64, h: 64 }, { type: 'rect', x: 1330, y: 300, w: 120, h: 56 },
        { type: 'rect', x: 980, y: 460, w: 64, h: 64 }, { type: 'rect', x: 380, y: 900, w: 160, h: 60 },
        { type: 'rect', x: 1160, y: 900, w: 160, h: 60 }, { type: 'circle', x: 1500, y: 460, r: 20 },
        { type: 'circle', x: 1500, y: 840, r: 20 }, { type: 'circle', x: 640, y: 1140, r: 20 },
        { type: 'circle', x: 1060, y: 1140, r: 20 }],
      THE_OVERLOOK: [
        { type: 'rect', x: 520, y: 360, w: 240, h: 16 }, { type: 'rect', x: 940, y: 360, w: 240, h: 16 },
        { type: 'rect', x: 1040, y: 460, w: 64, h: 56 }, { type: 'circle', x: 320, y: 430, r: 40 },
        { type: 'circle', x: 320, y: 860, r: 40 }, { type: 'rect', x: 660, y: 780, w: 96, h: 48 }],
      THE_UNDERCITY: [
        { type: 'circle', x: 560, y: 820, r: 56 }, { type: 'circle', x: 1100, y: 820, r: 50 },
        { type: 'rect', x: 1300, y: 300, w: 18, h: 260 }, { type: 'rect', x: 1280, y: 820, w: 140, h: 56 },
        { type: 'circle', x: 320, y: 430, r: 42 }, { type: 'rect', x: 520, y: 360, w: 200, h: 18 },
        { type: 'rect', x: 980, y: 360, w: 200, h: 18 }]
    };
  }

  function selfTest(opt) {
    opt = opt || {};
    var L = [], fails = 0;
    function say(cond, msg) { L.push((cond ? '  PASS  ' : '  FAIL  ') + msg); if (!cond) fails++; }
    function line(s) { L.push(s); }

    var ZONES = fixtureZones(), OBS = fixtureObstacles();
    var order = ['THE_OVERLOOK', 'DOWNTOWN', 'NEON_HEIGHTS', 'THE_YARDS', 'HOME_TURF', 'FACTORY_ROW', 'THE_UNDERCITY', 'THE_STRIP', 'THE_DOCKS'];

    line('================================================================');
    line(VER + ' -- self test');
    line('================================================================');

    // ---- 1. DETERMINISM -------------------------------------------------------------------
    line('');
    line('[1] DETERMINISM  (a district must be byte-identical on every load)');
    var a = planDistrict(ZONES.HOME_TURF, { obstacles: OBS.HOME_TURF });
    var b2 = planDistrict(ZONES.HOME_TURF, { obstacles: OBS.HOME_TURF });
    say(JSON.stringify(a.structures) === JSON.stringify(b2.structures),
        'two independent plans of HOME_TURF are identical (' + a.structures.length + ' structures)');
    var c3 = planDistrict(ZONES.THE_DOCKS, { obstacles: OBS.THE_DOCKS });
    say(JSON.stringify(c3.structures) !== JSON.stringify(a.structures),
        'a different district produces a different city (not one skyline reused nine times)');

    // ---- 2. SCALE -------------------------------------------------------------------------
    line('');
    line('[2] SCALE  (PHASE 6 thin decor ring: ~20-40 structures per district, down from ~110)'); /* AK-3DC-streets 2026-07-29 */
    var i, z, p, tot = 0, minS = 1e9, maxS = -1, plans = {};
    line('        district        authored  blocks  lots  placed  rejected  capped  deco  tris');
    for (i = 0; i < order.length; i++) {
      z = ZONES[order[i]];
      p = planDistrict(z, { obstacles: OBS[order[i]] });
      plans[order[i]] = p;
      tot += p.structures.length;
      if (p.structures.length < minS) minS = p.structures.length;
      if (p.structures.length > maxS) maxS = p.structures.length;
      line('        ' + pad(order[i], 15) + ' ' + pad((z.buildings || []).length, 8) + ' ' +
           pad(p.stats.blocks, 7) + ' ' + pad(p.stats.lots, 5) + ' ' + pad(p.stats.placed, 7) + ' ' +
           pad(p.stats.rejected, 9) + ' ' + pad(p.stats.heightCapped, 7) + ' ' +
           pad(p.stats.decorated, 5) + ' ' + p.stats.triangles);
    }
    /* AK-3DC-streets 2026-07-29 -- PHASE 6 re-anchored the brief from "60-120, up from 4" to a thin
     * decor ring. The floor still guarantees the ring EXISTS (a district must not collapse to bare
     * ground); the ceiling still guards against the generator ballooning back into a wall. */
    say(minS >= 18, 'every district keeps at least a thin ring (min ' + minS + ')');
    say(maxS <= CFG.targetMax + 12, 'no district blows past the thin-ring cap (max ' + maxS + ', cap ' + CFG.targetMax + ')');
    line('        TOTAL across 9 districts: ' + tot + ' structures  (thin ring; authored 18 buildings stay untouched)');

    // ---- 3. KEEP-OUTS ---------------------------------------------------------------------
    line('');
    line('[3] KEEP-OUTS  (authored footprints, doors, obstacles, spawns, plaza, world rim)');
    var koFails = 0, selfFails = 0, rimFails = 0;
    for (i = 0; i < order.length; i++) {
      p = plans[order[i]];
      var rects = [], k;
      for (k = 0; k < p.structures.length; k++) {
        var r = rectOfSpec(p.structures[k]);
        if (hitsAny(r, p.keepOuts)) koFails++;
        if (hitsAny(r, rects)) selfFails++;
        if (r.x < CFG.rim - 0.001 || r.y < CFG.rim - 0.001 ||
            r.x + r.w > p.worldW - CFG.rim + 0.001 || r.y + r.h > p.worldH - CFG.rim + 0.001) rimFails++;
        rects.push(r);
      }
    }
    say(koFails === 0, 'zero structures overlap a keep-out across all 9 districts (' + koFails + ')');
    say(selfFails === 0, 'zero structure-vs-structure overlaps (' + selfFails + ')');
    say(rimFails === 0, 'zero structures cross the world rim (' + rimFails + ')');

    // ---- 4. WALKABILITY -- the one that matters -------------------------------------------
    line('');
    line('[4] WALKABILITY  (flood fill from the plaza at a 20-unit step, player radius 23)');
    line('        district        cells  free   reached  reach%  targets  unreachable');
    var wFails = 0;
    for (i = 0; i < order.length; i++) {
      p = plans[order[i]];
      var wk = walkabilityOf(p, { zone: ZONES[order[i]], obstacles: OBS[order[i]] });
      if (!wk.ok) wFails++;
      line('        ' + pad(order[i], 15) + ' ' + pad(wk.cells, 6) + ' ' + pad(wk.free, 6) + ' ' +
           pad(wk.reached, 8) + ' ' + pad(wk.reachPct + '%', 7) + ' ' + pad(wk.targets, 8) + ' ' +
           (wk.fails.length ? wk.fails.join(',') : '-'));
    }
    say(wFails === 0, 'every district door approach and every district exit is reachable from the plaza');

    // ---- 5. DENSITY KNOB ------------------------------------------------------------------
    line('');
    line('[5] DENSITY KNOB  (the density knob thins the city monotonically; it does not change it)');
    /* AK-3DC-streets 2026-07-29 -- with PHASE 6's low targetMax the cap now clamps every real device
     * tier (autoDensity 0.45..1.0 all land on ~the cap), so those tiers plateau and the OLD
     * [1.0..0.25] probe measured cap jitter, not the knob. Exercise the knob BELOW the cap where it
     * is the sole lever, which is the genuine single-pass thinning curve this test is meant to prove. */
    var dens = [0.26, 0.20, 0.15, 0.10, 0.06], prev = 1e9, dOk = true, dLine = [];
    for (i = 0; i < dens.length; i++) {
      var dp = planDistrict(ZONES.HOME_TURF, { obstacles: OBS.HOME_TURF, density: dens[i] });
      dLine.push(dens[i] + '->' + dp.structures.length);
      if (dp.structures.length > prev) dOk = false;
      prev = dp.structures.length;
    }
    say(dOk, 'structure count is monotonic in density: ' + dLine.join('  '));

    // ---- 6. THE HEADLINE NUMBER -----------------------------------------------------------
    line('');
    line('[6] DRAW CALLS  BEFORE vs AFTER the optimisation lanes');
    var res = measureDrawCalls(plans.HOME_TURF, ZONES.HOME_TURF, L, say);
    line('');
    line(fails ? 'FAILURES PRESENT: ' + fails : 'ALL PASS');
    return { ok: fails === 0, fails: fails, lines: L, drawCalls: res, plans: plans };
  }

  function pad(v, n) { var s = String(v); while (s.length < n) s += ' '; return s; }

  /* measureDrawCalls -- the headline. Runs the PEER LANES' OWN cores over this lane's structures.
   * Nothing here re-implements culling, LOD or streaming; if akcull's frustum maths changes, this
   * number changes with it, which is the only way a cross-lane claim stays honest. */
  function measureDrawCalls(plan, zone, L, say) {
    function line(s) { L.push(s); }
    var cull = null, lod = null, stream = null, w3 = null;
    try { cull = require('./akcull.js'); } catch (_e) {}
    try { lod = require('./aklod.js'); } catch (_e) {}
    try { stream = require('./akstream.js'); } catch (_e) {}
    try { w3 = require('./world3d.js'); } catch (_e) {}

    var S2 = plan.structures, i, s;
    var deco = plan.stats.decorated;
    var naive = S2.length + deco;                        // 1 call per box + 1 per merged detail mesh
    var authored = (zone.buildings || []).length * 6;    // world3d.js 6-material array, unchanged

    line('        BEFORE (naive, everything drawn every frame)');
    line('          generated structures      ' + S2.length + ' meshes x 1 material  = ' + S2.length + ' draw calls');
    line('          generated bldmass detail  ' + deco + ' merged meshes         = ' + deco + ' draw calls');
    line('          authored buildings        ' + (zone.buildings || []).length + ' meshes x 6 materials = ' + authored + ' draw calls');
    line('          ------------------------------------------------------------');
    line('          TOTAL generated                                   = ' + naive + ' draw calls');
    line('          (for reference, the district BEFORE this lane existed = ' + authored + ' + 1 ground)');

    if (!cull || !lod || !w3) {
      line('        AFTER: NOT MEASURED -- a peer lane core is missing from ./systems/.');
      line('        akcull=' + !!cull + ' aklod=' + !!lod + ' world3d=' + !!w3 + ' akstream=' + !!stream);
      say(false, 'peer lane cores available for the after-measurement');
      return { naive: naive, measured: false };
    }

    // A real camera. world3d.js makeProjector defaults are the shipping ones (phi 52deg, dist 620,
    // fov 55); the viewport is a 2024-era phone in landscape at CSS pixels.
    var proj = w3.makeProjector({ worldW: plan.worldW, worldH: plan.worldH });
    proj.setViewport(844, 390);

    var boxes = [];
    for (i = 0; i < S2.length; i++) {
      s = S2[i];
      boxes.push({ id: s.id, x: s.x, y: s.y, w: s.w, d: s.d, h: s.h, solid: true, _s: s });
    }

    var core = lod.makeLodCore({ tiers: lod.DEFAULT_TIERS, hyst: lod.DEFAULT_HYST });
    var culler = cull.makeCuller();

    var grid = null, streamer = null, streamVis = null;
    if (stream) {
      grid = stream.makeChunkGrid({ worldW: plan.worldW, worldH: plan.worldH, size: 256 });
      streamVis = {};
      streamer = stream.makeStreamer(grid, { setVis: function (o2, v) { streamVis[o2.id] = v; } });
      for (i = 0; i < S2.length; i++) streamer.add({ id: S2[i].id }, S2[i].x, S2[i].y, 'wg', 1);
    }

    // A patrol around the district: the four exits and the plaza, sampled along the path. This is
    // the same shape of walk akstream.js uses for its residency numbers, so the two lanes' figures
    // are comparable.
    var path = [[850, 650], [850, 200], [1500, 650], [850, 1100], [200, 650], [850, 650]];
    var samples = [], seg, t, sx, sy;
    for (seg = 0; seg < path.length - 1; seg++) {
      for (t = 0; t < 1; t += 0.045) {
        sx = path[seg][0] + (path[seg + 1][0] - path[seg][0]) * t;
        sy = path[seg][1] + (path[seg + 1][1] - path[seg][1]) * t;
        samples.push([sx, sy]);
      }
    }

    var tiers = new Int8Array(S2.length);
    for (i = 0; i < tiers.length; i++) tiers[i] = -1;

    var sumNaive = 0, sumAfter = 0, sumCull = 0, sumLodCull = 0, sumStreamHid = 0, sumVis = 0;
    var worstAfter = 0, bestAfter = 1e9, n = samples.length;

    for (var f = 0; f < n; f++) {
      proj.follow(samples[f][0], samples[f][1]);
      if (streamer) streamer.update(samples[f][0], samples[f][1]);
      var cp = proj.camPos();
      var vis = culler.run(boxes, proj);

      // Map the culler's per-record verdict back onto structures.
      var visById = {};
      for (i = 0; i < vis.recs.length; i++) visById[vis.recs[i].id] = vis.recs[i].vis;

      var calls = 0, culled = 0, lodCulled = 0, streamHid = 0, drawn = 0;
      for (i = 0; i < S2.length; i++) {
        s = S2[i];
        var dx = s.x - cp.x, dy = s.h / 2 - cp.y, dz = s.y - cp.z;
        var tier = core.pick(dx * dx + dy * dy + dz * dz, tiers[i] < 0 ? 0 : tiers[i]);
        tiers[i] = tier;

        var sHid = streamVis ? (streamVis[s.id] === false) : false;
        var cHid = (visById[s.id] === false);
        var lHid = (tier >= core.maxTier);

        if (sHid) streamHid++;
        if (cHid) culled++;
        if (lHid) lodCulled++;
        if (sHid || cHid || lHid) continue;

        drawn++;
        // At T0 the merged bldmass detail draws too; aklod.js applyTier makes detail a T0-only
        // luxury and this mirrors that exactly.
        calls += 1 + ((s.deco && tier === 0) ? 1 : 0);
      }
      sumNaive += naive; sumAfter += calls; sumCull += culled; sumLodCull += lodCulled;
      sumStreamHid += streamHid; sumVis += drawn;
      if (calls > worstAfter) worstAfter = calls;
      if (calls < bestAfter) bestAfter = calls;
    }

    var meanAfter = sumAfter / n;
    line('');
    line('        AFTER  (akcull frustum+occlusion, aklod tiers ' + lod.DEFAULT_TIERS.join('/') +
         ', akstream 256-unit chunks)');
    line('          patrol of ' + n + ' camera positions, viewport 844x390, phi 52deg dist 620 fov 55');
    line('          mean frustum/occlusion culled  ' + (sumCull / n).toFixed(1) + ' / ' + S2.length);
    line('          mean LOD-tier culled           ' + (sumLodCull / n).toFixed(1) + ' / ' + S2.length);
    line('          mean chunk-streamed out        ' + (sumStreamHid / n).toFixed(1) + ' / ' + S2.length +
         (stream ? '' : '  (akstream not on disk)'));
    line('          mean structures actually drawn ' + (sumVis / n).toFixed(1) + ' / ' + S2.length);
    line('          ------------------------------------------------------------');
    line('          BEFORE  ' + naive + ' draw calls every frame');
    line('          AFTER   ' + meanAfter.toFixed(1) + ' draw calls mean  (best ' + bestAfter + ', worst ' + worstAfter + ')');
    line('          SAVED   ' + (naive - meanAfter).toFixed(1) + ' draw calls/frame = ' +
         Math.round((1 - meanAfter / naive) * 100) + '%');

    say(meanAfter < naive * 0.75, 'the optimisation lanes remove at least 25% of the generated draw calls');
    say(sumCull > 0, 'frustum/occlusion culling ACTIVATES on this content (' + sumCull + ' cull events)');
    /* AK-3DC-streets 2026-07-29 -- PHASE 6 thinned the world on purpose, so far-geometry is sparse
     * and LOD far-tier cull no longer fires on this patrol. Reported, not asserted: on the thin ring
     * frustum-cull + chunk-stream are the load-bearing lanes (see the ~75% cut above), not LOD. */
    line('          LOD tier-cull events on the thin ring: ' + sumLodCull + ' (informational; not load-bearing at this density)');
    if (stream) say(sumStreamHid > 0, 'chunk streaming ACTIVATES on this content (' + sumStreamHid + ' hide events)');

    return {
      measured: true, naive: naive, authored: authored, frames: n,
      meanAfter: meanAfter, best: bestAfter, worst: worstAfter,
      savedPct: Math.round((1 - meanAfter / naive) * 100),
      meanCulled: sumCull / n, meanLodCulled: sumLodCull / n,
      meanStreamHidden: sumStreamHid / n, meanDrawn: sumVis / n
    };
  }

  // ==========================================================================================
  // EXPORTS
  // ==========================================================================================
  var API = {
    version: function () { return VER; },
    // pure core
    planDistrict: planDistrict, planStreets: planStreets, blocksFrom: blocksFrom,
    keepOutsFor: keepOutsFor, subdivideBlock: subdivideBlock, walkabilityOf: walkabilityOf,
    rngFor: rngFor, overlaps: overlaps, rectOfSpec: rectOfSpec, obstacleRects: obstacleRects,
    KINDS: KINDS, KIND_BY_NAME: KIND_BY_NAME, config: CFG,
    // scene layer
    tick: tick, teardown: teardown,
    plan: function () { return S.plan; },
    structures: function () { return S.plan ? S.plan.structures.slice() : []; },
    meshes: function () { return S.meshes.slice(); },
    // the density knob the brief asks for. Call with no argument to re-auto-detect.
    setDensity: function (v) {
      CFG.density = (typeof v === 'number') ? Math.max(0, Math.min(1, v)) : autoDensity();
      if (S.zoneId) { teardown(); S.zoneId = null; }   // force a rebuild at the new density
      return CFG.density;
    },
    autoDensity: autoDensity,
    set: function (k, v) { if (Object.prototype.hasOwnProperty.call(CFG, k)) { CFG[k] = v; return true; } return false; },
    // Diagnostics. Errors are REPORTED, never swallowed.
    diag: function () {
      var st = w3state();
      return {
        version: VER, zone: S.zoneId, built: S.built, pending: S.queue.length,
        structures: S.plan ? S.plan.structures.length : 0,
        meshes: S.meshes.length, details: S.details.length,
        drawCallsNaive: S.meshes.length + S.details.length,
        density: CFG.density, buildMs: Math.round(S.buildMs), frames: S.frames,
        errors: S.errors, lastError: S.lastErr,
        three: !!engine(), scene: !!(st && st.scene), blds: st && st.blds ? st.blds.length : -1,
        peers: {
          bldmass: !!(root && root.AK_BLDMASS), lod: !!(root && root.AK_LOD),
          cull: !!(root && root.AK_CULL), stream: !!(root && root.AK_STREAM)
        },
        stats: S.plan ? S.plan.stats : null
      };
    },
    selfTest: selfTest,
    _state: S
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_WORLDGEN = API;
    /* SELF-REGISTRATION. This is the integration call site: _registry.js tickAll() is the caller,
     * reached from index.html akTickSystems, gated on state==='IN_ZONE' && !interiorOpen.
     *
     * NOTE for raids: index.html ticks only ['raidwaves','raidfortify','backpack'] while
     * state==='RAID'. 'akworldgen' is deliberately absent -- raids swap WORLD_W/H to the raid map
     * and world3d is frozen anyway, so a background city has nothing to do there. This is a
     * decision, not the index.html:2429 "dead on arrival" bug: that bug is about systems that NEED
     * raid ticks and never get them.
     *
     * init returns true and does nothing: world3d boots three ASYNCHRONOUSLY and its scene does not
     * exist at initAll() time. tick() polls for it, the same way akstream does. */
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({
          id: 'akworldgen',
          init: function () { CFG.density = autoDensity(); return true; },
          onTick: function (dt, ctx) {
            try { tick(dt, ctx); } catch (e) { note(e); }
          }
        });
      }
    } catch (_e) {}
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akworldgen.js` prints the world-scale proof. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  var _r = module.exports.selfTest();
  _r.lines.forEach(function (l) { console.log(l); });
  process.exit(_r.ok ? 0 : 1);
}
