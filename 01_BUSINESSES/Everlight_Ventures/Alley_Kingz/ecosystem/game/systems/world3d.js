/* Alley Kingz -- 3D DISTRICT WORLD (window.AK_WORLD3D)
 *
 * AK-WORLD3D 2026-07-18. ADDITIVE renderer. This file never rewrites the hub.
 * With Three.js absent it is a TOTAL no-op: no DOM, no globals touched, no canvas
 * stolen, and the Canvas2D hub does not know it exists.
 *
 * ---------------------------------------------------------------------------
 * WHY THIS SHAPE: the wx/wy seam
 * ---------------------------------------------------------------------------
 * index.html:3178 exposes the ONLY camera interface the plugin layer has:
 *
 *     world:{ ... wx:function(x){return x-cam.x;}, wy:function(y){return y-cam.y;}, ... }
 *
 * Every plugin system draws through it. All 24 real call sites (raid.js:644,
 * production.js:252, encounters.js:297, missions.js:557, buildmode.js:1285,
 * trading.js:705, worldverbs.js:1023, worldmap.js:1881, karma.js:449,
 * population.js:986, mission_active.js:450, marketplace.js:1283, ...) use the
 * SAME idiom:  var X = ctx.world.wx(a.x), Y = ctx.world.wy(a.y);
 *
 * Note what that signature forbids: wx() is handed ONE coordinate. Under a freely
 * yawed 3D camera, screen-x is a function of BOTH world x and y, so a 1-arg wx()
 * is mathematically unable to be correct. That is not a thing to paper over with
 * a latch; it is the actual constraint, and it decides the design:
 *
 *   COMPAT MODE (yaw locked, orthographic)  -> projection SEPARATES, so wx(x) and
 *     wy(y) stay exactly correct with ZERO plugin edits:
 *        sx = (x - camCx)*zoom + W/2
 *        sy = (y - camCy)*zoom*cos(phi) + H/2 - height*zoom*sin(phi)
 *     sx reads only x, sy reads only y. This is a strict GENERALIZATION of the
 *     hub: at zoom=1, phi=0 it reduces to x-cam.x / y-cam.y, bit for bit. That
 *     is the migration path that carries all ~15 plugin systems onto the 3D
 *     camera at once, and it is proven with real numbers in selfTest() below.
 *
 *   CINEMATIC MODE (free yaw, perspective) -> NOT separable. separable() returns
 *     false and the host must keep the flat 2D fallback for plugin draws. The
 *     3D scene still renders; only the 2D overlay projection stays flat.
 *
 * ---------------------------------------------------------------------------
 * THE ONE-LINE MIGRATION (index.html is LOCKED -- do NOT edit it here)
 * ---------------------------------------------------------------------------
 * When the orchestrator is ready to put the plugin layer on the 3D camera, the
 * ONLY change needed at index.html:3178 is to swap those two lambdas for:
 *
 *   wx:function(x){ var P=window.AK_WORLD3D; return (P&&P.separable())?P.wx(x):(x-cam.x); },
 *   wy:function(y){ var P=window.AK_WORLD3D; return (P&&P.separable())?P.wy(y):(y-cam.y); },
 *
 * separable() is false whenever this module is off, Three is missing, or the
 * camera is yawed, so that edit is safe to land BEFORE the 3D scene works.
 * Nothing else in index.html changes. No plugin changes at all.
 *
 * ---------------------------------------------------------------------------
 * ENGINE GATE -- the REAL three_boot.js contract (systems/three_boot.js)
 * ---------------------------------------------------------------------------
 * Verified against the real file, not assumed:
 *   AK_THREE.ok()    -> false until the async vendor load resolves. A purely
 *                       synchronous ok() check would NEVER boot, so init() awaits
 *                       AK_THREE.ready() once and boots from the .then.
 *   AK_THREE.get()   -> the namespace. It is NOT AK_THREE.THREE.
 *   AK_THREE.addon() -> ADDONS is {OrbitControls, GLTFLoader} (three_boot.js:103).
 *   AK_THREE.loadGLB(url,onLoad,onErr) -> three_boot.js:175. The PREFERRED hero
 *                       path: three_boot owns the loader lifecycle, so we do not
 *                       construct a second GLTFLoader. addon('GLTFLoader') is the
 *                       fallback for an older three_boot that predates loadGLB.
 * AK-WORLD3D-FIX 2026-07-18: an earlier revision of this header claimed
 * addon('GLTFLoader') "resolves null". That was true when this file was written
 * and is FALSE against the current three_boot.js -- the hero GLB now really loads.
 * With three_boot.js absent, or the vendor file 404ing, ok() stays false forever
 * and this module is a total no-op.
 *
 * ONE RENDERER LAW (three_boot.js budget block): a phone starts evicting WebGL
 * contexts around 8, and hub3d already spends up to 5 on model-viewer. The 3D
 * world, the FPS view and the isometric builder are mutually exclusive modes, so
 * they MUST share ONE WebGLRenderer. This module publishes that singleton at
 * window.AK_R3D and reuses an existing one if another lane got there first.
 * Whichever lane boots first owns creation; nobody constructs a second.
 * Entering 3D also parks hub3d's ally pool (window.__ak3d.on=false) to free up to
 * 4 contexts, and restores it on exit.
 *
 * hub3d.js already proves WebGL composites over the 2D canvas on the target
 * device (it pins a live model-viewer). This module is the same trick at scene
 * scale: WebGL canvas UNDER, Canvas2D hub + HUD + plugin draws OVER, exactly as
 * hub3d.js does in reverse.
 *
 * ---------------------------------------------------------------------------
 * COMPOSITING -- VERIFIED against the real CSS, and it needs ONE host edit
 * ---------------------------------------------------------------------------
 * AK-WORLD3D-FIX 2026-07-18. An earlier revision mounted the GL canvas with
 * z-index:0 and a comment saying "UNDER the 2D canvas". Both halves were wrong:
 *
 *   1. index.html:13 is  #c{display:block;width:100vw;height:100vh;}  -- NO
 *      position property, so #c is STATIC. In CSS painting order a POSITIONED
 *      element (our position:fixed canvas) paints ABOVE all non-positioned
 *      in-flow block descendants regardless of DOM order, so insertBefore() +
 *      z-index:0 put the GL canvas OVER the whole game, not under it.
 *   2. Even mounted correctly under, it would be invisible: index.html:2463 is
 *      draw(){ctx.fillStyle=curTint();ctx.fillRect(0,0,W,H); -- the hub repaints
 *      an OPAQUE full-screen tint every single frame.
 *
 * So the GL canvas now mounts at z-index:-1 (the negative-z group, which paints
 * beneath in-flow blocks), and while 3D is ON we clear body's opaque background
 * so the negative layer is actually reachable. html keeps its own #06060a, so
 * the page never flashes white. Both are restored on setOn(false)/dispose().
 *
 * THE ONE HOST EDIT THIS STILL NEEDS (index.html is LOCKED -- orchestrator only):
 * at index.html:2463, skip the opaque ground fill while 3D owns the ground:
 *
 *   function draw(){ var _w3=window.AK_WORLD3D;
 *     if(_w3&&_w3.isOn())ctx.clearRect(0,0,W,H); else {ctx.fillStyle=curTint();ctx.fillRect(0,0,W,H);}
 *
 * Until that lands, this module still renders correctly but is occluded by the
 * hub's own fill, which is WHY it ships default-OFF (see setOn below). That is
 * the honest state: the scene is real, the last centimetre is a host one-liner.
 */
