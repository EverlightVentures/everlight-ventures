/* ALLEY KINGZ -- AK_DOORS: buildings become DESTINATIONS.  AK-DOORS 2026-07-20.
 *
 * OPERATOR: "buildings are obstacles, not destinations -- no door, no prompt, no way in."
 *
 * WHAT IS ACTUALLY THERE TODAY (measured before a line of this was written, not assumed)
 *
 *   1. THERE IS NO DOOR. world3d.js:906 collects one marker per enterable building and
 *      buildDoors (world3d.js:981) raises them as two InstancedMeshes: a RingGeometry(30,42)
 *      lying flat on the ground at y=1.5, and an open-ended CylinderGeometry 150 tall at y=75.
 *      That is a glowing ring with a light shaft over it, standing in the OPEN STREET 0.14*b.h
 *      in front of the wall. It marks a SPOT. Nothing about it is a door: there is no threshold,
 *      no jamb, no lintel, nothing touching the building. At the shipping camera (tpp, eye 96,
 *      buildings 158-205 tall) the eye reads a wall with a lamp in front of it.
 *
 *   2. THERE IS NO PROMPT. The only text is index.html:2594
 *          if(dwellT<0.22) showBanner('Step into '+near.label+'...',0.5);
 *      which is the shared top-of-screen banner, fires at 53 units, and is replaced 0.22s later
 *      by the interior itself (index.html:2595). It cannot tell you a door exists from across
 *      the plaza, which is the entire complaint.
 *
 *   3. THE WAY IN ALREADY WORKS -- IT IS JUST INVISIBLE. index.html:2592 tests
 *          hypot(me.x - b.x, me.y - (b.y + b.h/2)) < me.r + 30      // 53
 *      against EVERY building in curBuildings(), and index.html:976 akNearestBuilding uses the
 *      same point at me.r+40 = 63 for the keyboard path. So the entry point is not a mystery and
 *      not a new system: it is (b.x, b.y + b.h/2), derived from the zone record.
 *
 * SO THIS MODULE BUILDS THE THREE MISSING THINGS AND NOTHING ELSE:
 *      a door you can SEE       -- lit threshold + jambs + lintel + a glow pool on the ground
 *      a prompt you can READ    -- "ENTER THE SILO", world-anchored, in and out with proximity
 *      a way in you can TAP     -- which walks the hero to the host's own door point and lets the
 *                                  host's own dwell fire. No parallel entry path exists here.
 *
 * WHAT THIS MODULE DELIBERATELY DOES NOT DO
 *   - It does not route. systems/akportal.js already classifies every door as
 *     panel / video / minigame2d / interior3d (akportal.js:71-100) and AK_SYSTEMS.enterBuilding
 *     (_registry.js:19) already decides who owns the screen. This module READS AK_PORTAL.route()
 *     for the prompt's sub-line and then hands entry to window.enterInterior -- the same function
 *     the dwell path calls at index.html:2595, already wrapped by akportal (akportal.js:345) so
 *     door memory and the exit watchdog keep working. A second router is the thing the lane
 *     brief forbids and it would silently void akportal's whole Section 5.
 *   - It does not replace world3d's ring/beam. Those are the FAR read (visible across the
 *     district, above the rooflines of the low buildings). This is the NEAR read (what the wall
 *     looks like when you get there). They compose: ring at y=1.5, this pool at y=0.9 underneath.
 *   - It never removes or edits authored art. The frame stands 2.5 units PROUD of the facade
 *     plane; the facade texture akfacade.js fits is untouched.
 *
 * ONE THING IN THE LANE BRIEF DID NOT SURVIVE CONTACT WITH THE DATA, AND IT MATTERS.
 * The brief asks for the door on "the face toward the plaza". The plaza is the district centre --
 * akworldgen.js:340 puts its keep-out disc at (W/2, H/2) and index.html:889 spawns the hero at
 * (850,650) in a 1700x1300 world. So the plaza-facing wall was computed for all 16 enterable
 * doors, by casting a ray from each building centre to (850,650) and taking the wall it exits.
 * The result, measured, not guessed:
 *
 *      plaza-facing wall:   E x6    W x7    N x2    S x1
 *      agrees with the wall the game lets you in through:   1 of 16   (ARENA only)
 *
 * That is not a rounding error, it is the district layout: every district flanks the centre plaza
 * with a LEFT/RIGHT pair of buildings, so their plaza-facing wall is almost always east or west.
 * Meanwhile index.html:2592 only ever measures to (b.x, b.y + b.h/2) -- the SOUTH face -- so south
 * is the only wall the game will open, for all 16.
 *
 * A door drawn on the plaza-facing wall would therefore be a picture of a door 15 times out of 16:
 * you would walk to it and nothing would happen, which is a more frustrating version of the exact
 * complaint being fixed. So the door goes on the ENTRY face, every time, and doorsFor() records
 * plazaFace + agrees so diag() reports the disagreement instead of burying it. If the host's entry
 * rule is ever generalised to all four walls, this module needs one line changed (doorY) and the
 * bookkeeping is already sitting there waiting.
 *
 * WHICH BUILDINGS ARE ENTERABLE IS DATA, NOT A LIST. The rule is world3d.js:906's rule, verbatim:
 * b.url !== 'soon'. index.html's B(...) helper (index.html:841) stores 'soon' for signposted-but-
 * shut buildings (TROPHY, ARCADE). Marking those would be a lie, and "unlit" is what currently
 * means "nothing for you here yet". Hardcoding an id list here would go stale the first time a
 * building opens.
 *
 * DRAW CALLS: TWO PER DISTRICT, FLAT.  Every door in the district is merged into ONE opaque
 * vertex-coloured mesh (the frame) plus ONE additive vertex-coloured mesh (the light). The naive
 * build is ~7 meshes x 4 authored buildings = 28 draw calls in HOME_TURF and would grow with the
 * district; merged it is 2, whatever the building count. Same argument bldmass.js:38 makes for
 * roof furniture and akinstance.js:697 makes for player structures -- on a phone the per-call
 * state change is what runs out, not triangles (this whole set is ~520 triangles).
 *
 * MERGING DIVERGES FROM bldmass.js IN ONE PLACE, ON PURPOSE. bldmass records boxes and bakes ONE
 * colour per box. The ground pool needs light that FALLS OFF with distance from the threshold and
 * the door panel needs to be brighter at the head than at the sill, which is a PER-VERTEX colour a
 * per-box record cannot express. So the accumulator here takes both: pushBox() for the carpentry,
 * pushQuad() with four independent corner colours for the light.
 *
 * UNITS ARE PIXELS AND EVERYTHING IS SIZED OFF THE HERO (60), never off a tutorial absolute.
 *   DOOR_H 66 = 1.10 x hero   -- a doorway must clear the character who walks through it
 *   DOOR_W 40 = 0.67 x hero   -- shoulder-width plus clearance
 *   pool    reaches 44 past the entry point, so the player is standing INSIDE the light at the
 *           moment index.html:2592's 53-unit dwell test fires. The light and the rule agree.
 *
 * ONE RENDERER LAW: constructs no WebGLRenderer, no canvas and no Scene. It borrows the scene
 * world3d already owns (AK_WORLD3D._state.scene) and the THREE instance three_boot already loaded.
 */
