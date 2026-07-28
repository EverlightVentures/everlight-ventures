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

  var S = { on: false, booted: false, renderer: null, scene: null, camera: null,
            stadium: null, mount: null, raf: 0, board: null, failed: false };

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

  function boot(cb) {
    if (S.booted) { cb && cb(true); return; }
    var T = root.AK_THREE;
    if (!T || !T.ok || !T.ok()) { S.failed = true; cb && cb(false); return; }
    var THREE = T.get(); if (!THREE) { S.failed = true; cb && cb(false); return; }
    if (!mount()) { S.failed = true; cb && cb(false); return; }

    try {
      S.renderer = new THREE.WebGLRenderer({ canvas: S.mount, antialias: false, alpha: true });
    } catch (_e) { S.failed = true; cb && cb(false); return; }
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
      if (!o) { S.failed = true; cb && cb(false); return; }
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
      cb && cb(true);
    }, function () { S.failed = true; cb && cb(false); });
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
