/* ALLEY KINGZ -- AK_CLUTTER: near-field street clutter + ground detail.  AK-CLUTTER 2026-07-19.
 *
 * WHY THIS EXISTS
 * ---------------
 * The district reads EMPTY and FLAT. That is not an opinion, it is arithmetic: bldmass.js:9
 * measured the whole visible world at 50 triangles, and index.html:806 puts FOUR buildings in
 * HOME_TURF, the spawn district and the worst case. Everything else on screen is one painted
 * ground plate (world3d.js:495 -- ONE PlaneGeometry, 2 triangles, the entire floor of the city).
 *
 * A big painted plate with four boxes on it has no depth cues. The reason AAA mobile scenes feel
 * dense is not polygon count -- it is CHEAP REPEATED PROPS AT VARYING DISTANCE. A lamp 40 units
 * away and a lamp 900 units away are the same 4 boxes, but the pair tells the eye how big the
 * street is, and a moving camera turns that into parallax. That is the cue this world is missing
 * and it is the cheapest one to buy.
 *
 * WHAT THIS LANE OWNS, AND WHAT IT DELIBERATELY DOES NOT
 * -----------------------------------------------------
 * akstream.js ALREADY scatters 12 prop kinds (akstream.js:437 CLUTTER) and bakes them per chunk
 * (akstream.js:756 bakeChunk) so its streamer has something to stream. That is real content and
 * this file does NOT replace it, duplicate it, or fight it. The split is by STRUCTURE:
 *
 *   akstream  = SCATTER.    Random points over the whole world, rejected off buildings, baked
 *                           into per-chunk merged meshes, hidden by chunk residency. It fills
 *                           the BLOCK INTERIORS -- the parts of the map you look across.
 *   THIS FILE = STRUCTURE.  Props placed ON THE STREET LATTICE: lamps at fixed intervals down a
 *                           kerb, kerb strips along the road edge, crosswalks at intersections,
 *                           bins and bags hugging the block edge that faces the alley. It fills
 *                           the parts of the map you WALK THROUGH, which is the near field.
 *
 * Scatter cannot produce a lamp run. A lamp run is what makes a road read as a road, because the
 * eye reads the EVEN SPACING as intent. Random lamps read as debris. So the two techniques are
 * not interchangeable and both are needed.
 *
 * They are de-conflicted for real, not by hope: dedupe() re-derives akstream's prop list from its
 * own exported pure planner (AK_STREAM.planClutter, akstream.js:544) with its own exported config,
 * and rejects any of our props landing within dedupR of one of theirs. Both planners are seeded
 * and deterministic, so the re-derived list is byte-identical to the one akstream baked -- that is
 * the only reason this de-conflict is sound rather than approximate.
 *
 * GROUND DETAIL IS HALF THE LANE NAME AND IT IS THE HALF NOBODY BUILDS
 * -------------------------------------------------------------------
 * Every prop in akstream stands UP (akstream.js:464 boxesFor -- twelve kinds, all boxes with
 * height). There is not one flat mark on the ground in this game. Puddles, manhole covers, storm
 * grates, crosswalk stripes, oil stains and kerb lines cost almost nothing and they are what stops
 * a ground plate from reading as wallpaper, because they BREAK THE TILE. A repeating plate texture
 * announces its repeat instantly at the 52-degree camera pitch (world3d.js:120 DEFAULT_PHI); an
 * irregular scatter of dark marks on top of it hides the seam for free.
 *
 * DRAW CALLS ARE THE WHOLE CONSTRAINT AND THIS FILE IS BUILT AROUND ONE NUMBER
 * ---------------------------------------------------------------------------
 * akinstance.js:5 states the wall: a mid-range Android eats 100k triangles and dies at ~300 draw
 * calls. This lane targets 300-700 props per district. As ordinary Meshes that is 300-700 calls
 * MINIMUM -- more, because a lamp is 4 boxes -- and the frame is over before the buildings draw.
 *
 * So every prop in this file goes through AK_INSTANCE, and it uses BOTH of that module's
 * techniques in the order they compose:
 *   merge     kills the PARTS   (a lamp's 4 boxes -> 1 geometry)      akinstance.js:152
 *   instance  kills the COPIES  (that lamp x 180 -> 1 InstancedMesh)  akinstance.js:445
 * Result: one draw call per KIND-VARIANT, not per prop. Measured by the headless test at the
 * bottom against real three r160, not asserted here.
 *
 * WHY THERE ARE GEOMETRY VARIANTS AT ALL
 * Instancing shares ONE geometry across every copy, so per-prop shape variation is impossible
 * inside a field. Rotation, scale and instance TINT are free per-copy (akinstance.js:315
 * writeMatrix / :337 writeColor), and for most kinds that is enough -- a hydrant is a hydrant.
 * But a crate STACK whose height never changes reads as a copy-paste, so the kinds where shape
 * variance is what sells it (CRATES, BAGS, PUDDLE, STAIN) declare `vars > 1` and get one field
 * per variant. Every extra variant is one extra draw call, so the variant count IS a budget and
 * the quality knob spends it: at q=0.45 every kind collapses to a single variant.
 *
 * THE TINT TRAP, because it has bitten this codebase's neighbours already
 * akinstance.js:341 spells it out: three MULTIPLIES instanceColor into the vertex colour, it does
 * not replace it. Our templates carry baked vertex colours, so an instance colour here is a
 * DARKENING TINT and 0xffffff is a no-op. Every tint this file emits is therefore in the 0x88..0xff
 * grey band and is used to break up uniformity, never to recolour a prop.
 *
 * NOT WALLING THE PLAYER IN
 * -------------------------
 * These props are DECORATION. They are not pushed into AK_COLLISION (worldmap.js:384) and that is
 * a decision, not an oversight: the collision list is consumed every frame by the AK-MOVE3 block
 * at index.html:2480, and adding 500 rects to it would turn an O(n) resolve into the frame budget's
 * biggest line item for the sake of bumping into a crisp packet. So the player walks THROUGH them
 * and cannot be trapped by construction.
 *
 * That makes "off walkable paths" a VISUAL requirement rather than a safety one, and it is still
 * enforced hard, because a dumpster standing in the doorway you just walked out of reads as a bug
 * whether or not it blocks you. Standing props are rejected against: authored building footprints
 * + their door corridors (exitInterior at index.html:1345 drops the player at b.y + b.h/2 + r + 85,
 * so the south apron is carved DEEPER than the others), every AK_COLLISION obstacle, the four edge
 * spawn discs, the centre plaza, and the middle of every street band. And walkabilityOf() then
 * flood-fills the district treating our standing props AS IF THEY WERE SOLID -- the strictest
 * possible reading of the rule, testing a constraint we do not even rely on -- and asserts the
 * plaza still reaches all four edge spawns and every building door. Ground decals are exempt from
 * that test because you walk over a puddle.
 *
 * ONE RENDERER LAW: this file constructs NO WebGLRenderer, NO canvas, and NO Scene. It builds
 * geometry and hands it to AK_INSTANCE, which attaches to the scene world3d.js already owns.
 * Zero WebGL contexts spent. three_boot.js:74, world3d.js:463.
 *
 * NO em-dashes anywhere in this file (hook law, use --).
 */
