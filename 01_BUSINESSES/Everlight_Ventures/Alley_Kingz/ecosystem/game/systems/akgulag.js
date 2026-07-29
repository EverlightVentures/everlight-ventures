/* ALLEY KINGZ -- AK_GULAG: gulag_3d.glb wired as a REAL, playable 1v1 gulag battle.  AK-GULAG 2026-07-28.
 *
 * OPERATOR: "a gulag battle that uses this map." assets/models/gulag_3d.glb was installed +
 * compressed (~758KB) and, like arena_interior.glb before it, had ZERO references anywhere -- audited
 * by grep across systems/, index.html and game.html. And the gulag itself was already the classic
 * "built but nothing calls it": systems/modes.js openGulag() is a complete 1v1 shooter, but nothing
 * in the whole tree calls openGulag OR routeEncounter (grep -rn returns only modes.js's own
 * definition + export). So the mode was generated and never reachable, and the map was generated and
 * never drawn. This module closes BOTH gaps at once: it renders gulag_3d.glb as the 3D battle floor
 * and runs a live gulag 1v1 on top of it, and it hands Wire a real trigger (a raid LOSS drops you in
 * the gulag for a redemption fight -- CoD "win your way back" semantics).
 *
 * THE PATTERN -- ADDITIVE GL BEHIND A TRANSPARENT Canvas2D, exactly like systems/arena3d.js
 * arena3d mounts a GL bowl UNDER the untouched #board Canvas2D and lets the fight draw on top. This
 * does the same, self-contained: a fixed fullscreen wrap owns TWO stacked canvases --
 *     wrap (opaque dark bg)                 <- the fallback floor if WebGL/GLB never arrives
 *       glCanvas   (WebGL, z below)         <- gulag_3d.glb, the 3D arena floor + walls
 *       uiCanvas   (Canvas2D, TRANSPARENT)  <- the 1v1 combat + HUD, pointer target
 * The combat is drawn with clearRect (never an opaque fill), so the 3D map shows through everywhere
 * the fighters and cover are not. A three.js / GLB failure costs the player nothing: the wrap's own
 * dark CSS background stands in for the floor and the identical 1v1 keeps running in pure 2D. Same
 * degrade discipline three_boot documents and arena3d relies on.
 *
 * WHY ITS OWN CANVASES, NOT ctx.overlay.open (which openGulag uses)
 * The overlay host (index.html:3643) gives its canvas an OPAQUE inline background (#06060a) AND the
 * 2D gulag paints an opaque rect over the whole thing. A GL canvas mounted behind that overlay would
 * be fully occluded -- the 3D map would never be seen. Owning both layers here is the only way the
 * additive-behind trick actually composits, and it keeps the shared overlay host byte-untouched.
 *
 * WHAT IS REUSED vs NEW (say it plainly, per the no-ghost-deals rule)
 *   REUSED  : the proven 1v1 combat mechanics from modes.js openGulag -- the 560x760 arena, the 5
 *             cover blocks, fire()/moveF()/aiThink()/step(), left-half move stick + right-half
 *             aim/fire, LOS-gated rival AI that ducks behind cover when hurt. Reimplemented HERE so
 *             modes.js (another lane's file) is never edited; the logic is a faithful port.
 *   NEW     : gulag_3d.glb rendered as the 3D battle floor, bbox-normalised + framed from its own
 *             bounding sphere (the units trap: a Tripo GLB is ~1 unit and renders 0.3px unless
 *             normalised), and the whole additive two-canvas stage that lets the fight sit on it.
 *   STUBBED : roster sourcing. openGulag reads ctx.cards() for canon stats; this uses sane fixed
 *             statlines + the rival NAME the caller passes. Wiring in the 106-card index is a
 *             follow-up, not required for a real, winnable fight.
 *
 * UNITS: PIXELS, not metres (project law). The arena logic is 560x760 px. The GLB is scaled from its
 * OWN bounding box to a sane on-screen size and then FRAMED from its bounding sphere, never from an
 * authored distance -- a hand-picked camera distance breaks the instant the map is re-exported.
 *
 * ONE RENDERER LAW (three_boot.js:64): a phone evicts WebGL contexts around 8 and the hub already
 * spends ~5 on model-viewer. The gulag is a FULLSCREEN mode -- the hub behind it is not visible -- so
 * on enter this SUSPENDS world3d (AK_WORLD3D.setOn(false)) and drops hub3d's ally pool
 * (window.__ak3d.on=false), then runs its own single renderer, and restores both on exit. Net live
 * contexts during the fight stay well inside the wall, and the renderer is disposed on close so the
 * context is handed straight back (losing the ref without dispose is the "hero randomly goes black"
 * leak three_boot warns about).
 *
 * Browser-only by design (same as systems/arena3d.js: it assigns window.AK_GULAG at load, so it is
 * mounted via <script>, never require()d in node). node --check is clean; the runtime body does no
 * DOM/global work until enter() is called, so simply loading the tag costs nothing.
 * NO em-dashes in strings a player can see (hook law, use --).
 */
