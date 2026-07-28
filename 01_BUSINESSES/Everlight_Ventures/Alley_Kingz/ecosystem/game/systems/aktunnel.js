/* ALLEY KINGZ -- AK_TUNNEL: walk BETWEEN districts through a real gateway.  AK-TUNNEL 2026-07-20.
 *
 * OPERATOR: "I walked to the edge and switched districts. It should be like walking down a path,
 * between buildings, and at the last building there's a tunnel that takes me to the next district."
 *
 * WHAT EXISTS TODAY (index.html:2574-2578, read before a line of this was written):
 *     if(state==='IN_ZONE' && spawnGrace<=0){ var E=42, ez=null;
 *       if(me.x<E && activeZone.edges.W) ez=activeZone.edges.W; else if(...E/N/S...)
 *       if(ez){ var tz=getZone(ez.to); if(tz.locked) showBarrier(tz); else enterZone(ez.to,ez.spawn); } }
 * Touch ANY pixel of a 1300px-long wall and the district hard-cuts. There is nothing to walk
 * toward, nothing to aim at, and no moment of passage -- which is exactly the complaint. The zone
 * records already carry everything a gateway needs (index.html:846-884):
 *     edges: { N|S|E|W: { to:'<ZONE_ID>', spawn:{x,y} } }
 *
 * WHERE THE MOUTH GOES -- DERIVED, NOT AUTHORED.
 * Every spawn in that table is the MIRROR of the edge you came through (the Stardew rule the
 * comment at index.html:842 states outright): DOWNTOWN.edges.E spawns you at {x:150,y:650} in
 * NEON_HEIGHTS, and NEON_HEIGHTS.edges.W spawns you back at {x:1550,y:650}. Both agree on y=650.
 * So the PERPENDICULAR component of the spawn IS the shared centre-line of that border crossing:
 *     E/W edge -> mouth sits at y = spawn.y        N/S edge -> mouth sits at x = spawn.x
 * Two districts therefore place the SAME crossing at the SAME world coordinate without either one
 * storing a tunnel position. Nothing new has to be authored into ZONES, and a future district gets
 * a correctly-placed tunnel the moment someone types its edges record.
 *
 * Then it SNAPS to the street. akpathwalk's lattice (AK_PATHWALK.latticeFor -> {vx,hy} corridor
 * bands) is queried, and if a corridor centre lies within SNAP=140px of the derived point the mouth
 * moves onto the corridor. That is what makes it "walk down the path and at the last building
 * there's a tunnel" instead of an arch parked in the middle of a block. No lattice (module absent,
 * worldgen missing) -> the derived point stands, and everything below still works.
 *
 * UNITS ARE PIXELS. The hero is 60 tall, r=23; buildings are 90-205 tall; the district is
 * 1700x1300. Every number here is sized off the hero, not off a metres-based tutorial:
 *     HALF_W 130  -> a 260px opening = 4.3 hero-heights wide. Wide enough to walk into at a jog
 *                    without aiming, narrow enough that it reads as a specific PLACE on the wall.
 *     ARCH_H 168  -> 2.8 hero-heights. Deliberately NOT taller than the block: buildings run
 *                    90-205, so the arch sits INSIDE the skyline and reads as part of the city.
 *     THROAT 210  -> 3.5 hero-heights of recession past the boundary. Below ~2 it reads as a
 *                    doorway; this reads as something with an inside.
 *     TELEGRAPH 430 -> ~7 hero-heights, about half a 900px viewport, so the destination name lands
 *                    while the gate is still a thing on the horizon you are choosing to walk to.
 *
 * NEVER TRAP THE PLAYER. Gating the crossing on the mouth means the rest of the wall becomes solid,
 * and a player pinned in a corner who cannot read the hint would be stuck in a district forever --
 * a far worse bug than the one being fixed. So MERCY_S: hold against a blocked stretch of wall for
 * 2.6 continuous seconds and crossGate hands control BACK to the host, which performs its original
 * hard cut unchanged. The feature degrades into today's behaviour rather than into a soft-lock.
 *
 * LOCKED DISTRICTS. THE_OVERLOOK ('POLICE CHECKPOINT') and THE_UNDERCITY ('COLLAPSED BRIDGE') carry
 * locked:true + barrierLabel. Those get a SEALED mouth -- same arch so the geography still reads as
 * a real crossing, but the throat is bricked, hazard-striped, and captioned with the barrier reason.
 * A sealed mouth is exempt from MERCY_S: mercy exists to stop soft-locks, and a sealed border is
 * not a soft-lock, it is content.
 *
 * ONE RENDERER LAW. This module constructs no WebGLRenderer and imports no three.js. It paints on
 * the 2D overlay through ctx.world.project()/wx()/wy() -- the same projected-overlay path every
 * other plug-in uses (encounters.js:297, missions.js:557, buildmode.js:2030) -- so it inherits the
 * 3D camera for free and costs nothing when 3D is off.
 *
 * IT DOES NOT EDIT index.html. Draw + tick arrive through AK_SYSTEMS (_registry.js:22/23), which is
 * automatic. The ONE thing it cannot self-wire is the crossing decision, because that lives inside
 * update(). crossGate() is the seam: the host calls it, and a `false` return means "not mine, do
 * exactly what you did before". See the Wire-phase call site handed back with this file.
 *
 * WHY onTick IS THE 'IN_ZONE' SIGNAL. index.html:2608 calls akTickSystems ONLY under
 * state==='IN_ZONE' && !interiorOpen && !entering && !_sf, while akDrawSystems (index.html:2824)
 * runs every frame including RAID. `state` is a top-level `let` (index.html:1309) so it is NOT a
 * window property and NOT on AK_CTX -- reading ctx.state gives undefined. (That is a live bug in
 * akpathwalk.js, whose onTick guard `if (st !== 'IN_ZONE') return;` therefore always returns; it is
 * reported with this lane.) So instead of a broken state read, the tick STAMPS a timestamp and the
 * draw refuses to paint on a stale stamp. Fresh tick == the host is in IN_ZONE, by construction.
 */
