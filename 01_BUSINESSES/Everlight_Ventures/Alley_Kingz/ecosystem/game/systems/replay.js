/* Alley Kingz -- RAID REPLAY + SPECTATOR FOUNDATION (window.AK_REPLAY)
 * AK-REPLAY 2026-07-18
 *
 * Live spectating needs concurrency this game does not have yet. REPLAY does not, and replay is the
 * honest first step: record what happened, play it back through the SAME renderer, cut a highlight,
 * hand it to viral.js. Everything here is client side. No backend, no sockets, no second renderer.
 *
 * THIS FILE OWNS
 *   - the recorder: samples the authoritative raid state on the RAID CLOCK (not wall clock)
 *   - the log format: a compact, delta-encoded, deterministic event log
 *   - playback: reconstructs state and writes it back into window.RAID + AK_CTX.me, so the raid
 *     renderer that already ships draws a replay exactly the way it draws a live raid
 *   - timeline control: play / pause / seek / speed, plus a free camera
 *   - highlight export shaped for systems/viral.js
 *   - capped local storage through AK_ECON.mutateProfile
 *
 * WHY IT SAMPLES INSTEAD OF LISTENING
 * The raid loop emits no events. index.html:2409 calls akRaidStep(dt) directly and never calls
 * AK_SYSTEMS.tickAll (that is gated to state==='IN_ZONE' at index.html:2407). So there is no event
 * bus to subscribe to and no registry tick during a raid. The recorder therefore OBSERVES the
 * authoritative state (window.RAID, AK_CTX.me) and DERIVES events from state transitions. Every
 * transition it cares about persists for at least one frame (RAID._wave, entity.dead, RAID.kills,
 * RAID.bag, RAID.secured, RAID.hp), so derivation is lossless for those events.
 *
 * WHY THE CLOCK IS RAID.t AND NOT performance.now()
 * Samples are keyed to elapsed RAID time (t0 - RAID.t) in centiseconds. That makes the log
 * independent of frame rate, of the sampling driver, and of how long the tab was backgrounded, and
 * it is what lets the same log be re-simulated on a server tick later.
 *
 * WHY me COMES FROM AK_CTX AND NOT window
 * index.html:728 declares `const me` and index.html:730 declares `let cam`. Top level const/let in
 * a classic script do NOT become window properties, so global.me is undefined. They are reachable
 * only through window.AK_CTX (index.html:3160 `me: me, cam: cam`). Reading global.me here would
 * have silently recorded nothing forever.
 *
 * WHY DISTRICT (zi) IS RECORDED -- AK-REPLAY-ZI 2026-07-18
 * A raid spans 2-3 districts. raidwaves.js:75 stamps every defender with `zi: r.zi|0`, survivors
 * are pulled forward on a district change (index.html:1593), and the DRAW PATH FILTERS ON IT:
 * index.html:2265 `if(e.dead||((e.zi|0)!==(RAID.zi|0)))continue`. akRaidDraw also reads
 * RAID.zone.buildings (index.html:2221). So a reconstruction that omits zi leaves every entity at
 * zi=0 and the renderer silently draws an EMPTY battlefield for any raid past the first district.
 * That is why the log carries EV.DIST (raid district) and EV.AZI (per actor district) and why
 * applyTo restores raid.zi AND raid.zone.
 *
 * RAIDPARAMS COMPATIBILITY (server re-sim)
 * The header stores the PURE INPUTS raidparams needs, not just its outputs: seed.defProfile (the
 * defender profile) plus seed.target (the raid target descriptor). systems/raidparams.js is pure
 * and headless, so a server can call AK_RAIDPARAMS.calculate(seed.defProfile, cards) and get
 * seed.rp back byte for byte, then planWaves() for the same wave composition. The map is
 * regenerable too: akRaidBuildZones(target) (index.html:1789) is a pure function of the target
 * descriptor, so seed.target is enough to rebuild the battlefield. That is why this format records
 * a SEED plus tracks, instead of dumping the built world.
 *
 * PUBLIC API (window.AK_REPLAY)
 *   install()                       start the observer (idempotent, browser only)
 *   isRecording()                   bool
 *   observe()                       one manual observation tick (idempotent on the raid clock)
 *   startRecording(), stopRecording(outcome)
 *   list()                          [{id, at, dur, outcome, bytes, pin}] newest first
 *   load(id) / remove(id) / pin(id, bool) / budget()
 *   open(recOrId)                   -> playback controller (see below)
 *   exportHighlight(rec, opts)      -> highlight package for viral.js
 *   shareHighlight(h)               -> calls AK_VIRAL.shareMoment (real, shipped API)
 *   encode(rec) / decode(str)       storage codec
 *   LIMITS, EV, FMT
 *
 * PLAYBACK CONTROLLER
 *   play() pause() toggle() playing()
 *   seek(sec) time() duration() setSpeed(s) speed()
 *   step(dtSec)                     advance the controller by dt (drives from any loop)
 *   state()                         reconstructed state at the current time
 *   applyTo(raid, ctx)              write reconstructed state into a RAID object + AK_CTX
 *   camera                          free camera: free(bool) focus(x,y) pan(dx,dy) zoom(z) follow()
 *   close()
 *
 * Guarded end to end. No DOM and no global reads at module load beyond the guarded AK_SYSTEMS
 * registration, so this file is requireable in node.
 */
