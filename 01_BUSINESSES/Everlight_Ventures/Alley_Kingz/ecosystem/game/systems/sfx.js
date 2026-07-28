/* ALLEY KINGZ -- systems/sfx.js  (AK-SFX 2026-07-12)
   Procedural WebAudio SFX engine. STANDALONE MODULE -- not wired into any
   fight/game file yet. A later pass owns the call sites in story.js, raid.js,
   modes.js, defense.js, raidscene.js and social.js (and the <script> tag in
   game.html / index.html); this file only builds the instrument and the API.

   HEADLINE JOB: make BOSS FIGHTS feel like adrenaline-pumping events. Also
   ships a small set of general-purpose UI/game SFX so the rest of the game
   has somewhere to plug in later without a second engine.

   ZERO ASSETS: every sound is synthesized live -- OscillatorNode sweeps,
   a shared white-noise AudioBuffer run through BiquadFilters, and GainNode
   envelopes. No .mp3/.wav/.ogg, no fetch, no <audio>, no credited/licensed
   sample, nothing to ship or attribute. Same "no assets" discipline engine.js
   already uses for its per-card voice system (see engine.js AK-AUDIO block)
   and districtmusic.js uses for ambient beds -- this module is a THIRD,
   independent instrument living under its own namespace (window.AK_SFX) and
   its own mute key (localStorage 'ak_sfx_muted'), separate from engine.js's
   'ak_muted' card-voice system on purpose: this lane ships before the wiring
   pass decides how (or whether) to unify the two mute toggles in the UI.

   PUBLIC API -- window.AK_SFX
     init()                 -- manually force the gesture-unlock (e.g. from a
                                "tap to start" screen). Idempotent, safe to
                                call anytime, safe to call repeatedly.
     play(name, opts)        -- fire a one-shot sound. opts: { volume: 0..2 }.
                                Returns true if a sound was actually triggered.
     loop(name, opts)        -- start a LOOPING sound (currently: 'heartbeat').
                                opts: { interval: ms, volume: 0..2 }. Idempotent
                                (calling twice while already looping is a no-op
                                that still returns true).
     stopLoop(name)          -- stop one active loop by name.
     stopAllLoops()          -- stop every active loop.
     setMuted(bool)          -- mute/unmute; persists to localStorage.
     muted()                 -- current mute state (bool).
     setVolume(0..1)         -- master volume multiplier (independent of mute).
     volume()                -- current master volume (0..1).
     isUnlocked()            -- has the first-gesture AudioContext unlock fired?
     list()                  -- array of every playable sound name (incl. aliases).

   GESTURE UNLOCK (mobile autoplay policy): the AudioContext is NEVER created
   before the user has interacted. A one-time pointerdown/touchstart/keydown
   listener (capture, {once:true}) is armed at load time; the first of any of
   those fires attemptUnlock(), which creates the context and resumes it.
   AK_SFX.init() does the exact same thing on demand (e.g. wire it to a splash
   tap). Any play()/loop() call before that first gesture is a safe no-op
   (loop() requests are remembered and started automatically once unlocked;
   one-shot play() calls are simply dropped -- nothing was audible yet anyway).

   MUTE: localStorage key 'ak_sfx_muted' ('1'/'0'), read once at load and kept
   in sync on every setMuted(). Mute is a pure master-gain-to-0 -- it does NOT
   tear down active loops (same convention as engine.js's akSetMuted), so
   unmuting mid-heartbeat resumes exactly where the loop already was.

   VOICE CAP + THROTTLE: a hard cap (TRANSIENT_CAP) on concurrent one-shot
   voices so a flurry of hits can never stack into clipping, PLUS a per-sound
   minimum-interval throttle (THROTTLE_MS) so e.g. 'impact' can't machine-gun
   faster than is audible as anything but noise. Compound multi-stage sounds
   (boss_enter, phase, victory...) route every layer through the SAME cap.

   HEADLESS SAFETY (hard guard, checked first, before anything else runs):
   if there is no AudioContext constructor available at all (Node harness,
   or an ancient browser), the ENTIRE module short-circuits to a no-op API
   with the exact same method names -- every call returns a safe falsy value
   and NOTHING ever throws. Every real code path below that guard is also
   wrapped in try/catch per call site, so a single bad browser quirk can
   never break the game loop that calls into this file.
*/
(function (root) {
  "use strict";

  // --------------------------------------------------------------------
  // 0. constants that must exist regardless of which branch runs below
  // --------------------------------------------------------------------
  var SOUND_LIST = [
    'boss_enter', 'boss_roar',
    'impact', 'hit', 'crit', 'heavy',
    'phase', 'enrage',
    'heartbeat',
    'charge', 'telegraph',
    'victory', 'crown', 'defeat',
    'tap', 'coin', 'reward', 'error', 'whoosh'
  ];

  function exportApi(api) {
    try { if (root) root.AK_SFX = api; } catch (_e) {}
    try { if (typeof module !== 'undefined' && module.exports) module.exports = api; } catch (_e) {}
    return api;
  }

  // --------------------------------------------------------------------
  // 1. HARD GUARD -- no AudioContext constructor anywhere = fully no-op.
  //    Nothing past this block ever runs in that environment.
  // --------------------------------------------------------------------
  var AudioCtor = null;
  try { AudioCtor = (root && (root.AudioContext || root.webkitAudioContext)) || null; } catch (_e) { AudioCtor = null; }

  if (!AudioCtor) {
    var FALSE_FN = function () { return false; };
    exportApi({
      init: FALSE_FN,
      play: FALSE_FN,
      loop: FALSE_FN,
      stopLoop: function () {},
      stopAllLoops: function () {},
      setMuted: function () {},
      muted: function () { return true; },   // no audio can ever play here -- "muted" is the honest read
      setVolume: function () {},
      volume: function () { return 0; },
      isUnlocked: function () { return false; },
      list: function () { return SOUND_LIST.slice(); }
    });
    return;
  }

  // --------------------------------------------------------------------
  // 2. state
  // --------------------------------------------------------------------
  var MUTE_KEY = 'ak_sfx_muted';

  var _ctx = null;
  var _master = null;       // gain -> compressor -> destination
  var _compressor = null;
  var _muted = false;
  var _volume = 1.0;        // 0..1, independent of mute
  var _unlocked = false;
  var _gestureBound = false;
  var _pendingLoops = {};   // name -> opts, requested before the first gesture
  var _activeVoices = 0;    // concurrent one-shot transient voice count
  var _lastPlayedAt = {};   // name -> ctx.currentTime of last trigger (throttle)
  var _loops = {};          // name -> { stop: fn } for currently-running loops
  var _noiseBuf = null;     // shared white-noise AudioBuffer, built once

  function readMutedPref() {
    try {
      if (typeof localStorage === 'undefined') return false;
      return localStorage.getItem(MUTE_KEY) === '1';
    } catch (_e) { return false; }
  }
  function writeMutedPref(v) {
    try { if (typeof localStorage !== 'undefined') localStorage.setItem(MUTE_KEY, v ? '1' : '0'); } catch (_e) {}
  }
  _muted = readMutedPref();

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // --------------------------------------------------------------------
  // 3. audio graph plumbing -- context is created ONLY from attemptUnlock()
  //    (first gesture, or a manual init() call). Never created eagerly.
  // --------------------------------------------------------------------
  function getCtx() {
    if (_ctx) return _ctx;
    try { _ctx = new AudioCtor(); } catch (_e) { _ctx = null; }
    return _ctx;
  }

  function applyMasterGain() {
    try { if (_master) _master.gain.value = _muted ? 0 : _volume; } catch (_e) {}
  }

  function getMaster() {
    var ctx = getCtx(); if (!ctx) return null;
    if (_master) return _master;
    try {
      var m = ctx.createGain();
      m.gain.value = _muted ? 0 : _volume;
      var out = ctx.destination;
      try {
        _compressor = ctx.createDynamicsCompressor();
        _compressor.connect(ctx.destination);
        out = _compressor;
      } catch (_e) { out = ctx.destination; }
      m.connect(out);
      _master = m;
    } catch (_e) { _master = null; }
    return _master;
  }

  function noiseBuffer(ctx) {
    if (_noiseBuf) return _noiseBuf;
    try {
      var len = Math.max(1, Math.floor(ctx.sampleRate * 2));   // 2s, looped/sliced per-use
      var buf = ctx.createBuffer(1, len, ctx.sampleRate);
      var data = buf.getChannelData(0);
      for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
      _noiseBuf = buf;
    } catch (_e) { _noiseBuf = null; }
    return _noiseBuf;
  }

  // --------------------------------------------------------------------
  // 4. voice cap + per-sound throttle
  // --------------------------------------------------------------------
  var TRANSIENT_CAP = 12;
  var THROTTLE_MS = {
    boss_enter: 1500, boss_roar: 250,
    impact: 35, hit: 35, crit: 70, heavy: 70,
    phase: 800, enrage: 800,
    charge: 300, telegraph: 300,
    victory: 2000, crown: 2000, defeat: 2000,
    tap: 30, coin: 30, reward: 150, error: 120, whoosh: 80
  };
  var THROTTLE_DEFAULT = 20;

  function voiceFree() { return _activeVoices < TRANSIENT_CAP; }
  function takeVoice(node, dur) {
    _activeVoices++;
    var done = false;
    function release() { if (!done) { done = true; _activeVoices = Math.max(0, _activeVoices - 1); } }
    try { node.onended = release; } catch (_e) {}
    try { if (typeof setTimeout !== 'undefined') setTimeout(release, Math.max(50, (dur || 0.3) * 1000 + 200)); } catch (_e) {}
  }
  function throttled(name) {
    if (!_ctx) return false;               // nothing to compare against yet
    var minGap = (THROTTLE_MS[name] != null ? THROTTLE_MS[name] : THROTTLE_DEFAULT) / 1000;
    var t = _ctx.currentTime;
    var last = _lastPlayedAt[name];
    if (last != null && (t - last) < minGap) return true;
    _lastPlayedAt[name] = t;
    return false;
  }

  function scheduleAfter(ms, fn) {
    try {
      if (typeof setTimeout === 'undefined') { fn(); return; }
      setTimeout(function () { try { fn(); } catch (_e) {} }, ms);
    } catch (_e) { try { fn(); } catch (_e2) {} }
  }

  // --------------------------------------------------------------------
  // 5. primitives -- every voice in the game is one of these two shapes.
  //    Both: voice-capped, master-routed, mute-checked, try/catch'd.
  // --------------------------------------------------------------------
  // tone(): oscillator with an optional frequency ramp + optional lowpass/
  // bandpass filter ramp, ADSR-lite gain envelope (linear attack, expo decay).
  function tone(opts) {
    var ctx = getCtx(); var m = getMaster();
    if (!ctx || !m || _muted || !voiceFree()) return false;
    opts = opts || {};
    try {
      var t0 = ctx.currentTime;
      var dur = opts.duration != null ? opts.duration : 0.2;
      var atk = opts.attack != null ? opts.attack : 0.005;
      var o = ctx.createOscillator();
      var g = ctx.createGain();
      o.type = opts.type || 'sine';
      var f0 = Math.max(20, opts.freq || 220);
      o.frequency.setValueAtTime(f0, t0);
      if (opts.freqEnd) o.frequency.exponentialRampToValueAtTime(Math.max(20, opts.freqEnd), t0 + dur);
      try { if (opts.detune && o.detune) o.detune.setValueAtTime(opts.detune, t0); } catch (_e) {}
      o.connect(g);
      var tail = g;
      if (opts.filterFreq && ctx.createBiquadFilter) {
        try {
          var fl = ctx.createBiquadFilter();
          fl.type = opts.filterType || 'lowpass';
          fl.frequency.setValueAtTime(opts.filterFreq, t0);
          if (opts.filterFreqEnd) fl.frequency.exponentialRampToValueAtTime(Math.max(20, opts.filterFreqEnd), t0 + dur);
          g.connect(fl); tail = fl;
        } catch (_e) { tail = g; }
      }
      tail.connect(m);
      var peak = clamp((opts.gain != null ? opts.gain : 0.2), 0.001, 0.9);
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.linearRampToValueAtTime(peak, t0 + atk);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur + atk);
      o.start(t0);
      o.stop(t0 + dur + atk + 0.05);
      takeVoice(o, dur + atk);
      return true;
    } catch (_e) { return false; }
  }

  // noiseHit(): shared noise buffer through a bandpass/lowpass filter ramp,
  // same gain envelope shape as tone(). Used for growls, clicks and swells.
  function noiseHit(opts) {
    var ctx = getCtx(); var m = getMaster();
    if (!ctx || !m || _muted || !voiceFree()) return false;
    var buf = noiseBuffer(ctx); if (!buf) return false;
    opts = opts || {};
    try {
      var t0 = ctx.currentTime;
      var dur = opts.duration != null ? opts.duration : 0.15;
      var atk = opts.attack != null ? opts.attack : 0.002;
      var src = ctx.createBufferSource();
      src.buffer = buf; src.loop = true;   // sliced short by start/stop below
      var g = ctx.createGain();
      src.connect(g);
      var tail = g;
      if (ctx.createBiquadFilter) {
        try {
          var fl = ctx.createBiquadFilter();
          fl.type = opts.filterType || 'lowpass';
          fl.frequency.setValueAtTime(opts.filterFreq || 1200, t0);
          if (opts.filterFreqEnd) fl.frequency.exponentialRampToValueAtTime(Math.max(40, opts.filterFreqEnd), t0 + dur);
          try { if (opts.q && fl.Q) fl.Q.value = opts.q; } catch (_e2) {}
          g.connect(fl); tail = fl;
        } catch (_e) { tail = g; }
      }
      tail.connect(m);
      var peak = clamp((opts.gain != null ? opts.gain : 0.2), 0.001, 0.9);
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.linearRampToValueAtTime(peak, t0 + atk);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur + atk);
      src.start(t0);
      src.stop(t0 + dur + atk + 0.05);
      takeVoice(src, dur + atk);
      return true;
    } catch (_e) { return false; }
  }

  // --------------------------------------------------------------------
  // 6. BOSS-FIGHT sound set (the headline job) + general hooks
  //    Every builder takes (volMul, opts) and returns true/false. Multi-
  //    stage sounds stagger their later layers via scheduleAfter -- each
  //    stage is still its own voice-capped, mute-checked primitive call.
  // --------------------------------------------------------------------
  // 'boss_enter' -- deep sub riser + distorted growl, lands on a low boom.
  // The "the boss has arrived" moment. ~1.3s total.
  function sBossEnter(vm) {
    tone({ type: 'sawtooth', freq: 200, freqEnd: 50, duration: 0.85, attack: 0.22, gain: 0.28 * vm });
    tone({ type: 'sine', freq: 60, freqEnd: 42, duration: 0.9, attack: 0.28, gain: 0.20 * vm });
    noiseHit({ filterType: 'bandpass', filterFreq: 650, filterFreqEnd: 170, q: 3.2, duration: 0.5, attack: 0.05, gain: 0.24 * vm });
    tone({ type: 'sawtooth', freq: 58, freqEnd: 44, duration: 0.5, detune: -18, gain: 0.14 * vm });
    tone({ type: 'sawtooth', freq: 58, freqEnd: 44, duration: 0.5, detune: 18, gain: 0.14 * vm });
    scheduleAfter(820, function () {
      tone({ type: 'sine', freq: 50, freqEnd: 30, duration: 0.5, attack: 0.006, gain: 0.40 * vm });
      noiseHit({ filterType: 'lowpass', filterFreq: 900, filterFreqEnd: 110, duration: 0.2, attack: 0.004, gain: 0.20 * vm });
    });
    return true;
  }
  // 'boss_roar' -- shorter growl for phase attacks. ~0.3s.
  function sBossRoar(vm) {
    noiseHit({ filterType: 'bandpass', filterFreq: 560, filterFreqEnd: 200, q: 3, duration: 0.28, attack: 0.02, gain: 0.22 * vm });
    tone({ type: 'sawtooth', freq: 70, freqEnd: 48, duration: 0.28, detune: -14, gain: 0.16 * vm });
    tone({ type: 'sawtooth', freq: 70, freqEnd: 48, duration: 0.28, detune: 14, gain: 0.16 * vm });
    return true;
  }
  // 'impact'/'hit' -- punchy transient: noise click through a fast-decay
  // lowpass + a short 60-90Hz sine thump. The core combat hit. ~70ms.
  function sImpact(vm) {
    noiseHit({ filterType: 'lowpass', filterFreq: 2400, filterFreqEnd: 220, duration: 0.05, attack: 0.001, gain: 0.20 * vm });
    tone({ type: 'sine', freq: 82, freqEnd: 52, duration: 0.07, attack: 0.002, gain: 0.24 * vm });
    return true;
  }
  // 'crit'/'heavy' -- bigger impact + a brief metallic ring (2-3 detuned
  // high partials). ~220ms.
  function sCrit(vm) {
    noiseHit({ filterType: 'lowpass', filterFreq: 2600, filterFreqEnd: 180, duration: 0.08, attack: 0.001, gain: 0.26 * vm });
    tone({ type: 'sine', freq: 70, freqEnd: 40, duration: 0.14, attack: 0.002, gain: 0.34 * vm });
    tone({ type: 'triangle', freq: 1800, duration: 0.22, attack: 0.002, gain: 0.09 * vm });
    tone({ type: 'triangle', freq: 2650, detune: 6, duration: 0.20, attack: 0.002, gain: 0.07 * vm });
    tone({ type: 'sine', freq: 3400, detune: -5, duration: 0.18, attack: 0.002, gain: 0.05 * vm });
    return true;
  }
  // 'phase'/'enrage' -- rising tension stinger (pitch-rising saw + swelling
  // noise) capped by a boom. Fire on an HP phase threshold. ~1.1s.
  function sPhase(vm) {
    tone({ type: 'sawtooth', freq: 90, freqEnd: 700, duration: 0.75, attack: 0.05, gain: 0.22 * vm });
    noiseHit({ filterType: 'bandpass', filterFreq: 400, filterFreqEnd: 2200, q: 2.2, duration: 0.75, attack: 0.05, gain: 0.16 * vm });
    scheduleAfter(760, function () {
      tone({ type: 'sine', freq: 55, freqEnd: 32, duration: 0.35, attack: 0.005, gain: 0.36 * vm });
      noiseHit({ filterType: 'lowpass', filterFreq: 1000, filterFreqEnd: 140, duration: 0.16, attack: 0.004, gain: 0.18 * vm });
    });
    return true;
  }
  // 'charge'/'telegraph' -- rising whine warning of a big incoming attack.
  // opts.duration lets the caller match the actual wind-up length.
  function sCharge(vm, opts) {
    var dur = (opts && opts.duration) || 0.85;
    tone({ type: 'sawtooth', freq: 280, freqEnd: 1250, duration: dur, attack: 0.03, gain: 0.16 * vm, filterType: 'lowpass', filterFreq: 2600, filterFreqEnd: 4200 });
    tone({ type: 'triangle', freq: 560, freqEnd: 1600, duration: dur, attack: 0.03, gain: 0.08 * vm });
    return true;
  }
  // 'victory'/'crown' -- short triumphant gold fanfare, warm major arpeggio.
  function sVictory(vm) {
    var notes = [523.25, 659.25, 784.0, 1046.5, 1318.5];   // C5 E5 G5 C6 E6
    for (var i = 0; i < notes.length; i++) {
      (function (f, idx) {
        scheduleAfter(idx * 115, function () {
          var isLast = idx === notes.length - 1;
          tone({ type: 'triangle', freq: f, freqEnd: f * 1.01, duration: 0.34, attack: 0.008, gain: (isLast ? 0.20 : 0.16) * vm });
          if (isLast) tone({ type: 'sine', freq: f * 2, duration: 0.4, attack: 0.01, gain: 0.06 * vm });
        });
      })(notes[i], i);
    }
    return true;
  }
  // 'defeat' -- descending somber tone.
  function sDefeat(vm) {
    var notes = [392.0, 329.63, 277.18, 220.0];   // G4 E4 C#4 A3, descending
    for (var i = 0; i < notes.length; i++) {
      (function (f, idx) {
        scheduleAfter(idx * 190, function () {
          tone({ type: 'sine', freq: f, freqEnd: f * 0.94, duration: 0.5, attack: 0.02, gain: 0.16 * vm });
        });
      })(notes[i], i);
    }
    return true;
  }
  // ---- light GENERAL hooks, tasteful + short ----
  function sTap(vm) { tone({ type: 'square', freq: 420, freqEnd: 300, duration: 0.04, attack: 0.002, gain: 0.10 * vm }); return true; }
  function sCoin(vm) {
    tone({ type: 'triangle', freq: 900, freqEnd: 1500, duration: 0.09, attack: 0.002, gain: 0.14 * vm });
    scheduleAfter(45, function () { tone({ type: 'triangle', freq: 1300, freqEnd: 1900, duration: 0.07, attack: 0.002, gain: 0.10 * vm }); });
    return true;
  }
  function sReward(vm) {
    var notes = [784.0, 1046.5, 1318.5];
    for (var i = 0; i < notes.length; i++) {
      (function (f, idx) {
        scheduleAfter(idx * 60, function () { tone({ type: 'triangle', freq: f, freqEnd: f * 1.03, duration: 0.18, attack: 0.006, gain: 0.14 * vm }); });
      })(notes[i], i);
    }
    return true;
  }
  function sError(vm) { tone({ type: 'square', freq: 220, freqEnd: 130, duration: 0.14, attack: 0.004, gain: 0.14 * vm }); return true; }
  function sWhoosh(vm) { noiseHit({ filterType: 'bandpass', filterFreq: 300, filterFreqEnd: 2600, q: 1.4, duration: 0.22, attack: 0.01, gain: 0.14 * vm }); return true; }

  // 'heartbeat' -- slow rhythmic low double-thud, LOOP-ONLY (start/stop via
  // AK_SFX.loop('heartbeat') / AK_SFX.stopLoop('heartbeat')). Meant to run
  // while boss/player HP is critical. opts.interval (ms) tunes the cycle.
  var HEARTBEAT_CYCLE_MS_DEFAULT = 950;
  function startHeartbeatLoop(opts) {
    opts = opts || {};
    var cycle = clamp(opts.interval || HEARTBEAT_CYCLE_MS_DEFAULT, 300, 3000);
    var vm = (opts.volume != null) ? clamp(opts.volume, 0, 2) : 1;
    var stopped = false;
    function beatOnce() {
      if (stopped || _muted) return;
      tone({ type: 'sine', freq: 58, freqEnd: 40, duration: 0.10, attack: 0.004, gain: 0.34 * vm });
      scheduleAfter(Math.round(cycle * 0.22), function () {
        if (stopped) return;
        tone({ type: 'sine', freq: 50, freqEnd: 34, duration: 0.12, attack: 0.004, gain: 0.30 * vm });
      });
    }
    beatOnce();
    var timer = null;
    try { timer = setInterval(beatOnce, cycle); } catch (_e) { timer = null; }
    return {
      stop: function () { stopped = true; try { if (timer != null) clearInterval(timer); } catch (_e) {} }
    };
  }

  var LOOP_BUILDERS = { heartbeat: startHeartbeatLoop };

  // name -> one-shot builder (aliases point at the same function, per spec's
  // slash-separated naming: 'impact'/'hit', 'crit'/'heavy', 'phase'/'enrage',
  // 'charge'/'telegraph', 'victory'/'crown'). 'heartbeat' is intentionally
  // absent here -- it is loop-only.
  var PLAY_BUILDERS = {
    boss_enter: sBossEnter,
    boss_roar: sBossRoar,
    impact: sImpact, hit: sImpact,
    crit: sCrit, heavy: sCrit,
    phase: sPhase, enrage: sPhase,
    charge: sCharge, telegraph: sCharge,
    victory: sVictory, crown: sVictory,
    defeat: sDefeat,
    tap: sTap, coin: sCoin, reward: sReward, error: sError, whoosh: sWhoosh
  };

  // --------------------------------------------------------------------
  // 7. gesture unlock
  // --------------------------------------------------------------------
  function markUnlocked() {
    _unlocked = true;
    try {
      for (var name in _pendingLoops) {
        if (!_pendingLoops.hasOwnProperty(name)) continue;
        var opts = _pendingLoops[name];
        delete _pendingLoops[name];
        loop(name, opts);
      }
    } catch (_e) {}
  }

  function attemptUnlock() {
    try {
      var ctx = getCtx();
      if (!ctx) return false;
      getMaster();   // build the bus now that we're allowed to touch audio
      if (ctx.state === 'suspended' && typeof ctx.resume === 'function') {
        var p = ctx.resume();
        if (p && typeof p.then === 'function') { p.then(markUnlocked, function () {}); }
        else { markUnlocked(); }
      } else {
        markUnlocked();
      }
      return true;
    } catch (_e) { return false; }
  }

  var GESTURE_EVENTS = ['pointerdown', 'touchstart', 'keydown'];
  function bindGestureUnlock() {
    if (_gestureBound) return;
    _gestureBound = true;
    try {
      if (!root || typeof root.addEventListener !== 'function') return;
      var handler = function () {
        attemptUnlock();
        for (var i = 0; i < GESTURE_EVENTS.length; i++) {
          try { root.removeEventListener(GESTURE_EVENTS[i], handler, true); } catch (_e) {}
        }
      };
      for (var i = 0; i < GESTURE_EVENTS.length; i++) {
        try { root.addEventListener(GESTURE_EVENTS[i], handler, { once: true, passive: true, capture: true }); }
        catch (_e) { try { root.addEventListener(GESTURE_EVENTS[i], handler, true); } catch (_e2) {} }
      }
    } catch (_e) {}
  }
  bindGestureUnlock();   // armed at load time; creates NOTHING until it fires

  // --------------------------------------------------------------------
  // 8. public API
  // --------------------------------------------------------------------
  function init() { return attemptUnlock(); }

  function play(name, opts) {
    try {
      if (!name || typeof name !== 'string') return false;
      if (_muted) return false;
      if (name === 'heartbeat') return false;   // loop-only, use loop()/stopLoop()
      var fn = PLAY_BUILDERS[name];
      if (!fn) return false;
      if (!_unlocked) return false;             // never touch the context pre-gesture
      if (throttled(name)) return false;
      var ctx = getCtx(); var m = getMaster();
      if (!ctx || !m) return false;
      var vm = (opts && isFinite(opts.volume)) ? clamp(opts.volume, 0, 2) : 1;
      return !!fn(vm, opts || {});
    } catch (_e) { return false; }
  }

  function loop(name, opts) {
    try {
      if (!name || typeof name !== 'string') return false;
      if (_loops[name]) return true;            // already running -- idempotent
      if (!_unlocked) { _pendingLoops[name] = opts || {}; return false; }
      var builder = LOOP_BUILDERS[name];
      if (!builder) return false;
      var ctx = getCtx(); var m = getMaster();
      if (!ctx || !m) return false;
      var ctrl = builder(opts || {});
      if (!ctrl) return false;
      _loops[name] = ctrl;
      return true;
    } catch (_e) { return false; }
  }

  function stopLoop(name) {
    try {
      delete _pendingLoops[name];
      var ctrl = _loops[name];
      if (ctrl) { try { ctrl.stop(); } catch (_e) {} delete _loops[name]; }
      return true;
    } catch (_e) { return false; }
  }

  function stopAllLoops() {
    try {
      for (var k in _loops) { if (_loops.hasOwnProperty(k)) stopLoop(k); }
      _pendingLoops = {};
    } catch (_e) {}
  }

  function setMuted(v) {
    try {
      _muted = !!v;
      writeMutedPref(_muted);
      applyMasterGain();
    } catch (_e) {}
    return _muted;
  }
  function isMuted() { return _muted; }

  function setVolume(v) {
    try {
      var n = Number(v);
      if (isFinite(n)) { _volume = clamp(n, 0, 1); applyMasterGain(); }
    } catch (_e) {}
    return _volume;
  }
  function getVolume() { return _volume; }

  function isUnlocked() { return _unlocked; }

  exportApi({
    init: init,
    play: play,
    loop: loop,
    stopLoop: stopLoop,
    stopAllLoops: stopAllLoops,
    setMuted: setMuted,
    muted: isMuted,
    setVolume: setVolume,
    volume: getVolume,
    isUnlocked: isUnlocked,
    list: function () { return SOUND_LIST.slice(); }
  });

})(typeof window !== 'undefined' ? window : globalThis);
