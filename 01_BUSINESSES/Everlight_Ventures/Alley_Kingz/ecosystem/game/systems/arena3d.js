/* ALLEY KINGZ -- AK_ARENA3D: the 3D STADIUM behind the tower-defense board.  AK-ARENA3D 2026-07-21.
 *
 * OPERATOR: "the arena is a 3D arena, the model, but it's flat/planar. So decorate the field with
 * the tower game already there, just lay it on top."
 *
 * THE GAP THIS CLOSES
 * assets/models/arena_interior.glb has been sitting on disk at 13.7 MB with ZERO references anywhere
 * in the codebase -- audited by grep across systems/, index.html and game.html. The battler
 * (game.html) is pure Canvas2D: three_boot appears 0 times, AK_THREE 0 times. So the stadium was
 * generated, compressed, deployed, and never once drawn. That is the sixth "built but nothing calls
 * it" in this project, and it is the one the operator keeps asking about.
 *
 * THE DESIGN -- BACKDROP, NOT A REWRITE
 * The card battle stays exactly as it is. #board is a 540x900 Canvas2D board with its own in-canvas
 * perspective (AK-TILT2 at game.html:2863) and every hit-test, tap round-trip and spawn rule is
 * built on it. Rewriting that into 3D would risk the whole combat loop for a visual gain.
 * So this mounts a GL canvas UNDERNEATH #board and renders the stadium as the surrounding bowl:
 *     GL stadium (z-index below)  <-  the world the fight happens inside
 *     #board Canvas2D (above)     <-  untouched: units, towers, cards, taps
 * Same additive trick world3d.js uses in the hub, and it means a three.js failure costs the player
 * nothing -- the battler renders exactly as it does today.
 *
 * WHY NOT ALIGN THE STADIUM FLOOR TO THE BOARD PIXEL-FOR-PIXEL
 * Tempting, and wrong. The board's tilt is a 2D shear applied in canvas space; the stadium is a real
 * perspective projection. Forcing them to agree exactly would mean re-deriving the board's tilt from
 * the GL camera every frame and would break the moment either is tuned. The stadium is framed so the
 * board sits ON its floor with the bowl rising around and behind it -- which is what reads as "the
 * fight is happening in a stadium" -- and small disagreement at the rim is invisible because the
 * board is opaque and drawn on top.
 *
 * UNITS: the GLB is Tripo-normalised (~1 unit). The board is 540x900. Scale is derived from the
 * model's own bounding box against the board diagonal, never from an authored constant -- the same
 * trap that once rendered the hero at 0.3 pixels.
 */