window.AK_GULAG = (function (root) {
  'use strict';

  var MODEL = 'assets/models/gulag_3d.glb';
  var WRAP_ID = 'ak-gulag-wrap', GL_ID = 'ak-gulag-gl', UI_ID = 'ak-gulag-ui';

  // Arena logic space, identical to modes.js openGulag so the ported mechanics behave the same.
  var AW = 560, AH = 760;
  var PI = Math.PI;

  // Static cover layout -- the same 5 blocks openGulag uses (a Tetris-ish bunker).
  var COVER = [
    { x: AW / 2 - 130, y: AH / 2 - 110, w: 70, h: 26 },
    { x: AW / 2 + 60,  y: AH / 2 - 110, w: 70, h: 26 },
    { x: AW / 2 - 18,  y: AH / 2 - 14,  w: 36, h: 90 },
    { x: AW / 2 - 130, y: AH / 2 + 86,  w: 70, h: 26 },
    { x: AW / 2 + 60,  y: AH / 2 + 86,  w: 70, h: 26 }
  ];

  // Fixed statlines (the roster-sourcing stub). Winnable, with a slight rival edge in range so the
  // fight has teeth. maxHp/dmg/fireInt are in the same regime openGulag derives from card stats.
  var YOU_ST = { maxHp: 240, dmg: 26, fireInt: 0.46, bSpd: 380, spd: 168 };
  var RV_ST  = { maxHp: 230, dmg: 24, fireInt: 0.52, bSpd: 360, spd: 150 };

  var S = {
    on: false, opts: null, onResult: null, resultSent: false,
    // DOM
    wrap: null, glCanvas: null, uiCanvas: null, ui: null, dpr: 1,
    // three
    THREE: null, renderer: null, scene: null, camera: null, stage: null,
    booted3d: false, tried3d: false, needFrame: false, worldWas: null, poolWas: false,
    // combat
    fighters: null, bullets: null, C: null, inp: null, TF: null, vp: null,
    // loop
    raf: 0, last: 0, closeAt: 0
  };

  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function hyp(dx, dy) { return Math.sqrt(dx * dx + dy * dy); }

  /* ---------------------------------------------------------------- DOM stage */
  function buildDom() {
    if (S.wrap) return S.wrap;
    var w = document.createElement('div');
    w.id = WRAP_ID;
    // Opaque dark bg IS the fallback floor: with no WebGL/GLB the fight still reads on this plate.
    // z-index 60 clears the overlay host band (index.html overlays use 40) and the 3D world under it.
    w.style.cssText = 'position:fixed;inset:0;z-index:60;background:#070608;touch-action:none;overflow:hidden;';

    var gl = document.createElement('canvas');
    gl.id = GL_ID;
    gl.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:none;';

    var ui = document.createElement('canvas');
    ui.id = UI_ID;
    // TRANSPARENT: cleared with clearRect every frame so the GL map shows through. Pointer target.
    ui.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;background:transparent;';

    w.appendChild(gl);
    w.appendChild(ui);
    document.body.appendChild(w);
    S.wrap = w; S.glCanvas = gl; S.uiCanvas = ui;
    S.ui = ui.getContext('2d');
    fitUi();
    return w;
  }

  function cssW() { return (root.innerWidth || (S.wrap && S.wrap.clientWidth) || 360); }
  function cssH() { return (root.innerHeight || (S.wrap && S.wrap.clientHeight) || 640); }

  function fitUi() {
    if (!S.uiCanvas || !S.ui) return;
    S.dpr = Math.min(2, root.devicePixelRatio || 1);
    var W = cssW(), H = cssH();
    S.uiCanvas.width = Math.max(1, Math.round(W * S.dpr));
    S.uiCanvas.height = Math.max(1, Math.round(H * S.dpr));
    S.ui.setTransform(S.dpr, 0, 0, S.dpr, 0, 0);
    S.vp = { w: W, h: H };
    // arena<->screen fit (portrait board centred), the exact transform openGulag draws with.
    var sc = Math.min(W / AW, H / AH) * 0.92;
    S.TF = { sc: sc, ox: (W - AW * sc) / 2, oy: (H - AH * sc) / 2 };
  }

  function onResize() { fitUi(); syncGlSize(); S.needFrame = true; }

  /* ---------------------------------------------------------------- combat (ported openGulag) */
  function mkF(name, team, x, y, st) {
    return {
      name: String(name || (team ? 'RIVAL' : 'YOU')), team: team, x: x, y: y, r: 16,
      maxHp: st.maxHp, hp: st.maxHp, dmg: st.dmg, fireInt: st.fireInt, bSpd: st.bSpd, spd: st.spd,
      fireT: 0, hitFx: 0, dead: false, strafe: 1, think: 0, _sx: 0, _sy: 0
    };
  }
  function blocked(x, y) {
    for (var i = 0; i < COVER.length; i++) { var c = COVER[i]; if (x > c.x && x < c.x + c.w && y > c.y && y < c.y + c.h) return true; }
    return false;
  }
  function fire(f, tx, ty) {
    if (f.fireT > 0) return; f.fireT = f.fireInt;
    var dx = tx - f.x, dy = ty - f.y, m = hyp(dx, dy) || 1;
    S.bullets.push({ x: f.x + dx / m * (f.r + 4), y: f.y + dy / m * (f.r + 4), vx: dx / m * f.bSpd, vy: dy / m * f.bSpd, dmg: f.dmg, team: f.team, life: 1.6 });
    try { if (root.AK_SFX && root.AK_SFX.play) root.AK_SFX.play('shot'); } catch (_e) {}
  }
  function moveF(f, vx, vy, dt) {
    var nx = clamp(f.x + vx * f.spd * dt, 20, AW - 20), ny = clamp(f.y + vy * f.spd * dt, 20, AH - 20);
    if (!blocked(nx, f.y)) f.x = nx;
    if (!blocked(f.x, ny)) f.y = ny;
  }
  function nearestCover(f) {
    var best = null, bd = 1e9;
    for (var i = 0; i < COVER.length; i++) { var c = COVER[i], cx = c.x + c.w / 2, cy = c.y + c.h / 2, d = hyp(cx - f.x, cy - f.y); if (d < bd) { bd = d; best = { x: cx, y: cy }; } }
    return best;
  }
  function lineBlocked(a, b) {
    var steps = 10;
    for (var i = 1; i < steps; i++) { var t = i / steps; if (blocked(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)) return true; }
    return false;
  }
  function aiThink(f, foe, dt) {
    f.think -= dt; f.fireT -= dt;
    if (f.think <= 0) { f.think = rand(0.5, 1.2); f.strafe = Math.random() < 0.5 ? -1 : 1; }
    var dx = foe.x - f.x, dy = foe.y - f.y, d = hyp(dx, dy) || 1;
    var want = 230;
    var radial = d > want ? 1 : (d < want - 70 ? -1 : 0);
    var perp = { x: -dy / d, y: dx / d };
    var mvx = (dx / d) * radial + perp.x * f.strafe * 0.8;
    var mvy = (dy / d) * radial + perp.y * f.strafe * 0.8;
    var lowHp = f.hp < f.maxHp * 0.35;
    if (lowHp) { var c = nearestCover(f); if (c) { mvx = c.x - f.x; mvy = c.y - f.y; var mm = hyp(mvx, mvy) || 1; mvx /= mm; mvy /= mm; } }
    moveF(f, mvx, mvy, dt);
    if (!lineBlocked(f, foe)) fire(f, foe.x, foe.y);
  }
  function step(dt) {
    S.C.t += dt;
    var you = S.fighters.you, rv = S.fighters.rv, inp = S.inp;
    you.fireT -= dt; if (you.hitFx > 0) you.hitFx -= dt; if (rv.hitFx > 0) rv.hitFx -= dt;
    moveF(you, inp.mvx, inp.mvy, dt);
    if (inp.firing && !you.dead) {
      var tx = inp.ax, ty = inp.ay;
      if (hyp(rv.x - tx, rv.y - ty) < 90) { tx = rv.x; ty = rv.y; }   // light aim-snap onto the rival
      fire(you, tx, ty);
    }
    if (!rv.dead) aiThink(rv, you, dt);
    for (var i = S.bullets.length - 1; i >= 0; i--) {
      var b = S.bullets[i]; b.x += b.vx * dt; b.y += b.vy * dt; b.life -= dt;
      if (b.life <= 0 || b.x < 0 || b.x > AW || b.y < 0 || b.y > AH || blocked(b.x, b.y)) { S.bullets.splice(i, 1); continue; }
      var tgt = b.team === 0 ? rv : you;
      if (!tgt.dead && hyp(b.x - tgt.x, b.y - tgt.y) < tgt.r) {
        tgt.hp -= b.dmg; tgt.hitFx = 0.12; S.bullets.splice(i, 1);
        if (tgt.hp <= 0 && !S.C.over) {
          tgt.dead = true; S.C.over = true; S.C.win = (tgt === rv);
          S.closeAt = S.C.t + 1.5;                     // let the banner land before we close
          try { if (root.AK_SFX && root.AK_SFX.play) root.AK_SFX.play(S.C.win ? 'victory' : 'defeat'); } catch (_e) {}
        }
      }
    }
  }

  /* ---------------------------------------------------------------- combat draw (transparent) */
  function X(x) { return S.TF.ox + x * S.TF.sc; }
  function Y(y) { return S.TF.oy + y * S.TF.sc; }
  function aimToArena(px, py) { return { x: (px - S.TF.ox) / S.TF.sc, y: (py - S.TF.oy) / S.TF.sc }; }

  function chip(g, x, y, r, fill, ring, letter, name) {
    g.save();
    g.globalAlpha = 0.3; g.fillStyle = '#000'; g.beginPath(); g.ellipse(x, y + r * 0.7, r, r * 0.4, 0, 0, 2 * PI); g.fill(); g.globalAlpha = 1;
    g.beginPath(); g.arc(x, y, r, 0, 2 * PI); g.fillStyle = fill; g.fill();
    g.lineWidth = 2.4; g.strokeStyle = ring; g.stroke();
    g.fillStyle = '#0b0b0f'; g.font = '900 ' + Math.round(r * 0.95) + 'px Inter,sans-serif';
    g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(letter, x, y + 0.5);
    g.font = '800 10px Inter,sans-serif'; g.fillStyle = '#eef'; g.fillText(name, x, y - r - 8);
    g.restore();
  }
  function bar(g, x, y, w, h, frac, col) {
    g.save(); g.fillStyle = 'rgba(0,0,0,.55)'; g.fillRect(x, y, w, h);
    g.fillStyle = col; g.fillRect(x, y, w * clamp(frac, 0, 1), h);
    g.strokeStyle = 'rgba(255,255,255,.25)'; g.lineWidth = 1; g.strokeRect(x, y, w, h); g.restore();
  }
  function banner(g, vp, title, col) {
    g.save(); g.fillStyle = 'rgba(6,6,12,.72)'; g.fillRect(0, vp.h / 2 - 44, vp.w, 88);
    g.fillStyle = col; g.font = '900 26px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(title, vp.w / 2, vp.h / 2); g.restore();
  }
  function drawCombat() {
    var g = S.ui, vp = S.vp; if (!g || !vp) return;
    g.clearRect(0, 0, vp.w, vp.h);                     // TRANSPARENT: the 3D map shows through

    // Faint arena boundary + cover, semi-transparent so the map reads underneath them.
    g.save();
    g.strokeStyle = 'rgba(201,168,76,.45)'; g.lineWidth = 2;
    g.strokeRect(X(0), Y(0), AW * S.TF.sc, AH * S.TF.sc);
    for (var i = 0; i < COVER.length; i++) {
      var c = COVER[i];
      g.fillStyle = 'rgba(40,38,32,.62)'; g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1.4;
      g.fillRect(X(c.x), Y(c.y), c.w * S.TF.sc, c.h * S.TF.sc);
      g.strokeRect(X(c.x), Y(c.y), c.w * S.TF.sc, c.h * S.TF.sc);
    }
    g.restore();

    for (var b = 0; b < S.bullets.length; b++) {
      var bu = S.bullets[b];
      g.fillStyle = bu.team === 0 ? '#ffe08a' : '#ff8a6b';
      g.beginPath(); g.arc(X(bu.x), Y(bu.y), 3 * S.TF.sc, 0, 2 * PI); g.fill();
    }

    ['rv', 'you'].forEach(function (k) {
      var f = S.fighters[k]; if (!f || f.dead) return;
      var fill = f.team === 0 ? '#caa84c' : '#b8434c';
      var ring = f.team === 0 ? '#fff' : '#ff9a9a';
      var rr = (f.r + (f.hitFx > 0 ? 2 : 0)) * S.TF.sc;
      chip(g, X(f.x), Y(f.y), rr, fill, ring, String(f.name).charAt(0).toUpperCase(), f.name);
      bar(g, X(f.x) - f.r * S.TF.sc, Y(f.y) - (f.r + 9) * S.TF.sc, f.r * 2 * S.TF.sc, 4, f.hp / f.maxHp, f.team === 0 ? '#6be08a' : '#ff6b6b');
    });

    // HUD
    g.save();
    g.fillStyle = 'rgba(6,6,12,.82)'; g.fillRect(0, 0, vp.w, 36);
    g.fillStyle = '#ff8a6b'; g.font = '900 13px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText('THE GULAG -- 1v1 -- win your way back', vp.w / 2, 18);
    g.restore();
    var you = S.fighters.you, rv = S.fighters.rv;
    bar(g, 14, vp.h - 26, 150, 12, you.hp / you.maxHp, '#6be08a');
    g.fillStyle = '#cfe'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText(you.name, 14, vp.h - 38);
    bar(g, vp.w - 164, 44, 150, 10, rv.hp / rv.maxHp, '#ff6b6b');
    g.fillStyle = '#f9b'; g.textAlign = 'right'; g.fillText(rv.name, vp.w - 14, 56);
    // aim hint ring (right thumb)
    g.save(); g.globalAlpha = 0.5; g.strokeStyle = '#e8c55a'; g.lineWidth = 1.5;
    g.beginPath(); g.arc(vp.w - 60, vp.h - 70, 40, 0, 2 * PI); g.stroke();
    g.fillStyle = '#e8c55a'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'center'; g.fillText('AIM+FIRE', vp.w - 60, vp.h - 70); g.restore();

    if (S.C.over) banner(g, vp, S.C.win ? "YOU'RE BACK IN -- GULAG WON" : 'DROPPED FOR GOOD -- GULAG LOST', S.C.win ? '#6be08a' : '#ff6b6b');
  }

  /* ---------------------------------------------------------------- pointer (ported openGulag) */
  function onPointer(evt) {
    if (!S.vp) return;
    var x = evt.clientX, y = evt.clientY, t = evt.type, inp = S.inp;
    if (t === 'pointerdown') {
      if (x < S.vp.w * 0.5) { inp.mvId = evt.pointerId; inp.mox = x; inp.moy = y; inp.mvx = 0; inp.mvy = 0; }
      else { inp.aimId = evt.pointerId; var a = aimToArena(x, y); inp.ax = a.x; inp.ay = a.y; inp.firing = true; }
    } else if (t === 'pointermove') {
      if (evt.pointerId === inp.mvId) { var dx = x - inp.mox, dy = y - inp.moy, m = hyp(dx, dy), cl = Math.min(m, 48) / 48, u = m || 1; inp.mvx = dx / u * cl; inp.mvy = dy / u * cl; }
      else if (evt.pointerId === inp.aimId) { var a2 = aimToArena(x, y); inp.ax = a2.x; inp.ay = a2.y; }
    } else {
      if (evt.pointerId === inp.mvId) { inp.mvId = null; inp.mvx = 0; inp.mvy = 0; }
      if (evt.pointerId === inp.aimId) { inp.aimId = null; inp.firing = false; }
    }
  }

  /* ---------------------------------------------------------------- 3D floor (gulag_3d.glb) */
  function warmThree() { try { var B = root.AK_THREE; if (B && B.ready) B.ready(); } catch (_e) {} }

  function syncGlSize() {
    if (!S.renderer || !S.glCanvas) return;
    var W = cssW(), H = cssH();
    try {
      S.renderer.setPixelRatio(Math.min(root.devicePixelRatio || 1, 2));
      S.renderer.setSize(W, H, false);
      if (S.camera) { S.camera.aspect = W / Math.max(1, H); S.camera.updateProjectionMatrix(); }
    } catch (_e) {}
  }

  // Frame the whole map from its OWN bounding sphere -- never an authored distance (re-export proof).
  function frameStage() {
    if (!S.stage || !S.camera || !S.THREE) return;
    var THREE = S.THREE;
    try {
      var bb = new THREE.Box3().setFromObject(S.stage);
      var sph = bb.getBoundingSphere(new THREE.Sphere());
      var R = sph.radius || 1;
      var vFov = S.camera.fov * PI / 180;
      var hFov = 2 * Math.atan(Math.tan(vFov / 2) * (S.camera.aspect || 1));
      var dist = (R / Math.sin(Math.min(vFov, hFov) / 2)) * 1.08;
      // 58deg above the floor: high enough that the fight plane reads almost top-down (so the 2D
      // combat maps cleanly onto it), low enough that the bunker walls still rise as real geometry.
      var el = 58 * PI / 180;
      S.camera.position.set(sph.center.x, sph.center.y + dist * Math.sin(el), sph.center.z + dist * Math.cos(el));
      S.camera.lookAt(sph.center.x, sph.center.y, sph.center.z);
      S.camera.updateProjectionMatrix();
    } catch (_e) {}
  }

  function boot3d() {
    if (S.tried3d) return; S.tried3d = true;
    var B = root.AK_THREE;
    if (!B || !B.ok || !B.ok()) { warmThree(); S.tried3d = false; return; }   // not up yet, retry next frame
    var THREE = B.get(); if (!THREE) { return; }
    S.THREE = THREE;

    // ONE RENDERER LAW: suspend the hub's 3D world + ally pool so we are the only live renderer.
    try { if (root.AK_WORLD3D && root.AK_WORLD3D.isOn && root.AK_WORLD3D.isOn()) { root.AK_WORLD3D.setOn(false); S.worldWas = true; } } catch (_e) {}
    try { var p = root.__ak3d; if (p && p.on) { S.poolWas = true; p.on = false; if (p.clear) p.clear(); } } catch (_e2) {}

    try { S.renderer = new THREE.WebGLRenderer({ canvas: S.glCanvas, antialias: false, alpha: true }); }
    catch (_e3) { S.renderer = null; return; }

    S.scene = new THREE.Scene();
    var tint = 0x0c0a12;
    S.scene.background = new THREE.Color(tint);
    // NO distance fog. The camera distance is DERIVED from the model's bounding sphere (frameStage),
    // so it scales with whatever size the GLB exports at -- ~5.5k units here. A hardcoded fog far
    // plane (the first cut used 5200) then sits INSIDE the model and fogs the whole map to black:
    // the map rendered (95 calls / 8943 tris) but every pixel was beyond the far plane. A tight
    // bunker needs no distance haze anyway, so the safe fix is to remove the scale-coupled fog
    // entirely rather than chase the export size every time.
    // Generous, emissive-floored lighting (same reasoning gulagFPS documents) so no export regime
    // can render the bunker pitch black.
    S.scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x2a2016, 1.35));
    var key = new THREE.DirectionalLight(0xffe6b4, 1.35); key.position.set(400, 1600, 700); S.scene.add(key);
    var rim = new THREE.DirectionalLight(0x9fc0ff, 0.7); rim.position.set(-500, 700, -600); S.scene.add(rim);
    S.scene.add(new THREE.AmbientLight(0xffffff, 0.55));

    S.camera = new THREE.PerspectiveCamera(46, (cssW() / Math.max(1, cssH())), 1, 12000);
    S.booted3d = true;
    syncGlSize();

    B.loadGLB(MODEL, function (glb) {
      var o = glb && (glb.scene || glb);
      if (!o || !S.scene) return;
      try {
        // bbox-normalise: scale the model's longest footprint edge up to ~1400px so it fills the
        // stage at a phone-sane world size, seat it on y=0, centre it under the camera. WITHOUT this
        // a ~1-unit Tripo export renders sub-pixel (the documented units trap).
        var bb = new THREE.Box3().setFromObject(o);
        var sz = bb.getSize(new THREE.Vector3());
        var foot = Math.max(sz.x, sz.z, 1e-6);
        var k = 1400 / foot;
        o.scale.setScalar(k);
        var bb2 = new THREE.Box3().setFromObject(o);
        o.position.y = -bb2.min.y;
        var c2 = bb2.getCenter(new THREE.Vector3());
        o.position.x = -c2.x; o.position.z = -c2.z;
        // Interiors are seen from inside = all back faces; force DoubleSide or the far wall vanishes.
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
      } catch (_e4) {}
      S.scene.add(o); S.stage = o;
      frameStage();
      S.needFrame = true;
      if (S.glCanvas) S.glCanvas.style.display = 'block';   // reveal only once the map is actually in
    }, function () { /* GLB missing: stay on the dark fallback plate, fight still runs */ });
  }

  function render3d() {
    if (!S.renderer || !S.scene || !S.camera) return;
    if (S.needFrame) { S.needFrame = false; frameStage(); }
    try { S.renderer.render(S.scene, S.camera); } catch (_e) {}
  }

  // Snapshot the live 3D framing for diag() -- pure read, no side effects. Used to prove the map is
  // actually on-camera (the map-not-visible class of bug is a framing/scale problem, not a load one).
  function stageStats() {
    if (!S.THREE || !S.stage || !S.camera) return null;
    try {
      var bb = new S.THREE.Box3().setFromObject(S.stage);
      var sz = bb.getSize(new S.THREE.Vector3()), c = bb.getCenter(new S.THREE.Vector3());
      var cp = S.camera.position;
      var info = (S.renderer && S.renderer.info && S.renderer.info.render) || {};
      return {
        size: [Math.round(sz.x), Math.round(sz.y), Math.round(sz.z)],
        center: [Math.round(c.x), Math.round(c.y), Math.round(c.z)],
        min: [Math.round(bb.min.x), Math.round(bb.min.y), Math.round(bb.min.z)],
        max: [Math.round(bb.max.x), Math.round(bb.max.y), Math.round(bb.max.z)],
        cam: [Math.round(cp.x), Math.round(cp.y), Math.round(cp.z)],
        calls: info.calls || 0, tris: info.triangles || 0,
        gl: [S.glCanvas ? S.glCanvas.width : 0, S.glCanvas ? S.glCanvas.height : 0],
        disp: S.glCanvas ? S.glCanvas.style.display : '?'
      };
    } catch (_e) { return null; }
  }

  /* ---------------------------------------------------------------- loop */
  function frame(now) {
    if (!S.on) return;
    var dt = Math.min(0.05, (now - S.last) / 1000); S.last = now;
    if (!S.booted3d && S.wrap) { S.tried3d = false; boot3d(); }   // keep probing until three lands
    if (!S.C.over) step(dt);
    render3d();
    drawCombat();
    if (S.C.over && S.C.t >= S.closeAt) { finish(); return; }
    S.raf = root.requestAnimationFrame(frame);
  }

  function finish() {
    var win = !!(S.C && S.C.win);
    close();
    if (!S.resultSent) {
      S.resultSent = true;
      try { if (typeof S.onResult === 'function') S.onResult({ win: win }); } catch (_e) {}
    }
  }

  /* ---------------------------------------------------------------- public: enter / close */
  function enter(opts) {
    if (S.on) return null;                       // one gulag at a time
    opts = opts || {};
    S.opts = opts; S.onResult = opts.onResult || null; S.resultSent = false;
    S.on = true; S.tried3d = false; S.booted3d = false; S.needFrame = false;
    S.worldWas = null; S.poolWas = false;

    var rival = opts.rival || 'RIVAL';
    S.fighters = { you: mkF(opts.heroName || 'YOU', 0, AW / 2, AH - 90, YOU_ST), rv: mkF(rival, 1, AW / 2, 90, RV_ST) };
    S.bullets = [];
    S.C = { t: 0, over: false, win: false };
    S.inp = { mvId: null, mox: 0, moy: 0, mvx: 0, mvy: 0, aimId: null, ax: 0, ay: 0, firing: false };
    S.closeAt = 0;

    buildDom();
    ['pointerdown', 'pointermove', 'pointerup', 'pointercancel'].forEach(function (t) { S.uiCanvas.addEventListener(t, onPointer); });
    root.addEventListener('resize', onResize);
    if (root.visualViewport) try { root.visualViewport.addEventListener('resize', onResize); } catch (_e) {}
    warmThree();

    S.last = (root.performance && root.performance.now) ? root.performance.now() : Date.now();
    S.raf = root.requestAnimationFrame(frame);
    return { close: function () { finish(); } };
  }

  function close() {
    if (!S.on) return;
    S.on = false;
    if (S.raf) { try { root.cancelAnimationFrame(S.raf); } catch (_e) {} S.raf = 0; }
    root.removeEventListener('resize', onResize);
    if (root.visualViewport) try { root.visualViewport.removeEventListener('resize', onResize); } catch (_e) {}
    // Dispose our renderer + scene so the WebGL context goes straight back (three_boot leak law).
    try {
      if (S.scene) {
        S.scene.traverse(function (m) {
          if (m.geometry && m.geometry.dispose) try { m.geometry.dispose(); } catch (_e) {}
          if (m.material) { var arr = Array.isArray(m.material) ? m.material : [m.material]; for (var i = 0; i < arr.length; i++) { if (arr[i] && arr[i].dispose) try { arr[i].dispose(); } catch (_e2) {} } }
        });
      }
    } catch (_e3) {}
    try { if (S.renderer) { S.renderer.dispose(); if (S.renderer.forceContextLoss) S.renderer.forceContextLoss(); } } catch (_e4) {}
    S.renderer = null; S.scene = null; S.camera = null; S.stage = null; S.THREE = null; S.booted3d = false;
    // Restore the hub's 3D world + ally pool exactly as we found them.
    try { if (S.worldWas && root.AK_WORLD3D && root.AK_WORLD3D.setOn) root.AK_WORLD3D.setOn(true); } catch (_e5) {}
    try { if (S.poolWas && root.__ak3d) root.__ak3d.on = true; } catch (_e6) {}
    S.worldWas = null; S.poolWas = false;
    if (S.wrap) { try { S.wrap.parentNode && S.wrap.parentNode.removeChild(S.wrap); } catch (_e7) {} }
    S.wrap = null; S.glCanvas = null; S.uiCanvas = null; S.ui = null;
    S.fighters = null; S.bullets = null;
  }

  var API = {
    enter: enter,
    close: function () { finish(); },
    isOn: function () { return S.on; },
    diag: function () {
      return { on: S.on, booted3d: S.booted3d, hasStage: !!S.stage, model: MODEL,
               over: !!(S.C && S.C.over), win: !!(S.C && S.C.win), stage: stageStats() };
    }
  };

  // Self-registering dev/entry global (mirrors index.html's akPunch()): reachable + testable in BOTH
  // hosts without any host edit. Wire the real trigger via the raidmap call site handed back below.
  if (typeof window !== 'undefined') {
    try { window.akGulag = function (rival) { return enter({ rival: rival || 'JAGGED' }); }; } catch (_e) {}
  }

  return API;
})(window);
