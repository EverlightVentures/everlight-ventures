/* ALLEY KINGZ -- AK_BLDMASS: real building massing for the 3D hub.  AK-BLDMASS 2026-07-19.
 *
 * WHY THIS EXISTS
 * Every hub building was ONE BoxGeometry with a facade photo on its +z face. Measured at the live
 * camera pitch (~52 deg above horizontal) that reads as a photo taped to a cube, for two reasons:
 *   1. the ROOF is the most visible face at this angle and a flat-shaded top says "slab", and
 *   2. a single box has exactly one silhouette -- no ledge, no parapet, nothing to catch light,
 *      so no matter how good the facade texture gets, the shape underneath stays a cube.
 * The gap analysis put numbers on it: the whole visible world was 50 triangles.
 *
 * THE CONTRACT -- ADDITIVE, NEVER DESTRUCTIVE
 * decorate() does NOT touch the caller's mesh, its geometry, or its material array. The facade lane
 * owns that array (BoxGeometry order [+x,-x,+y,-y,+z,-z]; index 4 = facade, index 2 = roof) and this
 * lane owns everything ADDED AROUND it. Both compose: swap the roof texture and the parapet still
 * fits; add a parapet and the facade is untouched. This is deliberate -- these two changes shipped
 * concurrently and a replace-the-box design would have silently voided the roof-texture wiring.
 *
 * Everything here is BoxGeometry. No new textures, no loader, no async. Cheap on a phone, and the
 * win is silhouette, which is a shape problem, not a pixel problem.
 */