window.AK_TUNNEL = (function (root) {
  'use strict';

  var ENABLED = true;

  // ---- geometry, all in pixels, all sized off the 60px hero (see header) ----
  // MEASURED against the real lattice (node harness, akworldgen.planStreets('HOME_TURF',1700,1300)):
  // the two MAIN corridors land at vx c=850 half=75 and hy c=650 half=75, i.e. a 150px-wide spine
  // road -- and the derived mouth centres are 850/650 exactly, so every tunnel already terminates a
  // boulevard with ZERO snap displacement. HALF_W 130 therefore flares 55px past each kerb: the
  // road runs straight in with margin on both sides, which is what a gateway plaza should do.
  var HALF_W    = 130;   // half the walkable opening
  var ARCH_H    = 168;   // top of the arch above ground
  var PYLON_W   = 40;    // thickness of each side pylon, along the wall
  var PYLON_D   = 46;    // how far the pylons stand proud of the boundary, into the district
  var THROAT    = 210;   // how far the tunnel recedes PAST the boundary (outside world bounds)
  var LINTEL_H  = 34;    // depth of the span across the top
  var SNAP      = 140;   // pull the mouth onto a street corridor within this range
  var TELEGRAPH = 430;   // destination-name range
  var MERCY_S   = 2.6;   // seconds pinned to a blocked wall before the host takes back over
  var WALK_S    = 0.55;  // passage time -- the beat that makes it a walk, not a teleport
  var ARRIVE_S  = 0.60;  // emerging-from-the-throat fade on the far side
  var BANNER_CD = 6.0;   // per-mouth telegraph cooldown

  var DIRS = ['N', 'S', 'E', 'W'];

  var _cache = null, _cacheKey = '';
  var _walk = null;              // active passage {dir, ez, cb, t}
  var _arrive = 0;               // seconds left of the arrival fade
  var _lastZone = '';
  var _pressT = 0, _pressAt = -1e9, _pressDir = '';
  var _bannerAt = {};            // mouth key -> last telegraph time (seconds)
  var _now = 0;                  // seconds, advanced by onTick
  var _tickAt = -1e9;            // last tick stamp -- the IN_ZONE proof (see header)
  var _diag = { mouths: 0, zone: '', crossed: 0, blocked: 0, mercy: 0, sealed: 0, drew: 0 };

  /* ---------------------------------------------------------------------
   * FRAME: one place that knows how a direction maps onto the world box.
   * point(dir, cx, cy, t, d, W, H) -- t = offset ALONG the wall from the mouth centre,
   *                                   d = distance INWARD from the boundary (negative = throat).
   * Every draw and every distance test below goes through this, so there is exactly one
   * opportunity to get a sign backwards instead of four. Standing law: left stays left --
   * the tangent axis is +y for E/W and +x for N/S in BOTH districts of a crossing, so a
   * landmark on your left walking east is on your right walking back west, as in life.
   * ------------------------------------------------------------------- */
  function point(dir, cx, cy, t, d, W, H) {
    if (dir === 'W') return { x: d,      y: cy + t };
    if (dir === 'E') return { x: W - d,  y: cy + t };
    if (dir === 'N') return { x: cx + t, y: d };
    return                 { x: cx + t, y: H - d };            // 'S'
  }
  // The player's position along the wall, measured from the mouth centre (same axis as `t`).
  function alongOf(dir, m, me) {
    return (dir === 'E' || dir === 'W') ? (me.y - m.cy) : (me.x - m.cx);
  }
  // Human hint for "the gate is THIS way along the wall". Screen-space truth, not compass poetry:
  // on an E/W wall the tangent is +y = DOWN the map = south, so a player at +delta walks north.
  function alongWord(dir, delta) {
    if (dir === 'E' || dir === 'W') return delta > 0 ? 'north' : 'south';
    return delta > 0 ? 'west' : 'east';
  }

  /* ---------------------------------------------------------------------
   * MOUTH DERIVATION. Pure: give it a zone record and it returns the crossings.
   * Exported for the test harness -- no DOM, no canvas, no globals touched.
   * ------------------------------------------------------------------- */
  function nearestBand(bands, v) {
    if (!bands || !bands.length) return null;
    var best = null, bd = SNAP;
    for (var i = 0; i < bands.length; i++) {
      var c = bands[i] && bands[i].c;
      if (typeof c !== 'number') continue;
      var d = Math.abs(v - c);
      if (d < bd) { bd = d; best = c; }
    }
    return best;
  }
  function deriveMouth(zone, dir, W, H, lattice, zones) {
    if (!zone || !zone.edges) return null;
    var e = zone.edges[dir];
    if (!e || !e.to) return null;
    var sp = e.spawn || {};
    // The perpendicular component of the MIRRORED spawn is the shared centre-line (header).
    var cx = (typeof sp.x === 'number') ? sp.x : W / 2;
    var cy = (typeof sp.y === 'number') ? sp.y : H / 2;
    var snapped = false;
    // Snap onto a street corridor so the tunnel terminates a road, not a block face.
    if (lattice) {
      if (dir === 'E' || dir === 'W') {
        var hb = nearestBand(lattice.hy, cy);
        if (hb !== null) { cy = hb; snapped = true; }
      } else {
        var vb = nearestBand(lattice.vx, cx);
        if (vb !== null) { cx = vb; snapped = true; }
      }
    }
    // Pin the OTHER component to the wall itself, so {cx,cy} is a genuine world position -- the
    // centre of the opening -- rather than one meaningful number beside one leftover from the spawn
    // record. Without this an E mouth carries cx=150 (the far district's spawn x, meaningless here)
    // and the first person to reach for m.cx on an E/W mouth gets a plausible-looking wrong answer.
    if (dir === 'E' || dir === 'W') cx = (dir === 'W') ? 0 : W;
    else                            cy = (dir === 'N') ? 0 : H;
    var tz = (zones && zones[e.to]) || null;
    return {
      key: (zone.id || '?') + ':' + dir,
      dir: dir, cx: cx, cy: cy,
      to: e.to, spawn: e.spawn,
      name: (tz && tz.name) || String(e.to).replace(/_/g, ' '),
      locked: !!(tz && tz.locked),
      barrierLabel: (tz && tz.barrierLabel) || 'SEALED',
      snapped: snapped
    };
  }
  function deriveAll(zone, W, H, lattice, zones) {
    var out = [];
    if (!zone || !zone.edges) return out;
    for (var i = 0; i < DIRS.length; i++) {
      var m = deriveMouth(zone, DIRS[i], W, H, lattice, zones);
      if (m) out.push(m);
    }
    return out;
  }

  // Cached per zone+size. planStreets is seeded/deterministic, so recomputing per frame would
  // burn CPU to produce a bit-identical answer (rule 7: seeded determinism only).
  function mouths(ctx) {
    var z = ctx && ctx.activeZone;
    if (!z) return [];
    var W = (ctx.world && ctx.world.WORLD_W) || 1700, H = (ctx.world && ctx.world.WORLD_H) || 1300;
    var key = (z.id || '?') + '|' + W + 'x' + H;
    if (_cache && _cacheKey === key) return _cache;
    var lat = null;
    try {
      if (root.AK_PATHWALK && root.AK_PATHWALK.latticeFor) lat = root.AK_PATHWALK.latticeFor(z.id, W, H);
    } catch (_e) { lat = null; }
    _cache = deriveAll(z, W, H, lat, ctx.ZONES || root.ZONES);
    _cacheKey = key;
    _diag.mouths = _cache.length; _diag.zone = z.id || '';
    return _cache;
  }

  /* ---------------------------------------------------------------------
   * THE CROSSING DECISION. Called from index.html's edge test (see Wire note).
   * Returns TRUE  = handled, host must do nothing.
   *         FALSE = not mine, host runs its original hard cut byte-for-byte.
   * ------------------------------------------------------------------- */
  function crossGate(dir, ez, tz, me, enterZone, showBarrier) {
    if (!ENABLED || !ez || !me) return false;
    if (_walk) return true;                                  // passage already running, swallow repeats
    var ctx = root.AK_CTX;
    var list = mouths(ctx);
    var m = null;
    for (var i = 0; i < list.length; i++) if (list[i].dir === dir) { m = list[i]; break; }
    if (!m) return false;                                    // no mouth derived -> host behaviour

    if (m.locked || (tz && tz.locked)) {                     // SEALED: the arch is there, the way is not
      _diag.sealed++;
      try { if (showBarrier && tz) showBarrier(tz); } catch (_e) {}
      return true;                                           // never crosses, never mercies
    }

    var delta = alongOf(dir, m, me);
    if (Math.abs(delta) <= HALF_W) {                         // in the mouth -> walk through it
      _pressT = 0; _pressDir = '';
      beginWalk(dir, ez, enterZone);
      return true;
    }

    // Pressed against a solid stretch of wall. Accumulate only while the contact is CONTINUOUS --
    // a gap between calls means they let go and walked off, so the clock restarts.
    if (_pressDir !== dir || (_now - _pressAt) > 0.4) _pressT = 0;
    _pressDir = dir; _pressAt = _now;
    _pressT += 0.016;                                        // per-frame contact; MERCY_S is ~160 frames
    if (_pressT >= MERCY_S) {                                // NEVER TRAP: give the host back control
      _diag.mercy++; _pressT = 0; _pressDir = '';
      return false;
    }
    _diag.blocked++;
    hintToward(ctx, m, delta);
    return true;
  }

  function beginWalk(dir, ez, enterZone) {
    _walk = { dir: dir, ez: ez, cb: enterZone, t: 0 };
    _diag.crossed++;
    try {
      var ctx = root.AK_CTX;
      if (ctx && ctx.showBanner) {
        var list = mouths(ctx), nm = '';
        for (var i = 0; i < list.length; i++) if (list[i].dir === dir) nm = list[i].name;
        ctx.showBanner(nm ? ('Through to ' + nm + '...') : 'Through the tunnel...', 1.0);
      }
    } catch (_e) {}
  }

  function hintToward(ctx, m, delta) {
    if (!ctx || !ctx.showBanner) return;
    var k = m.key + ':hint';
    if ((_now - (_bannerAt[k] || -1e9)) < 2.2) return;
    _bannerAt[k] = _now;
    ctx.showBanner('Wall runs on -- the way to ' + m.name + ' is ' +
                   alongWord(m.dir, delta) + ' along it', 1.3);
  }

  /* ---------------------------------------------------------------------
   * TELEGRAPH: name the destination while the gate is still on the horizon.
   * ------------------------------------------------------------------- */
  function telegraph(ctx, me) {
    var list = mouths(ctx);
    var W = (ctx.world && ctx.world.WORLD_W) || 1700, H = (ctx.world && ctx.world.WORLD_H) || 1300;
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      var p = point(m.dir, m.cx, m.cy, 0, 0, W, H);
      var d = Math.hypot(me.x - p.x, me.y - p.y);
      if (d > TELEGRAPH) continue;
      if ((_now - (_bannerAt[m.key] || -1e9)) < BANNER_CD) continue;
      _bannerAt[m.key] = _now;
      if (ctx.showBanner) {
        ctx.showBanner(m.locked
          ? (m.barrierLabel + ' -- ' + m.name + ' sealed')
          : (m.name + '  ·  ahead through the tunnel'), 1.6);
      }
      return;
    }
  }

  /* ---------------------------------------------------------------------
   * PROJECTION. ctx.world.project(x,y,h) -> {sx,sy,scale,vis} under the 3D camera
   * (world3d.js:331), null when 3D is off. The wx/wy fallback keeps the arch on screen in the flat
   * hub; height there is an honest approximation (screen-y lift), not a second projection.
   * ------------------------------------------------------------------- */
  function proj(ctx, x, y, h) {
    try {
      if (ctx.world.project) {
        var p = ctx.world.project(x, y, h || 0);
        if (p && p.depth > 1) return { x: p.sx, y: p.sy, s: p.scale, ok: true };
        if (p) return { x: p.sx, y: p.sy, s: 0, ok: false };
      }
    } catch (_e) {}
    var sx = ctx.world.wx(x, y), sy = ctx.world.wy(y, x);
    return { x: sx, y: sy - (h || 0), s: 1, ok: true };
  }
  function polyFrom(g, pts) {
    g.beginPath();
    g.moveTo(pts[0].x, pts[0].y);
    for (var i = 1; i < pts.length; i++) g.lineTo(pts[i].x, pts[i].y);
    g.closePath();
  }

  /* ---------------------------------------------------------------------
   * DRAW. Back-to-front: throat (deepest, outside the world box) -> ground light -> pylons ->
   * lintel -> nameplate. Painted in AK_SYSTEMS.drawAll (index.html:3533), i.e. on the 2D overlay
   * ABOVE the building pass -- correct here because nothing in the district stands between the
   * player and the boundary wall.
   * ------------------------------------------------------------------- */
  function drawMouth(ctx, g, m, me) {
    var W = (ctx.world && ctx.world.WORLD_W) || 1700, H = (ctx.world && ctx.world.WORLD_H) || 1300;
    var P = function (t, d, h) { var w = point(m.dir, m.cx, m.cy, t, d, W, H); return proj(ctx, w.x, w.y, h); };

    // Cheap cull: mouth centre well off screen -> skip the whole thing.
    var c0 = P(0, 0, 0);
    var VW = (ctx.world && ctx.world.W) || 900, VH = (ctx.world && ctx.world.H) || 600;
    if (c0.x < -700 || c0.x > VW + 700 || c0.y < -700 || c0.y > VH + 700) return false;

    var sealed = m.locked;
    var warm = sealed ? '190,64,48' : '232,197,90';          // sealed = hazard red, open = AK gold
    var hw = HALF_W;

    // ---- THROAT: 4 receding rings, narrowing 6% each, darkening inward. Reads as depth without a
    // single texture. The far ring is the light (or the brick, when sealed).
    var rings = 4, prevT = hw, prevD = 0;
    for (var r = 1; r <= rings; r++) {
      var f = r / rings;
      var nt = hw * (1 - 0.06 * r);
      var nd = -THROAT * f;
      g.fillStyle = 'rgba(' + (sealed ? '18,8,8' : '10,9,16') + ',' + (0.36 + 0.16 * r) + ')';
      polyFrom(g, [P(-prevT, prevD, 0), P(prevT, prevD, 0), P(nt, nd, 0), P(-nt, nd, 0)]); g.fill();
      // side walls of the throat, both hands
      g.fillStyle = 'rgba(' + (sealed ? '26,10,10' : '16,14,24') + ',' + (0.42 + 0.12 * r) + ')';
      polyFrom(g, [P(-prevT, prevD, 0), P(-nt, nd, 0), P(-nt, nd, ARCH_H * 0.92), P(-prevT, prevD, ARCH_H)]); g.fill();
      polyFrom(g, [P(prevT, prevD, 0), P(nt, nd, 0), P(nt, nd, ARCH_H * 0.92), P(prevT, prevD, ARCH_H)]); g.fill();
      prevT = nt; prevD = nd;
    }
    // Far end: an open tunnel GLOWS (somewhere to go); a sealed one is bricked and struck through.
    var farA = P(-prevT, prevD, 0), farB = P(prevT, prevD, 0);
    var farTA = P(-prevT, prevD, ARCH_H * 0.9), farTB = P(prevT, prevD, ARCH_H * 0.9);
    polyFrom(g, [farA, farB, farTB, farTA]);
    if (sealed) {
      g.fillStyle = 'rgba(28,16,16,.96)'; g.fill();
      g.strokeStyle = 'rgba(' + warm + ',.85)'; g.lineWidth = 5;
      g.beginPath(); g.moveTo(farA.x, farA.y); g.lineTo(farTB.x, farTB.y);
      g.moveTo(farB.x, farB.y); g.lineTo(farTA.x, farTA.y); g.stroke();   // boarded-up X
    } else {
      var lg = g.createLinearGradient(farA.x, farTA.y, farA.x, farA.y);
      lg.addColorStop(0, 'rgba(' + warm + ',.30)');
      lg.addColorStop(1, 'rgba(' + warm + ',.06)');
      g.fillStyle = lg; g.fill();
    }

    // ---- GROUND LIGHT spilling out of the mouth toward the player. This is the part that makes it
    // navigable from a distance: a lit pool on the road says "here" long before the arch resolves.
    if (!sealed) {
      var spill = [P(-hw * 0.92, 0, 0), P(hw * 0.92, 0, 0), P(hw * 1.15, PYLON_D + 96, 0), P(-hw * 1.15, PYLON_D + 96, 0)];
      var pg = g.createLinearGradient(spill[0].x, spill[0].y, spill[3].x, spill[3].y);
      pg.addColorStop(0, 'rgba(' + warm + ',.20)');
      pg.addColorStop(1, 'rgba(' + warm + ',0)');
      g.fillStyle = pg; polyFrom(g, spill); g.fill();
      // two chevrons on the road pointing IN -- direction, unmistakable, no text
      g.strokeStyle = 'rgba(' + warm + ',.55)'; g.lineWidth = 4; g.lineCap = 'round';
      for (var cvi = 0; cvi < 2; cvi++) {
        var cd = PYLON_D + 34 + cvi * 46, cw = hw * 0.42;
        var a = P(-cw, cd + 26, 0), b = P(0, cd, 0), cpt = P(cw, cd + 26, 0);
        g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.lineTo(cpt.x, cpt.y); g.stroke();
      }
      g.lineCap = 'butt';
    }

    // ---- PYLONS: two slabs framing the opening. Front face + return + inner face so they read
    // solid from any yaw (AK-SOLID's lesson from the single-sided GLBs: a flat card betrays itself
    // the moment the camera swings behind it).
    var side = [-1, 1];
    for (var si = 0; si < 2; si++) {
      var s = side[si];
      var o1 = s * hw, o2 = s * (hw + PYLON_W);
      g.fillStyle = 'rgba(22,21,31,.97)';                    // front face, into the district
      polyFrom(g, [P(o1, PYLON_D, 0), P(o2, PYLON_D, 0), P(o2, PYLON_D, ARCH_H), P(o1, PYLON_D, ARCH_H)]); g.fill();
      g.fillStyle = 'rgba(12,11,18,.97)';                    // return face into the wall
      polyFrom(g, [P(o2, PYLON_D, 0), P(o2, 0, 0), P(o2, 0, ARCH_H), P(o2, PYLON_D, ARCH_H)]); g.fill();
      g.fillStyle = 'rgba(' + warm + ',' + (sealed ? '.10' : '.16') + ')';   // inner face, lit by the throat
      polyFrom(g, [P(o1, PYLON_D, 0), P(o1, 0, 0), P(o1, 0, ARCH_H), P(o1, PYLON_D, ARCH_H)]); g.fill();
      var ea = P(o1, PYLON_D, 0), eb = P(o1, PYLON_D, ARCH_H);              // lit inner corner
      g.strokeStyle = 'rgba(' + warm + ',.75)'; g.lineWidth = 2.5;
      g.beginPath(); g.moveTo(ea.x, ea.y); g.lineTo(eb.x, eb.y); g.stroke();
      var lp = P(o1 - s * 12, PYLON_D + 4, ARCH_H - 30);                     // lamp on the shoulder
      g.fillStyle = 'rgba(' + warm + ',' + (sealed ? '.35' : '.9') + ')';
      g.beginPath(); g.arc(lp.x, lp.y, Math.max(2.2, 5 * (lp.s || 1) * 0.55), 0, 6.2832); g.fill();
    }

    // ---- LINTEL across the top + the nameplate that telegraphs the destination.
    var lin = [P(-(hw + PYLON_W), PYLON_D, ARCH_H), P(hw + PYLON_W, PYLON_D, ARCH_H),
               P(hw + PYLON_W, PYLON_D, ARCH_H + LINTEL_H), P(-(hw + PYLON_W), PYLON_D, ARCH_H + LINTEL_H)];
    g.fillStyle = 'rgba(26,25,36,.97)'; polyFrom(g, lin); g.fill();
    g.strokeStyle = 'rgba(' + warm + ',.7)'; g.lineWidth = 2; polyFrom(g, lin); g.stroke();

    var lab = P(0, PYLON_D, ARCH_H + LINTEL_H * 0.55);
    var mp = point(m.dir, m.cx, m.cy, 0, 0, W, H);
    var dist = Math.hypot(me.x - mp.x, me.y - mp.y);
    // Nameplate strengthens as you close on it: readable at range, bold at the threshold.
    var fade = Math.max(0.25, Math.min(1, 1 - (dist - TELEGRAPH) / 520));
    var fs = Math.max(11, Math.min(22, 15 * (lab.s || 1) * 1.15));
    g.save();
    g.globalAlpha = fade;
    g.font = '900 ' + fs.toFixed(1) + 'px system-ui,-apple-system,Segoe UI,Roboto,sans-serif';
    g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillStyle = 'rgba(8,8,12,.9)'; g.fillText(m.name, lab.x + 1, lab.y + 1);
    g.fillStyle = 'rgba(' + warm + ',.98)'; g.fillText(m.name, lab.x, lab.y);
    if (sealed) {
      g.font = '800 ' + (fs * 0.66).toFixed(1) + 'px system-ui,-apple-system,Segoe UI,Roboto,sans-serif';
      g.fillStyle = 'rgba(240,180,170,.92)';
      g.fillText(m.barrierLabel, lab.x, lab.y + fs * 1.15);
    }
    g.restore();
    return true;
  }

  /* Passage veil: the screen darkens FROM the mouth as you walk under the arch, and the far side
   * opens back up. enterZone (index.html:1519) already owns a 460ms gold fade; this 550ms veil sits
   * in front of it so the sequence is walk-in -> dark -> host fade -> emerge, instead of a cut. */
  function drawVeil(ctx, g) {
    var VW = (ctx.world && ctx.world.W) || 900, VH = (ctx.world && ctx.world.H) || 600;
    var k;
    if (_walk) k = Math.min(1, _walk.t / WALK_S);
    else if (_arrive > 0) k = Math.max(0, _arrive / ARRIVE_S);
    else return;
    var rg = g.createRadialGradient(VW / 2, VH * 0.52, Math.max(1, VH * 0.10 * (1 - k)),
                                    VW / 2, VH * 0.52, Math.max(2, VH * (0.95 - 0.45 * k)));
    rg.addColorStop(0, 'rgba(6,5,10,' + (k * 0.72).toFixed(3) + ')');
    rg.addColorStop(1, 'rgba(3,3,6,' + (k * 0.97).toFixed(3) + ')');
    g.fillStyle = rg; g.fillRect(0, 0, VW, VH);
  }

  /* ------------------------------------------------------------------- */
  var api = {
    id: 'aktunnel',

    onTick: function (dt, ctx) {
      try {
        if (!ENABLED || !ctx || !ctx.me) return;
        dt = dt || 0.016;
        _now += dt;
        _tickAt = _now;                       // IN_ZONE proof for the draw pass (header)

        var zid = (ctx.activeZone && ctx.activeZone.id) || '';
        if (zid !== _lastZone) {              // stepped into a new district
          if (_lastZone) _arrive = ARRIVE_S;  // emerge from the far throat (not on first boot)
          // CANCEL any passage in flight. The district changed by a route that is not ours --
          // worldmap fast-travel, a story teleport, a raid return, or (measured in the headless
          // browser run before this file was wired) the host's own edge cut firing in parallel.
          // A dangling _walk would sit through the whole next district and then yank the player
          // through a gate they never walked into, because its callback still holds the OLD edge.
          // Ticks are suspended while state==='TRANSITIONING' (index.html:2608), so a stale passage
          // can survive an arbitrarily long gap; this is the only place that can clear it.
          _walk = null;
          _lastZone = zid; _cache = null; _cacheKey = '';
          _pressT = 0; _pressDir = '';
        }
        if (_arrive > 0) _arrive = Math.max(0, _arrive - dt);

        if (_walk) {
          _walk.t += dt;
          if (_walk.t >= WALK_S) {
            var w = _walk; _walk = null;
            try { if (w.cb) w.cb(w.ez.to, w.ez.spawn); } catch (_e) {}
          }
          return;                             // no telegraphs mid-passage
        }
        telegraph(ctx, ctx.me);
      } catch (_e) {}
    },

    onDrawWorld: function (ctx) {
      try {
        if (!ENABLED || !ctx || !ctx.world || !ctx.me) return;
        // Stale tick == the host is in RAID / an interior / a story surface (index.html:2608 gates
        // the tick, index.html:2824 does NOT gate the draw). Do not paint district furniture there.
        if ((_now - _tickAt) > 0.25) return;
        var g = ctx.world.g;
        if (!g) return;
        var list = mouths(ctx), n = 0;
        g.save();
        for (var i = 0; i < list.length; i++) if (drawMouth(ctx, g, list[i], ctx.me)) n++;
        g.restore();
        drawVeil(ctx, g);
        _diag.drew = n;
      } catch (_e) { try { ctx.world.g.restore(); } catch (_e2) {} }
    }
  };
  if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api);

  /* ---------------------------------------------------------------------
   * SELF TEST -- pure math only, no canvas. Run by systems/aktunnel.test.js.
   * ------------------------------------------------------------------- */
  function selfTest() {
    var fails = [], n = 0;
    function ok(c, m) { n++; if (!c) fails.push(m); }

    var ZS = {
      A: { id: 'A', name: 'A TOWN', edges: { E: { to: 'B', spawn: { x: 150, y: 650 } } } },
      B: { id: 'B', name: 'B TOWN', edges: { W: { to: 'A', spawn: { x: 1550, y: 650 } },
                                             N: { to: 'L', spawn: { x: 850, y: 1150 } } } },
      L: { id: 'L', name: 'LOCKED', locked: true, barrierLabel: 'COLLAPSED BRIDGE', edges: {} }
    };
    var mA = deriveMouth(ZS.A, 'E', 1700, 1300, null, ZS);
    var mB = deriveMouth(ZS.B, 'W', 1700, 1300, null, ZS);
    ok(!!mA && !!mB, 'both sides of a crossing derive a mouth');
    ok(mA.cy === mB.cy, 'MIRROR RULE: both districts place the crossing on the same centre-line');
    ok(mA.name === 'B TOWN', 'mouth carries the destination district NAME for the telegraph');
    ok(mA.locked === false, 'open border is not sealed');
    // {cx,cy} is a genuine world point, not one live number beside one leftover spawn component.
    ok(mA.cx === 1700 && mB.cx === 0, 'E mouth sits ON the east wall, W mouth ON the west wall');

    var mL = deriveMouth(ZS.B, 'N', 1700, 1300, null, ZS);
    ok(mL.locked === true, 'locked target -> sealed mouth');
    ok(mL.barrierLabel === 'COLLAPSED BRIDGE', 'sealed mouth carries the barrier reason');
    ok(mL.cy === 0, 'N mouth sits ON the north wall');

    // Snap onto a street corridor within SNAP, ignore one outside it.
    var snapped = deriveMouth(ZS.A, 'E', 1700, 1300, { hy: [{ c: 700 }], vx: [] }, ZS);
    ok(snapped.cy === 700 && snapped.snapped, 'mouth snaps onto a corridor 50px away');
    var far = deriveMouth(ZS.A, 'E', 1700, 1300, { hy: [{ c: 1100 }], vx: [] }, ZS);
    ok(far.cy === 650 && !far.snapped, 'corridor 450px away is ignored (> SNAP)');

    // Frame math: inward normal points INTO the district on all four walls.
    var pW = point('W', 850, 650, 0, 40, 1700, 1300);
    var pE = point('E', 850, 650, 0, 40, 1700, 1300);
    var pN = point('N', 850, 650, 0, 40, 1700, 1300);
    var pS = point('S', 850, 650, 0, 40, 1700, 1300);
    ok(pW.x === 40 && pW.y === 650, 'W wall: inward is +x');
    ok(pE.x === 1660 && pE.y === 650, 'E wall: inward is -x');
    ok(pN.y === 40 && pN.x === 850, 'N wall: inward is +y');
    ok(pS.y === 1260 && pS.x === 850, 'S wall: inward is -y');
    ok(point('W', 850, 650, 0, -THROAT, 1700, 1300).x === -THROAT, 'throat recedes past the boundary');

    // Tangent axis: E/W measured on y, N/S on x -- the "left stays left" invariant.
    ok(alongOf('E', { cx: 850, cy: 650 }, { x: 1690, y: 720 }) === 70, 'E/W along-wall offset reads y');
    ok(alongOf('N', { cx: 850, cy: 650 }, { x: 780, y: 10 }) === -70, 'N/S along-wall offset reads x');

    // Mouth width: in-mouth vs solid wall.
    ok(Math.abs(alongOf('E', mA, { x: 1690, y: mA.cy + 100 })) <= HALF_W, 'y+100 is inside the mouth');
    ok(Math.abs(alongOf('E', mA, { x: 1690, y: mA.cy + 420 })) > HALF_W, 'y+420 is solid wall');

    // Hint direction: a player SOUTH of the gate (delta > 0, +y is down) is told to walk north.
    ok(alongWord('E', 300) === 'north' && alongWord('E', -300) === 'south', 'E/W hint words');
    ok(alongWord('N', 300) === 'west' && alongWord('N', -300) === 'east', 'N/S hint words');

    return { pass: n - fails.length, total: n, fails: fails };
  }

  return {
    // pure/testable
    deriveMouth: deriveMouth, deriveAll: deriveAll, point: point, alongOf: alongOf,
    selfTest: selfTest,
    // host seam
    crossGate: crossGate,
    mouths: function () { return mouths(root.AK_CTX); },
    isWalking: function () { return !!_walk; },
    setEnabled: function (b) { ENABLED = !!b; if (!ENABLED) { _walk = null; } return ENABLED; },
    isEnabled: function () { return ENABLED; },
    invalidate: function () { _cache = null; _cacheKey = ''; return true; },
    diag: function () {
      return { zone: _diag.zone, mouths: _diag.mouths, drew: _diag.drew, crossed: _diag.crossed,
               blocked: _diag.blocked, mercy: _diag.mercy, sealed: _diag.sealed,
               walking: !!_walk, enabled: ENABLED,
               consts: { HALF_W: HALF_W, ARCH_H: ARCH_H, THROAT: THROAT, MERCY_S: MERCY_S, WALK_S: WALK_S } };
    }
  };
})(window);
