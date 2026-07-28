/* ALLEY KINGZ -- systems/districtmusic.js  (AK-DISTRICTMUSIC 2026-06-21, punch-list #18)
   Per-district AMBIENT theme music for the walkable HUB.

   WHAT IT DOES
     - Each district gets its OWN ambient theme -- a distinct MOOD (warm street vs
       industrial-cold vs neon-synth vs dockside-dub vs uptown-gloss) built from
       PROCEDURAL Web-Audio (no asset files): 2-4 layered voices (pad + sub +
       gentle arp), a different KEY + TEMPO + TIMBRE per district so each FEELS
       different. Low tempo, gentle filter movement, NO percussion, NO battle
       energy -- exploration / atmosphere, not action.
     - When you cross into a new district (ctx.zoneId changes) it CROSSFADES
       (~1.5s) from the old theme to the new one.

   DESIGN LAWS (mirrors loops.js + AK_AUDIO_MASTERPLAN.md ground rules)
     - SELF-HOOKING: ships as an AK_SYSTEMS plug-in (window.AK_SYSTEMS.register
       with init/onTick). The ONLY host edit is the <script> tag in index.html.
       No engine.js change, no host-logic change, all IDs/hooks preserved.
     - REUSE the audio context: if the engine already exposes one
       (window.AK.getAudioCtx) we reuse it -- never a second AudioContext.
       In the hub (which does NOT load engine.js) we create one lazily.
     - AUTOPLAY-SAFE: Web-Audio is blocked until a user gesture, so nothing
       sounds until the first tap/pointer/key (same pattern as the loadscreen
       video .play()). No gesture => silence (correct, never throws).
     - HUB-ONLY: onTick only fires while the hub is walkable (index.html gates it
       to state==='IN_ZONE' && !interiorOpen && !entering). A cheap watchdog
       fades the bed to silence the instant onTick goes stale (interior open,
       overlay/encounter, transition, leaving) so the battler/menus keep their
       own audio. Resumes when you're walking again.
     - RESPECTS MUTE: reads localStorage 'ak_muted' (the shared key the engine +
       index.html use) and AK.isMuted() when present; master goes to 0 when muted.
     - DUCK HOOK: window.AKDistrictMusic.duck(ms) ducks the bed under a SFX hit
       and recovers -- so any SFX layer that wants to duck has a hook to call.
     - KILL SWITCH: localStorage 'ak_music_off' === '1' disables it entirely
       (low-end / operator opt-out), same shape as loops.js's ak_loops_off.

   PERF ($100-Android law)
     - The graph is built from CONTINUOUS oscillators (pad/sub/LFO) created ONCE
       per theme; the arp creates one short osc+gain per NOTE (~1 note/sec), never
       per-frame. onTick does ZERO allocation -- it only compares the zone id and
       stamps a timer. Only ever 1-2 themes are alive (current + the one fading
       out). Arp note-scheduling pauses when the hub isn't walkable.
     - Fully guarded: a headless/node harness (no AudioContext) makes every path
       a clean no-op.
*/
(function () {
  "use strict";

  // ----------------------------------------------------------------------
  // 0. tunables
  // ----------------------------------------------------------------------
  var MASTER_VOL   = 0.22;   // ambient bed sits well UNDER any SFX
  var XFADE_TAU    = 0.5;    // setTargetAtTime tau -> ~1.5s perceptual crossfade
  var BED_TAU      = 0.14;   // faster: walkable on/off + duck response
  var DUCK_LEVEL   = 0.38;   // bed multiplier while ducked under a SFX
  var STALE_MS     = 380;    // onTick gone quiet this long => not walking the hub
  var WATCH_MS     = 220;    // watchdog cadence (cheap; reads 2 localStorage keys)
  var TEARDOWN_MS  = 1850;   // kill a faded-out theme just after the crossfade ends

  // ----------------------------------------------------------------------
  // 1. PER-DISTRICT MOOD MAP  (key + tempo + timbre = a distinct feel each)
  //    root  : tonic frequency (the KEY)
  //    scale : semitone offsets the arp walks (the MODE/colour)
  //    tempo : seconds between arp notes (low = slow/sparse)
  //    pad   : continuous chord oscillator waveform + detune (cents)
  //    sub   : low drone waveform + level
  //    cutoff: lowpass base (Hz) + a slow LFO (rate Hz / depth Hz) = "filter movement"
  //    arp   : note waveform + level + its own lowpass
  //    desc  : the intended mood (for humans / debugging)
  // ----------------------------------------------------------------------
  var MOODS = {
    // --- NORTH ROW -----------------------------------------------------
    THE_OVERLOOK: { // locked police checkpoint, cold & watchful -- sparse high surveillance hum
      root: 110.00, scale: [0, 3, 7, 10, 12], tempo: 1.85,
      pad: { wave: "triangle", detune: 6, gain: 0.16 }, sub: { wave: "sine", gain: 0.12 },
      cutoff: { base: 720, lfoRate: 0.05, lfoDepth: 240 },
      arp: { wave: "sine", gain: 0.05, cutoff: 1600 },
      desc: "cold, distant surveillance -- A minor, very slow, glassy & sparse"
    },
    DOWNTOWN: { // neon city core -- mid neon-synth arp, urban movement
      root: 130.81, scale: [0, 2, 3, 7, 9, 10], tempo: 0.66,
      pad: { wave: "sawtooth", detune: 9, gain: 0.13 }, sub: { wave: "sine", gain: 0.13 },
      cutoff: { base: 1150, lfoRate: 0.09, lfoDepth: 520 },
      arp: { wave: "sawtooth", gain: 0.055, cutoff: 2400 },
      desc: "neon-synth city -- C dorian, mid tempo, saw arps, lively but not busy"
    },
    NEON_HEIGHTS: { // uptown shops -- glossy, bright, shimmery major
      root: 164.81, scale: [0, 2, 4, 7, 9, 12], tempo: 0.5,
      pad: { wave: "triangle", detune: 7, gain: 0.13 }, sub: { wave: "sine", gain: 0.10 },
      cutoff: { base: 1700, lfoRate: 0.11, lfoDepth: 700 },
      arp: { wave: "triangle", gain: 0.06, cutoff: 3200 },
      desc: "uptown gloss -- E major pentatonic, bright shimmer, the high-end district"
    },
    // --- CENTER ROW ----------------------------------------------------
    THE_YARDS: { // crews / community -- warm street, mid pad
      root: 98.00, scale: [0, 2, 4, 5, 7, 9], tempo: 0.92,
      pad: { wave: "triangle", detune: 8, gain: 0.16 }, sub: { wave: "sine", gain: 0.14 },
      cutoff: { base: 950, lfoRate: 0.07, lfoDepth: 360 },
      arp: { wave: "triangle", gain: 0.055, cutoff: 2000 },
      desc: "warm street / crew yard -- G mixolydian, mid tempo, communal & rootsy"
    },
    HOME_TURF: { // THE LOT, your home base -- the welcoming hub theme
      root: 146.83, scale: [0, 2, 4, 7, 9], tempo: 0.8,
      pad: { wave: "triangle", detune: 5, gain: 0.17 }, sub: { wave: "sine", gain: 0.14 },
      cutoff: { base: 1050, lfoRate: 0.06, lfoDepth: 380 },
      arp: { wave: "sine", gain: 0.06, cutoff: 2200 },
      desc: "home / welcoming -- D major, gentle, the comfortable 'you're home' bed"
    },
    FACTORY_ROW: { // production machinery -- industrial-cold, metallic, gritty
      root: 87.31, scale: [0, 1, 5, 7, 8], tempo: 1.1,
      pad: { wave: "square", detune: 14, gain: 0.10 }, sub: { wave: "sawtooth", gain: 0.13 },
      cutoff: { base: 620, lfoRate: 0.08, lfoDepth: 300 },
      arp: { wave: "square", gain: 0.04, cutoff: 1400 },
      desc: "industrial-cold -- F phrygian, slow, detuned metallic square, machine-room grit"
    },
    // --- SOUTH ROW -----------------------------------------------------
    THE_UNDERCITY: { // locked collapsed bridge -- deep cavernous sub, ominous-ambient
      root: 65.41, scale: [0, 3, 5, 7, 10], tempo: 2.2,
      pad: { wave: "sine", detune: 4, gain: 0.15 }, sub: { wave: "sine", gain: 0.18 },
      cutoff: { base: 480, lfoRate: 0.04, lfoDepth: 180 },
      arp: { wave: "sine", gain: 0.045, cutoff: 1100 },
      desc: "the undercity -- C minor, deep & cavernous, sub-heavy, very slow & dark"
    },
    THE_STRIP: { // street mode + arcade -- playful neon, a touch quicker
      root: 220.00, scale: [0, 2, 4, 7, 9, 12], tempo: 0.42,
      pad: { wave: "square", detune: 6, gain: 0.09 }, sub: { wave: "triangle", gain: 0.11 },
      cutoff: { base: 1600, lfoRate: 0.12, lfoDepth: 600 },
      arp: { wave: "square", gain: 0.045, cutoff: 2800 },
      desc: "the strip / arcade -- A major pentatonic, brighter & playful, soft chiptune sparkle"
    },
    THE_DOCKS: { // waterfront -- dockside-dub, wide, watery, slow
      root: 82.41, scale: [0, 2, 3, 7, 10], tempo: 1.4,
      pad: { wave: "triangle", detune: 11, gain: 0.14 }, sub: { wave: "sine", gain: 0.16 },
      cutoff: { base: 760, lfoRate: 0.05, lfoDepth: 320 },
      arp: { wave: "sine", gain: 0.05, cutoff: 1500 },
      desc: "dockside-dub -- E dorian, slow & wide, watery filter sway, cool & echoey"
    }
  };
  // any unmapped / future zone falls back to a neutral neon-noir bed
  var MOOD_DEFAULT = {
    root: 123.47, scale: [0, 3, 5, 7, 10], tempo: 0.9,
    pad: { wave: "sawtooth", detune: 8, gain: 0.13 }, sub: { wave: "sine", gain: 0.13 },
    cutoff: { base: 1000, lfoRate: 0.07, lfoDepth: 400 },
    arp: { wave: "triangle", gain: 0.05, cutoff: 2000 },
    desc: "neutral neon-noir fallback"
  };
  function moodFor(zoneId) { return (zoneId && MOODS[zoneId]) || MOOD_DEFAULT; }

  // ----------------------------------------------------------------------
  // 2. audio context + master bus  (reuse engine's if present, else lazy own)
  // ----------------------------------------------------------------------
  var _ac = null, _master = null, _bed = null;
  var _ownsCtx = false;

  function getCtx() {
    // prefer an existing engine context so we never run two AudioContexts
    try { if (window.AK && typeof AK.getAudioCtx === "function") { var a = AK.getAudioCtx(); if (a) return a; } } catch (_e) {}
    if (_ac) return _ac;
    try { _ac = new (window.AudioContext || window.webkitAudioContext)(); _ownsCtx = true; }
    catch (_e2) { _ac = null; }
    return _ac;
  }

  // master gain -> destination ; bed gain sits under it for walkable/duck control
  function master() {
    var ac = getCtx(); if (!ac) return null;
    if (!_master) {
      try {
        _master = ac.createGain();
        _master.gain.value = isMuted() ? 0 : MASTER_VOL;
        _master.connect(ac.destination);
        _bed = ac.createGain();
        _bed.gain.value = 0;            // starts silent; ramps up only when walkable
        _bed.connect(_master);
      } catch (_e) { _master = null; _bed = null; }
    }
    return _master;
  }

  function isMuted() {
    try { if (window.AK && typeof AK.isMuted === "function" && AK.isMuted()) return true; } catch (_e) {}
    try { return localStorage.getItem("ak_muted") === "1"; } catch (_e2) { return false; }
  }
  function killed() {
    try { return localStorage.getItem("ak_music_off") === "1"; } catch (_e) { return false; }
  }
  function rampTo(param, target, tau) {
    if (!param) return;
    var ac = getCtx(); if (!ac) return;
    try { param.cancelScheduledValues(ac.currentTime); param.setTargetAtTime(target, ac.currentTime, tau); } catch (_e) {}
  }
  function noteFreq(root, semi) { return root * Math.pow(2, semi / 12); }

  // ----------------------------------------------------------------------
  // 3. a THEME = the procedural voice graph for one district
  //    pad (2 osc) + sub (1 osc) + filter LFO (continuous) + scheduled arp.
  // ----------------------------------------------------------------------
  function Theme(zoneId) {
    this.zoneId = zoneId;
    this.mood = moodFor(zoneId);
    this.nodes = [];        // everything to stop()/disconnect()
    this.gain = null;       // this theme's own fader (crossfade target)
    this._arpTimer = 0;
    this._step = 0;
    this._dead = false;
    this._started = false;
  }

  Theme.prototype.start = function () {
    var ac = getCtx(); if (!ac) return false;
    var m = master(); if (!m || !_bed) return false;
    if (this._started) return true;
    var mood = this.mood, self = this;
    try {
      this.gain = ac.createGain();
      this.gain.gain.value = 0;           // fades in via crossfade
      this.gain.connect(_bed);

      // --- shared lowpass with a slow LFO = "gentle filter movement" ---
      var lp = ac.createBiquadFilter();
      lp.type = "lowpass";
      lp.frequency.value = mood.cutoff.base;
      lp.Q.value = 0.7;
      lp.connect(this.gain);
      var lfo = ac.createOscillator(); lfo.type = "sine"; lfo.frequency.value = mood.cutoff.lfoRate;
      var lfoG = ac.createGain(); lfoG.gain.value = mood.cutoff.lfoDepth;
      lfo.connect(lfoG); lfoG.connect(lp.frequency); lfo.start();
      this.nodes.push(lfo, lfoG, lp);

      // --- PAD: root + perfect-fifth, slightly detuned, continuous ---
      var padG = ac.createGain(); padG.gain.value = mood.pad.gain; padG.connect(lp);
      var p1 = ac.createOscillator(); p1.type = mood.pad.wave; p1.frequency.value = mood.root;            p1.detune.value = -mood.pad.detune;
      var p2 = ac.createOscillator(); p2.type = mood.pad.wave; p2.frequency.value = noteFreq(mood.root, 7); p2.detune.value =  mood.pad.detune;
      p1.connect(padG); p2.connect(padG); p1.start(); p2.start();
      this.nodes.push(p1, p2, padG);

      // --- SUB: octave-down sine drone, continuous ---
      var subG = ac.createGain(); subG.gain.value = mood.sub.gain; subG.connect(this.gain);
      var s1 = ac.createOscillator(); s1.type = mood.sub.wave; s1.frequency.value = mood.root / 2;
      s1.connect(subG); s1.start();
      this.nodes.push(s1, subG);

      // --- ARP: its own softer lowpass; notes scheduled one at a time ---
      this._arpLp = ac.createBiquadFilter(); this._arpLp.type = "lowpass";
      this._arpLp.frequency.value = mood.arp.cutoff; this._arpLp.connect(this.gain);
      this.nodes.push(this._arpLp);

      this._started = true;
      // kick the arp scheduler (it self-gates on walkable + alive)
      this._scheduleArp();
      return true;
    } catch (_e) { return false; }
  };

  // one short, soft arp note + recursive self-scheduling (NOT per-frame)
  Theme.prototype._scheduleArp = function () {
    var self = this;
    if (this._dead) return;
    var mood = this.mood;
    // humanise the interval a touch so it never sounds like a metronome
    var wait = mood.tempo * (0.9 + Math.random() * 0.2) * 1000;
    this._arpTimer = setTimeout(function () { self._tickArp(); }, wait);
  };

  Theme.prototype._tickArp = function () {
    if (this._dead) { return; }
    // only make sound while the hub is being walked + not muted/killed
    if (_walkable && !isMuted() && !killed()) {
      var ac = getCtx(), mood = this.mood;
      if (ac && this._arpLp) {
        try {
          // walk the scale; occasionally lift an octave for gentle motion
          this._step = (this._step + 1 + (Math.random() < 0.22 ? 1 : 0)) % mood.scale.length;
          var semi = mood.scale[this._step] + (Math.random() < 0.3 ? 12 : 0);
          var f = noteFreq(mood.root, semi);
          var t = ac.currentTime, dur = Math.min(0.9, mood.tempo * 0.85);
          var o = ac.createOscillator(); o.type = mood.arp.wave; o.frequency.value = f;
          var g = ac.createGain(); g.gain.value = 0;
          o.connect(g); g.connect(this._arpLp);
          // soft pluck: quick-ish attack, gentle release (no transient "hit")
          g.gain.setValueAtTime(0, t);
          g.gain.linearRampToValueAtTime(mood.arp.gain, t + 0.05);
          g.gain.exponentialRampToValueAtTime(0.0008, t + dur);
          o.start(t); o.stop(t + dur + 0.05);
          o.onended = function () { try { o.disconnect(); g.disconnect(); } catch (_e) {} };
        } catch (_e) {}
      }
    }
    this._scheduleArp();
  };

  Theme.prototype.fadeIn  = function () { rampTo(this.gain && this.gain.gain, 1, XFADE_TAU); };
  Theme.prototype.fadeOut = function () { rampTo(this.gain && this.gain.gain, 0, XFADE_TAU); };

  Theme.prototype.stop = function () {
    this._dead = true;
    if (this._arpTimer) { try { clearTimeout(this._arpTimer); } catch (_e) {} this._arpTimer = 0; }
    var ac = getCtx(), t = ac ? ac.currentTime : 0;
    this.nodes.forEach(function (n) {
      try { if (n.stop) n.stop(t + 0.02); } catch (_e) {}
      try { n.disconnect(); } catch (_e2) {}
    });
    try { if (this.gain) this.gain.disconnect(); } catch (_e) {}
    this.nodes = [];
  };

  // ----------------------------------------------------------------------
  // 4. the controller -- crossfade on zone change, watchdog for walkable/mute
  // ----------------------------------------------------------------------
  var _current = null;       // active Theme
  var _outgoing = [];        // themes mid-fade-out (torn down on a timer)
  var _curZone = null;
  var _unlocked = false;     // a user gesture has resumed the context
  var _walkable = false;     // onTick fired recently => hub is being walked
  var _lastTick = 0;         // performance.now() of last onTick
  var _hidden = false;
  var _duckUntil = 0;
  var _watch = 0;

  function nowMs() { try { return performance.now(); } catch (_e) { return Date.now(); } }

  function switchTo(zoneId) {
    if (!_unlocked || killed()) return;
    if (zoneId === _curZone && _current) return;
    var m = master(); if (!m) return;
    // fade out the old one + schedule its teardown
    if (_current) {
      var dying = _current;
      dying.fadeOut();
      _outgoing.push(dying);
      setTimeout(function () {
        try { dying.stop(); } catch (_e) {}
        var i = _outgoing.indexOf(dying); if (i >= 0) _outgoing.splice(i, 1);
      }, TEARDOWN_MS);
    }
    // bring the new one up
    var th = new Theme(zoneId);
    if (th.start()) { th.fadeIn(); _current = th; _curZone = zoneId; }
  }

  // bed gain = walkable? * duck? -- the global "is it audible right now" control
  function applyBed() {
    if (!_bed) return;
    var live = _walkable && !_hidden && _unlocked && !isMuted() && !killed();
    var duck = (nowMs() < _duckUntil) ? DUCK_LEVEL : 1;
    rampTo(_bed.gain, live ? duck : 0, BED_TAU);
    // mirror mute onto the master too (so a mid-session mute toggle is honoured)
    rampTo(master() && _master.gain, isMuted() ? 0 : MASTER_VOL, BED_TAU);
  }

  // ----------------------------------------------------------------------
  // 4b. NEEDLE-DROP (Tarantino) -- duck the bed + drop a short IN-KEY percussive
  //     stinger built in the CURRENT district's root/scale, then restore. Fires
  //     on a raid tier-up only (a PUNCH, never per-frame), so a handful of short
  //     -lived nodes per drop is well within the $100-Android budget -- the same
  //     pattern the arp already uses per note. Cached ONCE: a dedicated stinger
  //     bus (sits ABOVE the ducked bed so the drop cuts through) + a single white
  //     -noise buffer reused for every crack. Honours mute / kill-switch /
  //     headless / suspended-context (every path is a clean no-op).
  // ----------------------------------------------------------------------
  // shared duck control -- the public duck() hook AND the needle-drop both use it
  function duckBed(ms) { _duckUntil = nowMs() + (ms || 350); applyBed(); }

  var _stingBus = null, _noiseBuf = null, _lastDrop = 0;
  function stingBus() {
    var ac = getCtx(); if (!ac) return null;
    if (!master()) return null;
    if (!_stingBus) {
      try { _stingBus = ac.createGain(); _stingBus.gain.value = 1; _stingBus.connect(_master); }
      catch (_e) { _stingBus = null; }
    }
    return _stingBus;
  }
  function noiseBuf(ac) {
    if (_noiseBuf) return _noiseBuf;
    try {
      var n = Math.floor(ac.sampleRate * 0.4);     // 0.4s of white noise, built ONCE then reused
      _noiseBuf = ac.createBuffer(1, n, ac.sampleRate);
      var d = _noiseBuf.getChannelData(0);
      for (var i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    } catch (_e) { _noiseBuf = null; }
    return _noiseBuf;
  }

  // intensity 1..3 (the raid tier) -> a BIGGER drop: louder, brighter, more in
  // -key stabs, longer duck. Built from the CURRENT district mood so it lands
  // in the district's KEY (not a generic noise burst).
  function needleDrop(intensity) {
    var ac = getCtx(); if (!ac) return;                                  // headless => clean no-op
    if (isMuted() || killed()) return;                                   // respect mute + kill-switch
    try { if (ac.state && ac.state !== "running") return; } catch (_e) {} // autoplay-safe: only on a live ctx
    var t0 = nowMs(); if (t0 - _lastDrop < 220) return;                  // a punch, never a machine-gun
    _lastDrop = t0;
    var bus = stingBus(); if (!bus) return;

    var tier = Math.max(1, Math.min(3, Math.round(intensity || 1)));
    duckBed(260 + tier * 140);                                           // DUCK the ambient bed (reuse the hook)

    var mood  = (_current && _current.mood) || moodFor(_curZone);
    var root  = (mood && mood.root)  || 130.81;
    var scale = (mood && mood.scale) || [0, 3, 7];
    var t   = ac.currentTime;
    var lvl = 0.5 + tier * 0.16;

    try {
      // (a) BOOM -- a low percussive kick on the district ROOT: fast pitch-drop + fast decay
      var bo = ac.createOscillator(); bo.type = "sine";
      var bg = ac.createGain(); bg.gain.value = 0;
      bo.connect(bg); bg.connect(bus);
      bo.frequency.setValueAtTime(root * 1.6, t);
      bo.frequency.exponentialRampToValueAtTime(root * 0.5, t + 0.14);
      bg.gain.setValueAtTime(0, t);
      bg.gain.linearRampToValueAtTime(lvl, t + 0.006);
      bg.gain.exponentialRampToValueAtTime(0.0008, t + 0.20 + tier * 0.04);
      bo.start(t); bo.stop(t + 0.30 + tier * 0.05);
      bo.onended = function () { try { bo.disconnect(); bg.disconnect(); } catch (_e) {} };

      // (b) CRACK -- a filtered white-noise burst (snare/clap), brighter at higher tiers
      var nb = noiseBuf(ac);
      if (nb) {
        var ns = ac.createBufferSource(); ns.buffer = nb;
        var nf = ac.createBiquadFilter(); nf.type = "highpass"; nf.frequency.value = 1200 + tier * 700;
        var ng = ac.createGain(); ng.gain.value = 0;
        ns.connect(nf); nf.connect(ng); ng.connect(bus);
        var nd = 0.08 + tier * 0.03;
        ng.gain.setValueAtTime(0, t);
        ng.gain.linearRampToValueAtTime(0.18 + tier * 0.07, t + 0.004);
        ng.gain.exponentialRampToValueAtTime(0.0006, t + nd);
        ns.start(t); ns.stop(t + nd + 0.02);
        ns.onended = function () { try { ns.disconnect(); nf.disconnect(); ng.disconnect(); } catch (_e) {} };
      }

      // (c) STAB -- short IN-KEY tonal hits: root (+ a scale colour tone at T2,
      //     + an octave punch at T3) so the drop is in the district's KEY
      var tones = [0];
      if (tier >= 2) tones.push(scale[Math.min(2, scale.length - 1)] || 7);
      if (tier >= 3) tones.push(12);
      for (var k = 0; k < tones.length; k++) {
        var so = ac.createOscillator(); so.type = tier >= 3 ? "sawtooth" : "square";
        var sf = ac.createBiquadFilter(); sf.type = "lowpass"; sf.frequency.value = 1400 + tier * 900;
        var sg = ac.createGain(); sg.gain.value = 0;
        so.frequency.value = noteFreq(root, tones[k]);
        so.connect(sf); sf.connect(sg); sg.connect(bus);
        var sd = 0.16 + tier * 0.05;
        sg.gain.setValueAtTime(0, t);
        sg.gain.linearRampToValueAtTime(0.10 + tier * 0.04, t + 0.008);
        sg.gain.exponentialRampToValueAtTime(0.0006, t + sd);
        so.start(t); so.stop(t + sd + 0.03);
        (function (a, b, c) { a.onended = function () { try { a.disconnect(); b.disconnect(); c.disconnect(); } catch (_e) {} }; })(so, sf, sg);
      }
    } catch (_e) {}
  }

  function unlock() {
    if (_unlocked) return;
    var ac = getCtx(); if (!ac) return;
    try { if (ac.state === "suspended" && ac.resume) ac.resume(); } catch (_e) {}
    try { if (window.AK && typeof AK.resumeAudio === "function") AK.resumeAudio(); } catch (_e2) {}
    _unlocked = true;
    // start whatever zone we're standing in right now
    if (_curZone) switchTo(_curZone);
  }

  function startWatchdog() {
    if (_watch) return;
    _watch = setInterval(function () {
      // onTick stale => not walking the hub (interior/overlay/transition/left)
      _walkable = (nowMs() - _lastTick) < STALE_MS;
      applyBed();
      // if killed/muted mid-session, an arp simply stays silent (gated in _tickArp)
    }, WATCH_MS);
  }

  // ----------------------------------------------------------------------
  // 5. public API + AK_SYSTEMS registration
  // ----------------------------------------------------------------------
  var API = {
    // duck the bed under a SFX hit, recover after ms (default 350ms)
    duck: function (ms) { duckBed(ms); },
    // NEEDLE-DROP (Tarantino): duck the bed + drop a short in-key percussive stinger
    // sized by intensity (raid tier 1..3). A punch on a tier-up, not every hit.
    needleDrop: function (intensity) { needleDrop(intensity); },
    setEnabled: function (on) {
      try { localStorage.setItem("ak_music_off", on ? "0" : "1"); } catch (_e) {}
      if (!on && _current) { _current.fadeOut(); }
      applyBed();
    },
    isPlaying: function () { return !!(_current && _walkable && _unlocked && !isMuted()); },
    currentZone: function () { return _curZone; },
    moodFor: moodFor,
    MOODS: MOODS
  };
  window.AKDistrictMusic = API;
  window.AK_DISTRICTMUSIC = API;   // alias the modes.js needle-drop trigger looks for

  function init(ctx) {
    if (killed()) { /* still wire the kill-switch can be flipped off later via API */ }
    // remember the starting zone so the first gesture can begin immediately
    try { _curZone = (ctx && (ctx.zoneId || (ctx.activeZone && ctx.activeZone.id))) || _curZone; } catch (_e) {}
    // AUTOPLAY-SAFE: unlock on the first user gesture (same intent as the
    // loadscreen video .play()). capture+once so it's truly one-shot + cheap.
    var opt = { capture: true, once: true, passive: true };
    ["pointerdown", "touchstart", "mousedown", "keydown"].forEach(function (ev) {
      try { document.addEventListener(ev, unlock, opt); } catch (_e) {}
    });
    // pause the bed while the tab is backgrounded (battery); resume on return
    try {
      document.addEventListener("visibilitychange", function () {
        _hidden = !!document.hidden; applyBed();
      });
    } catch (_e) {}
    // NEEDLE-DROP trigger: any system can fire
    //   window.dispatchEvent(new CustomEvent('ak:needledrop', {detail:{intensity}}))
    // and the drop lands in the current district's key (used when the direct
    // window.AK_DISTRICTMUSIC.needleDrop() call is not available to that context).
    try {
      window.addEventListener("ak:needledrop", function (e) {
        var it = (e && e.detail && e.detail.intensity) || 1;
        needleDrop(it);
      });
    } catch (_e) {}
    startWatchdog();
  }

  function onTick(dt, ctx) {
    // NO allocation here: stamp the walkable clock + react to a zone change.
    _lastTick = nowMs();
    if (!_unlocked) return;            // wait for the gesture (autoplay policy)
    var z = null;
    try { z = ctx && (ctx.zoneId || (ctx.activeZone && ctx.activeZone.id)); } catch (_e) {}
    if (z && z !== _curZone) switchTo(z);
    else if (z && !_current && !killed()) switchTo(z);   // first start after unlock
  }

  // register as an AK_SYSTEMS plug-in (no onEnterBuilding => never claims a building)
  if (window.AK_SYSTEMS && AK_SYSTEMS.register) {
    AK_SYSTEMS.register({ id: "districtmusic", init: init, onTick: onTick });
  } else {
    // self-init fallback if the registry is absent (still autoplay-safe)
    try {
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { init(null); });
      else init(null);
    } catch (_e) {}
  }
})();
