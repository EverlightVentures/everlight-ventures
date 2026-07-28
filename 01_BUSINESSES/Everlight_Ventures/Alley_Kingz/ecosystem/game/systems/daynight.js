/* game/systems/daynight.js -- AK_SYSTEMS module: P7 "DAY / NIGHT".
   ------------------------------------------------------------------------
   A deterministic day/night cycle anchored to LOCAL PT (America/Los_Angeles).
   Mirrors the seasons.js onDrawWorld soft-light grade-wash pattern: a cheap,
   per-frame screen-space color grade that re-themes the whole hub by the time
   of day -- on TOP of the active season wash, never instead of it.

   WHAT THIS WAVE OWNS:
   - getPhase() -> 'dawn' | 'day' | 'dusk' | 'night', driven purely by PT time.
   - A smooth per-phase light/color GRADE over the hub (keyframed across 24h so
     the sky drifts gold->day->dusk->night and back -- it "feels" alive).
   - Phase-based HOOKS for the integration pass (no profile writes here):
       * NIGHT MARKET appointment window -- the Fence opens off-the-books deals
         at night (21:00 PT) and closes at first light (06:00 PT). Soft-currency
         discount only. An appointment-mechanic countdown is exposed.
       * DAWN BONUS -- first light (06:00-08:30 PT) flags a soft reward boost.
       * priceMult() -- a SOFT-CURRENCY Fence multiplier by phase (night cheaper).

   HARD-LAW COMPLIANCE:
   - PARITY: every phase hook moves SOFT currency / bones / TIME only. Night
     market = soft-currency discount, dawn bonus = soft reward boost. NEVER gems,
     never raw power, never pay-to-win. Gems stay cosmetic-only elsewhere.
   - DETERMINISTIC-BY-TIME: phase + grade are a pure function of the PT clock.
     ZERO Math.random -- every client in the world sees the same phase at the
     same instant (shared PT world-clock), so nothing breaks parity.
   - PROFILE-SAFE: this module is READ-ONLY on the profile -- it writes NOTHING.
     No AK_ECON.mutateProfile call, so a never-played profile stays byte-identical
     and the falsy-default / zero-state law is satisfied trivially.
   - engine.js stays FROZEN -- this only composites over the live world render.
   - 60fps CHEAP-ANDROID: the PT clock + grade are recomputed at most every ~30s
     in onTick (Intl formatter cached); onDrawWorld just reads the cache and
     paints 1-2 fillRects. Vignette gradients are cached by phase+size. No
     per-frame heavy work, no shadowBlur in the wash path.
   - SENSORY: gold cyberpunk palette -- warm gold dawn, bright day, magenta-gold
     dusk, deep neon-blue night with a soft vignette so "it's night" lands.
   - CANON ONLY: flavor names the 9 districts, the Fence, the Watch, the Old Pack,
     the Stray rank, Zoomie Syndicate + Boneguard Crew. No generic / invented art.
   - HEADLESS-SAFE: the live module only registers when AK_SYSTEMS exists, but the
     pure window.AK_DAYNIGHT surface is exposed everywhere (no DOM, no engine dep).
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';

  // ---- LOCAL PT clock (deterministic shared world-clock) --------------------
  // All players read the SAME Pacific-time hour regardless of device timezone,
  // so the phase is identical everywhere (parity-safe). DST handled by Intl;
  // fixed UTC-8 (PST) fallback when Intl/timeZone is unavailable.
  function ptParts(now) {
    now = (now == null) ? Date.now() : now;
    try {
      var f = ptParts._f || (ptParts._f = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/Los_Angeles', hour12: false, hour: '2-digit', minute: '2-digit'
      }));
      var parts = f.formatToParts(new Date(now)), h = 0, m = 0;
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].type === 'hour') h = parseInt(parts[i].value, 10) % 24;
        else if (parts[i].type === 'minute') m = parseInt(parts[i].value, 10);
      }
      return { h: h, m: m };
    } catch (_e) {
      var d = new Date(now - 8 * 3600000);   // PST (UTC-8) fallback
      return { h: d.getUTCHours(), m: d.getUTCMinutes() };
    }
  }
  function fhOf(now) { var p = ptParts(now); return p.h + p.m / 60; }   // fractional PT hour [0,24)

  // ---- phase bands (PT hours) -----------------------------------------------
  //   dawn  06:00 - 08:30   day   08:30 - 17:30
  //   dusk  17:30 - 21:00   night 21:00 - 06:00 (wraps)
  function phaseOf(fh) {
    if (fh >= 6 && fh < 8.5)    return 'dawn';
    if (fh >= 8.5 && fh < 17.5) return 'day';
    if (fh >= 17.5 && fh < 21)  return 'dusk';
    return 'night';
  }
  var PHASE_START = { dawn: 6, day: 8.5, dusk: 17.5, night: 21 };
  var BOUNDS = [6, 8.5, 17.5, 21];

  // ---- 24h GRADE keyframes (gold cyberpunk; soft-light wash + alpha) ---------
  // wash = [r,g,b] graded over the world; a = soft-light alpha; accent = the
  // gold-substitute tint for that hour. Day sits near-zero so daylight reads
  // bright; night sits deep neon-blue. Lerped by fractional hour -> a living sky.
  var KEYS = [
    { h: 0.0,  wash: [8, 12, 34],  a: 0.50, accent: '#7aa2ff' },
    { h: 5.0,  wash: [10, 14, 38], a: 0.48, accent: '#7aa2ff' },
    { h: 6.0,  wash: [70, 44, 30], a: 0.34, accent: '#ffb066' },
    { h: 7.5,  wash: [82, 48, 34], a: 0.30, accent: '#ffcf8a' },
    { h: 8.5,  wash: [60, 52, 40], a: 0.12, accent: '#ffe7b0' },
    { h: 12.0, wash: [56, 52, 44], a: 0.08, accent: '#fff0c8' },
    { h: 16.5, wash: [62, 50, 36], a: 0.12, accent: '#ffdf9a' },
    { h: 18.0, wash: [78, 40, 34], a: 0.32, accent: '#ff8a5a' },
    { h: 19.5, wash: [62, 26, 44], a: 0.40, accent: '#ff6a8a' },
    { h: 21.0, wash: [18, 18, 48], a: 0.46, accent: '#8aa6ff' },
    { h: 24.0, wash: [8, 12, 34],  a: 0.50, accent: '#7aa2ff' }
  ];
  function lerp(a, b, t) { return a + (b - a) * t; }
  function hex2rgb(hx) { hx = hx.replace('#', ''); return [parseInt(hx.substr(0, 2), 16), parseInt(hx.substr(2, 2), 16), parseInt(hx.substr(4, 2), 16)]; }
  function pad2(n) { var s = (n & 255).toString(16); return s.length < 2 ? '0' + s : s; }
  function rgb2hex(r, g, b) { return '#' + pad2(r) + pad2(g) + pad2(b); }
  function computeGrade(fh) {
    if (fh < 0) fh = 0; if (fh >= 24) fh = 23.999;
    var i = 0;
    for (; i < KEYS.length - 1; i++) { if (fh >= KEYS[i].h && fh < KEYS[i + 1].h) break; }
    if (i >= KEYS.length - 1) i = KEYS.length - 2;       // clamp guard
    var k0 = KEYS[i], k1 = KEYS[i + 1];
    var t = (k1.h === k0.h) ? 0 : (fh - k0.h) / (k1.h - k0.h);
    var c0 = hex2rgb(k0.accent), c1 = hex2rgb(k1.accent);
    return {
      wash: [Math.round(lerp(k0.wash[0], k1.wash[0], t)), Math.round(lerp(k0.wash[1], k1.wash[1], t)), Math.round(lerp(k0.wash[2], k1.wash[2], t))],
      alpha: lerp(k0.a, k1.a, t),
      accent: rgb2hex(Math.round(lerp(c0[0], c1[0], t)), Math.round(lerp(c0[1], c1[1], t)), Math.round(lerp(c0[2], c1[2], t)))
    };
  }

  // ---- per-phase metadata (canon-laced; soft-currency hooks only) -----------
  var PHASE_META = {
    dawn:  { label: 'FIRST LIGHT', glyph: '🌅', priceMult: 0.95, dawnBonus: true,  nightMarket: false,
             flavor: "Dawn breaks over the 9 districts. The Watch trades off shift -- first light favors the early Stray. Dawn bonus is live." },
    day:   { label: 'DAYLIGHT',    glyph: '☀️',  priceMult: 1.00, dawnBonus: false, nightMarket: false,
             flavor: "Daylight on the blocks. The Fence runs straight and the Watch stands easy across all 9 districts." },
    dusk:  { label: 'DUSK',        glyph: '🌆', priceMult: 1.00, dawnBonus: false, nightMarket: false,
             flavor: "Dusk bleeds gold. The Old Pack stirs and the deals sharpen as the light dies." },
    night: { label: 'NIGHT MARKET', glyph: '🌃', priceMult: 0.85, dawnBonus: false, nightMarket: true,
             flavor: "Night. The Fence opens the night market off the books -- Zoomie Syndicate runs the strip, Boneguard works the docks, the Watch is thin. Soft-currency deals only; closes at first light." }
  };

  // ---- appointment helpers (night market / phase countdowns) ----------------
  function hoursUntil(fh, target) { var d = target - fh; while (d <= 0) d += 24; return d; }
  function msUntilPhaseChange(fh) {
    var best = 24;
    for (var i = 0; i < BOUNDS.length; i++) { var d = BOUNDS[i] - fh; if (d <= 0) d += 24; if (d < best) best = d; }
    return Math.round(best * 3600000);
  }
  function nightMarketInfo(fh) {
    var open = (fh >= 21 || fh < 6);
    if (open) return { open: true,  opensInMs: 0, closesInMs: Math.round(hoursUntil(fh, 6) * 3600000), opensAt: '21:00 PT', closesAt: '06:00 PT' };
    return       { open: false, opensInMs: Math.round(hoursUntil(fh, 21) * 3600000), closesInMs: 0, opensAt: '21:00 PT', closesAt: '06:00 PT' };
  }

  // ---- full snapshot for the integration pass -------------------------------
  function buildState(now) {
    var p = ptParts(now), fh = p.h + p.m / 60;
    var phase = phaseOf(fh), meta = PHASE_META[phase], gr = computeGrade(fh);
    return {
      phase: phase, label: meta.label, glyph: meta.glyph,
      ptHour: p.h, ptMinute: p.m,
      accent: gr.accent, wash: gr.wash.slice(), alpha: gr.alpha,
      priceMult: meta.priceMult, dawnBonus: meta.dawnBonus,
      nightMarket: nightMarketInfo(fh),
      nextChangeInMs: msUntilPhaseChange(fh),
      flavor: meta.flavor
    };
  }

  // ---- cached live state (refreshed every ~30s in onTick; read in onDrawWorld)
  var STATE = { fh: -1, phase: 'day', grade: null };
  function refresh(now) {
    var fh = fhOf(now), phase = phaseOf(fh), grade = computeGrade(fh);
    var changed = (phase !== STATE.phase) || (STATE.fh < 0);
    STATE.fh = fh; STATE.phase = phase; STATE.grade = grade;
    return changed;
  }

  // ---- phase-change subscribers (integration pass wires events here) --------
  var _subs = [];
  function notify() { var s = buildState(Date.now()); for (var i = 0; i < _subs.length; i++) { try { _subs[i](STATE.phase, s); } catch (_e) {} } }

  // ---- the per-frame GRADE wash (cheap: cached gradients, 1-2 fillRects) -----
  var _grad = { key: '', val: null };
  function vignette(g, W, H, phase) {
    var key = phase + ':' + W + ':' + H;
    if (_grad.key !== key) {
      var vg;
      if (phase === 'night') {
        vg = g.createLinearGradient(0, 0, 0, H);
        vg.addColorStop(0, 'rgba(4,6,20,0.30)'); vg.addColorStop(0.5, 'rgba(4,6,20,0.10)'); vg.addColorStop(1, 'rgba(4,6,20,0.34)');
      } else {
        var warm = (phase === 'dawn') ? '255,176,102' : '255,120,90';
        vg = g.createLinearGradient(0, 0, 0, H);
        vg.addColorStop(0, 'rgba(' + warm + ',0.0)'); vg.addColorStop(0.62, 'rgba(' + warm + ',0.06)'); vg.addColorStop(1, 'rgba(' + warm + ',0.16)');
      }
      _grad.key = key; _grad.val = vg;
    }
    return _grad.val;
  }

  // ==========================================================================
  // PUBLIC SURFACE -- exposed ALWAYS (pure, no DOM, no engine dependency).
  // The integration pass reads getPhase() + getGrade() + now() and wires the
  // night-market window / dawn bonus / price multiplier into the Fence + check-in.
  // ==========================================================================
  global.AK_DAYNIGHT = {
    PHASES: ['dawn', 'day', 'dusk', 'night'],
    // required: phase by the LOCAL PT clock
    getPhase: function (now) { if (now != null) return phaseOf(fhOf(now)); if (STATE.fh < 0) refresh(Date.now()); return STATE.phase; },
    // required: the live color grade { wash:[r,g,b], alpha, accent }
    getGrade: function (now) {
      if (now != null) return computeGrade(fhOf(now));
      if (!STATE.grade) refresh(Date.now());
      var g = STATE.grade; return { wash: g.wash.slice(), alpha: g.alpha, accent: g.accent };
    },
    // full snapshot (phase, label, glyph, PT clock, grade, hooks, countdowns)
    now: function (n) { return buildState(n == null ? Date.now() : n); },
    // appointment mechanics -- the night market window (soft-currency only)
    isNightMarketOpen: function (n) { var fh = fhOf(n == null ? Date.now() : n); return (fh >= 21 || fh < 6); },
    nightMarket: function (n) { return nightMarketInfo(fhOf(n == null ? Date.now() : n)); },
    // SOFT-CURRENCY Fence multiplier by phase (parity-safe -- never gems/power)
    priceMult: function (n) { return PHASE_META[phaseOf(fhOf(n == null ? Date.now() : n))].priceMult; },
    dawnBonus: function (n) { return PHASE_META[phaseOf(fhOf(n == null ? Date.now() : n))].dawnBonus === true; },
    // ms until a given phase next begins (0 if already in it) -- appointment timer
    msUntilPhase: function (phase, n) {
      var s = PHASE_START[phase]; if (s == null) return null;
      var fh = fhOf(n == null ? Date.now() : n);
      return (phaseOf(fh) === phase) ? 0 : Math.round(hoursUntil(fh, s) * 3600000);
    },
    msUntilPhaseChange: function (n) { return msUntilPhaseChange(fhOf(n == null ? Date.now() : n)); },
    // subscribe to phase transitions (called from onTick); returns an unsubscribe fn
    subscribe: function (fn) { if (typeof fn === 'function') { _subs.push(fn); } return function () { var i = _subs.indexOf(fn); if (i >= 0) _subs.splice(i, 1); }; }
  };

  // ---- the live AK_SYSTEMS module (hub-only; node harness / battler no-op) --
  if (!global.AK_SYSTEMS) return;
  var _acc = 0;
  global.AK_SYSTEMS.register({
    id: 'daynight',

    init: function (_ctx) { refresh(Date.now()); },

    onTick: function (dt, _ctx) {
      _acc += dt;
      if (_acc < 30) return;                 // recompute the PT grade at most every ~30s (cheap)
      _acc = 0;
      if (refresh(Date.now())) { try { notify(); } catch (_e) {} }   // fire subscribers on a phase flip
    },

    // per-frame time-of-day GRADE over the live world render (on TOP of seasons):
    // (1) a soft-light wash keyed to the PT hour, (2) a cached vignette/horizon
    // glow so dawn/dusk/night read instantly. Reads the cache only -- no clock work.
    onDrawWorld: function (ctx) {
      var gr = STATE.grade; if (!gr) { refresh(Date.now()); gr = STATE.grade; }
      if (!gr) return;
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      g.save();
      // (1) soft-light color grade -- keeps the district + season art readable
      try { g.globalCompositeOperation = 'soft-light'; } catch (_e) {}
      g.globalAlpha = gr.alpha;
      g.fillStyle = 'rgb(' + gr.wash[0] + ',' + gr.wash[1] + ',' + gr.wash[2] + ')';
      g.fillRect(0, 0, W, H);
      g.globalCompositeOperation = 'source-over';
      // (2) the "it is night / golden hour" read -- one cached gradient, day = none
      if (STATE.phase !== 'day') {
        g.globalAlpha = 1;
        g.fillStyle = vignette(g, W, H, STATE.phase);
        g.fillRect(0, 0, W, H);
      }
      g.globalAlpha = 1;
      g.restore();
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
