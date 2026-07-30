/* Alley Kingz -- HUB 3D AVATAR (window.__hero3d)
 *
 * Overlays a live 3D <model-viewer> of the selected hero on top of the Canvas2D
 * district, pinned to the player's screen position. Plays a WALK clip while
 * moving and an IDLE clip while still, and yaws to face the real travel heading. This is
 * how you "walk the district as a real 3D character" without rebuilding the hub
 * in WebGL: the 2D world stays, the player becomes a 3D model.
 *
 * The hub calls __hero3d.pos(screenX, screenY, moving, faceDir, radius, faceAngle)
 * once per frame from its avatar-draw. Fully guarded: if the model has not loaded
 * (engine blocked, glb missing), .active stays false and the hub keeps drawing the
 * 2D avatar, so nothing ever disappears.
 *
 * Model = assets/models/bcardd.glb ($BCARDD, the 4-animation Tripo export). The clips
 * export with GENERIC names (NlaTrack.00X), so idle/walk are pinned by INDEX below,
 * VERIFIED via GLB motion analysis: 0 = run (25.5 motion / 1.3s loop), 1 = walk
 * (15.2 / 2.4s), 2 = power move (23.7 / 3.9s), 3 = idle (9.8 / 17.6s -- lowest motion,
 * longest loop). Name-match wins first (for future heroes whose clips ARE named);
 * otherwise these indices apply. Override live with
 * window.AK_HERO_CLIPS = {idle:N, walk:N, run:N}.
 */
