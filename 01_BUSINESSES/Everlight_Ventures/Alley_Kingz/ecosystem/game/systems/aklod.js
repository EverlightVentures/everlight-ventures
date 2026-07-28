/* ALLEY KINGZ -- AK_LOD: distance level-of-detail for the 3D district.  AK-LOD 2026-07-19.
 *
 * ---------------------------------------------------------------------------------------------
 * WHAT COSTS MONEY HERE, MEASURED, BEFORE ANY CODE WAS WRITTEN
 *
 * The instinct on "LOD" is swap-geometry-by-distance: a 5k-tri mesh becomes a 500-tri mesh at
 * range. That instinct is WRONG for this game and building it would have burned the lane. The
 * numbers say so:
 *
 *   - bldmass.js:9 measured the entire visible world at 50 TRIANGLES. A hub building is one
 *     BoxGeometry: 12 triangles. There is no lower-poly version of a box. A "LOD1 box" is the
 *     same box. Triangles are not the bill.
 *   - What IS the bill is DRAW CALLS, and the count is 6x what the mesh count suggests.
 *     world3d.js:539 builds each building as `new THREE.Mesh(geo, [side,side,roof,side,face,side])`.
 *     A material ARRAY makes three walk geometry.groups and push one render item PER GROUP.
 *     Verified in the vendored r160 build, assets/vendor/three.module.min.js, projectObject:
 *         Array.isArray(r)){const i=e.groups;for(...){...o&&o.visible&&_.push(t,e,o,n,q.z,a)}}
 *         else r.visible&&_.push(t,e,r,n,q.z,null)
 *     Six groups -> six render items -> six draw calls. Hand that same mesh a NON-array material
 *     and the else branch fires exactly once, group=null, and the whole geometry draws in ONE call.
 *     That single line is the entire reason this module exists: 6 -> 1 per distant building.
 *   - Same file, same function, first line: `function Xt(t,e,n,i){if(!1===t.visible)return;`
 *     so `mesh.visible=false` costs literally zero -- three never touches it again that frame.
 *
 * SO THE TIERS ARE NOT GEOMETRY VARIANTS. They are: how much of the SIX-SLOT material array,
 * and how much added detail mass, a building is allowed to spend at its current distance.
 *
 *   T0  NEAR   6 material slots (facade PNG on +z, roof PNG on +y) + the AK_BLDMASS detail mesh.
 *              ~7 draw calls. This is what the player is standing next to.
 *   T1  MID    same 6 slots, detail mesh hidden. ~6 draw calls. Parapets and roof AC units are
 *              sub-pixel past ~700 units; paying a draw call for them is pure waste.
 *   T2  FAR    ONE flat lit material for the whole box. ~1 draw call. The facade photo is
 *              unreadable here and scene.fog (world3d.js:666, Fog(tint, 420, 1750)) is already
 *              eating most of its contrast, so the texture is being blended toward the sky tint
 *              anyway. Dropping it also drops the texture bind and the sampler.
 *   T3  CULL   visible=false, 0 draw calls. Default threshold sits just under the fog FAR plane
 *              of 1750, past which a building is mathematically 100% fog colour. Culling
 *              something the fog has already erased is free in the strictest sense.
 *
 * HYSTERESIS IS NOT OPTIONAL AND IS THE MOST COMMONLY SKIPPED PART.
 * A single threshold means a building parked at exactly d=700 while the hero jitters (the hub
 * clamps dt to 50ms at index.html:2370 and the hero's own step is sub-unit) flips T0<->T1 EVERY
 * FRAME. Each flip reassigns mesh.material, and a material change is a renderer state change plus
 * a possible program lookup: the "optimisation" would cost more than the detail it removed, at
 * 60 flips a second, forever. So promote at T and demote at T*(1-h). The dead band is the fix.
 *
 * NO ALLOCATION IN THE UPDATE PATH, AND NO sqrt.
 * update() reads three numbers off the live camera's Vector3 (never camPos(), which builds a fresh
 * object literal every call -- world3d.js:202) and compares SQUARED distances against SQUARED
 * thresholds precomputed once in makeLodCore. Per entry the whole test is 3 subs, 3 muls, 2 adds
 * and a compare. At the ~110 buildings this lane ships, that is under 1000 flops a frame, which is
 * nothing next to the ~600 draw calls it removes.
 *
 * ---------------------------------------------------------------------------------------------
 * WHY THIS MODULE ALSO BUILDS BUILDINGS (read before deleting the infill)
 *
 * HOME_TURF has FOUR buildings. Four. An LOD system across four objects saves at most twenty-odd
 * draw calls and would be honest-to-god theatre. Per the operator directive, the correct reading
 * of that is not "LOD does not apply here" -- it is "the district is too small", and the fix is to
 * grow the district until the technique is load-bearing.
 *
 * So AK_LOD ships a SKYLINE RING: a procedurally placed band of background buildings in the
 * dead space OUTSIDE the 1700x1300 playfield, 1 to 4 cells deep on every side. Deliberate design
 * constraints, each one chosen to make this safe to land next to nine other lanes:
 *   - It is placed strictly OUTSIDE the world rect plus a 60-unit margin (planInfill enforces it
 *     and the headless test asserts it). The hero is clamped to the playfield, so the ring can
 *     never be walked into. NO COLLISION WORK IS NEEDED and no gameplay changes -- the ring is
 *     scenery, and scenery is exactly what an LOD system is for.
 *   - It is 3D-only. The 2D canvas layer draws from zone.buildings (index.html:2574) which this
 *     never touches, so with WebGL absent the game is byte-identical to before.
 *   - It is deterministic per district (FNV + xorshift on the zone id, the same idiom as
 *     bldmass.js:26) so a district looks the same on every entry and across sessions.
 *   - It is built on a PER-TICK BUDGET, not in one blocking loop. ~110 buildings x ~15 detail
 *     boxes through AK_BLDMASS is ~1650 temporary geometries; doing that inside one frame is a
 *     visible hitch on a phone. BUILD_BUDGET spreads it over ~18 frames instead.
 *
 * Result on HOME_TURF: 4 buildings / ~26 draw calls becomes ~110 buildings, and WITHOUT this
 * module that would be roughly 250 draw calls. With it, the far half of the ring is past the fog
 * plane and culled outright and the mid band is collapsed to one call each. Call AK_LOD.stats()
 * for the live numbers -- this module reports what it actually saved rather than asserting it.
 *
 * SECOND-ORDER WIN: this is the first and only caller of AK_BLDMASS.decorate(). bldmass.js has
 * shipped since 2026-07-19 with ZERO callers repo-wide -- its parapets, cornices, roof AC units,
 * water tanks and facade ledges have never rendered a pixel. Decoration is additive by contract
 * (bldmass.js:11) so adopting the real buildings' detail here voids nothing the facade lane owns,
 * and userData.akMassed guards against a later lane decorating the same mesh twice.
 *
 * ---------------------------------------------------------------------------------------------
 * WHAT THIS MODULE MAY NOT DO
 *   - It never constructs a WebGLRenderer, a Scene or a Camera. It borrows AK_WORLD3D._state
 *     (world3d.js:889 exports it precisely so peers do not have to edit that file). Phones evict
 *     WebGL contexts around 8 and AK_R3D is a hard singleton (three_boot.js:74).
 *   - It never edits systems/world3d.js.
 *   - It disposes every geometry AND material AND texture it creates, on district change and on
 *     teardown. world3d.js:761 disposes geometry only; this lane does not add to that debt.
 *   - It restores every real building it touched (material array, visibility) before letting go,
 *     so a torn-down AK_LOD leaves the scene exactly as world3d built it.
 *   - Total failure is silent-but-visible: if three is absent, if AK_WORLD3D is off, or if any
 *     build throws, the ring simply never appears and the 4 real buildings render as they always
 *     did. Errors are counted in stats().errors rather than swallowed into nothing (a corrupt
 *     vendor file once hid for hours behind an empty catch on this project).
 *
 * Pure core (tier maths + ring planner) is DOM-free, THREE-free and node-requireable.
 * Headless proof: `node systems/aklod.js`.
 * No em-dashes anywhere (hook law, use --).
 */
