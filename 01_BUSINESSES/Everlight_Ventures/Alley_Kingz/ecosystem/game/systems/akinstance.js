/* ALLEY KINGZ -- AK_INSTANCE: draw-call batching for the 3D hub.  AK-INSTANCE 2026-07-19.
 *
 * WHY THIS EXISTS
 * On a phone the wall is DRAW CALLS, not triangles. The GPU in a mid-range Android eats 100k
 * triangles without noticing and then dies at 300 draw calls, because every call is a CPU-side
 * state change: bind program, bind VAO, upload uniforms, validate, submit. The measured shape of
 * this repo makes the point better than any benchmark:
 *
 *   the whole visible world today = ~50 triangles (bldmass.js:9 measured it independently)
 *   and it already costs ~26-29 draw calls in HOME_TURF.
 *
 * Read that twice. 50 triangles, 29 calls. The triangle budget is EMPTY and the call budget is
 * already half spent, and that is with FOUR buildings and zero props. The reason is that a
 * building mesh carries a 6-material array (world3d.js:539), and three emits one call per
 * geometry GROUP when the material is an array -- so BoxGeometry's 6 groups become 6 render
 * items. Verified against the r160 source: WebGLRenderer.projectObject pushes once per group for
 * an array material and exactly once for a single material.
 *
 * So the moment the clutter lane starts scattering lamps, bins, fences and crates, the naive
 * path (one Mesh per prop) adds one call per prop MINIMUM. 400 props = 400 calls = a slideshow.
 * This module is the fix, and it is two techniques that both land on ONE draw call:
 *
 *   1. MERGE   -- N DIFFERENT static geometries -> one BufferGeometry with baked vertex colours.
 *                 Use for the INSIDE of a prop: a street lamp is a base + a post + a head + a
 *                 lens, four boxes that never move relative to each other. Merge them once and
 *                 the lamp is a single geometry instead of four.
 *   2. INSTANCE -- N COPIES of the SAME geometry -> one THREE.InstancedMesh, one call, with a
 *                 per-instance matrix and an optional per-instance colour. Use for the REPETITION:
 *                 the same lamp 200 times down a street.
 *
 * COMPOSE THEM AND THE MATH IS THE WHOLE POINT OF THIS FILE:
 *
 *   200 lamps x 4 parts, naive          = 800 draw calls
 *   200 lamps x 4 parts, merged only    = 200 draw calls   (merge kills the parts)
 *   200 lamps x 4 parts, merge+instance =   1 draw call    (instancing kills the repetition)
 *
 * Triangle count is IDENTICAL in all three. Nothing was made cheaper to rasterise. What was
 * removed is 799 CPU-side submissions per frame, and that is the number a phone feels.
 *
 * RELATION TO systems/bldmass.js
 * bldmass.js:56 mergeBoxes() already does technique 1, correctly, for building detail, and its
 * header (bldmass.js:41-53) already spells out the reasoning. This module does NOT replace it and
 * does not duplicate it -- it GENERALISES it. bldmass's merge is box-only, axis-aligned, position
 * only. AK_INSTANCE.merge() takes any BufferGeometry, applies full translate/rotate/scale through
 * a Matrix4 (so normals go through the proper inverse-transpose that geometry.applyMatrix4 does
 * for us), carries UVs when every part has them, and honours a pre-existing colour attribute.
 * bldmass's output is a legitimate INPUT here: a decorated building is one merged geometry, and if
 * a district ever repeats a building shape it can be instanced with zero further work.
 *
 * WHAT THIS MODULE DELIBERATELY DOES NOT DO
 * It does not place anything. Placement -- where the lamps go, how many, what avoids the
 * buildings -- is the clutter lane's call, and this file is the API underneath it. The one
 * exception is proof() at the bottom, which builds a real field against the live scene purely to
 * measure the claim above, and removes it again.
 *
 * ONE RENDERER LAW: this module constructs NO WebGLRenderer and NO canvas. It only ever builds
 * geometry and meshes, and it adds them to the scene that world3d.js already owns
 * (AK_WORLD3D._state.scene). Zero WebGL contexts spent. See three_boot.js:74.
 *
 * NO em-dashes anywhere in this file (hook law, use --).
 */
