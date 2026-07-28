/* ALLEY KINGZ -- AK_BLDMODELS: real GLB meshes REPLACING the facade boxes.  AK-BLDMODELS 2026-07-20.
 *
 * WHAT THIS IS
 * Buildings in the hub have been BoxGeometry with a painted facade on the +z face. Operator generated
 * real 3D models (Higgsfield -> Tripo) and asked for the box to be replaced ENTIRELY, not dressed:
 *   "replace the town hall entirely."
 * This module owns that swap. A building with a registered model loses its box and its bldmass
 * detail; a building without one keeps both, untouched. Mixed districts are the normal case.
 *
 * WHY REPLACING THE VISUAL IS SAFE
 * Collision does NOT live on the 3D mesh. The hub derives obstacles from the ZONE RECORD
 * (b.x, b.y, b.w, b.h at index.html:840-880) and the 2D layer never reads scene geometry. So the
 * box is PURELY VISUAL and swapping it cannot wall the player in or move a door. Verified before
 * writing this: no AK_COLLISION path reads W3.blds.
 *
 * THE UNITS TRAP -- THE MOST IMPORTANT THING IN THIS FILE
 * Tripo/Higgsfield export normalised, roughly unit-sized, Y-up. This world is PIXEL-scaled: the
 * world is 1700x1300, buildings are ~90-205 tall, the hero is 60. A GLB dropped in raw lands about
 * 1 unit tall and is INVISIBLE -- exactly the bug that made bcardd.glb render 0.3 pixels and cost
 * hours. So every model is normalised by its own bounding box to a target height derived from the
 * building's own record, and its feet are seated on y=0. Never trust the authored scale.
 *
 * MEMORY -- READ BEFORE ADDING MODELS
 * These are raw Tripo exports: 10-17 MB EACH, ~68 MB for five. The entire pre-existing build is
 * ~4.5 MB. Loading a district's worth over mobile data is heavy, so models load LAZILY -- only the
 * buildings in the district you are standing in, one at a time, and the cache is keyed by url so a
 * re-entered district costs nothing. Draco/meshopt compression plus 1K textures typically takes a
 * 16 MB export to 1-3 MB with no visible difference at this camera distance; that is the real fix
 * and it is not done yet. Until then keep the registry small on purpose.
 */
