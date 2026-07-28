/* game/systems/weather.js -- AK_SYSTEMS module: "2026 ATMOSPHERE PASS".
   ------------------------------------------------------------------------
   Canvas2D weather RENDERER + district FLAVOUR + gameplay MODIFIER aggregator.

   READ THIS BEFORE ADDING ANY CLOCK OR ANY WEATHER ROLL HERE
   ----------------------------------------------------------
   This file deliberately owns NO clock and NO weather roll of its own. The repo
   already had four time/weather authorities before this file existed, and a
   fifth would have been a guaranteed desync bug:

     1. systems/seasons.js  getWeather()      -- CITY weather sun/rain/fog/storm,
        deterministic by the LOCAL PT day (LCG on ptDayIndex). This is the key
        the HUD chip already prints (index.html:3604). CANONICAL for "what is
        the weather".
     2. economy.js          gardenWeather()   -- the older CROP weather roll
        (sun/rain/drought) on a UTC day bucket. buildmode.js stamps it onto each
        garden bed as b.wx. See DIVERGENCE note below.
     3. systems/daynight.js AK_DAYNIGHT       -- real-PT time of day
        (dawn/day/dusk/night) + a soft-light colour grade it already paints in
        its own onDrawWorld. CANONICAL for "what time is it".
     4. systems/raid.js     isNight()         -- an ACCELERATED heartbeat
        (CYCLE_MS = 6 real minutes per full day, NIGHT_FRAC 0.34) that exists so
        a single session can see a night raid. It is a COMBAT PACING clock, not
        a wall clock, and it is intentionally NOT the ambient clock.

   So: weather key comes from seasons.js, ambient phase comes from daynight.js,
   and raid.js isNight() is surfaced separately as `combatNight` so a raid can
   darken the sky without lying about the PT hour. Nothing here re-rolls, and
   the fallback path below reproduces seasons.js's EXACT wheel + LCG + PT-day
   bucket so that even a degraded load cannot disagree with the HUD.

   DIVERGENCE ALREADY IN THE REPO (not this file's to fix, reported upward):
   economy.js gardenWeather uses `Math.floor(t / 86400000)` (a UTC day) over a
   6-slot wheel containing `drought`; seasons.js getWeather uses a PT-offset day
   over an 8-slot wheel containing `fog` + `storm`. Same LCG constants, different
   wheels, different day anchors -- so the HUD chip can read "Storm" while the
   garden beds are running "sun". This module reports both via reconcile() and
   renders the SEASONS key, because that is the one the player can see.

   WHAT THIS FILE OWNS
   - A per-district weather state machine: the canonical key (clear/rain/fog/
     storm) plus district-flavoured VARIANTS -- acid rain on Factory Row, dust
     on The Yards. A variant never changes the canonical key, only the look,
     the blurb, and a small modifier delta, so parity holds across clients.
   - Canvas2D rendering: 3 parallax rain layers, drifting fog banks, lightning
     flash. Batched into O(layers) stroke calls, NOT O(particles). Pooled
     arrays, zero per-frame allocation. Budgets + live counters in budget().
   - GAMEPLAY MODIFIERS other systems read: visibility, move speed, crop growth,
     raid and encounter multipliers. This file edits NO consumer; consumers call
     AK_WEATHER.mod(domain, zoneId).

   EXPLICITLY OUT OF SCOPE (needs the 3D pipeline, do not fake it in 2D)
   - Volumetric fog: needs depth. A real volumetric pass samples the depth
     buffer so fog thickens with distance and wraps geometry. Canvas2D has no
     depth buffer, so what ships here is screen-space fog BANKS with parallax
     drift -- a convincing cheat, not volumetrics. UPGRADE PATH: when three_boot
     .js / world3d.js land a real scene, keep this module as the STATE + MODIFIER
     brain and swap only draw(): feed density(zoneId) into a THREE.FogExp2 on
     the scene and drive its `density` from the same fogDensity() this file
     already computes. The state machine, the variants, and every gameplay
     modifier survive the port untouched.
   - Procedural animation (cloth/foliage reacting to wind): needs per-vertex
     work on real meshes. UPGRADE PATH: windVector() below is already exported
     and already drives the 2D streak slant, so a future vertex shader can read
     the identical vector and stay in sync with the rain the player sees.

   HARD-LAW COMPLIANCE
   - PROFILE-SAFE: writes NOTHING. No AK_ECON.mutateProfile call, no
     localStorage, no persisted field. A never-played profile stays byte
     identical. (Nothing here is worth a save-slot; it is all derivable.)
   - DETERMINISTIC: zero Math.random in the STATE path -- key, variant and phase
     are pure functions of the PT clock, so every client sees the same weather.
     Math.random appears only in particle SEEDING (pure decoration, never read
     by a modifier), matching the seasons.js ambient-particle precedent.
   - HEADLESS-SAFE: no DOM, no canvas, no globals touched at module load. The
     pure window.AK_WEATHER surface always exports; only the AK_SYSTEMS
     registration is gated. Requireable in node.
   - 60fps CHEAP-ANDROID: state recomputes at most every ~20s; the draw path
     reads a cache and issues a fixed, capped number of ops. See budget().
   - CANON ONLY: the 9 real districts, the Fence, the Watch, the Old Pack.
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';

  // ==========================================================================
  // AK-WX 2026-07-18: canonical source adapters. Every one of these is a READ.
  // ==========================================================================

  var DAY_MS = 86400000;
  var PT_OFFSET_MS = 8 * 3600 * 1000;   // matches seasons.js PT_OFFSET_MS exactly

  // seasons.js parity fallback -- same LCG constants, same 8-slot wheel, same PT
  // day bucket. If seasons.js is loaded we ask IT; this only covers a load gap,
  // and it is byte-identical by construction so the two can never disagree.
  var WX_WHEEL = ['sun', 'sun', 'rain', 'fog', 'sun', 'rain', 'storm', 'sun'];
  function ptDayIndex(now) { return Math.floor(((now || Date.now()) - PT_OFFSET_MS) / DAY_MS); }
  function fallbackKey(now) { return WX_WHEEL[((ptDayIndex(now) * 1103515245 + 12345) >>> 0) % WX_WHEEL.length]; }

  // canonical CITY weather key. seasons.js first, econ second, parity wheel last.
  function baseKey(now) {
    try {
      if (global.AKSeasons && global.AKSeasons.getWeather) {
        var w = global.AKSeasons.getWeather(now);
        if (w && w.key) return w.key;
      }
    } catch (_e) {}
    return fallbackKey(now);
  }
  // the seasons.js modifier block for the live key (farm/raid/encounter), so our
  // numbers ARE their numbers and never a second opinion.
  function baseMods(now) {
    var out = { farmMult: 1, raidMult: 1, encounterMult: 1 };
    try {
      if (global.AKSeasons && global.AKSeasons.getWeather) {
        var w = global.AKSeasons.getWeather(now);
        if (w) {
          out.farmMult = num(w.farmMult, 1);
          out.raidMult = num(w.raidMult, 1);
          out.encounterMult = num(w.encounterMult, 1);
        }
      }
    } catch (_e) {}
    return out;
  }
  // ambient time of day -- daynight.js owns the real PT clock, we never re-derive it.
  function ptPhase(now) {
    try { if (global.AK_DAYNIGHT && global.AK_DAYNIGHT.getPhase) return global.AK_DAYNIGHT.getPhase(now); } catch (_e) {}
    return 'day';
  }
  // raid.js accelerated COMBAT night (6-min cycle). Separate on purpose.
  function combatNight() {
    try { if (global.AKRaid && global.AKRaid.isNight) return global.AKRaid.isNight() === true; } catch (_e) {}
    return false;
  }
  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  // ==========================================================================
  // AK-WX 2026-07-18: the state machine. 4 canonical states + district variants.
  // A VARIANT is a skin + a modifier delta on a canonical key, never a new key.
  // ==========================================================================

  // canonical states. `key` mirrors seasons.js exactly (sun|rain|fog|storm);
  // `clear` is accepted as an alias for sun on the way in.
  var STATES = {
    sun:   { key: 'sun',   label: 'Clear Skies', glyph: '☀️', icon: 'assets/icons/wx_sun.png',
             rain: 0,    fog: 0.00, lightning: false, wind: 0.10,
             blurb: 'Dry blocks, clean sightlines over the 9 districts.' },
    rain:  { key: 'rain',  label: 'Rain',        glyph: '🌧️', icon: 'assets/icons/wx_rain.png',
             rain: 1.0,  fog: 0.12, lightning: false, wind: 0.34,
             blurb: 'Crops drink deep, but the Watch runs thin in the wet.' },
    fog:   { key: 'fog',   label: 'Fog',         glyph: '🌫️', icon: 'assets/icons/wx_fog.png',
             rain: 0,    fog: 1.00, lightning: false, wind: 0.06,
             blurb: 'Low cover off the docks -- more strays slip the Fence.' },
    storm: { key: 'storm', label: 'Storm',       glyph: '⛈️', icon: 'assets/icons/wx_storm.png',
             rain: 1.45, fog: 0.30, lightning: true,  wind: 0.85,
             blurb: 'The streets bite back -- harvest suffers, raids turn vicious.' }
  };

  // district-flavoured variants. `on` = which canonical keys this variant skins.
  // deltas MULTIPLY the canonical modifiers -- they never replace them.
  var VARIANTS = {
    acid: {
      id: 'acid', zone: 'FACTORY_ROW', on: { rain: 1, storm: 1 },
      label: 'Acid Rain', glyph: '🌧️', icon: 'assets/icons/wx_rain.png',
      blurb: 'Runoff off the forge stacks. It eats the crops and the paint both.',
      streak: 'rgba(178,255,120,', fogTint: [120, 150, 60],
      d: { farm: 0.75, move: 0.96, vis: 0.94, raid: 1.00, enc: 1.05 }
    },
    dust: {
      id: 'dust', zone: 'THE_YARDS', on: { sun: 1, storm: 1 },
      label: 'Dust Haze', glyph: '🌫️', icon: 'assets/icons/wx_fog.png',
      blurb: 'The lots kick up. Grit in the teeth, and nobody sees the Watch coming.',
      streak: 'rgba(214,178,110,', fogTint: [186, 150, 92],
      d: { farm: 0.92, move: 1.00, vis: 0.80, raid: 1.00, enc: 1.10 }
    }
  };
  function variantFor(zoneId, key) {
    for (var id in VARIANTS) {
      if (!Object.prototype.hasOwnProperty.call(VARIANTS, id)) continue;
      var v = VARIANTS[id];
      if (v.zone === zoneId && v.on[key]) return v;
    }
    return null;
  }

  // phase -> ambient visibility + the streak/fog colour the precip picks up.
  var PHASE_VIS = { dawn: 0.88, day: 1.00, dusk: 0.86, night: 0.72 };
  var PHASE_TINT = {
    dawn:  'rgba(198,214,238,', day: 'rgba(206,224,246,',
    dusk:  'rgba(226,186,208,', night: 'rgba(150,178,232,'
  };

  // ==========================================================================
  // AK-WX 2026-07-18: resolved state, cached. Pure function of (zoneId, clock).
  // ==========================================================================

  function resolve(zoneId, now) {
    now = (now == null) ? Date.now() : now;
    var key = baseKey(now);
    if (key === 'clear') key = 'sun';
    if (key === 'drought') key = 'sun';          // econ-wheel alias -> nearest canonical
    var st = STATES[key] || STATES.sun;
    var ph = ptPhase(now);
    var v = variantFor(zoneId, st.key);
    var cn = combatNight();
    return {
      key: st.key,
      variant: v ? v.id : null,
      label: v ? v.label : st.label,
      glyph: v ? v.glyph : st.glyph,
      icon: v ? v.icon : st.icon,
      blurb: v ? v.blurb : st.blurb,
      phase: ph,                                  // real PT phase (daynight.js)
      night: ph === 'night',                      // ambient night, wall clock
      combatNight: cn,                            // raid.js accelerated night
      rain: st.rain, fogAmt: st.fog, lightning: st.lightning, wind: st.wind,
      zoneId: zoneId || null
    };
  }

  var _st = { z: null, t: 0, v: null };
  var STATE_TTL_MS = 20000;                       // recompute at most every ~20s
  function state(zoneId, now) {
    now = (now == null) ? Date.now() : now;
    var z = zoneId || '';
    // AK-WX 2026-07-18: the age window must be checked as a POSITIVE range. A
    // bare "now - t < TTL" is also true for NEGATIVE ages, so a backwards clock
    // step (NTP correction, DST fallback, the player changing the device clock or
    // timezone) would pin a stale state in this cache until wall-clock caught back
    // up: yesterday's storm still raining on a clear day, with every gameplay
    // modifier reading the stale key right along with it. Negative age = refresh.
    var age = now - _st.t;
    if (_st.v && _st.z === z && age >= 0 && age < STATE_TTL_MS) return _st.v;
    _st.v = resolve(z, now); _st.z = z; _st.t = now;
    return _st.v;
  }

  // ==========================================================================
  // AK-WX 2026-07-18: GAMEPLAY MODIFIERS. Read-only. Consumers call mod().
  // Canonical seasons.js numbers, multiplied by phase + district-variant deltas.
  // ==========================================================================

  function mods(zoneId, now) {
    now = (now == null) ? Date.now() : now;
    var s = state(zoneId, now);
    var b = baseMods(now);
    var v = s.variant ? VARIANTS[s.variant] : null;
    var d = v ? v.d : null;

    // visibility: phase x weather x variant. Floor 0.30 so nothing goes blind.
    var vis = num(PHASE_VIS[s.phase], 1);
    if (s.key === 'fog') vis *= 0.55;
    else if (s.key === 'storm') vis *= 0.62;
    else if (s.key === 'rain') vis *= 0.86;
    if (d) vis *= d.vis;
    if (s.combatNight) vis *= 0.90;               // a raid night on top of the wall clock
    vis = clamp(vis, 0.30, 1);

    // movement: storms shove you around, rain slicks the block.
    var mv = 1;
    if (s.key === 'storm') mv = 0.85;
    else if (s.key === 'rain') mv = 0.94;
    else if (s.key === 'fog') mv = 0.97;
    if (d) mv *= d.move;
    mv = clamp(mv, 0.60, 1.10);

    return {
      key: s.key, variant: s.variant, phase: s.phase,
      visibility: vis,                            // 0.30..1 -- draw distance / sight
      sightRange: vis,                            // alias for AI sight consumers
      moveMult: mv,                               // 0.60..1.10 -- walk speed
      cropGrowMult: b.farmMult * (d ? d.farm : 1),// >1 = grows FASTER in rain
      farmMult:     b.farmMult * (d ? d.farm : 1),
      raidMult:     b.raidMult * (d ? d.raid : 1),
      encounterMult: b.encounterMult * (d ? d.enc : 1)
    };
  }

  // single read, mirroring seasons.js weatherMod(domain) so a consumer can swap
  // one call for the other. Unknown domain -> 1 (no-op, parity-safe).
  function mod(domain, zoneId, now) {
    var m = mods(zoneId, now);
    if (domain === 'farm' || domain === 'crop') return m.cropGrowMult;
    if (domain === 'raid') return m.raidMult;
    if (domain === 'encounter') return m.encounterMult;
    if (domain === 'move' || domain === 'speed') return m.moveMult;
    if (domain === 'visibility' || domain === 'sight') return m.visibility;
    return 1;
  }

  // fog DENSITY, 0..1. The 2D path scales bank alpha by it; the future 3D path
  // feeds it straight into THREE.FogExp2.density. One number, both pipelines.
  function fogDensity(zoneId, now) {
    var s = state(zoneId, now);
    var f = s.fogAmt;
    if (s.phase === 'night') f = Math.min(1, f + 0.10);
    if (s.variant === 'dust') f = Math.min(1, f + 0.35);
    return clamp(f, 0, 1);
  }
  // wind vector, normalised. Drives the 2D streak slant today; a vertex shader
  // reads the SAME vector later so cloth and rain never disagree.
  function windVector(zoneId, now) {
    var s = state(zoneId, now);
    return { x: s.wind, y: 1, strength: s.wind };
  }
  // divergence readout: what seasons.js thinks vs what economy.js thinks.
  function reconcile(now) {
    now = (now == null) ? Date.now() : now;
    var city = null, garden = null;
    try { if (global.AKSeasons && global.AKSeasons.getWeather) city = global.AKSeasons.getWeather(now); } catch (_e) {}
    try { if (global.AK_ECON && global.AK_ECON.gardenWeather) garden = global.AK_ECON.gardenWeather(); } catch (_e) {}
    var ck = (city && city.key) || fallbackKey(now);
    var gk = (garden && garden.key) || null;
    return { city: ck, garden: gk, agree: (gk == null) ? null : (gk === ck), rendering: ck };
  }

  // ==========================================================================
  // AK-WX 2026-07-18: CANVAS2D RENDER. Pooled, capped, batched.
  //
  // COST MODEL (this is the whole cheap-phone argument):
  //   rain  -> 3 beginPath + <=CAP moveTo/lineTo pairs + 3 stroke   (O(layers))
  //   fog   -> N drawImage of ONE cached 128x64 sprite               (N<=6)
  //   flash -> 1 fillRect, storm only, ~1 per 8-14s
  // Particles live in pre-allocated pools seeded once, so a steady-state frame
  // allocates ZERO objects. Stroke calls do not scale with particle count --
  // that is why 140 streaks is affordable on a phone.
  // ==========================================================================

  var QUALITY = {
    low:  { rain: 0.45, fogBanks: 3, layers: 3 },
    med:  { rain: 0.70, fogBanks: 4, layers: 3 },
    high: { rain: 1.00, fogBanks: 6, layers: 3 }
  };
  // per-layer counts at quality=high. Sum = 100 streaks (34+40+26).
  // MEASURED: storm draws the SAME 100 streaks as rain, not more -- a storm is
  // sold with velocity (speed x1.45), longer streaks, lightning and thicker fog
  // rather than extra particles, because `take` is clamped by pool length. That
  // is deliberate: storm is the worst case for a cheap phone, so it must not
  // also be the frame that allocates the most work.
  //   high 100 streaks | med 70 (0.70x) | low 45 (0.45x)
  var LAYERS = [
    { n: 34, speed: 620,  len: 15, w: 0.9, a: 0.16, par: 0.35 },
    { n: 40, speed: 900,  len: 24, w: 1.2, a: 0.24, par: 0.62 },
    { n: 26, speed: 1250, len: 34, w: 1.7, a: 0.32, par: 1.00 }
  ];
  var RAIN_HARD_CAP = 160;                        // belt-and-braces ceiling; pools top out at 100
  var FOG_HARD_CAP = 6;

  var R = {
    q: 'high', W: 0, H: 0, seeded: false,
    pools: [], fog: [], sprite: null, spriteFail: false,
    flash: 0, flashNext: 0, live: { rain: 0, fog: 0, strokes: 0, draws: 0 }
  };

  function pickQuality() {
    try {
      var w = global.innerWidth || 0, h = global.innerHeight || 0;
      var dpr = global.devicePixelRatio || 1;
      var px = w * h * dpr * dpr;
      if (!px) return 'med';
      if (px > 3200000) return 'med';             // big/retina phone -- pull back
      if (w < 380) return 'low';
      return 'high';
    } catch (_e) { return 'med'; }
  }

  // seed pools ONCE per viewport size. Math.random here is DECORATION ONLY --
  // no modifier and no gameplay value ever reads a particle position.
  function seed(W, H) {
    R.W = W; R.H = H; R.pools = []; R.fog = [];
    var qf = QUALITY[R.q] || QUALITY.med;
    var i, j;
    for (i = 0; i < LAYERS.length; i++) {
      var L = LAYERS[i];
      var n = Math.max(1, Math.round(L.n * qf.rain));
      var arr = new Array(n);
      for (j = 0; j < n; j++) arr[j] = { x: Math.random() * W, y: Math.random() * H, s: 0.85 + Math.random() * 0.3 };
      R.pools.push(arr);
    }
    var banks = Math.min(FOG_HARD_CAP, qf.fogBanks);
    for (i = 0; i < banks; i++) {
      R.fog.push({ x: Math.random() * W, y: H * (0.30 + Math.random() * 0.55), r: 90 + Math.random() * 130, v: 6 + Math.random() * 16, a: 0.5 + Math.random() * 0.5 });
    }
    R.seeded = true;
  }

  // one cached soft blob, blitted per bank. Guarded: no document -> flat ellipse.
  function fogSprite() {
    if (R.sprite || R.spriteFail) return R.sprite;
    try {
      var c = global.document.createElement('canvas');
      c.width = 128; c.height = 64;
      var g2 = c.getContext('2d');
      var gr = g2.createRadialGradient(64, 32, 4, 64, 32, 62);
      gr.addColorStop(0, 'rgba(255,255,255,0.42)');
      gr.addColorStop(0.55, 'rgba(255,255,255,0.16)');
      gr.addColorStop(1, 'rgba(255,255,255,0)');
      g2.fillStyle = gr; g2.fillRect(0, 0, 128, 64);
      R.sprite = c;
    } catch (_e) { R.spriteFail = true; R.sprite = null; }
    return R.sprite;
  }

  function streakColor(s) {
    if (s.variant && VARIANTS[s.variant]) return VARIANTS[s.variant].streak;
    return PHASE_TINT[s.phase] || PHASE_TINT.day;
  }

  function draw(ctx, dt) {
    var w = ctx && ctx.world; if (!w) return;
    var g = w.g; if (!g) return;
    var W = w.W | 0, H = w.H | 0; if (W <= 0 || H <= 0) return;

    var s = state(ctx.zoneId, Date.now());
    var dens = fogDensity(ctx.zoneId, Date.now());
    var rainAmt = s.rain;
    if (rainAmt <= 0 && dens <= 0.02) { R.live.rain = 0; R.live.fog = 0; R.live.strokes = 0; R.live.draws = 0; return; }

    if (!R.seeded || R.W !== W || R.H !== H) seed(W, H);

    var cam = w.cam || { x: 0, y: 0 };
    var strokes = 0, draws = 0, rainN = 0, fogN = 0;
    var i, j;

    g.save();

    // ---- fog banks: parallax drift, ONE cached sprite blitted per bank -------
    if (dens > 0.02) {
      var sp = fogSprite();
      var vTint = (s.variant && VARIANTS[s.variant]) ? VARIANTS[s.variant].fogTint : null;
      g.globalAlpha = 1;
      for (i = 0; i < R.fog.length; i++) {
        var b = R.fog[i];
        b.x += b.v * dt;
        if (b.x - b.r > W) b.x = -b.r;
        var px = b.x - cam.x * 0.12;              // slow parallax -- fog sits far
        if (px + b.r < 0) px += W + b.r * 2;
        var al = clamp(0.30 * dens * b.a, 0, 0.55);
        if (sp) {
          g.globalAlpha = al;
          g.drawImage(sp, px - b.r, b.y - b.r * 0.5, b.r * 2, b.r);
          draws++;
        } else {
          g.globalAlpha = al * 0.7;
          g.fillStyle = vTint ? ('rgb(' + vTint[0] + ',' + vTint[1] + ',' + vTint[2] + ')') : '#c9d6e8';
          g.fillRect(px - b.r, b.y - b.r * 0.5, b.r * 2, b.r);
          draws++;
        }
        fogN++;
      }
      // one tint pass for a district variant, instead of recolouring the sprite
      if (vTint && sp) {
        g.globalAlpha = clamp(0.10 * dens, 0, 0.18);
        g.fillStyle = 'rgb(' + vTint[0] + ',' + vTint[1] + ',' + vTint[2] + ')';
        g.fillRect(0, 0, W, H);
        draws++;
      }
      g.globalAlpha = 1;
    }

    // ---- rain: 3 parallax layers, ONE batched path + ONE stroke per layer ----
    if (rainAmt > 0) {
      var col = streakColor(s);
      var slant = s.wind;
      var budget = RAIN_HARD_CAP;
      for (i = 0; i < R.pools.length && i < LAYERS.length; i++) {
        var L = LAYERS[i], pool = R.pools[i];
        var take = Math.min(pool.length, Math.max(0, budget));
        take = Math.min(take, Math.round(pool.length * clamp(rainAmt, 0, 1.6)));
        if (take <= 0) continue;
        budget -= take;
        var len = L.len * (0.8 + rainAmt * 0.35);
        var vy = L.speed * rainAmt;
        var vx = vy * slant * 0.45;
        var ox = -cam.x * L.par * 0.05;            // parallax: near layers slide more

        g.beginPath();
        for (j = 0; j < take; j++) {
          var p = pool[j];
          p.y += vy * p.s * dt;
          p.x += vx * p.s * dt;
          if (p.y > H) { p.y -= H + len; p.x = Math.random() * W; }
          if (p.x > W) p.x -= W; else if (p.x < 0) p.x += W;
          var sx = p.x + ox;
          if (sx > W) sx -= W; else if (sx < 0) sx += W;
          g.moveTo(sx, p.y);
          g.lineTo(sx - len * slant * 0.45, p.y + len);
          rainN++;
        }
        g.strokeStyle = col + (L.a * clamp(rainAmt, 0.4, 1.3)).toFixed(3) + ')';
        g.lineWidth = L.w;
        g.stroke();
        strokes++;
      }
    }

    // ---- lightning: storm only. 1 fillRect while the flash decays. -----------
    if (s.lightning) {
      var tn = Date.now();
      if (R.flashNext === 0) R.flashNext = tn + 8000 + Math.random() * 6000;
      if (tn >= R.flashNext) { R.flash = 1; R.flashNext = tn + 8000 + Math.random() * 6000; }
      if (R.flash > 0.001) {
        R.flash -= dt * 3.2;
        if (R.flash < 0) R.flash = 0;
        g.globalAlpha = clamp(R.flash * 0.34, 0, 0.34);
        g.fillStyle = '#e8f0ff';
        g.fillRect(0, 0, W, H);
        g.globalAlpha = 1;
        draws++;
      }
    }

    g.restore();
    R.live.rain = rainN; R.live.fog = fogN; R.live.strokes = strokes; R.live.draws = draws;
  }

  // live profiling readout -- real counts from the last drawn frame, plus caps.
  function budget() {
    var pooled = 0;
    for (var i = 0; i < R.pools.length; i++) pooled += R.pools[i].length;
    return {
      quality: R.q, pooledStreaks: pooled, fogBanks: R.fog.length,
      caps: { rain: RAIN_HARD_CAP, fog: FOG_HARD_CAP, layers: LAYERS.length },
      lastFrame: { streaks: R.live.rain, fogBanks: R.live.fog, strokeCalls: R.live.strokes, drawCalls: R.live.draws }
    };
  }

  // ==========================================================================
  // PUBLIC SURFACE -- always exported (pure, no DOM, no engine dependency).
  // ==========================================================================
  global.AK_WEATHER = {
    KEYS: ['sun', 'rain', 'fog', 'storm'],
    VARIANTS: ['acid', 'dust'],
    get: function (zoneId, now) { return resolve(zoneId, now); },   // uncached snapshot
    state: function (zoneId, now) { return state(zoneId, now); },   // cached (~20s)
    mods: mods,
    mod: mod,
    fogDensity: fogDensity,
    windVector: windVector,
    reconcile: reconcile,
    isNight: function (now) { return ptPhase(now) === 'night'; },
    phase: ptPhase,
    combatNight: combatNight,
    budget: budget,
    setQuality: function (q) { if (QUALITY[q]) { R.q = q; R.seeded = false; } return R.q; },
    // test seam: draw against any 2d-like context without the hub loop.
    _draw: draw
  };

  // ---- the live AK_SYSTEMS module (hub-only; battler / node harness no-op) ---
  if (!global.AK_SYSTEMS) return;
  var _acc = 0;
  global.AK_SYSTEMS.register({
    id: 'weather',

    init: function (ctx) {
      R.q = pickQuality();
      try { state(ctx && ctx.zoneId, Date.now()); } catch (_e) {}
    },

    // state is cheap and cached; this only forces a refresh every ~20s so a PT
    // phase flip or a PT-midnight weather roll lands without a reload.
    onTick: function (dt, ctx) {
      _acc += dt;
      if (_acc < 20) return;
      _acc = 0;
      try { _st.v = null; state(ctx && ctx.zoneId, Date.now()); } catch (_e) {}
    },

    // draws AFTER daynight.js's grade wash (include order below it in index.html)
    // so precipitation reads on top of the time-of-day tint rather than under it.
    onDrawWorld: function (ctx) { draw(ctx, 1 / 60); }
  });
})(typeof window !== 'undefined' ? window : globalThis);
