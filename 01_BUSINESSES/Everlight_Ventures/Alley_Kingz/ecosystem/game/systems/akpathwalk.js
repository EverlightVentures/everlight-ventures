/* ALLEY KINGZ -- AK_PATHWALK: walk the streets.  AK-PATHWALK 2026-07-20.
 *
 * OPERATOR: "I see there's a path but I can't walk down the path. I should be able to walk down the
 * path and follow and have it rotate like a real world."
 *
 * The streets are already generated -- akworldgen.planStreets() returns a LATTICE, not a spline:
 *     { vx: [ {c, half, rank}, ... ],   hy: [ {c, half, rank}, ... ] }
 * vertical and horizontal corridor bands, each a centre line and a half-width, ranked
 * main / street / alley. They are drawn, and buildings are kept out of them, but nothing ever
 * connected them to MOVEMENT -- so the player sees roads and walks across them like open ground.
 *
 * WHY NOT A CatmullRomCurve3 (the usual advice)
 * A curve is the right tool for a winding rail. This lattice is axis-aligned, so the nearest point
 * on a corridor is |x - c| -- one subtraction. A curve would need ~100 getPointAt() samples EVERY
 * FRAME to find the closest point, allocating a Vector3 each time, to compute something exactly
 * representable in closed form. On a phone at 60fps that is thousands of wasted allocations a second.
 *
 * WHAT IT DOES -- ASSIST, NEVER RAILS
 * Inside a corridor, a gentle force pulls the player toward its centre line, and ONLY on the axis
 * across the street (walking north down a north-south street is never resisted). Off a corridor it
 * does nothing at all. You can always leave the road; it just stops feeling like an open field.
 * Strength scales with how far off-centre you are, so the middle of the street is free movement and
 * the gutter nudges you back. A hard snap would fight the player, which is worse than no assist.
 */
window.AK_PATHWALK = (function (root) {
  'use strict';

  var ENABLED = true;
  var ASSIST  = 0.22;    // fraction of the off-centre error corrected per second at full strength
  var NEAR    = 1.35;    // a corridor "claims" you out to 1.35x its half-width, so kerbs still pull

  var _lattice = null, _zone = '', _diag = { claimed: 0, applied: 0, zone: '' };

  // Pull the street plan for a district. Cached per zone -- planStreets is seeded and deterministic,
  // so re-deriving it every frame would burn CPU to produce a bit-identical answer.
  function latticeFor(zoneId, W, H) {
    if (_lattice && _zone === zoneId) return _lattice;
    var G = root.AK_WORLDGEN;
    if (!G || typeof G.planStreets !== 'function') return null;
    try {
      _lattice = G.planStreets(zoneId, W || 1700, H || 1300, {});
      _zone = zoneId;
    } catch (_e) { _lattice = null; }
    return _lattice;
  }

  // Nearest band claiming this coordinate. Returns {c, half, rank} or null.
  function claim(bands, v) {
    if (!bands) return null;
    var best = null, bestD = Infinity;
    for (var i = 0; i < bands.length; i++) {
      var b = bands[i], d = Math.abs(v - b.c);
      if (d <= b.half * NEAR && d < bestD) { bestD = d; best = b; }
    }
    return best;
  }

  /* assist(me, dt, zoneId, W, H)
   * Mutates me.x / me.y toward the centre of whatever corridor claims the player.
   * Returns true if any correction was applied (used by diag and by the tests).
   *
   * The axis rule is the whole design: a VERTICAL corridor runs north-south, so it constrains X
   * (how far across the road you are) and must never touch Y (how far along it you have walked).
   * Getting that backwards would drag the player backwards down the street they are walking. */
  function assist(me, dt, zoneId, W, H) {
    if (!ENABLED || !me) return false;
    var L = latticeFor(zoneId, W, H);
    if (!L) return false;
    var k = Math.max(0, Math.min(1, ASSIST * (dt || 0.016) * 60 * 0.25));
    var did = false;

    var v = claim(L.vx, me.x);          // vertical corridor -> correct X only
    if (v) {
      _diag.claimed++;
      var ex = v.c - me.x;
      // Scale by how far off-centre: dead zone in the middle third, full pull at the kerb.
      var fx = Math.min(1, Math.abs(ex) / Math.max(1, v.half));
      if (fx > 0.33) { me.x += ex * k * fx; did = true; }
    }
    var h = claim(L.hy, me.y);          // horizontal corridor -> correct Y only
    if (h) {
      _diag.claimed++;
      var ey = h.c - me.y;
      var fy = Math.min(1, Math.abs(ey) / Math.max(1, h.half));
      if (fy > 0.33) { me.y += ey * k * fy; did = true; }
    }
    if (did) _diag.applied++;
    _diag.zone = zoneId || '';
    return did;
  }

  // Is this point on a walkable corridor at all? Useful for HUD hints and for the path-following
  // camera, and it is the cheap test the tunnel/transition work will want later.
  function onPath(x, y, zoneId, W, H) {
    var L = latticeFor(zoneId, W, H);
    if (!L) return false;
    return !!(claim(L.vx, x) || claim(L.hy, y));
  }

  var api = {
    id: 'akpathwalk',
    onTick: function (dt, ctx) {
      try {
        if (!ctx || !ctx.me) return;
        // AK-PATHWALK-FIX 2026-07-20: arriving here IS the IN_ZONE signal -- index.html:2608 calls
        // akTickSystems ONLY under state==='IN_ZONE' && !interiorOpen && !entering && !_sf. The old
        // guard read ctx.state/window.state, but `state` is a top-level `let` (index.html:1309) so it
        // is not a window property and AK_CTX has no state getter: both reads were undefined, the
        // guard always returned, and this whole module was a silent no-op. Raids are excluded by the
        // host gate, and belt-and-braces by the world size (raids swap WORLD_W/H to 1500x1150).
        var z = (ctx.activeZone && ctx.activeZone.id) || '';
        var w = (ctx.world && ctx.world.WORLD_W) || 1700;
        var hh = (ctx.world && ctx.world.WORLD_H) || 1300;
        assist(ctx.me, dt, z, w, hh);
      } catch (_e) {}
    }
  };
  if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api);

  return {
    assist: assist, onPath: onPath, latticeFor: latticeFor,
    setEnabled: function (b) { ENABLED = !!b; return ENABLED; },
    isEnabled: function () { return ENABLED; },
    setStrength: function (v) { ASSIST = Math.max(0, Math.min(1, v || 0)); return ASSIST; },
    diag: function () { return { claimed: _diag.claimed, applied: _diag.applied, zone: _diag.zone,
                                 enabled: ENABLED, strength: ASSIST, hasLattice: !!_lattice }; }
  };
})(window);