(function (root) {
  'use strict';

  var VER = 'AK-CLUTTER-1.0.0';

  /* =========================================================================================
   * PURE CORE. No THREE, no DOM, no globals except OPTIONAL reads of AK_WORLDGEN / AK_STREAM /
   * AK_COLLISION, every one of them behind a typeof guard with a built-in fallback. This half is
   * node-requireable and is what the headless test at the bottom exercises.
   * ========================================================================================= */

  /* Deterministic seeded RNG. Byte-identical to bldmass.js:24-33, akinstance.js:104-112 and
   * akworldgen.js:113-121 ON PURPOSE -- a shared hash means a seed string produces the same
   * sequence in every lane, so two modules asked to decorate "HOME_TURF:lamp:3" agree without
   * having to pass values to each other. Math.random() here would reshuffle every prop on every
   * district re-entry, and a street whose lamps move when you walk back into it does not read as
   * randomness, it reads as a rendering fault. */
  function hash(str) {
    var h = 2166136261, s = String(str || 'x');
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  /* ------------------------------------------------------------------------------------------
   * PALETTE. These hex values are deliberately the SAME NUMBERS as akstream.js:433-435 and
   * bldmass.js:37. Three lanes dressing the same street have to agree on what "grimy metal" is or
   * the props read as belonging to different games. Copied as literals rather than imported
   * because a cross-lane runtime dependency for six constants is a load-order bug waiting to
   * happen, and these numbers are frozen by the art direction anyway.
   * ---------------------------------------------------------------------------------------- */
  var C_METAL  = 0x3a3d46, C_RUST   = 0x4a3a2e, C_DARK  = 0x15151b, C_TRIM  = 0x1b1b22,
      C_WOOD   = 0x4d3b28, C_GREEN  = 0x2f4a3a, C_GREY  = 0x2a2a32, C_LAMP  = 0x5a5f6b,
      C_GLOW   = 0xffd98a, C_BAG    = 0x1a1a20, C_RED   = 0x6b2420, C_CONC  = 0x33333c;
  // Ground-mark tones. Darker than everything above, because a mark on asphalt is asphalt with
  // less light coming back off it, not a new material sitting on top.
  var C_WET    = 0x0e1016, C_OIL    = 0x0b0b10, C_IRON  = 0x24262d, C_PAINT = 0x9aa0ac,
      C_KERB   = 0x3c3f47;

  /* ------------------------------------------------------------------------------------------
   * TUNING. Every number is in WORLD UNITS (the 1700x1300 zone space, index.html:788 ZW/ZH).
   * ---------------------------------------------------------------------------------------- */
  var CFG = {
    quality: 1.0,        // 0..1 master knob. Scales density AND variant count. See setQuality().
    rim: 22,             // dead border at the world edge
    lampGap: 168,        // spacing down a lamp run. 168 puts 7-8 lamps on a 1300-unit avenue,
                         // which at the 52-degree pitch reads as a street rather than as a fence.
    lampIn: 16,          // how far INSIDE the kerb line a lamp post sits
    poolR: 46,           // radius of the light pool decal under a lamp
    kerbLen: 96,         // length of one kerb strip segment
    kerbW: 9,            // kerb strip width
    roadMarks: 44,       // flat marks (manhole/grate/puddle/stain) attempted per district
    edgeProps: 120,      // standing props attempted along block edges per district
    /* FRONTAGE SCALES WITH THE WORLD, IT IS NOT A CONSTANT. This is the operator's directive
     * discharged as a number rather than as a comment: the clutter budget is a function of how
     * much street-facing wall the district actually has, so growing the world grows the clutter
     * automatically instead of requiring a retune. A flat constant here is what made the first
     * build of this file place FEWER props on a 119-structure district than on a 4-building one --
     * the generated buildings ate the pavement the edge pass was using and nothing replaced it. */
    frontPerStruct: 2.2, // attempted props per generated structure
    frontMax: 300,       // ...capped, so a runaway generator cannot blow the draw-call budget
    crossings: 1,        // crosswalk stripe sets per main intersection quadrant
    spacing: 30,         // occupancy lattice cell. Two props in one cell = the second is dropped,
                         // which is what stops a "pile" reading as a glitch rather than as mess.
    playerR: 23,         // me.r in the hub. worldmap.js resolve() defaults r to 20 and
                         // validPlacement adds 23; 23 is the value index.html actually carries.
    passGap: 24,         // GUARANTEED walking gap between two standing props, measured between
                         // their footprints ALREADY INFLATED by playerR. See the passability note
                         // on placeStanding(): without this the lamp runs and the edge furniture
                         // interlock into a continuous wall along every kerb, and the walkability
                         // flood-fill sealed the TROPHY door off the plaza at 43% open map. That
                         // was a real failure of the first build of this file, caught by the test.
    dedupR: 44,          // reject radius against an akstream scatter prop
    bldPad: 34,          // keep-out ring around an authored building footprint
    doorApron: 118,      // extra south-face keep-out. exitInterior (index.html:1345) puts the
                         // player at b.y + b.h/2 + me.r + 85, so this covers the landing spot.
    obsMargin: 18,       // keep-out ring around an AK_COLLISION obstacle
    spawnR: 104,         // keep-out disc at each district edge spawn
    plazaR: 118,         // keep-out disc at the centre crossroads
    lanePad: 26,         // how far a standing prop must stay OUTSIDE the kerb line, i.e. out of
                         // the carriageway. Ground decals ignore this -- you walk over a puddle.
    decalY: 0.7,         // decal lift off the ground plane. world3d.js:497 puts the ground at
                         // y=0 exactly; a decal at y=0 z-fights it and the fight is resolution
                         // dependent, so it looks fine on the dev box and strobes on a phone.
    decalStep: 0.22      // per-layer extra lift so decals do not z-fight EACH OTHER either
  };

  /* ------------------------------------------------------------------------------------------
   * KIND TABLE.
   *   ground  true  -> flat mark, exempt from the walkability test and from lanePad
   *   glow    true  -> additive material, no depth write (the lamp pool only)
   *   foot          -> footprint diameter used by the occupancy lattice and the keep-out tests
   *   vars          -> geometry variants. See the header: every variant is one more draw call.
   *   parts         -> boxes/planes in the merged template, for the naive-vs-actual arithmetic
   * ---------------------------------------------------------------------------------------- */
  var KINDS = [
    // --- ground detail -----------------------------------------------------------------------
    { k: 'POOL',      ground: true,  glow: true,  foot: 92, vars: 1, parts: 1, layer: 3 },
    { k: 'PUDDLE',    ground: true,  glow: false, foot: 62, vars: 3, parts: 2, layer: 1 },
    { k: 'MANHOLE',   ground: true,  glow: false, foot: 34, vars: 1, parts: 2, layer: 2 },
    { k: 'GRATE',     ground: true,  glow: false, foot: 40, vars: 1, parts: 5, layer: 2 },
    { k: 'STAIN',     ground: true,  glow: false, foot: 70, vars: 2, parts: 2, layer: 0 },
    { k: 'CROSSWALK', ground: true,  glow: false, foot: 56, vars: 1, parts: 1, layer: 2 },
    { k: 'KERB',      ground: false, glow: false, foot: 96, vars: 1, parts: 1, layer: 0 },
    // --- standing near-field furniture -------------------------------------------------------
    { k: 'LAMP',      ground: false, glow: false, foot: 26, vars: 1, parts: 4 },
    { k: 'HYDRANT',   ground: false, glow: false, foot: 20, vars: 1, parts: 3 },
    { k: 'BOLLARD',   ground: false, glow: false, foot: 18, vars: 1, parts: 2 },
    { k: 'CONE',      ground: false, glow: false, foot: 18, vars: 1, parts: 2 },
    { k: 'FENCE',     ground: false, glow: false, foot: 74, vars: 2, parts: 6 },
    { k: 'DUMPSTER',  ground: false, glow: false, foot: 58, vars: 1, parts: 5 },
    { k: 'CRATES',    ground: false, glow: false, foot: 46, vars: 3, parts: 3 },
    { k: 'BAGS',      ground: false, glow: false, foot: 38, vars: 3, parts: 3 },
    { k: 'NEWSBOX',   ground: false, glow: false, foot: 26, vars: 1, parts: 3 }
  ];
  var KIND_BY_NAME = (function () { var m = {}, i; for (i = 0; i < KINDS.length; i++) m[KINDS[i].k] = KINDS[i]; return m; })();

  // Weighted pools per placement pass. A pass draws only from kinds that make sense where it is
  // placing: a dumpster belongs against a block edge, never in the middle of a carriageway.
  var POOL_EDGE  = [['DUMPSTER', 12], ['CRATES', 16], ['BAGS', 18], ['FENCE', 10], ['NEWSBOX', 7], ['CONE', 8], ['BOLLARD', 6]];
  var POOL_FRONT = [['BAGS', 20], ['CRATES', 14], ['NEWSBOX', 10], ['HYDRANT', 8], ['CONE', 9], ['BOLLARD', 9], ['DUMPSTER', 8]];
  var POOL_ROAD  = [['PUDDLE', 26], ['MANHOLE', 14], ['GRATE', 12], ['STAIN', 20]];

  function pickWeighted(pool, r) {
    var tot = 0, i;
    for (i = 0; i < pool.length; i++) tot += pool[i][1];
    var t = r * tot, acc = 0;
    for (i = 0; i < pool.length; i++) { acc += pool[i][1]; if (t < acc) return pool[i][0]; }
    return pool[pool.length - 1][0];
  }

  /* ==========================================================================================
   * THE STREET LATTICE.
   *
   * AK_WORLDGEN owns the canonical lattice (akworldgen.js:218 planStreets) and this lane uses it
   * verbatim when that module is loaded, so props line the SAME streets the generated buildings
   * address. But akworldgen.js is not in index.html's script tags yet (integration is a later
   * phase), and a clutter lane that renders nothing until a sibling lane ships is a dead lane.
   * So builtinStreets() reproduces its geometry exactly -- same pinned mains at W/2 and H/2 with
   * half-width 75, same quarter-line secondaries, same rim alleys, same seeded jitter, same
   * 'streets:'+zid seed string -- which means the fallback and the real thing produce IDENTICAL
   * bands. The test asserts that equality rather than trusting the copy.
   * ========================================================================================= */
  function builtinStreets(zoneId, W, H, o) {
    o = o || {};
    var rnd = rngFor('streets:' + zoneId);
    var j = (typeof o.jitter === 'number') ? o.jitter : 42;
    function jit() { return (rnd() * 2 - 1) * j; }

    var vx = [{ c: W * 0.5, half: 75, rank: 'main' }];
    var hy = [{ c: H * 0.5, half: 75, rank: 'main' }];
    vx.push({ c: W * 0.28 + jit(), half: 45, rank: 'street' });
    vx.push({ c: W * 0.72 + jit(), half: 45, rank: 'street' });
    hy.push({ c: H * 0.25 + jit(), half: 45, rank: 'street' });
    hy.push({ c: H * 0.75 + jit(), half: 45, rank: 'street' });
    vx.push({ c: W * 0.11 + jit() * 0.4, half: 26, rank: 'alley' });
    vx.push({ c: W * 0.89 + jit() * 0.4, half: 26, rank: 'alley' });
    hy.push({ c: H * 0.10 + jit() * 0.4, half: 24, rank: 'alley' });
    hy.push({ c: H * 0.90 + jit() * 0.4, half: 24, rank: 'alley' });
    function bySpan(a, b) { return a.c - b.c; }
    vx.sort(bySpan); hy.sort(bySpan);
    return { vx: vx, hy: hy };
  }

  function streetsOf(zoneId, W, H, o) {
    var G = root && root.AK_WORLDGEN;
    if (G && typeof G.planStreets === 'function') {
      try {
        var s = G.planStreets(zoneId, W, H, o);
        if (s && s.vx && s.hy && s.vx.length && s.hy.length) return s;
      } catch (_e) {}   // fall through -- a peer lane throwing must not take clutter down
    }
    return builtinStreets(zoneId, W, H, o);
  }

  /* kerbsOf -- the two edges of every street band, as directed lines.
   * A kerb line is {axis:'v'|'h', at, lo, hi, nx, ny, rank} where (nx,ny) points AWAY from the
   * carriageway, i.e. toward the pavement. That normal is the whole reason this returns lines
   * instead of bands: a lamp goes lampIn INSIDE the kerb, a dumpster goes lanePad OUTSIDE it, and
   * a newsbox faces the road. Every one of those is "kerb position +- k * normal", so getting the
   * normal right once removes a class of sign errors from four placement passes.
   */
  function kerbsOf(streets, W, H) {
    var out = [], i, b;
    for (i = 0; i < streets.vx.length; i++) {
      b = streets.vx[i];
      out.push({ axis: 'v', at: b.c - b.half, lo: 0, hi: H, nx: -1, ny: 0, rank: b.rank, c: b.c, half: b.half });
      out.push({ axis: 'v', at: b.c + b.half, lo: 0, hi: H, nx:  1, ny: 0, rank: b.rank, c: b.c, half: b.half });
    }
    for (i = 0; i < streets.hy.length; i++) {
      b = streets.hy[i];
      out.push({ axis: 'h', at: b.c - b.half, lo: 0, hi: W, nx: 0, ny: -1, rank: b.rank, c: b.c, half: b.half });
      out.push({ axis: 'h', at: b.c + b.half, lo: 0, hi: W, nx: 0, ny:  1, rank: b.rank, c: b.c, half: b.half });
    }
    return out;
  }

  // Point-in-any-street-band. Used to keep ground marks IN the road.
  function inStreet(streets, x, y, pad) {
    var p = pad || 0, i;
    for (i = 0; i < streets.vx.length; i++) if (Math.abs(x - streets.vx[i].c) < streets.vx[i].half + p) return true;
    for (i = 0; i < streets.hy.length; i++) if (Math.abs(y - streets.hy[i].c) < streets.hy[i].half + p) return true;
    return false;
  }

  /* inLaneCentre -- the actual "off the walkable path" rule, and it is NOT the same as "out of the
   * street band". That distinction was forced by a measurement, not by taste.
   *
   * The first version of this file rejected any standing prop inside a street band plus a 26-unit
   * pad, on the theory that props belong on the pavement. That works against the stock 4-building
   * district, which is 95% empty ground. It collapses against the enlarged one: akworldgen insets
   * its lots from the block rect by pad 7 (akworldgen.js CFG.pad), so a generated building comes
   * within 7 units of the street band edge and THERE IS NO PAVEMENT. Measured consequence: the
   * frontage pass logged 1623 keep-out rejections and the 119-structure district came back with
   * FEWER props than the 4-building one.
   *
   * The rule that is actually true of a street is that the MIDDLE is for traffic and the EDGE is
   * where the bins, bags, hydrants and lamps live. So a standing prop may stand in the outer half
   * of a band and never in the inner half. On a main avenue (half 75) that reserves a 75-unit
   * clear channel down the middle; on a rim alley (half 26) it reserves 26, and the passability
   * rule in planClutter guarantees a walkable gap on top of that. */
  function inLaneCentre(streets, x, y) {
    var i, b;
    for (i = 0; i < streets.vx.length; i++) { b = streets.vx[i]; if (Math.abs(x - b.c) < b.half * 0.5) return true; }
    for (i = 0; i < streets.hy.length; i++) { b = streets.hy[i]; if (Math.abs(y - b.c) < b.half * 0.5) return true; }
    return false;
  }

  /* nearestKerb -- the kerb line a point should be dressed against, plus which way the street is.
   * Returns {kerb, dist, at, along} or null. This is what lets the frontage pass put a prop
   * against the STREET-FACING wall of a generated building instead of against a random face:
   * a bin in a 46-unit alley between two 150-unit-tall boxes is invisible from the 52-degree
   * camera (world3d.js DEFAULT_PHI) and is a draw call spent on nothing. */
  function nearestKerb(kerbs, x, y) {
    var best = null, bd = Infinity, i, d;
    for (i = 0; i < kerbs.length; i++) {
      var kk = kerbs[i];
      d = (kk.axis === 'v') ? Math.abs(x - kk.at) : Math.abs(y - kk.at);
      if (d < bd) { bd = d; best = kk; }
    }
    if (!best) return null;
    return { kerb: best, dist: bd, along: (best.axis === 'v') ? y : x };
  }

  /* ==========================================================================================
   * KEEP-OUTS. Rects are {x,y,w,h} with x,y = TOP-LEFT, matching AK_COLLISION's convention
   * (worldmap.js). Building records are the OPPOSITE (index.html:788 B() -- x,y = CENTRE, w/h the
   * full extent, hit-tested at index.html:826 as |tx-b.x| < b.w/2). akworldgen.js:186 flags this
   * as the single easiest bug to write in a file like this, so every conversion goes through
   * rectOfBld() and nothing hand-rolls it.
   * ========================================================================================= */
  function overlaps(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }
  function grow(r, m) { return { x: r.x - m, y: r.y - m, w: r.w + m * 2, h: r.h + m * 2 }; }
  function rectOfBld(b) { return { x: b.x - (b.w || 160) / 2, y: b.y - (b.h || 96) / 2, w: (b.w || 160), h: (b.h || 96) }; }
  function hitsAny(r, list) {
    for (var i = 0; i < list.length; i++) if (overlaps(r, list[i])) return true;
    return false;
  }

  /* obstacleRects -- AK_COLLISION carries two shapes: rects with x,y = TOP-LEFT and circles with
   * x,y = CENTRE plus r (worldmap.js:306 blocks() distinguishes them exactly this way). Normalise
   * both to AABBs. A circle becomes its bounding square, over-reserving the corners by ~21% of the
   * disc area, which is the right direction to be wrong in: the cost is one missing crate and the
   * alternative is a crate growing out of a junked car. */
  function obstacleRects(obs, margin) {
    var out = [], i, o;
    if (!obs || !obs.length) return out;
    for (i = 0; i < obs.length; i++) {
      o = obs[i]; if (!o) continue;
      if (o.type === 'circle') out.push(grow({ x: o.x - (o.r || 0), y: o.y - (o.r || 0), w: (o.r || 0) * 2, h: (o.r || 0) * 2 }, margin));
      else out.push(grow({ x: o.x, y: o.y, w: o.w || 0, h: o.h || 0 }, margin));
    }
    return out;
  }

  function obstaclesOf(zone, override) {
    if (override) return override;
    try {
      var C = root && root.AK_COLLISION;
      if (C && typeof C.obstaclesFor === 'function') return C.obstaclesFor(zone) || [];
    } catch (_e) {}
    return [];
  }

  /* keepOutsOf -- everything a STANDING prop must not touch. Ground decals run a much shorter
   * list (buildings only) because a puddle in a doorway is a puddle, not an obstruction.
   * Each rect carries a `why` for debuggability; order never matters for correctness. */
  function keepOutsOf(zone, o) {
    o = o || {};
    var W = o.worldW || 1700, H = o.worldH || 1300;
    var out = [], i, b, r;
    var blds = (zone && zone.buildings) || [];

    for (i = 0; i < blds.length; i++) {
      b = blds[i];
      r = grow(rectOfBld(b), CFG.bldPad); r.why = 'bld:' + b.id; out.push(r);
      // SOUTH APRON. Every door in this game is at (b.x, b.y + b.h/2) -- worldmap.js validPlacement
      // fixes it -- and exitInterior (index.html:1345) drops the player at b.y + b.h/2 + me.r + 85.
      // Walking out of the Town Hall into a dumpster is the exact failure this rect prevents.
      out.push({
        x: b.x - Math.max(60, (b.w || 160) / 2), y: b.y + (b.h || 96) / 2,
        w: Math.max(120, (b.w || 160)), h: CFG.doorApron, why: 'door:' + b.id
      });
    }

    // Painted obstacles. READ-ONLY: we never mutate, reorder or filter AK_COLLISION's array --
    // AK_HARVEST (worldmap.js) salvages the same objects and a reordered list would repoint it.
    var obs = obstaclesOf(zone, o.obstacles);
    var orects = obstacleRects(obs, CFG.obsMargin);
    for (i = 0; i < orects.length; i++) { orects[i].why = 'obs'; out.push(orects[i]); }

    // Generated background city, when the worldscale lane is live. Its structures are the frontage
    // our props line, so we must not stand INSIDE one -- rectOfSpec is its own conversion
    // (akworldgen.js:196), reproduced here rather than called so this stays a pure function.
    var gen = o.structures || null;
    if (!gen) {
      try {
        var G = root && root.AK_WORLDGEN;
        if (G && typeof G.structures === 'function') {
          var plan = G.plan && G.plan();
          if (plan && plan.zoneId === ((zone && zone.id) || '')) gen = G.structures();
        }
      } catch (_e) {}
    }
    if (gen && gen.length) {
      for (i = 0; i < gen.length; i++) {
        var s = gen[i];
        out.push({ x: s.x - s.w / 2, y: s.y - s.d / 2, w: s.w, h: s.d, why: 'gen:' + s.id });
      }
    }

    // The four district edge spawns (index.html:799 -- every edge record spawns at x=150/1550 with
    // y=650, or y=150/1150 with x=850) and the centre plaza. Discs expressed as their bounding
    // squares; the over-reserve at the corners is deliberate slack around a teleport landing spot.
    var sp = [[150, H / 2], [W - 150, H / 2], [W / 2, 150], [W / 2, H - 150]];
    for (i = 0; i < sp.length; i++) {
      out.push({ x: sp[i][0] - CFG.spawnR, y: sp[i][1] - CFG.spawnR, w: CFG.spawnR * 2, h: CFG.spawnR * 2, why: 'spawn' });
    }
    out.push({ x: W / 2 - CFG.plazaR, y: H / 2 - CFG.plazaR, w: CFG.plazaR * 2, h: CFG.plazaR * 2, why: 'plaza' });

    return out;
  }

  // Ground decals only dodge the building footprints themselves. Not the door apron (a manhole
  // outside a door is correct), not the spawn discs, not the plaza.
  function decalKeepOutsOf(zone) {
    var out = [], blds = (zone && zone.buildings) || [], i;
    for (i = 0; i < blds.length; i++) out.push(grow(rectOfBld(blds[i]), 6));
    return out;
  }

  /* ==========================================================================================
   * DE-CONFLICT WITH akstream's SCATTER.
   * Re-derives its prop list from its own exported pure planner using its own exported config, so
   * the list we test against is the list it actually baked. Returns [] when that lane is absent,
   * which makes the whole de-conflict a no-op rather than an error.
   * ========================================================================================= */
  function akstreamProps(zone, W, H) {
    try {
      var S = root && root.AK_STREAM;
      if (!S || typeof S.planClutter !== 'function') return [];
      var c = S.config || {};
      return S.planClutter({
        zone: zone, worldW: W, worldH: H,
        attempts: c.attempts, spacing: c.spacing,
        spawn: { x: W / 2, y: H / 2, r: 110 }
      }) || [];
    } catch (_e) { return []; }
  }

  /* ==========================================================================================
   * THE PLANNER. Pure: same arguments in, byte-identical props out, on any machine.
   * ========================================================================================= */

  function makeOcc(cell) {
    var occ = Object.create(null);
    return {
      free: function (x, y, foot) {
        // Check the 3x3 neighbourhood, not just the home cell. A single-cell check lets two props
        // sit 1 unit apart across a cell boundary, which is exactly where a "pile" comes from.
        var need = Math.max(1, Math.ceil((foot || cell) / cell / 2));
        var cx = Math.floor(x / cell), cy = Math.floor(y / cell), i, j;
        for (i = -need; i <= need; i++) {
          for (j = -need; j <= need; j++) if (occ[(cx + i) + ',' + (cy + j)]) return false;
        }
        return true;
      },
      take: function (x, y) { occ[Math.floor(x / cell) + ',' + Math.floor(y / cell)] = 1; }
    };
  }

  /* planClutter(o) -> { props:[...], stats:{...}, rejected:{...} }
   *
   * A prop record is {k, v, x, y, rot, scale, tint, ground} in HUB world space (x,y), which is
   * what AK_INSTANCE's default 'hub' item space consumes directly (akinstance.js:319 maps
   * hub y -> three z and item.h -> three y). No conversion happens anywhere else in this file.
   */
  function planClutter(o) {
    o = o || {};
    var zone   = o.zone || { id: 'HOME_TURF', buildings: [] };
    var zid    = zone.id || 'ZONE';
    var W      = o.worldW > 0 ? o.worldW : 1700;
    var H      = o.worldH > 0 ? o.worldH : 1300;
    var q      = (typeof o.quality === 'number') ? Math.max(0, Math.min(1, o.quality)) : CFG.quality;
    var maxVar = q < 0.55 ? 1 : (q < 0.85 ? 2 : 3);

    var streets  = o.streets || streetsOf(zid, W, H, o);
    var kerbs    = kerbsOf(streets, W, H);
    var keepOuts = o.keepOuts || keepOutsOf(zone, { worldW: W, worldH: H, obstacles: o.obstacles, structures: o.structures });
    var decalKO  = decalKeepOutsOf(zone);
    var others   = (o.dedupe === false) ? [] : (o.others || akstreamProps(zone, W, H));

    // The seed idiom mirrors index.html genProps and akstream.js:556: a raid zone carries its own
    // propSeed, so a rival's block gets its own layout while a normal district is stable forever.
    var seed = (zone.propSeed | 0) || (91733 + zid.length * 137 + zid.charCodeAt(0));
    var rnd  = rngFor('akclutter:' + zid + ':' + seed);

    var occ = makeOcc(CFG.spacing);
    var props = [];
    var rej = { edge: 0, keepOut: 0, packed: 0, dedupe: 0, lane: 0, road: 0, pass: 0 };

    /* PASSABILITY. Every standing prop is recorded as a disc ALREADY INFLATED BY THE PLAYER
     * RADIUS, which is configuration space: the player becomes a point and an obstacle becomes
     * its footprint grown by me.r. Two inflated discs that touch are a wall the point cannot get
     * through, no matter how far apart their visual footprints look.
     *
     * This is not theory. The first build of this file had no such rule and the walkability test
     * came back with the TROPHY door unreachable from the plaza and only 43% of the district
     * open, because the 168-unit lamp runs and the randomly-placed edge furniture interlocked
     * into a continuous line along every kerb. The lamps alone were passable (96 units of gap);
     * one dumpster landing in that gap sealed it. Enforcing the gap between EVERY pair of
     * standing props is the fix, and it is also just better placement -- real streets leave room
     * to walk between the bins. */
    var solids = [];
    function passable(x, y, rad) {
      for (var si = 0; si < solids.length; si++) {
        var s = solids[si];
        var dx = s.x - x, dy = s.y - y;
        var need = s.rad + rad + CFG.passGap;
        if (dx * dx + dy * dy < need * need) return false;
      }
      return true;
    }

    function tooCloseToOther(x, y) {
      var R = CFG.dedupR, i, d;
      for (i = 0; i < others.length; i++) {
        d = (others[i].x - x) * (others[i].x - x) + (others[i].y - y) * (others[i].y - y);
        if (d < R * R) return true;
      }
      return false;
    }

    // The one funnel every prop goes through. Returns the record it pushed, or null.
    function place(k, x, y, rot, opt) {
      opt = opt || {};
      var def = KIND_BY_NAME[k]; if (!def) return null;
      var half = def.foot / 2;
      if (x - half < CFG.rim || y - half < CFG.rim || x + half > W - CFG.rim || y + half > H - CFG.rim) { rej.edge++; return null; }

      var r = { x: x - half, y: y - half, w: def.foot, h: def.foot };
      if (hitsAny(r, def.ground ? decalKO : keepOuts)) { rej.keepOut++; return null; }

      // Carriageway rule, and it runs in BOTH directions:
      //   a standing prop must stay OUT of the middle of a lane (see inLaneCentre)
      //   a road mark must be IN a band (a manhole in the middle of a lot is not a manhole)
      if (!def.ground && !opt.allowLane && inLaneCentre(streets, x, y)) { rej.lane++; return null; }
      if (opt.needRoad && !inStreet(streets, x, y, -4)) { rej.road++; return null; }

      if (!occ.free(x, y, def.foot)) { rej.packed++; return null; }
      if (!def.ground && tooCloseToOther(x, y)) { rej.dedupe++; return null; }

      // Draw scale BEFORE the passability test, because the inflated radius depends on it and a
      // test run against a different scale than the one we store is a test that proves nothing.
      var scl = opt.scale != null ? opt.scale : (0.88 + rnd() * 0.26);
      if (!def.ground) {
        var rad = def.foot / 2 * scl + CFG.playerR;
        if (!passable(x, y, rad)) { rej.pass++; return null; }
        solids.push({ x: x, y: y, rad: rad });
      }

      occ.take(x, y);
      var rec = {
        k: k, v: (def.vars > 1) ? Math.floor(rnd() * Math.min(def.vars, maxVar)) : 0,
        x: x, y: y, rot: rot || 0, ground: !!def.ground,
        // Scale jitter is free per-instance (akinstance.js:328) and it is the cheapest way to stop
        // 180 identical lamps reading as 180 identical lamps.
        scale: scl,
        // Tint is a DARKENING multiply, never a recolour -- see the header's tint trap note.
        tint: opt.tint != null ? opt.tint : tintOf(rnd())
      };
      props.push(rec);
      return rec;
    }

    // Grey multiplier in 0x8e..0xff. Kept above 0x8e because below that a prop stops reading as
    // the same object and starts reading as a hole in the ground.
    function tintOf(u) {
      var g = 142 + Math.floor(u * 113);
      return (g << 16) | (g << 8) | g;
    }

    /* ---- PASS 1: LAMP RUNS. The pass that makes a road read as a road. -----------------------
     * Lamps march down the inside of a kerb at a FIXED interval. The interval is the point: even
     * spacing is what the eye reads as a built street. Only 'main' and 'street' rank kerbs get
     * lamps -- a 26-unit rim alley (akworldgen.js:240) with street lighting reads wrong.
     * Every lamp emits a POOL decal at its foot, which is the near-field payoff: a pool of warm
     * light on wet asphalt at 40 units away is worth more depth cue than a whole extra building.
     */
    var i, kk, t, px, py;
    for (i = 0; i < kerbs.length; i++) {
      kk = kerbs[i];
      if (kk.rank === 'alley') continue;
      var gap = CFG.lampGap * (q < 0.55 ? 1.75 : (q < 0.85 ? 1.28 : 1));
      // Phase-offset each run by its own seeded fraction so opposite kerbs are not mirror images,
      // which at this camera pitch is instantly legible as a grid.
      var ph = rngFor('lamp:' + zid + ':' + i)() * gap;
      var span = (kk.axis === 'v') ? H : W;
      for (t = CFG.rim + ph; t < span - CFG.rim; t += gap) {
        if (kk.axis === 'v') { px = kk.at - kk.nx * CFG.lampIn; py = t; }
        else                 { px = t; py = kk.at - kk.ny * CFG.lampIn; }
        // A lamp stands just inside the kerb, i.e. technically in the band, so it is allowed to
        // bypass the carriageway rule -- that is what allowLane is for and it is the only caller.
        var lamp = place('LAMP', px, py, Math.atan2(kk.ny, kk.nx), { allowLane: true, scale: 0.95 + rnd() * 0.12 });
        if (!lamp) continue;
        // The pool is placed WITHOUT the occupancy lattice caring, because it is flat and it is
        // supposed to sit under the thing that just claimed the cell. It goes in directly.
        props.push({
          k: 'POOL', v: 0, x: px + kk.nx * 6, y: py + kk.ny * 6, rot: 0, ground: true,
          scale: 0.9 + rnd() * 0.3, tint: 0xffffff
        });
      }
    }

    /* ---- PASS 2: KERB STRIPS ---------------------------------------------------------------
     * A low concrete lip along the road edge. This is the single highest-value ground detail in
     * the file: it draws the boundary between carriageway and pavement, and without it the street
     * lattice is invisible because the ground plate is one continuous texture across both.
     */
    for (i = 0; i < kerbs.length; i++) {
      kk = kerbs[i];
      var klen = CFG.kerbLen, kspan = (kk.axis === 'v') ? H : W;
      var kstep = klen + 8;                       // small gaps so it reads as laid sections
      for (t = CFG.rim; t < kspan - CFG.rim; t += kstep) {
        if (kk.axis === 'v') { px = kk.at; py = t + klen / 2; }
        else                 { px = t + klen / 2; py = kk.at; }
        // Kerbs skip the whole rejection funnel except the world rim and the building footprints:
        // a kerb is part of the road surface, so it may pass a door apron and a spawn disc.
        if (px < CFG.rim || py < CFG.rim || px > W - CFG.rim || py > H - CFG.rim) { rej.edge++; continue; }
        var kr = { x: px - 10, y: py - 10, w: 20, h: 20 };
        if (hitsAny(kr, decalKO)) { rej.keepOut++; continue; }
        props.push({
          k: 'KERB', v: 0, x: px, y: py, rot: (kk.axis === 'v') ? Math.PI / 2 : 0,
          ground: true, scale: 1, tint: 0xffffff
        });
      }
    }

    /* ---- PASS 3: CROSSWALKS at the main intersection ----------------------------------------
     * Only at the plaza crossroads, where the two 'main' bands meet. Four ladders, one per arm.
     * They are the one piece of ground detail with a legible SHAPE, which is why they go exactly
     * where the player's eye already is (the plaza is the district's hub and every edge corridor
     * leads to it).
     */
    var mainV = null, mainH = null;
    for (i = 0; i < streets.vx.length; i++) if (streets.vx[i].rank === 'main') mainV = streets.vx[i];
    for (i = 0; i < streets.hy.length; i++) if (streets.hy[i].rank === 'main') mainH = streets.hy[i];
    if (mainV && mainH && q >= 0.4) {
      var arms = [
        { x: mainV.c, y: mainH.c - mainH.half - 26, rot: 0 },
        { x: mainV.c, y: mainH.c + mainH.half + 26, rot: 0 },
        { x: mainV.c - mainV.half - 26, y: mainH.c, rot: Math.PI / 2 },
        { x: mainV.c + mainV.half + 26, y: mainH.c, rot: Math.PI / 2 }
      ];
      for (i = 0; i < arms.length; i++) {
        var a = arms[i], n = 5;                   // 5 stripes reads as a crossing, 3 reads as a patch
        for (var s2 = 0; s2 < n; s2++) {
          var off = (s2 - (n - 1) / 2) * 26;
          var cx2 = a.rot === 0 ? a.x + off : a.x;
          var cy2 = a.rot === 0 ? a.y : a.y + off;
          props.push({ k: 'CROSSWALK', v: 0, x: cx2, y: cy2, rot: a.rot, ground: true, scale: 1, tint: 0xffffff });
        }
      }
    }

    /* ---- PASS 4: ROAD MARKS ----------------------------------------------------------------
     * Puddles, manholes, grates, oil stains -- IN the carriageway (needRoad), which is the one
     * place the player walks and therefore the one place near-field detail is actually near.
     */
    var nRoad = Math.round(CFG.roadMarks * (0.35 + q * 0.65)), got = 0;
    for (i = 0; i < nRoad * 8 && got < nRoad; i++) {
      px = CFG.rim + rnd() * (W - CFG.rim * 2);
      py = CFG.rim + rnd() * (H - CFG.rim * 2);
      if (place(pickWeighted(POOL_ROAD, rnd()), px, py, rnd() * Math.PI * 2, { needRoad: true })) got++;
    }

    /* ---- PASS 5: BLOCK-EDGE FURNITURE ------------------------------------------------------
     * Bins, bags, crates, fence runs pressed against the OUTSIDE of a kerb line, i.e. on the
     * pavement with their backs to the block. This is the pass that produces the alley look:
     * clutter accumulates where the street meets the building line, never in the open.
     */
    var nEdge = Math.round(CFG.edgeProps * (0.3 + q * 0.7)); got = 0;
    for (i = 0; i < nEdge * 8 && got < nEdge; i++) {
      kk = kerbs[Math.floor(rnd() * kerbs.length)];
      // Straddle the kerb: negative d2 = road side (against the kerb), positive = pavement side.
      // Both are correct places for clutter and using both is what makes a street edge read as
      // lived-in rather than as a tidy line of objects on one side.
      var d2 = -14 + rnd() * 74;
      var along = CFG.rim + rnd() * (((kk.axis === 'v') ? H : W) - CFG.rim * 2);
      if (kk.axis === 'v') { px = kk.at + kk.nx * d2; py = along; }
      else                 { px = along; py = kk.at + kk.ny * d2; }
      // Face the road. atan2(ny,nx) is the outward normal, so +PI turns the prop back around.
      if (place(pickWeighted(POOL_EDGE, rnd()), px, py, Math.atan2(kk.ny, kk.nx) + Math.PI + (rnd() - 0.5) * 0.4)) got++;
    }

    /* ---- PASS 6: FRONTAGE against the generated city ---------------------------------------
     * This pass is the reason the lane scales. With the stock 4-building district it places
     * almost nothing, because there is almost nothing to lean against. With AK_WORLDGEN live and
     * 60-120 structures in the district, every one of them has a street-facing wall that wants
     * bags against it, and the prop count goes from dozens to hundreds. That is the operator's
     * directive discharged in code: the technique does not shrink to fit a small world, the world
     * grows until the technique is load-bearing.
     */
    var gen = o.structures || genStructures(zone);
    if (gen && gen.length) {
      // Per-pass counter, NOT a scan of everything placed so far. The first build of this file
      // counted "props whose kind is in POOL_FRONT", and because the edge pass draws from an
      // overlapping kind set it had already satisfied the frontage budget before the frontage
      // pass ran a single iteration. The symptom was the one that matters: a 90-structure
      // district came back with FEWER props than a 4-building one, i.e. the lane got quieter
      // exactly as the world got bigger.
      var nFront = Math.round(Math.min(CFG.frontMax, gen.length * CFG.frontPerStruct) * (0.3 + q * 0.7)); got = 0;
      for (i = 0; i < nFront * 8 && got < nFront; i++) {
        var g = gen[Math.floor(rnd() * gen.length)];
        // Dress the STREET-FACING side. Find the kerb line this structure addresses, then stand
        // the prop just inside it, level with the structure, jittered along the frontage. This is
        // the pass that scales with the world: 119 structures address 119 stretches of kerb, and
        // every one of them gets bins and bags in proportion to how much frontage it has.
        /* Two sub-passes, because the enlarged district has two kinds of space and only one of
         * them is on the street lattice.
         *
         * ALLEY (40%): akworldgen holds a hard ALLEY_MIN of 46 units between the two frontage
         * strips of a double-loaded block. That gap exists ONLY when generated structures exist,
         * it is invisible to the kerb-based placement, and it is the single most alley-like space
         * in the game. Props go hard against a wall so the 46 units still walk. If the neighbour
         * is closer than that, the keep-out test rejects and nothing is lost.
         * KERB (60%): the street-facing wall, as below. */
        if (rnd() < 0.4) {
          var gw2 = (g.w || 60) / 2, gd2 = (g.d || 60) / 2;
          var side = rnd();
          var ax, ay, arot;
          if (side < 0.42)      { ax = g.x + (rnd() - 0.5) * g.w * 0.7; ay = g.y + gd2 + 13 + rnd() * 9; arot = Math.PI; }
          else if (side < 0.64) { ax = g.x + (rnd() - 0.5) * g.w * 0.7; ay = g.y - gd2 - 13 - rnd() * 9; arot = 0; }
          else if (side < 0.82) { ax = g.x - gw2 - 13 - rnd() * 9; ay = g.y + (rnd() - 0.5) * g.d * 0.7; arot = Math.PI / 2; }
          else                  { ax = g.x + gw2 + 13 + rnd() * 9; ay = g.y + (rnd() - 0.5) * g.d * 0.7; arot = -Math.PI / 2; }
          if (place(pickWeighted(POOL_FRONT, rnd()), ax, ay, arot + (rnd() - 0.5) * 0.3)) got++;
          continue;
        }

        var nk = nearestKerb(kerbs, g.x, g.y);
        if (!nk) continue;
        var kb = nk.kerb;
        /* Stand INSIDE the band (against the kerb, road side), which is where a bin actually goes
         * and, more to the point, the only clear ground that exists once the generator has packed
         * the block.
         *
         * THE OFFSET IS CLAMPED TO THE BAND'S OWN WIDTH and that clamp is the difference between
         * this pass working and this pass doing nothing. Structures address whatever kerb is
         * nearest, and measured against the real generator the median structure is 29 units from
         * a RIM ALLEY (half 24-26), not from an avenue (half 75). A flat 18-40 unit offset sails
         * straight past an alley's outer half and into its centre, where inLaneCentre rejects it:
         * that logged 1439 lane rejections and left the 119-structure district with FEWER props
         * than the 4-building one. half * 0.45 keeps the prop in the outer half of whatever band
         * it actually found. */
        var into = Math.min(CFG.lampIn + 2 + rnd() * 22, (kb.half || 45) * 0.45);
        var jitAlong = (rnd() - 0.5) * ((kb.axis === 'v') ? (g.d || 60) : (g.w || 60)) * 1.5;
        if (kb.axis === 'v') { px = kb.at - kb.nx * into; py = g.y + jitAlong; }
        else                 { px = g.x + jitAlong;       py = kb.at - kb.ny * into; }
        // Face out of the road, i.e. back toward the building it belongs to.
        if (place(pickWeighted(POOL_FRONT, rnd()), px, py, Math.atan2(kb.ny, kb.nx) + (rnd() - 0.5) * 0.35)) got++;
      }
    }

    // ---- stats -------------------------------------------------------------------------------
    var byKind = {}, fields = {}, naive = 0;
    for (i = 0; i < props.length; i++) {
      var p = props[i], def = KIND_BY_NAME[p.k];
      byKind[p.k] = (byKind[p.k] || 0) + 1;
      fields[p.k + ':' + p.v] = 1;
      naive += def ? def.parts : 1;
    }
    var nFields = 0; for (kk in fields) if (fields.hasOwnProperty(kk)) nFields++;

    return {
      zoneId: zid, worldW: W, worldH: H, quality: q,
      streets: streets, kerbs: kerbs, keepOuts: keepOuts,
      props: props,
      stats: {
        props: props.length, byKind: byKind,
        fields: nFields,                 // = draw calls after merge + instance
        naiveDrawCalls: naive,           // = one Mesh per PART per prop
        mergedDrawCalls: props.length,   // = merged prop, still one Mesh each
        saved: naive - nFields,
        others: others.length,
        rejected: rej
      }
    };
  }

  function genStructures(zone) {
    try {
      var G = root && root.AK_WORLDGEN;
      if (!G || typeof G.structures !== 'function') return null;
      var plan = G.plan && G.plan();
      if (!plan || plan.zoneId !== ((zone && zone.id) || '')) return null;
      return G.structures();
    } catch (_e) { return null; }
  }

  /* ==========================================================================================
   * WALKABILITY PROOF.
   *
   * These props do not feed AK_COLLISION, so they CANNOT trap the player. This test therefore
   * proves a constraint we do not rely on, on purpose: if the placement is clean under the
   * strictest possible reading (every standing prop is solid, inflated by the player radius),
   * then it is certainly clean under the real one, and the day someone decides clutter should
   * collide, that change is already proven safe.
   *
   * Ground decals are not blockers. You walk over a puddle.
   *
   * Rasterise at `step`, flood-fill 4-connected from the plaza, report which targets were reached.
   * Targets: the four district edge spawns and a point 40 units south of every building door.
   * ========================================================================================= */
  function walkabilityOf(plan, zone, o) {
    o = o || {};
    var step = o.step || 20, pr = (typeof o.playerR === 'number') ? o.playerR : 23;
    var W = plan.worldW, H = plan.worldH;
    var cols = Math.ceil(W / step), rows = Math.ceil(H / step);
    var blocked = new Uint8Array(cols * rows);
    var i, cx, cy;

    // Mark blocked cells. A cell is blocked when its CENTRE falls inside a standing prop's
    // footprint inflated by the player radius.
    for (i = 0; i < plan.props.length; i++) {
      var p = plan.props[i];
      if (p.ground) continue;
      var def = KIND_BY_NAME[p.k]; if (!def) continue;
      var half = def.foot / 2 * (p.scale || 1) + pr;
      var x0 = Math.max(0, Math.floor((p.x - half) / step)), x1 = Math.min(cols - 1, Math.floor((p.x + half) / step));
      var y0 = Math.max(0, Math.floor((p.y - half) / step)), y1 = Math.min(rows - 1, Math.floor((p.y + half) / step));
      for (cy = y0; cy <= y1; cy++) for (cx = x0; cx <= x1; cx++) blocked[cy * cols + cx] = 1;
    }
    // Painted obstacles are blockers too -- they were already there, and a corridor that our props
    // leave open but a train blocks is not actually open.
    var orects = obstacleRects(obstaclesOf(zone, o.obstacles), pr);
    for (i = 0; i < orects.length; i++) {
      var r = orects[i];
      var ox0 = Math.max(0, Math.floor(r.x / step)), ox1 = Math.min(cols - 1, Math.floor((r.x + r.w) / step));
      var oy0 = Math.max(0, Math.floor(r.y / step)), oy1 = Math.min(rows - 1, Math.floor((r.y + r.h) / step));
      for (cy = oy0; cy <= oy1; cy++) for (cx = ox0; cx <= ox1; cx++) blocked[cy * cols + cx] = 1;
    }

    var seen = new Uint8Array(cols * rows);
    var sx = Math.floor((W / 2) / step), sy = Math.floor((H / 2) / step);
    var stack = [sy * cols + sx];
    seen[sy * cols + sx] = 1;
    var reachedCells = 0;
    while (stack.length) {
      var idx = stack.pop(); reachedCells++;
      var ix = idx % cols, iy = (idx - ix) / cols;
      var nb = [[ix + 1, iy], [ix - 1, iy], [ix, iy + 1], [ix, iy - 1]];
      for (i = 0; i < 4; i++) {
        var nx = nb[i][0], ny = nb[i][1];
        if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
        var ni = ny * cols + nx;
        if (seen[ni] || blocked[ni]) continue;
        seen[ni] = 1; stack.push(ni);
      }
    }

    function reach(x, y) {
      var gx = Math.max(0, Math.min(cols - 1, Math.floor(x / step)));
      var gy = Math.max(0, Math.min(rows - 1, Math.floor(y / step)));
      return !!seen[gy * cols + gx];
    }

    var targets = [
      { n: 'spawn:W', x: 150, y: H / 2 }, { n: 'spawn:E', x: W - 150, y: H / 2 },
      { n: 'spawn:N', x: W / 2, y: 150 }, { n: 'spawn:S', x: W / 2, y: H - 150 }
    ];
    var blds = (zone && zone.buildings) || [];
    for (i = 0; i < blds.length; i++) {
      targets.push({ n: 'door:' + blds[i].id, x: blds[i].x, y: blds[i].y + (blds[i].h || 96) / 2 + 40 });
    }

    var failed = [];
    for (i = 0; i < targets.length; i++) if (!reach(targets[i].x, targets[i].y)) failed.push(targets[i].n);

    return {
      ok: failed.length === 0, failed: failed, targets: targets.length,
      cells: cols * rows, reached: reachedCells,
      openPct: Math.round(reachedCells / (cols * rows) * 100)
    };
  }

  /* =========================================================================================
   * SCENE LAYER. Everything below needs THREE and AK_INSTANCE. Nothing here runs at load.
   * ========================================================================================= */

  var S = {
    zoneId: null, built: false, plan: null, ids: [], templates: [], mats: [],
    /* kinds: field id -> {k, v, mesh}. Kept as a real map instead of parsing the kind back out of
     * the mesh name, because district ids contain underscores (HOME_TURF, NEON_HEIGHTS,
     * FACTORY_ROW) and so does the id format, so any split('_') recovery is wrong for 7 of the 9
     * districts. Diagnostics and the proof harness both read this. */
    kinds: {},
    buildMs: 0, errors: 0, lastErr: null, frames: 0, pending: false
  };

  function note(e) { S.errors++; S.lastErr = String((e && e.message) || e); }

  // Test seam, same idiom as akinstance.js:69 _engine: the headless proof injects the REAL
  // vendored r160 here because node has no window.AK_THREE gate to read.
  var _engine = null;

  function three() {
    if (_engine) return _engine;
    try {
      var T = root && root.AK_THREE;
      if (T && typeof T.ok === 'function' && T.ok()) return (typeof T.get === 'function' && T.get()) || null;
      if (root && root.THREE && root.THREE.InstancedMesh) return root.THREE;
    } catch (_e) {}
    return null;
  }
  function inst() { return (root && root.AK_INSTANCE) || null; }
  function w3scene() {
    try { var W = root && root.AK_WORLD3D; return (W && W._state && W._state.scene) || null; } catch (_e) { return null; }
  }

  /* ------------------------------------------------------------------------------------------
   * TEMPLATE GEOMETRY. Each kind+variant is a list of PART RECORDS in the template's own local
   * space, origin at the prop's foot (y = 0 is the ground). AK_INSTANCE.merge() collapses them
   * into one geometry with baked vertex colours, so a 6-box fence becomes one draw call before
   * instancing even starts.
   *
   * Ground kinds emit a PLANE part (rotated flat) rather than a thin box. A box has six faces and
   * an additive-blended box double-blends at every silhouette edge, which puts a bright rim around
   * every light pool. One plane, one blend, correct.
   * ---------------------------------------------------------------------------------------- */
  function partsFor(THREE, kind, v, sink) {
    var r = rngFor('akclutter:tmpl:' + kind + ':' + v);
    function B(w, h, d, c, x, y, z, ry) {
      var p = { w: w, h: h, d: d, c: c, x: x || 0, y: y || 0, z: z || 0 };
      if (ry) p.ry = ry;
      sink.push(p);
    }
    // A flat quad on the ground. PlaneGeometry is born in the XY plane facing +z, so -PI/2 about
    // x lays it down facing +y. This is the same rotation world3d.js:499 applies to its ground.
    /* A flat quad on the ground. PlaneGeometry is born in the XY plane facing +z, so -PI/2 about
     * x lays it down facing +y -- the same rotation world3d.js:499 applies to its ground plane.
     *
     * THERE IS NO ry PARAMETER AND THAT IS DELIBERATE. merge() composes the part transform from a
     * single Euler in three's default XYZ order (akinstance.js:184), so an ry stacked on top of
     * rx=-PI/2 does NOT spin the quad in its own plane -- it tilts it out of horizontal. Measured
     * against r160: with rx=-PI/2 and ry=0.5, local +x lands at y=-4.79, so a 26-unit quad dips
     * nearly 5 units through the ground plane. The proof harness caught it as 12 sub-ground
     * vertices. In-plane spin belongs on the INSTANCE (item.rot), which AK_INSTANCE applies as a
     * pure yaw about world Y (akinstance.js:323) and which is therefore always flat-preserving. */
    function P(w, d, c, y) {
      sink.push({ geometry: new THREE.PlaneGeometry(w, d), rx: -Math.PI / 2, y: y, color: c });
    }
    var yBase = CFG.decalY + (KIND_BY_NAME[kind] && KIND_BY_NAME[kind].layer != null ? KIND_BY_NAME[kind].layer * CFG.decalStep : 0);

    switch (kind) {
      /* --- ground detail -------------------------------------------------------------------- */
      case 'POOL':
        // The lamp's light pool. NOT a light: world3d.js:638 runs exactly two lights for the whole
        // scene, and 180 PointLights would end the frame. This is a warm additive disc, which at
        // the 52-degree pitch is indistinguishable from a real pool of lamplight and costs nothing.
        P(CFG.poolR * 2, CFG.poolR * 2, C_GLOW, yBase);
        break;
      case 'PUDDLE':
        // Two overlapping offset quads, because a single quad reads as a rectangle and a puddle
        // must not have a straight edge. Variant changes the offset, which is the whole shape.
        P(52 + r() * 22, 34 + r() * 18, C_WET, yBase);
        P(30 + r() * 26, 26 + r() * 16, C_WET, yBase + 0.05);
        break;
      case 'MANHOLE':
        P(30, 30, C_IRON, yBase);
        P(22, 22, C_DARK, yBase + 0.05);
        break;
      case 'GRATE':
        // The bars are BOXES, so their centre must sit half their height above the decal plane or
        // their underside dips below it and z-fights the ground. That is not hypothetical: the
        // first build put them at yBase + 0.1 with height 1.2, i.e. 0.5 units UNDER the plane, and
        // the proof harness counted 84 offending vertices. Centre = yBase + h/2, always.
        P(36, 24, C_DARK, yBase);
        B(34, 1.2, 3, C_IRON, 0, yBase + 0.6, -7);
        B(34, 1.2, 3, C_IRON, 0, yBase + 0.6, -2);
        B(34, 1.2, 3, C_IRON, 0, yBase + 0.6, 3);
        B(34, 1.2, 3, C_IRON, 0, yBase + 0.6, 8);
        break;
      case 'STAIN':
        P(58 + r() * 24, 40 + r() * 20, C_OIL, yBase);
        P(30 + r() * 20, 24 + r() * 14, C_OIL, yBase + 0.05);
        break;
      case 'CROSSWALK':
        P(16, 44, C_PAINT, yBase);
        break;
      case 'KERB':
        // Not flat: a kerb is a LIP, and the tiny 6-unit rise is what catches the directional
        // light (world3d.js:642) and draws the road edge as a line instead of a colour change.
        B(CFG.kerbLen, 6, CFG.kerbW, C_KERB, 0, 3, 0);
        break;

      /* --- standing furniture ---------------------------------------------------------------- */
      case 'LAMP':
        // Tallest emitter in the file at 78 units. akstream's makeProjTest sizes its chunk
        // residency test to topH 80 (akstream.js:461), so this deliberately stays under that --
        // a prop taller than the streaming test's assumed ceiling pops in late at the screen edge.
        B(9, 3, 9, C_TRIM, 0, 1.5, 0);
        B(4, 74, 4, C_LAMP, 0, 38, 0);
        B(16, 5, 6, C_LAMP, 5, 74, 0);
        B(9, 3, 5, C_GLOW, 8, 71, 0);
        break;
      case 'HYDRANT':
        B(9, 16, 9, C_RED, 0, 8, 0);
        B(13, 4, 13, C_RED, 0, 17, 0);
        B(4, 5, 9, C_RED, 6, 10, 0);
        break;
      case 'BOLLARD':
        B(8, 22, 8, C_METAL, 0, 11, 0);
        B(10, 3, 10, C_TRIM, 0, 22, 0);
        break;
      case 'CONE':
        B(14, 3, 14, C_RED, 0, 1.5, 0);
        B(7, 18, 7, C_RED, 0, 11, 0);
        break;
      case 'FENCE': {
        // Chain-link run: two posts, a top rail, and mesh panels faked as thin slabs. Variant 1
        // leans a panel, which is what stops a long fence run from reading as extruded wallpaper.
        var lean = v === 1 ? 0.16 : 0;
        B(5, 44, 5, C_METAL, -34, 22, 0);
        B(5, 44, 5, C_METAL, 34, 22, 0);
        B(72, 3, 3, C_METAL, 0, 43, 0);
        B(34, 38, 1.6, C_GREY, -17, 21, 0);
        B(34, 38, 1.6, C_GREY, 17, 21 - lean * 20, 0);
        B(72, 2, 2, C_METAL, 0, 4, 0);
        break;
      }
      case 'DUMPSTER':
        B(46, 26, 26, C_GREEN, 0, 13, 0);
        B(48, 4, 28, C_DARK, 0, 27, 0);
        B(4, 8, 4, C_DARK, -20, 4, 11);
        B(4, 8, 4, C_DARK, 20, 4, 11);
        B(40, 3, 3, C_TRIM, 0, 20, -13);
        break;
      case 'CRATES': {
        // Variant IS the stack height. This is the one kind where per-instance scale cannot fake
        // the difference, because a 3-high stack scaled down is still visibly a 3-high stack.
        var stack = 1 + v, yy = 0, ci;
        for (ci = 0; ci <= stack; ci++) {
          var sz = 22 + r() * 8;
          B(sz, sz * 0.8, sz, C_WOOD, (r() - 0.5) * 6, yy + sz * 0.4, (r() - 0.5) * 6, (r() - 0.5) * 0.5);
          yy += sz * 0.8;
        }
        break;
      }
      case 'BAGS': {
        var bags = 2 + v, bi;
        for (bi = 0; bi <= bags; bi++) {
          var bs = 13 + r() * 7;
          B(bs, bs * 0.9, bs * 0.9, C_BAG, (r() - 0.5) * 20, bs * 0.45, (r() - 0.5) * 16, r() * 1.2);
        }
        break;
      }
      case 'NEWSBOX':
        B(20, 30, 16, C_RUST, 0, 15, 0);
        B(22, 3, 18, C_TRIM, 0, 31, 0);
        B(14, 12, 1.5, C_DARK, 0, 20, 8.5);
        break;
      default:
        B(16, 16, 16, C_GREY, 0, 8, 0);
    }
    return sink;
  }

  /* materialFor -- three material policies, one per kind class, and the differences all matter.
   *   standing  Lambert + vertexColors. Lit by the same two lights as the buildings, so a crate
   *             and a wall agree about where the sun is.
   *   decal     Basic + transparent + depthWrite:false. Basic because a mark on the ground is a
   *             darkening of the ground, not a surface catching light -- a Lambert puddle goes
   *             BRIGHTER under the directional light, which is exactly backwards. depthWrite off
   *             so overlapping decals do not punch holes in each other.
   *   glow      as decal plus AdditiveBlending, for the lamp pool only.
   * renderOrder keeps decals after opaque geometry, which with depthWrite:false is required, not
   * cosmetic: a transparent surface drawn before the ground writes nothing and then the ground
   * paints over it.
   */
  function materialFor(THREE, def) {
    var m;
    if (def.glow) {
      m = new THREE.MeshBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.42,
        depthWrite: false, blending: THREE.AdditiveBlending
      });
    } else if (def.ground) {
      m = new THREE.MeshBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.82, depthWrite: false
      });
    } else {
      m = new THREE.MeshLambertMaterial({ vertexColors: true });
    }
    S.mats.push(m);
    return m;
  }

  /* buildFields -- plan -> AK_INSTANCE fields. ONE field per kind+variant that actually got used,
   * so an unused variant costs nothing. This is the integration point with the instancing lane and
   * it is the only place in this file that touches the scene.
   */
  function buildFields(plan) {
    var THREE = three(), I = inst();
    if (!THREE || !I) return 0;

    // Bucket props by kind+variant. Everything in one bucket shares a geometry, which is the
    // precondition for instancing and the reason variants exist as a separate axis at all.
    var buckets = {}, i, key;
    for (i = 0; i < plan.props.length; i++) {
      var p = plan.props[i];
      if (!KIND_BY_NAME[p.k]) continue;
      key = p.k + ':' + (p.v || 0);
      (buckets[key] || (buckets[key] = [])).push(p);
    }

    var made = 0;
    for (key in buckets) {
      if (!buckets.hasOwnProperty(key)) continue;
      var list = buckets[key];
      var kn = key.split(':')[0], vn = parseInt(key.split(':')[1], 10) || 0;
      var def = KIND_BY_NAME[kn];

      var parts = [];
      try { partsFor(THREE, kn, vn, parts); } catch (e) { note(e); continue; }
      var geo = I.merge(parts, {});
      // merge() clones every part, so the PlaneGeometry instances we handed it are ours to free.
      for (i = 0; i < parts.length; i++) {
        if (parts[i].geometry && parts[i].geometry.dispose) { try { parts[i].geometry.dispose(); } catch (_e) {} }
      }
      if (!geo) { note(new Error('merge failed for ' + key)); continue; }
      S.templates.push(geo);

      var mat = materialFor(THREE, def);
      var items = [];
      for (i = 0; i < list.length; i++) {
        items.push({
          x: list[i].x, y: list[i].y,
          h: 0,                                   // hub-space item: h is the THREE y. Props sit on
                                                  // the ground and the template already carries its
                                                  // own local height, so this is always 0.
          rot: list[i].rot || 0,
          scale: list[i].scale || 1,
          color: list[i].tint
        });
      }

      var id = 'akclutter_' + plan.zoneId + '_' + kn + '_' + vn;
      var handle = I.field({
        id: id, zone: plan.zoneId, geometry: geo, material: mat, items: items,
        // Static: the matrix buffer uploads once instead of every frame (akinstance.js:407).
        // Nothing in this lane animates.
        dynamic: false,
        renderOrder: def.ground ? (2 + (def.layer || 0)) : 0
      });
      S.ids.push(id);
      S.kinds[id] = { k: kn, v: vn, count: items.length, mesh: (handle && handle.mesh) || null };
      made++;
    }
    return made;
  }

  function teardown() {
    var I = inst(), i;
    for (i = 0; i < S.ids.length; i++) { try { I && I.remove(S.ids[i]); } catch (_e) {} }
    // AK_INSTANCE only disposes what IT created (akinstance.js:519 _ownGeo/_ownMat), and we passed
    // geometry+material in, so freeing them is our job. world3d.js:452 disposeScene() disposes
    // nothing at all and setZone (world3d.js:761) leaks materials and textures on every district
    // swap -- nine districts of round-tripping accumulates. This lane does not inherit that bug.
    for (i = 0; i < S.templates.length; i++) { try { S.templates[i].dispose(); } catch (_e) {} }
    for (i = 0; i < S.mats.length; i++) { try { S.mats[i].dispose(); } catch (_e) {} }
    S.ids = []; S.templates = []; S.mats = []; S.kinds = {};
    S.built = false; S.plan = null; S.zoneId = null;
    return true;
  }

  function build(ctx) {
    var THREE = three(); if (!THREE) return false;
    if (!inst()) return false;
    var sc = w3scene(); if (!sc) return false;             // world3d has not booted: stay queued
    var zone = (ctx && ctx.activeZone) || (root && root.activeZone);
    if (!zone) return false;

    var t0 = (root.performance && root.performance.now) ? root.performance.now() : Date.now();
    teardown();

    var W = 1700, H = 1300;
    try { if (ctx && ctx.world) { W = ctx.world.WORLD_W || W; H = ctx.world.WORLD_H || H; } } catch (_e) {}

    S.plan = planClutter({ zone: zone, worldW: W, worldH: H, quality: CFG.quality });
    S.zoneId = zone.id;
    buildFields(S.plan);
    S.built = true;
    S.buildMs = ((root.performance && root.performance.now) ? root.performance.now() : Date.now()) - t0;
    return true;
  }

  /* tick -- the per-frame path, and it is deliberately almost nothing.
   *
   * Zone change is a POLL, not an event: enterZone (index.html:1354) mutates activeZone and
   * notifies nobody, which is why world3d.js:900 also calls setZone(ctx) every tick. Same idiom
   * here, same reason. AK_INSTANCE's own tick (akinstance.js:681) already garbage-collects fields
   * whose zone no longer matches, so a district change frees our InstancedMeshes without us
   * asking -- but it does NOT free the geometry and materials we passed in, so teardown() still
   * runs on our side.
   *
   * Once built there is zero per-frame work: the fields are static, the matrices uploaded once,
   * and three culls the whole InstancedMesh by its bounding sphere for free.
   */
  function tick(dt, ctx) {
    S.frames++;
    var zid = (ctx && ctx.zoneId) || (ctx && ctx.activeZone && ctx.activeZone.id) || null;
    if (S.built && zid && zid !== S.zoneId) teardown();
    if (S.built) return false;
    // Retry cheaply until three + AK_INSTANCE + a live scene all exist. world3d boots three
    // ASYNCHRONOUSLY (world3d.js:741 awaits ready()) so the first few hundred frames legitimately
    // have no scene, and an init-time build would silently place nothing forever.
    if ((S.frames & 7) !== 0) return false;      // poll at ~7Hz, not every frame
    try { return build(ctx); } catch (e) { note(e); return false; }
  }

  /* Quality knob. Drives density AND variant count together, because on the device that needs
   * fewer props the extra draw call for a third crate variant is exactly the wrong thing to spend.
   * autoQuality mirrors akworldgen.js:634 autoDensity so the two lanes shed detail in step -- a
   * phone that gets the sparse city should not get the dense clutter. */
  function autoQuality() {
    try {
      var hc = (root.navigator && root.navigator.hardwareConcurrency) || 4;
      var dpr = root.devicePixelRatio || 1;
      if (hc <= 4 && dpr >= 2.5) return 0.45;
      if (hc <= 4) return 0.65;
      if (hc <= 6) return 0.85;
    } catch (_e) {}
    return 1.0;
  }

  function setQuality(v) {
    CFG.quality = (typeof v === 'number') ? Math.max(0, Math.min(1, v)) : autoQuality();
    if (S.built) teardown();                     // force a rebuild at the new quality
    return CFG.quality;
  }

  /* ==========================================================================================
   * EXPORTS
   * ========================================================================================= */
  var API = {
    version: function () { return VER; },
    // pure core
    planClutter: planClutter, walkabilityOf: walkabilityOf,
    streetsOf: streetsOf, builtinStreets: builtinStreets, kerbsOf: kerbsOf, inStreet: inStreet,
    keepOutsOf: keepOutsOf, decalKeepOutsOf: decalKeepOutsOf, obstacleRects: obstacleRects,
    akstreamProps: akstreamProps, rngFor: rngFor, hash: hash, overlaps: overlaps,
    KINDS: KINDS, KIND_BY_NAME: KIND_BY_NAME, config: CFG,
    // scene layer
    build: build, teardown: teardown, tick: tick, buildFields: buildFields, partsFor: partsFor,
    plan: function () { return S.plan; },
    props: function () { return S.plan ? S.plan.props.slice() : []; },
    fields: function () { return S.ids.slice(); },
    // the density knob the brief asks for
    setQuality: setQuality, autoQuality: autoQuality,
    set: function (k, v) { if (Object.prototype.hasOwnProperty.call(CFG, k)) { CFG[k] = v; return true; } return false; },
    /* Diagnostics. Errors are REPORTED, never swallowed -- a silent subsystem is how a corrupt
     * vendor file hid on this project for hours with zero console output. */
    diag: function () {
      var st = S.plan && S.plan.stats;
      return {
        version: VER, zone: S.zoneId, built: S.built, frames: S.frames,
        props: st ? st.props : 0, fields: S.ids.length,
        drawCallsNaive: st ? st.naiveDrawCalls : 0,
        drawCallsActual: S.ids.length,
        saved: st ? (st.naiveDrawCalls - S.ids.length) : 0,
        quality: CFG.quality, buildMs: Math.round(S.buildMs),
        errors: S.errors, lastError: S.lastErr,
        three: !!three(), instance: !!inst(), scene: !!w3scene(),
        peers: {
          worldgen: !!(root && root.AK_WORLDGEN), stream: !!(root && root.AK_STREAM),
          collision: !!(root && root.AK_COLLISION)
        },
        byKind: st ? st.byKind : null, rejected: st ? st.rejected : null
      };
    },
    selfTest: selfTest,
    _useEngine: function (T) { _engine = T || null; return _engine; },
    _state: S
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_CLUTTER = API;
    /* SELF-REGISTRATION. THIS IS THE INTEGRATION CALL SITE.
     * _registry.js:22 tickAll() is the caller, reached from index.html:3328 akTickSystems, which
     * index.html:2426 gates on state==='IN_ZONE' && !interiorOpen && !entering && !_sf.
     *
     * RAIDS: index.html:2436 ticks only ['raidwaves','raidfortify','backpack'] while state==='RAID'.
     * 'akclutter' is deliberately absent. A raid swaps WORLD_W/H to the raid map and freezes the 3D
     * renderer entirely (index.html:2426), so street furniture for a district you are not standing
     * in has nothing to do. This is a decision, not the index.html:2429 "dead on arrival" bug --
     * that bug is about systems that NEED raid ticks and silently never get them.
     *
     * init does no scene work on purpose: world3d boots three ASYNCHRONOUSLY (world3d.js:741) and
     * its scene does not exist at initAll() time. tick() polls for it at ~7Hz and builds on the
     * first frame all three preconditions are live. */
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({
          id: 'akclutter',
          init: function () { CFG.quality = autoQuality(); return true; },
          onTick: function (dt, ctx) { try { tick(dt, ctx); } catch (e) { note(e); } }
        });
      }
    } catch (_e) {}
  }

  /* ==========================================================================================
   * HEADLESS PROOF. Two halves:
   *   PURE   -- planner, keep-outs, determinism, walkability. No THREE needed.
   *   SCENE  -- real vendored three r160 + the real AK_INSTANCE, building real InstancedMeshes
   *             into a real Scene and counting real render items. No mocks: a stubbed THREE would
   *             happily "pass" a merge that three itself rejects, and that is precisely the class
   *             of bug that has shipped on this project before.
   * ========================================================================================= */
  function fixtureZone() {
    function B(id, label, col, x, y, w, h) { return { id: id, label: label, col: col, x: x, y: y, w: w, h: h }; }
    // Verbatim from index.html:806 HOME_TURF -- the spawn district and the worst case at 4 buildings.
    return {
      id: 'HOME_TURF', name: 'THE LOT', gx: 1, gy: 1, ground: 'uptown',
      buildings: [
        B('ARENA', 'TOWN HALL', '#e8c55a', 850, 360, 210, 124),
        B('TROPHY', 'TROPHY HALL', '#ffd76b', 430, 880, 160, 96),
        B('KENNEL', 'THE KENNEL', '#b6f06b', 1270, 880, 160, 96),
        B('INFIRMARY', 'INFIRMARY', '#ff7a7a', 1270, 500, 160, 96)
      ]
    };
  }

  /* The enlarged district. Uses the REAL AK_WORLDGEN when it is requireable, which is the whole
   * point: a synthetic scatter of boxes would let this lane pass against a world that does not
   * exist, and the first version of this test did exactly that and hid the frontage-budget bug
   * behind a fixture that happened to be sparser than the real generator. Falls back to a
   * synthetic field only so the proof still runs if that module is unavailable. */
  function fixtureStructures(zone, n) {
    try {
      var G = require('./akworldgen.js');
      if (G && G.planDistrict) {
        var p = G.planDistrict(zone, { worldW: 1700, worldH: 1300, density: 1.0, obstacles: [] });
        if (p && p.structures && p.structures.length) return p.structures;
      }
    } catch (_e) {}
    var out = [], r = rngFor('fixture:struct'), i;
    for (i = 0; i < n; i++) {
      var w = 60 + r() * 60, d = 50 + r() * 50;
      var x, y, tries = 0;
      do { x = 120 + r() * 1460; y = 120 + r() * 1060; tries++; }
      while (tries < 30 && (Math.abs(x - 850) < 130 || Math.abs(y - 650) < 130));
      out.push({ id: 'wg_' + i, kind: 'ROW', x: x, y: y, w: w, d: d, h: 80 + r() * 90, col: 0x33333a });
    }
    return out;
  }

  function selfTest(THREE) {
    var lines = [], ok = true;
    function say(cond, label, got) {
      if (!cond) ok = false;
      lines.push((cond ? 'PASS ' : 'FAIL ') + label + (got !== undefined ? ('  got=' + got) : ''));
    }
    function eq(label, a, b, tol) {
      var pass = Math.abs(a - b) <= (tol || 1e-9);
      if (!pass) ok = false;
      lines.push((pass ? 'PASS ' : 'FAIL ') + label + '  got=' + a + ' want=' + b);
    }

    var zone = fixtureZone(), W = 1700, H = 1300;

    // ---- 1. STREET LATTICE ------------------------------------------------------------------
    lines.push('--- street lattice ---');
    var st = builtinStreets('HOME_TURF', W, H);
    say(st.vx.length === 5 && st.hy.length === 5, 'lattice has 5 vertical + 5 horizontal bands', st.vx.length + '+' + st.hy.length);
    var mv = null, mh = null, i;
    for (i = 0; i < st.vx.length; i++) if (st.vx[i].rank === 'main') mv = st.vx[i];
    for (i = 0; i < st.hy.length; i++) if (st.hy[i].rank === 'main') mh = st.hy[i];
    eq('main N-S avenue pinned at W/2', mv.c, 850);
    eq('main E-W avenue pinned at H/2', mh.c, 650);
    eq('main half-width reproduces the x[775,925] corridor', mv.half, 75);
    // The four edge spawns and the plaza must all fall inside a street band, or the props would be
    // placed across the only routes out of the district.
    say(inStreet(st, 150, 650, 0), 'W edge spawn is on the street lattice');
    say(inStreet(st, 1550, 650, 0), 'E edge spawn is on the street lattice');
    say(inStreet(st, 850, 150, 0), 'N edge spawn is on the street lattice');
    say(inStreet(st, 850, 1150, 0), 'S edge spawn is on the street lattice');
    say(inStreet(st, 850, 650, 0), 'centre plaza is on the street lattice');
    // If AK_WORLDGEN is loadable in this process, prove the fallback is not a drifted copy.
    var G = null;
    try { G = require('./akworldgen.js'); } catch (_e) {}
    if (G && G.planStreets) {
      var real = G.planStreets('HOME_TURF', W, H);
      var same = real.vx.length === st.vx.length && real.hy.length === st.hy.length;
      for (i = 0; same && i < real.vx.length; i++) same = Math.abs(real.vx[i].c - st.vx[i].c) < 1e-9 && real.vx[i].half === st.vx[i].half;
      for (i = 0; same && i < real.hy.length; i++) same = Math.abs(real.hy[i].c - st.hy[i].c) < 1e-9 && real.hy[i].half === st.hy[i].half;
      say(same, 'builtin fallback lattice is IDENTICAL to AK_WORLDGEN.planStreets');
    } else {
      lines.push('SKIP  AK_WORLDGEN not requireable in this process');
    }

    var kerbs = kerbsOf(st, W, H);
    eq('kerbs = 2 per band', kerbs.length, (st.vx.length + st.hy.length) * 2);
    // The outward normal is what four placement passes depend on. A sign error here would put
    // every dumpster in the middle of the road, so it is asserted rather than assumed.
    var bad = 0;
    for (i = 0; i < kerbs.length; i++) {
      var kk = kerbs[i];
      var out1 = (kk.axis === 'v') ? { x: kk.at + kk.nx * 30, y: 650 } : { x: 850, y: kk.at + kk.ny * 30 };
      var in1 = (kk.axis === 'v') ? { x: kk.at - kk.nx * 6, y: 650 } : { x: 850, y: kk.at - kk.ny * 6 };
      // "outward" must be further from the band centre than "inward"
      var dOut = (kk.axis === 'v') ? Math.abs(out1.x - kk.c) : Math.abs(out1.y - kk.c);
      var dIn = (kk.axis === 'v') ? Math.abs(in1.x - kk.c) : Math.abs(in1.y - kk.c);
      if (!(dOut > dIn)) bad++;
    }
    eq('every kerb normal points away from its carriageway', bad, 0);

    // ---- 2. THE PLAN ------------------------------------------------------------------------
    lines.push('--- planner (stock 4-building district) ---');
    var plan = planClutter({ zone: zone, worldW: W, worldH: H, quality: 1.0, dedupe: false });
    say(plan.props.length > 150, 'stock district places a real prop field', plan.props.length);
    say(plan.stats.fields > 0 && plan.stats.fields <= 24, 'field count stays inside the draw-call budget', plan.stats.fields);
    say(plan.stats.naiveDrawCalls > plan.stats.fields * 8,
      'merge+instance is at least an 8x draw-call win', plan.stats.naiveDrawCalls + ' -> ' + plan.stats.fields);

    // Determinism. Two independent plans of the same district must be byte-identical, or the
    // street shimmers on every re-entry and reads as a rendering fault.
    var plan2 = planClutter({ zone: zone, worldW: W, worldH: H, quality: 1.0, dedupe: false });
    var ident = plan.props.length === plan2.props.length;
    for (i = 0; ident && i < plan.props.length; i++) {
      ident = plan.props[i].k === plan2.props[i].k && plan.props[i].x === plan2.props[i].x &&
              plan.props[i].y === plan2.props[i].y && plan.props[i].v === plan2.props[i].v &&
              plan.props[i].tint === plan2.props[i].tint;
    }
    say(ident, 'placement is deterministic across two independent plans');

    // Different districts must NOT share a layout, or all nine read as the same street.
    var zoneB = fixtureZone(); zoneB.id = 'THE_DOCKS';
    var planB = planClutter({ zone: zoneB, worldW: W, worldH: H, quality: 1.0, dedupe: false });
    var differs = false;
    for (i = 0; i < Math.min(plan.props.length, planB.props.length); i++) {
      if (plan.props[i].x !== planB.props[i].x || plan.props[i].y !== planB.props[i].y) { differs = true; break; }
    }
    say(differs, 'a different district gets a different layout');

    // ---- 3. KEEP-OUTS -- the rules that stop this reading as a bug ---------------------------
    lines.push('--- keep-out enforcement ---');
    var ko = keepOutsOf(zone, { worldW: W, worldH: H });
    var inBld = 0, inDoor = 0, inSpawn = 0, inLane = 0, offWorld = 0;
    for (i = 0; i < plan.props.length; i++) {
      var p = plan.props[i], def = KIND_BY_NAME[p.k];
      if (p.x < 0 || p.y < 0 || p.x > W || p.y > H) offWorld++;
      if (p.ground) continue;                                  // decals are exempt by design
      if (p.k === 'KERB') continue;                            // kerbs are road surface
      var pr = { x: p.x - def.foot / 2, y: p.y - def.foot / 2, w: def.foot, h: def.foot };
      for (var j = 0; j < ko.length; j++) {
        if (!overlaps(pr, ko[j])) continue;
        if (ko[j].why.indexOf('bld:') === 0) inBld++;
        else if (ko[j].why.indexOf('door:') === 0) inDoor++;
        else if (ko[j].why === 'spawn') inSpawn++;
      }
      // LAMP is the documented allowLane exception -- it stands just inside the kerb on purpose.
      if (p.k !== 'LAMP' && inLaneCentre(st, p.x, p.y)) inLane++;
    }
    eq('no prop lands outside the world', offWorld, 0);
    eq('no standing prop inside a building footprint', inBld, 0);
    eq('no standing prop in a door apron (exitInterior landing spot)', inDoor, 0);
    eq('no standing prop on an edge spawn', inSpawn, 0);
    eq('no standing prop in the carriageway', inLane, 0);

    // Ground marks must be IN the road, or they are not road marks.
    var roadKinds = { PUDDLE: 1, MANHOLE: 1, GRATE: 1, STAIN: 1 }, offRoad = 0, roadN = 0;
    for (i = 0; i < plan.props.length; i++) {
      if (!roadKinds[plan.props[i].k]) continue;
      roadN++;
      if (!inStreet(st, plan.props[i].x, plan.props[i].y, 0)) offRoad++;
    }
    say(roadN > 0, 'road marks were placed', roadN);
    eq('every road mark is actually on a road', offRoad, 0);

    // Every lamp must have exactly one light pool. The pool is the near-field payoff and a lamp
    // without one is a pole.
    var lamps = 0, pools = 0;
    for (i = 0; i < plan.props.length; i++) {
      if (plan.props[i].k === 'LAMP') lamps++;
      if (plan.props[i].k === 'POOL') pools++;
    }
    say(lamps > 20, 'lamp runs produced a real number of lamps', lamps);
    eq('every lamp carries exactly one light pool', pools, lamps);

    // ---- 4. WALKABILITY ---------------------------------------------------------------------
    lines.push('--- walkability (props treated as SOLID, the strictest reading) ---');
    var wk = walkabilityOf(plan, zone, { step: 20, playerR: 23 });
    say(wk.ok, 'plaza reaches all 4 edge spawns and every building door' + (wk.ok ? '' : ' FAILED: ' + wk.failed.join(',')), wk.targets + ' targets');
    say(wk.openPct > 55, 'district stays mostly open', wk.openPct + '% of cells reachable');

    // ---- 5. QUALITY KNOB ---------------------------------------------------------------------
    lines.push('--- quality knob ---');
    var lo = planClutter({ zone: zone, worldW: W, worldH: H, quality: 0.45, dedupe: false });
    var mid = planClutter({ zone: zone, worldW: W, worldH: H, quality: 0.7, dedupe: false });
    say(lo.props.length < plan.props.length, 'q=0.45 places fewer props than q=1.0', lo.props.length + ' < ' + plan.props.length);
    say(mid.props.length < plan.props.length && mid.props.length > lo.props.length, 'q=0.7 sits between', mid.props.length);
    say(lo.stats.fields < plan.stats.fields, 'q=0.45 also collapses variants, so fewer draw calls', lo.stats.fields + ' < ' + plan.stats.fields);
    var loVarMax = 0;
    for (i = 0; i < lo.props.length; i++) if (lo.props[i].v > loVarMax) loVarMax = lo.props[i].v;
    eq('q=0.45 uses a single geometry variant per kind', loVarMax, 0);
    var wkLo = walkabilityOf(lo, zone, { step: 20 });
    say(wkLo.ok, 'low quality is still fully walkable');

    // ---- 6. SCALE -- the operator directive, discharged ---------------------------------------
    lines.push('--- scale to the enlarged world (worldscale lane live) ---');
    var gs = fixtureStructures(zone, 90);
    lines.push('  generated structures in the district: ' + gs.length);
    var big = planClutter({ zone: zone, worldW: W, worldH: H, quality: 1.0, dedupe: false, structures: gs });
    say(big.props.length > plan.props.length,
      'the enlarged district carries MORE clutter than the 4-building one',
      plan.props.length + ' -> ' + big.props.length);
    say(big.props.length >= 300, 'the enlarged district reaches the hundreds-of-props target', big.props.length);
    say(big.stats.fields <= 24, 'and still fits the draw-call budget', big.stats.fields + ' fields');
    say(big.stats.naiveDrawCalls / big.stats.fields > 20,
      'at scale the instancer is worth >20x', Math.round(big.stats.naiveDrawCalls / big.stats.fields) + 'x');
    var wkBig = walkabilityOf(big, zone, { step: 20 });
    say(wkBig.ok, 'the enlarged district is still walkable' + (wkBig.ok ? '' : ' FAILED: ' + wkBig.failed.join(',')));
    // No prop may stand inside a generated structure either.
    var inGen = 0;
    for (i = 0; i < big.props.length; i++) {
      var bp = big.props[i]; if (bp.ground || bp.k === 'KERB') continue;
      for (var gi = 0; gi < gs.length; gi++) {
        var g = gs[gi];
        if (Math.abs(bp.x - g.x) < g.w / 2 && Math.abs(bp.y - g.y) < g.d / 2) { inGen++; break; }
      }
    }
    eq('no prop stands inside a generated building', inGen, 0);

    // ---- 7. DE-CONFLICT WITH akstream --------------------------------------------------------
    lines.push('--- de-conflict with akstream scatter ---');
    var fakeOthers = [];
    for (i = 0; i < 200; i++) fakeOthers.push({ k: 'CRATES', x: 100 + (i * 37) % 1500, y: 100 + (i * 71) % 1100 });
    var ded = planClutter({ zone: zone, worldW: W, worldH: H, quality: 1.0, others: fakeOthers });
    var clash = 0;
    for (i = 0; i < ded.props.length; i++) {
      var dp = ded.props[i]; if (dp.ground) continue;
      for (var oi = 0; oi < fakeOthers.length; oi++) {
        var dx = fakeOthers[oi].x - dp.x, dy = fakeOthers[oi].y - dp.y;
        if (dx * dx + dy * dy < CFG.dedupR * CFG.dedupR) { clash++; break; }
      }
    }
    eq('no standing prop lands on an akstream scatter prop', clash, 0);
    say(ded.stats.rejected.dedupe > 0, 'the de-conflict actually rejected something', ded.stats.rejected.dedupe + ' rejections');

    // ---- 8. SCENE LAYER -- real three, real AK_INSTANCE, real Scene ---------------------------
    if (!THREE) {
      lines.push('SKIP  scene layer (no THREE handed to selfTest)');
      return { ok: ok, lines: lines };
    }
    lines.push('--- scene layer (real three r160 + real AK_INSTANCE) ---');
    var I = null;
    try { I = require('./akinstance.js'); } catch (e) { lines.push('SKIP  AK_INSTANCE not requireable: ' + e.message); }
    if (!I) return { ok: ok, lines: lines };

    var prevInst = root.AK_INSTANCE, prevW3 = root.AK_WORLD3D;
    var sc = new THREE.Scene();
    I._useEngine(THREE);
    _engine = THREE;                 // our own gate has no window.AK_THREE to read in node
    I.clear(null);
    root.AK_INSTANCE = I;
    root.AK_WORLD3D = { _state: { scene: sc } };

    // Templates must merge under real three, including the PlaneGeometry decal parts. A mocked
    // THREE would pass a merge that r160 rejects, which is why this uses the vendored module.
    var tmplFails = 0, tmplTris = 0;
    for (i = 0; i < KINDS.length; i++) {
      for (var vv = 0; vv < KINDS[i].vars; vv++) {
        var parts = [];
        partsFor(THREE, KINDS[i].k, vv, parts);
        var g2 = I.merge(parts, {});
        if (!g2 || !g2.attributes.position || !g2.attributes.position.count) tmplFails++;
        else {
          tmplTris += (g2.attributes.position.count / 3) | 0;
          if (!g2.attributes.color) tmplFails++;      // vertexColors is the whole merge contract
          g2.dispose();
        }
        for (var pi = 0; pi < parts.length; pi++) if (parts[pi].geometry) parts[pi].geometry.dispose();
      }
    }
    eq('every kind+variant template merges under real three', tmplFails, 0);
    say(tmplTris > 0, 'templates carry real geometry', tmplTris + ' triangles across all templates');

    // Now the real thing: build the fields for the enlarged district.
    S.ids = []; S.templates = []; S.mats = [];
    var bigPlan = planClutter({ zone: zone, worldW: W, worldH: H, quality: 1.0, dedupe: false, structures: gs });
    var made = buildFields(bigPlan);
    say(made > 0, 'buildFields created fields', made);
    eq('one field per kind+variant in the plan', made, bigPlan.stats.fields);

    // THE NUMBER THIS LANE EXISTS TO MOVE. Counted off the real scene graph, not asserted.
    var calls = I.estimateDrawCalls(sc);
    eq('scene draw calls == field count', calls, made);
    say(calls < bigPlan.stats.naiveDrawCalls / 20,
      'measured draw calls beat naive by >20x', bigPlan.stats.naiveDrawCalls + ' naive -> ' + calls + ' actual');

    // Every prop must actually be IN an InstancedMesh. This is the check that catches the repo's
    // #1 failure mode: geometry that exists and is never submitted.
    var totalInstances = 0, meshes = 0;
    sc.traverse(function (o) {
      if (o.isInstancedMesh) { meshes++; totalInstances += o.count; }
    });
    eq('every planned prop is a live instance', totalInstances, bigPlan.props.length);
    eq('and they live in exactly `made` InstancedMeshes', meshes, made);

    // Material policy: decals must not write depth or they punch holes in each other.
    // Kind comes from S.kinds, never from the mesh name -- 7 of the 9 district ids contain an
    // underscore, so name-splitting recovers the wrong token (this test failed exactly that way).
    var badMat = 0, glowN = 0, decalN = 0, litN = 0, fid;
    for (fid in S.kinds) {
      if (!S.kinds.hasOwnProperty(fid)) continue;
      var rec = S.kinds[fid], mesh = rec.mesh;
      var def = KIND_BY_NAME[rec.k];
      if (!def || !mesh || !mesh.material) { badMat++; continue; }
      if (def.ground) {
        decalN++;
        if (mesh.material.depthWrite !== false || !mesh.material.transparent) badMat++;
        if (mesh.material.type !== 'MeshBasicMaterial') badMat++;
      } else {
        litN++;
        if (mesh.material.type !== 'MeshLambertMaterial') badMat++;
      }
      if (def.glow) { glowN++; if (mesh.material.blending !== THREE.AdditiveBlending) badMat++; }
    }
    eq('material policy holds for every field', badMat, 0);
    say(decalN > 0 && litN > 0, 'both material classes are actually in use', decalN + ' decal fields / ' + litN + ' lit fields');
    eq('the light pool is the one additive field', glowN, 1);

    // Decals must be lifted off the ground plane or they z-fight it. world3d.js:497 puts the
    // ground at exactly y=0, and a z-fight there is resolution dependent: clean on a desktop,
    // strobing on a phone.
    var lowVert = 0;
    for (fid in S.kinds) {
      if (!S.kinds.hasOwnProperty(fid)) continue;
      var rc = S.kinds[fid];
      if (!KIND_BY_NAME[rc.k] || !KIND_BY_NAME[rc.k].ground || !rc.mesh) continue;
      var pos = rc.mesh.geometry.attributes.position;
      for (var vi = 0; vi < pos.count; vi++) if (pos.getY(vi) < CFG.decalY - 1e-6) lowVert++;
    }
    eq('no decal vertex sits at or below the ground plane', lowVert, 0);

    // Teardown must free everything it allocated -- world3d.js:452 disposes nothing and this lane
    // does not inherit that.
    var nTemplates = S.templates.length, nMats = S.mats.length;
    teardown();
    var after = I.estimateDrawCalls(sc);
    eq('teardown removes every field from the scene', after, 0);
    say(nTemplates === made && nMats === made, 'teardown had one geometry + one material per field to free',
      nTemplates + 'g/' + nMats + 'm for ' + made + ' fields');
    eq('teardown emptied our bookkeeping', S.ids.length + S.templates.length + S.mats.length, 0);

    I.clear(null);
    root.AK_INSTANCE = prevInst; root.AK_WORLD3D = prevW3;

    // ---- headline ---------------------------------------------------------------------------
    lines.push('--- headline ---');
    lines.push('  stock 4-building district : ' + plan.props.length + ' props, ' + plan.stats.fields + ' draw calls (naive ' + plan.stats.naiveDrawCalls + ')');
    lines.push('  90-structure district     : ' + bigPlan.props.length + ' props, ' + calls + ' draw calls (naive ' + bigPlan.stats.naiveDrawCalls + ')');
    lines.push('  low-end (q=0.45)          : ' + lo.props.length + ' props, ' + lo.stats.fields + ' draw calls');
    lines.push('  saved at scale            : ' + (bigPlan.stats.naiveDrawCalls - calls) + ' draw calls/frame');

    return { ok: ok, lines: lines };
  }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akclutter.js` -- imports the REAL vendored r160 and asserts against
 * it. No mocks anywhere: a stubbed THREE would happily "pass" a merge that three itself rejects,
 * and that is precisely the class of bug that has shipped on this project before. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  import('../assets/vendor/three.module.min.js').then(function (T) {
    var r = module.exports.selfTest(T);
    r.lines.forEach(function (l) { console.log(l); });
    console.log(r.ok ? 'ALL PASS' : 'FAILURES PRESENT');
    process.exit(r.ok ? 0 : 1);
  }, function (e) {
    console.log('vendor three not importable: ' + (e && e.message) + ' -- running pure core only');
    var r = module.exports.selfTest(null);
    r.lines.forEach(function (l) { console.log(l); });
    console.log(r.ok ? 'ALL PASS (pure core)' : 'FAILURES PRESENT');
    process.exit(r.ok ? 0 : 1);
  });
}