(function (root) {
  'use strict';

  var HAS_DOM = (typeof document !== 'undefined' && typeof document.createElement === 'function');

  /* =========================================================================
     SECTION 1 -- THE NUMBERS
     Every one of these is hero-relative (hero = 60 units tall, feet on y=0) or copied from a
     measured host rule. None of them is a taste number and none is a tutorial absolute.
     ========================================================================= */

  var HERO      = 60;          // the yardstick. hub3d.js scales the GLB to this.
  var DOOR_H    = 66;          // 1.10 x hero -- taller than the dog walking through it
  var DOOR_W    = 40;          // 0.67 x hero
  var JAMB_W    = 7;           // post thickness; below ~5 it disappears at tpp distance
  var LINTEL_H  = 9;           // the head over the opening
  var BAND_H    = 4;           // the tinted sign strip above the lintel (carries b.col)
  var STEP_H    = 3;           // threshold step, just enough to catch the directional light
  var STEP_D    = 14;          // how far the step protrudes into the street
  var FRAME_D   = 5;           // how deep the carpentry is (front-to-back)
  var PROUD     = 2.5;         // frame stands this far off the facade plane. Below ~1.5 the
                               // depth buffer ties with the facade quad and the frame flickers.
  var PANEL_Z   = 0.8;         // the lit panel sits just off the wall, INSIDE the frame
  var POOL_Y    = 0.9;         // ground plane is y=0; world3d's door ring is at y=1.5. Sitting
                               // under the ring means both read, and neither z-fights the plate.
  var POOL_HW   = 46;          // 1.15 x DOOR_W at the threshold...
  var POOL_FLARE= 1.35;        // ...widening to 1.35x at the far edge: light spreads, it does not
                               // travel down a corridor.
  var POOL_OUT  = 44;          // how far past the entry point the light reaches (see header)

  // Host-derived, NOT chosen here:
  var DEPTH_K   = 0.36;        // world3d.js:855 builds the box depth as b.h*0.72, so the front
                               // wall plane is at b.y + b.h*0.36. The frame must land on THAT,
                               // not on b.y + b.h/2 (which is the street, 0.14*b.h further out).
  var ENTRY_R   = 63;          // index.html:976 akNearestBuilding, me.r+40. The widest radius at
                               // which the host will actually let you in. AK_PORTAL.ENTRY_R is
                               // the same number for the same reason.
  var DWELL_R   = 53;          // index.html:2592, me.r+30. The walk-in radius.
  var TARGET_OUT= 30;          // tap-to-walk aims here past the door point: inside DWELL_R (53) so
                               // the host's dwell still fires, but clear enough of the wall that
                               // AK_COLLISION.resolve (index.html:2571) is not fighting the target.

  // Prompt proximity. Hysteresis, because a single radius makes the pill strobe when the player
  // idles exactly on the boundary -- and idling on a boundary is what a joystick does.
  var SHOW_R    = 210;         // 3.5 x hero. Far enough to be a destination, near enough to mean you.
  var HIDE_R    = 246;         // 1.17 x SHOW_R
  var PROMPT_H  = 104;         // world height the prompt is anchored at: clears the sign band
                               // (66+9+4 = 79) with margin, still well under the 158-205 roofline.

  // Pulse. 2.6s is a slow breath. Anything under ~1s reads as an ALERT (something is wrong);
  // a doorway should read as an invitation, so it is deliberately slower than any warning fx.
  var PULSE_S   = 2.6;
  var GLOW_BASE = 0.34;
  var GLOW_AMP  = 0.16;        // -> 0.18 .. 0.50

  // Palette. The carpentry is grimier and cooler than the facade so it reads as separate material
  // (bldmass.js:41 makes the same call for the same reason). The LIGHT takes the building's own
  // b.col, because index.html already trains the player on those tints -- it strokes each facade
  // and prints each label in b.col, and world3d.js:978 tints the door ring with it. Introducing a
  // 19th colour for doors would break a mapping the player has already learned.
  var C_JAMB = 0x1b1b22, C_LINTEL = 0x24242c, C_STEP = 0x15151b;

  /* =========================================================================
     SECTION 2 -- WHICH BUILDINGS HAVE DOORS, AND WHERE (pure, node-testable)
     ========================================================================= */

  // world3d.js:906's rule, verbatim. Kept as a named function so there is exactly one definition
  // of "enterable" in this file and the self-test can assert against it.
  function isEnterable(b) {
    return !!b && b.url !== 'soon';
  }

  /* AK-DOORFIT 2026-07-20. wallZ is the plane the door FRAME sits on, and it must be the plane of
   * the geometry the player can actually SEE.
   *
   * The bug this fixes: DEPTH_K=0.36 encodes world3d's BoxGeometry depth (b.h*0.72). That is
   * correct for a boxed building and WRONG for a modelled one -- bldmodels sets the box
   * m.visible=false for ARENA/SILO/WARD/BLOCK/INFIRMARY/DROP and stands a GLB in its place, and the
   * GLB's depth is whatever Tripo exported, unrelated to b.h. So on the six best-looking buildings
   * in the game the frame was pinned to a plane that is never drawn.
   *
   * bldmodels now publishes the measured post-scale footprint, so ask for the truth and fall back
   * to the formula only when there is no model (or the GLB has not loaded yet -- models are lazy
   * and async, so null is a normal transient, not an error). */
  function wallZFor(b, bh) {
    try {
      var M = window.AK_BLDMODELS;
      if (M && M.footprint) {
        var fp = M.footprint(b.id);
        if (fp && fp.halfD > 0) return b.y + fp.halfD;   // real front face of the real mesh
      }
    } catch (_e) {}
    return b.y + bh * DEPTH_K;                            // boxed building: original behaviour
  }

  /* doorsFor(zone) -> [{ id, label, act, col, bx, by, bw, bh, doorX, doorY, wallZ, plazaFace, agrees }]
   *
   * doorX/doorY IS index.html:2592's dwell point, character for character:
   *      dx = me.x - b.x ,  dy = me.y - (b.y + b.h/2)
   * That is not a coincidence to be maintained, it is the point of the module. A door drawn
   * anywhere else would be a lie -- you would walk to the picture and nothing would happen.
   *
   * plazaFace/agrees are HONESTY BOOKKEEPING, not geometry -- see the header. plazaFace is the
   * wall a ray from the building centre to the district plaza (W/2, H/2) exits through, and
   * `agrees` is whether that is the same wall the host will actually open. Measured across every
   * district: agrees is TRUE for exactly 1 of 16 doors. The door is placed on the entry face
   * regardless; diag().plazaMismatch surfaces the count so the conflict is visible.
   *
   * The exit wall is found by comparing |dx|/halfWidth against |dy|/halfHeight, not raw pixels.
   * Footprints here are 160-210 wide by 96-124 deep, so a raw |dx|>|dy| test answers a different
   * question than "which wall does the ray leave through". akportal.js:139 faceFor normalises the
   * same way for the same reason.
   */
  function doorsFor(zone, worldW, worldH) {
    var out = [];
    if (!zone || !zone.buildings) return out;
    var pcx = (worldW || 1700) / 2, pcy = (worldH || 1300) / 2;
    for (var i = 0; i < zone.buildings.length; i++) {
      var b = zone.buildings[i];
      if (!isEnterable(b)) continue;
      var bw = b.w || 160, bh = b.h || 96;
      var col = 0xe8c55a;
      try { col = parseInt(String(b.col || '#e8c55a').slice(1), 16); } catch (_e) {}
      var nx = (pcx - b.x) / Math.max(1, bw / 2);
      var ny = (pcy - b.y) / Math.max(1, bh / 2);
      var pf = (Math.abs(nx) > Math.abs(ny)) ? (nx > 0 ? 'E' : 'W') : (ny > 0 ? 'S' : 'N');
      out.push({
        id: b.id, label: b.label || b.id || 'BUILDING', act: b.act || '',
        col: col, bx: b.x, by: b.y, bw: bw, bh: bh,
        doorX: b.x,                    // index.html:2592
        doorY: b.y + bh / 2,           // index.html:2592
        wallZ: wallZFor(b, bh),        // real GLB footprint when modelled, box formula otherwise
        plazaFace: pf, agrees: pf === 'S',
        _b: b
      });
    }
    return out;
  }

  // Nearest door to the player, with hysteresis. `held` is the id currently shown, so a door keeps
  // the prompt out to HIDE_R once it has it -- that is the whole anti-strobe mechanism.
  function pickNear(doors, x, y, held) {
    var best = null, bestD = Infinity;
    for (var i = 0; i < doors.length; i++) {
      var d = doors[i];
      var dist = Math.hypot(x - d.doorX, y - d.doorY);
      var lim = (held && d.id === held) ? HIDE_R : SHOW_R;
      if (dist <= lim && dist < bestD) { bestD = dist; best = d; }
    }
    return best ? { door: best, dist: bestD, armed: bestD <= ENTRY_R } : null;
  }

  /* =========================================================================
     SECTION 3 -- THE GEOMETRY ACCUMULATOR

     One flat position/normal/colour triple-buffer per mesh. Non-indexed throughout: a box goes
     24 -> 36 verts, which is a rounding error at ~520 triangles for a whole district, and it
     removes every index-offset bug class from the merge. bldmass.js:56 made the same trade.
     ========================================================================= */

  // Glow opacity at time t. Extracted so the self-test measures the SHIPPING function rather than
  // a restatement of it -- a duplicated formula in a test proves the test, not the code.
  function pulseAt(t) {
    return GLOW_BASE + GLOW_AMP * Math.sin(t * Math.PI * 2 / PULSE_S);
  }

  function sink() { return { pos: [], nor: [], col: [] }; }

  function rgb(hex) {
    return [((hex >> 16) & 255) / 255, ((hex >> 8) & 255) / 255, (hex & 255) / 255];
  }
  function scaleRgb(c, k) { return [c[0] * k, c[1] * k, c[2] * k]; }
  // Push a colour toward white. A lit doorway is not just "more of the tint" -- real light
  // desaturates as it gets brighter, and without this the bright end of the panel reads as
  // flat paint rather than as a lamp.
  function toward1(c, k) {
    return [c[0] + (1 - c[0]) * k, c[1] + (1 - c[1]) * k, c[2] + (1 - c[2]) * k];
  }

  function pushBox(THREE, S, w, h, d, hex, x, y, z) {
    var g = new THREE.BoxGeometry(w, h, d);
    var ng = (typeof g.toNonIndexed === 'function') ? g.toNonIndexed() : g;
    var p = ng.attributes.position, n = ng.attributes.normal, c = rgb(hex);
    for (var v = 0; v < p.count; v++) {
      S.pos.push(p.getX(v) + x, p.getY(v) + y, p.getZ(v) + z);
      S.nor.push(n.getX(v), n.getY(v), n.getZ(v));
      S.col.push(c[0], c[1], c[2]);
    }
    try { g.dispose(); if (ng !== g) ng.dispose(); } catch (_e) {}
  }

  /* Four arbitrary corners, four independent corner colours, two triangles. This is the primitive
   * bldmass cannot express and the reason the light in this module has falloff instead of being a
   * flat glowing rectangle. p0..p3 wind around the quad; the diagonal is p0-p2. */
  function pushQuad(S, p0, p1, p2, p3, c0, c1, c2, c3, nrm) {
    var P = [p0, p1, p2, p0, p2, p3], C = [c0, c1, c2, c0, c2, c3];
    for (var i = 0; i < 6; i++) {
      S.pos.push(P[i][0], P[i][1], P[i][2]);
      S.nor.push(nrm[0], nrm[1], nrm[2]);
      S.col.push(C[i][0], C[i][1], C[i][2]);
    }
  }

  function finish(THREE, S) {
    if (!S.pos.length) return null;
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(S.pos, 3));
    g.setAttribute('normal',   new THREE.Float32BufferAttribute(S.nor, 3));
    g.setAttribute('color',    new THREE.Float32BufferAttribute(S.col, 3));
    return g;
  }

  /* =========================================================================
     SECTION 4 -- ONE DOOR, WRITTEN INTO THE TWO SHARED SINKS

     Read this as a section drawing looking down at the wall from above:

         street  (+z, toward the default camera)
            ^
            |     [=== ground glow pool, widening outward, fading to 0 ===]
            |     [ step ]
        wallZ +---[jamb][ lit panel ][jamb]---+   <- frame stands PROUD of the facade
            |     [        lintel        ]
            |     [      b.col band      ]
         building interior
     ========================================================================= */

  function buildOne(THREE, FR, GL, d) {
    var cx = d.doorX;                     // = b.x
    var zw = d.wallZ;                     // front wall plane, world3d.js:855
    var zf = zw + PROUD;                  // carpentry plane
    var half = DOOR_W / 2;
    var openW = DOOR_W + JAMB_W * 2;      // outer width of the frame
    var tint = rgb(d.col);

    // --- carpentry (opaque, merged into FR) ---
    // Jambs run the full height of the opening PLUS the lintel, so the corner joint reads solid
    // from an oblique tpp angle instead of showing a gap where the two boxes meet.
    var jh = DOOR_H + LINTEL_H;
    pushBox(THREE, FR, JAMB_W, jh, FRAME_D, C_JAMB, cx - half - JAMB_W / 2, jh / 2, zf);
    pushBox(THREE, FR, JAMB_W, jh, FRAME_D, C_JAMB, cx + half + JAMB_W / 2, jh / 2, zf);
    pushBox(THREE, FR, openW, LINTEL_H, FRAME_D + 1.5, C_LINTEL, cx, DOOR_H + LINTEL_H / 2, zf);
    // The tinted band. This is the ONLY place the building's colour appears as solid material --
    // it is the sign over the door, which is exactly how the 2D layer already labels buildings.
    pushBox(THREE, FR, openW, BAND_H, FRAME_D + 1.5, d.col, cx, DOOR_H + LINTEL_H + BAND_H / 2, zf);
    // Threshold step, protruding into the street. At the shipping pitch the top face of this box
    // is what catches the directional light (world3d.js:1396) and gives the door a base edge --
    // without it the frame appears to be standing on nothing.
    pushBox(THREE, FR, openW + 10, STEP_H, STEP_D, C_STEP, cx, STEP_H / 2, zf + FRAME_D / 2 + STEP_D / 2);

    // --- light (additive, merged into GL) ---
    // The panel: brighter at the head (where a fixture would be), warmer and dimmer at the sill.
    var top = toward1(tint, 0.55);
    var bot = scaleRgb(tint, 0.55);
    var zp = zw + PANEL_Z;
    pushQuad(GL,
      [cx - half, 0,      zp], [cx + half, 0,      zp],
      [cx + half, DOOR_H, zp], [cx - half, DOOR_H, zp],
      bot, bot, top, top, [0, 0, 1]);

    // The ground pool: full at the threshold, ZERO at the far edge, and flaring wider as it goes.
    // Zero-at-the-edge is what makes it read as spill instead of as a painted rug -- an additive
    // vertex colour of (0,0,0) contributes literally nothing, so the quad has no visible boundary.
    var zFar = d.doorY + POOL_OUT;
    var near = toward1(tint, 0.30);
    var dark = [0, 0, 0];
    pushQuad(GL,
      [cx - POOL_HW,               POOL_Y, zw],
      [cx + POOL_HW,               POOL_Y, zw],
      [cx + POOL_HW * POOL_FLARE,  POOL_Y, zFar],
      [cx - POOL_HW * POOL_FLARE,  POOL_Y, zFar],
      near, near, dark, dark, [0, 1, 0]);
  }

  /* =========================================================================
     SECTION 5 -- SCENE LIFECYCLE

     WHY THIS IS POLLED AND NOT CALLED: world3d.js owns setZone (world3d.js:1518) and this lane
     must not edit that file. setZone also REUSES the same THREE.Scene across districts and removes
     only its own objects, so anything else parented there survives a district swap -- which is
     exactly how HOME_TURF's doors would end up standing in THE_DOCKS. akinstance.js:~50 documents
     the same trap. So: watch _state.zoneId, and on any change tear our own meshes down first and
     rebuild from the new zone record.
     ========================================================================= */

  var _built = '';        // zoneId our meshes currently represent ('' = nothing built)
  var _frame = null, _glow = null, _glowMat = null;
  var _doors = [];        // the door records for _built, reused every frame by the prompt
  var _t = 0;
  var _diag = { builds: 0, doors: 0, drawCalls: 0, verts: 0, errors: 0, zone: '',
                plazaMismatch: 0, lastErr: '' };

  function THREEof() {
    try {
      var T = root.AK_THREE;
      return (T && T.ok && T.ok() && T.get) ? T.get() : null;
    } catch (_e) { return null; }
  }
  function sceneOf() {
    try {
      var W = root.AK_WORLD3D;
      if (!W || !W.isOn || !W.isOn()) return null;
      var st = W._state;
      return (st && st.scene) ? st : null;
    } catch (_e) { return null; }
  }

  function teardown(st) {
    var s = st && st.scene;
    var kill = [_frame, _glow];
    for (var i = 0; i < kill.length; i++) {
      var m = kill[i]; if (!m) continue;
      try {
        if (s) s.remove(m);
        if (m.geometry && m.geometry.dispose) m.geometry.dispose();
        if (m.material && m.material.dispose) m.material.dispose();
      } catch (_e) {}
    }
    _frame = null; _glow = null; _glowMat = null; _doors = []; _built = '';
  }

  function build(THREE, st, zone, worldW, worldH) {
    var doors = doorsFor(zone, worldW, worldH);
    _doors = doors;
    _built = zone.id;
    _diag.zone = zone.id; _diag.doors = doors.length;
    _diag.plazaMismatch = 0;
    for (var q = 0; q < doors.length; q++) if (!doors[q].agrees) _diag.plazaMismatch++;
    if (!doors.length) { _diag.drawCalls = 0; _diag.verts = 0; return true; }

    var FR = sink(), GL = sink();
    for (var i = 0; i < doors.length; i++) buildOne(THREE, FR, GL, doors[i]);

    var gf = finish(THREE, FR), gg = finish(THREE, GL);
    if (gf) {
      _frame = new THREE.Mesh(gf, new THREE.MeshLambertMaterial({ vertexColors: true }));
      _frame.userData.akDoorFrame = true;
      // NOT pushed into st.blds. akcull.js:484 claims st.blds as its only intake, and a frustum
      // culler keyed on a merged district-wide mesh's centre would blank every door in the
      // district at once the moment that centre left the frustum. world3d.js:1019 keeps its own
      // door markers out of blds for the same reason.
      st.scene.add(_frame);
    }
    if (gg) {
      _glowMat = new THREE.MeshBasicMaterial({
        vertexColors: true, transparent: true, opacity: GLOW_BASE,
        // DoubleSide because the pool quad and the panel quad are authored with opposite winding
        // conventions (XZ vs XY) and the camera orbits a full 360 (AK-CAMYAW-FIX). Backface
        // culling here would blank the pool from half the yaw range. world3d.js:988 takes the
        // same decision for its ring for the same reason.
        side: THREE.DoubleSide,
        // depthWrite off so the light never occludes the hero standing in it; additive so it
        // BRIGHTENS the plate underneath instead of pasting a grey rectangle on it.
        depthWrite: false, blending: THREE.AdditiveBlending, fog: true
      });
      _glow = new THREE.Mesh(gg, _glowMat);
      _glow.renderOrder = 2;      // after the opaque pass, so the additive blend has something to add to
      _glow.userData.akDoorGlow = true;
      st.scene.add(_glow);
    }
    _diag.builds++;
    _diag.drawCalls = (_frame ? 1 : 0) + (_glow ? 1 : 0);
    _diag.verts = (FR.pos.length + GL.pos.length) / 3;
    return true;
  }

  function sync(ctx) {
    var THREE = THREEof(); if (!THREE) return false;
    var st = sceneOf();
    if (!st) { if (_built) teardown(null); return false; }
    var zone = ctx && ctx.activeZone;
    if (!zone || !zone.id) return false;
    // world3d has not finished swapping yet -- wait rather than build against a stale record.
    if (st.zoneId !== zone.id) return false;
    if (_built === zone.id) return true;
    try {
      if (_built) teardown(st);
      var w = (ctx.world && ctx.world.WORLD_W) || 1700;
      var h = (ctx.world && ctx.world.WORLD_H) || 1300;
      return build(THREE, st, zone, w, h);
    } catch (e) {
      // Never silent: a swallowed throw here would look exactly like "the module is not wired".
      _diag.errors++; _diag.lastErr = String((e && e.message) || e);
      try { if (root.console && console.warn) console.warn('[AK_DOORS] build failed', e); } catch (_x) {}
      return false;
    }
  }

  /* =========================================================================
     SECTION 6 -- THE PROMPT

     Anchored with AK_WORLD3D.project(x, y, h) -> {sx, sy, depth, scale, vis} (world3d.js:332).
     That projector is the ONE the hero, the buildings and the 2D overlay all already agree on --
     inventing a second screen transform is how a label ends up drifting off its building the
     moment the camera orbits.

     THE 2D FALLBACK IS NOT OPTIONAL. world3d ships default-OFF and is turned on by an async poll
     (index.html:3520) that gives up after ~20s on a device with no WebGL. On that device
     project() does not exist and the whole 3D half of this module is inert -- but the buildings,
     the dwell rule and the operator's complaint are all still there. So the prompt falls back to
     the hub's own wx/wy pair (AK_CTX.world.wx/wy, index.html:3477), which is the same transform
     the 2D layer draws every building with.
     ========================================================================= */

  var _el = null, _pill = null, _title = null, _sub = null, _stem = null;
  var _shownId = '', _shownArmed = null, _visible = false;
  var _tapDoor = null;

  function mkPrompt() {
    if (_el || !HAS_DOM) return _el;
    var wrap = document.createElement('div');
    wrap.id = 'ak-door-prompt';
    // z-index 9: above the world canvas and the #phud chips (index.html:24, z 6), BELOW #interior
    // (index.html:95, z 12) and #fade (index.html:21, z 20). A prompt that outranked the keeper
    // card would sit on top of the very screen it just opened.
    wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:9;pointer-events:none;' +
      'display:none;flex-direction:column;align-items:center;' +
      'font-family:Inter,system-ui,sans-serif;will-change:transform;' +
      'transform:translate(-50%,-100%);';

    var pill = document.createElement('div');
    // pointer-events:auto ONLY on the pill: the wrapper stays transparent to touch so the pill
    // never steals a drag meant for the camera orbit.
    pill.style.cssText = 'pointer-events:auto;cursor:pointer;-webkit-tap-highlight-color:transparent;' +
      'padding:8px 14px 7px;border-radius:12px;text-align:center;white-space:nowrap;' +
      'background:linear-gradient(180deg,rgba(14,12,18,.93),rgba(6,6,10,.93));' +
      'box-shadow:0 6px 18px rgba(0,0,0,.55);border:1px solid rgba(232,197,90,.45);';

    var t = document.createElement('b');
    t.style.cssText = 'display:block;font-size:13px;font-weight:900;letter-spacing:.07em;color:#e8c55a;';
    var s = document.createElement('span');
    s.style.cssText = 'display:block;font-size:9.5px;font-weight:700;letter-spacing:.06em;' +
      'color:#9a8f6a;text-transform:uppercase;margin-top:2px;';

    // A downward tick that ties the pill to the doorway it is naming. Without it a floating label
    // over a dense skyline is ambiguous about WHICH building it belongs to.
    var stem = document.createElement('div');
    stem.style.cssText = 'width:1px;height:16px;background:linear-gradient(180deg,rgba(232,197,90,.7),rgba(232,197,90,0));';

    pill.appendChild(t); pill.appendChild(s);
    wrap.appendChild(pill); wrap.appendChild(stem);
    try { document.body.appendChild(wrap); } catch (_e) { return null; }

    pill.addEventListener('click', onTap);
    pill.addEventListener('pointerdown', function (e) { try { e.stopPropagation(); } catch (_x) {} });

    _el = wrap; _pill = pill; _title = t; _sub = s; _stem = stem;
    return _el;
  }

  /* THE WAY IN. Two paths, and NEITHER of them is a new entry system.
   *
   *   in range (<= ENTRY_R 63)  -> window.enterInterior(b). That is the exact call index.html:2595
   *                               makes at the end of a dwell, and akportal.js:345 has already
   *                               wrapped it, so door memory and the exit watchdog both engage.
   *   out of range             -> set me.tx/me.ty to a point TARGET_OUT past the door. index.html:2565
   *                               walks the hero there (`else if(me.tx!=null)`), AK_COLLISION
   *                               slides him around anything in the way (index.html:2571), and
   *                               when he arrives the host's OWN dwell test fires and lets him in.
   *
   * The second path is the one that matters: tapping a far door makes the dog walk to it and open
   * it himself. Nothing here decides what is behind the door -- AK_SYSTEMS.enterBuilding
   * (_registry.js:19) does, exactly as it does for a walk-in.
   */
  function onTap(e) {
    try { if (e) { e.preventDefault(); e.stopPropagation(); } } catch (_x) {}
    var d = _tapDoor; if (!d) return;
    var c = root.AK_CTX, me = c && c.me; if (!me) return;
    var dist = Math.hypot(me.x - d.doorX, me.y - d.doorY);
    if (dist <= ENTRY_R && typeof root.enterInterior === 'function') {
      try { root.enterInterior(d._b); } catch (_e) {}
      hide();
      return;
    }
    me.tx = d.doorX;
    me.ty = d.doorY + TARGET_OUT;
  }

  function hide() {
    if (!_el || !_visible) return;
    _visible = false; _shownId = ''; _shownArmed = null; _tapDoor = null;
    try { _el.style.display = 'none'; } catch (_e) {}
  }

  // Screen point for the door head. Prefers the 3D projector; falls back to the hub's 2D pair.
  // Returns null when the point is behind the camera or off screen, which is the signal to hide.
  function screenFor(d, ctx) {
    var W = root.AK_WORLD3D;
    if (W && W.isOn && W.isOn() && typeof W.project === 'function') {
      var p = W.project(d.doorX, d.doorY, PROMPT_H);
      if (!p || !p.vis || !(p.depth > 0)) return null;
      return { sx: p.sx, sy: p.sy };
    }
    var wo = ctx && ctx.world;
    if (wo && typeof wo.wx === 'function' && typeof wo.wy === 'function') {
      // 2D hub: wx(x,y)/wy(y,x) are the paired projection (index.html:3477). No height term
      // exists in that transform, so lift the label in SCREEN space instead -- 0.62 of PROMPT_H
      // matches how the flat layer already foreshortens vertical world offsets.
      return { sx: wo.wx(d.doorX, d.doorY), sy: wo.wy(d.doorY, d.doorX) - PROMPT_H * 0.62 };
    }
    return null;
  }

  function updatePrompt(ctx) {
    if (!HAS_DOM) return;
    var me = ctx && ctx.me;
    if (!me || !_doors.length) { hide(); return; }

    var hit = pickNear(_doors, me.x, me.y, _shownId);
    if (!hit) { hide(); return; }

    var pt = screenFor(hit.door, ctx);
    if (!pt) { hide(); return; }

    if (!mkPrompt()) return;
    var d = hit.door;
    _tapDoor = d;

    // DOM WRITES ONLY ON CHANGE. This runs every frame; re-assigning textContent and a 400-char
    // cssText at 60fps forces layout on a phone for no reason. The DEF chip at index.html:3596
    // uses the same lastTxt guard.
    if (_shownId !== d.id) {
      _shownId = d.id;
      _title.textContent = 'ENTER ' + String(d.label || '').toUpperCase();
      _sub.textContent = sublineFor(d);
      var css = '#' + ('000000' + d.col.toString(16)).slice(-6);
      _pill.style.borderColor = css;
      _title.style.color = css;
      _stem.style.background = 'linear-gradient(180deg,' + css + 'b3,' + css + '00)';
      _shownArmed = null;
    }
    // ARMED = the host will actually let you in from here (index.html:976, me.r+40). The state
    // change is the honest part: the pill only promises entry once entry is genuinely available.
    if (_shownArmed !== hit.armed) {
      _shownArmed = hit.armed;
      _pill.style.boxShadow = hit.armed
        ? ('0 6px 18px rgba(0,0,0,.55), 0 0 22px ' + ('#' + ('000000' + d.col.toString(16)).slice(-6)) + '66')
        : '0 6px 18px rgba(0,0,0,.55)';
      _pill.style.opacity = hit.armed ? '1' : '0.88';
    }

    // Size falls off with distance so the prompt sits in the world rather than on the glass.
    // Clamped hard at 0.82 -- below that the sub-line stops being legible on a 412px phone, and
    // an unreadable prompt is the same as no prompt.
    var s = 1.10 - 0.28 * Math.min(1, hit.dist / SHOW_R);
    if (s < 0.82) s = 0.82;
    _el.style.transform = 'translate(' + Math.round(pt.sx) + 'px,' + Math.round(pt.sy) +
                          'px) translate(-50%,-100%) scale(' + s.toFixed(3) + ')';
    if (!_visible) { _visible = true; _el.style.display = 'flex'; }
  }

  /* The sub-line. b.act is authored per building in the zone record (index.html:841 B(...,act)) --
   * "garden / sunflower land", "production: gems", "the SHOP". That is the truest description
   * available and it is DATA. AK_PORTAL.route(b).mode is the fallback: it is the router's own
   * classification of what is behind the door (akportal.js:71), so even an unlabelled building
   * says something true about what happens when you walk in. */
  var MODE_WORD = {
    panel: 'step inside', video: 'step inside',
    minigame2d: 'step in and play', interior3d: 'walk in'
  };
  function sublineFor(d) {
    if (d.act) return d.act;
    try {
      var P = root.AK_PORTAL;
      if (P && typeof P.route === 'function') return MODE_WORD[P.route(d._b).mode] || 'step inside';
    } catch (_e) {}
    return 'step inside';
  }

  /* =========================================================================
     SECTION 7 -- THE STARVATION WATCHDOG

     onTick CANNOT hide the prompt when an interior opens, because index.html:2608 gates
     akTickSystems on `!interiorOpen` -- the tick STOPS at the exact moment the prompt must come
     down, so the last frame's pill would be left frozen on top of the keeper card. A standalone
     interval is the only clock that survives that gate. akportal.js Section 6 hit the identical
     problem for the identical reason and reached the identical answer.

     260ms threshold at a 200ms poll: comfortably longer than a 60fps frame (16ms) or even a
     stuttering 10fps one (100ms), so it never fires on a slow phone, but fast enough that the
     pill is gone before the interior has finished its 240ms fade (akportal.js:204).
     ========================================================================= */

  var _lastTick = 0, _watch = null;
  function nowMs() {
    try { return (root.performance && performance.now) ? performance.now() : Date.now(); }
    catch (_e) { return Date.now(); }
  }
  function armWatch() {
    if (_watch || !HAS_DOM) return;
    try {
      _watch = setInterval(function () {
        if (_visible && nowMs() - _lastTick > 260) hide();
      }, 200);
    } catch (_e) {}
  }

  /* =========================================================================
     SECTION 8 -- THE PLUG-IN

     Self-registers with AK_SYSTEMS, so the <script> tag is the whole host wiring -- _registry.js:22
     tickAll() does the rest, reached from index.html:2608 akTickSystems, already gated on
     IN_ZONE && !interiorOpen && !entering && !storyFocus. That gate is why nothing in here re-tests
     the game state: if this tick is running, the player is on his feet in a district.

     (`ctx.state` deliberately NOT consulted: index.html:1309 declares `state` with top-level `let`
     in a classic script, which binds in SCRIPT scope and never reaches window, and AK_CTX exposes
     no state field. Any module gating its tick on ctx.state is gating on undefined and is a
     permanent no-op -- see the note returned with this file.)

     MUST LOAD AFTER world3d.js. tickAll walks modules in registration order and registration order
     is script order, so ticking later means sync() sees the district world3d rebuilt THIS frame
     (fresh _state.zoneId) and a projector already advanced for this frame. aklod, akinstance,
     akstream and akfacade all sit after world3d for exactly this reason.
     ========================================================================= */

  var api = {
    id: 'akdoors',

    init: function () { armWatch(); return true; },

    onTick: function (dt, ctx) {
      _lastTick = nowMs();
      _t += (dt || 0.016);
      try {
        sync(ctx);
        // Pulse. ONE material for the whole district, so every door breathes in phase. That is a
        // deliberate cost decision, not an oversight: per-door phase would need either N materials
        // (N draw calls, the thing this module exists to avoid) or a per-vertex phase attribute
        // plus a custom shader, and a synchronised breath is not a defect at the distances a
        // player ever sees two doors at once.
        if (_glowMat) _glowMat.opacity = pulseAt(_t);
        updatePrompt(ctx);
      } catch (e) {
        _diag.errors++; _diag.lastErr = String((e && e.message) || e);
      }
    }
  };

  try { if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api); } catch (_e) {}

  /* =========================================================================
     SECTION 9 -- SELF TEST
     `node systems/akdoors.js`. Same convention as world3d.js:290 / akportal.js:534 / akclutter.js:1704:
     the proof ships inside the module. The scene half runs against the REAL vendored three r160
     (assets/vendor/three.module.min.js), because a fake THREE can only prove this file calls the
     methods it thinks it calls -- it cannot prove the merged buffers are well formed or that the
     result is two render items.
     ========================================================================= */

  function selfTest(THREE, log) {
    var fails = [], n = 0;
    function ok(c, label) { n++; if (!c) fails.push(label); }
    function near(a, b, tol, label) { ok(Math.abs(a - b) <= (tol || 1e-6), label + ' (got ' + a + ', want ' + b + ')'); }

    // ---- fixtures: the REAL zone records, index.html:862-869 and 875-878 -------------------
    var HOME = { id: 'HOME_TURF', buildings: [
      { id: 'ARENA',  label: 'TOWN HALL',   col: '#e8c55a', x: 850,  y: 360, w: 210, h: 124, url: 'game.html',              act: 'the main game' },
      { id: 'TROPHY', label: 'TROPHY HALL', col: '#ffd76b', x: 430,  y: 880, w: 160, h: 96,  url: 'soon',                   act: 'trophies / profile' },
      { id: 'KENNEL', label: 'THE KENNEL',  col: '#b6f06b', x: 1270, y: 880, w: 160, h: 96,  url: 'shop/shop.html#handlers', act: 'handlers' },
      { id: 'SILO',   label: 'THE SILO',    col: '#b6f06b', x: 1270, y: 500, w: 160, h: 96,  url: '',                       act: 'garden / sunflower land' }
    ] };
    var ROW = { id: 'FACTORY_ROW', buildings: [
      { id: 'GEM',   label: 'GEM MINE',   col: '#b07bff', x: 520,  y: 540, w: 160, h: 100, url: 'prod', act: 'production: gems' },
      { id: 'MINT',  label: 'GOLD MINT',  col: '#ffd76b', x: 1180, y: 540, w: 160, h: 100, url: 'prod', act: 'production: gold' },
      { id: 'FORGE', label: 'CARD FORGE', col: '#ff9d5c', x: 850,  y: 960, w: 170, h: 104, url: 'prod', act: 'production: cards' }
    ] };

    // ---- 1. enterable is DATA -------------------------------------------------------------
    var hd = doorsFor(HOME, 1700, 1300);
    ok(hd.length === 3, 'HOME_TURF yields 3 doors, not 4 (TROPHY is url:soon), got ' + hd.length);
    ok(!hd.filter(function (d) { return d.id === 'TROPHY'; }).length, 'TROPHY (soon) gets NO door');
    ok(!!hd.filter(function (d) { return d.id === 'SILO'; }).length, "SILO (url:'') DOES get a door -- '' is not 'soon'");
    ok(isEnterable({ url: '' }) && !isEnterable({ url: 'soon' }), 'isEnterable is world3d.js:906 verbatim');

    // ---- 2. the door is ON the host's own entry point --------------------------------------
    // The compatibility proof. index.html:2592: dx = me.x - b.x, dy = me.y - (b.y + b.h/2).
    var silo = hd.filter(function (d) { return d.id === 'SILO'; })[0];
    near(silo.doorX, 1270, 1e-9, 'door x IS b.x (index.html:2592)');
    near(silo.doorY, 500 + 96 / 2, 1e-9, 'door y IS b.y + b.h/2 (index.html:2592)');
    // ...and the wall it is fixed to is world3d's actual box front, not the entry point.
    near(silo.wallZ, 500 + 96 * 0.36, 1e-9, 'wall plane IS b.y + b.h*0.36 (world3d.js:855)');
    ok(silo.doorY - silo.wallZ > 0, 'the entry point stands OUTSIDE the wall, in the street');
    near(silo.doorY - silo.wallZ, 96 * 0.14, 1e-9, 'gap between wall and entry point is b.h*0.14');

    // ---- 3. the light covers the spot where entry actually fires ---------------------------
    // The pool runs from the wall to doorY + POOL_OUT. The host lets you in within DWELL_R of
    // doorY. If the pool stopped short of that, the player would be standing in the dark at the
    // exact moment the game let him in.
    var poolFar = silo.doorY + POOL_OUT;
    ok(poolFar > silo.doorY, 'the pool reaches PAST the entry point');
    near(poolFar - silo.doorY, 44, 1e-9, 'it reaches 44 past -- inside the 53-unit dwell radius');
    ok(POOL_OUT < DWELL_R, 'pool reach (' + POOL_OUT + ') is inside the dwell radius (' + DWELL_R + ')');

    // ---- 4. hero-relative sizing ------------------------------------------------------------
    ok(DOOR_H > HERO, 'the doorway (' + DOOR_H + ') clears the hero (' + HERO + ')');
    near(DOOR_H / HERO, 1.1, 0.001, 'door height is 1.10 x hero');
    ok(DOOR_W < HERO && DOOR_W > HERO * 0.5, 'door width is shoulder-scaled to the hero');
    // Against the shortest and tallest real buildings: h3 = max(90, b.h*1.65) -> 158.4 .. 204.6
    var hMin = Math.max(90, 96 * 1.65), hMax = Math.max(90, 124 * 1.65);
    ok(DOOR_H + LINTEL_H + BAND_H < hMin * 0.6,
       'the whole door assembly fits inside the shortest facade (' + hMin.toFixed(1) + ')');
    ok(hMax > 200, 'tallest authored building is 205-ish as documented, got ' + hMax.toFixed(1));

    // ---- 5. proximity + hysteresis ---------------------------------------------------------
    var far = pickNear(hd, silo.doorX, silo.doorY - 400, '');
    ok(!far, 'no prompt at 400 units');
    var app = pickNear(hd, silo.doorX, silo.doorY + 180, '');
    ok(!!app && app.door.id === 'SILO', 'prompt appears at 180 units');
    ok(app && !app.armed, 'at 180 the prompt is NOT armed -- the host would not let you in');
    var arm = pickNear(hd, silo.doorX, silo.doorY + 40, '');
    ok(!!arm && arm.armed, 'at 40 units the prompt IS armed (inside ENTRY_R ' + ENTRY_R + ')');
    // Hysteresis: 228 is past SHOW_R (210) but inside HIDE_R (246). Isolated to ONE door on
    // purpose -- in the real HOME_TURF, standing 228 south of the SILO puts you 152 from the
    // KENNEL, so a multi-door fixture would prove the nearest-wins rule instead of hysteresis.
    var solo = doorsFor({ id: 'SOLO', buildings: [
      { id: 'SILO', label: 'THE SILO', col: '#b6f06b', x: 1270, y: 500, w: 160, h: 96, url: '' }
    ] }, 1700, 1300);
    ok(!pickNear(solo, 1270, 548 + 228, ''), 'at 228 a NEW door does not appear');
    ok(!!pickNear(solo, 1270, 548 + 228, 'SILO'), 'at 228 the HELD door stays -- no strobe');
    ok(!pickNear(solo, 1270, 548 + 260, 'SILO'), 'past HIDE_R even the held door drops');
    // nearest wins when two are in range
    var mid = pickNear(hd, 1270, 700, '');
    ok(mid && mid.door.id === 'SILO', 'nearest door wins, got ' + (mid && mid.door.id));

    // ---- 6. plaza-face bookkeeping is honest -------------------------------------------------
    // The header's headline measurement, asserted rather than asserted-in-prose.
    ok(silo.plazaFace === 'W', 'SILO (1270,500) has the plaza to its WEST, got ' + silo.plazaFace);
    ok(silo.agrees === false, 'so the plaza wall and the entry wall DISAGREE for SILO');
    var rd = doorsFor(ROW, 1700, 1300);
    var forge = rd.filter(function (d) { return d.id === 'FORGE'; })[0];
    ok(forge.plazaFace === 'N', 'FORGE (850,960) has its plaza face to the NORTH');
    ok(forge.agrees === false, 'and that is RECORDED as a disagreement, not silently ignored');
    near(forge.doorY, 960 + 104 / 2, 1e-9,
         'FORGE door still lands on the ENTRY face -- a door you cannot open is the bug being fixed');
    var arena = hd.filter(function (d) { return d.id === 'ARENA'; })[0];
    ok(arena.plazaFace === 'S' && arena.agrees === true,
       'ARENA is the ONE building of 16 where the two rules agree');

    // ---- 7. colour comes from the zone record ------------------------------------------------
    ok(silo.col === 0xb6f06b, 'SILO carries its own #b6f06b, got 0x' + silo.col.toString(16));
    ok(forge.col === 0xff9d5c, 'FORGE carries its own #ff9d5c');
    ok(doorsFor({ id: 'X', buildings: [{ id: 'Q', x: 1, y: 1, w: 10, h: 10, url: '' }] })[0].col === 0xe8c55a,
       'a building with no col falls back to hub gold, it does not throw');

    // ---- 8. the sub-line is data ------------------------------------------------------------
    ok(sublineFor(silo) === 'garden / sunflower land', 'sub-line is the zone record act field');
    ok(sublineFor({ act: '', _b: { id: 'GEM' } }) === 'step inside',
       'with no act it falls through the AK_PORTAL mode map without throwing');

    // ---- 9. the scene layer, against REAL three ---------------------------------------------
    if (!THREE) {
      log('SKIP  scene layer: three not loadable in this process');
    } else {
      var scene = new THREE.Scene();
      var st = { scene: scene, zoneId: 'HOME_TURF', blds: [] };
      _built = ''; _frame = null; _glow = null; _glowMat = null;
      build(THREE, st, HOME, 1700, 1300);

      ok(!!_frame, 'a frame mesh was built');
      ok(!!_glow, 'a glow mesh was built');
      ok(scene.children.length === 2, 'EXACTLY 2 objects added for the whole district, got ' + scene.children.length);
      ok(_diag.drawCalls === 2, 'draw calls = 2 regardless of door count, got ' + _diag.drawCalls);
      ok(st.blds.length === 0, 'nothing was pushed into st.blds -- akcull.js:484 must not claim these');

      // 3 doors x (5 boxes x 36 verts + 2 quads x 6 verts) = 3 x 192 = 576
      var perDoor = 5 * 36 + 2 * 6;
      ok(_diag.verts === 3 * perDoor,
         'vertex count is 3 doors x ' + perDoor + ' = ' + (3 * perDoor) + ', got ' + _diag.verts);
      var tris = _diag.verts / 3;
      ok(tris === 192, 'the whole district costs ' + tris + ' triangles');

      // buffers well formed
      var pa = _frame.geometry.attributes.position, ca = _frame.geometry.attributes.color,
          na = _frame.geometry.attributes.normal;
      ok(pa.count === ca.count && pa.count === na.count, 'frame position/normal/colour counts match');
      var pg = _glow.geometry.attributes.position;
      ok(pg.count === 3 * 2 * 6, 'glow holds 2 quads per door = ' + (3 * 2 * 6) + ' verts, got ' + pg.count);
      ok(_frame.material.vertexColors === true, 'frame runs vertexColors (one material, one call)');
      ok(_glow.material.blending === THREE.AdditiveBlending, 'glow is additive');
      ok(_glow.material.depthWrite === false, 'glow does not write depth -- it cannot occlude the hero');
      ok(_glow.material.side === THREE.DoubleSide, 'glow is double sided across the full 360 yaw');

      // GEOMETRY LANDS ON THE RIGHT WALL. Take the frame's bounding box and check it hugs the
      // SILO/KENNEL/ARENA walls rather than floating in the street or sinking into the building.
      _frame.geometry.computeBoundingBox();
      var bb = _frame.geometry.boundingBox;
      ok(bb.min.y >= -0.01, 'nothing dips below the ground plane (min y ' + bb.min.y.toFixed(2) + ')');
      near(bb.max.y, DOOR_H + LINTEL_H + BAND_H, 0.01, 'frame tops out at the sign band');
      // ARENA is the northernmost door (y 360 + 62 = 422) and KENNEL/TROPHY the southernmost.
      // ARENA wall z = 360 + 124*0.36 = 404.64, frame plane 407.14, step out to 416.64.
      var arenaWall = 360 + 124 * 0.36;
      ok(bb.min.z >= arenaWall - JAMB_W, 'no door geometry sits north of the ARENA wall');

      // The pool must reach the entry point of the SOUTHERNMOST door (KENNEL, doorY = 928).
      _glow.geometry.computeBoundingBox();
      var gb = _glow.geometry.boundingBox;
      ok(gb.max.z >= 928 + POOL_OUT - 0.01,
         'the light reaches ' + POOL_OUT + ' past the furthest entry point, got ' + gb.max.z.toFixed(1));
      // gb.min.y is 0, not POOL_Y -- the lit PANEL runs down to the sill at y=0. So assert the
      // pool's own plane by finding it: every vertex at the far edge of a pool quad sits at POOL_Y.
      var gpos = _glow.geometry.attributes.position, foundPool = 0;
      for (var gi = 0; gi < gpos.count; gi++) {
        if (Math.abs(gpos.getY(gi) - POOL_Y) < 1e-6) foundPool++;
      }
      ok(foundPool === 3 * 6, 'each door contributes exactly one 6-vert pool quad at y=' + POOL_Y +
                              ', got ' + foundPool);
      ok(POOL_Y < 1.5 && POOL_Y > 0,
         'the pool lies under world3d\'s door ring (y ' + POOL_Y + ' vs 1.5) and above the plate');
      near(gb.min.y, 0, 1e-6, 'the lit panel runs all the way down to the sill');

      // Pulse band, measured off the SHIPPING pulseAt() across a full period.
      var lo = 9, hi = -9;
      for (var k = 0; k <= 240; k++) {
        var v = pulseAt((k / 240) * PULSE_S);
        if (v < lo) lo = v; if (v > hi) hi = v;
      }
      near(lo, GLOW_BASE - GLOW_AMP, 0.005, 'pulse floor');
      near(hi, GLOW_BASE + GLOW_AMP, 0.005, 'pulse ceiling');
      ok(lo > 0.1, 'the door never goes fully dark mid-pulse (floor ' + lo.toFixed(2) + ')');
      ok(hi < 0.75, 'and never blows out to opaque (ceiling ' + hi.toFixed(2) + ')');
      ok(PULSE_S > 2, 'the breath is slower than any alert fx (' + PULSE_S + 's)');

      // DISTRICT SWAP: the meshes must come down, or HOME_TURF's doors stand in FACTORY_ROW.
      // This is the akinstance.js trap -- world3d.setZone reuses the same Scene.
      var st2 = { scene: scene, zoneId: 'FACTORY_ROW', blds: [] };
      var fakeCtx = { activeZone: ROW, world: { WORLD_W: 1700, WORLD_H: 1300 } };
      // sync() needs live globals; drive build/teardown directly, which is what sync() calls.
      teardown(st2);
      ok(scene.children.length === 0, 'teardown removes BOTH meshes, got ' + scene.children.length);
      build(THREE, st2, ROW, 1700, 1300);
      ok(scene.children.length === 2, 'the new district builds its own 2, got ' + scene.children.length);
      ok(_diag.doors === 3, 'FACTORY_ROW has 3 doors (all 3 are prod, none soon)');
      ok(_diag.plazaMismatch === 3,
         'all 3 FACTORY_ROW doors disagree with their plaza face (GEM=E MINT=W FORGE=N), got ' +
         _diag.plazaMismatch);
      ok(!!fakeCtx, 'ctx fixture built');

      // Every district, end to end: still 2 draw calls, never a throw.
      var ALL = [HOME, ROW,
        { id: 'DOWNTOWN', buildings: [
          { id: 'DROP', label: 'THE DROP', col: '#ff8fae', x: 560, y: 560, w: 170, h: 104, url: 'shop/shop.html#gems', act: 'the SHOP' },
          { id: 'GARAGE', label: 'THE GARAGE', col: '#7fc8ff', x: 1140, y: 560, w: 170, h: 104, url: 'shop/shop.html#deck', act: 'deck builder' }] },
        { id: 'THE_STRIP', buildings: [
          { id: 'STREET', label: 'THE STREET', col: '#7CFFb0', x: 560, y: 560, w: 160, h: 96, url: 'shop/shop.html#street', act: 'street mode' },
          { id: 'ARCADE', label: 'THE ARCADE', col: '#7CFFE0', x: 1140, y: 560, w: 160, h: 96, url: 'soon', act: 'mini-games' }] },
        { id: 'THE_OVERLOOK', buildings: [] }];
      var worst = 0, totalDoors = 0;
      for (var z = 0; z < ALL.length; z++) {
        var stz = { scene: new THREE.Scene(), zoneId: ALL[z].id, blds: [] };
        _built = ''; _frame = null; _glow = null; _glowMat = null;
        build(THREE, stz, ALL[z], 1700, 1300);
        worst = Math.max(worst, _diag.drawCalls);
        totalDoors += _diag.doors;
        ok(_diag.drawCalls <= 2, ALL[z].id + ' costs <= 2 draw calls, got ' + _diag.drawCalls);
      }
      ok(worst === 2, 'worst district still 2 draw calls, got ' + worst);
      ok(totalDoors === 3 + 3 + 2 + 1 + 0,
         'THE_STRIP contributes 1 door not 2 (ARCADE is soon) and THE_OVERLOOK 0; total ' + totalDoors);
      ok(_diag.errors === 0, 'zero build errors across every district, got ' + _diag.errors);

      // naive-vs-merged, the number the merge exists for
      var naive = totalDoors * 7;
      log('      draw calls: naive ' + naive + ' meshes -> merged 2 per district');
    }

    return { pass: n - fails.length, total: n, fails: fails };
  }

  /* =========================================================================
     SECTION 10 -- PUBLISH
     ========================================================================= */
  var PUBLIC = {
    // data
    doorsFor: doorsFor, isEnterable: isEnterable, pickNear: pickNear,
    // constants other lanes may want to agree with rather than re-derive
    HERO: HERO, DOOR_W: DOOR_W, DOOR_H: DOOR_H,
    ENTRY_R: ENTRY_R, DWELL_R: DWELL_R, SHOW_R: SHOW_R, HIDE_R: HIDE_R,
    // introspection
    doors: function () { return _doors.slice(); },
    diag: function () {
      return { zone: _diag.zone, doors: _diag.doors, drawCalls: _diag.drawCalls,
               verts: _diag.verts, builds: _diag.builds, errors: _diag.errors,
               lastErr: _diag.lastErr, plazaMismatch: _diag.plazaMismatch,
               promptVisible: _visible, promptFor: _shownId,
               built: _built, hasFrame: !!_frame, hasGlow: !!_glow };
    },
    // manual controls (debug / future lanes)
    hidePrompt: hide,
    rebuild: function () { var st = sceneOf(); teardown(st); return sync(root.AK_CTX); },
    selfTest: selfTest
  };

  // Published on window for the browser (the <script> tag is the whole wiring -- registration
  // above already put us in the tick), and on module.exports so `node systems/akdoors.js` and
  // any future *.test.js can require the pure half without a DOM.
  if (root && root.document) root.AK_DOORS = PUBLIC;
  if (typeof module !== 'undefined' && module.exports) module.exports = PUBLIC;
  return PUBLIC;

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node systems/akdoors.js`. Loads the REAL vendored three r160 so the scene half is
   proved against the same library the browser runs, not against a mock of it. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  (function () {
    var API = module.exports;
    var lines = [];
    function log(s) { lines.push(s); }
    function report(res) {
      lines.forEach(function (l) { console.log(l); });
      console.log('[AK_DOORS selfTest] ' + res.pass + '/' + res.total + ' passed');
      if (res.fails.length) {
        console.log('FAILURES:');
        res.fails.forEach(function (f) { console.log('  - ' + f); });
        process.exit(1);
      }
    }
    import('../assets/vendor/three.module.min.js').then(function (T) {
      report(API.selfTest(T, log));
    }, function (e) {
      log('SKIP  three not loadable: ' + ((e && e.message) || e));
      report(API.selfTest(null, log));
    });
  })();
}