(function (root) {
  'use strict';

  /* =====================================================================
   * PURE PROJECTION CORE -- no DOM, no globals, requireable in node.
   * ===================================================================== */

  var DEG = Math.PI / 180;
  var PHI_MAX = 88 * DEG;      // 0 = top-down, 88 = all but eye level. Not 90: at exactly 90 the
                               // view direction is parallel to world-up and the camera basis
                               // degenerates (the classic gimbal flip), so the last 2 degrees are
                               // deliberately withheld.
  /* CAMERA MODES. camPos() had NO EYE-HEIGHT TERM -- camera height was purely dist*cos(phi), so at
   * any walking distance the camera sat on the floor. `eye` lifts it to head height, which is what
   * makes FPP and over-shoulder TPP possible at all. Hero is 60 units tall, so 52 is roughly his
   * eyeline and 90 is a camera floating just above and behind him.
   *   tpp -- default. Over-the-shoulder, Call of Duty third person. Horizon visible, city read as
   *          walls around you rather than roofs below you.
   *   fpp -- first person. dist collapses to almost nothing and the eye sits at the hero's head.
   *   map -- the old overhead survey view, kept for the district map and buildmode. */
  /* AK-FOLLOW 2026-07-20 -- HOW A REAL THIRD-PERSON CAMERA BEHAVES.
   * Operator: "when I walk left the whole world does a 3D spin... the world needs to stay
   * stationary while my character walks through it... look how WoW does it, the world slowly
   * moves around the character."
   * The first cut followed the hero's INSTANTANEOUS heading in ANY direction at 10% of the error
   * per frame. Measured: that swings the world 90 degrees in 0.70s off a single sideways step.
   * Two separate mistakes, and the second is the real one:
   *   RATE      too fast -- reads as a spin, not a drift.
   *   STRUCTURE it followed EVERY direction. In WoW/GTA a sideways step is a STRAFE: the character
   *             slides and the camera does NOT rotate. Only sustained FORWARD travel draws it
   *             round. Following sideways motion also CLOSES A FEEDBACK LOOP -- input is
   *             camera-relative, so rotating the camera redefines "left", the hero curves, and the
   *             camera chases again. That loop is the spin he is describing.
   * Follow is now gated four ways: dead zone, forward cone, slow rate, suspend-after-drag.
   */
  var FOLLOW_DEADZONE = 34 * Math.PI / 180;  // inside this the world does NOT move at all
  var FOLLOW_CONE     = 68 * Math.PI / 180;  // only headings within this of camera-forward pull it
  var FOLLOW_SUSPEND  = 1.25;                // seconds of no auto-follow after a manual drag

  var CAM_MODES = {
    // MEASURED, not guessed: at phi 74 / dist 300 / eye 92 the camera sat 175 units up -- ABOVE the
    // 150-205 roofline, i.e. still surveying the city from over the rooftops, which is the exact
    // complaint this mode exists to fix. These numbers put the eye at ~96 (just over the 60-tall
    // hero's head) and 171 behind him, so buildings TOWER over the camera and you read as being
    // down in the street. height = dist*cos(phi) + eye; behind = dist*sin(phi).
    tpp: { phi: 78, dist: 175, eye:  60, follow: 0.014 },
    fpp: { phi: 87, dist:  22, eye:  52, follow: 0.05 },
    map: { phi: 46, dist: 820, eye:   0, follow: 0.00 },
    /* AK-3DC-world3d 2026-07-29 -- Phase 5: one camera rig per GAMEPLAY surface. The index.html HUD
     * lane switches these with AK_WORLD3D.setMode(name). PURELY ADDITIVE -- tpp/fpp/map above keep
     * their exact numbers, so every existing caller and the boot default are untouched.
     *   district -- roaming isometric-mid (Clash/Sunflower). dist 300 PRESERVES the AK-CAMSCALE
     *               close-3rd-person default (makeProjector dist||300 / loadCam cap 380); phi 62
     *               sits inside loadCam's persistable [58,72] band, so the district reads as it ships.
     *   street   -- over-the-shoulder (GTA/Prototype-2). Same rig as tpp, named for the mobs surface.
     *   gulag    -- first person (survival FPS). Same rig as fpp.
     *   tower    -- top-down lane (Clash Royale): near-overhead, pulled back to read a whole lane.
     *   interior -- framed close on the assigned keeper (Sims): tight, gentle tilt, no follow.
     * persist:false marks a TRANSIENT combat/framed rig that must NEVER be saved as the roaming
     * camera -- loadCam would otherwise restore the whole district at e.g. gulag's dist 22. */
    district: { phi: 62, dist: 300, eye: 60, follow: 0.014 },
    street:   { phi: 78, dist: 175, eye: 60, follow: 0.014 },
    gulag:    { phi: 87, dist:  22, eye: 52, follow: 0.05, persist: false },
    tower:    { phi: 34, dist: 720, eye:  0, follow: 0.00, persist: false },
    interior: { phi: 66, dist: 150, eye: 48, follow: 0.00, persist: false }
  };
  var DEFAULT_MODE = 'tpp';

  var DEFAULT_PHI = CAM_MODES[DEFAULT_MODE].phi * DEG;  // AK-TILT 2026-07-19: the shipping default. Far enough off overhead to
                               // show real perspective and the buildings' textured front faces, but
                               // not so low that the 2D sprite layer composited over it skews wrong.
  var PHI_MIN = 0;
  var PHI_EPS = 0.08;          // perspective path only: avoids the up-vector gimbal at dead overhead
  var ZOOM_MIN = 0.55, ZOOM_MAX = 2.2;
  // AK-CAMWALK 2026-07-20 (operator: "we should be walking IN the city not on top of it").
  // DIST_MIN was 260, which made a first-person view unreachable -- the camera could never get
  // closer than 260 units to the hero. phi is the POLAR angle from straight up: 0 = dead overhead,
  // 90 = eye level. The old PHI_MAX of 72 physically could not look at the horizon.
  var DIST_MIN = 18, DIST_MAX = 1150;


  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  // AK-WORLD3D 2026-07-18: the projector owns cam.x/cam.y in the HUB's own units
  // (top-left of the viewport in world space) so the reduction to x-cam.x is literal.
  function makeProjector(o) {
    o = o || {};
    var S = {
      cam:     { x: 0, y: 0 },                  // mirrors index.html cam{} exactly
      W:       o.W || 900,
      H:       o.H || 600,
      worldW:  o.worldW || 1700,                // ZW
      worldH:  o.worldH || 1300,                // ZH
      yaw:     0,                               // radians; 0 = plugin-compatible
      eye:     CAM_MODES[DEFAULT_MODE].eye,     // AK-CAMWALK: camera height above the ground plane
      mode:    DEFAULT_MODE,                    // 'tpp' | 'fpp' | 'map'
      followHold: 0,                            // AK-FOLLOW: seconds left of manual-drag suspension
      follow:  CAM_MODES[DEFAULT_MODE].follow,  // 0 = free yaw, >0 = ease behind the hero's heading
      // AK-TILT 2026-07-19: was `o.phi || 0`, i.e. DEAD OVERHEAD by default, which is why the world
      // read as "the same flat top-down view" even with the 3D scene live. Two consequences, both
      // fixed by tilting: (1) no perspective is visible at 0, and (2) BoxGeometry material order is
      // [+x,-x,+y,-y,+z,-z] so the FACADE TEXTURE sits on +z (the front face) while +y (the top) is
      // flat colour -- looking straight down showed only the untextured top, which is exactly why
      // the buildings looked like solid placeholder blocks. At 52 degrees you see the textured front
      // AND get real foreshortening. Note `|| 0` also meant an explicit 0 could never be requested;
      // this now honours a real numeric 0 for anyone who genuinely wants the old flat hub.
      phi:     (typeof o.phi === 'number' ? o.phi : DEFAULT_PHI),   // polar from straight-up; 0 = flat hub
      zoom:    o.zoom || 1,
      dist:    o.dist || 300,   // AK-CAMSCALE 2026-07-28: was 620 (hero rendered a tiny speck). Close 3rd-person default so a NEW player (no saved cam, loadCam early-returns) also gets presence.
      fov:     o.fov || 55
    };

    function setViewport(W, H) { S.W = W || S.W; S.H = H || S.H; }
    function setWorld(w, h) { S.worldW = w || S.worldW; S.worldH = h || S.worldH; }

    // AK-CAMCENTRE 2026-07-19 (operator bug 1): the hero must walk in place while the MAP moves.
    // Mirrors akCamFollow() at index.html:907, which is the single definition the hub's 5 camera
    // sites now share. Both layers must agree EXACTLY or the 2D sprites detach from the 3D ground.
    //
    // This was `clamp(hx - S.W/2, 0, S.worldW - S.W)` -- the hub's old world-bounds clamp. Two
    // reasons the clamp is gone rather than merely widened:
    //   1. It caused the bug. World 1700x1300 vs a ~900x600 viewport let the camera pan only
    //      800x700 while the hero walked the full 1700x1300; the remainder was the hero sliding.
    //   2. It was a standing PARITY HAZARD. The clamp read S.worldW, which is refreshed only at
    //      boot (world3d.js:748) and on setZone (world3d.js:809), while index.html clamped against
    //      its live WORLD_W -- reassigned to RAID_W=1500 on raid entry (index.html:2089). Any raid
    //      whose setZone did not land left this projector clamping against a stale 1700 while the
    //      hub clamped against 1500, detaching the layers near a map edge. Centring makes cam a
    //      pure function of (hx, S.W), so worldW cannot desync the seam at all.
    // NOTE: S.worldW/S.worldH are still live and still used -- buildGround sizes the ground plate
    // from them (world3d.js:507). Only the CAMERA stopped depending on them.
    function follow(hx, hy) {
      S.cam.x = hx - S.W / 2;
      S.cam.y = hy - S.H / 2;
      return S.cam;
    }

    function camCx() { return S.cam.x + S.W / 2; }
    function camCy() { return S.cam.y + S.H / 2; }

    function orbit(dYaw, dPhi) {
      // AK-FOLLOW: manual camera input parks auto-follow. Without this the assist fights the
      // player's own drag and springs back, which reads as broken rather than assisted.
      if (dYaw || dPhi) S.followHold = FOLLOW_SUSPEND;
      S.yaw += (dYaw || 0);
      while (S.yaw > Math.PI) S.yaw -= Math.PI * 2;
      while (S.yaw < -Math.PI) S.yaw += Math.PI * 2;
      S.phi = clamp(S.phi + (dPhi || 0), PHI_MIN, PHI_MAX);
      return S;
    }
    function setYaw(a) { S.yaw = a || 0; return S; }
    function setPhi(p) { S.phi = clamp(p || 0, PHI_MIN, PHI_MAX); return S; }
    function zoomBy(f) { S.zoom = clamp(S.zoom * (f || 1), ZOOM_MIN, ZOOM_MAX); return S.zoom; }
    function setZoom(z) { S.zoom = clamp(z || 1, ZOOM_MIN, ZOOM_MAX); return S.zoom; }
    function dolly(d) { S.dist = clamp(S.dist + (d || 0), DIST_MIN, DIST_MAX); return S.dist; }

    // TRUE only while wx()/wy() are each a function of their single argument.
    function separable() { return Math.abs(S.yaw) < 1e-6; }

    /* --- COMPAT (separable, orthographic). The wx/wy seam delegates HERE. --- */
    function wx(x) { return (x - camCx()) * S.zoom + S.W / 2; }
    function wy(y, height) {
      return (y - camCy()) * S.zoom * Math.cos(S.phi) + S.H / 2
             - (height || 0) * S.zoom * Math.sin(S.phi);
    }
    // Inverse of the pair above: screen back to the ground plane (tap-to-walk).
    function unwx(sx) { return (sx - S.W / 2) / S.zoom + camCx(); }
    function unwy(sy) {
      var c = Math.cos(S.phi);
      if (c < 1e-6) return camCy();
      return (sy - S.H / 2) / (S.zoom * c) + camCy();
    }

    /* --- CINEMATIC (full perspective orbit). Used for HUD anchoring in 3D. --- */
    function camPos() {
      var p = Math.max(S.phi, PHI_EPS), sp = Math.sin(p), cp = Math.cos(p);
      return {
        x: camCx() + S.dist * sp * Math.sin(S.yaw),
        // AK-CAMWALK 2026-07-20: + S.eye. Without it camera height is dist*cos(phi) alone, which
        // goes to ZERO as phi approaches eye level -- the camera sank into the pavement at exactly
        // the angle needed to walk the city. eye lifts the whole rig to head height.
        y: S.dist * cp + S.eye,
        z: camCy() + S.dist * sp * Math.cos(S.yaw)
      };
    }

    // AK-CAMWALK: switch rig. Returns the mode applied, or null if unknown.
    function setMode(name) {
      var M = CAM_MODES[name]; if (!M) return null;
      S.mode = name; S.phi = clamp(M.phi * DEG, PHI_MIN, PHI_MAX);
      S.dist = clamp(M.dist, DIST_MIN, DIST_MAX); S.eye = M.eye; S.follow = M.follow;
      return name;
    }
    function mode() { return S.mode; }

    /* AUTO-CENTRE THE HORIZON (operator: "not static, but auto center the horizon").
     * Two halves, and both matter:
     *  1. yaw eases toward the hero's heading so the camera settles BEHIND him. Without it you
     *     walk sideways relative to the view and lose your bearings, which is what he described.
     *     Shortest-arc so turning past due-south does not spin the long way round.
     *  2. phi is pulled back to the mode's rest angle, so a stray drag does not leave you staring
     *     at the sky or the pavement forever. That is the "auto centre" -- the horizon returns.
     * Called once per frame with the hero's heading; a follow of 0 (map mode) disables both. */
    function autoCentre(heading, dt, moving) {
      var step = Math.max(0.001, Math.min(0.1, dt || 0.016));
      if (S.followHold > 0) { S.followHold -= step; return S; }   // player is driving; stay out
      if (!S.follow) return S;
      // Standing still must never rotate the world -- a parked hero has no meaningful heading and
      // following its noise is drift for no reason.
      if (moving === false) return S;
      if (typeof heading !== 'number' || !isFinite(heading)) return S;

      var d = heading - S.yaw;
      while (d > Math.PI) d -= Math.PI * 2;
      while (d < -Math.PI) d += Math.PI * 2;
      var ad = Math.abs(d);

      // DEAD ZONE: small heading differences produce ZERO camera motion. This is what makes the
      // world feel stationary while you walk -- ordinary course corrections do not move it.
      if (ad < FOLLOW_DEADZONE) return S;
      // FORWARD CONE: a strafe or a backpedal must not swing the camera. Past the cone the pull is
      // zero, so walking sideways leaves the world exactly where it was.
      if (ad > FOLLOW_CONE) return S;

      // Ramp from the dead-zone edge so correction STARTS at zero instead of snapping to full
      // strength -- a hard edge would jolt every time the heading crossed 34 degrees.
      var ramp = (ad - FOLLOW_DEADZONE) / Math.max(1e-6, (FOLLOW_CONE - FOLLOW_DEADZONE));
      var k = (1 - Math.pow(1 - S.follow, step * 60)) * ramp;
      // Aim at the dead-zone EDGE, not dead centre: the camera settles as soon as the hero is
      // roughly ahead, instead of hunting for perfect alignment forever.
      S.yaw += (d - (d < 0 ? -1 : 1) * FOLLOW_DEADZONE) * k;
      return S;
    }

    // World (hub x, hub y, height) -> screen. Returns depth so callers can cull/sort.
    function project(x, y, height) {
      var C = camPos();
      var tx = camCx(), ty = 0, tz = camCy();
      var fx = tx - C.x, fy = ty - C.y, fz = tz - C.z;
      var fl = Math.hypot(fx, fy, fz) || 1; fx /= fl; fy /= fl; fz /= fl;
      // right = cross(forward, worldUp) with worldUp = (0,1,0)  ->  (-fz, 0, fx)
      var rx = -fz, ry = 0, rz = fx;
      var rl = Math.hypot(rx, ry, rz) || 1; rx /= rl; ry /= rl; rz /= rl;
      // up = cross(right, forward)
      var ux = ry * fz - rz * fy, uy = rz * fx - rx * fz, uz = rx * fy - ry * fx;

      var dx = x - C.x, dy = (height || 0) - C.y, dz = y - C.z;
      var pz = dx * fx + dy * fy + dz * fz;
      if (pz <= 1) return { sx: 0, sy: 0, depth: pz, scale: 0, vis: false };
      var px = dx * rx + dy * ry + dz * rz;
      var py = dx * ux + dy * uy + dz * uz;
      var focal = (S.H / 2) / Math.tan(S.fov * DEG / 2);
      var sx = S.W / 2 + focal * px / pz;
      var sy = S.H / 2 - focal * py / pz;
      return {
        sx: sx, sy: sy, depth: pz, scale: focal / pz,
        vis: (sx > -240 && sx < S.W + 240 && sy > -240 && sy < S.H + 240)
      };
    }

    return {
      state: S, DEG: DEG, PHI_MAX: PHI_MAX,
      setViewport: setViewport, setWorld: setWorld, follow: follow,
      camCx: camCx, camCy: camCy, camPos: camPos,
      orbit: orbit, setYaw: setYaw, setPhi: setPhi,
      zoomBy: zoomBy, setZoom: setZoom, dolly: dolly,
      separable: separable, wx: wx, wy: wy, unwx: unwx, unwy: unwy,
      project: project, setMode: setMode, mode: mode, autoCentre: autoCentre,
      MODES: CAM_MODES
    };
  }

  /* ---------------------------------------------------------------------
   * HEADING TRACKER -- pure, headless, no globals. AK-WORLD3D-FIX 2026-07-18.
   *
   * THE BUG THIS REPLACES: frame() used to read
   *     var fa = (typeof root.faceAngle === 'number') ? root.faceAngle : 0;
   * index.html:731 declares faceAngle with `let`, at the top level of a classic
   * script. Top-level `let`/`const` bind in SCRIPT scope and do NOT become
   * properties of the global object (only `var` and function declarations do).
   * So window.faceAngle is permanently undefined, the ternary always took the
   * else branch, and the 3D hero was pinned at yaw 0 forever -- he slid around
   * the district without ever turning.
   *
   * The tell is in the hub itself: index.html:2545 hands faceAngle to hub3d as an
   * ARGUMENT (__hero3d.pos(X,Y,avMoving,faceDir,me.r*ds,faceAngle,running)) from
   * inside script scope, because reading it off window is not possible.
   *
   * Since index.html is locked we cannot be handed the value, so we DERIVE it from
   * the motion of the position we are already given, which is exactly how the hub
   * derives it too (index.html:2387: faceAngle=Math.atan2(_dy,_dx)). If a future
   * host publishes a real heading we prefer it -- see headingFrom() in frame().
   *
   * HOLD-ON-STOP: below the movement epsilon we keep the last heading instead of
   * snapping to 0, so a stopped hero stays facing where he was walking.
   */
  var HEAD_EPS = 0.35;          // world units per frame; below this the hero is "stopped"

  function makeHeading() {
    var H = { a: 0, x: null, y: null, moving: false };
    H.update = function (x, y) {
      if (typeof x !== 'number' || typeof y !== 'number') return H.a;
      if (H.x === null) { H.x = x; H.y = y; return H.a; }
      var dx = x - H.x, dy = y - H.y;
      H.x = x; H.y = y;
      if (Math.hypot(dx, dy) < HEAD_EPS) { H.moving = false; return H.a; }
      H.moving = true; H.a = Math.atan2(dy, dx);
      return H.a;
    };
    H.reset = function () { H.a = 0; H.x = null; H.y = null; H.moving = false; };
    return H;
  }

  /* --- Headless proof. Real numbers, no mocks, run via `node world3d.js`. --- */
  function selfTest() {
    var out = [], ok = true;
    function eq(label, a, b, tol) {
      var pass = Math.abs(a - b) <= (tol || 1e-9);
      if (!pass) ok = false;
      out.push((pass ? 'PASS ' : 'FAIL ') + label + '  got=' + a + ' want=' + b);
    }
    // Real hub constants: ZW=1700 ZH=1300 (index.html:552), hero spawn me={x:850,y:650} (index.html:712).
    // AK-PLR3D 2026-07-19: `phi: 0` is now EXPLICIT. When AK-TILT changed the default from 0 to
    // DEFAULT_PHI (52 deg) it silently broke the four identity assertions below -- they assert the
    // reduction wy(y) == y-cam.y, which only holds at phi=0, and they had been FAILING ever since
    // (`node systems/world3d.js` printed FAILURES PRESENT). A failing proof is a proof nobody can
    // gate a ship on, which is exactly when it stops catching anything. The AK-TILT note at
    // makeProjector already promises a real numeric 0 is honoured; this is the call site that
    // depends on that promise.
    var P = makeProjector({ W: 900, H: 600, worldW: 1700, worldH: 1300, phi: 0 });
    P.follow(850, 650);
    // AK-CAMCENTRE: hub does akCamFollow() -> cam.x = me.x - W/2 = 850-450 = 400 (index.html:909).
    // The spawn is the world CENTRE, so the old clamp produced these same numbers -- which makes this
    // pair a useful control: it holds identically before and after the fix, and the projection
    // assertions below (which depend on cam) are therefore unchanged by the camera change.
    eq('cam.x matches hub akCamFollow', P.state.cam.x, 400);
    eq('cam.y matches hub akCamFollow', P.state.cam.y, 350);
    // IDENTITY: at zoom=1, phi=0 the 3D projector IS the current 2D seam.
    // Real building: HOME_TURF TOWN HALL at (850,360) (index.html:683).
    eq('wx == x-cam.x  (TOWN HALL)', P.wx(850), 850 - 400);
    eq('wy == y-cam.y  (TOWN HALL)', P.wy(360), 360 - 350);
    // Real building: INFIRMARY at (1270,500) (index.html:686).
    eq('wx == x-cam.x  (INFIRMARY)', P.wx(1270), 1270 - 400);
    eq('wy == y-cam.y  (INFIRMARY)', P.wy(500), 500 - 350);
    // AK-CAMCENTRE 2026-07-19: the hero stays SCREEN-CENTRED everywhere, including the corners the
    // old clamp used to pin. These four used to assert the clamp (cam pinned to 0 / worldW-W); that
    // pinning WAS operator bug 1, so they now assert the opposite and would fail if it came back.
    // The invariant that matters: hero screen pos == viewport centre, at every world position.
    function screenOf(hx, hy) { P.follow(hx, hy); return { sx: hx - P.state.cam.x, sy: hy - P.state.cam.y }; }
    var corners = [[60, 60], [1640, 60], [60, 1240], [1640, 1240], [850, 650], [20, 20], [1680, 1280]];
    for (var ci = 0; ci < corners.length; ci++) {
      var sc = screenOf(corners[ci][0], corners[ci][1]);
      eq('hero screen-centred x @' + corners[ci][0] + ',' + corners[ci][1], sc.sx, 450);
      eq('hero screen-centred y @' + corners[ci][0] + ',' + corners[ci][1], sc.sy, 300);
    }
    // PARITY with the hub. akCamFollow() at index.html:907 is cam.x=me.x-W/2, cam.y=me.y-H/2.
    // Recomputed here independently -- if either layer's rule is edited alone, this fails.
    function hubCam(mx, my, w, h) { return { x: mx - w / 2, y: my - h / 2 }; }
    var parity = [[850, 650], [60, 60], [1640, 1240], [9999, 9999], [-500, -500]];
    for (var pi = 0; pi < parity.length; pi++) {
      var hc = hubCam(parity[pi][0], parity[pi][1], 900, 600);
      P.follow(parity[pi][0], parity[pi][1]);
      eq('3D cam.x == hub akCamFollow @' + parity[pi][0], P.state.cam.x, hc.x);
      eq('3D cam.y == hub akCamFollow @' + parity[pi][1], P.state.cam.y, hc.y);
    }
    // PARITY UNDER A STALE setWorld -- the exact raid desync the old clamp could produce.
    // Hub is on RAID_W/RAID_H (1500x1150) while this projector still holds a stale 1700x1300.
    // Under the old clamp these diverged by 200 on x at the map edge; centring makes them equal.
    var Pstale = makeProjector({ W: 900, H: 600, worldW: 1700, worldH: 1300 });   // never told about the raid
    var hcRaid = hubCam(1430, 1080, 900, 600);                                    // hub, WORLD_W=1500 WORLD_H=1150
    Pstale.follow(1430, 1080);
    eq('stale setWorld cannot desync cam.x', Pstale.state.cam.x, hcRaid.x);
    eq('stale setWorld cannot desync cam.y', Pstale.state.cam.y, hcRaid.y);
    // SEPARABILITY: the property the wx/wy seam depends on.
    P.follow(850, 650); P.setPhi(45 * DEG); P.setZoom(1.4);
    eq('separable while yaw=0', P.separable() ? 1 : 0, 1);
    var a = P.wx(1270), b = P.wx(1270);
    eq('wx is a pure function of x', a, b);
    eq('wx(1270) tilted', P.wx(1270), (1270 - 850) * 1.4 + 450);
    eq('wy(500) tilted', P.wy(500), (500 - 650) * 1.4 * Math.cos(45 * DEG) + 300, 1e-9);
    eq('wy height leans up', P.wy(500, 100) < P.wy(500) ? 1 : 0, 1);
    // Round trip through the inverse (this is what tap-to-walk needs).
    eq('unwx round trip', P.unwx(P.wx(1270)), 1270, 1e-9);
    eq('unwy round trip', P.unwy(P.wy(500)), 500, 1e-9);
    // Yaw breaks separability, and separable() must SAY so.
    P.setYaw(30 * DEG);
    eq('yawed => not separable', P.separable() ? 1 : 0, 0);
    // Perspective path stays finite and in front of the camera at the hero.
    P.setYaw(0); P.setPhi(50 * DEG);
    var pr = P.project(850, 650, 0);
    eq('hero projects in front', pr.depth > 0 ? 1 : 0, 1);
    eq('hero projects visible', pr.vis ? 1 : 0, 1);
    eq('hero scale positive', pr.scale > 0 ? 1 : 0, 1);
    var near = P.project(850, 900, 0), far = P.project(850, 200, 0);
    eq('nearer point has smaller depth', near.depth < far.depth ? 1 : 0, 1);
    eq('nearer point has bigger scale', near.scale > far.scale ? 1 : 0, 1);

    // --- HEADING (AK-WORLD3D-FIX 2026-07-18). Proves the hero actually turns. ---
    // Regression guard for the real bug: window.faceAngle is undefined because
    // index.html:731 declares it with `let`, so the old code fed a constant 0 here.
    var Hd = makeHeading();
    eq('first sample seeds, no turn', Hd.update(850, 650), 0);
    // Walk EAST from the spawn: +x is screen-right, atan2(0, +d) = 0.
    eq('east heading', Hd.update(900, 650), 0);
    // Walk SOUTH (+y is screen-down in hub space): atan2(+d, 0) = +PI/2.
    eq('south heading', Hd.update(900, 700), Math.PI / 2, 1e-12);
    // Walk WEST: atan2(0, -d) = PI.
    eq('west heading', Hd.update(850, 700), Math.PI, 1e-12);
    // Walk NORTH: atan2(-d, 0) = -PI/2.
    eq('north heading', Hd.update(850, 650), -Math.PI / 2, 1e-12);
    // Sub-epsilon jitter must HOLD the last heading, not snap the model to 0.
    eq('stopped holds last heading', Hd.update(850.1, 650), -Math.PI / 2, 1e-12);
    eq('stopped clears moving flag', Hd.moving ? 1 : 0, 0);
    // The old broken read, reproduced exactly: a `let` never reaches the global object.
    eq('derived yaw differs from the old constant 0', Hd.a !== 0 ? 1 : 0, 1);
    // A district swap teleports the hero; reset() must stop that becoming a heading.
    Hd.reset();
    eq('reset re-seeds instead of turning', Hd.update(150, 650), 0);
    // Real diagonal: TOWN HALL (850,360) toward INFIRMARY (1270,500) = atan2(140,420).
    Hd.reset(); Hd.update(850, 360);
    eq('diagonal to INFIRMARY', Hd.update(1270, 500), Math.atan2(140, 420), 1e-12);

    /* --- AK-PLR3D 2026-07-19. The player-structure pure core, on real p.builds shapes. ---
     * These are hoisted function declarations defined further down the file; selfTest only ever
     * runs after the IIFE body has executed, so the forward reference is resolved. */
    // The zone filter is the whole bug in miniature: get it wrong and a base renders in the wrong
    // district or not at all. buildmode.js:2011 filters on b.zone === zid, and so must this.
    var builds = [
      { type: 'WALL',  x: 640, y: 704, zone: 'HOME_TURF' },
      { type: 'WALL',  x: 704, y: 704, zone: 'HOME_TURF', rot: 1 },
      { type: 'STONE', x: 768, y: 704, zone: 'DOWNTOWN' },          // different district: must NOT plan
      { type: 'PATH',  x: 640, y: 768, zone: 'HOME_TURF' },
      null,                                                          // a hole left by splice()
      { x: 900, y: 900, zone: 'HOME_TURF' }                          // typeless legacy row
    ];
    var pl = planPlayerStructs(builds, 'HOME_TURF');
    eq('plans only this district', pl.list.length, 3);
    eq('skips a null entry and a typeless row', pl.list.length, 3);
    var plD = planPlayerStructs(builds, 'DOWNTOWN');
    eq('the other district gets its own one structure', plD.list.length, 1);
    eq('district is part of the signature', pl.sig === plD.sig ? 1 : 0, 0);
    // A signature that does not move when a structure moves means a placement never appears.
    var moved = planPlayerStructs([{ type: 'WALL', x: 640, y: 704, zone: 'HOME_TURF' }], 'HOME_TURF');
    var moved2 = planPlayerStructs([{ type: 'WALL', x: 704, y: 704, zone: 'HOME_TURF' }], 'HOME_TURF');
    eq('moving a structure changes the signature', moved.sig === moved2.sig ? 1 : 0, 0);
    eq('an unchanged base has a stable signature',
       planPlayerStructs([{ type: 'WALL', x: 640, y: 704, zone: 'HOME_TURF' }], 'HOME_TURF').sig === moved.sig ? 1 : 0, 1);
    // Rotation must SWAP the footprint, exactly like buildmode.js:476 effDW does for the 2D draw.
    var wallDef = { dw: 76, dh: 42, family: 'wall' };
    var r0 = structBox('WALL', 0, wallDef), r1 = structBox('WALL', 1, wallDef);
    eq('rot0 keeps the authored footprint', r0.w, 76);
    eq('rot0 depth', r0.d, 42);
    eq('rot1 swaps the long axis', r1.w, 42);
    eq('rot1 depth', r1.d, 76);
    eq('rot2 == rot0', structBox('WALL', 2, wallDef).w, 76);
    eq('rot3 == rot1', structBox('WALL', 3, wallDef).w, 42);
    // A circle never swaps -- buildmode.js:476 special-cases shape:'circle' and so does this.
    var potDef = { dw: 42, dh: 42, shape: 'circle', cr: 24, family: 'deco' };
    eq('a circular piece is rotation-invariant', structBox('PLANTER', 1, potDef).w, 42);
    // The branch that keeps an unknown type VISIBLE. `if (!def) continue` is how akinstance.js
    // silently drops every type buildmode does not define; this must return a real box instead.
    var unk = structBox('STORAGE_GOLD', 0, null);
    eq('an unknown type still gets a real footprint', unk.w > 0 && unk.d > 0 ? 1 : 0, 1);
    // Heights come from buildmode's own family table, with PATH the documented special case.
    eq('a wall extrudes to buildmode STRUCT_H', structHeight({ family: 'wall' }, 'WALL'), 46);
    eq('a barricade extrudes to its own height', structHeight({ family: 'barricade' }, 'BARRICADE'), 34);
    eq('PATH is flat, not 26', structHeight({ family: 'deco' }, 'PATH'), 2);
    eq('an unknown family falls back, never to 0', structHeight(null, 'MYSTERY'), 24);

    return { ok: ok, lines: out };
  }

  /* =====================================================================
   * SCENE LAYER -- everything below is GUARDED. Nothing here runs at load.
   * ===================================================================== */

  // AK-WORLD3D 2026-07-18: district ground plates. game/assets/maps/<theme>/L<NN>_<arch>.png
  // (10 themes x 10 levels x 4 archetypes). Falls back to the hub bg PNG the 2D
  // district already paints (index.html:577 DBG), which is always a correct plate.
  var PLATE = {
    HOME_TURF:     { dir: 'the_lot',           arch: 'core',   bg: 'the_lot' },
    DOWNTOWN:      { dir: 'neon_night',        arch: 'core',   bg: 'downtown' },
    NEON_HEIGHTS:  { dir: 'skyline_rooftops',  arch: 'market', bg: 'neon_heights' },
    THE_YARDS:     { dir: 'golden_industrial', arch: 'works',  bg: 'the_yards' },
    FACTORY_ROW:   { dir: 'golden_industrial', arch: 'works',  bg: 'factory_row' },
    THE_STRIP:     { dir: 'casino_strip',      arch: 'market', bg: 'the_strip' },
    THE_DOCKS:     { dir: 'rain_docks',        arch: 'gate',   bg: 'the_docks' },
    THE_OVERLOOK:  { dir: 'crown_citadel',     arch: 'gate',   bg: 'the_overlook' },
    THE_UNDERCITY: { dir: 'undercity_subway',  arch: 'core',   bg: 'the_undercity' }
  };
  // Mirrors index.html:567 FAC. Building id -> facade PNG already on disk.
  var FACADE = {
    ARENA: 'town_hall', TROPHY: 'trophy', FIXER: 'fixer', GARAGE: 'garage', DROP: 'drop',
    KENNEL: 'kennel', CLAN: 'clan', PASS: 'pass', WARD: 'wardrobe', ARCH: 'archive',
    STREET: 'street', ARCADE: 'arcade', GEM: 'gem_mine', MINT: 'gold_mint',
    FORGE: 'card_forge', LAB: 'research_lab', GEN: 'power_gen', INFIRMARY: 'infirmary'
  };

  function plateUrl(zoneId, lvl) {
    var p = PLATE[zoneId];
    if (!p) return '';
    var n = clamp(lvl | 0 || 1, 1, 10);
    return 'assets/maps/' + p.dir + '/L' + (n < 10 ? '0' + n : '10') + '_' + p.arch + '.png';
  }
  function plateFallbackUrl(zoneId) {
    var p = PLATE[zoneId];
    return p ? ('assets/hub/' + p.bg + '_bg.png') : '';
  }
  function facadeUrl(id) { var f = FACADE[id]; return f ? ('assets/hub/' + f + '.png') : ''; }

  // AK-FACADECUT 2026-07-19: the facade PNGs are RGB with NO alpha channel (measured:
  // all 18 are mode RGB). town_hall.png is art on a baked-in black background -- 48.6%
  // of the frame is pure black that a box face renders as an opaque black rectangle,
  // which is the single loudest "this is a photo taped to a cube" tell in the hub.
  // art/facade_alpha_and_roofs.py emits <name>_cut.png with a real alpha channel, cut
  // by a BORDER-CONNECTED FLOOD FILL rather than a global luminance threshold (a global
  // threshold eats the windows and outlines -- 106,357 dark interior pixels survive the
  // flood fill that a threshold would have deleted). Only images that MEASURE as cutouts
  // get a _cut: the other 17 are full-bleed painted storefront scenes with no background
  // to remove, so they have no _cut file and fall through to the original untouched.
  function facadeCutUrl(id) { var f = FACADE[id]; return f ? ('assets/hub/' + f + '_cut.png') : ''; }

  // AK-ROOF 2026-07-19: BoxGeometry material order is [+x, -x, +y, -y, +z, -z], so index
  // 2 is the TOP. It used to get the same flat-colour `side` material as the walls. At
  // the hub's camera pitch the roof is one of the LARGEST visible faces of every building
  // (see the default view: the boxes are read almost top-down), so a flat colour there is
  // a primary reason the scene reads as fake. Textures are procedural + tileable, built
  // by art/facade_alpha_and_roofs.py in the night-alley palette.
  var ROOF_KINDS = ['tar', 'gravel', 'corrugated', 'asphalt'];
  function roofUrl(kind) { return 'assets/hub/roofs/roof_' + kind + '.png'; }
  // Stable per-building pick: the same building always gets the same roof across
  // reloads and district swaps, but neighbours differ so the block is not uniform.
  function roofKindFor(id) {
    var s = String(id || ''), n = 0;
    for (var i = 0; i < s.length; i++) n = (n * 31 + s.charCodeAt(i)) & 0x7fffffff;
    return ROOF_KINDS[n % ROOF_KINDS.length];
  }

  // Hard gate. Returns the REAL three namespace via AK_THREE.get(), or null.
  // Never throws. ok() is false until three_boot's async load resolves.
  function engine() {
    try {
      var T = root && root.AK_THREE;
      if (!T || typeof T.ok !== 'function' || !T.ok()) return null;
      return (typeof T.get === 'function' && T.get()) || null;
    } catch (_e) { return null; }
  }

  var W3 = {
    on: false, booted: false, mount: null, renderer: null, scene: null, camera: null,
    ground: null, blds: [], mass: [], models: [], hero: null, zoneId: '', proj: makeProjector({}), _drag: null,
    head: makeHeading(), _bgWas: null,   // AK-WORLD3D-FIX 2026-07-18: derived hero yaw + body-bg restore
    apron: null, paths: null,  // AK-APRON / AK-PATHS 2026-07-19: same lifetime as `ground`, disposed with it
    // AK-PLR3D / AK-ENTRANCE 2026-07-19. plr/plrMass are the player's own p.builds structures as
    // real geometry; doors/doorMat are the two instanced entrance markers. All four are district
    // scoped and torn down by setZone alongside blds/mass.
    plr: [], plrMass: [], plrSig: '', plrAt: 0, doors: [], doorMat: [],
    // id -> 1 for every AUTHORED building that currently has a real box in the scene. Backs the
    // O(1) hasBox() the host calls per building per frame; see the API note on hasBox.
    bldIds: {},
    // AK-3DC-world3d 2026-07-29 (Phase 6): optional bloom+FXAA post-processing. DEFAULT OFF. The
    // composer is built lazily + async; until it exists (addons not vendored) the plain renderer
    // runs UNCHANGED. _postFailed latches any build/render failure so we never retry-spam or throw.
    postOn: false, _composer: null, _composerTried: false, _postFailed: false,
    _composerSize: { w: 0, h: 0 }, _bloom: null, _fxaa: null
  };

  // AK-WORLD3D 2026-07-18: teardown drops OUR scene but leaves the SHARED renderer
  // alive for the FPS view / iso builder. dispose() only if we own it and no peer does.
  function disposeScene() {
    W3.scene = null; W3.camera = null; W3.ground = null; W3.apron = null; W3.paths = null;
    W3.blds = []; W3.mass = []; W3.hero = null; W3.booted = false; W3.on = false;
    // AK-PLR3D / AK-ENTRANCE: the scene reference is already gone by here, so there is nothing to
    // remove FROM -- just drop the bookkeeping so a re-boot does not think it still owns meshes
    // that belong to a dead Scene. Real disposal happens in setZone, which runs with a live scene.
    W3.plr = []; W3.plrMass = []; W3.plrSig = ''; W3.plrAt = 0; W3.doors = []; W3.doorMat = [];
    // Must clear too, or hasBox() keeps answering true for a disposed scene and the host would
    // permanently stop painting its 2D facades -- buildings would simply vanish.
    W3.bldIds = {};
    try { if (W3.renderer && W3.renderer.domElement) W3.renderer.domElement.style.display = 'none'; } catch (_e) {}
    disposeComposer();   // AK-3DC-world3d 2026-07-29: the composer holds this renderer + scene; drop it with them
    W3.renderer = null;
    restorePool(); bodyBg(false);   // AK-WORLD3D-FIX: never leave body transparent behind us
  }

  // ONE WebGLRenderer for the whole game (three_boot.js budget law). First lane to
  // need one creates it and publishes window.AK_R3D; every other lane reuses it and
  // swaps scene + camera. Never construct a second.
  function sharedRenderer(THREE) {
    var host = root.document && root.document.body;
    if (!host) return null;
    if (root.AK_R3D && root.AK_R3D.domElement) {
      try { root.AK_R3D.domElement.style.display = ''; } catch (_e) {}
      return root.AK_R3D;
    }
    var r;
    try { r = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' }); }
    catch (_e) { return null; }                 // context refused (budget blown): stay 2D
    r.setPixelRatio(Math.min(2, root.devicePixelRatio || 1));   // DPR 3 phones thermal-throttle
    // AK-TONEMAP 2026-07-28: NoToneMapping (the default) clips shadows to pure black, which is most
    // of why the night hub looked like a void. ACES filmic + exposure 1.25 lifts the shadow floor
    // and adds filmic contrast so the scene reads as lit rather than dark. Verified via render.
    try { r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.5; } catch (_tm) {}   // AK-LIGHTUP2 2026-07-28: 1.25->1.5. Exposure is the ONLY brightness lever for the UNLIT MeshBasic ground plate; a render-verified playtest showed the lot still murky. Bumped with the light floor below.
    r.setSize(root.innerWidth || 900, root.innerHeight || 600, false);
    var el = r.domElement;
    el.id = 'ak-world3d';
    // AK-WORLD3D-FIX 2026-07-18: z-index:-1, NOT 0. #c (index.html:13) is static, and a
    // positioned element beats a static one in paint order no matter the DOM order, so
    // z-index:0 mounted this OVER the entire game. The negative-z group paints beneath
    // in-flow blocks, which is the layer we actually want. Starts hidden: default-OFF.
    el.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100dvh;z-index:-1;pointer-events:none;display:none;';
    host.insertBefore(el, host.firstChild);   // under the 2D canvas + HUD, never over
    root.AK_R3D = r; W3.mount = host;
    return r;
  }

  // Free up to 4 model-viewer contexts while a full-3D mode owns the screen.
  function parkPool() {
    try { var p = root.__ak3d; if (p && p.on) { W3._poolWas = true; p.on = false; if (p.clear) p.clear(); } } catch (_e) {}
  }
  function restorePool() {
    try { if (W3._poolWas && root.__ak3d) { root.__ak3d.on = true; W3._poolWas = false; } } catch (_e) {}
  }

  // AK-APRON 2026-07-19: the district plate's base colour, shared with the apron skirt so the two
  // meet at the world rim in the SAME colour and the join cannot be seen. One constant, two call
  // sites (buildGround's plate + buildApron's skirt) -- they must never drift apart.
  var GROUND_COLOR = 0x23262f;   // AK-LIGHTUP: was 0x101018 (near-black); lighter wet-asphalt

  /* AK-APRON 2026-07-19 -- THE "I AM IN THE SKY" FIX.
   *
   * MEASURED, not guessed. The ground plate above is EXACTLY worldW x worldH, so it stops dead at
   * z=0 (the north rim) with nothing behind it. At the shipping camera (phi=52, dist=620, fov=55)
   * the top of the screen looks at ground z = camCy - 1571, but on a 430x880 phone camCy bottoms
   * out at 440 -- so rows above screen-y 203 show NO GROUND AT ALL, just background. Walk to the
   * north wall (me.y=20, the index.html:2542 clamp) and the hero's feet land at sy=210 with his
   * head at sy=157: 87% of his body is silhouetted against empty sky. He is not flying -- he is
   * ground-locked at world3d.js:822 (me.x, 0, me.y) -- but he LOOKS airborne, which is the bug the
   * operator actually reported.
   *
   * PROVEN NOT TO BE BUG 1 IN A COSTUME: re-running the same projection with a perfect, UNCLAMPED
   * follow camera pins the hero at screen centre (sy=440.0 at every me.y) and the sky band is
   * UNCHANGED -- at me.y=20 the north rim still projects to sy=423.6, above his head at sy=371.5.
   * Camera work cannot conjure ground that does not exist. This defect is independent of BUG 1 and
   * needs its own fix; the camera clamp only makes it worse by walking him 230px UP into the band.
   *
   * THE FIX: one oversized skirt under the plate, in the fog colour. Sizing is derived, not picked:
   * the worst case is a fully dollied camera (DIST_MAX=1150) at phi=52, whose top ray reaches
   * camCy-2914, so 3000 units past every edge covers it. It never reads as a visible rim because
   * Fog(0x0d0f18, 420, 1750) saturates at 1750 -- far short of the skirt edge -- so the apron
   * dissolves into haze exactly like a real city horizon. Cost: ONE mesh, two triangles.
   * Sits at y=-0.5 so it can never z-fight the textured plate it backs. */
  function buildApron(THREE) {
    try {
      var S = W3.proj.state, PAD = 3000;
      var geo = new THREE.PlaneGeometry(S.worldW + PAD * 2, S.worldH + PAD * 2, 1, 1);
      // fog: true is the default on MeshBasicMaterial -- that is the whole point here, the skirt
      // is MEANT to fade into Fog's colour rather than end in a hard line.
      //
      // GROUND colour, NOT the sky tint -- and this was caught by RENDERING it, not by reasoning.
      // The first cut of this mesh used W3.skyTint so it could never form a hard horizon rim. It
      // could not: it also could not form anything else. Rendered headless at me.y=20 with the
      // apron on and off, the two PNGs came back BYTE-IDENTICAL (md5 cadb4976...), because a
      // fog-coloured plane in front of a fog-coloured background is invisible by construction.
      // The mesh ran, cost a draw call, and changed not one pixel -- the silent-no-op cousin of
      // the code-nothing-calls bug this repo keeps getting bitten by.
      //
      // Painting it the GROUND colour is what actually fills the void: near the world rim it reads
      // as pavement continuing past the plate edge, and Fog(tint, 420, 1750) blends it toward the
      // sky tint with distance on its own -- so it still cannot end in a hard line, which was the
      // only thing the skyTint version was buying. Matching the plate's own 0x101018 also means the
      // seam AT the rim is between two identical colours, so the join is invisible from any angle.
      var mat = new THREE.MeshBasicMaterial({ color: GROUND_COLOR });
      var a = new THREE.Mesh(geo, mat);
      a.rotation.x = -Math.PI / 2;
      a.position.set(S.worldW / 2, -0.5, S.worldH / 2);
      a.renderOrder = -1;                       // paint before the plate; it is pure backdrop
      W3.scene.add(a); W3.apron = a;
    } catch (_e) { try { console.warn('[world3d] apron failed', _e); } catch (_e2) {} }
  }

  /* AK-PATHS 2026-07-19 -- "I need to be able to follow a path."
   *
   * Reuses the EXISTING lattice: AK_WORLDGEN.planStreets(zoneId, W, H) (akworldgen.js:245), the
   * same seeded generator akclutter.js:269 already lines its props against. No parallel path system
   * is invented here, and no geometry is duplicated -- this only PAINTS what planStreets returns.
   *
   * Why this actually guides you to the buildings -- MEASURED against the real seeded output, not
   * the un-jittered ideal. For HOME_TURF planStreets returns vx centres 187/436/850/1214/1497 and
   * hy centres 132/341/650/977/1176. Distance from each building's DOOR (b.x, b.y+b.h/2, the
   * index.html:2549 trigger point) to the nearest street EDGE:
   *     ARENA  (850,422) vert 0, horiz 36      TROPHY (430,928) vert 0,  horiz 4
   *     KENNEL (1270,928) vert 11, horiz 4     INFIRM (1270,548) vert 11, horiz 27
   * Every door is ON or within a few strides of a carriageway, and the same holds in FACTORY_ROW
   * (max gap 17) and THE_YARDS (max gap 64). The lattice already leads
   * where the operator wants to walk; it was simply invisible.
   *
   * SHIPS DEFAULT-OFF, DELIBERATELY -- see setPaths() below. The district plate is real painted
   * art (assets/maps/the_lot/L01_core.png, 1248x1824) with its own strong light/dark banding, and
   * planStreets' jittered centres are NOT derived from that art, so the lattice can land as a
   * SECOND, misaligned grid on top of a picture the operator has already signed off on. Whether it
   * reads as guidance or as dirt cannot be settled headlessly: the plate texture does not load in a
   * node harness, and this phase is explicitly not allowed to ship. So the geometry is built,
   * disposed and unit-tested, and the visual judgement is left to a phase that can render it in
   * game with the texture present. Flip it with AK_WORLD3D.setPaths(true).
   *
   * DELIBERATELY SUBTLE (opacity 0.16, additive-free, depthWrite off). The district plate art is
   * the look the operator signed off on, so these are a faint sheen that reads as lit asphalt, NOT
   * an opaque grey overlay painted across his artwork. Absent AK_WORLDGEN this is a clean no-op. */
  function buildPaths(THREE, zone) {
    try {
      if (!W3.showPaths) return;                               // default-off; AK_WORLD3D.setPaths(true) arms it
      var G = root.AK_WORLDGEN;
      if (!G || typeof G.planStreets !== 'function') return;   // module not loaded: no-op, plate untouched
      var S = W3.proj.state;
      var st = G.planStreets((zone && zone.id) || 'HOME_TURF', S.worldW, S.worldH);
      if (!st || !st.vx || !st.hy) return;
      var mat = new THREE.MeshBasicMaterial({
        color: 0x2b3040, transparent: true, opacity: 0.16, depthWrite: false
      });
      var grp = new THREE.Group(), i, b;
      function strip(w, h, cx, cz) {
        var q = new THREE.Mesh(new THREE.PlaneGeometry(w, h, 1, 1), mat);
        q.rotation.x = -Math.PI / 2;
        q.position.set(cx, 0.6, cz);          // above the plate (y=0), below the hero's feet
        grp.add(q);
      }
      for (i = 0; i < st.vx.length; i++) { b = st.vx[i]; strip(b.half * 2, S.worldH, b.c, S.worldH / 2); }
      for (i = 0; i < st.hy.length; i++) { b = st.hy[i]; strip(S.worldW, b.half * 2, S.worldW / 2, b.c); }
      grp.renderOrder = 1;
      W3.scene.add(grp); W3.paths = grp;
    } catch (_e) { try { console.warn('[world3d] paths failed', _e); } catch (_e2) {} }
  }

  function buildGround(THREE, zone) {
    var S = W3.proj.state;
    var geo = new THREE.PlaneGeometry(S.worldW, S.worldH, 1, 1);
    var mat = new THREE.MeshBasicMaterial({ color: GROUND_COLOR });   // shared with the apron skirt
    var m = new THREE.Mesh(geo, mat);
    m.rotation.x = -Math.PI / 2;
    m.position.set(S.worldW / 2, 0, S.worldH / 2);
    W3.scene.add(m); W3.ground = m;
    // AK-GROUND 2026-07-20: the plate is PORTRAIT art (all 400 files under assets/maps/ measure
    // aspect 0.6842) on a LANDSCAPE 1700x1300 plane, so it ships stretched 1.9112x, and it is two
    // triangles of MeshBasicMaterial so it cannot carry any surface variation at all. This fixes
    // the aspect in the UV ATTRIBUTE (not in texture.repeat, so it cannot race the plate loader
    // below), subdivides to 48x36, and parents an authored tiled grit overlay to the plate.
    // It reads plate.geometry and sets material.vertexColors; it NEVER touches material.map, so
    // the async load below still lands exactly as it always did. Guarded: on any failure the
    // plate is left precisely as built above.
    try { if (root.AK_GROUND && root.AK_GROUND.apply) root.AK_GROUND.apply(THREE, m, (zone && zone.id) || 'HOME_TURF', S.worldW, S.worldH); } catch (_eG) {}
    buildApron(THREE);            // call site: the ONLY one, and it runs on every ground build
    buildPaths(THREE, zone);      // call site: the ONLY one, same lifetime as the plate
    var lvl = 1;
    try { var LVs = root.AK_CTX && root.AK_CTX.buildingLevels; if (LVs && LVs.ARENA) lvl = LVs.ARENA | 0; } catch (_e) {}
    var urls = [plateUrl(zone.id, lvl), plateFallbackUrl(zone.id)];
    var loader = new THREE.TextureLoader();
    (function tryAt(i) {
      if (i >= urls.length || !urls[i]) return;
      loader.load(urls[i], function (tex) {
        if (!W3.ground) return;
        try { tex.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
        W3.ground.material.map = tex;
        W3.ground.material.color.set(0xffffff);
        W3.ground.material.needsUpdate = true;
      }, null, function () { tryAt(i + 1); });
    })(0);
  }

  // Boxes first, textured with the facade PNG the 2D hub already draws. b.x/b.y are
  // the CENTER (index.html:826 hit-tests |tx-b.x| < b.w/2), so they drop straight in.
  function buildBuildings(THREE, zone) {
    var list = (zone && zone.buildings) || [], loader = new THREE.TextureLoader();
    var doors = [];   // AK-ENTRANCE 2026-07-19: collected here, raised as TWO instanced meshes below
    W3.bldIds = {};   // rebuilt from scratch: a district swap must never leave the old ids answering hasBox
    for (var i = 0; i < list.length; i++) {
      var b = list[i];
      var h = Math.max(140, (b.h || 96) * 2.35);   // AK-BIGGER 2026-07-28: was 90/1.65
      var geo = new THREE.BoxGeometry(b.w || 160, h, (b.h || 96) * 0.72);
      var col = 0x2a2a34;
      try { col = parseInt(String(b.col || '#2a2a34').slice(1), 16); } catch (_e) {}
      var side = new THREE.MeshLambertMaterial({ color: col });
      var face = new THREE.MeshLambertMaterial({ color: 0xffffff });
      // AK-ROOF 2026-07-19: the roof gets its OWN material instance. It cannot share
      // `side`, because `side` is the single instance bound to slots 0/1/3/5 as well --
      // hanging a roof map on it would texture all four walls with gravel too.
      var roof = new THREE.MeshLambertMaterial({ color: col });
      // BoxGeometry material order: +x, -x, +y, -y, +z, -z. +z faces the default camera,
      // and index 2 (+y) is the TOP.
      var m = new THREE.Mesh(geo, [side, side, roof, side, face, side]);
      m.position.set(b.x, h / 2, b.y);
      m.userData.akId = b.id;
      // AK-ENTRANCE 2026-07-19 (operator bug 4B): "there's still 3D buildings in the background
      // that I don't know." THREE populations now share one skyline -- these 18 AUTHORED buildings
      // (enterable, photo facades, saturated tints), the player's own p.builds structures, and
      // akworldgen's ~112 generated backdrop boxes (akworldgen.js tags every one of those
      // m.userData.akWorldGen = true and holds them in a desaturated 44..74 grey band). Tone alone
      // is a weak signal on a phone at night. akFunctional is the POSITIVE mark, and it is what the
      // door treatment below keys off, so "can I walk in here" is answered by a light on the ground
      // rather than by the player memorising a palette.
      m.userData.akFunctional = true;
      if (b.id) W3.bldIds[b.id] = 1;   // backs hasBox(); the host de-dupes its flat facade on this
      W3.scene.add(m); W3.blds.push(m);
      // AK-BLDMODELS 2026-07-20 (operator: "replace the town hall entirely"). If this building has a
      // real GLB, the BOX BECOMES INVISIBLE and the mesh stands in its place. Deliberately hidden
      // rather than skipped: m still carries userData.akId (backs hasBox so the 2D layer de-dupes its
      // flat facade), userData.akFunctional (drives the door light), and it is still what the door
      // collector below measures. Skipping construction would silently drop all three. The box costs
      // nothing invisible -- three.js culls !visible before the draw call.
      var _hasModel = !!(root.AK_BLDMODELS && root.AK_BLDMODELS.has(b.id));
      if (_hasModel) {
        m.visible = false;
        (function (bb) {
          root.AK_BLDMODELS.attach(THREE, W3.scene, bb, function (g) {
            if (g) { W3.models.push(g); }
            else {
              // Model failed to load. Show the box again so the district never has a hole in it.
              for (var q = 0; q < W3.blds.length; q++) {
                if (W3.blds[q].userData.akId === bb.id) { W3.blds[q].visible = true; break; }
              }
            }
          });
        })(b);
      }
      // Door position is the hub's own rule (worldmap.js validPlacement: the approach is at
      // b.y + b.h/2), so the marker lands exactly where walking in already works. 'soon' buildings
      // are signposted-but-shut (index.html: B(...,'soon')), and marking those would be a lie --
      // they are deliberately left unlit, which makes "unlit" mean "nothing for you here yet".
      if (b.url !== 'soon') doors.push({ x: b.x, y: b.y + (b.h || 96) / 2, col: col });
      // AK-BLDMASS 2026-07-19: dress the box with real building massing -- parapet, cornice,
      // base plinth, roof AC units, water tank, setback, facade ledges. Without this a building
      // is a single box with exactly ONE silhouette, which is why the hub read as photos taped
      // to cubes no matter how good the facade got. bldmass returns ONE merged mesh (vertex
      // colours) so the whole detail set costs a single draw call instead of ~15 -- at ~29
      // buildings that is the difference between +29 and +435 draw calls on a phone.
      // ADDITIVE BY CONTRACT: it never touches m.material, so the facade (+z, index 4) and roof
      // (+y, index 2) textures above keep working untouched. Kept in WORLD space (not parented to
      // m) because decorate() computes absolute coords; tracked separately for disposal.
      if (!_hasModel && root.AK_BLDMASS && root.AK_BLDMASS.decorate) {
        try {
          var _mass = root.AK_BLDMASS.decorate(THREE, m, b);
          if (_mass) { W3.scene.add(_mass); W3.mass.push(_mass); }
        } catch (_eMass) { try { console.warn('[world3d] bldmass failed', _eMass); } catch (_e2) {} }
      }
      (function (mat, id) {
        // Prefer the alpha-cut facade; fall back to the original on 404. Only the
        // genuine cutouts have a _cut file, so this is a no-op for painted scenes.
        if (_hasModel) return;   // AK-BLDMODELS: the GLB owns its own surfaces
        var cut = facadeCutUrl(id), plain = facadeUrl(id);
        if (!plain) return;
        function useTex(tex, isCut) {
          try { tex.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
          mat.map = tex;
          if (isCut) {
            // alphaTest discards the cut-away fragments in the depth pass too, so the
            // silhouette occludes correctly instead of blending as a sorted sprite.
            mat.transparent = true; mat.alphaTest = 0.5;
          }
          mat.needsUpdate = true;
        }
        if (cut) {
          loader.load(cut, function (t) { useTex(t, true); }, null, function () {
            loader.load(plain, function (t) { useTex(t, false); }, null, function () {});
          });
        } else {
          loader.load(plain, function (t) { useTex(t, false); }, null, function () {});
        }
      })(face, b.id);
      (function (mat, id, bw, bd) {
        if (_hasModel) return;   // AK-BLDMODELS: the GLB owns its own roof
        var u = roofUrl(roofKindFor(id));
        loader.load(u, function (tex) {
          try { tex.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
          try {
            tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
            // Tile at a fixed ~128 world-units per repeat so texel density stays
            // constant whether the footprint is a kiosk or the Town Hall.
            tex.repeat.set(Math.max(1, Math.round(bw / 128)), Math.max(1, Math.round(bd / 128)));
          } catch (_e) {}
          mat.map = tex;
          mat.color.set(0xffffff);   // stop the flat build colour tinting the gravel
          mat.needsUpdate = true;
        }, null, function () {});
      })(roof, b.id, (b.w || 160), ((b.h || 96) * 0.72));
    }
    buildDoors(THREE, doors);
  }

  /* AK-ENTRANCE 2026-07-19 -- the "what can I actually walk into" mark.
   *
   * TWO InstancedMeshes for the WHOLE district, not two meshes per building. At 16 lit doors the
   * naive version is 32 draw calls on a device where three_boot's own budget block is the reason
   * this file may only own one renderer; instanced it is 2, flat, regardless of how many buildings
   * a district grows to. Same argument akinstance.js:697 makes for player structures.
   *
   * The ring sits ON the ground (y just above 0) and the beam stands over it. Ring alone reads
   * clearly from overhead and vanishes at a low camera angle; beam alone floats. Together they
   * survive the full PHI_MIN..PHI_MAX pitch range the orbit input allows.
   *
   * COLOUR IS THE BUILDING'S OWN b.col, not a uniform gold. The hub already trains the player on
   * those tints -- index.html strokes each facade and prints each label in b.col -- so the light on
   * the ground matches the sign over the door instead of introducing a 19th colour.
   */
  function buildDoors(THREE, doors) {
    if (!doors || !doors.length) return;
    try {
      var n = doors.length, i;
      var ringGeo = new THREE.RingGeometry(30, 42, 22);
      var ringMat = new THREE.MeshBasicMaterial({
        color: 0xffffff, transparent: true, opacity: 0.55,
        side: THREE.DoubleSide, depthWrite: false, fog: true
      });
      var ring = new THREE.InstancedMesh(ringGeo, ringMat, n);
      // Thin, tall, and OPEN-ENDED: a capped cylinder shows a bright disc at the top that reads as
      // a floating coin. Additive so it brightens the scene behind it instead of masking it.
      var beamGeo = new THREE.CylinderGeometry(9, 15, 150, 10, 1, true);
      var beamMat = new THREE.MeshBasicMaterial({
        color: 0xffffff, transparent: true, opacity: 0.13,
        side: THREE.DoubleSide, depthWrite: false,
        blending: THREE.AdditiveBlending, fog: true
      });
      var beam = new THREE.InstancedMesh(beamGeo, beamMat, n);
      var mtx = new THREE.Matrix4(), q = new THREE.Quaternion();
      var pos = new THREE.Vector3(), scl = new THREE.Vector3(1, 1, 1);
      var col = new THREE.Color();
      // RingGeometry is authored in the XY plane; -90 deg about X lays it on the ground plane.
      var flat = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
      for (i = 0; i < n; i++) {
        var d = doors[i];
        pos.set(d.x, 1.5, d.y);                     // 1.5 above y=0: clears the ground plane's z-fight band
        mtx.compose(pos, flat, scl); ring.setMatrixAt(i, mtx);
        pos.set(d.x, 75, d.y);                      // beam is 150 tall, so centre at 75 stands it on the ground
        mtx.compose(pos, q, scl); beam.setMatrixAt(i, mtx);
        col.setHex(d.col); ring.setColorAt(i, col); beam.setColorAt(i, col);
      }
      ring.instanceMatrix.needsUpdate = true; beam.instanceMatrix.needsUpdate = true;
      if (ring.instanceColor) ring.instanceColor.needsUpdate = true;
      if (beam.instanceColor) beam.instanceColor.needsUpdate = true;
      ring.userData.akDoor = true; beam.userData.akDoor = true;
      // NOT pushed into W3.blds. blds is AK_CULL's only intake (akcull.js sync reads st.blds) and a
      // frustum culler that hides a door light the moment its ring centre leaves the frustum would
      // blink the marker off exactly when the player is standing on it. Tracked in W3.doors instead,
      // which is also what gives them their own disposal path in setZone.
      W3.scene.add(ring); W3.scene.add(beam);
      W3.doors = [ring, beam];
      W3.doorMat = [ringMat, beamMat];
    } catch (_e) { try { console.warn('[world3d] door markers failed', _e); } catch (_e2) {} }
  }

  // Disposal for the door markers. Separate from the blds/mass loops because these are
  // InstancedMeshes with shared materials this module owns outright.
  function clearDoors() {
    for (var i = 0; i < W3.doors.length; i++) {
      try {
        W3.scene.remove(W3.doors[i]);
        if (W3.doors[i].geometry) W3.doors[i].geometry.dispose();
        if (W3.doors[i].dispose) W3.doors[i].dispose();     // InstancedMesh owns instance buffers
      } catch (_e) {}
    }
    for (var j = 0; j < W3.doorMat.length; j++) {
      try { if (W3.doorMat[j] && W3.doorMat[j].dispose) W3.doorMat[j].dispose(); } catch (_e) {}
    }
    W3.doors = []; W3.doorMat = [];
  }

  /* =====================================================================
   * AK-PLR3D 2026-07-19 -- PLAYER-BUILT STRUCTURES IN 3D (operator bug 4A)
   * =====================================================================
   * Operator: "The buildings I have built are still not mesh."
   *
   * ROOT CAUSE, as a call site: buildBuildings() above reads `zone.buildings` and NOTHING ELSE.
   * That array is the 18 hand-authored records from index.html's ZONES table. Everything the
   * player places lives somewhere completely different -- p.builds[], written by
   * buildmode.js:612-615 through AK_ECON.mutateProfile -- and the only thing that has ever drawn
   * it is the Canvas2D pass at buildmode.js:2005 onDrawWorld -> drawStruct (buildmode.js:1260).
   * So with the 3D district on, a player's walls are painted as flat top-down sprites onto the 2D
   * canvas composited OVER the GL layer. They are not "not mesh yet"; there was no mesh path at
   * all. akgrid.js:16 states this plainly in its own header and it stayed true until now.
   *
   * WHY THIS LIVES HERE AND NOT ONLY IN akinstance.js
   * akinstance.js:806 syncBuilds already renders exactly this content, better (one InstancedMesh
   * per type instead of one Mesh per structure), and index.html:528 already has its script tag.
   * But that module is NOT on the live edge, so today it 404s and the hole is fully open. A fix
   * that only works after another lane ships is not a fix. So world3d owns a correct fallback and
   * STANDS DOWN the moment the instanced lane is genuinely alive -- see instanceLaneLive().
   *
   * READ-ONLY on p.builds, exactly like akinstance. buildmode.js:50 is explicit that every write
   * goes through its one mutateProfile path; a second writer here would be a save-loss surface.
   */

  // Per-family extrusion, mirroring buildmode.js:1367 STRUCT_H with PATH special-cased to 2.
  // Preferred at runtime from AK_BUILDMODE.iso.structH so the 3D district, the isometric base
  // editor and this lane cannot drift into three different wall heights; the table is the
  // headless/absent-module fallback only.
  var PLR_H = { wall: 46, barricade: 34, garden: 10, deco: 26 };
  function structHeight(def, type) {
    try {
      var B = root.AK_BUILDMODE;
      if (B && B.iso && typeof B.iso.structH === 'function') return B.iso.structH(def, type);
    } catch (_e) {}
    return type === 'PATH' ? 2 : ((def && PLR_H[def.family]) || 24);
  }

  /* Tints mirror buildmode.js ISO_COL `top` -- the colours the player already sees on the top face
   * of every piece inside the isometric base editor. Matching them means a wall does not change
   * colour when he walks out of the editor into the district, which is the same class of "one
   * state, many renderers" promise basegrid.js:14 makes about placement. */
  var PLR_COL = {
    WALL: 0x7a5228, STONE: 0x8a8d95, METAL: 0x4d5966, BARRICADE: 0x2c261c,
    PATH: 0x3a3a4a, GARDEN: 0x4a3320, PLANTER: 0x3a3040
  };

  // The 2D layer already draws real authored art for these (buildmode.js:1265 spriteImg). House
  // law is that authored art is never replaced by generic art, so the 3D box wears the SAME PNG on
  // its top face rather than a procedural roof. A type with no sprite falls through to the
  // procedural roof texture the authored buildings use, so nothing is ever left flat-shaded.
  function structSpriteUrl(def) {
    return (def && typeof def.sprite === 'string' && def.sprite) ? def.sprite : '';
  }

  function structDefs() {
    try { var B = root.AK_BUILDMODE; return (B && B.STRUCT) || null; } catch (_e) { return null; }
  }
  function loadProfile() {
    try {
      var e = root.AK_ECON;
      return (e && typeof e.loadProfile === 'function') ? (e.loadProfile() || null) : null;
    } catch (_e) { return null; }
  }
  function underConstruction(b) { return !!(b && b.uc && Date.now() < (b.uc.t0 + b.uc.dur)); }

  /* Stand down when the instanced lane is genuinely live. Checking for the GLOBAL alone is not
   * enough -- akinstance publishes AK_INSTANCE at load but renders nothing until three is up --
   * so this asks for both the module and its engine gate, which is the same condition its own
   * syncBuilds() requires before it will build a field. Ordering-independent: it is re-evaluated
   * on every throttled resync, so whichever lane loads first, exactly one of us draws. */
  function instanceLaneLive() {
    try {
      var I = root.AK_INSTANCE;
      return !!(I && I.builds && typeof I.ok === 'function' && I.ok());
    } catch (_e) { return false; }
  }

  /* PURE: this district's structures + a cheap change signature, in one pass. Split from the scene
   * work so it is testable with a literal array, no profile, no DOM and no three. Signature
   * includes the under-construction flag so a finished build re-tints without a manual poke.
   * Same zone filter buildmode.js:2011 uses -- b.zone === zid, not a truthiness test. */
  function planPlayerStructs(builds, zoneId) {
    var out = [], sig = (zoneId || '-') + '|', i;
    for (i = 0; i < (builds || []).length; i++) {
      var b = builds[i];
      if (!b || !b.type) continue;
      if (b.zone !== zoneId) continue;
      // AK-NOFORT 2026-07-20: walls and barricades no longer belong on a district street (they moved
      // into THE SILO). Filtering at the PLAN stage means an already-placed fort stops rendering in
      // 3D without touching the player's save -- the structure is still in p.builds and comes back
      // if this rule is ever lifted. Never mutate p.builds here; a render rule must not destroy data.
      if (root.AK_BUILDMODE && root.AK_BUILDMODE.isDistrictBanned &&
          root.AK_BUILDMODE.isDistrictBanned(b.type)) continue;
      out.push(b);
      sig += b.type + ',' + (b.x | 0) + ',' + (b.y | 0) + ',' + ((b.rot | 0) & 3) +
             (underConstruction(b) ? 'u' : '') + ';';
    }
    return { list: out, sig: sig };
  }

  /* Footprint resolution, in priority order, and the order is the whole point:
   *   1. AK_BUILDMODE.STRUCT dw/dh -- the ART size the 2D layer draws at (buildmode.js:476 effDW
   *      swaps the pair for an odd rotation, and this reproduces that swap exactly). A wall is
   *      76x42, not a 64 cell, so quantising it to the lattice would visibly fatten it.
   *   2. AK_GRID.footprint(type, rot) * AK_GRID.CELL -- the grid truth, which covers every type
   *      buildmode does not define (HUT, TOWER, STORAGE_*, TOWNHALL ... akgrid.js:159 MIRROR).
   *      Without this branch those types render NOTHING, silently, which is the exact failure
   *      shape of `if (!def) continue`.
   *   3. A 1-cell box, so an unknown future type is visible and wrong rather than invisible.
   * PLACEMENT is never quantised. b.x/b.y are authoritative -- buildmode's snap() already put them
   * on the 64 lattice, and akgrid.js:456 warns that a quantised round-trip MOVES a free-placed or
   * legacy entry. A renderer must never move a player's building. */
  function structBox(type, rot, def) {
    var swap = ((rot | 0) & 1) === 1;
    if (def && (def.dw || def.dh)) {
      var dw = def.dw || 64, dh = def.dh || 64;
      if (def.shape === 'circle') { dw = def.dw || 42; dh = def.dh || 42; }   // circles do not swap
      else if (swap) { var t = dw; dw = dh; dh = t; }
      return { w: dw, d: dh };
    }
    try {
      var G = root.AK_GRID;
      if (G && typeof G.footprint === 'function') {
        var f = G.footprint(type, rot | 0);                 // already applies the rotation swap
        var cell = G.CELL || 64;
        if (f && f.gw > 0 && f.gh > 0) return { w: f.gw * cell, d: f.gh * cell };
      }
    } catch (_e) {}
    return { w: 64, d: 64 };
  }

  function clearPlayerStructs() {
    var i;
    for (i = 0; i < W3.plr.length; i++) {
      var m = W3.plr[i];
      try {
        W3.scene.remove(m);
        if (m.geometry) m.geometry.dispose();
        // Materials are an array per box and this module allocated every one of them.
        var ma = m.material;
        if (ma) {
          if (ma.length) { for (var k = 0; k < ma.length; k++) { if (ma[k] && ma[k].dispose) ma[k].dispose(); } }
          else if (ma.dispose) ma.dispose();
        }
      } catch (_e) {}
    }
    W3.plr = [];
    for (i = 0; i < W3.plrMass.length; i++) {
      var d = W3.plrMass[i];
      try {
        W3.scene.remove(d);
        if (d.geometry) d.geometry.dispose();
        if (d.material && d.material.dispose) d.material.dispose();
      } catch (_e) {}
    }
    W3.plrMass = [];
  }

  function buildPlayerStructs(THREE, zoneId) {
    clearPlayerStructs();
    W3.plrSig = '';
    if (!W3.scene || instanceLaneLive()) return 0;
    var p = loadProfile(); if (!p) return 0;
    var plan = planPlayerStructs(p.builds || [], zoneId);
    W3.plrSig = plan.sig;
    if (!plan.list.length) return 0;
    var defs = structDefs() || {};
    var loader = new THREE.TextureLoader(), built = 0;
    for (var i = 0; i < plan.list.length; i++) {
      var b = plan.list[i];
      var def = defs[b.type] || null;
      var rot = (b.rot | 0) & 3;
      // ROT 0, DELIBERATELY. The geometry is built UNROTATED and the quarter turn is applied as a
      // real yaw on the mesh below. Passing `rot` here instead swaps dw/dh AND then rotates, which
      // applies the turn TWICE and lands a rot-1 wall back at its rot-0 world footprint -- caught
      // by tests/world3d_player_gl_test.mjs asserting on world-space Box3 bounds, not on the
      // arguments. akinstance.js:797 documents the identical trap for its instanced templates.
      // structBox(type, rot, def) still reports the ROTATED footprint, which is the right answer
      // for any caller asking "how much ground does this occupy"; this call site simply is not one.
      var box = structBox(b.type, 0, def);
      var h = Math.max(2, structHeight(def, b.type));
      var col = PLR_COL[b.type] || 0x555560;
      // Scaffolding reads as a dark ghost, matching what the 2D layer already signals with
      // drawBuildSite (buildmode.js drawStruct branches to it for the same predicate).
      var uc = underConstruction(b);
      var geo, m, side, top;
      try {
        geo = new THREE.BoxGeometry(box.w, h, box.d);
        side = new THREE.MeshLambertMaterial({ color: uc ? 0x2b2b31 : col });
        // Own instance for the top: `side` is bound to slots 0/1/3/4/5, so hanging the sprite on
        // it would wrap the same art around all four walls. Same trap AK-ROOF calls out above.
        top = new THREE.MeshLambertMaterial({ color: uc ? 0x2b2b31 : col });
        m = new THREE.Mesh(geo, [side, side, top, side, side, side]);
      } catch (_eGeo) { continue; }
      // b.x/b.y are the CENTER in world units (buildmode.js:614), hub y maps to three z, and the
      // box is raised by h/2 so it stands ON the ground exactly like buildBuildings does.
      m.position.set(b.x, h / 2, b.y);
      m.rotation.y = -rot * Math.PI / 2;   // hub rot is clockwise screen-space quarter turns; three yaw is CCW
      m.userData.akId = 'plr:' + b.type + ':' + (b.x | 0) + ':' + (b.y | 0);
      m.userData.akPlayerBuilt = true;
      // Deliberately NOT akFunctional: a wall is the player's, but it is not a door. Three
      // populations, three reads -- lit door = enterable, this = yours, unmarked grey = backdrop.
      W3.scene.add(m); W3.plr.push(m); built++;

      // Top face art. The struct sprite is the authored top-down view of this very piece, so it is
      // the correct "roof" for it; procedural roof texture is the fallback for a type with no art.
      (function (mat, sprite, type, bw, bd) {
        function useRoof() {
          loader.load(roofUrl(roofKindFor(type)), function (tex) {
            try { tex.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
            try {
              tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
              tex.repeat.set(Math.max(1, Math.round(bw / 128)), Math.max(1, Math.round(bd / 128)));
            } catch (_e) {}
            mat.map = tex; mat.color.set(0xffffff); mat.needsUpdate = true;
          }, null, function () {});
        }
        if (!sprite) { useRoof(); return; }
        loader.load(sprite, function (tex) {
          try { tex.colorSpace = THREE.SRGBColorSpace; } catch (_e) {}
          mat.map = tex; mat.color.set(0xffffff); mat.needsUpdate = true;
        }, null, useRoof);
      })(top, uc ? '' : structSpriteUrl(def), b.type, box.w, box.d);

      // AK-BLDMASS on anything with a silhouette to invest in. Gated on height, and the gate is
      // the point: a parapet + cornice + roof AC unit on a 46-unit wall is not massing, it is
      // noise the width of the wall itself, and it would double the draw calls of a 40-wall base
      // for nothing. akworldgen.js makes the same call with its per-kind `deco` flag.
      if (h >= 60 && !uc && root.AK_BLDMASS && root.AK_BLDMASS.decorate) {
        try {
          var _dm = root.AK_BLDMASS.decorate(THREE, m, { id: m.userData.akId });
          if (_dm) { W3.scene.add(_dm); W3.plrMass.push(_dm); }
        } catch (_eM) { try { console.warn('[world3d] player bldmass failed', _eM); } catch (_e2) {} }
      }
    }
    return built;
  }

  /* Throttled resync. p.builds changes on a player ACTION, never per frame, and loadProfile() is a
   * localStorage read plus a JSON.parse, so polling it every frame would be absurd. 700ms with a
   * signature compare means the steady-state cost is one parse and one string compare per poll and
   * zero scene work -- and a placement still lands well inside the time it takes the player to
   * look up from the build menu. */
  var PLR_POLL_MS = 700;
  function syncPlayerStructs(THREE, force) {
    if (!W3.scene) return false;
    var now = Date.now();
    if (!force && (now - W3.plrAt) < PLR_POLL_MS) return false;
    W3.plrAt = now;
    if (instanceLaneLive()) {                 // the better lane took over: drop ours and stay out
      if (W3.plr.length) { clearPlayerStructs(); W3.plrSig = ''; }
      return false;
    }
    var p = loadProfile(); if (!p) return false;
    var plan = planPlayerStructs(p.builds || [], W3.zoneId);
    if (!force && plan.sig === W3.plrSig) return false;    // unchanged: the common path, zero work
    buildPlayerStructs(THREE, W3.zoneId);
    return true;
  }

  // Hero GLB driven by the hub's own me{} (index.html:728, spawn 850/650), with the
  // heading DERIVED (see makeHeading -- window.faceAngle does not exist).
  // AK-WORLD3D-FIX 2026-07-18: three_boot now ships a real GLTFLoader (ADDONS at
  // three_boot.js:103) plus a managed loadGLB at three_boot.js:175. Prefer loadGLB so
  // three_boot owns the loader lifecycle and we never construct a second one; fall back
  // to addon('GLTFLoader') for an older three_boot. Either way the hero is optional:
  // if both paths fail the anchor stays empty and hub3d's model-viewer keeps drawing
  // the real hero, so nothing ever disappears.
  var HERO_GLB = 'assets/models/bcardd.glb';

  /* AK-ONEHERO 2026-07-19: TWO HEROES ON SCREEN -- this GLB is the one that is OFF.
   *
   * Operator: "I have 2 heroes on the ground. One's a small one, one's a big one."
   * Both hero systems always existed; only the sizes changed. Before AK-HEROSCALE this
   * GLB measured ~0.3 PIXELS so nobody ever saw it, and hub3d's pinned <model-viewer>
   * (window.__hero3d, index.html:2775) was the only hero on screen. Scaling this one to
   * HERO_H=60 revealed the second body. The "big one" is the model-viewer (index.html
   * me.r=23 -> h=clamp(23*ds*5,120,340) = ~120-170px); the "small one" is this GLB
   * (60 world units, ~1 unit/px at zoom 1).
   *
   * WHY THIS ONE LOSES, despite living in the depth buffer: IT HAS NO ANIMATION AT ALL.
   * attach() below reads only glb.scene and drops glb.animations on the floor, and there
   * is no THREE.AnimationMixer anywhere in the game -- `grep -rn "AnimationMixer\|clipAction"
   * systems/*.js` returns zero hits. So this hero is a frozen bind-pose model sliding across
   * the district. hub3d drives real idle/walk/run clips (hub3d.js:38 CLIP_IDX {idle:3,
   * walk:1, run:0}; hub3d.js:200 picks per frame) plus an eased 3D yaw turn (hub3d.js:192)
   * on facing constants tuned against real e5 renders (hub3d.js:32). Keeping this one and
   * dropping that trades a walk cycle for occlusion -- exactly the downgrade the operator
   * would notice first.
   *
   * NOT a deletion. The Group anchor is still created, still added to the scene, and frame()
   * still drives its position + derived heading (world3d.js:821), so the depth-correct path
   * stays wired and warm. Flip HERO_IN_SCENE (or set window.AK_HERO_IN_SCENE=true live) to
   * bring it back the moment an AnimationMixer lands here -- at which point hub3d's
   * model-viewer hero should be the one turned off, freeing a WebGL context.
   */
  var HERO_IN_SCENE = false;
  function heroInScene() {
    try { if (typeof root.AK_HERO_IN_SCENE === 'boolean') return root.AK_HERO_IN_SCENE; } catch (_e) {}
    return HERO_IN_SCENE;
  }

  function buildHero(THREE) {
    var g = new THREE.Group();
    g.position.set(850, 0, 650);
    W3.scene.add(g); W3.hero = g;
    var T = root && root.AK_THREE;
    if (!T) return;
    // AK-ONEHERO: anchor only. No GLB fetch, no second body, no 13 MB download.
    if (!heroInScene()) return;
    // AK-HEROSCALE 2026-07-19: THE GLB IS AUTHORED IN METRES, THE HUB WORLD IS IN PIXELS. Attached
    // raw, bcardd.glb measures 0.2 x 0.5 x 0.4 world units in a 1700x1300 world -- 0.2% of a
    // building's height, about 0.3 PIXELS on screen. Measured consequence: a pixel-diff of the hero
    // in front of a building, behind it, and with the building deleted returned 0 changed pixels in
    // all three cases. He was never visible, so he could never occlude or be occluded, which is why
    // the 3D world had no sense of depth at all. Normalise by the model's own bounding box so any
    // future hero GLB lands at a sane size regardless of its authoring units, and sit his feet on
    // y=0 rather than burying him half under the ground plane.
    var HERO_H = 60;   // world units. Buildings run ~90-205 tall, so the dog reads as a dog.
    function attach(glb) {
      var o = glb && (glb.scene || glb);
      if (!o || !W3.hero) return;
      try {
        var THREE_ = (root.AK_THREE && root.AK_THREE.get && root.AK_THREE.get()) || null;
        if (THREE_ && THREE_.Box3) {
          var box = new THREE_.Box3().setFromObject(o);
          var size = box.getSize(new THREE_.Vector3());
          var tall = Math.max(size.y || 0, 1e-6);
          var s = HERO_H / tall;
          if (isFinite(s) && s > 0) {
            o.scale.setScalar(s);
            o.position.y = -box.min.y * s;      // feet on the ground plane
          }
        }
      } catch (_e) {}
      try { W3.hero.add(o); } catch (_e2) {}
    }
    if (typeof T.loadGLB === 'function') {
      try { T.loadGLB(HERO_GLB, attach, function () {}); } catch (_e) {}
      return;
    }
    if (typeof T.addon !== 'function') return;
    try {
      T.addon('GLTFLoader').then(function (GL) {
        if (!GL || !W3.hero) return;
        try { new GL().load(HERO_GLB, attach, null, function () {}); } catch (_e) {}
      }, function () {});
    } catch (_e) {}
  }

  function buildLights(THREE) {
    // AK-LIGHTUP 2026-07-28: the hub read as near-black -- 74 buildings were barely visible
    // silhouettes (verified by render). Colours here are all dark (ground 0x22242c, buildings
    // ~0x2a2a34), so moderate light left it in the murk. Brighter sky + key + a low ambient fill
    // so the shadow side of a building is still readable. Kept warm/cool split so it stays a MOODY
    // night alley, not flat daylight -- verified against the live render, not guessed.
    W3.scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x302418, 2.2));   // AK-LIGHTUP2: 1.75->2.2 (lit buildings still read dark in the render-verified lot)
    W3.scene.add(new THREE.AmbientLight(0x404a5c, 0.85));   // AK-LIGHTUP2: 0.55->0.85 fill -- the biggest lever on "murky" shadow floor
    var d = new THREE.DirectionalLight(0xffe9b8, 1.7);       // AK-LIGHTUP2: 1.55->1.7 key, the "streetlamp sun"
    d.position.set(600, 900, 400);
    W3.scene.add(d); W3.keyLight = d;
    // AK-DAYNIGHT-3D 2026-07-28: a visible sun/moon disc so the sky has a light SOURCE, and it moves
    // with the phase. daynight.js already computes the phase deterministically; we just render it.
    var sun = new THREE.Mesh(new THREE.SphereGeometry(70, 16, 12),
                             new THREE.MeshBasicMaterial({ color: 0xffe9b8, fog: false }));
    sun.position.set(600, 900, 400); W3.scene.add(sun); W3.sun = sun;
    var d2 = new THREE.DirectionalLight(0x8fb4ff, 0.5);      // cool rim from the opposite side
    d2.position.set(-500, 400, -300);
    W3.scene.add(d2);
  }

  // AK-SKYFOG 2026-07-19: measured, 26% of the frame at default pitch and 38% at a low angle was
  // pure alpha-0 VOID -- the ground plane simply ended and black began, with a hard rectangular
  // edge. That single fact does more to break "this is a place" than any missing geometry.
  // Two cheap fixes, both straight out of how the reference RPGs handle it:
  //   SKY  a district-tinted background so the space beyond the ground reads as distance, not a hole
  //   FOG  fades the ground into that same colour, which HIDES the plate's hard edge. This is what
  //        WoW's fogEnd/fogScaler exists for, and its absence is a documented reason OSRS reads flat.
  // Fog colour MUST match the background or the horizon becomes a visible seam. Tint comes from the
  // district when daynight/districtmusic expose one, else a night-alley default.
  var SKY_FALLBACK = 0x0d0f18;
  function districtTint() {
    try {
      var dn = root.AK_DAYNIGHT;
      if (dn && typeof dn.skyColor === 'function') {
        var c = dn.skyColor();
        if (typeof c === 'number') return c;
        if (typeof c === 'string' && c.charAt(0) === '#') return parseInt(c.slice(1), 16);
      }
    } catch (_e) {}
    return SKY_FALLBACK;
  }
  function buildSky(THREE) {
    try {
      var tint = districtTint();
      W3.scene.background = new THREE.Color(tint);
      // near/far chosen off the camera dolly range (260-1150) so the far edge of a 1700x1300 plate
      // is well inside the fade instead of ending abruptly.
      W3.scene.fog = new THREE.Fog(tint, 700, 2600);   // AK-LIGHTUP: was 420/1750, buildings faded to black too soon
      W3.skyTint = tint;
    } catch (_e) {}
  }

  /* --- Orbit input: drag to turn, pinch to zoom, polar clamped. --- */
  function bindInput() {
    var doc = root.document; if (!doc) return;
    function pt(e) { return { x: e.clientX, y: e.clientY }; }
    function down(e) {
      if (!W3.on) return;
      if (e.touches && e.touches.length === 2) {
        W3._drag = { pinch: Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                                       e.touches[0].clientY - e.touches[1].clientY) };
      } else if (e.touches ? e.touches.length === 1 : true) {
        var p = e.touches ? e.touches[0] : e;
        W3._drag = { x: p.clientX, y: p.clientY };
      }
    }
    function move(e) {
      if (!W3.on || !W3._drag) return;
      if (e.touches && e.touches.length === 2 && W3._drag.pinch) {
        var d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                           e.touches[0].clientY - e.touches[1].clientY);
        if (W3._drag.pinch > 4) W3.proj.zoomBy(d / W3._drag.pinch);
        W3._drag.pinch = d; return;
      }
      var p = e.touches ? e.touches[0] : e;
      if (W3._drag.x == null) return;
      W3.proj.orbit((p.clientX - W3._drag.x) * 0.006, -(p.clientY - W3._drag.y) * 0.004);
      W3._drag.x = p.clientX; W3._drag.y = p.clientY;
    }
    function up() { W3._drag = null; }
    doc.addEventListener('pointerdown', down, { passive: true });
    doc.addEventListener('pointermove', move, { passive: true });
    doc.addEventListener('pointerup', up, { passive: true });
    doc.addEventListener('pointercancel', up, { passive: true });
  }

  /* =====================================================================
   * AK-3DC-world3d 2026-07-29 -- PHASE 6: OPTIONAL BLOOM + FXAA DEPTH PASS
   * =====================================================================
   * A guarded post-processing chain around the SHARED renderer. DEFAULT OFF (W3.postOn), so the
   * shipped game renders EXACTLY as today. When enabled it lazily + asynchronously loads the three
   * post-processing addons and, only if the core chain plus at least one effect is reachable, routes
   * frame() through an EffectComposer (RenderPass -> UnrealBloomPass -> FXAA -> OutputPass). If ANY
   * required addon is missing, or the build/render throws, W3._postFailed latches and frame() falls
   * straight back to the plain W3.renderer.render() -- this can NEVER black-screen.
   *
   * The post-processing addons are NOT vendored yet (three_boot.js ADDONS is only
   * {OrbitControls, GLTFLoader}). This lane does NOT vendor them -- see the handoff. The moment the
   * main session drops the flat vendor files (and/or adds the names to three_boot's ADDONS map),
   * ppLoad() finds them and this lights up with zero further edits here.
   */

  // The vendor dir the flat post-processing files load from -- mirrors three_boot's coreUrl/addonUrl
  // so a post-processing module's own `import './three.module.min.js'` resolves to the SAME singleton
  // (a query-free URL is one module identity; a second copy makes every instanceof silently false).
  function vendorDir() {
    try {
      var raw = (root && root.AK_THREE_SRC) || 'assets/vendor/three.module.min.js';
      var base = (root.document && root.document.baseURI) ||
                 (root.location && root.location.href) || '';
      var u = base ? new URL(raw, base).href : raw;
      var i = u.lastIndexOf('/');
      return (i === -1 ? '' : u.slice(0, i + 1));
    } catch (_e) { return 'assets/vendor/'; }
  }

  // Resolve ONE post-processing export, three ways, most-preferred first. Always resolves (null on
  // miss), never rejects, so the Promise.all below cannot blow up:
  //   1. already on the THREE namespace (a UMD-style vendored build attaches it)
  //   2. three_boot's addon() -- lights up if the main session adds the name to its ADDONS map
  //   3. a direct guarded ESM import from the flat vendor dir (mirrors three_boot's own addon path)
  function ppImport(name, file) {
    try {
      var p = import(vendorDir() + file);      // guarded: an absent/unrewritten file rejects -> null
      if (!p || typeof p.then !== 'function') return Promise.resolve(null);
      return p.then(function (ns) { return (ns && (ns[name] || ns['default'])) || null; },
                    function () { return null; });
    } catch (_e) { return Promise.resolve(null); }
  }
  function ppLoad(THREE, name, file) {
    try { if (THREE && THREE[name]) return Promise.resolve(THREE[name]); } catch (_e) {}
    try {
      var T = root && root.AK_THREE;
      if (T && typeof T.addon === 'function') {
        return T.addon(name).then(function (c) { return c || ppImport(name, file); },
                                  function () { return ppImport(name, file); });
      }
    } catch (_e) {}
    return ppImport(name, file);
  }

  function buildComposerFrom(THREE, parts) {
    var EffectComposer = parts[0], RenderPass = parts[1], UnrealBloomPass = parts[2],
        ShaderPass = parts[3], FXAAShader = parts[4], OutputPass = parts[5];
    // Need the core chain AND at least one real effect, or the composer is a pure-cost passthrough.
    if (!EffectComposer || !RenderPass || (!UnrealBloomPass && !(ShaderPass && FXAAShader))) {
      W3._postFailed = true; return;
    }
    if (!W3.renderer || !W3.scene || !W3.camera) { W3._composerTried = false; return; }  // not booted: retry
    var S = W3.proj.state;
    var pr = (W3.renderer.getPixelRatio && W3.renderer.getPixelRatio()) || 1;
    var comp = new EffectComposer(W3.renderer);
    comp.setSize(S.W, S.H);
    comp.addPass(new RenderPass(W3.scene, W3.camera));
    if (UnrealBloomPass) {
      // Subtle NIGHT-ALLEY glow: strength/radius/threshold tuned so lit signs + door beams bloom
      // without washing the murky scene. Bloom-heavy would fight the AK-LIGHTUP tone floor.
      var bloom = new UnrealBloomPass(new THREE.Vector2(S.W, S.H), 0.55, 0.4, 0.85);
      comp.addPass(bloom); W3._bloom = bloom;
    }
    if (ShaderPass && FXAAShader) {
      var fxaa = new ShaderPass(FXAAShader);
      try { fxaa.material.uniforms['resolution'].value.set(1 / (S.W * pr), 1 / (S.H * pr)); } catch (_e) {}
      comp.addPass(fxaa); W3._fxaa = fxaa;
    }
    // OutputPass (if vendored) does tonemap + sRGB at the END of the chain, which is where three r160
    // wants it once a composer intercepts the frame. Absent, the renderer's own ACES tonemap still
    // applies at RenderPass time -- slightly less correct, never broken.
    if (OutputPass) { try { comp.addPass(new OutputPass()); } catch (_e) {} }
    W3._composer = comp; W3._composerSize = { w: S.W, h: S.H };
  }

  // One-shot async composer build. Guarded end to end; a failure latches _postFailed so frame()
  // stops trying and stays on the plain renderer.
  function ensureComposer() {
    if (W3._composer || W3._composerTried || W3._postFailed) return;
    var THREE = engine();
    if (!THREE || !W3.renderer || !W3.scene || !W3.camera) return;   // not booted yet: retry later
    W3._composerTried = true;
    try {
      Promise.all([
        ppLoad(THREE, 'EffectComposer',  'EffectComposer.js'),
        ppLoad(THREE, 'RenderPass',      'RenderPass.js'),
        ppLoad(THREE, 'UnrealBloomPass', 'UnrealBloomPass.js'),
        ppLoad(THREE, 'ShaderPass',      'ShaderPass.js'),
        ppLoad(THREE, 'FXAAShader',      'FXAAShader.js'),
        ppLoad(THREE, 'OutputPass',      'OutputPass.js')
      ]).then(function (parts) {
        try { buildComposerFrom(THREE, parts); }
        catch (_e) { W3._composer = null; W3._bloom = null; W3._fxaa = null; W3._postFailed = true; }
      }, function () { W3._postFailed = true; });
    } catch (_e) { W3._postFailed = true; }
  }

  // Enable/disable the post pass. DEFAULT OFF. Enabling kicks the one-shot addon load; the plain
  // renderer keeps running every frame until (and unless) the composer actually comes up.
  function setPostOn(on) {
    W3.postOn = !!on;
    if (W3.postOn && !W3._composer) { W3._postFailed = false; W3._composerTried = false; ensureComposer(); }
    return W3.postOn;
  }

  // Called from frame(). Returns TRUE only if it rendered through a live composer; the caller does
  // the plain render whenever this returns false. Any throw here degrades to the plain render.
  function renderPost(S) {
    try {
      if (!W3.postOn || W3._postFailed) return false;
      if (!W3._composer) { ensureComposer(); return false; }   // pending / plain until it comes up
      if (W3._composerSize.w !== S.W || W3._composerSize.h !== S.H) {
        var pr = (W3.renderer.getPixelRatio && W3.renderer.getPixelRatio()) || 1;
        W3._composer.setSize(S.W, S.H);
        if (W3._bloom && W3._bloom.setSize) { try { W3._bloom.setSize(S.W, S.H); } catch (_e) {} }
        if (W3._fxaa && W3._fxaa.material) {
          try { W3._fxaa.material.uniforms['resolution'].value.set(1 / (S.W * pr), 1 / (S.H * pr)); } catch (_e) {}
        }
        W3._composerSize = { w: S.W, h: S.H };
      }
      W3._composer.render();
      return true;
    } catch (_e) {
      W3._composer = null; W3._bloom = null; W3._fxaa = null; W3._postFailed = true;   // never twice
      return false;
    }
  }

  function disposeComposer() {
    try { if (W3._composer && W3._composer.dispose) W3._composer.dispose(); } catch (_e) {}
    W3._composer = null; W3._bloom = null; W3._fxaa = null;
    W3._composerTried = false; W3._composerSize = { w: 0, h: 0 };
  }

  /* --- Public lifecycle. Every entry point re-checks the gate. --- */

  function boot(ctx) {
    var THREE = engine();
    if (!THREE || W3.booted) return false;
    var r = sharedRenderer(THREE);
    if (!r) return false;                       // no context to be had: stay 2D, silently
    W3.renderer = r;
    W3.scene = new THREE.Scene();
    W3.camera = new THREE.PerspectiveCamera(55, (root.innerWidth || 900) / (root.innerHeight || 600), 1, 6000);
    var zone = (ctx && ctx.activeZone) || null;
    W3.proj.setViewport(root.innerWidth || 900, root.innerHeight || 600);
    try { if (ctx && ctx.world) W3.proj.setWorld(ctx.world.WORLD_W, ctx.world.WORLD_H); } catch (_e) {}
    W3.zoneId = (zone && zone.id) || '';
    buildLights(THREE); buildSky(THREE); buildGround(THREE, zone || { id: W3.zoneId });
    buildBuildings(THREE, zone); buildHero(THREE);
    // AK-PLR3D 2026-07-19: the player's own structures, from p.builds[]. Must run AFTER
    // W3.zoneId is set (four lines up) because it filters on it -- reading it earlier would
    // silently plan an empty district, which is the shape of the bug this lane is fixing.
    buildPlayerStructs(THREE, W3.zoneId);
    bindInput();
    // AK-WORLD3D-FIX 2026-07-18: build the scene but DO NOT seize the screen. The old
    // code set on=true here, so the moment three finished loading a full-screen GL
    // canvas took over the hub with nothing in the host asking for it. Additive means
    // additive: the scene is warm and idle until someone calls setOn(true). This is
    // also why we no longer parkPool() at boot -- killing hub3d's 4 ally contexts for
    // a scene nobody is looking at is a pure regression. Both happen in setOn(true).
    W3.booted = true; W3.on = false;
    return true;
  }

  // AK-WORLD3D 2026-07-18: ok() is FALSE until three_boot's async vendor load lands,
  // so a synchronous gate alone would never boot. Await ready() ONCE, then boot.
  // Resolves false (never rejects) when three is absent or the vendor file 404s.
  function init(ctx) {
    try {
      var T = root && root.AK_THREE;
      if (!T || typeof T.ready !== 'function') return Promise.resolve(false);
      if (W3._initing) return W3._initing;
      W3._initing = T.ready().then(function (NS) {
        if (!NS) return false;                  // vendor missing: total no-op, 2D untouched
        var okd = boot(ctx || (root.AK_CTX || null));
        if (okd) loadCam();
        return okd;
      }, function () { return false; });
      return W3._initing;
    } catch (_e) { return Promise.resolve(false); }
  }

  // District swap. The hub already hard-cuts zones (index.html:1319); this rebuilds
  // only the ground plate + the box set, never the renderer.
  function setZone(ctx) {
    var THREE = engine(); if (!THREE || !W3.booted) return false;
    var zone = ctx && ctx.activeZone; if (!zone || zone.id === W3.zoneId) return false;
    for (var i = 0; i < W3.blds.length; i++) {
      var m = W3.blds[i];
      try { W3.scene.remove(m); if (m.geometry) m.geometry.dispose(); } catch (_e) {}
    }
    W3.blds = [];
    for (var _mi = 0; _mi < W3.mass.length; _mi++) {          // AK-BLDMASS: same lifetime as blds
      var _mm = W3.mass[_mi];
      try {
        W3.scene.remove(_mm);
        if (_mm.geometry) _mm.geometry.dispose();
        if (_mm.material && _mm.material.dispose) _mm.material.dispose();
      } catch (_e) {}
    }
    W3.mass = [];
    for (var _gi = 0; _gi < W3.models.length; _gi++) {      // AK-BLDMODELS: same lifetime as blds
      try { root.AK_BLDMODELS && root.AK_BLDMODELS.dispose(THREE, W3.scene, W3.models[_gi]); } catch (_e) {}
    }
    W3.models = [];
    // AK-PLR3D / AK-ENTRANCE 2026-07-19: both are rebuilt per district below, so both must be torn
    // down here. The blds loop above cannot do it -- these were deliberately kept OUT of blds (the
    // door markers so AK_CULL cannot blink them off, the player structures so a cull pass sees the
    // authored skyline it was tuned against), which means they also miss its disposal.
    clearPlayerStructs();
    clearDoors();
    if (W3.ground) {
      // AK-GROUND 2026-07-20: the detail overlay is a CHILD of the plate, so the remove() below
      // already detaches it from the scene -- this is what actually frees its geometry, material
      // and texture. Without it a district swap leaks one overlay per swap, the same
      // same-lifetime-as-ground-but-not-disposed-with-it leak AK-BLDMASS and AK-APRON both hit.
      // apply() also self-disposes the previous overlay, so a missed call here degrades to a
      // GPU-buffer leak rather than stacked meshes.
      try { if (root.AK_GROUND && root.AK_GROUND.dispose) root.AK_GROUND.dispose(); } catch (_eG) {}
      try { W3.scene.remove(W3.ground); if (W3.ground.geometry) W3.ground.geometry.dispose(); } catch (_e) {}
      W3.ground = null;
    }
    // AK-APRON / AK-PATHS 2026-07-19: buildGround() re-creates BOTH on every swap, so without this
    // each district change would leak a 7700x7300 skirt and a fresh street group into the scene --
    // the exact "same lifetime as ground, but not disposed with it" leak AK-BLDMASS hit above.
    if (W3.apron) {
      try { W3.scene.remove(W3.apron); if (W3.apron.geometry) W3.apron.geometry.dispose(); if (W3.apron.material && W3.apron.material.dispose) W3.apron.material.dispose(); } catch (_e) {}
      W3.apron = null;
    }
    if (W3.paths) {
      try {
        W3.scene.remove(W3.paths);
        // one shared material across every strip: dispose the children's geometry, the material once.
        var _pm = null;
        for (var _pi = 0; _pi < W3.paths.children.length; _pi++) {
          var _pc = W3.paths.children[_pi];
          if (_pc.geometry) _pc.geometry.dispose();
          _pm = _pm || _pc.material;
        }
        if (_pm && _pm.dispose) _pm.dispose();
      } catch (_e) {}
      W3.paths = null;
    }
    W3.zoneId = zone.id;
    // AK-WORLD3D-FIX 2026-07-18: a district swap TELEPORTS the hero (index.html:1336
    // sets a fresh spawn). Without this the next update() sees a ~1400-unit jump and
    // derives a garbage heading, snapping the model to face the old district.
    W3.head.reset();
    try { if (ctx.world) W3.proj.setWorld(ctx.world.WORLD_W, ctx.world.WORLD_H); } catch (_e) {}
    buildGround(THREE, zone); buildBuildings(THREE, zone);
    buildPlayerStructs(THREE, W3.zoneId);   // AK-PLR3D: a base is per-district, so it rebuilds with the district
    return true;
  }

  // Heading resolution order: an explicitly published value wins (so the day the host
  // exposes the real faceAngle this upgrades itself with no edit here), else derive.
  // ctx.faceAngle / window.AK_FACE are BOTH absent today -- this is forward wiring, and
  // the derived path is what actually runs. Guarded: never throws.
  function headingFrom(ctx, me) {
    try {
      if (ctx && typeof ctx.faceAngle === 'number') return ctx.faceAngle;
      if (root && typeof root.AK_FACE === 'number') return root.AK_FACE;
    } catch (_e) {}
    return W3.head.update(me.x, me.y);
  }

  function frame(dt, ctx) {
    var THREE = engine();
    if (!THREE || !W3.booted || !W3.on || !W3.renderer) return false;
    // AK-PLR3D 2026-07-19: pick up a structure the player placed, moved or demolished. Internally
    // throttled to PLR_POLL_MS and short-circuited by a signature compare, so the steady-state
    // per-frame cost of this line is one Date.now() subtraction.
    syncPlayerStructs(THREE, false);
    // AK-ENTRANCE: breathe the door lights. A static marker is furniture; a moving one is a
    // signal, and this is the cheapest possible version -- two shared material opacities, no
    // per-instance work, no geometry touched. Period ~2.6s, shallow enough not to strobe.
    if (W3.doorMat.length) {
      var _pulse = 0.5 + 0.5 * Math.sin(Date.now() * 0.0024);
      try {
        W3.doorMat[0].opacity = 0.40 + 0.26 * _pulse;    // ring
        W3.doorMat[1].opacity = 0.09 + 0.09 * _pulse;    // beam (additive: stays subtle)
      } catch (_e) {}
    }
    var me = (ctx && ctx.me) || root.me || { x: 850, y: 650 };
    W3.proj.setViewport(root.innerWidth || W3.proj.state.W, root.innerHeight || W3.proj.state.H);
    /* AK-P2CAM 2026-07-28 (Prototype-2 momentum camera): instead of hard-pinning the hero dead-centre,
     * ease the projector centre toward a point AHEAD of him in the travel direction -- more lead the
     * faster he moves, so a sprint reads as surging forward and the hero sits back on screen. follow()
     * stays a pure hard-set primitive (parity self-test + raid centring); the lead + smoothing lives
     * here at the one live call site. 2D sprites and the 3D ground both project through the SAME S.cam,
     * so leading it moves the whole scene coherently -- they cannot detach. */
    (function () {
      var vx = me.vx || 0, vy = me.vy || 0, sp = Math.hypot(vx, vy);
      var tx = me.x, ty = me.y;
      if (sp > 10) {
        var maxsp = (me.spd || 300) * 1.9;                  // approx sprint top speed
        var lead = 42 + 62 * Math.min(1, sp / maxsp);        // ~42px lead at a walk, up to ~104px at full sprint
        tx += (vx / sp) * lead; ty += (vy / sp) * lead;
      }
      if (W3._camLX == null) { W3._camLX = tx; W3._camLY = ty; }  // first frame: snap, no lurch
      var _s = Math.max(0.001, Math.min(0.1, dt || 0.016));
      var k = 1 - Math.pow(0.5, _s * 9);                     // frame-rate-independent trailing ease
      W3._camLX += (tx - W3._camLX) * k; W3._camLY += (ty - W3._camLY) * k;
      W3.proj.follow(W3._camLX, W3._camLY);
    })();
    // AK-CAMWALK 2026-07-20: ease the camera behind the hero and settle the horizon. Uses the same
    // headingFrom() the hero mesh is rotated by, so the rig and the dog can never disagree about
    // which way "forward" is -- a mismatch there is what makes a third-person camera feel drunk.
    // AK-CAMYAW-FIX 2026-07-20: headingFrom() returns Math.atan2(dy,dx) -- a standard MATH angle in
    // hub coordinates. Camera yaw is a DIFFERENT convention: camPos() places the camera at offset
    // (sin(yaw), cos(yaw)) from the target. Feeding the heading in raw (as the first cut did) settles
    // the camera at the wrong angle, and because AK-CAMREL rotates D-pad input BY that yaw, every
    // direction comes out consistently wrong -- the "directional navigation is still messed up" bug.
    // To sit BEHIND a hero travelling at heading h the offset must be -(cos h, sin h), so
    //   sin(yaw) = -cos(h),  cos(yaw) = -sin(h)   =>   yaw = -h - PI/2
    // Verified exact against atan2(-cos h, -sin h) across a full 360-degree sweep.
    // AK-FOLLOW: pass MOVING so a parked hero never rotates the world. Speed threshold, not a flag:
    // me.vx/vy carry residual velocity while decelerating and would otherwise keep the camera
    // creeping after the player has stopped.
    var _mv = Math.hypot(me.vx || 0, me.vy || 0) > 6;
    try { W3.proj.autoCentre(-headingFrom(ctx, me) - Math.PI / 2, dt, _mv); } catch (_eAC) {}
    if (W3.hero) {
      W3.hero.position.set(me.x, (me.z || 0), me.y);   // AK-P2Z 2026-07-28: lift the 3D hero mesh by jump height (me.z), ground stays at 0
      // AK-WORLD3D-FIX 2026-07-18: window.faceAngle does not exist (index.html:731
      // is a top-level `let`, which never lands on the global object -- see the
      // makeHeading header). Prefer any REAL published heading, otherwise derive it
      // from motion the same way the hub does at index.html:2387.
      W3.hero.rotation.y = -headingFrom(ctx, me) + Math.PI / 2;
    }
    // AK-DAYNIGHT-3D: drive the 3D key light + sun/moon from the deterministic phase. Throttled to
    // ~1s -- the phase changes over minutes, so per-frame is waste. Night = cooler + dimmer, day =
    // warm + bright. Bounded so it never goes darker than the readable floor set by AK-LIGHTUP.
    try {
      var _now = (root.performance && root.performance.now) ? root.performance.now() : 0;
      if (W3.keyLight && (!W3._dnAt || _now - W3._dnAt > 1000)) {
        W3._dnAt = _now;
        var DN = root.AK_DAYNIGHT, cur = (DN && DN.current) ? DN.current() : null;
        var ph = cur && cur.phase || 'day';
        // intensity + colour + sun height per phase
        // AK-LIGHTUP2 2026-07-28: raised the whole key-light floor so no phase reads murky. Night was
        // 0.85 (too dark on the render-verified lot); now 1.3. day 1.75->2.0, dawn/dusk lifted to match.
        var P = ({ dawn:  { i: 1.65, c: 0xffd9b0, y: 500, mc: 0xffe9b8 },
                   day:   { i: 2.0,  c: 0xffe9b8, y: 950, mc: 0xffe9b8 },
                   dusk:  { i: 1.6,  c: 0xffb877, y: 420, mc: 0xffbb88 },
                   night: { i: 1.3,  c: 0x9fb6e8, y: 780, mc: 0xdfe6ff } })[ph] || { i: 1.8, c: 0xffe9b8, y: 900, mc: 0xffe9b8 };
        W3.keyLight.intensity += (P.i - W3.keyLight.intensity) * 0.1;   // ease, no snap
        W3.keyLight.color.setHex(P.c);
        if (W3.sun) { W3.sun.position.y += (P.y - W3.sun.position.y) * 0.1; W3.sun.material.color.setHex(P.mc); }
      }
    } catch (_edn) {}
    var C = W3.proj.camPos(), S = W3.proj.state;
    W3.camera.aspect = (S.W || 900) / (S.H || 600);
    W3.camera.fov = S.fov;
    W3.camera.position.set(C.x, C.y, C.z);
    W3.camera.lookAt(W3.proj.camCx(), 0, W3.proj.camCy());
    W3.camera.updateProjectionMatrix();
    W3.renderer.setSize(S.W, S.H, false);
    // AK-3DC-world3d 2026-07-29 (Phase 6): route through the bloom+FXAA composer when it is enabled
    // AND live; otherwise render plain. renderPost() never throws -- it degrades to false, and the
    // plain path below is the EXACT behaviour the game ships with today.
    if (!renderPost(S)) { W3.renderer.render(W3.scene, W3.camera); }
    return true;
  }

  // AK-WORLD3D-FIX 2026-07-18: body carries an opaque background (index.html:11
  // html,body{...background:#06060a...}). A z-index:-1 child paints beneath in-flow
  // blocks but NOT beneath an opaque background on its own parent, so the GL layer
  // would stay invisible. Clear body's background while 3D owns the ground and put
  // the exact previous inline value back on the way out. html keeps its own #06060a,
  // so there is never a white flash.
  function bodyBg(hide) {
    try {
      var b = root.document && root.document.body; if (!b) return;
      if (hide) {
        if (W3._bgWas == null) W3._bgWas = b.style.background || '';
        b.style.background = 'transparent';
      } else if (W3._bgWas != null) {
        b.style.background = W3._bgWas; W3._bgWas = null;
      }
    } catch (_e) {}
  }

  function setOn(v) {
    if (!v) {
      W3.on = false; restorePool(); bodyBg(false);
      if (W3.renderer && W3.renderer.domElement) W3.renderer.domElement.style.display = 'none';
      return false;
    }
    if (!engine() || !W3.booted) return false;   // never show an unbuilt scene
    W3.on = true; parkPool(); bodyBg(true);
    if (W3.renderer && W3.renderer.domElement) W3.renderer.domElement.style.display = 'block';
    return true;
  }

  // AK-WORLD3D 2026-07-18: camera prefs persist ONLY through AK_ECON.mutateProfile.
  // Direct localStorage writes are banned in this repo (save-loss class of bug).
  function saveCam() {
    try {
      var e = root.AK_ECON; if (!e || typeof e.mutateProfile !== 'function') return false;
      var S = W3.proj.state;
      e.mutateProfile(function (p) { p.world3d = { phi: S.phi, zoom: S.zoom, dist: S.dist }; });
      return true;
    } catch (_e) { return false; }
  }
  function loadCam() {
    try {
      var e = root.AK_ECON; if (!e || typeof e.loadProfile !== 'function') return false;
      var c = (e.loadProfile() || {}).world3d; if (!c) return false;
      // AK-TILT 2026-07-19: `c.phi || 0` slammed a restored camera back to dead overhead whenever the
      // saved value was absent OR a legacy 0 from before the tilt default existed. Honour a real
      // saved number, otherwise fall back to the shipping tilt rather than to flat.
      /* AK-CAMSCALE 2026-07-28 (operator: "hero is a tiny speck, camera too high/far -- no sense of
       * scale"). The hub restored to dist 620 (far + top-down), shrinking the hero to a dot. Pull the
       * camera IN to a close third-person view with real presence, and CLAMP stale saves so a bad
       * saved camera can never re-shrink the hero or flatten the district into a top-down map. */
      var _phi = (typeof c.phi === 'number' && c.phi > 0.01) ? c.phi : DEFAULT_PHI;
      _phi = Math.max(58 * DEG, Math.min(72 * DEG, _phi));            // moderate 3rd-person tilt: never top-down-map, never so flat you lose the street
      W3.proj.setPhi(_phi);
      W3.proj.setZoom(c.zoom || 1);
      var _hd = (typeof c.dist === 'number' && c.dist > 0.01) ? Math.min(c.dist, 380) : 300;   // close: hero has presence (was 620); cap stale far saves
      W3.proj.dolly(_hd - W3.proj.state.dist);
      return true;
    } catch (_e) { return false; }
  }

  var API = {
    // --- the seam. index.html:3154 delegates here once the orchestrator lands the swap. ---
    separable: function () { return !!(W3.on && W3.booted) && W3.proj.separable(); },
    wx: function (x) { return W3.proj.wx(x); },
    wy: function (y, h) { return W3.proj.wy(y, h); },
    unwx: function (sx) { return W3.proj.unwx(sx); },
    unwy: function (sy) { return W3.proj.unwy(sy); },
    project: function (x, y, h) { return W3.proj.project(x, y, h); },
    // AK-CAMWALK 2026-07-20 / AK-3DC-world3d 2026-07-29: gameplay-mode camera rigs. Roaming:
    // 'district' (isometric mid) | 'street'/'tpp' (over-shoulder) | 'map' (survey). Transient:
    // 'gulag'/'fpp' (first person) | 'tower' (top-down lane) | 'interior' (framed keeper). The
    // index.html HUD lane calls this on a mode switch. Guarded: W3.proj always exists, so this is
    // safe to call BEFORE boot -- it just sets the projector state the first frame will honour.
    setMode: function (m) {
      var r = W3.proj.setMode(m);
      // Persist ONLY the roaming family. A transient rig (persist:false) must never be written as
      // the saved district camera -- loadCam would otherwise restore the whole district at e.g.
      // gulag's dist 22 on the next boot.
      if (r) { try { var M = CAM_MODES[r]; if (!M || M.persist !== false) saveCam(); } catch (_e) {} }
      return r;
    },
    camMode: function () { return W3.proj.mode(); },
    camModes: function () { try { return Object.keys(CAM_MODES); } catch (_e) { return []; } },
    camYaw: function () { return W3.proj.state.yaw; },
    // --- lifecycle ---
    available: function () { return !!engine(); },
    isOn: function () { return !!(W3.on && W3.booted); },
    renderer: function () { return W3.renderer || (root && root.AK_R3D) || null; },
    init: init, boot: boot, setZone: setZone, frame: frame, setOn: setOn, dispose: disposeScene,
    saveCam: saveCam, loadCam: loadCam,
    // AK-3DC-world3d 2026-07-29 (Phase 6): optional bloom+FXAA. DEFAULT OFF; the shipped game must
    // leave it off. setPostFx(true) / setQuality('high') kick a one-shot addon load and light the
    // pass ONLY if the post-processing addons are vendored -- otherwise the plain renderer keeps
    // running. postFxActive() reports whether the pass is actually live (vendored + enabled + built).
    setPostFx: function (on) { return setPostOn(on); },
    setQuality: function (level) {
      return setPostOn(level === true || level === 'high' || level === 'ultra' || level === 'on');
    },
    postFxActive: function () { return !!(W3.postOn && W3._composer && !W3._postFailed); },
    proj: W3.proj, makeProjector: makeProjector, makeHeading: makeHeading, selfTest: selfTest,
    plateUrl: plateUrl, plateFallbackUrl: plateFallbackUrl, facadeUrl: facadeUrl,

    /* AK-PLR3D / AK-ENTRANCE 2026-07-19 -- the reads index.html needs.
     *
     * hasBox(id) is the one that matters. index.html's world draw still paints the full 2.5D
     * facade body for every authored building, and while the 3D district is on that flat sprite
     * lands on top of the very box carrying the same PNG -- which is the "painted and geometric
     * buildings coexist and do not line up" half of the operator's report. The host asks this
     * before it paints the body, so the duplicate is dropped ONLY where a real box actually
     * exists. If a box failed to build, or three never loaded, the answer is false and the 2D art
     * paints exactly as it always has. Authored art is never lost, only de-duplicated.
     *
     * O(1) BY CONSTRUCTION, and that is not premature: this is called once per authored building
     * per frame, and W3.blds is the array akworldgen.js pushes its ~112 generated boxes into. A
     * linear scan would be 18 x 130 userData lookups every frame for an answer that only changes
     * on a district swap. bldIds is stamped in buildBuildings and cleared in setZone with it. */
    hasBox: function (id) {
      return !!(W3.on && W3.booted && id && W3.bldIds[id]);
    },
    // Verification seam: proves the player lane is doing work rather than silently no-opping.
    playerStats: function () {
      return {
        zone: W3.zoneId, structures: W3.plr.length, massed: W3.plrMass.length,
        doors: W3.doors.length, deferredToInstanceLane: instanceLaneLive()
      };
    },
    // force defaults TRUE (a caller asking by hand means "now"). Pass false to drive the real
    // per-frame path -- throttle plus signature compare -- which is what a test must exercise to
    // prove the steady state does no work.
    syncPlayer: function (force) {
      var T = engine();
      return T ? syncPlayerStructs(T, force !== false) : false;
    },
    planPlayerStructs: planPlayerStructs, structBox: structBox, structHeight: structHeight,
    _state: W3
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (root && root.document) {
    root.AK_WORLD3D = API;
    // Self-register so the hub's existing initAll/tickAll dispatch drives us with
    // ZERO index.html edits. onTick already receives (dt, ctx) at index.html:3183.
    try {
      if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
        root.AK_SYSTEMS.register({
          id: 'world3d',
          // init kicks the ASYNC vendor load. It resolves false and stays quiet when
          // three is absent, so initAll() is safe on a device with no WebGL.
          init: function (ctx) { init(ctx); },
          onTick: function (dt, ctx) {
            if (!engine() || !W3.booted) return;   // still loading, or no engine: 2D owns the frame
            setZone(ctx); frame(dt, ctx);
          }
        });
      }
    } catch (_e) {}
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));

/* Headless run: `node game/systems/world3d.js` prints the projection proof. */
if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
  var r = module.exports.selfTest();
  r.lines.forEach(function (l) { console.log(l); });
  console.log(r.ok ? 'ALL PASS' : 'FAILURES PRESENT');
  process.exit(r.ok ? 0 : 1);
}