(function () {
  'use strict';
  var mv = null, ready = false, curAnim = '', names = [], idleN = '', walkN = '', runN = '', lastPos = 0;
  // real-time 3D yaw state + tunables (tuned/verified on the e5 render)
  var curTheta = 0, tgtTheta = 0, haveHeading = false;
  // AK-FACING 2026-07-17: operator reported "he still walks opposite". cameraOrbit rotates the
  // CAMERA around the model, which is the mirror of rotating the model, so the old
  // (BASE 90, SIGN -1) mapping came out handed the wrong way. (BASE -90, SIGN +1) mirrors
  // left/right while KEEPING toward/away correct (theta 0 = front, 180 = back are symmetric
  // under the sign, so only the sideways case changes).
  var THETA_BASE = -90;  // deg: maps "screen right" heading onto the model's front
  var THETA_SIGN = 1;    // flip if the hero turns the wrong way
  var PHI = 72;          // deg: slight 3rd-person downward tilt (90 = eye level)
  // GLB-verified clip indices for $BCARDD's generic-named export (see header).
  // Single source of truth for idle/walk/run; override live via window.AK_HERO_CLIPS.
  // e5 render (2026-07-17) independently confirmed clip3 = the relaxed idle loop.
  /* AK-CLIPMAP 2026-07-20: clip indices are PER MODEL, not global. This is not a nicety -- the
  // legendary bcardd.glb ships 14 clips while jagged.glb ships 4, so a single global
  // {idle:2, walk:10, run:7} puts walk and run OUT OF RANGE on Jagged and breaks him outright.
  // Exporters name every clip NlaTrack.00N, so names carry zero information and indices must be
  // MEASURED per model, by motion analysis, not guessed:
  //     bcardd legendary (14 clips)  clip 2  rot 4.3   trans 0.005 -> IDLE (stationary, lowest of 14)
  //                                  clip 10 rot 52.1  trans 1.23  -> WALK
  //                                  clip 7  rot 207.3 trans 2.50  -> RUN  (2x walk's travel)
  //     jagged / basic rig (4 clips) the original GLB-verified set, unchanged
  // Translation range is the discriminator: a stationary idle against a walk/run pair reads as
  // roughly 0 : 1 : 2. WHEN A NEW HERO GLB LANDS, RE-MEASURE IT AND ADD A ROW HERE. Falling back
  // to the 4-clip default on an unknown 14-clip model would silently play the wrong animations. */
  /* AK-3DALL 2026-07-28: ALL SIX heroes re-exported as the *_3d_all GLBs (operator downloaded a new
   * batch with MORE animations). Every index below was RE-MEASURED from the new file's animation
   * accessors via scratchpad/glb_measure.py (per-bone leg/arm rotation energy + root translation
   * range -- the same motion-analysis method as before, since NlaTrack.00N names still carry zero
   * info and a fresh export REORDERS every clip). Proof it must be re-measured: old bcardd.glb was
   * {2,10,7}; the new Bacardi_3d_all export measures {5,1,8}. The three new breed heroes map to their
   * bible cards (cards_catalog.js): bulldog=Grit Bulldog 0006, rottweiler=Iron Rottweiler 0004,
   * malamute=Blackout Malamute 0127. */
  /* AK-CLIPFIX 2026-07-28 (operator: "my hero uses his front kick as a walk"). RE-MEASURED every GLB's
   * animation accessors: a quadruped WALK is LEG-driven with QUIET arms (leg/arm energy ratio ~2-2.7),
   * whereas the old table pointed `walk` at arm-active COMBAT clips -- so the hub played a punch/kick as
   * the walk. New indices = highest leg-dominance for walk, fastest high-energy leg cycle for run, lowest
   * energy for idle. Corroborated: the akheroactions header independently measured bcardd walk=10 too. */
  var CLIP_BY_MODEL = {
    'bcardd.glb':     { idle: 5,  walk: 10, run: 2 },   // Bacardi_3d_all 14 clips  (was walk:1 = a leg-lunge combat clip)
    'balboa.glb':     { idle: 15, walk: 4,  run: 5 },   // Balboa_3d_all 16 clips
    'jagged.glb':     { idle: 9,  walk: 1,  run: 12 },  // Jagged_3d_all 15 clips
    'bulldog.glb':    { idle: 1,  walk: 3,  run: 7 },   // Grit Bulldog 0006, 10 clips
    'rottweiler.glb': { idle: 4,  walk: 9,  run: 5 },   // Iron Rottweiler 0004, 12 clips
    'malamute.glb':   { idle: 11, walk: 7,  run: 0 }    // Blackout Malamute 0127, 12 clips
  };
  var CLIP_DEFAULT = { idle: 3, walk: 1, run: 0 }; // safe on any 4-clip Tripo export
  /* AK-3DC-COMBAT 2026-07-29: strike (JAB) clip RAW-index per hero for the 3D-unit pool, taken from
   * akheroactions' measured combat set. Lets a deployed/raid/lane GLB throw a real punch on a landed
   * hit (index.html/game.html pass opts.combat). Missing model -> no combat clip -> unit stays on walk. */
  var COMBAT_BY_MODEL = { 'bcardd.glb': 3, 'balboa.glb': 14, 'jagged.glb': 5, 'bulldog.glb': 10, 'rottweiler.glb': 2, 'malamute.glb': 9 };
  function clipsForModel(url) {
    var u = String(url || '');
    for (var k in CLIP_BY_MODEL) { if (u.indexOf(k) !== -1) return CLIP_BY_MODEL[k]; }
    return CLIP_DEFAULT;
  }
  var CLIP_IDX = clipsForModel(typeof DEFAULT_MODEL !== 'undefined' ? DEFAULT_MODEL : '');
  // Hero -> 3D model registry. Whoever the player has SELECTED as their hero
  // loads THAT hero's glb -- not hardcoded. Rich runs $BCARDD so it resolves to
  // bcardd.glb; a player who picked Jagged resolves to jagged.glb. Per Rich:
  // "whoever's using that hero uses that GLB." Add a row here per new hero model.
  var HERO_MODELS = {
    bcardd: 'assets/models/bcardd.glb',
    jagged: 'assets/models/jagged.glb',
    balboa: 'assets/models/balboa.glb',
    // AK-3DALL 2026-07-28: three new breed heroes. Keys are the BREED slug on purpose -- the resolver
    // below matches by substring (indexOf), so 'rottweiler' matches the card "Iron Rottweiler",
    // 'bulldog' matches "Grit Bulldog", 'malamute' matches "Blackout Malamute".
    rottweiler: 'assets/models/rottweiler.glb',   // Iron Rottweiler (0004)
    bulldog:    'assets/models/bulldog.glb',       // Grit Bulldog (0006)
    malamute:   'assets/models/malamute.glb'       // Blackout Malamute (0127)
  };
  var DEFAULT_MODEL = 'assets/models/bcardd.glb';   // $BCARDD fallback (4 anims, 43-bone rig)
  // Resolve the selected hero's model. A future hero-selector sets window.AK_HERO
  // (or the player object's heroId/avatarCard); until then this returns $BCARDD.
  // AK-RUNNER3D 2026-07-18: resolve the 3D model from the REAL runner. The hub's runner picker
  // stores the choice as p.heroName and surfaces it through heroCard() (which also enforces
  // ownership + the infirmary rule). We were reading window.AK_HERO / me.heroId, which the picker
  // never sets -- so switching runner changed the 2D card but the 3D hero stayed $BCARDD.
  // Now: AK_HERO (explicit override) -> heroCard() (the truth) -> me.* (legacy fallback).
  function heroSlug() {
    var raw = '';
    try {
      if (window.AK_HERO) raw = window.AK_HERO;
      else if (typeof window.heroCard === 'function') {
        var c = window.heroCard();
        if (c) raw = c.name || c.id || c.cardNumber || '';
      }
      if (!raw && window.me) raw = window.me.heroId || window.me.avatarCard || window.me.hero || '';
    } catch (_e) {}
    return String(raw).toLowerCase().replace(/[^a-z0-9]/g, '');
  }
  function heroModel() {
    var s = heroSlug();
    for (var slug in HERO_MODELS) { if (s.indexOf(slug) !== -1) return HERO_MODELS[slug]; }
    return DEFAULT_MODEL;   // any runner without its own GLB still walks as the default rig
  }
  var MODEL = heroModel(), _tick = 0, _unlocked = false;

  // AK-UNIT3D 2026-07-18: clip resolver, lifted VERBATIM out of the hero's load handler so the
  // hero and the pooled units below pick idle/walk/run the exact same way and can never drift.
  // Name-match first (named-clip heroes); else the GLB-verified index; else clip 0.
  function pickClips(nm) {
    var ov = (typeof window !== 'undefined' && window.AK_HERO_CLIPS) || {};
    // AK-CLIPMAP: resolve against whichever model is actually loaded right now. MODEL changes when
    // the player switches hero, so reading a boot-time constant here would apply bcardd's 14-clip
    // indices to Jagged's 4-clip rig.
    var CI = clipsForModel(MODEL);
    var iIdle = ov.idle != null ? ov.idle : CI.idle;
    var iWalk = ov.walk != null ? ov.walk : CI.walk;
    var iRun  = ov.run  != null ? ov.run  : CI.run;
    var _i = nm.find(function (n) { return /idle|stand|relax/i.test(n); })
             || nm[iIdle] || nm[0] || '';
    var _w = nm.find(function (n) { return /walk|move|trot/i.test(n); })
             || nm[iWalk] || (nm.length > 1 ? nm[1] : nm[0]) || '';
    var _r = nm.find(function (n) { return /run|sprint|dash/i.test(n); })
             || nm[iRun] || _w || '';
    return { idle: _i, walk: _w, run: _r };
  }

  // AK-HEROUNLOCK 2026-07-18: THE RULE -- if we shipped a 3D hero for a card, that card IS playable
  // as a runner. The runner picker only lists OWNED cards, so a finished hero the player does not own
  // is unreachable: that is exactly why Jagged (card 0013, full GLB live) never appeared in the picker.
  // Rather than hand-granting one dog, every hero in HERO_MODELS is ensured owned. New hero + GLB =
  // automatically switchable, no follow-up wiring. Idempotent, guarded, runs once per load.
  // AK-3DALL 2026-07-28: hero slug -> bible card NAME (cards_catalog.js), so every hero with a GLB is
  // auto-granted + switchable. balboa was missing before; the three breed heroes are new.
  var HERO_CARD_NAME = {
    bcardd: '$BCARDD', jagged: 'Jagged', balboa: 'Balboa',
    rottweiler: 'Iron Rottweiler', bulldog: 'Grit Bulldog', malamute: 'Blackout Malamute'
  };
  function unlockHeroes() {
    try {
      var econ = window.AK_ECON;
      if (!econ || typeof econ.mutateProfile !== 'function') return false;
      var added = 0;
      econ.mutateProfile(function (p) {
        if (!Array.isArray(p.owned)) p.owned = [];
        for (var s in HERO_MODELS) {
          var nm = HERO_CARD_NAME[s];
          if (nm && p.owned.indexOf(nm) < 0) { p.owned.push(nm); added++; }
        }
      });
      if (added && typeof window.akHeroBust === 'function') window.akHeroBust();
      return true;                                  // econ was ready; stop retrying
    } catch (_e) { return false; }
  }

  function build() {
    mv = document.createElement('model-viewer');
    mv.setAttribute('src', MODEL);
    mv.setAttribute('autoplay', '');
    mv.setAttribute('interaction-prompt', 'none');
    mv.setAttribute('disable-zoom', '');
    mv.setAttribute('disable-tap', '');
    mv.setAttribute('disable-pan', '');
    mv.setAttribute('shadow-intensity', '0');
    mv.setAttribute('exposure', '1.0');
    mv.setAttribute('camera-orbit', '0deg ' + PHI + 'deg 3.4m');
    mv.setAttribute('camera-target', '0m 0.95m 0m');
    mv.setAttribute('field-of-view', '26deg');
    mv.style.cssText = 'position:fixed;left:0;top:0;width:120px;height:200px;' +
      'pointer-events:none;z-index:3;opacity:0;transition:opacity .18s;' +
      '--poster-color:transparent;background:transparent;';
    document.body.appendChild(mv);
    mv.addEventListener('load', function () {
      // AK-FRAME 2026-07-18: orbit around the MODEL'S REAL CENTRE, not a hardcoded target.
      // The GLB's origin is offset from the body, so orbiting a fixed '0m 0.95m 0m' swung him out
      // of the 26deg frame on ONE side -- he vanished running LEFT but was fine running RIGHT.
      // Centring on the bounding box makes the turn symmetric. Also widen the FOV + pull the
      // camera back a touch so a big turn can never clip him out of frame.
      try {
        var c = mv.getBoundingBoxCenter && mv.getBoundingBoxCenter();
        if (c && isFinite(c.x)) {
          mv.cameraTarget = c.x.toFixed(3) + 'm ' + c.y.toFixed(3) + 'm ' + c.z.toFixed(3) + 'm';
        }
        mv.fieldOfView = '34deg';
      } catch (_e) {}
      names = mv.availableAnimations || [];
      var cl = pickClips(names);
      idleN = cl.idle; walkN = cl.walk; runN = cl.run;
      ready = true;
    });
    // auto-hide when the hub stops feeding positions (menus, battle, other views)
    (function hideLoop() {
      try {
        if (mv && (nowMs() - lastPos) > 160 && mv.style.opacity !== '0') {
          mv.style.opacity = '0'; API.active = false;
        }
      } catch (_e) {}
      requestAnimationFrame(hideLoop);
    })();
  }
  function nowMs() { try { return performance.now(); } catch (_e) { return lastPos + 999; } }

  var API = {
    on: true,
    active: false,
    setModel: function (url) { MODEL = url; if (mv) { mv.setAttribute('src', url); ready = false; curAnim = ''; } },
    pos: function (x, y, moving, faceDir, r, faceAngle, running) {
      if (!this.on) return;
      if (!mv) { try { build(); } catch (_e) { return; } }
      lastPos = nowMs();
      // AK-RUNNER3D: hot-swap the GLB the instant the player switches runner. Cheap (~every 32
      // frames) and heroCard() is itself 2s-cached, so this costs nothing in the loop.
      if (((++_tick) & 31) === 0) {
        if (!_unlocked) _unlocked = unlockHeroes();          // retry until AK_ECON exists, then never again
        var _want = heroModel(); if (_want !== MODEL) API.setModel(_want);
      }
      var h = Math.max(120, Math.min(340, r * 5)), w = h * 0.6;
      mv.style.width = w + 'px';
      mv.style.height = h + 'px';
      mv.style.left = (x - w / 2) + 'px';
      mv.style.top = ((y + r * 0.9) - h) + 'px';
      // Real-time 3D yaw: the hero TURNS to face the travel heading and SPINS
      // when the player spins, instead of a flat left/right mirror. faceAngle is
      // the screen-space heading in radians (atan2(dy,dx): right=0, down=+90,
      // left=180, up=-90). Orbiting camera theta rotates the model about its
      // vertical axis. THETA_BASE/SIGN/PHI are tuned on the e5 render.
      if (typeof faceAngle === 'number' && moving) {
        tgtTheta = THETA_BASE + THETA_SIGN * (faceAngle * 180 / Math.PI);
        haveHeading = true;
      } else if (typeof faceAngle !== 'number') {
        tgtTheta = THETA_BASE + THETA_SIGN * (faceDir < 0 ? 180 : 0);
        haveHeading = true;
      }
      if (haveHeading) {
        var _d = ((tgtTheta - curTheta + 540) % 360) - 180;   // shortest arc
        curTheta += _d * 0.3;                                 // ease -> smooth turn/spin
        try { mv.cameraOrbit = curTheta.toFixed(1) + 'deg ' + PHI + 'deg 3.4m'; } catch (_e) {}
      }
      if (ready) {
        if (mv.style.opacity !== '1') { mv.style.opacity = '1'; }
        this.active = true;
        var want = !moving ? idleN : (running && runN ? runN : walkN);
        if (want && curAnim !== want) {
          try { mv.animationName = want; mv.play(); } catch (_e) {}
          curAnim = want;
        }
      }
    }
  };
  window.__hero3d = API;

  /* ---- AK-UNIT3D 2026-07-18: POOLED 3D UNITS (window.__ak3d) ---------------------------
   * The hero above owns ONE pinned model-viewer. Deployed allies had no 3D at all -- they
   * were circle-clipped card art in the raid draw -- so a deployed Jagged never showed his
   * GLB even though assets/models/jagged.glb is live. This is the same rig as the hero,
   * keyed by a caller-chosen id, so any unit on the field can render in 3D.
   *
   * CAP = 4 extra units. Each <model-viewer> is a LIVE WebGL context holding its own GLB in
   * GPU memory (bcardd 13 MB, jagged 19 MB) and the target device is a PHONE: mobile
   * browsers start silently dropping the oldest context somewhere around 8, and GPU memory
   * is the real wall well before that. 1 hero + 4 units = 5 contexts, which leaves headroom
   * for the AK_CARDFX <video> pool and the hub's own canvas. Past the cap unit() returns
   * false and the caller keeps drawing 2D card art, so a 6th deployed dog DEGRADES instead
   * of blacking out the raid.
   *
   * Lifecycle mirrors the hero's hideLoop: a key not fed for ~200ms is HIDDEN, and a key
   * still cold at 2.5s is DESTROYED (element removed, context + slot freed). The gap keeps
   * a dog that blinks out for a few frames from paying a 19 MB reload.
   */
  var UNIT_CAP = 4, units = {}, unitN = 0;

  function unitBuild(rg, url) {
    var el = document.createElement('model-viewer');
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
    // z-index 2 = UNDER the hero (3), so your own dog always reads on top of the crew
    el.style.cssText = 'position:fixed;left:0;top:0;width:80px;height:130px;' +
      'pointer-events:none;z-index:2;opacity:0;transition:opacity .18s;' +
      '--poster-color:transparent;background:transparent;';
    document.body.appendChild(el);
    el.addEventListener('load', function () {
      // same bounding-box recentre + widened FOV the hero uses (AK-FRAME): the GLB origin is
      // offset from the body, so a fixed camera-target swings the model out of frame on one side
      try {
        var c = el.getBoundingBoxCenter && el.getBoundingBoxCenter();
        if (c && isFinite(c.x)) el.cameraTarget = c.x.toFixed(3) + 'm ' + c.y.toFixed(3) + 'm ' + c.z.toFixed(3) + 'm';
        el.fieldOfView = '34deg';
      } catch (_e) {}
      var cl = pickClips(el.availableAnimations || []);
      rg.idle = cl.idle; rg.walk = cl.walk; rg.run = cl.run; rg.ready = true;
      // AK-3DC-COMBAT: resolve the strike clip by RAW index (the same indexing akheroactions/CLIP_BY_MODEL use)
      try { var _bn = (rg.url || '').split('/').pop(); var _ci = COMBAT_BY_MODEL[_bn]; var _av = el.availableAnimations || []; if (_ci != null && _av[_ci]) rg.combat = _av[_ci]; } catch (_e) {}
    });
    rg.mv = el; rg.url = url;
  }

  function unitKill(k) {
    var rg = units[k]; if (!rg) return;
    try { if (rg.mv) { rg.mv.removeAttribute('src'); if (rg.mv.parentNode) rg.mv.parentNode.removeChild(rg.mv); } } catch (_e) {}
    delete units[k]; unitN--;
    if (unitN < 0) unitN = 0;
  }

  // sweep: hide the cold, destroy the frozen. Mirrors the hero's hideLoop.
  (function unitLoop() {
    try {
      var t = nowMs();
      for (var k in units) {
        var rg = units[k], age = t - rg.last;
        if (age > 2500) { unitKill(k); }
        else if (age > 200 && rg.mv && rg.mv.style.opacity !== '0') { rg.mv.style.opacity = '0'; }
      }
    } catch (_e) {}
    requestAnimationFrame(unitLoop);
  })();

  var POOL = {
    on: true,
    cap: UNIT_CAP,
    // Resolve ANY card name to its GLB through the SAME HERO_MODELS registry the hero uses,
    // so shipping a new hero model lights it up for deployed units too with no extra wiring.
    // Returns '' when that card has no model -- the caller's signal to keep its 2D card art.
    modelFor: function (name) {
      var s = String(name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      if (!s) return '';
      for (var slug in HERO_MODELS) { if (s.indexOf(slug) !== -1) return HERO_MODELS[slug]; }
      return '';
    },
    // Feed one unit for this frame. RETURNS TRUE only when the 3D model is actually on screen;
    // on false (no model, pool full, still loading, engine blocked) the caller MUST draw its
    // normal 2D art, exactly like the hero's .active guard.
    unit: function (key, modelUrl, x, y, o) {
      if (!this.on || !key || !modelUrl) return false;
      o = o || {};
      var rg = units[key];
      if (!rg) {
        if (unitN >= UNIT_CAP) return false;                 // over cap -> 2D, no crash
        rg = units[key] = { mv: null, url: '', ready: false, cur: '', idle: '', walk: '', run: '',
                            last: 0, theta: 0, tgt: 0, have: false };
        unitN++;
        try { unitBuild(rg, modelUrl); } catch (_e) { delete units[key]; unitN--; return false; }
      } else if (modelUrl !== rg.url) {
        try { rg.mv.setAttribute('src', modelUrl); } catch (_e) {}
        rg.url = modelUrl; rg.ready = false; rg.cur = '';
      }
      rg.last = nowMs();
      if (o.combat && rg.combat) rg.combatT = nowMs() + 450;   // AK-3DC-COMBAT: a landed hit latches a ~450ms strike window
      var r = o.r || 16;
      // same footprint math as the hero (feet land at y + r*0.9), lower floor because a crew
      // dog rides r=16 against the hero's much larger me.r*ds
      var h = Math.max(70, Math.min(340, r * 5)), w = h * 0.6, st = rg.mv.style;
      st.width = w + 'px'; st.height = h + 'px';
      st.left = (x - w / 2) + 'px'; st.top = ((y + r * 0.9) - h) + 'px';
      // real-time yaw, same THETA_BASE/SIGN/PHI mapping the hero is tuned on. No faceAngle
      // just means the unit holds its last heading (front-facing until it first turns).
      if (typeof o.faceAngle === 'number' && o.moving) {
        rg.tgt = THETA_BASE + THETA_SIGN * (o.faceAngle * 180 / Math.PI);
        rg.have = true;
      }
      if (rg.have) {
        var _d = ((rg.tgt - rg.theta + 540) % 360) - 180;    // shortest arc
        rg.theta += _d * 0.3;
        try { rg.mv.cameraOrbit = rg.theta.toFixed(1) + 'deg ' + PHI + 'deg 3.4m'; } catch (_e) {}
      }
      if (!rg.ready) return false;                           // glb still loading -> 2D covers it
      if (st.opacity !== '1') st.opacity = '1';
      // AK-3DC-COMBAT: throwing a strike overrides walk/idle until the latched window elapses, then eases back
      var want = (rg.combat && rg.combatT && nowMs() < rg.combatT) ? rg.combat
               : (!o.moving ? rg.idle : (o.running && rg.run ? rg.run : rg.walk));
      if (want && rg.cur !== want) {
        try { rg.mv.animationName = want; rg.mv.play(); } catch (_e) {}
        rg.cur = want;
      }
      return true;
    },
    // drop one key now (a dog goes down); clear the whole pool on raid exit
    drop: function (key) { try { unitKill(key); } catch (_e) {} },
    clear: function () { try { for (var k in units) unitKill(k); } catch (_e) {} }
  };
  window.__ak3d = POOL;
})();