(function (root) {
  'use strict';

  /* =====================================================================
   * ENGINE ACCESS -- never throws, returns null when three is not up yet.
   * ===================================================================== */

  var _engine = null;   // test seam: _useEngine() injects a real THREE in node

  function three() {
    if (_engine) return _engine;
    try {
      var T = root && root.AK_THREE;
      if (T && typeof T.ok === 'function' && T.ok()) {
        return (typeof T.get === 'function' && T.get()) || null;
      }
      // A host that published a bare global (three_boot.js does this on load) is fine too.
      if (root && root.THREE && root.THREE.InstancedMesh) return root.THREE;
    } catch (_e) {}
    return null;
  }

  // The scene world3d owns. We never create one -- if world3d has not booted there is
  // nothing to attach to yet, and field() queues instead of failing (see flushPending).
  function scene() {
    try {
      var W = root && root.AK_WORLD3D;
      var st = W && W._state;
      return (st && st.scene) || null;
    } catch (_e) { return null; }
  }

  function renderer() {
    try {
      var W = root && root.AK_WORLD3D;
      if (W && typeof W.renderer === 'function') return W.renderer();
      return (root && root.AK_R3D) || null;
    } catch (_e) { return null; }
  }

  /* Deterministic seeded RNG, byte-identical to bldmass.js:24-33 on purpose. The clutter lane
   * needs stable placement -- a prop field reseeded with Math.random() on every district
   * re-entry makes the whole street shimmer, which reads as a rendering bug rather than as
   * randomness. Same FNV-ish hash + xorshift so a seed produces the same field in both modules. */
  function hash(str) {
    var h = 2166136261, s = String(str || 'x');
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  /* =====================================================================
   * TECHNIQUE 1 -- MERGE. N different static geometries -> ONE geometry.
   * ===================================================================== */

  /* A part record. Everything is optional except a source of geometry.
   *   { geometry } an existing BufferGeometry (NOT consumed -- we clone, caller still owns it)
   *   { w,h,d }    or a box shorthand, built and disposed internally
   *   x,y,z        offset in the TEMPLATE's own local space (not world -- see field())
   *   rx,ry,rz     euler radians
   *   scale        number or {x,y,z}
   *   color        0xRRGGBB baked into the vertex colour attribute
   */
  function box(w, h, d, color, x, y, z, opts) {
    var p = { w: w, h: h, d: d, c: color, x: x || 0, y: y || 0, z: z || 0 };
    if (opts) {
      p.rx = opts.rx; p.ry = opts.ry; p.rz = opts.rz; p.scale = opts.scale;
    }
    return p;
  }

  function colorOf(p) {
    var c = (p && (p.color != null ? p.color : p.c));
    return (typeof c === 'number') ? c : null;
  }

  /* merge(parts, opts) -> BufferGeometry (or null).
   *
   * toNonIndexed() everywhere, exactly as bldmass.js:59 reasoned: a box goes 24 -> 36 verts,
   * which is a rounding error at this scale, and it deletes a whole class of index-rebasing
   * bugs when concatenating geometries that may or may not be indexed.
   *
   * UV POLICY: UVs are carried only if EVERY part has them. A merged geometry runs under ONE
   * material, so a half-populated uv array would map garbage onto the parts that had none. When
   * any part lacks uv the whole set drops it and the output is vertex-coloured only, which is
   * the intended mode anyway (that is why there is no texture loading in this file).
   */
  function merge(parts, opts) {
    var THREE = three();
    if (!THREE || !parts || !parts.length) return null;
    opts = opts || {};

    var prepared = [], i, p;

    // Pass 1: realise every part into an owned, non-indexed, transformed geometry.
    for (i = 0; i < parts.length; i++) {
      p = parts[i];
      if (!p) continue;
      var src = p.geometry || null, owned = false;
      if (!src) {
        if (!(p.w > 0 && p.h > 0 && p.d > 0)) continue;   // not a geometry and not a box: skip
        src = new THREE.BoxGeometry(p.w, p.h, p.d);
        owned = true;                                      // we made it, we dispose it
      }
      if (!src.attributes || !src.attributes.position) { if (owned) { try { src.dispose(); } catch (_e) {} } continue; }

      // Clone before touching anything -- applyMatrix4 mutates in place and the caller's
      // template geometry must come out of here byte-identical to how it went in.
      var g = src.index ? src.toNonIndexed() : src.clone();
      if (owned) { try { src.dispose(); } catch (_e) {} }
      if (!g.attributes.normal) { try { g.computeVertexNormals(); } catch (_e) {} }

      var sc = p.scale;
      var sx = 1, sy = 1, sz = 1;
      if (typeof sc === 'number') { sx = sy = sz = sc; }
      else if (sc) { sx = sc.x != null ? sc.x : 1; sy = sc.y != null ? sc.y : 1; sz = sc.z != null ? sc.z : 1; }

      var m = new THREE.Matrix4();
      m.compose(
        new THREE.Vector3(p.x || 0, p.y || 0, p.z || 0),
        new THREE.Quaternion().setFromEuler(new THREE.Euler(p.rx || 0, p.ry || 0, p.rz || 0)),
        new THREE.Vector3(sx, sy, sz)
      );
      // applyMatrix4 runs normals through the normal matrix (inverse transpose), so a rotated
      // or non-uniformly scaled part still lights correctly. Doing this by hand, as a
      // position-only merge must, is where merge implementations usually go wrong.
      g.applyMatrix4(m);

      prepared.push({ g: g, c: colorOf(p) });
    }
    if (!prepared.length) return null;

    var allUV = true, total = 0;
    for (i = 0; i < prepared.length; i++) {
      if (!prepared[i].g.attributes.uv) allUV = false;
      total += prepared[i].g.attributes.position.count;
    }
    var keepUV = allUV && opts.uv !== false;

    // Pass 2: concatenate into flat typed arrays. Preallocated -- push() on a 100k-element
    // array reallocs a dozen times and this runs on a district swap, not at leisure.
    var pos = new Float32Array(total * 3);
    var nor = new Float32Array(total * 3);
    var col = new Float32Array(total * 3);
    var uvs = keepUV ? new Float32Array(total * 2) : null;
    var o3 = 0, o2 = 0;

    for (i = 0; i < prepared.length; i++) {
      var pg = prepared[i].g, hex = prepared[i].c;
      var ap = pg.attributes.position, an = pg.attributes.normal, ac = pg.attributes.color, au = pg.attributes.uv;
      var n = ap.count;
      var r = 1, gg = 1, bb = 1, hasFlat = (hex != null);
      if (hasFlat) { r = ((hex >> 16) & 255) / 255; gg = ((hex >> 8) & 255) / 255; bb = (hex & 255) / 255; }

      for (var v = 0; v < n; v++) {
        var k3 = o3 + v * 3;
        pos[k3] = ap.getX(v); pos[k3 + 1] = ap.getY(v); pos[k3 + 2] = ap.getZ(v);
        if (an) { nor[k3] = an.getX(v); nor[k3 + 1] = an.getY(v); nor[k3 + 2] = an.getZ(v); }
        // Explicit part colour wins; else carry the source geometry's own colour attribute;
        // else white, which is a no-op multiply against whatever the material does.
        if (hasFlat) { col[k3] = r; col[k3 + 1] = gg; col[k3 + 2] = bb; }
        else if (ac) { col[k3] = ac.getX(v); col[k3 + 1] = ac.getY(v); col[k3 + 2] = ac.getZ(v); }
        else { col[k3] = 1; col[k3 + 1] = 1; col[k3 + 2] = 1; }
        if (uvs && au) { var k2 = o2 + v * 2; uvs[k2] = au.getX(v); uvs[k2 + 1] = au.getY(v); }
      }
      o3 += n * 3; o2 += n * 2;
      try { pg.dispose(); } catch (_e) {}
    }

    var out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    if (uvs) out.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    // No groups on the output. A geometry with zero groups under a single material is exactly
    // one draw call, which is the entire point -- see estimateDrawCalls().
    out.clearGroups();
    try { out.computeBoundingSphere(); out.computeBoundingBox(); } catch (_e) {}
    out.userData.akMerged = prepared.length;
    return out;
  }

  /* Default material for a merged, vertex-coloured template.
   * Lambert and not Standard: the hub scene is lit by exactly one HemisphereLight plus one
   * DirectionalLight with no shadows and no environment map (world3d.js:638-642), so a PBR
   * material would pay for roughness/metalness/IBL sampling it has no data to use. Lambert is
   * the cheapest material that still responds to those two lights. */
  function defaultMaterial(THREE, geo, opts) {
    opts = opts || {};
    var def = { vertexColors: !!(geo && geo.attributes && geo.attributes.color) };
    if (opts.transparent) { def.transparent = true; def.opacity = opts.opacity != null ? opts.opacity : 1; }
    if (opts.alphaTest) def.alphaTest = opts.alphaTest;
    if (opts.color != null && !def.vertexColors) def.color = opts.color;
    if (opts.flatShading) def.flatShading = true;
    return new THREE.MeshLambertMaterial(def);
  }

  /* template(spec) -> {geometry, material, parts, tris, dispose}
   * Convenience wrapper: merge the parts AND pick a material, so the clutter lane can go from a
   * list of boxes to something field() accepts in one call. */
  function template(spec) {
    var THREE = three(); if (!THREE) return null;
    spec = spec || {};
    var geo = spec.geometry || merge(spec.parts, spec);
    if (!geo) return null;
    var mat = spec.material || defaultMaterial(THREE, geo, spec);
    return {
      geometry: geo, material: mat,
      parts: (geo.userData && geo.userData.akMerged) || 1,
      tris: (geo.attributes.position.count / 3) | 0,
      dispose: function () {
        try { geo.dispose(); } catch (_e) {}
        try { mat.dispose(); } catch (_e) {}
      }
    };
  }

  /* =====================================================================
   * TECHNIQUE 2 -- INSTANCE. N copies of one geometry -> ONE draw call.
   * ===================================================================== */

  var _fields = {};     // id -> handle
  var _seq = 0;
  var _lastZone = null;
  var _scratch = null;  // reused Matrix4/Quaternion/Vector3, allocated once three exists

  function scratch(THREE) {
    if (!_scratch) {
      _scratch = {
        m: new THREE.Matrix4(), q: new THREE.Quaternion(), e: new THREE.Euler(),
        p: new THREE.Vector3(), s: new THREE.Vector3(), c: new THREE.Color()
      };
    }
    return _scratch;
  }

  /* COORDINATE CONTRACT -- read this before placing anything.
   *
   * The hub speaks (x, y) on a 1700x1300 ground plane. Three speaks (x, y, z) with y UP. world3d
   * maps them at world3d.js:541 as position.set(b.x, height, b.y), i.e.
   *
   *     hub x  ->  three x        (east)
   *     hub y  ->  three z        (south / depth)
   *     height ->  three y        (up)
   *
   * Getting this backwards lays a prop field flat against a wall, and it is silent -- the props
   * render, they are just in the wrong plane. So HUB SPACE IS THE DEFAULT here and an item reads
   * {x, y, h}: the same x,y the hub and the zone building records already use, plus h for height
   * off the ground. Pass space:'three' on the field to opt out and supply raw {x,y,z}.
   */
  function writeMatrix(THREE, h, i, it) {
    var S = scratch(THREE);
    var px, py, pz;
    if (h.space === 'three') { px = it.x || 0; py = it.y || 0; pz = it.z || 0; }
    else { px = it.x || 0; py = it.h || 0; pz = it.y || 0; }

    // rot is yaw about the vertical axis, which is what a prop standing on the ground needs
    // 99% of the time. rx/ry/rz override it for the cases that are not upright.
    var ry = (it.ry != null) ? it.ry : (it.rot || 0);
    S.e.set(it.rx || 0, ry, it.rz || 0);
    S.q.setFromEuler(S.e);
    S.p.set(px, py, pz);

    var sc = it.scale;
    if (typeof sc === 'number') S.s.set(sc, sc, sc);
    else if (sc) S.s.set(sc.x != null ? sc.x : 1, sc.y != null ? sc.y : 1, sc.z != null ? sc.z : 1);
    else S.s.set(1, 1, 1);

    S.m.compose(S.p, S.q, S.s);
    h.mesh.setMatrixAt(i, S.m);
  }

  function writeColor(THREE, h, i, it) {
    if (it.color == null || !h.mesh) return false;
    var S = scratch(THREE);
    S.c.setHex(it.color);
    // THE MULTIPLY TRAP: three's shader does vColor *= color (vertex attr) and then
    // vColor.xyz *= instanceColor.xyz. They MULTIPLY, they do not replace. On a template that
    // already carries baked vertex colours, an instance colour is therefore a TINT: 0xffffff is
    // a no-op and anything darker darkens. If you want a prop that is genuinely a different
    // colour, build it on a white template and let instanceColor supply the whole hue.
    h.mesh.setColorAt(i, S.c);
    return true;
  }

  /* Bounds are the #1 instancing bug and it is worth being explicit about, because it is silent
   * and it is BACKWARDS from what you expect: the field disappears when it is ON screen.
   *
   * Verified against r160's own source. Frustum.intersectsObject reads:
   *     if (void 0 !== t.boundingSphere) { null === t.boundingSphere && t.computeBoundingSphere(); ... }
   * InstancedMesh declares boundingSphere = null, so three DOES lazily compute a correct
   * instance-aware sphere the first time it culls -- good. But look at the guard: it only
   * recomputes while the value is NULL. Once computed it is cached forever, and three has no
   * idea you rewrote the matrices.
   *
   * Measured, in node, against the real r160 build:
   *     2 instances at x=0 and x=100      -> radius 58.66
   *     move instance 1 out to x=5000     -> radius STILL 58.66   (stale, no recompute)
   *     null the sphere and recompute     -> radius 2508.66
   *
   * A stale sphere that is too SMALL means three culls the whole field the moment the tight old
   * sphere leaves the frustum, while the instances that actually moved are still in view. So
   * every path in this file that writes a matrix nulls the bounds, and the tick recomputes once
   * per dirty field rather than once per item.
   *
   * Over-allocating capacity is safe: computeBoundingSphere iterates this.count, not the
   * allocated length. Measured -- 2 live of 10 allocated gives radius 1.73, not a sphere
   * stretched back to the origin by 8 unwritten identity matrices.
   */
  function markDirty(h) {
    if (!h.mesh) return;
    h.mesh.instanceMatrix.needsUpdate = true;
    h.mesh.boundingSphere = null;
    h.mesh.boundingBox = null;
    h._dirty = true;
  }

  function capacityFor(spec, items) {
    var want = Math.max(items.length, (spec.capacity | 0) || 0);
    // Headroom so a clutter field that grows by a few props does not realloc the whole buffer.
    // Only applied when the caller did not state a capacity, so an explicit budget is honoured.
    if (!spec.capacity && want > 0 && spec.grow !== false) want = Math.ceil(want * 1.25);
    return Math.max(1, want);
  }

  function build(h) {
    var THREE = three(); if (!THREE || h.mesh) return false;
    var sc = h.spec.scene || scene();
    if (!sc) return false;                       // world3d has not booted: stay queued

    var geo = h.spec.geometry || (h.spec.template && h.spec.template.geometry) || merge(h.spec.parts, h.spec);
    if (!geo) return false;
    var mat = h.spec.material || (h.spec.template && h.spec.template.material) || defaultMaterial(THREE, geo, h.spec);

    var items = h.items;
    var cap = capacityFor(h.spec, items);
    var mesh = new THREE.InstancedMesh(geo, mat, cap);
    mesh.count = items.length;                   // render only the live slots, keep the rest spare
    mesh.name = 'akinstance:' + h.id;
    mesh.userData.akField = h.id;
    mesh.userData.akZone = h.zone;
    // Static by default: the matrix buffer is uploaded once instead of every frame. A field that
    // animates (swaying, spawning) must declare dynamic:true or the upload is wasted work.
    try { mesh.instanceMatrix.setUsage(h.spec.dynamic ? THREE.DynamicDrawUsage : THREE.StaticDrawUsage); } catch (_e) {}
    if (h.spec.frustumCulled === false) mesh.frustumCulled = false;
    if (h.spec.renderOrder != null) mesh.renderOrder = h.spec.renderOrder;

    h.mesh = mesh; h.geometry = geo; h.material = mat; h.scene = sc;
    h._ownGeo = !h.spec.geometry && !h.spec.template;   // only dispose what we built ourselves
    h._ownMat = !h.spec.material && !h.spec.template;

    var anyColor = false;
    for (var i = 0; i < items.length; i++) {
      writeMatrix(THREE, h, i, items[i]);
      if (writeColor(THREE, h, i, items[i])) anyColor = true;
    }
    if (anyColor && mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    markDirty(h);
    sc.add(mesh);
    h.built = true;
    return true;
  }

  /* field(spec) -> handle. ALWAYS returns a usable handle, even when three has not loaded and
   * even when world3d has not booted. That is deliberate: the clutter lane runs from init(), and
   * init() fires long before the async vendor load resolves (world3d.js:741 awaits ready()).
   * A field() that returned null in that window would push every caller into writing its own
   * retry loop, and the ones that forgot would silently place nothing. Instead the handle queues
   * and the tick builds it the moment the scene exists.
   *
   * spec:
   *   id          stable string. Re-creating the same id replaces the old field.
   *   parts       part records -> merged into the template (or pass geometry/template/material)
   *   items       [{x,y,h,rot,scale,color}] in HUB space by default
   *   zone        district id this field belongs to. Auto-disposed on district change.
   *               Pass '*' to survive district swaps.
   *   space       'hub' (default) or 'three'
   *   dynamic     true if the matrices change per frame
   *   capacity    preallocate for growth; defaults to items.length * 1.25
   */
  function field(spec) {
    spec = spec || {};
    var id = spec.id || ('akfield_' + (++_seq));
    if (_fields[id]) remove(id);                 // replace, never silently stack two fields

    var h = {
      id: id,
      spec: spec,
      items: (spec.items || []).slice(),
      zone: (spec.zone != null) ? spec.zone : currentZone(),
      space: spec.space === 'three' ? 'three' : 'hub',
      mesh: null, geometry: null, material: null, scene: null,
      built: false, _dirty: false, _ownGeo: false, _ownMat: false
    };

    h.count = function () { return h.items.length; };

    /* Rewrite every placement. Rebuilds the buffer only when the new set overflows the
     * allocated capacity, otherwise it just rewrites matrices and moves .count -- which is why
     * capacity headroom exists. */
    h.setItems = function (items) {
      h.items = (items || []).slice();
      if (!h.mesh) return h;                     // still queued: build() will pick these up
      var THREE = three();
      var cap = h.mesh.instanceMatrix.count;
      if (h.items.length > cap) { rebuild(h); return h; }
      var anyColor = false;
      for (var i = 0; i < h.items.length; i++) {
        writeMatrix(THREE, h, i, h.items[i]);
        if (writeColor(THREE, h, i, h.items[i])) anyColor = true;
      }
      h.mesh.count = h.items.length;
      if (anyColor && h.mesh.instanceColor) h.mesh.instanceColor.needsUpdate = true;
      markDirty(h);
      return h;
    };

    h.setItem = function (i, it) {
      if (i < 0 || i >= h.items.length) return h;
      h.items[i] = it;
      if (!h.mesh) return h;
      var THREE = three();
      writeMatrix(THREE, h, i, it);
      if (writeColor(THREE, h, i, it) && h.mesh.instanceColor) h.mesh.instanceColor.needsUpdate = true;
      markDirty(h);
      return h;
    };

    h.setColor = function (i, hex) {
      if (!h.mesh || i < 0 || i >= h.items.length) return h;
      h.items[i] = h.items[i] || {}; h.items[i].color = hex;
      var THREE = three();
      if (writeColor(THREE, h, i, h.items[i]) && h.mesh.instanceColor) h.mesh.instanceColor.needsUpdate = true;
      return h;
    };

    h.show = function (b) { if (h.mesh) h.mesh.visible = !!b; return h; };

    h.stats = function () {
      var parts = (h.geometry && h.geometry.userData && h.geometry.userData.akMerged) || 1;
      var n = h.items.length;
      return {
        id: h.id, zone: h.zone, built: !!h.built, count: n, parts: parts,
        capacity: h.mesh ? h.mesh.instanceMatrix.count : 0,
        tris: h.geometry ? ((h.geometry.attributes.position.count / 3) | 0) * n : 0,
        naiveCalls: n * parts,                   // one Mesh per part per prop
        mergedCalls: n,                          // merged prop, still one Mesh each
        actualCalls: (h.built && h.mesh && h.mesh.visible && n > 0) ? 1 : 0,
        saved: Math.max(0, n * parts - ((h.built && n > 0) ? 1 : 0))
      };
    };

    h.dispose = function () { remove(h.id); };

    _fields[id] = h;
    build(h);                                    // build now if we can, else the tick will
    return h;
  }

  function rebuild(h) {
    var items = h.items, spec = h.spec;
    detach(h, /*keepTemplate*/ true);
    h.spec = spec; h.items = items; h.mesh = null; h.built = false;
    build(h);
  }

  function detach(h, keepTemplate) {
    try { if (h.mesh && h.scene) h.scene.remove(h.mesh); } catch (_e) {}
    try { if (h.mesh && h.mesh.dispose) h.mesh.dispose(); } catch (_e) {}   // frees instance buffers
    if (!keepTemplate) {
      // Only dispose what this field actually created. A shared template passed in by the
      // clutter lane may back several fields, and disposing it here would blank the others.
      if (h._ownGeo) { try { h.geometry && h.geometry.dispose(); } catch (_e) {} }
      if (h._ownMat) { try { h.material && h.material.dispose(); } catch (_e) {} }
    }
    h.mesh = null; h.built = false;
  }

  function remove(id) {
    var h = _fields[id]; if (!h) return false;
    detach(h, false);
    delete _fields[id];
    return true;
  }

  function get(id) { return _fields[id] || null; }
  function list() { var out = []; for (var k in _fields) if (_fields.hasOwnProperty(k)) out.push(_fields[k]); return out; }

  function clear(zoneId) {
    var n = 0, all = list();
    for (var i = 0; i < all.length; i++) {
      if (zoneId == null || all[i].zone === zoneId) { remove(all[i].id); n++; }
    }
    return n;
  }

  function currentZone() {
    try {
      var c = root && root.AK_CTX;
      if (c && c.zoneId) return c.zoneId;
      var W = root && root.AK_WORLD3D;
      return (W && W._state && W._state.zoneId) || null;
    } catch (_e) { return null; }
  }

  /* =====================================================================
   * DRAW CALL ACCOUNTING
   * ===================================================================== */

  /* estimateDrawCalls -- a STATIC count, mirroring how r160 builds its render list, NOT a GPU
   * measurement. The ground truth in-page is renderer.info.render.calls, which proof() reads.
   * This exists so the clutter lane can budget before it ships anything to a device.
   *
   * The rule, from WebGLRenderer.projectObject: an array material pushes one render item per
   * geometry group that resolves to a material; a single material pushes exactly one item for
   * the whole mesh regardless of how many groups the geometry has. That asymmetry is why the
   * hub's buildings cost 6 calls each (BoxGeometry has 6 groups, verified, and world3d.js:539
   * hands it a 6-material array) while an InstancedMesh of 400 props costs 1.
   */
  function callsForObject(o) {
    if (!o || o.visible === false || !o.geometry || !o.material) return 0;
    var mat = o.material;
    if (Object.prototype.toString.call(mat) === '[object Array]') {
      var groups = o.geometry.groups || [];
      if (!groups.length) return mat.length ? 1 : 0;
      var n = 0;
      for (var i = 0; i < groups.length; i++) { if (mat[groups[i].materialIndex]) n++; }
      return n;
    }
    return 1;
  }

  function estimateDrawCalls(obj) {
    var total = 0;
    if (!obj) return 0;
    if (typeof obj.traverseVisible === 'function') {
      obj.traverseVisible(function (o) { total += callsForObject(o); });
      return total;
    }
    return callsForObject(obj);
  }

  /* report() -- the number this lane exists to move. Sums every live field and states what the
   * same content would have cost as ordinary Meshes. */
  function report() {
    var all = list(), i, s;
    var r = { fields: all.length, props: 0, tris: 0, naiveCalls: 0, mergedCalls: 0, actualCalls: 0, perField: [] };
    for (i = 0; i < all.length; i++) {
      s = all[i].stats();
      r.props += s.count; r.tris += s.tris;
      r.naiveCalls += s.naiveCalls; r.mergedCalls += s.mergedCalls; r.actualCalls += s.actualCalls;
      r.perField.push(s);
    }
    r.saved = r.naiveCalls - r.actualCalls;
    r.sceneCalls = estimateDrawCalls(scene());
    return r;
  }

  /* =====================================================================
   * LIFECYCLE -- AK_SYSTEMS registration
   * ===================================================================== */

  /* Zone change is a POLL, not an event. index.html:1354 enterZone() mutates activeZone and
   * notifies nobody, which is why world3d.js:900 re-checks every tick. Same idiom here, and it
   * is not optional for this module: world3d.setZone (world3d.js:758) reuses the SAME
   * THREE.Scene across a district swap and removes only its own buildings + ground. Anything
   * else parented to that scene SURVIVES the swap. Without this GC a street of lamps placed in
   * HOME_TURF would still be standing in THE_DOCKS, floating over a different ground plate. */
  function onZone(zid) {
    if (zid === _lastZone) return 0;
    var prev = _lastZone;
    _lastZone = zid;
    if (prev == null) return 0;                  // first observation is not a change
    var all = list(), n = 0;
    for (var i = 0; i < all.length; i++) {
      var h = all[i];
      if (h.zone === '*' || h.zone == null) continue;      // explicitly district-agnostic
      if (h.spec.autoGC === false) continue;
      if (h.zone !== zid) { remove(h.id); n++; }
    }
    return n;
  }

  function flushPending() {
    var all = list(), n = 0;
    for (var i = 0; i < all.length; i++) {
      var h = all[i];
      if (h.built) {
        // world3d re-boots into a BRAND NEW Scene (world3d.js:719). A field attached to the old
        // one is orphaned and renders nothing, with no error. Re-attach instead of going dark.
        var live = h.spec.scene || scene();
        if (live && h.scene !== live && h.mesh) {
          try { h.scene && h.scene.remove(h.mesh); } catch (_e) {}
          try { live.add(h.mesh); h.scene = live; } catch (_e) {}
        }
        continue;
      }
      if (build(h)) n++;
    }
    return n;
  }

  function flushDirty() {
    var all = list(), n = 0;
    for (var i = 0; i < all.length; i++) {
      var h = all[i];
      if (!h._dirty || !h.mesh) continue;
      // Recompute once per field per frame instead of once per setItem call. Nulled bounds
      // would be lazily recomputed by three's own frustum test anyway, but doing it here keeps
      // the cost off the render path and out of the middle of a frame.
      try { h.mesh.computeBoundingSphere(); } catch (_e) {}
      h._dirty = false; n++;
    }
    return n;
  }

  function tick(dt, ctx) {
    if (!three()) return;                        // vendor not up: nothing to do, stay silent
    var zid = (ctx && ctx.zoneId) || currentZone();
    // Compare the district BEFORE onZone consumes the change. onZone returns the number of
    // fields it collected, which is legitimately 0 on a district that had none -- keying the
    // structure re-read off that return value would silently skip the rebuild exactly when the
    // previous district was empty, which is the common case.
    var zoneChanged = (zid !== _lastZone);
    onZone(zid);
    if (zoneChanged) BUILDS.sig = null;          // force a structure re-read for the new district
    syncBuilds(ctx, false);                      // throttled to 4Hz and no-ops on an unchanged sig
    flushPending();
    flushDirty();
  }

  /* =====================================================================
   * LOAD-BEARING CONSUMER -- player structures (p.builds[]) in 3D.
   *
   * WHY THIS IS HERE AND NOT IN THE CLUTTER LANE
   * An instancing API with no caller is the failure mode this repo has hit four times. But the
   * decorative prop scatter belongs to the clutter lane, so this module needed a workload that is
   * unambiguously ITS OWN. Player structures are exactly that, for three reasons:
   *   1. They are the canonical instancing case -- N copies of literally the same geometry. A base
   *      with 40 walls is 40 identical boxes, which is the textbook InstancedMesh workload.
   *   2. They already exist as real, saved, player-authored content. Nothing is invented here.
   *   3. They are MISSING from 3D entirely. buildmode.js:2005 draws p.builds through Canvas2D
   *      drawStruct only, and world3d.js never reads p.builds at all, so a player who walls in
   *      their turf sees it vanish the moment the 3D district is on.
   *
   * So this both exercises the technique at real scale and closes an actual hole.
   *
   * READ-ONLY on p.builds. buildmode.js owns every write (its header at buildmode.js:50 is
   * explicit that all writers go through the one ctx.econ.mutateProfile path). This only reads,
   * so there is no second writer and no save-loss surface.
   *
   * DRAW CALL MATH for a typical walled base -- 40 walls + 16 path tiles + 6 planters:
   *   naive, one Mesh each                    = 62 draw calls
   *   instanced, one field per type present   =  3 draw calls
   * and the 62-call version does not exist today at all, so the honest framing is: this adds the
   * content at 3 calls instead of the 62 it would have cost the obvious way.
   * ===================================================================== */

  /* Extrusion heights come from buildmode's OWN table (buildmode.js:1367 STRUCT_H, keyed by
   * family, with PATH special-cased to 2) rather than from numbers invented here. buildmode's
   * isometric editor already extrudes structures by exactly these values, so a wall is the same
   * height in the iso editor and in the 3D district instead of two lanes disagreeing. */
  var STRUCT_H = { wall: 46, barricade: 34, garden: 10, deco: 26 };
  function structHeight(def, type) { return type === 'PATH' ? 2 : ((def && STRUCT_H[def.family]) || 24); }

  // Per-family tint. Vertex-baked into the template, so instanceColor stays free as a per-piece
  // multiply (see the multiply trap in writeColor) -- which is what marks scaffolding below.
  var STRUCT_COL = {
    WALL: 0x6b4a2a, STONE: 0x6a6a72, METAL: 0x8a8f9a, BARRICADE: 0x5a4632,
    PATH: 0x3a3a42, GARDEN: 0x3f6b32, PLANTER: 0x2f5f55
  };

  var BUILDS = { on: true, sig: null, zone: null, at: 0, ids: [], n: 0, calls: 0 };

  function structDefs() {
    try { var B = root && root.AK_BUILDMODE; return (B && B.STRUCT) || null; } catch (_e) { return null; }
  }
  function profile() {
    try { var e = root && root.AK_ECON; return (e && typeof e.loadProfile === 'function') ? (e.loadProfile() || null) : null; } catch (_e) { return null; }
  }
  function underConstruction(b) { return !!(b && b.uc && Date.now() < (b.uc.t0 + b.uc.dur)); }

  /* PURE: group this district's structures by type. Split out from the sync so it is directly
   * testable with a literal array and no profile, no DOM and no three. */
  function groupBuilds(builds, zoneId) {
    var out = {}, i, b;
    for (i = 0; i < (builds || []).length; i++) {
      b = builds[i];
      if (!b || !b.type) continue;
      if (zoneId != null && b.zone !== zoneId) continue;    // buildmode.js:439 uses the same filter
      if (!out[b.type]) out[b.type] = [];
      out[b.type].push(b);
    }
    return out;
  }

  /* PURE: a cheap change signature. Rebuilding the instanced fields every frame would be absurd
   * (a district swap allocates geometry), and p.builds changes on a player action, never per
   * frame. So the tick compares this string at 4Hz and does nothing at all when it matches.
   * Includes the under-construction flag so a build finishing re-tints without a manual poke. */
  function buildsSig(groups, zoneId) {
    var keys = [], k, i, arr, s = (zoneId || '-') + '|';
    for (k in groups) if (groups.hasOwnProperty(k)) keys.push(k);
    keys.sort();
    for (i = 0; i < keys.length; i++) {
      arr = groups[keys[i]];
      s += keys[i] + ':' + arr.length + ':';
      for (var j = 0; j < arr.length; j++) {
        var b = arr[j];
        s += (b.x | 0) + ',' + (b.y | 0) + ',' + ((b.rot | 0) & 3) + (underConstruction(b) ? 'u' : '') + ';';
      }
      s += '|';
    }
    return s;
  }

  /* Template per structure type. This is where merge() earns its generalisation over
   * bldmass.js:56: PLANTER is shape:'circle', so its template is a real CylinderGeometry, which a
   * box-only merge could not express. Everything else is a slab plus a cap -- the cap exists
   * purely for silhouette, the same argument bldmass.js:96 makes about parapets. */
  function structTemplate(THREE, type, def) {
    var h = structHeight(def, type);
    var col = STRUCT_COL[type] || 0x555560;
    var parts;
    if (def && def.shape === 'circle') {
      var r = def.cr || 24;
      parts = [
        { geometry: new THREE.CylinderGeometry(r, r * 0.86, h, 10), y: h / 2, color: col },
        { geometry: new THREE.CylinderGeometry(r * 1.08, r * 1.08, Math.max(2, h * 0.12), 10), y: h, color: 0x1b1b22 }
      ];
    } else {
      // Unrotated footprint on purpose. b.rot is 0..3 quarter turns (buildmode.js:474 swaps w/h
      // for a rotated piece) and this lane applies a REAL yaw of rot*PI/2 in the instance matrix.
      // Pre-swapping the template AND rotating the matrix would apply the turn twice.
      var w = (def && def.dw) || 64, d = (def && def.dh) || 64;
      parts = [{ w: w, h: h, d: d, c: col, x: 0, y: h / 2, z: 0 }];
      if (type !== 'PATH') parts.push({ w: w * 1.04, h: Math.max(2, h * 0.10), d: d * 1.04, c: 0x1b1b22, x: 0, y: h, z: 0 });
    }
    return merge(parts);
  }

  function syncBuilds(ctx, force) {
    if (!BUILDS.on) return false;
    var THREE = three(); if (!THREE) return false;
    if (!scene()) return false;
    var now = Date.now();
    if (!force && (now - BUILDS.at) < 250) return false;    // 4Hz, see buildsSig
    BUILDS.at = now;

    var defs = structDefs(); if (!defs) return false;       // buildmode not loaded: nothing to do
    var p = profile(); if (!p) return false;
    var zid = (ctx && ctx.zoneId) || currentZone();
    var groups = groupBuilds(p.builds || [], zid);
    var sig = buildsSig(groups, zid);
    if (!force && sig === BUILDS.sig) return false;         // unchanged: the common path, zero work
    BUILDS.sig = sig; BUILDS.zone = zid;

    for (var i = 0; i < BUILDS.ids.length; i++) remove(BUILDS.ids[i]);
    BUILDS.ids = []; BUILDS.n = 0; BUILDS.calls = 0;

    for (var type in groups) {
      if (!groups.hasOwnProperty(type)) continue;
      var def = defs[type]; if (!def) continue;
      var arr = groups[type];
      var geo = structTemplate(THREE, type, def);
      if (!geo) continue;
      var items = [];
      for (var j = 0; j < arr.length; j++) {
        var b = arr[j];
        items.push({
          x: b.x, y: b.y, h: 0,
          rot: ((b.rot | 0) & 3) * (Math.PI / 2),
          // Scaffolding reads as a dark ghost. instanceColor MULTIPLIES the baked vertex colour,
          // so 0x6a6a6a is a 42% dim of whatever the family tint already is, not a flat grey.
          color: underConstruction(b) ? 0x6a6a6a : 0xffffff
        });
      }
      var id = 'akbuilds_' + type;
      field({ id: id, geometry: geo, items: items, zone: zid, autoGC: false });
      BUILDS.ids.push(id); BUILDS.n += items.length; BUILDS.calls++;
    }
    return true;
  }

  function buildsStats() {
    return {
      on: BUILDS.on, zone: BUILDS.zone, types: BUILDS.ids.length,
      props: BUILDS.n, actualCalls: BUILDS.calls, naiveCalls: BUILDS.n,
      saved: Math.max(0, BUILDS.n - BUILDS.calls)
    };
  }

  /* =====================================================================
   * PROOF -- measured, against the live renderer. Not a claim, a reading.
   * ===================================================================== */

  /* proof(n) builds a real field of n props (4 boxes each) in the live scene, reads
   * renderer.info.render.calls before and after a render, then removes it. This is the only
   * place in this file that puts anything on screen, and it cleans up after itself.
   * Reachable in a browser as AK_INSTANCE.proof() or with ?akinstance=proof on the hub URL. */
  function proof(n) {
    n = n | 0 || 200;
    var THREE = three(), sc = scene(), r = renderer();
    var out = { ok: false, n: n, note: '' };
    if (!THREE) { out.note = 'three not loaded'; return out; }
    if (!sc) { out.note = 'world3d scene not booted'; return out; }

    function calls() {
      if (!r || !r.info || !r.info.render) return null;
      try {
        var cam = (root.AK_WORLD3D && root.AK_WORLD3D._state && root.AK_WORLD3D._state.camera) || null;
        if (cam) r.render(sc, cam);
        return r.info.render.calls;
      } catch (_e) { return null; }
    }

    out.callsBefore = calls();
    out.sceneCallsBefore = estimateDrawCalls(sc);

    // A 4-part prop: base, post, head, lens. Deliberately the shape of a real street lamp so
    // the parts-per-prop multiplier in the math is honest rather than a flattering 1.
    var parts = [
      box(6, 3, 6, 0x1b1b22, 0, 1.5, 0),
      box(2, 34, 2, 0x24242c, 0, 19, 0),
      box(10, 3, 6, 0x3a3d46, 0, 37, 2),
      box(6, 2, 4, 0xffd9a0, 0, 35.5, 3)
    ];
    var rnd = rngFor('akinstance-proof');
    var items = [];
    for (var i = 0; i < n; i++) {
      items.push({ x: rnd() * 1700, y: rnd() * 1300, h: 0, rot: rnd() * Math.PI * 2 });
    }
    var f = field({ id: '__akinstance_proof', parts: parts, items: items, zone: '*', autoGC: false });
    flushPending();

    out.callsAfter = calls();
    out.sceneCallsAfter = estimateDrawCalls(sc);
    var s = f.stats();
    out.built = s.built;
    out.parts = s.parts;
    out.naiveCalls = s.naiveCalls;
    out.actualCalls = s.actualCalls;
    out.deltaMeasured = (out.callsBefore != null && out.callsAfter != null) ? (out.callsAfter - out.callsBefore) : null;
    out.deltaEstimated = out.sceneCallsAfter - out.sceneCallsBefore;
    out.ok = !!s.built;
    remove('__akinstance_proof');
    try {
      console.log('[AK_INSTANCE] proof: ' + n + ' props x ' + s.parts + ' parts = ' + s.naiveCalls +
        ' naive draw calls -> ' + out.actualCalls + ' actual. estimated scene delta ' +
        out.deltaEstimated + ', measured renderer delta ' + out.deltaMeasured);
    } catch (_e) {}
    return out;
  }

  /* =====================================================================
   * API
   * ===================================================================== */

  var API = {
    // capability
    ok: function () { return !!three(); },
    three: three, scene: scene, renderer: renderer,

    // technique 1 -- merge
    merge: merge, box: box, template: template, defaultMaterial: function (g, o) {
      var T = three(); return T ? defaultMaterial(T, g, o) : null;
    },

    // technique 2 -- instance
    field: field, get: get, remove: remove, list: list, clear: clear,

    // accounting
    estimateDrawCalls: estimateDrawCalls, callsForObject: callsForObject, report: report,

    // helpers the clutter lane needs
    rngFor: rngFor, hash: hash, currentZone: currentZone,

    // the load-bearing consumer: player structures (p.builds[]) rendered instanced in 3D
    builds: {
      sync: function (ctx, force) { return syncBuilds(ctx || (root && root.AK_CTX) || null, force !== false); },
      stats: buildsStats,
      group: groupBuilds, sig: buildsSig, height: structHeight,
      enable: function (b) { BUILDS.on = b !== false; if (!BUILDS.on) { for (var i = 0; i < BUILDS.ids.length; i++) remove(BUILDS.ids[i]); BUILDS.ids = []; BUILDS.sig = null; } return BUILDS.on; }
    },

    // lifecycle (exposed for tests and for a host that wants to drive it manually)
    tick: tick, flushPending: flushPending, flushDirty: flushDirty, onZone: onZone,

    // proof + test seam
    proof: proof,
    _useEngine: function (T) { _engine = T || null; _scratch = null; return _engine; },
    _fields: _fields,
    selfTest: selfTest
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_INSTANCE = API;
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({
          id: 'akinstance',
          init: function (ctx) { _lastZone = (ctx && ctx.zoneId) || currentZone(); },
          onTick: function (dt, ctx) { tick(dt, ctx); }
        });
      }
    } catch (_e) {}
    // Opt-in in-page proof. Costs nothing unless explicitly asked for on the URL.
    try {
      if (String(root.location && root.location.search || '').indexOf('akinstance=proof') >= 0) {
        root.setTimeout(function () { proof(400); }, 6000);   // after the async vendor load lands
      }
    } catch (_e) {}
  }

  /* =====================================================================
   * HEADLESS PROOF -- real three r160, no mocks. `node systems/akinstance.js`
   * ===================================================================== */
  function selfTest(THREE) {
    var out = [], ok = true;
    function chk(label, cond, got) {
      if (!cond) ok = false;
      out.push((cond ? 'PASS ' : 'FAIL ') + label + (got !== undefined ? ('  got=' + got) : ''));
    }
    function eq(label, a, b, tol) {
      var pass = Math.abs(a - b) <= (tol || 1e-6);
      if (!pass) ok = false;
      out.push((pass ? 'PASS ' : 'FAIL ') + label + '  got=' + a + ' want=' + b);
    }

    _useEngineLocal(THREE);
    clear(null);
    _lastZone = null;

    // --- technique 1: merge ---------------------------------------------------------------
    var parts = [
      box(6, 3, 6, 0x1b1b22, 0, 1.5, 0),
      box(2, 34, 2, 0x24242c, 0, 19, 0),
      box(10, 3, 6, 0x3a3d46, 0, 37, 2),
      box(6, 2, 4, 0xffd9a0, 0, 35.5, 3)
    ];
    var geo = merge(parts);
    chk('merge returns a geometry', !!geo);
    eq('merged vert count = 4 boxes x 36 non-indexed verts', geo.attributes.position.count, 144);
    chk('merged carries a colour attribute', !!geo.attributes.color);
    chk('merged has zero groups (1 material, 1 call)', geo.groups.length === 0, geo.groups.length);
    eq('merged records its part count', geo.userData.akMerged, 4);
    // colour actually baked per part, not a uniform fill
    var c0 = geo.attributes.color.getX(0), c3 = geo.attributes.color.getX(143);
    chk('per-part colours differ across the merge', Math.abs(c0 - c3) > 0.01, c0 + ' vs ' + c3);

    // caller's geometry must survive untouched (we clone, we do not consume)
    var srcG = new THREE.BoxGeometry(2, 2, 2);
    var beforeX = srcG.attributes.position.getX(0);
    merge([{ geometry: srcG, x: 500, y: 0, z: 0, color: 0xff0000 }]);
    eq('caller geometry is NOT mutated by merge', srcG.attributes.position.getX(0), beforeX);

    // rotation goes through the normal matrix, not just positions
    var flat = merge([{ geometry: new THREE.PlaneGeometry(2, 2), rx: -Math.PI / 2, color: 0x808080 }]);
    eq('rotated part normal points up (+y)', flat.attributes.normal.getY(0), 1, 1e-6);

    // --- technique 2: instancing ----------------------------------------------------------
    var sc = new THREE.Scene();
    var N = 200;
    var items = [];
    for (var i = 0; i < N; i++) items.push({ x: i * 8, y: i * 5, h: 0, rot: i * 0.1 });
    var f = field({ id: 'lamps', parts: parts, items: items, scene: sc, zone: 'HOME_TURF' });
    chk('field built immediately when scene + engine exist', f.built === true);
    eq('InstancedMesh renders exactly items.length', f.mesh.count, N);
    chk('capacity over-allocated for growth', f.mesh.instanceMatrix.count > N, f.mesh.instanceMatrix.count);
    eq('field is 1 draw call', estimateDrawCalls(f.mesh), 1);

    var s = f.stats();
    eq('naive cost = props x parts', s.naiveCalls, N * 4);
    eq('merged-only cost = props', s.mergedCalls, N);
    eq('actual cost', s.actualCalls, 1);
    eq('draw calls saved', s.saved, N * 4 - 1);

    // hub-space mapping: {x,y,h} -> three (x, h, y). Getting this wrong is silent.
    var m = new THREE.Matrix4(); f.mesh.getMatrixAt(7, m);
    var pos = new THREE.Vector3().setFromMatrixPosition(m);
    eq('hub x -> three x', pos.x, 56);
    eq('hub h -> three y', pos.y, 0);
    eq('hub y -> three z', pos.z, 35);

    // three-space opt-out
    var f3 = field({ id: 'three_space', parts: [box(1, 1, 1, 0xffffff, 0, 0, 0)], scene: sc, space: 'three', items: [{ x: 1, y: 2, z: 3 }], zone: '*' });
    var m3 = new THREE.Matrix4(); f3.mesh.getMatrixAt(0, m3);
    var p3 = new THREE.Vector3().setFromMatrixPosition(m3);
    chk('space:three passes x,y,z straight through', p3.x === 1 && p3.y === 2 && p3.z === 3, p3.x + ',' + p3.y + ',' + p3.z);

    // --- the bounds staleness bug (the reason markDirty exists) ---------------------------
    f.mesh.computeBoundingSphere();
    var rBefore = f.mesh.boundingSphere.radius;
    f.setItems([{ x: 0, y: 0, h: 0 }, { x: 5000, y: 0, h: 0 }]);
    chk('setItems nulls the cached bounds', f.mesh.boundingSphere === null);
    flushDirty();
    var rAfter = f.mesh.boundingSphere.radius;
    chk('bounds recomputed to cover the moved instances', rAfter > 2400, rAfter.toFixed(1));
    chk('bounds actually changed from the stale value', Math.abs(rAfter - rBefore) > 1, rBefore.toFixed(1) + ' -> ' + rAfter.toFixed(1));
    eq('count follows setItems down', f.mesh.count, 2);

    // --- capacity overflow rebuild --------------------------------------------------------
    var big = [];
    for (i = 0; i < 900; i++) big.push({ x: i, y: i, h: 0 });
    f.setItems(big);
    eq('overflow rebuilt the buffer', f.mesh.count, 900);
    chk('rebuilt capacity covers the new set', f.mesh.instanceMatrix.count >= 900, f.mesh.instanceMatrix.count);
    chk('rebuilt mesh is back in the scene', sc.children.indexOf(f.mesh) >= 0);

    // --- per-instance colour --------------------------------------------------------------
    var fc = field({ id: 'tinted', parts: [box(2, 2, 2, 0xffffff, 0, 0, 0)], scene: sc, zone: '*',
      items: [{ x: 0, y: 0, h: 0, color: 0xff0000 }, { x: 10, y: 0, h: 0, color: 0x00ff00 }] });
    chk('instanceColor allocated when items carry colour', !!fc.mesh.instanceColor);
    var col = new THREE.Color(); fc.mesh.getColorAt(0, col);
    chk('per-instance colour written', col.r > 0.9 && col.g < 0.1, col.r + ',' + col.g);

    // --- draw-call estimator vs the hub's own 6-material buildings -------------------------
    var bldMat = [];
    for (i = 0; i < 6; i++) bldMat.push(new THREE.MeshLambertMaterial());
    var bld = new THREE.Mesh(new THREE.BoxGeometry(160, 160, 70), bldMat);
    eq('a 6-material building box is 6 draw calls (world3d.js:539)', estimateDrawCalls(bld), 6);
    var single = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshLambertMaterial());
    eq('the same box with ONE material is 1 draw call', estimateDrawCalls(single), 1);

    // scene-wide walk
    var sc2 = new THREE.Scene();
    sc2.add(bld); sc2.add(single);
    eq('scene walk sums render items', estimateDrawCalls(sc2), 7);
    single.visible = false;
    eq('invisible objects are not counted', estimateDrawCalls(sc2), 6);

    // --- zone GC (world3d reuses ONE Scene across district swaps) -------------------------
    _lastZone = 'HOME_TURF';
    var before = list().length;
    var gcd = onZone('THE_DOCKS');
    chk('district change disposed the HOME_TURF field', gcd === 1, gcd);
    chk('zone:"*" fields survived the swap', !!get('three_space') && !!get('tinted'));
    chk('the HOME_TURF field is gone', !get('lamps'));
    chk('field count dropped by exactly one', list().length === before - 1, list().length);

    // --- queueing before the scene exists --------------------------------------------------
    var noScene = field({ id: 'queued', parts: [box(1, 1, 1, 0xffffff, 0, 0, 0)], items: [{ x: 1, y: 1, h: 0 }], zone: '*' });
    chk('field() returns a handle even with no scene', !!noScene && noScene.built === false);
    noScene.spec.scene = sc;                       // scene arrives later, as world3d boot does
    eq('flushPending builds the queued field', flushPending(), 1);
    chk('queued field is now live', noScene.built === true && noScene.mesh.count === 1);

    // --- player structures: grouping + signature (pure) -----------------------------------
    var builds = [
      { type: 'WALL', x: 64, y: 64, rot: 0, zone: 'HOME_TURF' },
      { type: 'WALL', x: 128, y: 64, rot: 1, zone: 'HOME_TURF' },
      { type: 'PATH', x: 192, y: 64, rot: 0, zone: 'HOME_TURF' },
      { type: 'WALL', x: 999, y: 999, rot: 0, zone: 'THE_DOCKS' }   // other district: must not appear
    ];
    var grp = groupBuilds(builds, 'HOME_TURF');
    eq('groupBuilds filters by district', grp.WALL.length, 2);
    chk('groupBuilds keeps other types', grp.PATH && grp.PATH.length === 1);
    chk('groupBuilds excludes other districts', !grp.THE_DOCKS);
    var sigA = buildsSig(grp, 'HOME_TURF');
    chk('signature is stable across identical reads', sigA === buildsSig(groupBuilds(builds, 'HOME_TURF'), 'HOME_TURF'));
    builds[0].x = 320;
    chk('signature changes when a piece moves', buildsSig(groupBuilds(builds, 'HOME_TURF'), 'HOME_TURF') !== sigA);
    builds[0].x = 64;
    var sigB = buildsSig(groupBuilds(builds, 'HOME_TURF'), 'HOME_TURF');
    chk('signature returns to the original when the move is undone', sigB === sigA);
    builds[0].uc = { t0: Date.now(), dur: 60000 };
    chk('signature reflects under-construction state', buildsSig(groupBuilds(builds, 'HOME_TURF'), 'HOME_TURF') !== sigA);
    delete builds[0].uc;
    // heights come from buildmode's own table, not from invented numbers
    eq('wall height matches buildmode STRUCT_H.wall', structHeight({ family: 'wall' }, 'WALL'), 46);
    eq('PATH is special-cased flat', structHeight({ family: 'deco' }, 'PATH'), 2);

    // --- player structures: full sync against a fake profile + real three ------------------
    var prevEcon = root.AK_ECON, prevBM = root.AK_BUILDMODE, prevW3 = root.AK_WORLD3D;
    var scB = new THREE.Scene();
    root.AK_ECON = { loadProfile: function () { return { builds: builds }; } };
    root.AK_BUILDMODE = { STRUCT: {
      WALL:    { family: 'wall', shape: 'rect', dw: 76, dh: 42, cw: 84, ch: 48 },
      PATH:    { family: 'deco', shape: 'rect', dw: 60, dh: 60, cw: 64, ch: 64 },
      PLANTER: { family: 'deco', shape: 'circle', cr: 24, dw: 42, dh: 42 }
    } };
    root.AK_WORLD3D = { _state: { scene: scB } };
    BUILDS.on = true; BUILDS.sig = null; BUILDS.at = 0; BUILDS.ids = [];
    chk('syncBuilds ran', syncBuilds({ zoneId: 'HOME_TURF' }, true) === true);
    var bs = buildsStats();
    eq('structures instanced: 3 pieces in this district', bs.props, 3);
    eq('two types present -> two InstancedMeshes', bs.types, 2);
    eq('actual draw calls = one per type', bs.actualCalls, 2);
    eq('naive would be one per piece', bs.naiveCalls, 3);
    var wallF = get('akbuilds_WALL');
    chk('WALL field exists and is built', !!wallF && wallF.built === true);
    eq('WALL field holds both walls', wallF.mesh.count, 2);
    eq('each structure field is 1 draw call', estimateDrawCalls(wallF.mesh), 1);
    chk('structure meshes are in the world3d scene', scB.children.indexOf(wallF.mesh) >= 0);
    // rot 0..3 quarter turns -> a real yaw in the instance matrix
    var mw = new THREE.Matrix4(); wallF.mesh.getMatrixAt(1, mw);
    var qw = new THREE.Quaternion(); mw.decompose(new THREE.Vector3(), qw, new THREE.Vector3());
    var yaw = new THREE.Euler().setFromQuaternion(qw, 'YXZ').y;
    eq('rot:1 becomes a 90 degree yaw', Math.abs(yaw), Math.PI / 2, 1e-6);
    // The two independent gates that keep this off the per-frame budget. force:true deliberately
    // bypasses the signature (AK_INSTANCE.builds.sync() defaults to forcing, so a manual poke
    // always rebuilds), so each gate has to be exercised on its own or a pass means nothing.
    chk('4Hz throttle blocks a same-tick re-sync', syncBuilds({ zoneId: 'HOME_TURF' }, false) === false);
    BUILDS.at = 0;   // defeat the throttle so the NEXT call is gated purely by the signature
    chk('unchanged signature does no work', syncBuilds({ zoneId: 'HOME_TURF' }, false) === false);
    BUILDS.at = 0;
    builds.push({ type: 'WALL', x: 256, y: 128, rot: 2, zone: 'HOME_TURF' });
    chk('a new structure changes the signature and rebuilds', syncBuilds({ zoneId: 'HOME_TURF' }, false) === true);
    eq('the new wall is in the field', get('akbuilds_WALL').mesh.count, 3);
    eq('still one draw call for all three walls', estimateDrawCalls(get('akbuilds_WALL').mesh), 1);
    BUILDS.at = 0;
    chk('a district with no structures clears to zero fields',
      syncBuilds({ zoneId: 'NEON_HEIGHTS' }, false) === true && buildsStats().props === 0);
    // circle-shaped structures merge a real CylinderGeometry, which a box-only merge cannot express
    var cyl = structTemplate(THREE, 'PLANTER', root.AK_BUILDMODE.STRUCT.PLANTER);
    chk('circle structures build from CylinderGeometry', !!cyl && cyl.attributes.position.count > 0, cyl && cyl.attributes.position.count);
    eq('circle template merged 2 parts', cyl.userData.akMerged, 2);
    try { cyl.dispose(); } catch (_e) {}
    root.AK_ECON = prevEcon; root.AK_BUILDMODE = prevBM; root.AK_WORLD3D = prevW3;
    BUILDS.on = false;

    // --- report ----------------------------------------------------------------------------
    var rep = report();
    chk('report counts live fields', rep.fields === list().length, rep.fields);
    chk('report saved >= 0', rep.saved >= 0, rep.saved);

    clear(null);
    chk('clear() disposed everything', list().length === 0, list().length);

    return { ok: ok, lines: out };
  }

  function _useEngineLocal(T) { _engine = T || null; _scratch = null; }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akinstance.js` -- imports the REAL vendored r160 and asserts
 * against it. No mocks: a stubbed THREE would happily "pass" a merge that three itself rejects,
 * and that is precisely the class of bug that has shipped here before. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  import('../assets/vendor/three.module.min.js').then(function (T) {
    var r = module.exports.selfTest(T);
    r.lines.forEach(function (l) { console.log(l); });
    console.log(r.ok ? 'ALL PASS' : 'FAILURES PRESENT');
    process.exit(r.ok ? 0 : 1);
  }, function (e) {
    console.log('vendor three not importable:', e && e.message);
    process.exit(1);
  });
}