window.AK_ARENA3D = (function (root) {
  'use strict';

  var MODEL = 'assets/models/arena_interior.glb';
  var ID    = 'ak-arena3d';

  var S = { on: false, booted: false, booting: false, bootCbs: null, renderer: null,
            scene: null, camera: null, stadium: null, mount: null, raf: 0, board: null,
            failed: false };

  function boardEl() {
    if (S.board && S.board.isConnected) return S.board;
    S.board = document.getElementById('board');
    return S.board;
  }

  /* Mount the GL canvas directly behind #board. It tracks the board's box rather than the viewport:
   * the board is letterboxed inside its container, and a full-viewport stadium would spill past the
   * playfield and read as wallpaper instead of a room. */
  /* AK-ARENA3D-FIX 2026-07-21: MOUNT OUTSIDE THE LAYOUT.
   * The first cut inserted the GL canvas as a SIBLING inside #board's parent and set
   * parent-affecting styles (position:relative on the board, z-index on the board). That was a
   * regression: the operator reported "I cannot see the entire 2D arena". Adding a child to a flex
   * or grid container changes how that container sizes and positions its existing children, so the
   * board itself got resized/shifted -- the stadium broke the game it was meant to decorate.
   *
   * A backdrop must never participate in the layout of the thing it sits behind. So the canvas now
   * attaches to document.body with position:fixed and simply TRACKS the board's viewport rect every
   * frame. Nothing about #board or its ancestors is touched -- no inserted siblings, no style writes
   * to the board, no reparenting. If this module is removed entirely the battler is byte-identical
   * to before it existed. */
  /* AK-ARENA3D-V2 2026-07-21. Operator: "I should see the ENTIRE arena.glb and have the tower map
   * INSIDE the stadium field, where the game takes place. Make sure the camera angle and zoom is
   * good for both the map and the playing field."
   *
   * V1 sized the GL canvas to the board's own rect, so the stadium was crammed into a 540x900
   * portrait window -- you could never see the bowl. V2 composes properly:
   *   1. the GL canvas fills #boardwrap (like the existing #boardbg, absolute + inset, z-index 0),
   *      so the whole stadium has room to be seen
   *   2. the camera is FRAMED FROM THE MODEL'S OWN BOUNDING SPHERE, so the entire bowl fits
   *      regardless of what Tripo exported
   *   3. the 2D #board is CSS-TRANSFORMED onto the stadium's pitch
   *
   * WHY TRANSFORM AND NOT width/height/left/top: transform is layout-neutral -- it cannot resize a
   * flex sibling or reflow #boardwrap, which is exactly the regression V1 caused ("I cannot see the
   * entire 2D arena"). And getBoundingClientRect() REFLECTS transforms, which matters more than it
   * sounds: game.html:2961 notes canvasToArena() reads a fresh rect for every deploy tap, so the
   * board can be moved and scaled onto the pitch and every tap still lands on the right cell. No
   * hit-test code changes. */
  function wrapEl() {
    var b = boardEl(); if (!b) return null;
    return document.getElementById('boardwrap') || b.parentNode;
  }

  function mount() {
    var w = wrapEl(); if (!w) return null;
    var c = document.getElementById(ID);
    if (!c) {
      c = document.createElement('canvas');
      c.id = ID;
      // Mirrors #boardbg (game.html:442): absolutely positioned, so it is OUT OF FLOW and cannot
      // affect how the flex wrap sizes #board. Behind the board, transparent to taps.
      c.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;display:none;';
      try { if (getComputedStyle(w).position === 'static') w.style.position = 'relative'; } catch (_e) {}
      w.insertBefore(c, w.firstChild);
    }
    S.mount = c;
    return c;
  }

  function syncSize() {
    var w = wrapEl(), c = S.mount; if (!w || !c) return false;
    var r = w.getBoundingClientRect();
    var ww = Math.max(1, Math.round(r.width)), hh = Math.max(1, Math.round(r.height));
    if (ww < 8 || hh < 8) return false;
    if (S.renderer && (c.width !== ww || c.height !== hh)) {
      try {
        S.renderer.setPixelRatio(Math.min(root.devicePixelRatio || 1, 2));
        S.renderer.setSize(ww, hh, false);
        if (S.camera) { S.camera.aspect = ww / hh; S.camera.updateProjectionMatrix(); }
      } catch (_e) {}
      S.needFrame = true;
    }
    return true;
  }

  /* Frame the camera so the WHOLE stadium fits, derived from its bounding sphere rather than tuned
   * constants -- a hand-picked distance breaks the moment the model is re-exported at another size. */
  function frameStadium(THREE) {
    if (!S.stadium || !S.camera) return;
    try {
      var bb = new THREE.Box3().setFromObject(S.stadium);
      var sph = bb.getBoundingSphere(new THREE.Sphere());
      var R = sph.radius || 1;
      var vFov = S.camera.fov * Math.PI / 180;
      var hFov = 2 * Math.atan(Math.tan(vFov / 2) * (S.camera.aspect || 1));
      // distance that fits the sphere on the TIGHTER axis, then 1.12 margin so the rim is not clipped
      var dist = (R / Math.sin(Math.min(vFov, hFov) / 2)) * 1.12;

      /* AK-ARENA3D-V4 2026-07-28: FOG MUST RIDE THE CAMERA, or it erases the whole stadium.
       * boot() sets a fixed fog band of 900..3400. But the model is scaled to BOARD_DIAG*2.1 (~2205 px
       * diagonal), so its bounding-sphere radius R is ~1100 and this fit distance lands the camera ~5-6k
       * px from the bowl. At that range the ENTIRE stadium sits BEYOND fog-far 3400 and every surface
       * blends 100% to the background tint -- the arena rendered as a flat 0x0d0f18 void (verified: the
       * stadium-only screenshot, board lifted, was uniform background colour). So place the band ON the
       * model: start just in front of the near rim, end past the far stands. Derived from dist/R, never
       * authored, so it survives a model re-export at any scale. Kept just inside the 9000 far-plane. */
      if (S.scene && S.scene.fog) {
        S.scene.fog.near = Math.max(1, dist - R * 1.2);
        S.scene.fog.far  = Math.min(8800, dist + R * 2.6);
      }
      // 34deg above the pitch: high enough to read the whole bowl, low enough that the far stand
      // still rises behind the field instead of being looked down into.
      var el = 34 * Math.PI / 180;
      S.camera.position.set(sph.center.x,
                            sph.center.y + dist * Math.sin(el),
                            sph.center.z + dist * Math.cos(el));
      S.camera.lookAt(sph.center.x, sph.center.y * 0.55, sph.center.z);
      S.camera.updateProjectionMatrix();
      S.sphere = sph;
      S.pitchY = bb.min.y;   // the floor plane the board sits on
    } catch (_e) {}
  }

  /* AK-ARENA3D-V3 2026-07-21: DO NOT TRANSFORM THE BOARD.
   * V2 CSS-transformed #board onto the projected pitch. That was wrong for a reason I only found by
   * reading the battler: #board ALREADY applies its own transform -- the TILT system (game.html:5223)
   * -- and its hit-test does closed-form inverse math to undo EXACTLY that transform when mapping a
   * tap to a cell. Stacking a second transform on top would silently break every deploy tap and the
   * tilt un-projection with it.
   *
   * So the stadium is purely a BACKDROP filling #boardwrap, behind the board's own #boardbg. The
   * camera frames the whole bowl; the board sits in front of it with its own tilt providing the
   * playfield perspective. The bowl rises around and behind the tilted board, which is what reads as
   * "the fight is in a stadium" -- and the board, its tilt, and its taps are byte-for-byte untouched. */
  function placeBoard() { /* intentionally empty: the board owns its own transform */ }

  function clearBoard() {
    var b = boardEl(); if (!b) return;
    try { b.style.transform = ''; b.style.transformOrigin = ''; } catch (_e) {}
    S.boardPlaced = false;
  }

  function frame() {
    S.raf = 0;
    if (!S.on || !S.renderer || !S.scene || !S.camera) return;
    syncSize();
    if (S.needFrame && S.stadium) {
      S.needFrame = false;
      try { var TH = root.AK_THREE && root.AK_THREE.get(); if (TH) { frameStadium(TH); } } catch (_e) {}
    }
    try { S.renderer.render(S.scene, S.camera); } catch (_e) {}
    S.raf = root.requestAnimationFrame(frame);
  }

  /* AK-ARENA3D-V4 2026-07-28: BOOT OWNS THE THREE LOAD -- this is the deadlock fix.
   * three_boot is LAZY by design. ok()/get() are PASSIVE reads (three_boot.js:187-188 -- ok() is just
   * `return !!THREE`); ONLY ready()/loadGLB() fire the dynamic import() that actually loads three
   * (three_boot.js:146 loadCore, :186 ready wraps it). The battler (game.html) calls ready() NOWHERE:
   * it loads neither world3d.js nor hub3d.js, so nothing ever kicked the loader. V3's boot() then bailed
   * on `!T.ok()` (this line) and loadGLB -- the one call that WOULD have kicked the load -- sat below the
   * guard, unreachable. That is a hard deadlock: ok() needs a load, the load needs loadGLB, loadGLB needs
   * boot() to pass the ok() gate. So ok() stayed false for the life of the page and the stadium never
   * rendered (headless diag stuck at {on:false, booted:false, failed:true, hasStadium:false, mounted:false},
   * the whole board area a flat black void). Even a direct AK_ARENA3D.setOn(true) bailed here.
   *
   * The fix mirrors the working HUB exactly: world3d.js awaits AK_THREE.ready() once and boots from the
   * .then (world3d.js:56-57). So boot() now KICKS the load itself and continues from the resolved promise
   * instead of reading a value nobody populated. ready() is idempotent -- every caller shares the one
   * in-flight core promise (three_boot.js:147 `if (coreP) return coreP`) -- so a warm boot costs nothing,
   * and per the three_boot contract it NEVER rejects (resolves THREE or null). A null resolve degrades to
   * the untouched 2D board exactly as the old ok()-false path did. Side benefit: setOn(true) is now
   * self-sufficient from ANY caller, not just the game.html poll (the diagnosis harness needed that). */
  function boot(cb) {
    if (S.booted) { cb && cb(true); return; }
    var T = root.AK_THREE;
    if (!T || typeof T.ready !== 'function') { S.failed = true; cb && cb(false); return; }
    // Coalesce re-entrant boots: a second setOn(true) while the load is in flight must NOT start a
    // second WebGLRenderer (one-renderer law) -- it just rides the same in-flight boot.
    if (S.booting) { S.bootCbs.push(cb || null); return; }
    S.booting = true; S.bootCbs = [cb || null];
    function finish(ok) {
      S.booting = false;
      var cbs = S.bootCbs || []; S.bootCbs = null;
      for (var i = 0; i < cbs.length; i++) { try { if (cbs[i]) cbs[i](ok); } catch (_e) {} }
    }
    // ready() kicks loadCore() -> the dynamic import() -> ok() flips true on its own. Boot from the .then.
    T.ready().then(function (THREE) {
      if (!THREE || !THREE.WebGLRenderer) { S.failed = true; return finish(false); }  // vendor 404 -> 2D
      if (!mount()) { S.failed = true; return finish(false); }

      try {
        S.renderer = new THREE.WebGLRenderer({ canvas: S.mount, antialias: false, alpha: true });
      } catch (_e) { S.failed = true; return finish(false); }
      S.scene = new THREE.Scene();

      // Match the hub's night-alley atmosphere so the stadium does not read as a different game.
      var tint = 0x0d0f18;
      S.scene.background = new THREE.Color(tint);
      S.scene.fog = new THREE.Fog(tint, 900, 3400);
      S.scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x2a2418, 1.15));
      var d = new THREE.DirectionalLight(0xffe9b8, 0.9); d.position.set(500, 1200, 700);
      S.scene.add(d);

      S.camera = new THREE.PerspectiveCamera(42, 1, 1, 9000);
      S.booted = true;
      syncSize();

      T.loadGLB(MODEL, function (glb) {
        var o = glb && (glb.scene || glb);
        if (!o) { S.failed = true; return finish(false); }
        try {
          // Scale from the model's OWN bbox against the board diagonal. Never an authored constant.
          var bb = new THREE.Box3().setFromObject(o);
          var sz = bb.getSize(new THREE.Vector3());
          var BOARD_DIAG = Math.hypot(540, 900);              // the 2D board, in its own units
          var modelDiag = Math.max(1e-6, Math.hypot(sz.x, sz.z));
          // 2.1x so the bowl surrounds the playfield rather than sitting flush with its edges.
          var k = (BOARD_DIAG * 2.1) / modelDiag;
          o.scale.setScalar(k);
          var bb2 = new THREE.Box3().setFromObject(o);
          o.position.y = -bb2.min.y;                          // floor on y=0
          var c2 = bb2.getCenter(new THREE.Vector3());
          o.position.x = -c2.x; o.position.z = -c2.z;         // centre the bowl on the board
          // Back faces on: Tripo exports vary, and a stadium seen from inside is ALL back faces --
          // with culling on you would see straight through the far stand to the void.
          o.traverse(function (m) {
            if (!m.isMesh || !m.material) return;
            var arr = Array.isArray(m.material) ? m.material : [m.material];
            for (var i = 0; i < arr.length; i++) {
              if (arr[i] && arr[i].side !== THREE.DoubleSide) {
                var cl = arr[i].clone(); cl.side = THREE.DoubleSide; cl.needsUpdate = true;
                if (Array.isArray(m.material)) m.material[i] = cl; else m.material = cl;
              }
            }
          });
        } catch (_e) {}
        S.scene.add(o); S.stadium = o;

        // Camera: above and behind the board's near edge, looking down the long axis at the far end,
        // so the player's own towers are nearest and the bowl rises past the far goal.
        try { frameStadium(THREE); } catch (_e2) {}
        S.needFrame = true;
        finish(true);
      }, function () { S.failed = true; finish(false); });
    }, function () { S.failed = true; finish(false); });  // contract says ready() never rejects; belt-and-suspenders
  }

  function setOn(v) {
    v = !!v;
    if (v === S.on) return S.on;
    if (v) {
      boot(function (ok) {
        if (!ok) { S.on = false; return; }
        S.on = true;
        if (S.mount) S.mount.style.display = 'block';
        if (!S.raf) S.raf = root.requestAnimationFrame(frame);
      });
      return S.on;
    }
    S.on = false;
    clearBoard();                       // board returns to exactly where the battler put it
    if (S.raf) { root.cancelAnimationFrame(S.raf); S.raf = 0; }
    if (S.mount) S.mount.style.display = 'none';
    return S.on;
  }

  return {
    setOn: setOn,
    isOn: function () { return S.on; },
    failed: function () { return S.failed; },
    resize: function () { S.needFrame = true; return syncSize(); },
    clearBoard: clearBoard,
    diag: function () {
      return { on: S.on, booted: S.booted, failed: S.failed, hasStadium: !!S.stadium,
               model: MODEL, mounted: !!(S.mount && S.mount.isConnected) };
    }
  };
})(window);

