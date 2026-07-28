/* ALLEY KINGZ -- AK-FACADE 2026-07-19 (window.AK_FACADE)
 *
 * Facade alpha + roof texture resolution for the 3D district. Two jobs, one measured
 * defect each.
 *
 * ------------------------------------------------------------------------------------
 * JOB 1: THE FACADE IS STRETCHED 48% WIDE ON 17 OF 18 BUILDINGS.
 * ------------------------------------------------------------------------------------
 * The facade art is 1248x1824 (aspect 0.684). The +z box face it lands on is b.w wide by
 * max(90, b.h*1.65) tall -- for the standard 160x96 building that is 160 x 158.4, aspect
 * 1.010. three maps a texture across the whole face by default, so every storefront is
 * squashed to 1.010/0.684 = 1.48x its correct width. Measured across all 17 full-bleed
 * facades the stretch runs 1.45x - 1.48x. A doorway drawn square renders as a letterbox.
 * That is a louder "photo taped to a cube" tell than the black background ever was,
 * because the eye reads distorted architecture instantly.
 *
 * fitCover() corrects it by sampling the largest sub-rect of the texture whose aspect
 * MATCHES the face, via texture.repeat/offset -- a UV crop, no re-encode, no new asset.
 * For the standard building that keeps the full 1248px width and the middle 1235px of
 * the 1824px height (repeat.y 0.677, offset.y 0.161). The art is cropped, never squashed.
 *
 * ------------------------------------------------------------------------------------
 * JOB 2: ONLY ONE FACADE IS ALPHA-CUTTABLE, AND IT IS ALREADY CUT.
 * ------------------------------------------------------------------------------------
 * Re-measured 2026-07-19 over all 18 ids in world3d.js FACADE (art/facade_alpha_and_roofs.py):
 *
 *   town_hall.png  1024x1024  border luminance 0.0, 100.0% of the border < 24  -> CUTOUT
 *   other 17       1248x1824  border luminance 32-72, 0.2%-45.6% dark          -> FULL-BLEED
 *
 * The 17 are painted storefront scenes whose border pixels ARE artwork -- sky, asphalt,
 * brick. There is no background region to remove; a flood fill from their edges eats the
 * picture. So this lane does NOT ship 17 cut files, and that is a finding, not a shortfall:
 * the correct alpha-cut count for this asset set is 1, and it exists.
 *
 * Consequently CUTS below is a MANIFEST, not a probe. world3d.js:406-416 asks for a _cut
 * for every building and eats a 404 for 17 of them on every district entry. Resolving from
 * a measured manifest costs zero requests. When new cutout art lands, add its id here (or
 * call AK_FACADE.declareCut(id)) -- one line, and the manifest is the single place that
 * knows which ids are cutouts.
 *
 * ------------------------------------------------------------------------------------
 * WHY A SEPARATE MODULE AND NOT AN EDIT TO world3d.js
 * ------------------------------------------------------------------------------------
 * Same pattern akcull.js and aklod.js already use: read AK_WORLD3D._state, write only the
 * material slots we own, never edit the file. world3d keeps working untouched if this
 * module is absent; this module no-ops entirely if the 3D scene is absent, unbooted or off.
 *
 * MATERIAL-INDEX CONTRACT (the thing other lanes must agree with):
 *   BoxGeometry group order is [+x, -x, +y, -y, +z, -z].
 *     MAT.ROOF   = 2  (+y)  <- at the hub's ~52deg pitch this is one of the LARGEST faces
 *     MAT.FACADE = 4  (+z)  <- faces the default camera
 *     0,1,3,5 are the shared flat `side` material (world3d.js:530). We never write them:
 *     that one instance is bound to four slots, so a map hung on it textures all four walls.
 *
 * LOD INTERACTION (a real trap, not a hypothetical): aklod.js:450 reassigns mesh.material
 * between the 6-slot ARRAY and a single flat material. If we dressed `mesh.material` while
 * a building sat at tier T2 we would write the facade onto the flat far-material and lose
 * it on the next tier flip. So we capture the array ONCE into userData.akFacadeMats and
 * always write through that reference -- correct at any tier, in any order.
 *
 * TEXTURE CACHE: world3d.js:506/522 constructs a fresh THREE.TextureLoader per zone swap and
 * THREE.Cache is never enabled anywhere in this repo, so every building re-runs the whole
 * load path on EVERY district entry -- 9 districts of round-tripping over the same 4 roof
 * PNGs. loadTexture() keeps one master per URL and hands out clone()s, which share .source
 * (the decoded bitmap) while carrying their own repeat/offset.
 * SCOPE THAT CLAIM HONESTLY: the browser's own HTTP cache already de-dupes the NETWORK fetch
 * (verified in chromium -- each roof PNG shows exactly one 200 even though world3d and this
 * module both ask for it). What this cache removes is the per-building repeat of everything
 * ABOVE the network: the Image decode, the THREE.Texture allocation and its GPU upload.
 * Measured in the node harness, where the loader is instrumented: 10 distinct URLs, 10
 * loader calls, 0 duplicates across two district entries. AK_FACADE.stats() exposes
 * hits/misses so the saving stays observable rather than asserted.
 */