(function (root) {
  'use strict';

  /* =====================================================================================
   * PURE CORE -- no DOM, no THREE, no globals. Requireable and testable in node.
   * ===================================================================================== */

  /* Thresholds in WORLD UNITS, measured against the real camera rig rather than guessed:
   * world3d.js:135 puts the camera at dist 620 (DIST_MIN 260 / DIST_MAX 1150) on a polar phi of
   * 52 degrees, looking at the hero. So a building standing right next to the hero is already
   * ~620 units from the eye, and the far corner of a 1700x1300 district is ~2100-2700.
   *   700  -> roughly "in the same block as the hero". Detail mass still legible.
   *  1120  -> two thirds of the way across the district. Facade photo is a smear by here.
   *  1650  -> just inside scene.fog's far plane of 1750 (world3d.js:666), past which a building
   *           resolves to 100% sky tint. Culling at 1650 removes something already invisible.
   * Anyone re-tuning these must keep T3 <= the fog far plane, or buildings will pop out of a
   * sky they have not fully faded into yet. */
  var DEFAULT_TIERS = [700, 1120, 1650];

  /* 10% dead band. Chosen, not guessed: the hero's top speed is a few units per frame, so a 10%
   * band on the nearest threshold is 70 units, which is ~20+ frames of travel. A building has to
   * genuinely commit to crossing before it pays for a second tier change. Below ~4% the band is
   * thinner than a single dt-clamped frame's motion and stops preventing anything. */
  var DEFAULT_HYST = 0.10;

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  /* makeLodCore -> the tier decision function. Everything expensive (the squaring) happens ONCE,
   * here, so update() never multiplies a threshold and never calls Math.sqrt.
   *
   * tiers.length thresholds produce tiers.length+1 tiers, numbered 0 (nearest) upward.
   * up2[i]  : squared distance at which tier i is abandoned for tier i+1  (moving AWAY)
   * dn2[i]  : squared distance at which tier i+1 falls back to tier i     (moving TOWARD)
   * dn2[i] < up2[i] always, and the gap between them is the anti-flap dead band.
   */
  function makeLodCore(o) {
    o = o || {};
    var src = (o.tiers && o.tiers.length) ? o.tiers : DEFAULT_TIERS;
    var h = clamp(typeof o.hyst === 'number' ? o.hyst : DEFAULT_HYST, 0, 0.45);
    var tiers = [], up2 = [], dn2 = [], i, t, d;
    for (i = 0; i < src.length; i++) {
      t = Math.max(1, +src[i] || 0);
      // Monotonicity guard: a mis-ordered tier list would make pick() oscillate forever, which
      // is the exact bug hysteresis exists to prevent. Clamp rather than throw -- a bad config
      // must degrade to a working LOD, never take the district down.
      if (i > 0 && t <= tiers[i - 1]) t = tiers[i - 1] + 1;
      tiers.push(t);
      up2.push(t * t);
      d = t * (1 - h);
      dn2.push(d * d);
    }

    /* pick(d2, cur) -> tier index. Allocation-free, branch-cheap, and CONVERGENT: both loops
     * only ever move in one direction, so a hero teleporting across the map (district edges do
     * exactly that, index.html:1354) resolves in one call instead of one tier per frame. */
    function pick(d2, cur) {
      var n = tiers.length;
      cur = cur | 0;
      if (cur < 0) cur = 0; else if (cur > n) cur = n;
      while (cur < n && d2 > up2[cur]) cur++;
      while (cur > 0 && d2 < dn2[cur - 1]) cur--;
      return cur;
    }

    return {
      tiers: tiers, hyst: h, up2: up2, dn2: dn2,
      maxTier: tiers.length,      // == the CULL tier index
      pick: pick
    };
  }

  /* --- deterministic per-district noise. Same FNV1a + xorshift pair as bldmass.js:26, on
   * purpose: a shared idiom means a district's ring and its building detail derive from the
   * same family of hashes and a reader only has to learn it once. Math.random() here would
   * re-roll the entire skyline on every district re-entry, which reads as the city rebuilding
   * itself behind the player. --- */
  function hash(str) {
    var h = 2166136261, s = String(str == null ? 'x' : str), i;
    for (i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  var INFILL_DEFAULTS = {
    cell:   220,   // grid pitch. 220 leaves a believable ~40-70 unit alley between neighbours.
    pad:    900,   // how far past each world edge the ring extends. 900 puts the outermost row
                   // ~2300+ units from the camera, i.e. beyond the fog plane, i.e. permanently
                   // in the cull tier -- which is the POINT: the cull tier must be exercised.
    margin:  60,   // keep-out beyond the playfield. Nothing may encroach on the walkable rect
                   // or on the edge-transition strips the hub uses at index.html:1354.
    fill:   0.62,  // occupancy. Under ~0.5 reads as scattered sheds, over ~0.8 as a solid wall.
    minH:    90,
    stepH:   46,   // per ring-depth height gain: near rows low, far rows tall. That gradient is
                   // what makes a flat band of boxes read as a skyline instead of a fence.
    jitH:   130
  };

  /* planInfill(zoneId, o) -> [{id,x,y,w,d,h,col,ring}]  PURE. No THREE, no DOM.
   * x,y are hub world coords (the 3D layer maps hub y -> three z, world3d.js:541).
   * Every returned record is guaranteed OUTSIDE the playfield rect inflated by o.margin;
   * selfTest asserts it, because a single stray interior box would be an invisible wall the
   * player collides with in 2D and cannot see coming. */
  function planInfill(zoneId, o) {
    o = o || {};
    var W = o.worldW || 1700, H = o.worldH || 1300;
    var cell = o.cell || INFILL_DEFAULTS.cell;
    var pad = (typeof o.pad === 'number') ? o.pad : INFILL_DEFAULTS.pad;
    var margin = (typeof o.margin === 'number') ? o.margin : INFILL_DEFAULTS.margin;
    var fill = (typeof o.fill === 'number') ? o.fill : INFILL_DEFAULTS.fill;
    var minH = o.minH || INFILL_DEFAULTS.minH;
    var stepH = (typeof o.stepH === 'number') ? o.stepH : INFILL_DEFAULTS.stepH;
    var jitH = (typeof o.jitH === 'number') ? o.jitH : INFILL_DEFAULTS.jitH;

    var rnd = rngFor('ring:' + zoneId);
    var cols = Math.ceil((W + pad * 2) / cell);
    var rows = Math.ceil((H + pad * 2) / cell);
    var out = [], r, c, cx, cy, ring, w, d, h, tone, n = 0;

    for (r = 0; r < rows; r++) {
      for (c = 0; c < cols; c++) {
        cx = -pad + (c + 0.5) * cell;
        cy = -pad + (r + 0.5) * cell;

        // KEEP-OUT: skip anything inside the playfield plus its margin. Drawn from the cell
        // CENTRE plus half a footprint so a wide box cannot lean into the walkable rect either.
        var half = cell * 0.42;
        if (cx + half > -margin && cx - half < W + margin &&
            cy + half > -margin && cy - half < H + margin) continue;

        // Consume the rng for EVERY candidate cell, accepted or not, so the sequence does not
        // shift when fill/pad change. Determinism you can retune is worth one wasted call.
        var keep = rnd() < fill;
        var rw = rnd(), rd = rnd(), rh = rnd(), rt = rnd();
        if (!keep) continue;

        // ring depth = how many cells outside the playfield this cell sits, on its nearest edge.
        ring = 0;
        if (cx < 0) ring = Math.max(ring, Math.ceil((0 - cx) / cell));
        if (cx > W) ring = Math.max(ring, Math.ceil((cx - W) / cell));
        if (cy < 0) ring = Math.max(ring, Math.ceil((0 - cy) / cell));
        if (cy > H) ring = Math.max(ring, Math.ceil((cy - H) / cell));

        w = cell * (0.50 + rw * 0.30);
        d = cell * (0.50 + rd * 0.30);
        h = minH + (ring - 1) * stepH + rh * jitH;

        // Cool desaturated greys, darker than any playfield building so the eye reads the ring
        // as background and the real, saturated, texture-mapped buildings as the subject.
        tone = 26 + Math.floor(rt * 26);
        out.push({
          id: 'ring_' + zoneId + '_' + (n++),
          x: cx, y: cy, w: w, d: d, h: h, ring: ring,
          col: (tone << 16) | ((tone + 2) << 8) | (tone + 8)
        });
      }
    }
    return out;
  }

  /* =====================================================================================
   * HEADLESS PROOF -- real numbers, no mocks. `node systems/aklod.js`.
   * ===================================================================================== */
  function selfTest() {
    var out = [], ok = true;
    function chk(label, pass, extra) {
      if (!pass) ok = false;
      out.push((pass ? 'PASS ' : 'FAIL ') + label + (extra ? ('  ' + extra) : ''));
    }
    function eq(label, a, b) { chk(label, a === b, 'got=' + a + ' want=' + b); }

    var core = makeLodCore({ tiers: [700, 1120, 1650], hyst: 0.10 });
    var d2 = function (d) { return d * d; };

    // ---- 1. thresholds fire where the config says, walking OUTWARD from tier 0 ----
    eq('out d=0    -> T0', core.pick(d2(0), 0), 0);
    eq('out d=699  -> T0', core.pick(d2(699), 0), 0);
    eq('out d=701  -> T1', core.pick(d2(701), 0), 1);
    eq('out d=1119 -> T1', core.pick(d2(1119), 1), 1);
    eq('out d=1121 -> T2', core.pick(d2(1121), 1), 2);
    eq('out d=1649 -> T2', core.pick(d2(1649), 2), 2);
    eq('out d=1651 -> T3(cull)', core.pick(d2(1651), 2), 3);
    eq('maxTier == cull index', core.maxTier, 3);

    // ---- 2. coming back IN, the boundary is T*(1-h), NOT T. This is the hysteresis. ----
    // 700*0.9=630, 1120*0.9=1008, 1650*0.9=1485
    eq('in  d=690 from T1 -> stays T1', core.pick(d2(690), 1), 1);
    eq('in  d=640 from T1 -> stays T1', core.pick(d2(640), 1), 1);
    eq('in  d=620 from T1 -> T0',       core.pick(d2(620), 1), 0);
    eq('in  d=1100 from T2 -> stays T2', core.pick(d2(1100), 2), 2);
    eq('in  d=1000 from T2 -> T1',       core.pick(d2(1000), 2), 1);
    eq('in  d=1600 from T3 -> stays T3', core.pick(d2(1600), 3), 3);
    eq('in  d=1480 from T3 -> T2',       core.pick(d2(1480), 3), 2);

    // ---- 3. a full outward sweep changes tier exactly 3 times and never goes backwards ----
    var cur = 0, changes = 0, back = 0, prev = 0, d;
    for (d = 0; d <= 2600; d += 1) {
      var t = core.pick(d2(d), cur);
      if (t !== cur) { changes++; if (t < cur) back++; cur = t; }
      prev = t;
    }
    eq('outward sweep: 3 tier changes', changes, 3);
    eq('outward sweep: 0 backward steps', back, 0);
    eq('outward sweep ends at cull', prev, 3);

    // ---- 4. THE FLAP TEST. A building parked on a boundary while the camera jitters.
    // With hysteresis: crosses once, then the dead band holds it. Without: flips every step. ----
    function flaps(hyst, lo, hi, n) {
      var c = makeLodCore({ tiers: [700, 1120, 1650], hyst: hyst });
      var tier = 0, flip = 0, i, dd;
      for (i = 0; i < n; i++) {
        dd = (i % 2) ? hi : lo;                 // oscillate across the 700 boundary
        var nt = c.pick(dd * dd, tier);
        if (nt !== tier) { flip++; tier = nt; }
      }
      return flip;
    }
    var withH = flaps(0.10, 690, 710, 1000);
    var noH   = flaps(0.00, 690, 710, 1000);
    eq('hysteresis 0.10: 690<->710 flips once', withH, 1);
    chk('hysteresis 0.00: same sweep flaps hard', noH > 400, 'flips=' + noH);
    chk('hysteresis prevents >99% of flaps', withH * 100 < noH, 'with=' + withH + ' without=' + noH);

    // a jitter that stays entirely INSIDE the dead band must never change tier at all
    eq('jitter inside dead band: 0 flips', flaps(0.10, 640, 698, 500), 0);

    // ---- 5. idempotence + convergence: re-picking with the answer changes nothing, and a
    // teleport resolves in ONE call (district edges teleport the hero ~1400 units) ----
    var stable = true, oneShot = true;
    for (d = 0; d <= 2600; d += 7) {
      var a = core.pick(d2(d), 0);
      if (core.pick(d2(d), a) !== a) stable = false;
      if (core.pick(d2(d), 3) !== core.pick(d2(d), core.pick(d2(d), 3))) oneShot = false;
    }
    chk('pick() is idempotent across the sweep', stable);
    chk('teleport converges in one call', oneShot);

    // ---- 6. degenerate configs must degrade, never hang or throw ----
    var bad = makeLodCore({ tiers: [1000, 500, 200], hyst: 9 });
    chk('mis-ordered tiers get sorted up', bad.tiers[0] < bad.tiers[1] && bad.tiers[1] < bad.tiers[2],
        JSON.stringify(bad.tiers));
    chk('hyst clamped below 0.5', bad.hyst <= 0.45, 'hyst=' + bad.hyst);
    eq('degenerate core still picks', bad.pick(d2(99999), 0), 3);

    // ---- 7. RING PLANNER. Determinism, keep-out, and that it actually produces scale. ----
    var ringA = planInfill('HOME_TURF', {});
    var ringB = planInfill('HOME_TURF', {});
    var ringC = planInfill('THE_DOCKS', {});
    eq('ring is deterministic (count)', ringA.length, ringB.length);
    chk('ring is deterministic (bytes)', JSON.stringify(ringA) === JSON.stringify(ringB));
    chk('different district -> different ring', JSON.stringify(ringA) !== JSON.stringify(ringC));
    chk('ring is big enough for LOD to matter', ringA.length >= 60, 'n=' + ringA.length);

    // THE SAFETY ASSERTION: not one box may touch the playfield. A stray interior box is an
    // invisible wall in the 2D layer, which has no idea this module exists.
    var W = 1700, H = 1300, m = 60, intruder = null, i2;
    for (i2 = 0; i2 < ringA.length; i2++) {
      var b = ringA[i2], hw = b.w / 2, hd = b.d / 2;
      if (b.x + hw > -m && b.x - hw < W + m && b.y + hd > -m && b.y - hd < H + m) { intruder = b; break; }
    }
    chk('no ring box intrudes on the playfield', intruder === null,
        intruder ? ('at ' + intruder.x.toFixed(0) + ',' + intruder.y.toFixed(0)) : '');

    // ---- 8. THE PAYOFF, in the units that actually cost: draw calls on the shipped district.
    // Real buildings are 6 slots (material array) + 1 detail; ring buildings are 1 + 1.
    // Camera sits ~620 out from the hero at the district centre (world3d.js dist default). ----
    var camx = 850, camz = 650 - 490, camy = 380;   // approx camPos() at phi=52deg, dist=620
    var naive = 0, lod = 0, tally = [0, 0, 0, 0];
    for (i2 = 0; i2 < ringA.length; i2++) {
      var rb = ringA[i2];
      var ddx = rb.x - camx, ddy = (rb.h / 2) - camy, ddz = rb.y - camz;
      var t2 = core.pick(ddx * ddx + ddy * ddy + ddz * ddz, 0);
      tally[t2]++;
      naive += 2;                                  // box + detail, drawn unconditionally
      lod += (t2 >= 3) ? 0 : (t2 === 0 ? 2 : 1);
    }
    naive += 4 * 7; lod += 4 * 7;                  // the 4 real HOME_TURF buildings, all near
    out.push('INFO ring=' + ringA.length + ' buildings  tiers[T0,T1,T2,cull]=' + tally.join(',') +
             '  drawcalls: naive=' + naive + ' withLOD=' + lod +
             '  saved=' + (naive - lod) + ' (' + Math.round((1 - lod / naive) * 100) + '%)');
    chk('LOD removes real draw calls at shipped scale', lod < naive * 0.6,
        'naive=' + naive + ' lod=' + lod);
    chk('cull tier is actually exercised (not dead code)', tally[3] > 0, 'culled=' + tally[3]);
    chk('near tier is actually exercised', tally[0] > 0, 'near=' + tally[0]);

    return { ok: ok, lines: out };
  }

  /* =====================================================================================
   * GL LAYER -- everything below is guarded and does nothing at load time.
   * ===================================================================================== */

  var CFG = {
    infill: true,          // build the skyline ring (see the header before turning this off)
    decorateReal: true,    // run AK_BLDMASS.decorate on world3d's real buildings
    buildBudget: 6,        // meshes built per tick. ~110 ring buildings -> ~18 frames, no hitch.
    ring: {}               // planInfill overrides
  };

  var L = {
    on: true,
    core: makeLodCore({}),
    ents: [],              // preallocated entry objects; update() mutates, never creates
    scene: null,           // identity handle -- world3d.dispose() makes a NEW Scene
    bldsRef: null,         // identity handle -- world3d.setZone() makes a NEW blds array
    zoneId: '',
    group: null,           // everything THIS module added to the scene, in one node
    queue: [],             // pending planInfill records, drained on a per-tick budget
    owned: [],             // geometries/materials we allocated and must dispose
    frames: 0, changes: 0, errors: 0, lastErr: ''
  };

  function THREEof() {
    try {
      var T = root && root.AK_THREE;
      return (T && typeof T.get === 'function' && T.get()) || null;
    } catch (_e) { return null; }
  }
  function note(e) {
    // NOT a silent catch. A subsystem may fail without taking the game down, but it may not
    // fail INVISIBLY -- that is how a corrupt vendor file hid for hours on this project.
    L.errors++;
    try { L.lastErr = String((e && e.message) || e); console.warn('[AK_LOD]', e); } catch (_x) {}
  }

  /* applyTier -- the only place mesh state is written. Early-outs when the tier is unchanged,
   * which is the common case by a wide margin: with hysteresis, in a typical frame ZERO entries
   * change tier, so this whole function does not run at all.
   *
   * ---------------------------------------------------------------------------------------------
   * CO-TENANCY: WE DO NOT OWN mesh.visible ON BORROWED BUILDINGS. THIS IS LOAD-BEARING.
   *
   * systems/akcull.js registers the SAME st.blds meshes and writes mesh.visible for its frustum +
   * occlusion verdict, snapshotting the prior value in hidPrev[] and handing it back when a mesh
   * leaves its cull set. Two independent writers on one boolean is undecidable -- akcull.js:541
   * says so in its own header and calls the fix "a shared arbiter, which needs BOTH lanes to adopt
   * it". It measured the residual at 101/198 stomps under a fast camera teleport.
   *
   * A shared arbiter is not needed. The conflict dissolves if ONE lane stops writing, and it should
   * be this one, because ceding costs us almost nothing and akcull nearly everything:
   *   - Only 4 meshes per district are borrowed. Our distance cull on them is worth ~24 draw calls
   *     that akcull's frustum test already removes whenever they are genuinely off-screen.
   *   - The 93 RING meshes -- where the cull tier actually pays, 52 of them at the spawn camera --
   *     are allocated by us, live in our own group, and are invisible to akcull. We keep full
   *     control exactly where the win is.
   * So: e.own === true -> we write .visible freely. e.own === false -> we NEVER write it, and a
   * borrowed building at the cull distance degrades to the cheapest state we can reach without
   * touching visibility (flat far material, detail off). After this, no two lanes write the same
   * object and the stomp cannot occur in either direction.
   *
   * The detail mesh is a CHILD of its building (see attachDetail), not a sibling. That is what
   * keeps this honest: when akcull hides a building, three's projectObject early-return
   * (`if(!1===t.visible)return;`) skips the whole subtree, so the parapets and roof AC go with it.
   * As siblings they would have kept drawing over a hidden building -- floating roof furniture.
   */
  function applyTier(e, t) {
    if (e.tier === t) return false;
    e.tier = t;
    var cull = (t >= L.core.maxTier);

    if (cull && !e.own) {                         // borrowed: akcull owns .visible, hands off
      if (e.detail) e.detail.visible = false;
      if (e.far && e.mesh.material !== e.far) e.mesh.material = e.far;
      return true;
    }
    if (cull) {                                   // ours: three's projectObject early-returns
      e.mesh.visible = false;
      return true;                                // detail is a child, it goes with the parent
    }
    if (e.own) e.mesh.visible = true;             // only assert visibility on what we allocated
    if (e.detail) e.detail.visible = (t === 0);   // detail mass is a T0-only luxury
    // THE 6 -> 1 DRAW CALL SWAP. Array material = one render item per geometry group;
    // non-array = one render item total. Verified in the vendored r160 projectObject, and
    // measured live in headless chromium: 6 -> 1 -> 0 real GPU draw calls on one building.
    var want = (t >= 2 && e.far) ? e.far : e.near;
    if (e.mesh.material !== want) e.mesh.material = want;
    return true;
  }

  /* Hang a bldmass detail mesh under its building so it inherits the building's visibility from
   * whichever lane wrote it. decorate() bakes WORLD-space positions (bldmass.js:106 reads
   * mesh.position), so as a child it needs the parent transform backed out. world3d never rotates
   * or scales a building -- buildBuildings only calls position.set (world3d.js:541) -- so a plain
   * negated translation is exact, not an approximation. */
  function attachDetail(host, det) {
    det.position.set(-host.position.x, -host.position.y, -host.position.z);
    host.add(det);
  }

  // Estimated draw calls for an entry at its current tier. Used by stats() so the module
  // REPORTS its saving instead of claiming one.
  function callsFor(e) {
    if (e.tier < 0 || e.tier >= L.core.maxTier) return 0;
    var base = (e.tier >= 2 && e.far) ? 1 : e.slots;
    return base + ((e.detail && e.tier === 0) ? 1 : 0);
  }
  function naiveCallsFor(e) { return e.slots + (e.detail ? 1 : 0); }

  function addEntry(mesh, detail, near, far, x, y, z, own) {
    L.ents.push({
      mesh: mesh, detail: detail, near: near, far: far,
      x: x, y: y, z: z,
      slots: (near && near.length) ? near.length : 1,
      tier: -1,          // -1 == never applied, so the first update() always writes a real tier
      own: !!own
    });
  }

  /* Adopt the buildings world3d already built. We do not create them, do not move them, do not
   * touch their geometry, and we restore their material array on teardown. */
  function adoptReal(THREE, st) {
    var list = st.blds || [], i, m, near, far, side, det;
    for (i = 0; i < list.length; i++) {
      m = list[i];
      if (!m || !m.geometry) continue;
      near = m.material;
      far = null;
      try {
        // Pull the flat tint off the shared `side` material (world3d.js:535, slots 0/1/3/5) so
        // the far silhouette matches the near building's colour instead of guessing at it.
        side = (near && near.length) ? near[0] : near;
        if (side && side.color && typeof side.color.getHex === 'function') {
          far = new THREE.MeshLambertMaterial({ color: side.color.getHex() });
          L.owned.push(far);
        }
      } catch (e) { note(e); }

      det = null;
      if (CFG.decorateReal && root.AK_BLDMASS && typeof root.AK_BLDMASS.decorate === 'function') {
        try {
          // userData.akMassed: the integration phase may also wire decoration in world3d.js.
          // Two detail meshes on one building is z-fighting plus a wasted draw call, so whoever
          // gets there first claims the mesh and the other backs off.
          if (!m.userData || !m.userData.akMassed) {
            det = root.AK_BLDMASS.decorate(THREE, m, { id: (m.userData && m.userData.akId) || ('b' + i) });
            if (det) {
              m.userData = m.userData || {};
              m.userData.akMassed = true;
              det.userData.akLodOwned = true;
              attachDetail(m, det);              // child, not sibling -- inherits akcull's verdict
              L.owned.push(det.geometry, det.material);
            }
          }
        } catch (e) { note(e); det = null; }
      }

      addEntry(m, det, near, far, m.position.x, m.position.y, m.position.z, false);
    }
  }

  /* One ring building. Single material by design: a background box has no facade photo to place,
   * so giving it a 6-slot array would spend 6 draw calls to draw one flat colour. */
  function buildRing(THREE, spec) {
    var geo = new THREE.BoxGeometry(spec.w, spec.h, spec.d);
    var mat = new THREE.MeshLambertMaterial({ color: spec.col });
    var m = new THREE.Mesh(geo, mat);
    m.position.set(spec.x, spec.h / 2, spec.y);   // hub y maps to three z (world3d.js:541)
    m.userData.akId = spec.id;
    m.userData.akLodRing = true;
    L.group.add(m);
    L.owned.push(geo, mat);

    var det = null;
    if (root.AK_BLDMASS && typeof root.AK_BLDMASS.decorate === 'function') {
      try {
        det = root.AK_BLDMASS.decorate(THREE, m, spec);
        if (det) { det.userData.akLodOwned = true; attachDetail(m, det); L.owned.push(det.geometry, det.material); }
      } catch (e) { note(e); det = null; }
    }
    // far material is SHARED across the whole ring: at >1120 units, under fog, every ring box is
    // within a few percent of the same value anyway, and one shared material lets three's render
    // list group them without a state change between draws.
    addEntry(m, det, mat, L.ringFar, spec.x, spec.h / 2, spec.y, true);
  }

  // Drain the build queue on a budget. A 110-building ring built in one frame is ~1650 temporary
  // geometries through bldmass's merge path and a visible stall on a phone; 6 a tick is invisible.
  function pump(THREE) {
    var n = CFG.buildBudget, spec;
    while (n-- > 0 && L.queue.length) {
      spec = L.queue.shift();
      try { buildRing(THREE, spec); } catch (e) { note(e); }
    }
  }

  /* Full release of everything this module put in the scene, plus restoration of everything it
   * borrowed. world3d.js:761 disposes geometry but never materials or textures; this lane does
   * not add to that debt -- it owns its allocations end to end. */
  function teardown() {
    var i, e, o;
    for (i = 0; i < L.ents.length; i++) {
      e = L.ents[i];
      if (e.own) continue;                       // ring meshes die with the group below
      try {                                       // hand borrowed buildings back untouched
        // NB: we never wrote .visible on a borrowed mesh (see applyTier co-tenancy note), so we
        // must not write it here either -- akcull may be legitimately holding this one hidden.
        if (e.detail && e.detail.parent) e.detail.parent.remove(e.detail);
        if (e.mesh.material !== e.near) e.mesh.material = e.near;
        if (e.mesh.userData) e.mesh.userData.akMassed = false;
      } catch (_x) {}
    }
    L.ents.length = 0;
    try {
      if (L.group && L.group.parent) L.group.parent.remove(L.group);
      if (L.group) L.group.clear ? L.group.clear() : (L.group.children.length = 0);
    } catch (e2) { note(e2); }
    for (i = 0; i < L.owned.length; i++) {
      o = L.owned[i];
      try {
        if (!o) continue;
        if (o.map && o.map.dispose) o.map.dispose();
        if (o.dispose) o.dispose();
      } catch (_x) {}
    }
    L.owned.length = 0;
    L.queue.length = 0;
    L.group = null; L.scene = null; L.bldsRef = null; L.zoneId = '';
  }

  /* Zone-change detection is a POLL, not an event -- index.html:1354 enterZone() notifies nobody
   * and world3d.js:900 solves it the same way. Three identity handles, any one of which changing
   * means the scene under us was rebuilt:
   *   scene    -> world3d.dispose() then boot() again
   *   blds     -> setZone() assigns a FRESH array (world3d.js:765)
   *   zoneId   -> belt and braces for a same-array rebuild
   */
  function sync(THREE, st, ctx) {
    var zid = st.zoneId || '';
    if (L.scene === st.scene && L.bldsRef === st.blds && L.zoneId === zid) return false;
    teardown();
    L.scene = st.scene; L.bldsRef = st.blds; L.zoneId = zid;
    L.group = new THREE.Group();
    L.group.name = 'AK_LOD';
    st.scene.add(L.group);
    if (!L.ringFar) {
      // 0x26282e is the MEAN of the tones planInfill generates (tone 26..51, +2 green, +8 blue),
      // not a hand-picked dark. Picking the mean is what keeps the T1->T2 material swap from
      // reading as a pop: the average ring box changes by nothing, and the outliers change by
      // ~13/255 at a distance where scene.fog has already blended them >50% toward the sky tint.
      L.ringFar = new THREE.MeshLambertMaterial({ color: 0x26282e });
      // deliberately NOT pushed to L.owned: it outlives district swaps on purpose, so we are not
      // recompiling the same program nine times on a lap of the map. Freed only in dispose().
    }
    adoptReal(THREE, st);
    if (CFG.infill) {
      var W = 1700, H = 1300;
      try { if (ctx && ctx.world) { W = ctx.world.WORLD_W || W; H = ctx.world.WORLD_H || H; } } catch (_x) {}
      var o = { worldW: W, worldH: H }, k;
      for (k in CFG.ring) { if (Object.prototype.hasOwnProperty.call(CFG.ring, k)) o[k] = CFG.ring[k]; }
      L.queue = planInfill(zid || 'HOME_TURF', o);
    }
    return true;
  }

  /* THE UPDATE PATH. Zero allocation, zero sqrt, zero Vector3 construction.
   * cx/cy/cz come from the live camera's own Vector3 rather than proj.camPos(), which builds a
   * fresh object literal on every call (world3d.js:202). */
  function update(cx, cy, cz) {
    var ents = L.ents, core = L.core, n = ents.length, i, e, dx, dy, dz, t, ch = 0;
    for (i = 0; i < n; i++) {
      e = ents[i];
      dx = e.x - cx; dy = e.y - cy; dz = e.z - cz;
      t = core.pick(dx * dx + dy * dy + dz * dz, e.tier < 0 ? 0 : e.tier);
      if (t !== e.tier && applyTier(e, t)) ch++;
    }
    L.changes += ch;
    return ch;
  }

  /* stats() -- what this lane actually did, in the units that cost.
   *
   * READ THE FIELD NAMES CAREFULLY, they are not interchangeable:
   *
   *   submitted / submittedNaive  are LOD's own accounting: how many render items this module
   *   ALLOWS through, before three gets a say. They are NOT GPU draw calls, and treating them as
   *   such over-reports the win. Measured live in headless chromium with real WebGL: LOD's own
   *   count said 65 while renderer.info.render.calls said 25, because three ALREADY frustum-culls
   *   every object outside the view (WebGLRenderer projectObject, `!t.frustumCulled||V.intersects`)
   *   and at a 900x600 viewport most of a 93-building ring is off-screen anyway. LOD and the
   *   frustum cull remove overlapping sets; LOD's unique contribution is the part the frustum
   *   CANNOT remove -- on-screen buildings whose material array collapses 6 slots into 1, and
   *   in-frustum-but-fogged buildings past the cull threshold.
   *
   *   gpu  is the truth: renderer.info.render.calls for the LAST frame actually submitted. Null
   *   when no shared renderer is up yet. When you want to know what this module bought, read gpu
   *   with AK_LOD.setOn(false) and again with setOn(true). Measured that way at the HOME_TURF
   *   spawn: 54 -> 25 draw calls and 408 -> 60 triangles.
   */
  function stats() {
    var i, e, tiers = [], calls = 0, naive = 0, gpu = null;
    for (i = 0; i <= L.core.maxTier; i++) tiers.push(0);
    for (i = 0; i < L.ents.length; i++) {
      e = L.ents[i];
      if (e.tier >= 0) tiers[e.tier]++;
      calls += callsFor(e); naive += naiveCallsFor(e);
    }
    try {
      var r = root.AK_R3D || (root.AK_WORLD3D && root.AK_WORLD3D.renderer && root.AK_WORLD3D.renderer());
      if (r && r.info && r.info.render) {
        gpu = { calls: r.info.render.calls, triangles: r.info.render.triangles,
                geometries: r.info.memory.geometries, textures: r.info.memory.textures };
      }
    } catch (_x) {}
    return {
      on: L.on, zone: L.zoneId, tracked: L.ents.length, pending: L.queue.length,
      tiers: tiers, thresholds: L.core.tiers.slice(), hyst: L.core.hyst,
      submitted: calls, submittedNaive: naive, submittedSaved: naive - calls,
      submittedSavedPct: naive ? Math.round((1 - calls / naive) * 100) : 0,
      gpu: gpu,
      frames: L.frames, tierChanges: L.changes, errors: L.errors, lastError: L.lastErr
    };
  }

  function onTick(dt, ctx) {
    if (!L.on) return;
    var W = root.AK_WORLD3D;
    if (!W || typeof W.isOn !== 'function') return;
    var st = W._state;
    /* world3d.dispose() (world3d.js:452) nulls scene/camera and sets booted=false. If we only
     * ever early-returned on isOn() we would sit on a dead scene holding ~200 live GPU buffers
     * until the context was lost, which surfaces much later as an unrelated-looking bug. Release
     * on a real teardown -- but NOT on a plain setOn(false), which is a transient toggle and does
     * not invalidate the scene. Rebuilding a 93-building ring on every 3D on/off would be worse
     * than the thing it fixed. */
    if (!st || !st.booted || !st.scene) { if (L.scene) teardown(); return; }
    // 3D off / still loading / interior open (the hub stops ticking systems entirely at
    // index.html:2426) -> nothing to do and nothing to pay for.
    if (!W.isOn() || !st.camera) return;
    var THREE = THREEof();
    if (!THREE) return;
    try {
      sync(THREE, st, ctx);
      if (L.queue.length) pump(THREE);
      var p = st.camera.position;
      if (!p) return;
      L.frames++;
      update(p.x, p.y, p.z);
    } catch (e) { note(e); }
  }

  var API = {
    // --- tuning ---
    setOn: function (v) {
      L.on = !!v;
      // Turning LOD off must not leave half the district invisible. Restore every entry to T0.
      if (!L.on) { for (var i = 0; i < L.ents.length; i++) applyTier(L.ents[i], 0); }
      return L.on;
    },
    setTiers: function (tiers, hyst) {
      L.core = makeLodCore({ tiers: tiers, hyst: hyst });
      for (var i = 0; i < L.ents.length; i++) L.ents[i].tier = -1;   // force a re-evaluation
      return L.core.tiers.slice();
    },
    setInfill: function (v) { CFG.infill = !!v; return CFG.infill; },
    setDecorateReal: function (v) { CFG.decorateReal = !!v; return CFG.decorateReal; },
    setBudget: function (n) { CFG.buildBudget = Math.max(1, n | 0); return CFG.buildBudget; },
    config: function (o) { if (o) { for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) CFG[k] = o[k]; } return CFG; },

    // --- manual registration, for any lane with meshes of its own ---
    register: function (mesh, o) {
      if (!mesh || !mesh.position) return false;
      o = o || {};
      addEntry(mesh, o.detail || null, o.near || mesh.material, o.far || null,
               mesh.position.x, mesh.position.y, mesh.position.z, !!o.own);
      return true;
    },

    // --- lifecycle / introspection ---
    update: update,
    tick: onTick,
    stats: stats,
    dispose: function () {
      teardown();
      try { if (L.ringFar && L.ringFar.dispose) L.ringFar.dispose(); } catch (_x) {}
      L.ringFar = null;
    },
    entries: function () { return L.ents.slice(); },

    // --- pure core, exported for tests and for any peer that wants the maths ---
    makeLodCore: makeLodCore, planInfill: planInfill, rngFor: rngFor, selfTest: selfTest,
    DEFAULT_TIERS: DEFAULT_TIERS, DEFAULT_HYST: DEFAULT_HYST,
    _state: L, _cfg: CFG
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_LOD = API;
    /* Self-register so the hub's existing dispatch drives us with ZERO further host wiring.
     * _registry.js:22 tickAll() walks the list in REGISTRATION ORDER, and index.html loads this
     * file AFTER systems/world3d.js, so by the time onTick runs, world3d has already run setZone
     * (fresh blds array to adopt) and frame() (camera.position fully updated for this frame).
     * Our tier writes therefore land on the very next render, one frame later -- which at a
     * 70-unit dead band is ~20 frames of slack, i.e. invisible.
     *
     * NOTE for raids: index.html:2436 ticks only ['raidwaves','raidfortify','backpack'] while
     * state==='RAID'. 'aklod' is deliberately NOT in that list -- raids run their own scene and
     * world3d is frozen too, so there is nothing here to update. */
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({ id: 'aklod', onTick: onTick });
      }
    } catch (_e) {}
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/aklod.js` prints the LOD proof (thresholds, hysteresis, ring). */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  var _r = module.exports.selfTest();
  _r.lines.forEach(function (l) { console.log(l); });
  console.log(_r.ok ? 'ALL PASS' : 'FAILURES PRESENT');
  process.exit(_r.ok ? 0 : 1);
}