(function (global) {
  'use strict';

  var ID = 'replay';
  var FMT = 1;

  /* ===================================================================== *
   * TUNABLES
   * Sample rates are the whole storage story. Player at 10 Hz reads smooth;
   * actors at 5 Hz is enough for readable movement once playback interpolates
   * between frames. A 390s TH10 raid (the longest raidparams can produce) at
   * these rates with delta encoding lands well inside perReplayBytes; if a
   * pathological raid would blow the budget the recorder DECIMATES the actor
   * track instead of truncating the raid, so you always keep the whole fight.
   * ===================================================================== */
  var POS_HZ = 10;
  var ACT_HZ = 5;
  var LIMITS = {
    perReplayBytes: 96 * 1024,
    totalBytes: 320 * 1024,
    maxReplays: 4,
    maxActors: 24,            // hard cap on tracked defenders per raid
    maxEvents: 6000
  };
  // Highlight window. viral.js:288 records a FIXED 6000ms starting at the beginning of the window,
  // so pre+post must total 6.0s or the tape runs out mid clip. A 6s pre-roll would end the
  // recording exactly ON the kill and cut off the payoff, so the anchor sits at 4.5s (75% through)
  // and 1.5s of reaction follows it. Total 6.0s = the tape, exactly.
  var HL = { preSec: 4.5, postSec: 1.5 };

  // AK-REPLAY-ZI 2026-07-18: DIST = the raid moved district (a=zi). AZI = one actor moved district
  // (a=slot, b=zi). Both are rare (only on a district transition) so the cost is a few ints a raid,
  // and without them the renderer draws nothing past district 0. See the header note.
  var EV = { SPAWN: 1, WAVE: 2, HIT: 3, KILL: 4, LOOT: 5, SECURE: 6, PHURT: 7, BOSS: 8, END: 9, DIST: 10, AZI: 11 };
  // Index order MUST match AK_RAIDWAVES.OUTCOME values (raidwaves.js:247) so a re-sim agrees.
  var OUTCOMES = ['extract', 'surrender', 'timeout', 'wipe'];

  /* ===================================================================== *
   * GUARDED ACCESSORS
   * Nothing in this file touches a global except through these.
   * ===================================================================== */
  function CTX() { try { return global.AK_CTX || null; } catch (_e) { return null; } }
  function ME(c) { try { c = c || CTX(); return (c && c.me) || null; } catch (_e) { return null; } }
  function CAM(c) { try { c = c || CTX(); return (c && c.cam) || null; } catch (_e) { return null; } }
  function R() { try { return global.RAID || null; } catch (_e) { return null; } }
  function ECON() { try { return global.AK_ECON || null; } catch (_e) { return null; } }
  function now() { try { return Date.now(); } catch (_e) { return 0; } }

  function q(n) { n = Math.round(n || 0); return (n === n && n !== Infinity && n !== -Infinity) ? n : 0; }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  /* ===================================================================== *
   * RECORDER
   * ===================================================================== */
  var REC = null;      // recording in progress
  var LAST = null;     // most recently finished recording (survives a missing econ)
  // AK-REPLAY-EOR 2026-07-18: the raid object whose recording is already closed. akRaidEnd only
  // sets RAID.over=true (index.html:2044); it does NOT null RAID, and the rAF driver keeps calling
  // observe() every frame afterwards. Without this latch each of those frames opened a fresh
  // recording, hit `if (r.over) finish(...)` on the same call, and SAVED a 0-duration replay --
  // 60 a second, evicting the real one out of a 4-slot store almost instantly.
  var DONERAID = null;

  // Elapsed raid time in centiseconds. RAID.t counts DOWN (index.html:1922 `RAID.t-=dt`), so
  // elapsed is t0 - t. Keyed this way the log is frame-rate and driver independent.
  function elapsedCs(r, t0) {
    var t = (typeof r.t === 'number') ? r.t : 0;
    return Math.max(0, q((t0 - t) * 100));
  }

  // The re-sim seed. PURE INPUTS ONLY, so raidparams can rebuild the difficulty profile and
  // akRaidBuildZones can rebuild the map. We deliberately do not store the built world.
  function snapSeed(r) {
    // hp0/hpMax come from the raid object (index.html:1880 `hp:100, hpMax:100`). Recorded rather
    // than assumed, so playback starts the health bar where the raid actually started it.
    var s = { t0: (typeof r.t === 'number') ? r.t : 0, raidW: 0, raidH: 0, exX: 0, exY: 0, exR: 0,
              hp0: (typeof r.hp === 'number') ? (r.hp | 0) : 100, hpMax: (r.hpMax | 0) || 100, zi0: r.zi | 0 };
    try { s.raidW = q(global.RAID_W || 1500); s.raidH = q(global.RAID_H || 1150); } catch (_e) {}
    try { s.exX = q(r.exX); s.exY = q(r.exY); s.exR = q(r.exR); } catch (_e) {}
    // The whole difficulty profile raidparams produced for this raid (index.html:1876).
    try { s.rp = r.rp ? JSON.parse(JSON.stringify(r.rp)) : null; } catch (_e) { s.rp = null; }
    // The PURE INPUT raidparams consumed (index.html:1877). calculate(defProfile, cards) === rp.
    try { s.defProfile = r._defProfile ? JSON.parse(JSON.stringify(r._defProfile)) : null; } catch (_e) { s.defProfile = null; }
    // The target descriptor. akRaidBuildZones(target) is pure, so this regenerates the battlefield.
    try {
      var t = r.target || null;
      if (t) {
        s.target = {
          name: t.name || '', faction: t.faction || '', tier: t.tier | 0, id: t.id || '',
          layout: t.layout ? JSON.parse(JSON.stringify(t.layout)) : null
        };
      } else s.target = null;
    } catch (_e) { s.target = null; }
    return s;
  }

  // Stable per-entity identity across the whole raid. The defenders array is pushed to and
  // reordered, so index is not identity. A hidden _rpid is.
  function slotOf(rec, d) {
    if (typeof d._rpid === 'number') return d._rpid;
    if (rec._nextSlot >= LIMITS.maxActors) return -1;      // over cap: not tracked, never breaks
    d._rpid = rec._nextSlot++;
    return d._rpid;
  }

  // Entity descriptor, deduped into rec.protos. Most defenders in a wave are identical, so this
  // collapses N entities into a handful of prototypes.
  function protoIdx(rec, d) {
    var key = [d.name || '?', d.role || '', d.maxHp | 0, d.r | 0, d.rarity || '', d.lvl | 0, d.boss ? 1 : 0, d.ranged ? 1 : 0].join('|');
    var i = rec._protoKey[key];
    if (typeof i === 'number') return i;
    i = rec.protos.length;
    rec.protos.push({
      name: d.name || '?', role: d.role || '', maxHp: d.maxHp | 0, r: d.r | 0,
      rarity: d.rarity || '', lvl: d.lvl | 0, boss: d.boss ? 1 : 0, ranged: d.ranged ? 1 : 0,
      spd: d.spd | 0, tier: d.tier | 0
    });
    rec._protoKey[key] = i;
    return i;
  }

  function kindIdx(rec, k) {
    var i = rec.kinds.indexOf(k);
    if (i >= 0) return i;
    rec.kinds.push(k);
    return rec.kinds.length - 1;
  }

  function pushEv(rec, cs, code, a, b) {
    if (rec.ev.length >= LIMITS.maxEvents * 4) return;      // flat array, 4 ints per event
    rec.ev.push(cs, code, a | 0, b | 0);
  }

  function begin(r, c) {
    var me = ME(c);
    if (!r || !me) return null;
    var t0 = (typeof r.t === 'number') ? r.t : 0;
    REC = {
      v: FMT,
      id: 'rp_' + now().toString(36) + Math.random().toString(36).slice(2, 6),
      at: now(),
      posHz: POS_HZ, actHz: ACT_HZ,
      seed: snapSeed(r),
      protos: [], kinds: [],
      pos: [],            // [cs, x, y, dcs, dx, dy, ...]
      act: [],            // [cs, n, slot, dx, dy, ... n times] repeated
      ev: [],             // [cs, code, a, b, ...]
      dur: 0,
      outcome: '',
      kills: 0,
      // ---- transient recorder state (stripped by encode) ----
      _raid: r, _t0: t0, _cs: -1, _ended: false,
      _protoKey: {}, _nextSlot: 0,
      _posCs: -1e9, _actCs: -1e9,
      _lastPos: null, _lastAct: {},
      _hpBySlot: {}, _deadSlot: {}, _seenSlot: {}, _aziBySlot: {},
      _wave: 0, _kills: 0, _bag: {}, _secured: 0, _hp: (r.hp | 0) || 0, _boss: false,
      _zi: -1,                                   // AK-REPLAY-ZI: forces a DIST event on the first observe
      _dec: 1, _estBytes: 0
    };
    return REC;
  }

  // Derive every event we care about from state transitions since the last observation.
  function scanEvents(rec, r, cs) {
    // --- waves ---
    try {
      var w = r._wave | 0;
      if (w > rec._wave) { pushEv(rec, cs, EV.WAVE, w, 0); rec._wave = w; }
    } catch (_e) {}

    // --- district (AK-REPLAY-ZI): index.html:1588 moves RAID.zi + RAID.zone together ---
    try {
      var zi = r.zi | 0;
      if (zi !== rec._zi) { pushEv(rec, cs, EV.DIST, zi, 0); rec._zi = zi; }
    } catch (_e) {}

    var ds = null;
    try { ds = Array.isArray(r.defenders) ? r.defenders : null; } catch (_e) {}
    if (ds) {
      for (var i = 0; i < ds.length; i++) {
        var d = ds[i];
        if (!d) continue;
        var slot = slotOf(rec, d);
        if (slot < 0) continue;

        // --- spawn ---
        if (!rec._seenSlot[slot]) {
          rec._seenSlot[slot] = 1;
          pushEv(rec, cs, EV.SPAWN, slot, protoIdx(rec, d));
          rec._hpBySlot[slot] = d.hp | 0;
          rec._aziBySlot[slot] = 0;              // SPAWN implies zi 0; a non-zero zi emits AZI below
          if (d.boss && !rec._boss) { rec._boss = true; pushEv(rec, cs, EV.BOSS, slot, d.tier | 0); }
        }

        // --- district (AK-REPLAY-ZI): raidwaves.js:75 spawns with zi=r.zi, index.html:1593 pulls
        //     survivors forward. The draw path filters on it, so a miss here means a blank screen. ---
        var azi = d.zi | 0;
        if (azi !== (rec._aziBySlot[slot] | 0)) { pushEv(rec, cs, EV.AZI, slot, azi); rec._aziBySlot[slot] = azi; }

        // --- damage ---
        var hp = d.hp | 0, prev = rec._hpBySlot[slot];
        if (typeof prev === 'number' && hp < prev) {
          pushEv(rec, cs, EV.HIT, slot, prev - hp);
          rec._hpBySlot[slot] = hp;
        } else if (typeof prev !== 'number') {
          rec._hpBySlot[slot] = hp;
        }

        // --- death ---
        if (d.dead && !rec._deadSlot[slot]) {
          rec._deadSlot[slot] = 1;
          pushEv(rec, cs, EV.KILL, slot, 0);
        }
      }
    }

    // --- loot picked up into the carried bag (index.html:2003) ---
    try {
      var bag = r.bag || {};
      for (var k in bag) {
        if (!Object.prototype.hasOwnProperty.call(bag, k)) continue;
        var v = bag[k] | 0, pv = rec._bag[k] | 0;
        if (v > pv) { pushEv(rec, cs, EV.LOOT, kindIdx(rec, k), v - pv); }
        rec._bag[k] = v;
      }
    } catch (_e) {}

    // --- extraction: bag moved into secured (raidwaves.js secure()) ---
    try {
      var sec = 0, sm = r.secured || {};
      for (var sk in sm) { if (Object.prototype.hasOwnProperty.call(sm, sk)) sec += sm[sk] | 0; }
      if (sec > rec._secured) { pushEv(rec, cs, EV.SECURE, sec - rec._secured, sec); rec._secured = sec; }
    } catch (_e) {}

    // --- player took damage ---
    try {
      var php = r.hp | 0;
      if (php < rec._hp) { pushEv(rec, cs, EV.PHURT, rec._hp - php, php); }
      rec._hp = php;
    } catch (_e) {}

    try { rec._kills = r.kills | 0; } catch (_e) {}
  }

  function samplePos(rec, me, cs) {
    var iv = Math.round(100 / rec.posHz);
    if (cs - rec._posCs < iv) return;
    rec._posCs = cs;
    var x = q(me.x), y = q(me.y);
    if (!rec._lastPos) {
      rec.pos.push(cs, x, y);
      rec._estBytes += 14;
    } else {
      rec.pos.push(cs - rec._lastPos.cs, x - rec._lastPos.x, y - rec._lastPos.y);
      rec._estBytes += 9;
    }
    rec._lastPos = { cs: cs, x: x, y: y };
  }

  function sampleActors(rec, r, cs) {
    var iv = Math.round(100 / rec.actHz) * rec._dec;
    if (cs - rec._actCs < iv) return;
    rec._actCs = cs;
    var ds = null;
    try { ds = Array.isArray(r.defenders) ? r.defenders : null; } catch (_e) {}
    if (!ds) return;

    var frame = [], n = 0;
    for (var i = 0; i < ds.length; i++) {
      var d = ds[i];
      if (!d || typeof d._rpid !== 'number') continue;
      var slot = d._rpid;
      var x = q(d.x), y = q(d.y);
      var la = rec._lastAct[slot];
      if (la) frame.push(slot, x - la.x, y - la.y);
      else frame.push(slot, x, y);
      rec._lastAct[slot] = { x: x, y: y };
      n++;
    }
    rec.act.push(cs, n);
    for (var f = 0; f < frame.length; f++) rec.act.push(frame[f]);
    rec._estBytes += 10 + n * 9;

    // Budget guard. Halve the actor rate rather than cutting the raid short, so a long fight
    // degrades in smoothness instead of losing its ending.
    if (rec._estBytes > LIMITS.perReplayBytes * 0.8 && rec._dec < 8) rec._dec *= 2;
  }

  function outcomeOf(r) {
    try {
      if (r._outcome && OUTCOMES.indexOf(r._outcome) >= 0) return r._outcome;
      if (r.win) return 'extract';
      if ((r.hp | 0) <= 0) return 'wipe';
      if ((r.t || 0) <= 0) return 'timeout';
    } catch (_e) {}
    return 'surrender';
  }

  function finish(outcome) {
    var rec = REC;
    if (!rec || rec._ended) return null;
    rec._ended = true;
    DONERAID = rec._raid;                        // AK-REPLAY-EOR: this raid is closed for good
    rec.outcome = (OUTCOMES.indexOf(outcome) >= 0) ? outcome : 'surrender';
    rec.dur = Math.max(0, rec._cs) / 100;
    rec.kills = rec._kills | 0;
    pushEv(rec, Math.max(0, rec._cs), EV.END, OUTCOMES.indexOf(rec.outcome), rec.kills);
    // Hold the finished record BEFORE attempting to persist. finish() is normally reached from
    // inside observe(), so the caller never sees a return value; without this the recording would
    // be unreachable whenever AK_ECON is absent (headless harness, econ not yet loaded) and a whole
    // raid would silently evaporate. LAST is the handoff point for share/export too.
    LAST = rec;
    try { save(rec); } catch (_e) {}
    REC = null;
    return rec;
  }

  /* One observation. Idempotent on the RAID CLOCK: if RAID.t has not moved since the last call
   * this does nothing, so the rAF driver and an AK_SYSTEMS tick can both call it without ever
   * double-sampling. That is what makes the two drivers safe to run together. */
  function observe() {
    // AK-REPLAY-ACTIVE: a driving replay WRITES into window.RAID and AK_CTX.me, so recording during
    // playback would record the playback. Suspend, and never let it close the live recording either.
    if (activePlayback()) return false;
    var r = R();
    if (!r) {
      if (REC && !REC._ended) finish(REC._hp > 0 ? 'surrender' : 'wipe');
      return false;
    }
    var c = CTX(), me = ME(c);
    if (!me) return false;

    if (!REC || REC._raid !== r || REC._ended) {
      if (REC && !REC._ended) finish('surrender');
      // AK-REPLAY-EOR: do not re-open a raid we already closed, and never open one that is already
      // over. Both would produce a 0-duration replay that overwrites LAST and evicts the real one.
      if (r === DONERAID || r.over) return false;
      if (!begin(r, c)) return false;
    }
    var rec = REC;
    var cs = elapsedCs(r, rec._t0);
    if (cs <= rec._cs) {
      if (r.over) finish(outcomeOf(r));
      return false;
    }
    rec._cs = cs;
    scanEvents(rec, r, cs);
    samplePos(rec, me, cs);
    sampleActors(rec, r, cs);
    if (r.over) finish(outcomeOf(r));
    return true;
  }

  function startRecording() {
    var r = R();
    if (!r) return null;
    if (REC && !REC._ended) return REC;
    return begin(r, CTX());
  }
  function stopRecording(outcome) { return finish(outcome || 'surrender'); }
  function isRecording() { return !!(REC && !REC._ended); }

  /* ===================================================================== *
   * CODEC
   * ===================================================================== */
  function encode(rec) {
    if (!rec) return '';
    var out = {
      v: rec.v, id: rec.id, at: rec.at, posHz: rec.posHz, actHz: rec.actHz,
      dur: rec.dur, outcome: rec.outcome, kills: rec.kills,
      seed: rec.seed, protos: rec.protos, kinds: rec.kinds,
      pos: rec.pos, act: rec.act, ev: rec.ev
    };
    try { return JSON.stringify(out); } catch (_e) { return ''; }
  }
  function decode(str) {
    try {
      var o = (typeof str === 'string') ? JSON.parse(str) : str;
      if (!o || (o.v | 0) !== FMT) return null;
      if (!Array.isArray(o.pos) || !Array.isArray(o.act) || !Array.isArray(o.ev)) return null;
      return o;
    } catch (_e) { return null; }
  }
  function sizeOf(rec) { var s = encode(rec); return s ? s.length : 0; }

  /* ===================================================================== *
   * STORAGE -- capped, local, and ONLY through AK_ECON.mutateProfile.
   * Direct localStorage writes are banned in this repo (they caused a whole
   * class of save-loss bugs), so replays live on the profile like everything
   * else and ride the existing save path.
   * ===================================================================== */
  function rowsFrom(p) {
    var a = (p && p.replays);
    return Array.isArray(a) ? a : [];
  }
  function evict(rows) {
    // newest first, then trim by count and by total bytes. Pinned rows survive until nothing
    // else is left to drop.
    rows.sort(function (a, b) { return (b.at | 0) - (a.at | 0); });
    var keep = [], total = 0;
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var bytes = row.bytes | 0;
      if (keep.length >= LIMITS.maxReplays && !row.pin) continue;
      if (total + bytes > LIMITS.totalBytes && !row.pin) continue;
      keep.push(row); total += bytes;
    }
    return keep;
  }
  function save(rec) {
    var E = ECON();
    if (!E || !E.mutateProfile) return { ok: false, error: 'no-econ' };
    var blob = encode(rec);
    if (!blob) return { ok: false, error: 'encode' };
    if (blob.length > LIMITS.perReplayBytes) return { ok: false, error: 'too-big', bytes: blob.length };
    var row = {
      id: rec.id, at: rec.at | 0, dur: +(rec.dur || 0).toFixed(2),
      outcome: rec.outcome || '', kills: rec.kills | 0, bytes: blob.length, pin: 0, blob: blob
    };
    var ok = false;
    try {
      E.mutateProfile(function (p) {
        var rows = rowsFrom(p).filter(function (x) { return x && x.id !== row.id; });
        rows.push(row);
        p.replays = evict(rows);
        ok = true;
      });
    } catch (_e) { return { ok: false, error: 'mutate' }; }
    return { ok: ok, id: rec.id, bytes: blob.length };
  }
  function list() {
    var E = ECON();
    if (!E || !E.loadProfile) return [];
    var out = [];
    try {
      var rows = rowsFrom(E.loadProfile());
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        if (!r) continue;
        out.push({ id: r.id, at: r.at | 0, dur: +r.dur || 0, outcome: r.outcome || '', kills: r.kills | 0, bytes: r.bytes | 0, pin: !!r.pin });
      }
      out.sort(function (a, b) { return b.at - a.at; });
    } catch (_e) {}
    return out;
  }
  function load(id) {
    var E = ECON();
    if (!E || !E.loadProfile) return null;
    try {
      var rows = rowsFrom(E.loadProfile());
      for (var i = 0; i < rows.length; i++) if (rows[i] && rows[i].id === id) return decode(rows[i].blob);
    } catch (_e) {}
    return null;
  }
  function remove(id) {
    var E = ECON();
    if (!E || !E.mutateProfile) return false;
    var hit = false;
    try {
      E.mutateProfile(function (p) {
        var rows = rowsFrom(p);
        var next = rows.filter(function (x) { return !(x && x.id === id); });
        hit = next.length !== rows.length;
        p.replays = next;
      });
    } catch (_e) { return false; }
    return hit;
  }
  function pin(id, on) {
    var E = ECON();
    if (!E || !E.mutateProfile) return false;
    var hit = false;
    try {
      E.mutateProfile(function (p) {
        var rows = rowsFrom(p);
        for (var i = 0; i < rows.length; i++) if (rows[i] && rows[i].id === id) { rows[i].pin = on ? 1 : 0; hit = true; }
        p.replays = rows;
      });
    } catch (_e) { return false; }
    return hit;
  }
  function budget() {
    var rows = list(), used = 0;
    for (var i = 0; i < rows.length; i++) used += rows[i].bytes | 0;
    return { used: used, cap: LIMITS.totalBytes, count: rows.length, max: LIMITS.maxReplays, perReplay: LIMITS.perReplayBytes };
  }

  /* ===================================================================== *
   * PLAYBACK
   * Reconstruction walks the decoded log up to a target time and rebuilds the
   * exact state the recorder saw. Position tracks are sampled, so a time that
   * lands ON a sample returns that sample verbatim (no interpolation error);
   * a time between samples is linearly interpolated purely for smoothness.
   * ===================================================================== */

  // Expand the delta-encoded player track once, at open time.
  function expandPos(o) {
    var out = [], p = o.pos, cs = 0, x = 0, y = 0;
    for (var i = 0; i + 2 < p.length + 0; i += 3) {
      if (i === 0) { cs = p[0] | 0; x = p[1] | 0; y = p[2] | 0; }
      else { cs += p[i] | 0; x += p[i + 1] | 0; y += p[i + 2] | 0; }
      out.push({ cs: cs, x: x, y: y });
    }
    return out;
  }

  // Expand the delta-encoded actor track into absolute per-frame slot positions.
  function expandAct(o) {
    var frames = [], a = o.act, i = 0, last = {};
    while (i + 1 < a.length) {
      var cs = a[i] | 0, n = a[i + 1] | 0;
      i += 2;
      var slots = {};
      for (var k = 0; k < n && i + 2 < a.length; k++) {
        var slot = a[i] | 0, dx = a[i + 1] | 0, dy = a[i + 2] | 0;
        i += 3;
        var la = last[slot];
        var x = la ? la.x + dx : dx;
        var y = la ? la.y + dy : dy;
        last[slot] = { x: x, y: y };
        slots[slot] = { x: x, y: y };
      }
      frames.push({ cs: cs, slots: slots });
    }
    return frames;
  }

  function lastAtOrBefore(arr, cs) {
    // binary search: highest index with arr[i].cs <= cs
    var lo = 0, hi = arr.length - 1, best = -1;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (arr[mid].cs <= cs) { best = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return best;
  }

  function open(recOrId) {
    var o = (typeof recOrId === 'string') ? load(recOrId) : decode(recOrId);
    if (!o) return null;

    var posT = expandPos(o);
    var actT = expandAct(o);
    var durCs = Math.max(
      q((o.dur || 0) * 100),
      posT.length ? posT[posT.length - 1].cs : 0,
      actT.length ? actT[actT.length - 1].cs : 0
    );

    var cur = 0, playing = false, spd = 1;
    var pool = {};                                  // slot -> entity object (stable identity)
    var camS = { free: false, x: 0, y: 0, zoom: 1 };

    function protoFor(idx) { return o.protos[idx] || { name: '?', role: '', maxHp: 1, r: 18, rarity: '', lvl: 1, boss: 0, ranged: 0, spd: 0, tier: 0 }; }

    // Rebuild the full state at cs by replaying events then applying the sampled tracks.
    function stateAt(cs) {
      cs = clamp(q(cs), 0, durCs);
      var sd = o.seed || {};
      var st = {
        cs: cs, t: (sd.t0 ? sd.t0 : 0) - cs / 100,
        px: 0, py: 0, wave: 0, kills: 0, hp: 0, hpMax: (sd.hpMax | 0) || 100, bag: {}, secured: 0,
        zi: sd.zi0 | 0, entities: [], bySlot: {}, outcome: ''
      };
      st.hp = (typeof sd.hp0 === 'number') ? sd.hp0 : 100;

      // --- events up to cs ---
      var live = {};
      var ev = o.ev;
      for (var i = 0; i + 3 < ev.length + 0; i += 4) {
        var ecs = ev[i] | 0;
        if (ecs > cs) break;
        var code = ev[i + 1] | 0, a = ev[i + 2] | 0, b = ev[i + 3] | 0;
        if (code === EV.SPAWN) {
          var pr = protoFor(b);
          live[a] = { slot: a, proto: pr, hp: pr.maxHp, dead: false, boss: !!pr.boss, zi: 0 };
        } else if (code === EV.WAVE) { st.wave = a; }
        else if (code === EV.DIST) { st.zi = a; }
        else if (code === EV.AZI) { if (live[a]) live[a].zi = b; }
        else if (code === EV.HIT) { if (live[a]) live[a].hp = Math.max(0, live[a].hp - b); }
        else if (code === EV.KILL) { if (live[a]) { live[a].dead = true; live[a].hp = 0; } st.kills++; }
        else if (code === EV.LOOT) { var kn = o.kinds[a]; if (kn) st.bag[kn] = (st.bag[kn] | 0) + b; }
        else if (code === EV.SECURE) { st.secured = b; for (var bk in st.bag) if (Object.prototype.hasOwnProperty.call(st.bag, bk)) st.bag[bk] = 0; }
        else if (code === EV.PHURT) { st.hp = b; }
        else if (code === EV.END) { st.outcome = OUTCOMES[a] || ''; }
      }

      // --- player position ---
      if (posT.length) {
        var pi = lastAtOrBefore(posT, cs);
        if (pi < 0) { st.px = posT[0].x; st.py = posT[0].y; }
        else if (posT[pi].cs === cs || pi === posT.length - 1) { st.px = posT[pi].x; st.py = posT[pi].y; }
        else {
          var p0 = posT[pi], p1 = posT[pi + 1];
          var f = (p1.cs === p0.cs) ? 0 : (cs - p0.cs) / (p1.cs - p0.cs);
          st.px = p0.x + (p1.x - p0.x) * f;
          st.py = p0.y + (p1.y - p0.y) * f;
        }
      }

      // --- actor positions ---
      var fi = actT.length ? lastAtOrBefore(actT, cs) : -1;
      var f0 = (fi >= 0) ? actT[fi] : null;
      var f1 = (fi >= 0 && fi < actT.length - 1) ? actT[fi + 1] : null;
      var lerpF = 0;
      if (f0 && f1 && f1.cs !== f0.cs && f0.cs !== cs) lerpF = clamp((cs - f0.cs) / (f1.cs - f0.cs), 0, 1);

      for (var slotKey in live) {
        if (!Object.prototype.hasOwnProperty.call(live, slotKey)) continue;
        var L = live[slotKey];
        var s0 = f0 ? f0.slots[L.slot] : null;
        if (!s0) continue;                                   // not yet in a sampled frame
        var ex = s0.x, ey = s0.y;
        if (lerpF > 0 && f1) {
          var s1 = f1.slots[L.slot];
          if (s1) { ex = s0.x + (s1.x - s0.x) * lerpF; ey = s0.y + (s1.y - s0.y) * lerpF; }
        }
        var e = ent(L, ex, ey);
        st.entities.push(e);
        st.bySlot[L.slot] = e;
      }
      return st;
    }

    // Pooled entity objects. The renderer keeps per-entity transient state, so identity has to be
    // stable across frames or a replay flickers where a live raid does not.
    function ent(L, x, y) {
      var e = pool[L.slot];
      if (!e) {
        e = pool[L.slot] = {
          x: 0, y: 0, hx: 0, hy: 0, zi: 0, r: L.proto.r || 18,
          hp: L.proto.maxHp, maxHp: L.proto.maxHp, spd: L.proto.spd || 88,
          atkT: 0, wind: 0, rwind: 0, ranged: !!L.proto.ranged,
          name: L.proto.name, dead: false, lvl: L.proto.lvl, rarity: L.proto.rarity,
          role: L.proto.role, _rpid: L.slot, _replay: true
        };
        if (L.proto.boss) { e.boss = true; e.tier = L.proto.tier || 1; e.phase = 1; }
      }
      e.x = x; e.y = y; e.hx = x; e.hy = y;
      e.hp = L.hp; e.dead = !!L.dead;
      e.zi = L.zi | 0;                           // AK-REPLAY-ZI: index.html:2265 skips any e.zi!==RAID.zi
      return e;
    }

    /* Write the reconstructed state into the LIVE globals, so the raid renderer that already
     * ships draws the replay. This is the whole point: one renderer, not two. Pinning _wave also
     * stops raidwaves from spawning a fresh wave on top of a replay if the registry ever starts
     * ticking during raids. */
    function applyTo(raid, c) {
      var st = stateAt(cur);
      c = c || CTX();
      var me = ME(c);
      if (me) { me.x = st.px; me.y = st.py; me.tx = null; me.ty = null; me.vx = 0; me.vy = 0; }
      if (raid) {
        raid.t = st.t;
        raid.hp = st.hp;
        raid.kills = st.kills;
        raid.bag = st.bag;
        raid.defenders = st.entities;
        raid._wave = st.wave;
        raid._replay = true;
        // AK-REPLAY-ZI: the draw path filters entities on RAID.zi (index.html:2265) and reads
        // RAID.zone.buildings (index.html:2221), so both have to move together exactly the way
        // index.html:1588 moves them live. Guarded: a raid with no zones keeps whatever it had.
        raid.zi = st.zi;
        try { if (raid.zones && raid.zones[st.zi]) raid.zone = raid.zones[st.zi]; } catch (_e) {}
      }
      var cam = CAM(c);
      if (cam && camS.free) { cam.x = camS.x; cam.y = camS.y; }
      return st;
    }

    function step(dt) {
      if (!playing) return cur / 100;
      cur = clamp(cur + q((dt || 0) * 100 * spd), 0, durCs);
      if (cur >= durCs) playing = false;
      return cur / 100;
    }

    var camera = {
      free: function (on) { if (arguments.length) camS.free = !!on; return camS.free; },
      focus: function (x, y) { camS.free = true; camS.x = q(x); camS.y = q(y); return camS; },
      pan: function (dx, dy) { camS.free = true; camS.x += q(dx); camS.y += q(dy); return camS; },
      zoom: function (z) { if (arguments.length) camS.zoom = clamp(+z || 1, 0.5, 3); return camS.zoom; },
      follow: function () { camS.free = false; return camS; },
      get: function () { return { free: camS.free, x: camS.x, y: camS.y, zoom: camS.zoom }; }
    };

    return {
      id: o.id,
      raw: o,
      seed: o.seed,
      play: function () { playing = true; return true; },
      pause: function () { playing = false; return true; },
      toggle: function () { playing = !playing; return playing; },
      playing: function () { return playing; },
      seek: function (sec) { cur = clamp(q((sec || 0) * 100), 0, durCs); return cur / 100; },
      time: function () { return cur / 100; },
      duration: function () { return durCs / 100; },
      setSpeed: function (s) { spd = clamp(+s || 1, 0.1, 8); return spd; },
      speed: function () { return spd; },
      step: step,
      state: function () { return stateAt(cur); },
      stateAt: function (sec) { return stateAt(q((sec || 0) * 100)); },
      applyTo: applyTo,
      camera: camera,
      _closed: false,
      close: function () { playing = false; pool = {}; this._closed = true; return true; }
    };
  }

  /* ===================================================================== *
   * HIGHLIGHT EXPORT -> systems/viral.js
   *
   * viral.js is the only acquisition channel this project has, so the handoff
   * has to be usable the day it lands, not after viral.js changes.
   *
   * WHAT VIRAL.JS NEEDS TODAY (viral.js:215 shareMoment(kind, meta)):
   *   kind : one of win | killstreak | raid_win | chest | levelup
   *          (the exact MEDIA table keys at viral.js:203; anything else falls back to MEDIA.win)
   *   meta : { title, sub, handle, cinematic } -- those FOUR and no others are read
   *          (viral.js:220-223). meta.stat below is extra context for a future overlay and is
   *          deliberately ignored by viral.js today; it costs nothing and breaks nothing.
   * It paints title/sub into the 9:16 lower third (viral.js:131-146), records ~6000ms off a
   * <video> whose src is meta.cinematic (falling back to its own MEDIA table),
   * and stamps the ?ref= invite from AK_VIRAL.inviteUrl(kind). So
   * exportHighlight returns a meta object in EXACTLY that shape and
   * shareHighlight passes it straight through. Zero viral.js change required
   * for a working, shareable, ref-tagged clip.
   *
   * WHAT VIRAL.JS WOULD NEED TO COMPOSITE THE ACTUAL REPLAY PIXELS instead of
   * the canned cinematic is one line, documented in the module return below.
   * ===================================================================== */

  // Pick the moment worth showing: boss kill wins, then the last kill, then extraction, then end.
  function anchorOf(o) {
    var ev = o.ev, bossSlot = -1, lastKill = -1, lastSecure = -1, bossKill = -1, endCs = 0;
    for (var i = 0; i + 3 < ev.length + 0; i += 4) {
      var cs = ev[i] | 0, code = ev[i + 1] | 0, a = ev[i + 2] | 0;
      if (code === EV.BOSS) bossSlot = a;
      else if (code === EV.KILL) { lastKill = cs; if (a === bossSlot && bossSlot >= 0) bossKill = cs; }
      else if (code === EV.SECURE) lastSecure = cs;
      else if (code === EV.END) endCs = cs;
    }
    if (bossKill >= 0) return { cs: bossKill, why: 'boss_kill' };
    if (lastKill >= 0) return { cs: lastKill, why: 'kill' };
    if (lastSecure >= 0) return { cs: lastSecure, why: 'extract' };
    return { cs: endCs, why: 'end' };
  }

  function kindFor(o, why) {
    if (why === 'boss_kill') return 'raid_win';
    if (o.outcome === 'extract') return 'raid_win';
    if ((o.kills | 0) >= 5) return 'killstreak';
    return 'win';
  }

  function exportHighlight(recOrId, opts) {
    opts = opts || {};
    var o = (typeof recOrId === 'string') ? load(recOrId) : decode(recOrId);
    if (!o) return null;

    var anchor = opts.atSec != null ? { cs: q(opts.atSec * 100), why: 'manual' } : anchorOf(o);
    var pre = (opts.preSec != null ? +opts.preSec : HL.preSec) * 100;
    var post = (opts.postSec != null ? +opts.postSec : HL.postSec) * 100;
    var durCs = q((o.dur || 0) * 100);
    var t0 = clamp(anchor.cs - pre, 0, durCs);
    var t1 = clamp(anchor.cs + post, t0, durCs);

    // clip the event track to the window so a consumer does not have to carry the whole raid
    var clipped = [];
    for (var i = 0; i + 3 < o.ev.length + 0; i += 4) {
      var cs = o.ev[i] | 0;
      if (cs < t0) continue;
      if (cs > t1) break;
      clipped.push(cs - t0, o.ev[i + 1] | 0, o.ev[i + 2] | 0, o.ev[i + 3] | 0);
    }

    var kind = opts.kind || kindFor(o, anchor.why);
    var kills = o.kills | 0;
    var title = opts.title || (anchor.why === 'boss_kill' ? 'BOSS DROPPED'
      : o.outcome === 'extract' ? 'TAKEOVER'
      : kills >= 5 ? 'DOG GOD' : 'ON THE BLOCK');
    var th = 0;
    try { th = (o.seed && o.seed.rp && o.seed.rp.th) | 0; } catch (_e) {}
    var sub = opts.sub || ('$BCARDD - ' + kills + ' down' + (th ? ' on a TH' + th + ' base' : ''));

    var ref = '';
    try { if (global.AK_VIRAL && global.AK_VIRAL.inviteUrl) ref = global.AK_VIRAL.inviteUrl(kind); } catch (_e) {}

    return {
      replayId: o.id,
      kind: kind,
      // EXACTLY viral.js shareMoment meta shape. Pass straight through, no adapter.
      meta: {
        title: title,
        sub: sub,
        handle: opts.handle || '',
        cinematic: opts.cinematic || '',      // '' lets viral.js pick from its own MEDIA table
        stat: kills
      },
      window: { t0Sec: t0 / 100, t1Sec: t1 / 100, durMs: Math.round((t1 - t0) * 10) },
      anchor: { atSec: anchor.cs / 100, why: anchor.why },
      // Everything a renderer needs to drive the window through the normal playback path.
      playback: { replayId: o.id, seekSec: t0 / 100, speed: 1 },
      events: clipped,
      ref: ref
    };
  }

  // Real call into the shipped viral.js API (viral.js:349 exports shareMoment).
  function shareHighlight(h) {
    if (!h) return false;
    try {
      if (global.AK_VIRAL && typeof global.AK_VIRAL.shareMoment === 'function') {
        global.AK_VIRAL.shareMoment(h.kind, h.meta);
        return true;
      }
    } catch (_e) {}
    return false;
  }

  /* ===================================================================== *
   * ACTIVE PLAYBACK HANDLE -- AK-REPLAY-ACTIVE 2026-07-18
   * index.html owns the raid loop and is locked to another workflow, so the hook it needs has to
   * be ONE line with no local variable for it to manage. This module holds the handle instead:
   * playActive(id) opens + registers + plays, activePlayback() hands it back, and the raid loop
   * asks "is a replay driving right now?" and calls step + applyTo instead of akRaidStep. Recording
   * is suspended while a replay drives, so a playback never records itself.
   * ===================================================================== */
  var ACTIVE = null;
  function activePlayback() { return (ACTIVE && !ACTIVE._closed) ? ACTIVE : null; }
  function playActive(recOrId) {
    var pb = open(recOrId);
    if (!pb) return null;
    closeActive();
    ACTIVE = pb;
    pb.play();
    return pb;
  }
  function closeActive() {
    if (ACTIVE) { try { ACTIVE.close(); } catch (_e) {} }
    ACTIVE = null;
    return true;
  }

  /* ===================================================================== *
   * DRIVERS
   * The registry path is registered for the day raids are wired into it. The
   * rAF path is what actually runs today, because index.html:2390 gates
   * AK_SYSTEMS.tickAll to state==='IN_ZONE' and index.html:2392 runs raids
   * through akRaidStep instead. Both call observe(), which is idempotent on
   * the raid clock, so running both is safe.
   * ===================================================================== */
  var installed = false;
  function install() {
    if (installed) return false;
    installed = true;
    try {
      if (typeof global.requestAnimationFrame !== 'function') return false;
      var loop = function () {
        try { observe(); } catch (_e) {}
        try { global.requestAnimationFrame(loop); } catch (_e2) {}
      };
      global.requestAnimationFrame(loop);
      return true;
    } catch (_e) { return false; }
  }

  var api = {
    id: ID,
    init: function () { try { install(); } catch (_e) {} },
    onTick: function () { try { observe(); } catch (_e) {} }
  };
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(api); } catch (_e) {}

  global.AK_REPLAY = {
    FMT: FMT, EV: EV, LIMITS: LIMITS, OUTCOMES: OUTCOMES,
    install: install, observe: observe,
    startRecording: startRecording, stopRecording: stopRecording, isRecording: isRecording,
    encode: encode, decode: decode, sizeOf: sizeOf,
    save: save, list: list, load: load, remove: remove, pin: pin, budget: budget,
    open: open,
    // AK-REPLAY-ACTIVE: the one-line hook surface for the locked raid loop.
    playActive: playActive, activePlayback: activePlayback, closeActive: closeActive,
    exportHighlight: exportHighlight, shareHighlight: shareHighlight, anchorOf: anchorOf,
    // The raid that just ended. Available even when AK_ECON is absent, so a caller can encode,
    // share or export a highlight without a round trip through storage.
    lastRecording: function () { return LAST; },
    // exposed for tests + a future server re-sim harness
    _elapsedCs: elapsedCs, _current: function () { return REC; }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_REPLAY;
  // globalThis, NOT `this`, for the headless case. At node module scope `this` is module.exports,
  // so the `this` idiom would bind the host object to an empty object and every global read here
  // (RAID, AK_CTX, AK_ECON, AK_VIRAL) would silently see undefined. raidscene.js:521 already uses
  // this form; raidwaves.js does not, which is why it cannot be state-driven from a node harness.
})(typeof window !== 'undefined' ? window : globalThis);