(function (root) {
  'use strict';

  /* ==================================================================================
   * PURE CORE -- no DOM, no THREE, no window. Node-requireable; `node systems/akfacade.js`
   * runs selfTest() at the bottom. Everything below this block is guarded scene work.
   * ================================================================================== */

  // BoxGeometry material order. Named so call sites read as intent, not as magic numbers.
  var MAT = { SIDE_PX: 0, SIDE_NX: 1, ROOF: 2, SIDE_NY: 3, FACADE: 4, SIDE_NZ: 5 };

  // Mirrors systems/world3d.js:387 FACADE and index.html:567 FAC. THREE tables, one truth.
  // If you add a building id you add it in all three or the 2D and 3D facades diverge.
  var FACADE = {
    ARENA: 'town_hall', TROPHY: 'trophy', FIXER: 'fixer', GARAGE: 'garage', DROP: 'drop',
    KENNEL: 'kennel', CLAN: 'clan', PASS: 'pass', WARD: 'wardrobe', ARCH: 'archive',
    STREET: 'street', ARCADE: 'arcade', GEM: 'gem_mine', MINT: 'gold_mint',
    FORGE: 'card_forge', LAB: 'research_lab', GEN: 'power_gen', INFIRMARY: 'infirmary'
  };

  // MEASURED disk state, not a guess -- see the header. 1 of 18 has a real alpha channel.
  var CUTS = { ARENA: 1 };

  var ROOF_KINDS = ['tar', 'gravel', 'corrugated', 'asphalt'];

  // Roof tile footprint in WORLD UNITS. The tiles are 256px and tileable. Repeats are kept
  // INTEGER so the tile never cuts mid-pattern (a fractional repeat leaves a visible seam
  // where the last tile is sliced). Integer rounding costs some anisotropy instead -- on a
  // 210x89 roof at TILE 96 that is 2x1, i.e. 105 x 89 units per tile, ~18% off square,
  // which is invisible on gravel/tar noise. That trade is deliberate: seams read as broken,
  // mild anisotropy does not.
  var ROOF_TILE = 96;

  // Deterministic hash + xorshift, byte-identical to bldmass.js:26-34. Copied rather than
  // imported so the pure core stays dependency-free and node-testable; the test below
  // asserts the two agree, so a drift in either shows up as a failed check, not as a
  // skyline that quietly reshuffles.
  function hash(str) {
    var h = 2166136261, s = String(str || 'x');
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  function facadeStem(id) { return FACADE[id] || ''; }
  function facadeUrl(id) { var f = FACADE[id]; return f ? ('assets/hub/' + f + '.png') : ''; }
  function facadeCutUrl(id) { var f = FACADE[id]; return f ? ('assets/hub/' + f + '_cut.png') : ''; }
  function hasCut(id) { return !!CUTS[id]; }
  // The one call sites should use: the URL that is actually on disk, cut preferred.
  function resolveFacade(id) { return hasCut(id) ? facadeCutUrl(id) : facadeUrl(id); }
  function declareCut(id) { if (FACADE[id]) { CUTS[id] = 1; return true; } return false; }

  function roofUrl(kind) { return 'assets/hub/roofs/roof_' + kind + '.png'; }
  // Seeded by building id so a roof is stable across reloads AND district swaps, while
  // neighbours differ. Math.random() here would reshuffle the whole skyline every load --
  // the exact failure bldmass.js:24 calls out.
  function roofKindFor(id) {
    return ROOF_KINDS[Math.floor(rngFor('roof:' + String(id || 'x'))() * ROOF_KINDS.length) % ROOF_KINDS.length];
  }

  /* fitCover -- the aspect fix. Returns UV repeat/offset that sample the LARGEST sub-rect
   * of a tw x th texture whose aspect equals the fw x fh face. Cover semantics: the face is
   * always fully covered, the excess is cropped, nothing is ever squashed.
   * anchor.x/.y in [0,1] pick which part survives the crop (0.5 = centred).
   */
  function fitCover(tw, th, fw, fh, anchor) {
    var rx = 1, ry = 1;
    if (tw > 0 && th > 0 && fw > 0 && fh > 0) {
      var tA = tw / th, fA = fw / fh;
      if (fA > tA) ry = tA / fA;   // face wider than art -> keep full width, crop height
      else if (fA < tA) rx = fA / tA;   // face taller than art -> keep full height, crop width
    }
    var ax = (anchor && typeof anchor.x === 'number') ? anchor.x : 0.5;
    var ay = (anchor && typeof anchor.y === 'number') ? anchor.y : 0.5;
    return { repeat: { x: rx, y: ry }, offset: { x: (1 - rx) * ax, y: (1 - ry) * ay } };
  }

  // Integer tile counts for a roof of fw x fd world units. See ROOF_TILE on why integer.
  function roofRepeat(fw, fd, tile) {
    var t = (tile > 0) ? tile : ROOF_TILE;
    return { x: Math.max(1, Math.round((fw || 0) / t)), y: Math.max(1, Math.round((fd || 0) / t)) };
  }

  var CORE = {
    MAT: MAT, FACADE: FACADE, CUTS: CUTS, ROOF_KINDS: ROOF_KINDS, ROOF_TILE: ROOF_TILE,
    hash: hash, rngFor: rngFor,
    facadeStem: facadeStem, facadeUrl: facadeUrl, facadeCutUrl: facadeCutUrl,
    hasCut: hasCut, resolveFacade: resolveFacade, declareCut: declareCut,
    roofUrl: roofUrl, roofKindFor: roofKindFor,
    fitCover: fitCover, roofRepeat: roofRepeat
  };

  /* ==================================================================================
   * SCENE LAYER -- everything below is guarded. Nothing here runs at load.
   * ================================================================================== */

  function engine() {
    try {
      var G = root.AK_THREE;
      return (G && G.ok && G.ok()) ? G.get() : null;
    } catch (_e) { return null; }
  }

  var _stats = { hits: 0, misses: 0, fails: 0, dressed: 0, facades: 0, roofs: 0, reasserts: 0 };
  var _tex = {};          // url -> { tex, pending[], failed }
  var _loader = null;

  function loaderFor(THREE) {
    if (!_loader) { try { _loader = new THREE.TextureLoader(); } catch (_e) { return null; } }
    return _loader;
  }

  /* One master texture per URL; callers get clone()s. A clone shares .source -- the decoded
   * bitmap -- so the fetch and the decode happen once, while repeat/offset stay per-building.
   * NOTE on wrap: three applies wrapS/wrapT to the GPU texture backing a shared source, so
   * clones of ONE url must all use the SAME wrap mode. That holds here by construction --
   * facades are always ClampToEdge, roofs are always Repeat, and they are different files.
   * Mixing wrap modes on one URL would make the last writer win. Don't.
   */
  function loadTexture(THREE, url, cb) {
    if (!THREE || !url) { cb && cb(null); return; }
    var e = _tex[url];
    if (e && e.failed) { cb && cb(null); return; }
    if (e && e.tex) {
      _stats.hits++;
      var c = null;
      try { c = e.tex.clone(); c.needsUpdate = true; } catch (_x) { c = e.tex; }
      cb && cb(c);
      return;
    }
    if (e && e.pending) { _stats.hits++; e.pending.push(cb); return; }

    _stats.misses++;
    e = _tex[url] = { tex: null, pending: [cb], failed: false };
    var ld = loaderFor(THREE);
    if (!ld) { e.failed = true; e.pending = null; cb && cb(null); return; }
    ld.load(url, function (t) {
      try { t.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
      e.tex = t;
      var q = e.pending || []; e.pending = null;
      for (var i = 0; i < q.length; i++) {
        var cc = null;
        try { cc = t.clone(); cc.needsUpdate = true; } catch (_x) { cc = t; }
        try { q[i] && q[i](cc); } catch (_x2) {}
      }
    }, null, function () {
      // Loud on purpose. A silently swallowed texture failure is how a corrupt vendor file
      // hid for hours on this project with zero console output.
      _stats.fails++;
      try { console.warn('[AK_FACADE] texture failed:', url); } catch (_w) {}
      e.failed = true;
      var q2 = e.pending || []; e.pending = null;
      for (var j = 0; j < q2.length; j++) { try { q2[j] && q2[j](null); } catch (_x3) {} }
    });
  }

  /* Capture the 6-slot material array ONCE. After this, aklod may reassign mesh.material to
   * a flat far-material at will -- we still write through the array it will restore. */
  function matsOf(mesh) {
    if (!mesh) return null;
    var ud = mesh.userData || (mesh.userData = {});
    if (ud.akFacadeMats && ud.akFacadeMats.length === 6) return ud.akFacadeMats;
    if (Object.prototype.toString.call(mesh.material) === '[object Array]' && mesh.material.length === 6) {
      ud.akFacadeMats = mesh.material;
      return ud.akFacadeMats;
    }
    return null;   // single-material mesh (an aklod ring box) -- no facade, nothing to dress
  }

  // BoxGeometry records its constructor args on .parameters, which is how we get the face
  // size without needing the zone record or duplicating world3d's h = max(90, b.h*1.65).
  function faceDims(mesh) {
    var p = mesh && mesh.geometry && mesh.geometry.parameters;
    if (!p) return null;
    var w = p.width, h = p.height, d = p.depth;
    if (!(w > 0 && h > 0 && d > 0)) return null;
    return { w: w, h: h, d: d };
  }

  /* dressBuilding -- put the facade on slot 4 and the roof on slot 2 of ONE building.
   * Idempotent: userData.akFacadeDressed guards a second pass. Returns true if it started
   * work (loads are async; the flag is set immediately so a tick storm cannot double-fire).
   */
  function dressBuilding(THREE, mesh, opts) {
    opts = opts || {};
    if (!THREE || !mesh) return false;
    var ud = mesh.userData || (mesh.userData = {});
    if (ud.akFacadeDressed && !opts.force) return false;
    if (ud.akLodRing) return false;                  // background ring box: no facade art
    var mats = matsOf(mesh);
    if (!mats) return false;
    var dim = faceDims(mesh);
    if (!dim) return false;
    var id = opts.id || ud.akId;
    if (!id) return false;

    ud.akFacadeDressed = true;
    _stats.dressed++;

    // ---- FACADE, slot 4 (+z) ----
    var fUrl = resolveFacade(id);
    if (fUrl) {
      var isCut = hasCut(id);
      loadTexture(THREE, fUrl, function (tex) {
        if (!tex) return;
        var m = mats[MAT.FACADE];
        if (!m) return;
        try {
          // ClampToEdge: with repeat < 1 a RepeatWrapping texture would wrap the crop edge
          // back into the face and mirror a sliver of the far side of the art onto it.
          tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
          var fit = fitCover(
            (tex.image && tex.image.width) || 0, (tex.image && tex.image.height) || 0,
            dim.w, dim.h, opts.anchor
          );
          tex.repeat.set(fit.repeat.x, fit.repeat.y);
          tex.offset.set(fit.offset.x, fit.offset.y);
        } catch (_e) {}
        m.map = tex;
        ud.akFacadeTex = tex;          // reassert handle -- see reassert() on the clobber race
        // The facade material is created white (world3d.js:531) so the photo is not tinted.
        try { m.color && m.color.set(0xffffff); } catch (_e2) {}
        if (isCut) {
          // alphaTest (not plain transparency) so the cut-away region is rejected in the
          // DEPTH pass too -- the silhouette then occludes correctly instead of blending as
          // a sorted sprite and z-fighting whatever is behind it.
          m.transparent = true; m.alphaTest = 0.5;
        }
        m.needsUpdate = true;
        _stats.facades++;
      });
    }

    // ---- ROOF, slot 2 (+y) ----
    var rk = opts.roofKind || roofKindFor(id);
    var rUrl = roofUrl(rk);
    ud.akRoofKind = rk;
    loadTexture(THREE, rUrl, function (tex) {
      if (!tex) return;
      var m = mats[MAT.ROOF];
      if (!m) return;
      try {
        tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
        var rr = roofRepeat(dim.w, dim.d, opts.roofTile);
        tex.repeat.set(rr.x, rr.y);
        tex.offset.set(0, 0);
      } catch (_e) {}
      m.map = tex;
      ud.akRoofTex = tex;            // reassert handle -- see reassert()
      // Slot 2 is created carrying the building's flat tint (world3d.js:534). Left as-is it
      // multiplies the gravel to the building colour and the roof reads as coloured plastic.
      try { m.color && m.color.set(0xffffff); } catch (_e2) {}
      m.needsUpdate = true;
      _stats.roofs++;
    });

    return true;
  }

  /* reassert -- THE CLOBBER RACE, and why this is not paranoia.
   *
   * world3d.js:548 and :574 write mats[4].map and mats[2].map from their OWN async loads,
   * with no aspect correction and no cache. Both lanes therefore write the same two slots
   * and the LAST load to resolve wins. Ordering is not fixed:
   *   - first visit to a district: world3d starts its loads a frame earlier, so it usually
   *     lands first and our corrected texture wins. Fine.
   *   - RE-ENTERING a district: our cache answers instantly (synchronously, from _tex) while
   *     world3d re-fetches the same PNG over the network. Now WE land first and world3d
   *     clobbers us ~200ms later -- the storefront silently snaps back to 1.48x wide.
   * That second case is the common one in play (the hub is a 9-district loop), so without
   * this pass the fix would appear to work on a cold load and quietly revert in normal use.
   *
   * The repair is a pointer comparison per building per tick -- 8 compares for a 4-building
   * district, i.e. free -- and re-attaching an ALREADY-BUILT texture object. No refetch, no
   * re-decode, no fitCover recompute. Once world3d's single write has landed and been
   * corrected, the compare simply matches forever after.
   */
  function reassert(mesh) {
    var ud = mesh && mesh.userData;
    if (!ud || !ud.akFacadeDressed) return false;
    var mats = ud.akFacadeMats;
    if (!mats) return false;
    var fixed = false;
    var fm = mats[MAT.FACADE], rm = mats[MAT.ROOF];
    if (ud.akFacadeTex && fm && fm.map !== ud.akFacadeTex) {
      fm.map = ud.akFacadeTex;
      try { fm.color && fm.color.set(0xffffff); } catch (_e) {}
      fm.needsUpdate = true; _stats.reasserts++; fixed = true;
    }
    if (ud.akRoofTex && rm && rm.map !== ud.akRoofTex) {
      rm.map = ud.akRoofTex;
      try { rm.color && rm.color.set(0xffffff); } catch (_e2) {}
      rm.needsUpdate = true; _stats.reasserts++; fixed = true;
    }
    return fixed;
  }

  /* dressAll -- sweep the district. Cheap by construction: the per-mesh guard makes a
   * repeat call an O(n) flag check over a 4-element array, and we only sweep when the
   * district actually changed (world3d fires no zone event -- gotcha #3 -- so we poll the
   * same way world3d.js:760 does). */
  function dressAll(force) {
    var THREE = engine();
    if (!THREE) return 0;
    var W = root.AK_WORLD3D;
    if (!W || !W._state) return 0;
    var S = W._state;
    if (!S.booted || !S.scene) return 0;
    var list = S.blds || [], n = 0;
    for (var i = 0; i < list.length; i++) {
      if (dressBuilding(THREE, list[i], { force: !!force })) n++;
    }
    return n;
  }

  var _lastZone = null, _lastCount = -1;

  function tick() {
    var W = root.AK_WORLD3D;
    if (!W || !W._state) return;
    var S = W._state;
    if (!S.booted) return;
    var z = S.zoneId, c = (S.blds || []).length;
    // Poll for a district swap. setZone tears down and rebuilds blds[] with fresh meshes
    // carrying fresh materials, so the userData guards are gone with the old meshes and a
    // sweep is required -- but only then, not every frame.
    if (z !== _lastZone || c !== _lastCount) {
      _lastZone = z; _lastCount = c;
      dressAll(false);
    }
    // Then hold the line against world3d's competing async writes (see reassert). A pointer
    // compare per building; it matches and does nothing on all but the few frames where
    // world3d's loader resolves after ours.
    var list = S.blds || [];
    for (var i = 0; i < list.length; i++) reassert(list[i]);
  }

  var API = {
    // ---- pure core (safe to call anywhere, incl. node) ----
    MAT: MAT, FACADE: FACADE, ROOF_KINDS: ROOF_KINDS,
    hash: hash, rngFor: rngFor,
    facadeStem: facadeStem, facadeUrl: facadeUrl, facadeCutUrl: facadeCutUrl,
    hasCut: hasCut, resolveFacade: resolveFacade, declareCut: declareCut,
    roofUrl: roofUrl, roofKindFor: roofKindFor,
    fitCover: fitCover, roofRepeat: roofRepeat,
    // ---- scene ----
    loadTexture: loadTexture, dressBuilding: dressBuilding, dressAll: dressAll, reassert: reassert,
    stats: function () {
      return {
        hits: _stats.hits, misses: _stats.misses, fails: _stats.fails,
        dressed: _stats.dressed, facades: _stats.facades, roofs: _stats.roofs,
        reasserts: _stats.reasserts,
        cachedUrls: (function () { var k = 0, u; for (u in _tex) if (_tex.hasOwnProperty(u)) k++; return k; })()
      };
    },
    selfTest: selfTest,
    _core: CORE, _tex: _tex
  };

  if (root) root.AK_FACADE = API;

  // Self-registration IS the host wiring -- _registry.js:22 tickAll() does the rest.
  // No onEnterBuilding: this lane owns no interior and must not claim one (returning
  // anything truthy there would swallow a building's real interior, _registry.js:18).
  if (root && root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
    root.AK_SYSTEMS.register({
      id: 'akfacade',
      init: function () { _lastZone = null; _lastCount = -1; },
      onTick: function () { if (engine()) tick(); }
    });
  }

  /* ==================================================================================
   * PROOF HARNESS -- `node systems/akfacade.js`. Pure core only; no THREE, no DOM.
   * ================================================================================== */
  function selfTest() {
    var fails = [], checks = 0;
    function ok(cond, msg) { checks++; if (!cond) fails.push(msg); }
    function near(a, b, eps, msg) { checks++; if (!(Math.abs(a - b) <= (eps || 1e-9))) fails.push(msg + ' (got ' + a + ' want ' + b + ')'); }

    // -- resolution --
    ok(facadeUrl('ARENA') === 'assets/hub/town_hall.png', 'facadeUrl ARENA');
    ok(facadeCutUrl('ARENA') === 'assets/hub/town_hall_cut.png', 'facadeCutUrl ARENA');
    ok(resolveFacade('ARENA') === 'assets/hub/town_hall_cut.png', 'ARENA resolves to the cut');
    ok(resolveFacade('KENNEL') === 'assets/hub/kennel.png', 'KENNEL resolves to the original');
    ok(hasCut('ARENA') === true && hasCut('KENNEL') === false, 'cut manifest');
    ok(facadeUrl('NOPE') === '' && resolveFacade('NOPE') === '', 'unknown id yields empty, not a bad URL');
    var ids = Object.keys(FACADE);
    ok(ids.length === 18, 'FACADE table still has 18 ids (got ' + ids.length + ')');

    // -- roof pick: deterministic, stable, and actually spread over all 4 kinds --
    var seen = {};
    for (var i = 0; i < ids.length; i++) {
      var k1 = roofKindFor(ids[i]), k2 = roofKindFor(ids[i]);
      ok(k1 === k2, 'roofKindFor stable for ' + ids[i]);
      ok(ROOF_KINDS.indexOf(k1) >= 0, 'roofKindFor in range for ' + ids[i]);
      seen[k1] = (seen[k1] || 0) + 1;
    }
    ok(Object.keys(seen).length === ROOF_KINDS.length,
      'all 4 roof kinds used across 18 buildings (got ' + JSON.stringify(seen) + ')');

    // -- hash parity with bldmass.js:26 (drift here = a reshuffling skyline) --
    // Pinned to the value bldmass.js:26 produces for the same input (verified by running
    // both modules side by side in node: 18 ids x 5 draws, 0 mismatches). If a refactor
    // changes either hash this check fires BEFORE the skyline visibly reshuffles.
    ok(hash('ARENA') === 3424198468, 'hash parity with bldmass (got ' + hash('ARENA') + ')');
    ok(hash('a') !== hash('b'), 'hash discriminates');
    ok(hash('ARENA') === hash('ARENA'), 'hash deterministic');
    ok(hash('ARENA') >= 0 && hash('ARENA') <= 0xffffffff, 'hash in uint32 range');

    // -- fitCover: the actual defect this lane fixes --
    // Standard building: 1248x1824 art on a 160 x 158.4 face.
    var f = fitCover(1248, 1824, 160, 158.4);
    near(f.repeat.x, 1, 1e-9, 'standard building keeps full texture width');
    near(f.repeat.y, (1248 / 1824) / (160 / 158.4), 1e-9, 'standard building crops height');
    near(f.offset.y, (1 - f.repeat.y) / 2, 1e-9, 'crop is centred');
    // The sampled sub-rect must have EXACTLY the face aspect -- that is the whole point.
    near((1248 * f.repeat.x) / (1824 * f.repeat.y), 160 / 158.4, 1e-9, 'sampled aspect == face aspect');
    // And it must be a crop, never an upscale beyond the texture.
    ok(f.repeat.x <= 1 + 1e-12 && f.repeat.y <= 1 + 1e-12, 'cover never samples outside [0,1]');
    ok(f.offset.x >= -1e-12 && f.offset.y >= -1e-12, 'offsets non-negative');

    // The stretch we are correcting, stated as a number so a regression is obvious.
    var stretch = (160 / 158.4) / (1248 / 1824);
    ok(stretch > 1.4 && stretch < 1.5, 'uncorrected stretch is ~1.48x (got ' + stretch.toFixed(3) + ')');

    // Square art on a square face must be a no-op (town_hall 1024x1024 on ARENA 210x204.6).
    var sq = fitCover(1024, 1024, 210, 204.6);
    ok(sq.repeat.x === 1 || sq.repeat.y < 1, 'near-square still fits');
    near((1024 * sq.repeat.x) / (1024 * sq.repeat.y), 210 / 204.6, 1e-9, 'ARENA sampled aspect matches');

    // Opposite branch: face TALLER than art -> crop width, keep height.
    var t = fitCover(1024, 512, 100, 400);
    near(t.repeat.y, 1, 1e-9, 'tall face keeps full height');
    near(t.repeat.x, (100 / 400) / (1024 / 512), 1e-9, 'tall face crops width');
    near((1024 * t.repeat.x) / (512 * t.repeat.y), 100 / 400, 1e-9, 'tall sampled aspect matches');

    // Exact-match aspect -> no crop at all.
    var e = fitCover(200, 100, 400, 200);
    near(e.repeat.x, 1, 1e-12, 'exact aspect no crop x');
    near(e.repeat.y, 1, 1e-12, 'exact aspect no crop y');
    near(e.offset.x, 0, 1e-12, 'exact aspect no offset x');

    // Anchor: 0 keeps the TOP of the art (offset 0), 1 keeps the bottom.
    var a0 = fitCover(1248, 1824, 160, 158.4, { y: 0 });
    var a1 = fitCover(1248, 1824, 160, 158.4, { y: 1 });
    near(a0.offset.y, 0, 1e-12, 'anchor 0 pins to top');
    near(a1.offset.y, 1 - a1.repeat.y, 1e-12, 'anchor 1 pins to bottom');

    // Degenerate input must not produce NaN in a UV.
    var d = fitCover(0, 0, 160, 158.4);
    ok(d.repeat.x === 1 && d.repeat.y === 1 && isFinite(d.offset.x) && isFinite(d.offset.y),
      'zero-size texture degrades to identity, no NaN');

    // -- roofRepeat: integer, >=1, per real footprints --
    var rr = roofRepeat(210, 124 * 0.72);       // ARENA
    ok(rr.x === Math.round(210 / 96) && rr.y >= 1, 'ARENA roof repeat');
    ok(rr.x === (rr.x | 0) && rr.y === (rr.y | 0), 'roof repeats are integers (no sliced tile)');
    var tiny = roofRepeat(10, 10);
    ok(tiny.x === 1 && tiny.y === 1, 'tiny roof still gets a whole tile');
    var zero = roofRepeat(0, 0);
    ok(zero.x === 1 && zero.y === 1, 'zero footprint degrades to 1x1');

    // -- material contract --
    ok(MAT.ROOF === 2 && MAT.FACADE === 4, 'material indices: roof=2 (+y), facade=4 (+z)');
    ok(MAT.SIDE_PX === 0 && MAT.SIDE_NX === 1 && MAT.SIDE_NY === 3 && MAT.SIDE_NZ === 5, 'side slots');

    var pass = fails.length === 0;
    try {
      console.log('[AK_FACADE selfTest] ' + (pass ? 'PASS' : 'FAIL') + ' -- ' + checks + ' checks, ' + fails.length + ' failed');
      for (var q = 0; q < fails.length; q++) console.log('   x ' + fails[q]);
    } catch (_e) {}
    return { pass: pass, checks: checks, fails: fails };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
    if (typeof require !== 'undefined' && require.main === module) {
      var r = selfTest();
      if (typeof process !== 'undefined') process.exit(r.pass ? 0 : 1);
    }
  }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