/* AK-3DC-tower 2026-07-29 ===========================================================================
 * PHASE 4 -- TOWER-LANE 3D UNIT POOL  (window.AK_ARENA3D_UNITS)
 *
 * game.html draws every lane unit as a flat Canvas2D token (drawUnit, game.html:3842). This pins a
 * live WALKING GLB over the tilted board at each unit's SCREEN position -- the same additive-overlay
 * trick hub3d.js:__ak3d(:352) runs in the hub, but a SEPARATE pool on purpose:
 *   - game.html never loads hub3d.js, so window.__ak3d does not exist in the battler.
 *   - the battler already carries the arena3d STADIUM WebGL context above, so this pool is capped on
 *     its own budget: stadium + CAP model-viewer contexts + the cardfx <video> pool must stay under
 *     the phone ~8-context wall.
 *
 * FALLBACK-FIRST, FULLY GUARDED. unit() returns TRUE only when a GLB is actually on screen. On ANY
 * miss it returns FALSE and the caller keeps its full 2D drawUnit token:
 *   - <model-viewer> not registered  (game.html loads it async as a module, and it may 404)
 *   - the card has no hero GLB        (only the 6 hero cards resolve at first; every other card = 2D)
 *   - pool at CAP                     (the extra units stay 2D)
 *   - the GLB is still downloading    (2D covers until the clip is ready)
 * If model-viewer never loads, the lane is byte-identical to today. This module NEVER touches the
 * board canvas, the arena3d stadium, or AK_ARENA3D -- a failure here cannot black-screen the fight.
 *
 * Mirrors the hub pool's model / clip / yaw / lifecycle logic so the two cannot drift.
 */