window.AK_BLDMODELS = (function (root) {
  'use strict';

  /* ---------------------------------------------------------------------
   * REGISTRY -- building id -> model. Keys are ZONE BUILDING IDS (the first
   * argument of B() in index.html), not display labels. 'ARENA' is the id of
   * the building LABELLED "TOWN HALL"; that mismatch is pre-existing canon.
   * ------------------------------------------------------------------- */
  var MODELS = {
    ARENA:     { url: 'assets/models/bld_townhall.glb',   scale: 1.00, yaw: 0 },
    SILO:      { url: 'assets/models/bld_silo.glb',       scale: 1.00, yaw: 0 },
    WARD:      { url: 'assets/models/bld_wardrobe.glb',   scale: 1.00, yaw: 0 },
    BLOCK:     { url: 'assets/models/bld_block_comic.glb', scale: 1.00, yaw: 0 },
    INFIRMARY: { url: 'assets/models/bld_infirmary.glb',  scale: 1.00, yaw: 0 },
    DROP:      { url: 'assets/models/bld_drop.glb',       scale: 1.00, yaw: 0 }
  };

  // A building's target height in world units. The zone record's `h` is a FOOTPRINT depth (96-124),
  // and buildBuildings already derives visual height as max(90, h*1.65). Matching that keeps a
  // modelled building the same size as its boxed neighbours instead of towering over them.
  function targetHeight(b) {
    var h = (b && b.h) || 96;
    return Math.max(90, h * 1.65);
  }

  function modelFor(id) { return (id && MODELS[id]) || null; }
  function has(id) { return !!modelFor(id); }

  /* ---------------------------------------------------------------------
   * LOAD + NORMALISE
   * ------------------------------------------------------------------- */
  var _fp = {};           // building id -> {halfW, halfD, height} measured AFTER scaling
  var _cache = {};        // url -> loaded root object (cloned per use)
  var _inflight = {};     // url -> [callbacks]

  function loadGLB(url, cb) {
    if (_cache[url]) { cb(_cache[url]); return; }
    if (_inflight[url]) { _inflight[url].push(cb); return; }
    _inflight[url] = [cb];
    var T = root.AK_THREE;
    if (!T || typeof T.loadGLB !== 'function') { flush(url, null); return; }
    try {
      T.loadGLB(url, function (glb) {
        var o = glb && (glb.scene || glb);
        _cache[url] = o || null;
        flush(url, o || null);
      }, function () { flush(url, null); });
    } catch (_e) { flush(url, null); }
  }
  function flush(url, obj) {
    var list = _inflight[url] || []; delete _inflight[url];
    for (var i = 0; i < list.length; i++) { try { list[i](obj); } catch (_e) {} }
  }

  /* AK-SOLID 2026-07-20: force back faces on. AUDITED, not assumed -- of nine models, the two
   * ~100k-triangle exports (bld_townhall 98,689 tris and bld_infirmary 103,002) carry
   * doubleSided:false, while every 4-5k export carries true. Different Tripo export settings, and
   * the operator could see straight THROUGH the Town Hall from behind: with backface culling on,
   * a wall viewed from its inside face is simply not drawn.
   *
   * Cost note, because the usual advice gets this wrong: DoubleSide does NOT double draw calls.
   * The draw call count is identical -- it disables backface culling, so roughly twice the
   * fragments can be shaded on a closed mesh. On a handful of buildings that is negligible, and
   * it is far cheaper than re-exporting or extruding geometry that is already solid.
   *
   * Applied per-instance on the CLONE, never on the cached source, so we never mutate a shared
   * material that another district is still using. */
  function solidify(THREE, obj, id) {
    var n = 0;
    try {
      obj.traverse(function (o) {
        if (!o.isMesh || !o.material) return;
        var mats = Array.isArray(o.material) ? o.material : [o.material];
        for (var i = 0; i < mats.length; i++) {
          var m = mats[i]; if (!m || m.side === THREE.DoubleSide) continue;
          // clone before mutating -- clone(true) shares materials with the cached source
          var c = m.clone(); c.side = THREE.DoubleSide; c.needsUpdate = true;
          if (Array.isArray(o.material)) o.material[i] = c; else o.material = c;
          n++;
        }
      });
    } catch (_e) {}
    return n;
  }

  // Normalise by the model's OWN bbox, then seat feet on y=0. See the units trap above.
  function fit(THREE, obj, b, spec) {
    try {
      var box = new THREE.Box3().setFromObject(obj);
      var size = box.getSize(new THREE.Vector3());
      var tall = Math.max(size.y || 0, 1e-6);
      var s = (targetHeight(b) / tall) * ((spec && spec.scale) || 1);
      if (!isFinite(s) || s <= 0) return false;
      obj.scale.setScalar(s);
      // Re-measure AFTER scaling -- box.min.y is in the pre-scale space.
      var box2 = new THREE.Box3().setFromObject(obj);
      obj.position.y = -box2.min.y;
      if (spec && spec.yaw) obj.rotation.y = spec.yaw * Math.PI / 180;
      /* AK-FOOTPRINT 2026-07-20: publish the REAL post-scale footprint. akdoors was placing door
       * frames at b.y + b.h*0.36 -- the front wall of the BoxGeometry world3d builds at depth
       * b.h*0.72. For a modelled building that box is set invisible (AK-BLDMODELS), and the GLB's
       * own depth is whatever Tripo produced, so the frame landed on geometry that is not drawn.
       * We already measure this box to seat the feet; throwing it away and re-deriving depth from
       * a formula that describes a DIFFERENT mesh is what broke the doors on the four best
       * buildings. Half-extents in world units, hero-relative like everything else. */
      var sz2 = box2.getSize(new THREE.Vector3());
      _fp[b.id] = { halfW: sz2.x / 2, halfD: sz2.z / 2, height: sz2.y };
      return true;
    } catch (_e) { return false; }
  }

  /* ---------------------------------------------------------------------
   * PUBLIC: attach(THREE, scene, b, onDone)
   * Loads this building's model, fits it, parents it to a world-positioned
   * Group, adds it to the scene. onDone(groupOrNull) so the caller can track
   * it for disposal. Returns the Group SYNCHRONOUSLY (empty until the GLB
   * lands) so the caller can hide its box immediately and never show both.
   * ------------------------------------------------------------------- */
  function attach(THREE, scene, b, onDone) {
    var spec = modelFor(b && b.id);
    if (!THREE || !scene || !spec) { if (onDone) onDone(null); return null; }
    var g = new THREE.Group();
    g.position.set(b.x, 0, b.y);
    g.userData.akModelFor = b.id;
    scene.add(g);
    loadGLB(spec.url, function (src) {
      if (!src) {
        // Model failed. The caller already hid the box, so un-hide it rather than
        // leaving a hole where a building should be. Loud, not silent -- a swallowed
        // failure here reads as "the building vanished".
        g.userData.akFailed = true;
        try { console.warn('[AK_BLDMODELS] model failed, restoring box:', b.id, spec.url); } catch (_e) {}
        if (onDone) onDone(null);
        return;
      }
      var inst;
      try { inst = src.clone(true); } catch (_e) { inst = src; }
      solidify(THREE, inst, b.id);
      fit(THREE, inst, b, spec);
      try { g.add(inst); } catch (_e2) {}
      if (onDone) onDone(g);
    });
    return g;
  }

  function dispose(THREE, scene, g) {
    if (!scene || !g) return;
    try {
      scene.remove(g);
      g.traverse(function (o) {
        if (o.geometry && o.geometry.dispose) o.geometry.dispose();
        // Materials/textures are shared with the cached source; disposing them would
        // corrupt the next district that reuses this model. Geometry clones are ours.
      });
    } catch (_e) {}
  }

  return {
    MODELS: MODELS, has: has, modelFor: modelFor,
    targetHeight: targetHeight, attach: attach, dispose: dispose, solidify: solidify,
    /* footprint(id) -> {halfW, halfD, height} in world units, or null if this building has no model
     * or its GLB has not landed yet. Callers MUST handle null: models load lazily and async, so the
     * first frames after entering a district legitimately have no footprint. */
    footprint: function (id) { return (id && _fp[id]) || null; },
    _fit: fit,
    register: function (id, spec) { if (id && spec && spec.url) { MODELS[id] = spec; return true; } return false; }
  };
})(window);
