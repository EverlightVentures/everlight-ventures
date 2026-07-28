/* ALLEY KINGZ -- AK_GROUND: ground that reads as ground.  AK-GROUND 2026-07-20.
 *
 * OPERATOR: "the floor looks like a tilted photograph, not a surface you stand on."
 *
 * He is describing the render exactly. It IS a photograph: one quad, one picture, stretched.
 * Four separate defects stack up to produce that read, and all four were MEASURED before a line
 * of this file was written. Numbers first, because three of the four are counter-intuitive.
 *
 * DEFECT 1 -- THE PLATE IS PORTRAIT ART ON A LANDSCAPE PLANE. 91.1% HORIZONTAL STRETCH.
 *   Every district plate on disk was measured (400 files under assets/maps/, mixed formats --
 *   259 are JPEG despite the .png extension, which is why a PNG-header-only scan silently sees
 *   only 141 of them and must not be trusted):
 *       259 x 1248x1824   141 x 832x1216   ONE distinct aspect: 0.6842
 *   The plane is world3d.js:823 PlaneGeometry(S.worldW, S.worldH) = 1700 x 1300, aspect 1.3077.
 *   Ground texel aspect = (1700/832) / (1300/1216) = 2.0433 / 1.0691 = 1.9112.
 *   So every painted circle in the art renders as an ellipse 1.91x too wide. That is not a
 *   subtle tell. It is THE tell, and it is identical for both pixel sizes because the aspect is
 *   the same 0.6842 for all 400.
 *
 * DEFECT 2 -- TEXEL DENSITY IS ABOUT A TENTH OF WHAT A SURFACE NEEDS.
 *   832 texels across 1700 units = 0.489 texels/unit in x. The hero is 60 units tall
 *   (RULE 6: units are PIXELS here, not metres), so one hero-height of ground carries 29 texels
 *   across. At the SHIPPING camera that is fatal: tpp is world3d.js:159 phi=78, dist=175, eye=60,
 *   i.e. the eye sits 175*cos(78) + 60 = 96 units up and 171 behind. That is a grazing view.
 *   The ground fills the bottom half of the frame at a few dozen units away, where 29 texels per
 *   hero-height is a blur with no material in it. (The stale phi=52/dist=620 numbers in the
 *   AK-APRON comment above buildApron predate AK-CAMWALK; do not size anything off them.)
 *
 * DEFECT 3 -- THE PAINTED ART IS PSEUDO-3D, LYING FLAT.
 *   This one was settled by LOOKING, not by statistics, and the statistics would have lied.
 *   Gradient-energy anisotropy on the_lot/L01_core is 1.045 vertical/horizontal, i.e. the art
 *   measures as very nearly direction-free. It is not. Rendered and inspected, the plate is a
 *   Clash-style base layout: painted buildings drawn with visible SIDE walls and baked drop
 *   shadows falling consistently to the lower left. Those painted buildings are laid flat on the
 *   floor and then viewed at phi=78, while REAL boxes (world3d.js:869 buildBuildings) stand up
 *   nearby with real fog on them. Two incompatible lighting models in one frame is what makes
 *   the eye classify the floor as a picture.
 *   *** THIS IS WHY THE PLATE IS NOT ROTATED 90 DEGREES. *** The aspect math loves the rotation:
 *   turning 832x1216 into 1216x832 drops the mismatch from 91.1% to 10.5% and would crop only
 *   10.5% of the art instead of 47.7%. It was rendered side by side and rejected on sight -- it
 *   lays every painted building on its side and swings the baked shadows 90 degrees off the real
 *   DirectionalLight at world3d.js:(buildLights) position (600, 900, 400). An 11-point-better
 *   aspect number is not worth art that is visibly on its side. Measured does not mean numeric.
 *
 * DEFECT 4 -- TWO TRIANGLES CANNOT TAKE SHADING.
 *   PlaneGeometry(1700, 1300, 1, 1) is 4 vertices and 2 triangles, and the material is
 *   MeshBasicMaterial, which is unlit by definition. So the entire 2.21 million square units of
 *   district floor carries exactly ONE tonal value per texel with zero large-scale variation.
 *   Real ground is never uniform: it has damp patches, wear, oil, tyre polish. Perfect uniformity
 *   is itself a strong "this is printed" cue, independent of resolution.
 *
 * ---------------------------------------------------------------------------------------------
 * WHAT THIS MODULE DOES. THREE LAYERS, ONE EXTRA DRAW CALL.
 *
 * A) ASPECT FIX, ENCODED IN THE UV ATTRIBUTE -- NOT IN texture.repeat/offset.
 *    This is the load-bearing integration decision. world3d.js:834-844 loads the plate
 *    ASYNCHRONOUSLY and, in its callback, writes material.map / material.color / needsUpdate.
 *    If the aspect fix lived on the texture (tex.repeat / tex.offset) this module would be racing
 *    that callback for ownership of an object world3d creates and I am not allowed to edit
 *    (RULE 9). The UV attribute belongs to the GEOMETRY, and that callback never touches
 *    geometry. So the fix is applied once, up front, and the async load lands on top of it and
 *    just works. No polling required for correctness, no ownership conflict, no ordering bug.
 *    Cover fit, centred: u spans the art's full width, v keeps the middle 52.322% of its height.
 *      texels/unit x = 832 * 1.00000 / 1700 = 0.48941
 *      texels/unit z = 1216 * 0.52322 / 1300 = 0.48942     ratio 1.0000, square texels.
 *    Cost: 47.68% of the art's height is cropped. That is the honest price and it is the right
 *    trade here because the subject matter of these plates is CENTRED (the base layout sits in
 *    the middle with dirt and vegetation margins), so a centre crop eats margin, not content.
 *    All UVs stay inside [0,1], so the plate's default ClampToEdge wrapping is never reached and
 *    no edge texel is ever smeared. That is why 'cover' is safe and 'contain' (which needs UVs
 *    outside [0,1] and DOES smear the border) is available but not the default.
 *
 * B) TILED SURFACE DETAIL -- AUTHORED ART, NOT GENERATED ART.
 *    assets/hub/roofs/roof_gravel.png, 256x256, already on disk, already authored, already
 *    shipped, and already fetched by this game (world3d.js:952 maps these onto building roofs
 *    with exactly this RepeatWrapping idiom at ~128 world-units per repeat). Reusing it at the
 *    SAME 128 units/tile is deliberate: the street and the rooftops then share one material
 *    scale, and nothing new has to be authored, downloaded, or invented.
 *      256 texels / 128 units = 2.000 texels/unit = 120 texels per hero-height.
 *      That is 4.09x the plate's best-case density and 6.8x its stretched x density.
 *    It goes ON TOP at 14%, so the authored plate keeps 86% of the composite. RULE 10: the art is
 *    not replaced, it is not moved, and after the gain below it is not even re-exposed. It gets
 *    grain laid into it, which is what a real street is -- a surface with grit settled into it.
 *    TWO THINGS HERE WERE WRONG UNTIL A RENDER SAID SO, and both are worth knowing about:
 *      1. The obvious tile (roof_asphalt) is roofing FELT and carries horizontal seams. Under a
 *         phi=78 grazing camera it striped the whole district. roof_gravel measures isotropic
 *         (dy/dx 0.990) and does not. See CFG.detailUrl.
 *      2. These tiles are night art, several times darker than the plates, so blending one in at
 *         face value cost 14% of the district's brightness -- a detail layer silently regrading
 *         the operator's art. A linear gain fixes it to a 0.0% shift. See CFG.detailGain.
 *
 * C) SEEDED VERTEX-COLOUR VARIATION ON A SUBDIVIDED PLANE.
 *    48 x 36 segments = 1813 vertices, 3456 triangles, up from 4 and 2. For scale: one town-hall
 *    GLB is ~100k triangles, so the entire district floor now costs 3.5% of ONE building. Quads
 *    come out 35.42 x 36.11 units, near-square, which matters because a stretched quad grid makes
 *    interpolated vertex colour band along the long axis.
 *    Two octaves of seeded value noise (4x3 and 10x8 cells) at +/-8% brightness. RULE 7: seeded
 *    off the zone id through the SAME FNV-1a hash as akclutter.js:119, bldmass.js:24,
 *    akinstance.js:104 and akworldgen.js:113, so this district's wear pattern is bit-identical on
 *    every reload and different from the next district's. Math.random() here would make the floor
 *    shimmer on re-entry, which reads as a rendering fault, not as randomness.
 *    The noise field is MEAN-NORMALISED before it is written: the realised mean is measured and
 *    divided out, so mean vertex colour is 1.000000 and the art's overall tone is provably
 *    unchanged. Only the local variation is new. selfTest asserts this to 1e-6.
 *    It also breaks up the tile repeat in (B): 13.3 x 10.2 repeats of one 256px tile would
 *    otherwise read as a visible grid, and a low-frequency brightness field at a different,
 *    non-commensurate scale is the cheapest known fix for that.
 *
 * NOT DONE ON PURPOSE -- HEIGHT DISPLACEMENT. Subdividing invites displacing y for real surface
 * relief. It is wrong here: the hero is ground-locked at y=0 (world3d.js:822 sets the plate to
 * y=0 and the hero rides that plane), so any bump would sink his feet or float them. Colour only.
 *
 * FOG. Both layers use the material default fog:true, so both fade into
 * world3d.js:1428 Fog(tint, 420, 1750) at the same rate as the plate always did. The detail
 * overlay therefore cannot introduce a horizon seam: past 1750 units it and the plate are both
 * fully fog, exactly as the AK-APRON skirt below them already relies on.
 *
 * NO em-dashes anywhere in this file (hook law, use --).
 */