(function (root, doc) {
  'use strict';

  // Hero slug -> GLB, copied from hub3d.js HERO_MODELS (the battler cannot read hub3d's private map).
  var HERO_MODELS = {
    bcardd:     'assets/models/bcardd.glb',
    jagged:     'assets/models/jagged.glb',
    balboa:     'assets/models/balboa.glb',
    rottweiler: 'assets/models/rottweiler.glb',   // Iron Rottweiler
    bulldog:    'assets/models/bulldog.glb',       // Grit Bulldog
    malamute:   'assets/models/malamute.glb'       // Blackout Malamute
  };
  // GLB-verified idle/walk/run clip INDICES per model (copied from hub3d.js CLIP_BY_MODEL -- clips
  // export as NlaTrack.00N carrying zero info, so indices are MEASURED, never guessed; a wrong index
  // plays the wrong animation). An unknown model falls back to the safe 4-clip Tripo set.
  var CLIP_BY_MODEL = {
    'bcardd.glb':     { idle: 5,  walk: 10, run: 2 },
    'balboa.glb':     { idle: 15, walk: 4,  run: 5 },
    'jagged.glb':     { idle: 9,  walk: 1,  run: 12 },
    'bulldog.glb':    { idle: 1,  walk: 3,  run: 7 },
    'rottweiler.glb': { idle: 4,  walk: 9,  run: 5 },
    'malamute.glb':   { idle: 11, walk: 7,  run: 0 }
  };
  var CLIP_DEFAULT = { idle: 3, walk: 1, run: 0 };   // safe on any 4-clip Tripo export
  function clipsForModel(url) {
    var u = String(url || '');
    for (var k in CLIP_BY_MODEL) { if (u.indexOf(k) !== -1) return CLIP_BY_MODEL[k]; }
    return CLIP_DEFAULT;
  }
  // Same yaw mapping the hub hero is tuned on (hub3d.js:32-34).
  var THETA_BASE = -90, THETA_SIGN = 1, PHI = 72;
  var UNIT_CAP = 4, units = {}, unitN = 0;

  function mvReady() {
    // <model-viewer> must be a REGISTERED custom element, or createElement yields an inert node with
    // no .play()/.availableAnimations. Until it upgrades (async module) or if the vendor 404s -> 2D.
    try { return !!(root.customElements && root.customElements.get('model-viewer')); }
    catch (_e) { return false; }
  }
  function nowMs() { try { return root.performance.now(); } catch (_e) { return Date.now(); } }

  // Resolve idle/walk/run/combat clip NAMES from this GLB's list. Name-match wins (future heroes with
  // named clips); else the measured index. COMBAT prefers a punch/attack-named clip and otherwise
  // reuses the (measured, always in-range) run clip, so engage never plays an out-of-range animation.
  function pickClips(names, url) {
    var CI = clipsForModel(url);
    var _i = names.find(function (n){ return /idle|stand|relax/i.test(n); }) || names[CI.idle] || names[0] || '';
    var _w = names.find(function (n){ return /walk|move|trot/i.test(n); })   || names[CI.walk] || (names.length > 1 ? names[1] : names[0]) || '';
    var _r = names.find(function (n){ return /run|sprint|dash/i.test(n); })  || names[CI.run]  || _w || '';
    var _c = names.find(function (n){ return /punch|attack|kick|hook|jab|combat|fight|strike|power/i.test(n); }) || _r || _w || '';
    return { idle: _i, walk: _w, run: _r, combat: _c };
  }

  function unitBuild(rg, url) {
    var el = doc.createElement('model-viewer');
    el.setAttribute('src', url);
    el.setAttribute('autoplay', '');
    el.setAttribute('interaction-prompt', 'none');
    el.setAttribute('disable-zoom', '');
    el.setAttribute('disable-tap', '');
    el.setAttribute('disable-pan', '');
    el.setAttribute('shadow-intensity', '0');
    el.setAttribute('exposure', '1.0');
    el.setAttribute('camera-orbit', '0deg ' + PHI + 'deg 3.4m');
    el.setAttribute('camera-target', '0m 0.95m 0m');
    el.setAttribute('field-of-view', '26deg');
    // position:fixed over the board; canvas coords are converted to viewport px by the caller, the
    // same convention the killstreak / cardfx overlays use. z-index 40: above the board + stadium,
    // below the killstreak tier-up videos (z-index 50) so those still pop over a fighter.
    el.style.cssText = 'position:fixed;left:0;top:0;width:90px;height:150px;' +
      'pointer-events:none;z-index:40;opacity:0;transition:opacity .15s;' +
      '--poster-color:transparent;background:transparent;';
    doc.body.appendChild(el);
    el.addEventListener('load', function () {
      // orbit the model's REAL bbox centre + widen FOV so a big turn never clips it (hub AK-FRAME).
      try {
        var c = el.getBoundingBoxCenter && el.getBoundingBoxCenter();
        if (c && isFinite(c.x)) el.cameraTarget = c.x.toFixed(3) + 'm ' + c.y.toFixed(3) + 'm ' + c.z.toFixed(3) + 'm';
        el.fieldOfView = '34deg';
      } catch (_e) {}
      var cl = pickClips(el.availableAnimations || [], url);
      rg.idle = cl.idle; rg.walk = cl.walk; rg.run = cl.run; rg.combat = cl.combat; rg.ready = true;
    });
    rg.mv = el; rg.url = url;
  }

  function unitKill(k) {
    var rg = units[k]; if (!rg) return;
    try { if (rg.mv) { rg.mv.removeAttribute('src'); if (rg.mv.parentNode) rg.mv.parentNode.removeChild(rg.mv); } } catch (_e) {}
    delete units[k]; unitN--; if (unitN < 0) unitN = 0;
  }

  // sweep: hide the cold, destroy the frozen (mirrors hub3d unitLoop + the hero hideLoop). A unit not
  // fed for ~200ms is HIDDEN; still cold at 2.5s is DESTROYED so the context + slot free -- which also
  // cleans the pool when the match ends and drawUnit stops feeding.
  (function unitLoop() {
    try {
      var t = nowMs();
      for (var k in units) {
        var rg = units[k], age = t - rg.last;
        if (age > 2500) unitKill(k);
        else if (age > 200 && rg.mv && rg.mv.style.opacity !== '0') rg.mv.style.opacity = '0';
      }
    } catch (_e) {}
    try { root.requestAnimationFrame(unitLoop); } catch (_e) {}
  })();

  var POOL = {
    on: true,
    cap: UNIT_CAP,
    // card (object or name) -> hero GLB via the same substring match hub3d uses. '' = keep 2D.
    modelFor: function (card) {
      var s = '';
      if (card && typeof card === 'object') s = (card.name || '') + ' ' + (card.id || '') + ' ' + (card.cardNumber || '');
      else s = String(card || '');
      s = s.toLowerCase().replace(/[^a-z0-9]/g, '');
      if (!s) return '';
      for (var slug in HERO_MODELS) { if (s.indexOf(slug) !== -1) return HERO_MODELS[slug]; }
      return '';
    },
    // Feed one unit this frame. TRUE only when the GLB is on screen; on FALSE the caller draws 2D.
    // x,y are ON-SCREEN (viewport) px of the unit's body point; o = {r, faceAngle, moving, engaging, running}.
    unit: function (key, modelUrl, x, y, o) {
      if (!this.on || !key || !modelUrl) return false;
      if (!mvReady()) return false;                         // web component not registered yet -> 2D
      o = o || {};
      var rg = units[key];
      if (!rg) {
        if (unitN >= UNIT_CAP) return false;                // over cap -> 2D, no crash
        rg = units[key] = { mv: null, url: '', ready: false, cur: '', idle: '', walk: '', run: '',
                            combat: '', last: 0, theta: 0, tgt: 0, have: false };
        unitN++;
        try { unitBuild(rg, modelUrl); } catch (_e) { delete units[key]; unitN--; return false; }
      } else if (modelUrl !== rg.url) {
        try { rg.mv.setAttribute('src', modelUrl); } catch (_e) {}
        rg.url = modelUrl; rg.ready = false; rg.cur = '';
      }
      if (!rg.mv) return false;
      rg.last = nowMs();
      var r = o.r || 20;
      // same footprint math as the hub pool: feet land at y + r*0.9, clamped screen height 70..340.
      var h = Math.max(70, Math.min(340, r * 5)), w = h * 0.6, st = rg.mv.style;
      st.width = w + 'px'; st.height = h + 'px';
      st.left = (x - w / 2) + 'px'; st.top = ((y + r * 0.9) - h) + 'px';
      // real-time yaw toward the travel heading, same THETA_BASE/SIGN/PHI mapping the hero is tuned on.
      if (typeof o.faceAngle === 'number' && o.moving) {
        rg.tgt = THETA_BASE + THETA_SIGN * (o.faceAngle * 180 / Math.PI);
        rg.have = true;
      }
      if (rg.have) {
        var _d = ((rg.tgt - rg.theta + 540) % 360) - 180;   // shortest arc
        rg.theta += _d * 0.3;
        try { rg.mv.cameraOrbit = rg.theta.toFixed(1) + 'deg ' + PHI + 'deg 3.4m'; } catch (_e) {}
      }
      if (!rg.ready) return false;                          // glb still loading -> 2D covers it
      if (st.opacity !== '1') st.opacity = '1';
      // engage (stopped on a target) fires the combat clip; moving plays walk/run; else idle.
      var want;
      if (o.engaging && !o.moving) want = rg.combat || rg.run || rg.idle;
      else if (o.moving) want = (o.running && rg.run) ? rg.run : (rg.walk || rg.idle);
      else want = rg.idle;
      if (want && rg.cur !== want) {
        try { rg.mv.animationName = want; rg.mv.play(); } catch (_e) {}
        rg.cur = want;
      }
      return true;
    },
    // drop one key now (a unit goes down); clear the whole pool on match exit.
    drop: function (key) { try { unitKill(key); } catch (_e) {} },
    clear: function () { try { for (var k in units) unitKill(k); } catch (_e) {} },
    diag: function () { return { on: this.on, cap: UNIT_CAP, live: unitN, mv: mvReady() }; }
  };
  root.AK_ARENA3D_UNITS = POOL;
})(window, document);