window.AK_BLDMASS = (function () {
  'use strict';

  // Deterministic per-building pseudo-random, so a given building looks the SAME every load and
  // across sessions. Math.random() here would make the skyline shimmer on every re-enter.
  function hash(str) {
    var h = 2166136261, s = String(str || 'x');
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function rngFor(seed) {
    var s = hash(seed) || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  // Palette: the roof//detail furniture is grimier and a touch cooler than the facade so the eye
  // reads it as separate material, not as more building.
  var C_PARAPET = 0x24242c, C_TRIM = 0x1b1b22, C_METAL = 0x3a3d46, C_RUST = 0x4a3a2e, C_DARK = 0x15151b;

  /* box() does NOT create a Mesh -- it records a box into a list which build() later MERGES into a
   * single geometry. That distinction is the whole performance story of this module:
   *   naive  -> ~15 detail meshes x 29 buildings = ~435 extra DRAW CALLS
   *   merged -> 1 draw call per building
   * The triangle count is identical either way (~5k, nothing to a GPU). What costs on a phone is the
   * per-call state change and CPU overhead, and this game already runs close to the context limit
   * (phones evict WebGL contexts around 8, which is why AK_R3D is a hard singleton). Merging is only
   * possible because every detail box shares ONE material -- so the colour is baked into a per-vertex
   * attribute and the material runs with vertexColors:true instead of one material per tint.
   */
  function box(THREE, w, h, d, color, x, y, z, sink) {
    sink.push({ w: w, h: h, d: d, c: color, x: x, y: y, z: z });
  }

  // Merge every recorded box into ONE BufferGeometry with vertex colours.
  // toNonIndexed() sidesteps index-offset bookkeeping; a box goes 24 -> 36 verts, which is a
  // rounding error at this scale and removes a whole class of off-by-one bugs.
  function mergeBoxes(THREE, boxes) {
    if (!boxes.length) return null;
    var pos = [], nor = [], col = [];
    for (var i = 0; i < boxes.length; i++) {
      var b = boxes[i];
      var g = new THREE.BoxGeometry(b.w, b.h, b.d);
      var ng = (typeof g.toNonIndexed === 'function') ? g.toNonIndexed() : g;
      var p = ng.attributes.position, n = ng.attributes.normal;
      var r = ((b.c >> 16) & 255) / 255, gg = ((b.c >> 8) & 255) / 255, bb = (b.c & 255) / 255;
      for (var v = 0; v < p.count; v++) {
        pos.push(p.getX(v) + b.x, p.getY(v) + b.y, p.getZ(v) + b.z);
        nor.push(n.getX(v), n.getY(v), n.getZ(v));
        col.push(r, gg, bb);
      }
      try { g.dispose(); if (ng !== g) ng.dispose(); } catch (_e) {}
    }
    var out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    out.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return out;
  }

  /* decorate(THREE, mesh, spec) -> THREE.Group of detail meshes in WORLD space.
   * mesh  : the existing building box (read only -- position + geometry params)
   * spec  : the zone building record ({id,x,y,w,h,col,...}) -- used for the stable seed
   * The returned group is NOT added to any scene; the caller adds it, so the caller keeps
   * full control of scene membership and disposal. Returns null if anything is missing,
   * because a missing detail layer must never take the building itself down with it.
   */
  function decorate(THREE, mesh, spec) {
    if (!THREE || !mesh || !mesh.geometry || !mesh.geometry.parameters) return null;
    var P = mesh.geometry.parameters;
    var W = P.width, H = P.height, D = P.depth;              // the box we are dressing
    if (!(W > 0 && H > 0 && D > 0)) return null;

    var g = [];   // sink of box records -- merged into ONE geometry at the end (see box/mergeBoxes)
    var cx = mesh.position.x, cz = mesh.position.z;          // building centre in world
    var top = mesh.position.y + H / 2;                       // world Y of the roof surface
    var rnd = rngFor((spec && spec.id) || (cx + 'x' + cz));

    // ---- 1. PARAPET -------------------------------------------------------------------
    // A low wall around the roof edge. This is the single highest-value addition at a tilted
    // camera: it turns the roof from a painted lid into a container with walls, and it gives
    // the roofline a real, lit edge instead of a hard texture boundary.
    var pw = Math.max(3, Math.min(W, D) * 0.045);            // parapet thickness
    var ph = Math.max(6, H * 0.05);                          // parapet height
    var py = top + ph / 2;
    box(THREE, W, ph, pw, C_PARAPET, cx, py, cz - D / 2 + pw / 2, g);   // front (camera side)
    box(THREE, W, ph, pw, C_PARAPET, cx, py, cz + D / 2 - pw / 2, g);   // back
    box(THREE, pw, ph, D, C_PARAPET, cx - W / 2 + pw / 2, py, cz, g);   // left
    box(THREE, pw, ph, D, C_PARAPET, cx + W / 2 - pw / 2, py, cz, g);   // right

    // ---- 2. CORNICE ------------------------------------------------------------------
    // A thin overhanging ledge just under the parapet. Real buildings have one, and it reads
    // as a dark horizontal line that separates wall from roof -- cheap, and it stops the
    // facade texture from running straight into the sky.
    var co = Math.max(2, pw * 0.9);
    box(THREE, W + co * 2, Math.max(3, H * 0.018), D + co * 2, C_TRIM, cx, top - 1, cz, g);

    // ---- 3. BASE PLINTH ---------------------------------------------------------------
    // Buildings that meet the ground with a slightly wider base look planted; ones that don't
    // look like they are floating or clipped into the plane.
    var bh = Math.max(4, H * 0.035);
    box(THREE, W + co * 1.6, bh, D + co * 1.6, C_DARK, cx, mesh.position.y - H / 2 + bh / 2, cz, g);

    // ---- 4. ROOF FURNITURE ------------------------------------------------------------
    // AC units / vents / a water tank. This is what sells "lived-in" from above. Kept inside
    // the parapet so nothing pokes through the walls we just built.
    var innerW = W - pw * 2 - 4, innerD = D - pw * 2 - 4;
    var units = 1 + Math.floor(rnd() * 3);                   // 1-3 AC boxes
    for (var i = 0; i < units; i++) {
      var uw = Math.max(8, Math.min(innerW * 0.30, 26 + rnd() * 14));
      var ud = Math.max(8, Math.min(innerD * 0.45, 18 + rnd() * 12));
      var uh = 8 + rnd() * 10;
      var ux = cx + (rnd() - 0.5) * Math.max(0, innerW - uw);
      var uz = cz + (rnd() - 0.5) * Math.max(0, innerD - ud);
      box(THREE, uw, uh, ud, C_METAL, ux, top + uh / 2, uz, g);
      // vent cap -- a smaller box on top, so the unit has two tones instead of one flat face
      box(THREE, uw * 0.5, Math.max(2, uh * 0.22), ud * 0.5, C_TRIM, ux, top + uh + uh * 0.11, uz, g);
    }

    // Water tank on bigger roofs only -- a squat cylinder-ish box on stilts. Skipped on small
    // buildings because it would dominate them.
    if (W > 130 && D > 60 && rnd() > 0.45) {
      var tw = Math.min(34, W * 0.22), th = 26 + rnd() * 12;
      var tx = cx + (rnd() - 0.5) * (innerW - tw), tz = cz + (rnd() - 0.5) * (innerD - tw);
      var legH = 10;
      box(THREE, tw * 0.16, legH, tw * 0.16, C_TRIM, tx - tw * 0.32, top + legH / 2, tz - tw * 0.32, g);
      box(THREE, tw * 0.16, legH, tw * 0.16, C_TRIM, tx + tw * 0.32, top + legH / 2, tz + tw * 0.32, g);
      box(THREE, tw, th, tw, C_RUST, tx, top + legH + th / 2, tz, g);
      box(THREE, tw * 1.12, Math.max(3, th * 0.10), tw * 1.12, C_TRIM, tx, top + legH + th, tz, g);
    }

    // ---- 5. SETBACK / STAIR HEAD ------------------------------------------------------
    // Tall buildings get a smaller upper volume: a roof stair bulkhead, or on the tallest a
    // genuine setback storey. This breaks the "every building is one extruded rectangle"
    // rhythm that makes a skyline read as a bar chart.
    if (H > 150) {
      var sw = W * (0.30 + rnd() * 0.16), sd = Math.max(14, D * 0.5), sh = 18 + rnd() * 16;
      var sx = cx + (rnd() - 0.5) * (W - sw) * 0.55;
      box(THREE, sw, sh, sd, C_PARAPET, sx, top + ph + sh / 2, cz, g);
      box(THREE, sw + co, Math.max(3, sh * 0.12), sd + co, C_TRIM, sx, top + ph + sh, cz, g);
    }

    // ---- 6. FACADE LEDGES -------------------------------------------------------------
    // Two or three horizontal string courses down the camera-facing wall. At this pitch they
    // catch the directional light and give the facade actual relief instead of one flat plane.
    var bands = H > 150 ? 3 : 2;
    for (var bnd = 1; bnd <= bands; bnd++) {
      var byv = mesh.position.y - H / 2 + (H * bnd / (bands + 1));
      box(THREE, W + 2, Math.max(2, H * 0.012), 3, C_TRIM, cx, byv, cz - D / 2 - 1.2, g);
    }

    // Collapse every recorded box into a single mesh: 1 draw call for this building's whole
    // detail set instead of one per box. vertexColors carries the per-box tint.
    var geo = mergeBoxes(THREE, g);
    if (!geo) return null;
    var out = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ vertexColors: true }));
    out.userData.akMassFor = (spec && spec.id) || null;
    out.userData.akBoxCount = g.length;
    return out;
  }

  return { decorate: decorate, _rngFor: rngFor };
})();