(function (root) {
  'use strict';

  var VER = 'AK-GROUND-1.0.0';

  /* =========================================================================================
   * PURE CORE. No THREE, no DOM. This half is node-requireable and is what the headless test at
   * the bottom exercises without a GPU.
   * ========================================================================================= */

  /* Byte-identical to akclutter.js:119 / bldmass.js:24 / akinstance.js:104 / akworldgen.js:113 ON
   * PURPOSE. A shared hash means "HOME_TURF" seeds the same integer in every lane, so the ground
   * wear, the clutter placement and the building massing for one district agree without any of
   * them having to pass values to each other. */
  function hash(str) {
    var h = 2166136261, s = String(str || 'x');
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }

  // Integer lattice hash -> 0..1. Math.imul is required for a 32-bit-exact mix; it has been in
  // every browser since 2013 and anything running three r160 + WebGL2 has it. The guard exists so
  // a node build without it degrades to a poorer but still DETERMINISTIC mix rather than throwing.
  var _imul = Math.imul || function (a, b) { return (a * b) | 0; };
  function latticeHash(ix, iz, seed) {
    var h = ((ix | 0) * 374761393 + (iz | 0) * 668265263 + (seed | 0) * 1442695041) | 0;
    h = _imul(h ^ (h >>> 13), 1274126177);
    h = (h ^ (h >>> 16)) >>> 0;
    return h / 4294967296;
  }

  // Smoothstep. Plain linear interpolation between lattice points leaves visible creases along
  // the cell boundaries once the field is stretched over 35-unit quads.
  function smooth(t) { return t * t * (3 - 2 * t); }

  /* One octave of seeded value noise over the unit square. cx/cz are cells across the world, so
   * cx=4 over worldW=1700 is a 425-unit feature -- about 7 hero-heights, the size of a damp patch
   * or a worn vehicle track. Deliberately much larger than the 128-unit detail tile in (B): if the
   * two scales were close the noise would beat against the tile instead of hiding it. */
  function vnoise(u, v, cx, cz, seed) {
    var x = u * cx, z = v * cz;
    var x0 = Math.floor(x), z0 = Math.floor(z);
    var fx = smooth(x - x0), fz = smooth(z - z0);
    var a = latticeHash(x0,     z0,     seed), b = latticeHash(x0 + 1, z0,     seed);
    var c = latticeHash(x0,     z0 + 1, seed), d = latticeHash(x0 + 1, z0 + 1, seed);
    var top = a + (b - a) * fx, bot = c + (d - c) * fx;
    return top + (bot - top) * fz;
  }

  /* ------------------------------------------------------------------------------------------
   * TUNABLES. Every default here is a measured number, not a preference. Changing one is fine;
   * changing one without re-measuring is how the plate ended up 1.91x wide in the first place.
   * ---------------------------------------------------------------------------------------- */
  var CFG = {
    fit:          'cover',   // 'cover' | 'contain' | 'stretch'. See (A) above for why cover wins.
    segX:         48,        // 1700/48 = 35.42 units per quad
    segZ:         36,        // 1300/36 = 36.11 units per quad -- within 2% of square, see (C)
    noiseAmp:     0.08,      // +/-8% brightness. At 0.15 it reads as blotches, at 0.03 it is invisible.
    /* WHICH AUTHORED TILE, AND WHY GRAVEL RATHER THAN THE OBVIOUS ASPHALT.
     * Four tileable authored textures already ship (assets/hub/roofs/, 256x256, all four already
     * used for building roofs at world3d.js:952). "Asphalt" is the obvious pick for a street and
     * it is the WRONG one. Measured gradient anisotropy dy/dx, where 1.0 is direction-free:
     *     roof_asphalt     1.249    relStd 0.2197   linMean 0.01977
     *     roof_gravel      0.990    relStd 0.2663   linMean 0.04187
     *     roof_tar         1.095    relStd 0.2414   linMean 0.02585
     *     roof_corrugated  0.222    relStd 0.2134   linMean 0.10199
     * roof_asphalt is roofing FELT: it carries horizontal seams (25% more gradient across rows
     * than down columns), and laid flat under a phi=78 grazing camera those seams read as regular
     * stripes marching to the horizon. That is not a subtle defect either -- it showed up plainly
     * in magnified crops of the test render. roof_corrugated is worse and obviously so, being
     * literal corrugated metal at dy/dx 0.222.
     * roof_gravel wins on all three axes that matter: it is the most direction-free of the four
     * (0.990, so it cannot form stripes at any camera angle), it has the HIGHEST relative
     * contrast (0.2663, so it delivers the most grain per unit of opacity spent), and it is the
     * brightest of the three dark ones, which means it needs the least gain to be tone neutral
     * and therefore has the most headroom before highlights clip. */
    detailUrl:    'assets/hub/roofs/roof_gravel.png',
    detailTile:   128,       // world units per 256px tile -> 2.000 texels/unit. Matches the roof idiom.
    /* detailOpacity -- PICKED OFF A RENDERED LADDER, NOT OFF A FEELING.
     * Alpha blending is a lerp, so every point of opacity buys grain and spends plate contrast.
     * Measured at the shipping tpp camera, on the flattest 120x120 patch of ground in frame
     * (which is where a surface either reads as a surface or does not) against whole-frame
     * contrast:
     *     opacity   flat-patch |dx|   whole-frame std   luminance
     *       0.00      0.2476  (1.00x)     46.92          baseline
     *       0.14      0.5922  (2.39x)     39.86          +0.0%
     *       0.22      0.8313  (3.36x)     35.98          +0.0%
     * 0.22 buys more grain but the frame visibly hazes over: the plate's own painted detail is
     * being washed out faster than grit is being added. 0.14 more than doubles real surface
     * texture while leaving 86% of the authored art's contrast intact, and that is the trade this
     * lane is supposed to make. Retune with AK_GROUND.setDetail(op) against the same numbers. */
    detailOpacity: 0.14,
    /* detailGain -- A LINEAR-SPACE MULTIPLIER > 1, AND THE RENDER IS WHY IT EXISTS.
     * The first cut alpha-blended roof_asphalt over the plate with a plain darkening tint and it
     * cost 14% of the district's brightness. Measured cause: that tile is NIGHT rooftop art and it
     * is very dark. In linear space its mean is 0.01977 while the plates average 0.1725
     * (measured: the_lot L01_core 0.17866, golden_industrial L01_works 0.16627). It is roughly 9x
     * darker than what it is being laid over, so ANY opacity of it is an exposure cut wearing a
     * texture's clothes -- a detail layer that silently regrades the operator's art.
     * Multiplying it up to the plate's own mean makes the overlay tonally neutral: it then adds
     * only variance, which is all a grain layer should ever do.
     *   gain = plateLinearMean / tileLinearMean = 0.1725 / 0.04187 = 4.12
     * Plate means measured per district: the_lot L01_core 0.17866, golden_industrial L01_works
     * 0.16627, which want 4.27 and 3.97, so one constant lands both inside 4% of their original
     * brightness and the overlay contributes under 1% of net luminance either way.
     * CLIPPING: gravel's brightest linear texel is 0.53948 and 0.53948 * 4.12 = 2.22, so the very
     * top of its range does saturate -- but that is 0.077% of texels, roughly 50 of 65536, and
     * they are the specular glints on wet stone that read as white anyway. Checked rather than
     * assumed, because the same check is what ruled out driving a unit-mean modulation (gain
     * 23.9), which would have clipped 46% of the texture and destroyed the grain it was adding.
     * Applied through Color.setRGB, which writes the working (linear) space directly and, unlike
     * a hex literal, is allowed to exceed 1.0. */
    detailGain:   4.12,
    detailLift:   0.25,      // world units above the plate. Plate 0, paths 0.6, apron -0.5.
    watchFrames:  240        // ~4s of rAF to notice the real plate dimensions. See applyWhenLoaded.
  };

  // Measured constant, used ONLY as the pre-load assumption. All 400 plates under assets/maps/
  // share this aspect, so the fit is already correct before the texture arrives; the watcher in
  // (D) below re-fits for free if art ever ships at a different shape.
  var PLATE_ASPECT = 832 / 1216;   // 0.684210...

  /* THE ASPECT SOLVER. Returns the uv rectangle of the SOURCE IMAGE that should be shown on the
   * plane, plus the resulting texel densities so callers (and the self test) can assert on them
   * instead of trusting the arithmetic. Pure, no side effects, node-testable. */
  function fitUv(texAspect, worldW, worldH, mode) {
    var Aa = texAspect > 0 ? texAspect : PLATE_ASPECT;
    var Ap = worldW / worldH;
    var u0 = 0, u1 = 1, v0 = 0, v1 = 1, f;
    if (mode === 'stretch') {
      // The shipped behaviour. Kept reachable so a before/after can be rendered from ONE build.
    } else if (mode === 'contain') {
      // Whole image visible, plane not filled. Needs UVs OUTSIDE [0,1], which with the plate's
      // default ClampToEdge smears the border texels across the empty bands. Honest, ugly, and
      // exactly why it is not the default.
      if (Aa < Ap) { f = Aa / Ap; u0 = (1 - 1 / f) / 2; u1 = 1 - u0; }
      else         { f = Ap / Aa; v0 = (1 - 1 / f) / 2; v1 = 1 - v0; }
    } else {
      // COVER. Fill the plane, crop the overflow, centred. Never leaves [0,1].
      if (Aa < Ap) { f = Aa / Ap; v0 = (1 - f) / 2; v1 = 1 - v0; }   // art too tall  -> crop height
      else         { f = Ap / Aa; u0 = (1 - f) / 2; u1 = 1 - u0; }   // art too wide  -> crop width
    }
    var spanU = u1 - u0, spanV = v1 - v0;
    // Density is expressed per source-texel of a 1-unit-wide image, so it is resolution
    // independent; multiply by the real pixel width to get texels/unit.
    return {
      u0: u0, u1: u1, v0: v0, v1: v1, spanU: spanU, spanV: spanV,
      // stretch = how many times wider a texel is in x than in z. 1.0 is correct.
      stretch: (spanV / worldH) === 0 ? 0 : ((worldW / (Aa * spanU)) / (worldH / spanV)),
      keptArea: spanU * spanV,
      croppedPct: 100 * (1 - Math.min(1, spanU) * Math.min(1, spanV))
    };
  }

  // Texels per world unit for a real pixel size, so the density claims in the header can be
  // asserted rather than asserted-at.
  function density(texW, texH, worldW, worldH, uv) {
    return { x: texW * uv.spanU / worldW, z: texH * uv.spanV / worldH };
  }

  /* The vertex-colour field. Separated from the THREE call so it can be tested for determinism
   * and for mean-preservation with no engine present. Returns a Float32Array of rgb triples. */
  function shadeField(nx, nz, seedStr, amp) {
    var seed = hash(seedStr) | 0;
    var n = nx * nz, raw = new Float64Array(n), i, ix, iz, u, v, sum = 0;
    for (iz = 0; iz < nz; iz++) {
      for (ix = 0; ix < nx; ix++) {
        u = nx > 1 ? ix / (nx - 1) : 0;
        v = nz > 1 ? iz / (nz - 1) : 0;
        // 0.68/0.32 split: the coarse octave carries the read, the fine one keeps it from looking
        // like a gradient ramp. Second seed offset so the octaves are not correlated.
        var s = 0.68 * vnoise(u, v, 4, 3, seed) + 0.32 * vnoise(u, v, 10, 8, (seed + 101) | 0);
        raw[iz * nx + ix] = s; sum += s;
      }
    }
    /* NORMALISE TWICE, AND THE SECOND ONE WAS A TEST FAILURE TALKING.
     *
     * MEAN: value noise does not average to exactly 0.5, so an unnormalised field would silently
     * brighten or darken the operator's art by a percent or two. Subtracting the realised mean
     * makes the mean multiplier exactly 1.0 and tone is provably preserved.
     *
     * AMPLITUDE: the first cut scaled deviations by a fixed 2x on the assumption that raw noise
     * is symmetric about its mean. It is not. Sampled on this 49x37 lattice the realised range
     * came out [0.000, 0.864] about a mean of 0.5506, so the fixed 2x produced 0.9119 .. 1.0502
     * -- a 12% dip where the header promised 8%, and skewed dark. The self test caught it.
     * Dividing by the largest absolute deviation instead makes both guarantees exact and
     * simultaneous: mean is still 1.0 (scaling zero-mean deviations cannot move the mean) and no
     * vertex can leave [1-amp, 1+amp], while at least one vertex reaches the bound so the band is
     * fully used rather than merely respected. */
    var mean = sum / n, maxAbs = 0, dev;
    for (i = 0; i < n; i++) { dev = Math.abs(raw[i] - mean); if (dev > maxAbs) maxAbs = dev; }
    var k = maxAbs > 1e-12 ? (amp / maxAbs) : 0;   // a perfectly flat field stays flat, no divide by zero
    var col = new Float32Array(n * 3);
    for (i = 0; i < n; i++) {
      var g = 1 + (raw[i] - mean) * k;
      if (g < 0) g = 0;
      col[i * 3] = g; col[i * 3 + 1] = g; col[i * 3 + 2] = g;
    }
    return col;
  }

  /* =========================================================================================
   * ENGINE LAYER. Everything below needs THREE. Guarded so a failure leaves the plate exactly as
   * world3d.js built it -- a broken ground is worse than an unimproved one.
   * ========================================================================================= */

  var S = {
    plate: null, overlay: null, geo: null, oGeo: null, oMat: null, oTex: null,
    zone: '', worldW: 0, worldH: 0, fit: '', uv: null, dens: null,
    watch: 0, refit: false, texW: 0, texH: 0, built: 0, tileState: 'none'
  };

  // Rewrite the uv attribute of an existing PlaneGeometry in place. PlaneGeometry lays vertices
  // out row-major from v=1 (far) down to v=0, u=0 to u=1, which is why the v term is inverted:
  // getting this backwards flips the district north/south, which is subtle enough to ship.
  function writeUv(geo, uv) {
    var att = geo.attributes.uv, i, u, v;
    for (i = 0; i < att.count; i++) {
      u = att.getX(i); v = att.getY(i);
      att.setXY(i, uv.u0 + u * uv.spanU, uv.v0 + v * uv.spanV);
    }
    att.needsUpdate = true;
  }

  function disposeOverlay() {
    try {
      if (S.overlay && S.overlay.parent) S.overlay.parent.remove(S.overlay);
      if (S.oGeo && S.oGeo.dispose) S.oGeo.dispose();
      if (S.oTex && S.oTex.dispose) S.oTex.dispose();
      if (S.oMat && S.oMat.dispose) S.oMat.dispose();
    } catch (_e) {}
    S.overlay = null; S.oGeo = null; S.oMat = null; S.oTex = null;
  }

  /* The tiled detail overlay. Parented to the PLATE, not to the scene, and that is the whole
   * disposal story: world3d.js:1546 does scene.remove(W3.ground), which detaches this subtree in
   * the same call. Without the parenting it would be a scene child world3d has never heard of and
   * every district swap would leak one -- the identical "same lifetime as ground but not disposed
   * with it" leak that AK-BLDMASS and AK-APRON both had to be fixed for.
   *
   * PARENT FRAME GOTCHA: the plate carries rotation.x = -PI/2 (world3d.js:826), so in its local
   * frame +Z points at world +Y. A child lifted "up" is therefore position.z = lift, NOT .y, and
   * the child needs no rotation of its own because it inherits the plate's. */
  function buildOverlay(THREE, plate, worldW, worldH) {
    var geo = new THREE.PlaneGeometry(worldW, worldH, 1, 1);   // 2 triangles; it carries no shading
    var mat = new THREE.MeshBasicMaterial({
      transparent: true,
      opacity: CFG.detailOpacity,
      depthWrite: false      // pure decoration: it must never occlude, and it cannot z-fight
    });
    // setRGB, not a hex colour: this value is deliberately > 1 and must land in the working
    // (linear) space unconverted. See the detailGain note in CFG for the measurement.
    try { mat.color.setRGB(CFG.detailGain, CFG.detailGain, CFG.detailGain); } catch (_e) {}
    var mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, 0, CFG.detailLift);   // local +Z == world +Y, see the note above
    mesh.renderOrder = 0;                      // transparent pass already sorts it after the plate
    mesh.frustumCulled = false;                // it is the size of the world; culling it is a coin flip
    plate.add(mesh);
    S.overlay = mesh; S.oGeo = geo; S.oMat = mat;

    /* THE LOADER IS WRAPPED, AND THE HEADLESS TEST IS WHY. three's TextureLoader goes through
     * ImageLoader, which calls document.createElementNS on the spot -- so in ANY DOM-less context
     * (the `node systems/akground.js` harness, a worker, a server-side render) this line throws
     * SYNCHRONOUSLY, before the error callback below can ever fire. Found by running the harness,
     * not by reading the docs. Unwrapped, that exception escapes apply() and skips the overlay
     * teardown, leaving a flat 22% grey wash sitting on the operator's art with no texture in it.
     * Catch it, and fall through to the same disposal path a 404 takes. */
    S.tileState = 'loading';
    try {
      var loader = new THREE.TextureLoader();
      loader.load(CFG.detailUrl, function (tex) {
        try {
          if (!S.oMat) { if (tex.dispose) tex.dispose(); return; }   // disposed while in flight
          try { tex.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
          tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
          /* ANISOTROPY -- NOT OPTIONAL AT THIS CAMERA, AND THE MAGNIFIED CROPS PROVED IT.
           * The shipping camera is tpp phi=78, which is 12 degrees off horizontal: the ground is
           * viewed at a hard grazing angle where one screen pixel covers many texels along z and
           * almost none along x. With the default anisotropy of 1 the mip selection is driven by
           * the WORST axis, so a 128-unit tile collapses into regular horizontal bands marching
           * to the horizon. Rendered and magnified, that is exactly what came back: periodic
           * stripes, not asphalt. Anisotropic filtering is the fix this case exists for.
           * Queried from the live renderer rather than hardcoded, because asking for more than
           * the driver supports is silently ignored on some phones and 16 is not universal.
           * ONE RENDERER LAW: this READS the existing singleton, it never constructs one. */
          var aniso = 8;
          try {
            var R = root.AK_R3D || (root.AK_WORLD3D && root.AK_WORLD3D.renderer && root.AK_WORLD3D.renderer());
            if (R && R.capabilities && R.capabilities.getMaxAnisotropy) {
              aniso = Math.max(1, Math.min(16, R.capabilities.getMaxAnisotropy()));
            }
          } catch (_e) {}
          tex.anisotropy = aniso;
          tex.generateMipmaps = true;
          tex.minFilter = THREE.LinearMipmapLinearFilter;
          // 1700/128 = 13.28 and 1300/128 = 10.16 repeats. Fractional on purpose: rounding to whole
          // tiles would change the material scale per district and break the shared 128-unit idiom.
          // Same idiom and same ~128-unit scale as the roof textures at world3d.js:952.
          tex.repeat.set(worldW / CFG.detailTile, worldH / CFG.detailTile);
          S.oTex = tex;
          S.oMat.map = tex; S.oMat.needsUpdate = true;
          S.tileState = 'ok';
        } catch (_e) {}
      }, null, function () {
        // No tile: drop the overlay entirely rather than leave a flat 22% grey wash over the art.
        // A silent no-op mesh that still costs a draw call is the failure mode AK-APRON documented.
        S.tileState = 'missing';
        disposeOverlay();
      });
    } catch (_e) {
      /* Synchronous throw (DOM-less). Keep the mesh so the headless harness can still assert on
       * its parenting, lift and material state, but zero its opacity: without a map this material
       * is a flat grey rectangle, and a flat grey rectangle over the operator's art is strictly
       * worse than no overlay at all. Nothing renders in that environment anyway, so this costs
       * nothing and keeps the browser-visible behaviour safe under an impossible-but-cheap case. */
      S.tileState = 'unavailable';
      try { mat.opacity = 0; } catch (_e2) {}
    }
    return mesh;
  }

  /* (D) THE LATE RE-FIT. apply() runs inside buildGround, BEFORE world3d's TextureLoader has
   * resolved, so the true pixel size is not knowable yet. The initial fit uses PLATE_ASPECT,
   * which is correct for all 400 plates measured today, so this watcher is not needed for
   * correctness -- it is the guard against ART CHANGING SHAPE later without this file being
   * touched. It reads material.map.image, never writes it, so it cannot race world3d's callback.
   * Self-terminating: it stops the moment it sees the image, or after watchFrames. */
  function applyWhenLoaded() {
    if (typeof root.requestAnimationFrame !== 'function') return;
    S.watch = 0;
    (function tick() {
      if (!S.plate || !S.geo) return;                        // torn down under us
      if (++S.watch > CFG.watchFrames) return;               // give up quietly, initial fit stands
      var mp = S.plate.material && S.plate.material.map;
      var img = mp && mp.image;
      if (img && img.width > 0 && img.height > 0) {
        S.texW = img.width; S.texH = img.height;
        var a = img.width / img.height;
        // Only rewrite when the real art disagrees with the assumption by more than a rounding
        // wobble. Re-uploading a 1813-vertex uv buffer for a 0.0001 difference is pure waste.
        if (Math.abs(a - PLATE_ASPECT) > 0.002) {
          S.uv = fitUv(a, S.worldW, S.worldH, S.fit);
          writeUv(S.geo, S.uv);
          S.refit = true;
        }
        S.dens = density(S.texW, S.texH, S.worldW, S.worldH, S.uv);
        return;
      }
      root.requestAnimationFrame(tick);
    })();
  }

  /* ===== THE INTEGRATION POINT =============================================================
   * apply(THREE, plateMesh, zoneId, worldW, worldH)
   *
   * Called from world3d.js buildGround immediately after `W3.scene.add(m); W3.ground = m;`.
   * It does NOT need the scene: the overlay parents to the plate and the plate is already in it.
   * It does NOT touch plate.material, so world3d's async map/color/needsUpdate writes still land.
   * It DOES replace plate.geometry, and disposes the 2-triangle original it replaces.
   * ========================================================================================= */
  function apply(THREE, plate, zoneId, worldW, worldH) {
    if (!THREE || !plate || !plate.geometry) return null;
    var W = worldW > 0 ? worldW : 1700, H = worldH > 0 ? worldH : 1300;

    disposeOverlay();                       // idempotent: a second apply() never stacks overlays
    try { if (S.geo && S.geo !== plate.geometry && S.geo.dispose) S.geo.dispose(); } catch (_e) {}

    var uv = fitUv(PLATE_ASPECT, W, H, CFG.fit);
    var geo = new THREE.PlaneGeometry(W, H, CFG.segX, CFG.segZ);
    writeUv(geo, uv);

    var nx = CFG.segX + 1, nz = CFG.segZ + 1;
    var col = shadeField(nx, nz, 'akground:' + (zoneId || 'HOME_TURF'), CFG.noiseAmp);
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));

    var old = plate.geometry;
    plate.geometry = geo;
    try { if (old && old.dispose) old.dispose(); } catch (_e) {}

    // vertexColors multiplies material.color. Before the plate texture lands that colour is
    // world3d's GROUND_COLOR 0x101018; after, its callback sets it to 0xffffff. The field is
    // mean-1.0 so it is tonally neutral against BOTH, which is why this is safe to set now.
    try { plate.material.vertexColors = true; plate.material.needsUpdate = true; } catch (_e) {}

    S.plate = plate; S.geo = geo; S.zone = zoneId || ''; S.worldW = W; S.worldH = H;
    S.fit = CFG.fit; S.uv = uv; S.texW = 0; S.texH = 0; S.refit = false;
    S.dens = density(832, 1216, W, H, uv);   // provisional, refreshed by the watcher
    S.built++;

    buildOverlay(THREE, plate, W, H);
    applyWhenLoaded();
    return plate;
  }

  // Called from world3d.js disposeScene, just before it removes W3.ground. Safe to call twice and
  // safe to call when nothing was ever built. The overlay would ALSO be taken off the scene by
  // scene.remove(W3.ground) on its own; this is what actually frees its GPU buffers.
  function dispose() {
    disposeOverlay();
    S.plate = null; S.geo = null; S.uv = null; S.dens = null; S.watch = CFG.watchFrames + 1;
    return true;
  }

  function diag() {
    return {
      ver: VER, built: S.built, zone: S.zone, fit: S.fit,
      hasPlate: !!S.plate, hasOverlay: !!S.overlay, hasTile: !!S.oTex, tileState: S.tileState,
      plateTex: S.texW ? (S.texW + 'x' + S.texH) : 'pending', refitFromArt: S.refit,
      uv: S.uv, texelsPerUnit: S.dens,
      texelsPerHero: S.dens ? { x: +(S.dens.x * 60).toFixed(1), z: +(S.dens.z * 60).toFixed(1) } : null,
      detailTexelsPerUnit: 256 / CFG.detailTile,
      tris: CFG.segX * CFG.segZ * 2, verts: (CFG.segX + 1) * (CFG.segZ + 1)
    };
  }

  /* ------------------------------------------------------------------------------------------
   * SELF TEST. Pure-core assertions run with no engine; the geometry assertions run against the
   * REAL vendored three r160 when it is importable. A stubbed THREE would happily pass a uv
   * rewrite that three itself rejects, and that is exactly the class of bug this repo has shipped.
   * ---------------------------------------------------------------------------------------- */
  function selfTest(T) {
    var lines = [], ok = true;
    function say(cond, label, extra) {
      if (!cond) ok = false;
      lines.push((cond ? 'PASS  ' : 'FAIL  ') + label + (extra != null ? '   [' + extra + ']' : ''));
    }
    function near(a, b, eps) { return Math.abs(a - b) <= eps; }
    function eq(label, got, want) { say(got === want, label, 'got ' + got + ' want ' + want); }

    lines.push('--- ' + VER + ' pure core ---');

    // 1. The defect itself, reproduced from the shipped path.
    var st = fitUv(PLATE_ASPECT, 1700, 1300, 'stretch');
    say(near(st.stretch, 1.9112, 0.001), 'shipped stretch fit reproduces the measured 1.9112x defect',
      st.stretch.toFixed(4));
    var dS = density(832, 1216, 1700, 1300, st);
    say(near(dS.x, 0.4894, 0.001) && near(dS.z, 0.9354, 0.001),
      'stretched texel density matches the measured 0.489 x / 0.935 z',
      dS.x.toFixed(4) + ' / ' + dS.z.toFixed(4));

    // 2. Cover fit makes texels square and stays inside [0,1].
    var cv = fitUv(PLATE_ASPECT, 1700, 1300, 'cover');
    say(near(cv.stretch, 1, 1e-9), 'cover fit yields square texels (stretch 1.0)', cv.stretch.toFixed(8));
    say(cv.u0 >= 0 && cv.u1 <= 1 && cv.v0 >= 0 && cv.v1 <= 1,
      'cover fit never leaves [0,1], so ClampToEdge can never smear an edge texel',
      'u ' + cv.u0.toFixed(4) + '..' + cv.u1.toFixed(4) + '  v ' + cv.v0.toFixed(4) + '..' + cv.v1.toFixed(4));
    say(near(cv.spanV, 0.52322, 0.0001), 'cover keeps the measured middle 52.322% of art height',
      cv.spanV.toFixed(5));
    say(near(cv.croppedPct, 47.678, 0.01), 'cover crops the measured 47.678% of the art', cv.croppedPct.toFixed(3));
    var dC = density(832, 1216, 1700, 1300, cv);
    say(near(dC.x, dC.z, 1e-6), 'cover density is equal on both axes', dC.x.toFixed(5) + ' / ' + dC.z.toFixed(5));

    // 3. Both pixel sizes on disk behave identically, because they share one aspect.
    var d1 = density(1248, 1824, 1700, 1300, cv), d2 = density(832, 1216, 1700, 1300, cv);
    say(near(d1.x / d1.z, 1, 1e-6) && near(d2.x / d2.z, 1, 1e-6),
      'both shipped plate sizes (1248x1824, 832x1216) come out square under cover',
      d1.x.toFixed(3) + ' vs ' + d2.x.toFixed(3) + ' texels/unit');

    // 4. The rejected rotation, kept as a number so the decision is auditable.
    var rot = fitUv(1216 / 832, 1700, 1300, 'cover');
    say(rot.croppedPct < cv.croppedPct,
      'rotating 90deg WOULD crop less art (this is why it was tested, and it was rejected on sight: it lays the painted buildings on their side)',
      'rot ' + rot.croppedPct.toFixed(1) + '% vs cover ' + cv.croppedPct.toFixed(1) + '%');

    // 5. Detail density is the actual point of layer B.
    var detail = 256 / CFG.detailTile;
    say(detail / dC.x >= 4, 'tiled detail beats the plate density by at least 4x',
      detail.toFixed(3) + ' vs ' + dC.x.toFixed(3) + ' texels/unit = ' + (detail / dC.x).toFixed(2) + 'x');
    say(near(detail * 60, 120, 0.001), 'tiled detail gives 120 texels per 60-unit hero height', (detail * 60).toFixed(1));

    // 6. Shade field: determinism, tone preservation, amplitude, and per-zone difference.
    var nx = CFG.segX + 1, nz = CFG.segZ + 1, i;
    var A = shadeField(nx, nz, 'akground:HOME_TURF', CFG.noiseAmp);
    var B = shadeField(nx, nz, 'akground:HOME_TURF', CFG.noiseAmp);
    var C = shadeField(nx, nz, 'akground:THE_YARDS', CFG.noiseAmp);
    var same = true, diff = 0, mean = 0, lo = 9, hi = -9;
    for (i = 0; i < A.length; i++) {
      if (A[i] !== B[i]) same = false;
      if (A[i] !== C[i]) diff++;
    }
    for (i = 0; i < A.length; i += 3) { mean += A[i]; if (A[i] < lo) lo = A[i]; if (A[i] > hi) hi = A[i]; }
    mean /= (A.length / 3);
    say(same, 'shade field is deterministic for a seed (RULE 7: no reload shimmer)');
    say(diff > A.length * 0.5, 'a different district gets a different wear pattern', diff + '/' + A.length + ' components differ');
    say(near(mean, 1, 1e-6), 'mean vertex colour is exactly 1.0, so the art tone is provably unchanged', mean.toFixed(9));
    say(lo >= 1 - CFG.noiseAmp - 1e-6 && hi <= 1 + CFG.noiseAmp + 1e-6,
      'variation stays inside the +/-8% band', lo.toFixed(4) + ' .. ' + hi.toFixed(4));
    say(hi - lo > CFG.noiseAmp, 'variation actually uses its range (not a flat field)', (hi - lo).toFixed(4));
    say(near(hi - 1, CFG.noiseAmp, 1e-6) || near(1 - lo, CFG.noiseAmp, 1e-6),
      'amplitude normalisation makes at least one vertex reach the band edge exactly',
      'peak dev ' + Math.max(hi - 1, 1 - lo).toFixed(6));

    // 7. Quad aspect. A stretched quad grid bands the interpolated vertex colour.
    var qx = 1700 / CFG.segX, qz = 1300 / CFG.segZ;
    say(Math.abs(qx / qz - 1) < 0.05, 'subdivision quads are near-square', qx.toFixed(2) + ' x ' + qz.toFixed(2));

    // ---- engine half ------------------------------------------------------------------------
    if (!T || !T.PlaneGeometry) {
      lines.push('SKIP  engine assertions: vendored three not supplied');
      return { ok: ok, lines: lines };
    }
    lines.push('--- engine (real vendored three) ---');

    var plateMat = new T.MeshBasicMaterial({ color: 0x101018 });
    var plateGeo = new T.PlaneGeometry(1700, 1300, 1, 1);
    var plate = new T.Mesh(plateGeo, plateMat);
    plate.rotation.x = -Math.PI / 2;
    plate.position.set(850, 0, 650);
    var scene = new T.Scene();
    scene.add(plate);

    eq('baseline plate really is 2 triangles', plateGeo.attributes.position.count, 4);

    var res = apply(T, plate, 'HOME_TURF', 1700, 1300);
    say(!!res, 'apply returned the plate');
    eq('geometry was replaced with the subdivided plane', plate.geometry.attributes.position.count, nx * nz);
    eq('triangle count is the documented 3456', plate.geometry.index.count / 3, CFG.segX * CFG.segZ * 2);
    say(!!plate.geometry.attributes.color, 'vertex colour attribute is present');
    say(plate.material.vertexColors === true, 'material has vertexColors enabled');

    // uv range must match the solver exactly, and must never leave [0,1].
    var uva = plate.geometry.attributes.uv, umin = 9, umax = -9, vmin = 9, vmax = -9;
    for (i = 0; i < uva.count; i++) {
      var uu = uva.getX(i), vvv = uva.getY(i);
      if (uu < umin) umin = uu; if (uu > umax) umax = uu;
      if (vvv < vmin) vmin = vvv; if (vvv > vmax) vmax = vvv;
    }
    say(near(umin, cv.u0, 1e-5) && near(umax, cv.u1, 1e-5), 'u range matches the cover solve',
      umin.toFixed(5) + '..' + umax.toFixed(5));
    say(near(vmin, cv.v0, 1e-5) && near(vmax, cv.v1, 1e-5), 'v range matches the cover solve',
      vmin.toFixed(5) + '..' + vmax.toFixed(5));
    say(umin >= 0 && umax <= 1 && vmin >= 0 && vmax <= 1, 'no uv escapes [0,1] on the real geometry');

    // The plate keeps its own footprint: this lane must not move or resize the district.
    var pb = plate.geometry.attributes.position, pxmin = 1e9, pxmax = -1e9, pymin = 1e9, pymax = -1e9;
    for (i = 0; i < pb.count; i++) {
      var px = pb.getX(i), py = pb.getY(i);
      if (px < pxmin) pxmin = px; if (px > pxmax) pxmax = px;
      if (py < pymin) pymin = py; if (py > pymax) pymax = py;
    }
    say(near(pxmax - pxmin, 1700, 1e-3) && near(pymax - pymin, 1300, 1e-3),
      'plate still spans exactly 1700 x 1300', (pxmax - pxmin) + ' x ' + (pymax - pymin));
    say(plate.position.x === 850 && plate.position.y === 0 && plate.position.z === 650,
      'plate was not moved (hero is ground-locked to y=0)');

    // Overlay: parented to the plate, lifted in the PLATE frame, and above the plate in WORLD y.
    say(!!S.overlay, 'detail overlay was created');
    say(S.overlay && S.overlay.parent === plate, 'overlay is a CHILD of the plate, so world3d disposal takes it');
    if (S.overlay) {
      plate.updateMatrixWorld(true);
      var wp = new T.Vector3();
      S.overlay.getWorldPosition(wp);
      say(near(wp.y, CFG.detailLift, 1e-4),
        'overlay sits detailLift above the plate in WORLD y (local +Z maps to world +Y under rotation.x=-PI/2)',
        'world y=' + wp.y.toFixed(4));
      say(wp.y > 0 && wp.y < 0.6, 'overlay is above the plate (0) and below the paths layer (0.6)', wp.y.toFixed(3));
      say(S.overlay.material.depthWrite === false && S.overlay.material.transparent === true,
        'overlay cannot z-fight or occlude (depthWrite off, transparent on)');
      // The gain is the whole reason the overlay is tone-neutral. A hex colour cannot carry it.
      say(S.overlay.material.color.r > 1.5,
        'overlay colour carries the linear gain (a hex literal could not exceed 1.0)',
        'r=' + S.overlay.material.color.r.toFixed(3));
      var tileMeanLin = 0.04187, plateMeanLin = 0.1725;   // roof_gravel, plates averaged
      say(Math.abs(CFG.detailGain * tileMeanLin / plateMeanLin - 1) < 0.05,
        'gain brings the tile mean to within 5% of the plate mean (tone neutral)',
        (100 * (CFG.detailGain * tileMeanLin / plateMeanLin - 1)).toFixed(2) + '%');
      // The overlay must never move the district's brightness by more than a rounding error.
      var netShift = CFG.detailOpacity * (CFG.detailGain * tileMeanLin / plateMeanLin - 1);
      say(Math.abs(netShift) < 0.02, 'net luminance shift from the overlay is under 2%',
        (100 * netShift).toFixed(2) + '%');
      say(CFG.detailUrl.indexOf('gravel') >= 0,
        'the isotropic tile is the one wired up (asphalt measured 1.249 dy/dx and striped)',
        CFG.detailUrl);
      say(S.overlay.material.fog !== false && plate.material.fog !== false,
        'both layers keep fog:true so they fade into Fog(420,1750) together and cannot seam');
      // Tile availability. In this DOM-less harness three's ImageLoader throws on
      // document.createElementNS, which is the real synchronous-failure path, so assert the
      // safe degradation rather than pretending the tile loaded.
      if (S.tileState === 'unavailable') {
        say(S.overlay.material.opacity === 0,
          'with no tile available the overlay is zeroed, so it can never grey-wash the art',
          'tileState=' + S.tileState);
      } else {
        say(S.tileState === 'loading' || S.tileState === 'ok',
          'tile load is in flight or complete', 'tileState=' + S.tileState);
      }
    }

    // Idempotence: buildGround runs on every district swap, so apply() must not stack overlays.
    var before = plate.children.length;
    apply(T, plate, 'THE_YARDS', 1700, 1300);
    eq('a second apply() does not stack a second overlay', plate.children.length, before);

    // Disposal must actually detach.
    dispose();
    eq('dispose() removes the overlay from the plate', plate.children.length, 0);
    say(S.overlay === null, 'dispose() cleared internal overlay state');

    // Guard behaviour: a null engine or a plate-less call must be a quiet no-op, never a throw.
    var threw = false;
    try { apply(null, plate, 'X', 1700, 1300); apply(T, null, 'X', 1700, 1300); } catch (_e) { threw = true; }
    say(!threw, 'apply() with a missing engine or missing plate is a quiet no-op');

    lines.push('--- headline ---');
    lines.push('  plate aspect     : art 0.6842 on plane 1.3077  ->  shipped stretch 1.9112x  ->  fixed 1.0000x');
    lines.push('  plate density    : 0.489 x / 0.935 z  ->  0.489 / 0.489 texels per unit (square)');
    lines.push('  surface detail   : ' + (256 / CFG.detailTile).toFixed(3) + ' texels/unit tiled = ' +
               ((256 / CFG.detailTile) / dC.x).toFixed(2) + 'x the plate, 120 per hero height');
    lines.push('  geometry         : 4 verts / 2 tris  ->  ' + (nx * nz) + ' verts / ' + (CFG.segX * CFG.segZ * 2) + ' tris');
    lines.push('  draw calls added : 1');
    return { ok: ok, lines: lines };
  }

  var API = {
    id: 'akground',
    ver: VER,
    apply: apply,
    dispose: dispose,
    diag: diag,
    selfTest: selfTest,
    // Pure core, exported so a render harness can compute the SHIPPED look and the FIXED look
    // from one build and produce a real before/after instead of a claim.
    fitUv: fitUv,
    density: density,
    shadeField: shadeField,
    hash: hash,
    cfg: function () { var o = {}, k; for (k in CFG) if (CFG.hasOwnProperty(k)) o[k] = CFG[k]; return o; },
    setFit: function (m) { CFG.fit = (m === 'stretch' || m === 'contain') ? m : 'cover'; return CFG.fit; },
    setDetail: function (op, tile, gain) {
      if (typeof op === 'number') CFG.detailOpacity = Math.max(0, Math.min(1, op));
      if (typeof tile === 'number' && tile > 0) CFG.detailTile = tile;
      if (typeof gain === 'number' && gain > 0) CFG.detailGain = gain;
      try {
        if (S.oMat) {
          S.oMat.opacity = CFG.detailOpacity;
          S.oMat.color.setRGB(CFG.detailGain, CFG.detailGain, CFG.detailGain);
        }
        if (S.oTex) S.oTex.repeat.set(S.worldW / CFG.detailTile, S.worldH / CFG.detailTile);
      } catch (_e) {}
      return { opacity: CFG.detailOpacity, tile: CFG.detailTile, gain: CFG.detailGain };
    },
    setNoise: function (a) { CFG.noiseAmp = Math.max(0, Math.min(0.5, a || 0)); return CFG.noiseAmp; }
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;

  if (root && root.document) {
    root.AK_GROUND = API;
    /* REGISTRY NOTE -- READ BEFORE "FIXING" THIS.
     * This module is NOT registered with AK_SYSTEMS, and that is deliberate. Its integration
     * point is world3d.js buildGround, not the hub tick: it has no onTick, no onDrawWorld and no
     * onEnterBuilding work to do. Registering it anyway would put an entry in _registry.js:22
     * tickAll() that dispatches to nothing, which is this repo's single most repeated failure
     * (code nothing calls) wearing a registry badge. The real call sites are quoted in the
     * handoff and belong to the Wire phase, which owns world3d.js under RULE 9.
     *
     * The one thing worth doing at load time is warming the detail tile so it cannot pop in after
     * the district is already on screen. A plain Image() does that through the normal HTTP cache
     * with no THREE dependency and no load-order risk. */
    try { var w = new root.Image(); w.src = CFG.detailUrl; } catch (_e) {}
  }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akground.js` -- imports the REAL vendored r160 and asserts against
 * it. No mocks: a stubbed THREE would pass a uv rewrite or a parenting trick that three itself
 * rejects, and that is exactly how "verified" work has shipped broken here before. */
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
