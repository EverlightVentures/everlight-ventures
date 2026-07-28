/* game/systems/encounters.js -- AK_SYSTEMS "encounters" wave (wave 3).
   ------------------------------------------------------------------------------
   WILD DOG SYMBOL-ENCOUNTERS (Pokemon DS/GO bible -> AK_LIVING_WORLD).
   Visible, AVOIDABLE wild dogs -- REAL cards.json units, BY NAME -- roam each
   district. Each carries a DERIVED sensor package {detectR, visionR, strikeR,
   chaseLeashR} (synthesis sec 10 "Wild Stray Sensor Package"). Walk into one ->
   it triggers an encounter:
     - LEASH capture mini-game (Canvas2D overlay, ctx.overlay.open): wear the
       stray's stamina below the LEASH-ZONE threshold, then sling a leash. Catch
       below the HP/stamina threshold -> a soulbound copy via AK_ECON.addCopy.
     - or STREET FIGHT -> ctx.battle.launch({mode:'encounter', nemesis:<card>}) ->
       a short single-board battle (engine convoyMode=false, NEVER a fork).
   chaseLeashR is the ANTI-GRIEF give-up radius: a stray can never chase forever.
   Mythics NEVER roam; spawns weight Common/Rare. Crypto/parity law: capture grants
   ONLY a soft, non-tradeable copy -- no gems, no $BCARDD/ALK anywhere.

   CONTRACT COMPLIANCE
   - Self-registers into window.AK_SYSTEMS; edits NO shared file.
   - All player state via window.AK_ECON behind falsy-default fields:
       p.captures {} (cardName -> capture count, soulbound dex ledger)
       p.encSeed  0  (deterministic spawn cursor)
   - Headless-safe: bails when AK_SYSTEMS is absent; no top-level DOM/localStorage;
     new Image() only at runtime inside dogImg().
   - Roamers via ctx.world.addRoamer (host auto-updates + auto-draws + culls them).
   ------------------------------------------------------------------------------ */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;           // hub-only; the battler page has no registry -> skip.

  // ============================ TUNABLES =====================================
  var MAX_PER_ZONE  = 3;        // visible strays per district
  var MAX_TOTAL     = 14;       // hard cap across all zones (prune off-screen strays)
  var SPAWN_MIN     = 3.5;      // seconds between spawn attempts (random)
  var SPAWN_MAX     = 7.5;
  var SPAWN_AWAY    = 220;      // never spawn within this px of the player
  var THROWS        = 4;        // leash throws per encounter (out -> the stray bolts)
  var CAP_THRESHOLD = 0.45;     // stamina fraction below which the catch gets real traction
  var RARITY        = ['Common', 'Rare', 'Epic', 'Legendary', 'Mythic'];
  // rarity -> base catch multiplier (rarer = harder; Mythics never roam so 0)
  var CATCH_MOD = { Common: 1.0, Rare: 0.82, Epic: 0.6, Legendary: 0.42, Mythic: 0 };
  // rarity -> spawn weight (toward Common/Rare; Mythics excluded entirely)
  var SPAWN_W   = { Common: 60, Rare: 28, Epic: 9, Legendary: 3, Mythic: 0 };

  // ---- THE LONG FUSE + THE MERCY (Tarantino standoff + del Toro mercy) -------
  // A wild encounter no longer slot-pulls straight into a leash sling. It opens
  // on a 2-3 beat STANDOFF: the stray trash-talks, a tension meter burns, and the
  // player commits to LEASH (de-escalate -> the existing capture mini-game, harder
  // catch, NO karma) or STRIKE (fight -> the battler, easier/faster, COSTS karma).
  // Reading more dialogue improves LEASH odds AND raises the STRIKE payoff -- the
  // conversation is the scene, the catch/fight is the payoff. After the stray is
  // beaten below the LEASH ZONE (CAP_THRESHOLD), a MERCY choice fires: SPARE (joins
  // soulbound, loyalty EARNED over time) or BREAK (faster/guaranteed, permanent
  // trust penalty). Capture math (THROWS + CAP_THRESHOLD + catch chance) is intact;
  // we only add a SCENE+CHOICE in front and a soul choice after.
  var MAX_BEATS              = 3;     // trash-talk beats in the standoff (the long fuse)
  var TENSION_RATE           = 0.16;  // tension meter fill per second while they square up
  var TENSION_PER_READ       = 0.28;  // jump each time you READ THE ROOM (let it talk longer)
  var TENSION_TICK_STEP      = 0.12;  // a tick sfx every this much tension (the fuse burning)
  var RATTLE_PER_BEAT        = 14;    // each beat READ rattles the stray -> starts nearer the LEASH ZONE
  var LEASH_RATIO_PER_BEAT   = 0.12;  // each beat READ also nudges the real catch ratio up (better odds)
  var STRIKE_PAYOFF_PER_BEAT = 0.2;   // each beat READ raises the STRIKE fight payoff (handed to battler)
  var STRIKE_KARMA_COST      = 8;     // STRIKE spends district karma; LEASH costs none
  // gritty gangland standoff lines -- faction-flavored, escalating across the beats.
  // {breed} swaps in the stray's breed. NO em-dashes anywhere.
  var STANDOFF_LINES = {
    boneguard: [
      "You lost, pup? This block belongs to the Boneguard.",
      "I buried tougher mutts than you under that fence.",
      "Last warning. Step off, or you join the bone pile."
    ],
    zoomie: [
      "Heh. You really think you can catch me?",
      "Blink twice and I am three alleys gone, slowpoke.",
      "Tick tock. My patience just ran all the way out."
    ],
    leashbreak: [
      "No collar ever held me. Yours sure won't.",
      "We don't kneel out here. We bite the hand.",
      "Come closer. I'll show you what a free dog does."
    ],
    k9: [
      "Threat logged. You walked right into my grid.",
      "My sensors clocked you a block back. Bad move.",
      "Recalibrating. Termination protocol warming up."
    ],
    generic: [
      "This alley is mine, {breed}. Keep walking.",
      "You smell like somebody who picks the wrong fights.",
      "Alright. You went and asked for this one."
    ]
  };

  // ============================ MODULE STATE =================================
  var S = { pool: null, seed: 1, spawnCD: 1.5, lastZone: '', engaging: false, sinceSave: 0 };
  var imgCache = {};

  function profile(ctx) { try { return ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function playSfx(n) { try { if (global.AK && global.AK.playSfx) global.AK.playSfx(n); } catch (_) {} }
  // duck the district ambient bed under a beat (the districtmusic.js duck() hook).
  function duckBed(ms) { try { if (global.AKDistrictMusic && global.AKDistrictMusic.duck) global.AKDistrictMusic.duck(ms || 320); } catch (_) {} }

  // ---- deterministic spawn RNG (mulberry32 over the persisted encSeed cursor) ----
  function nextRand() {
    S.seed = (S.seed + 0x6D2B79F5) | 0;
    var t = S.seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  function persistSeed(ctx) {
    try { if (ctx.econ) ctx.econ.mutateProfile(function (p) { p.encSeed = S.seed | 0; }); } catch (_) {}
  }

  // ---- art resolver bridge (canon.js akCardArtRel; cached <img> per card) ----
  function dogImg(card) {
    var key = card.name, im = imgCache[key];
    if (im) return im;
    im = new Image();
    try {
      var rel = (global.akCardArtRel) ? global.akCardArtRel(card) : '';
      if (rel) im.src = 'assets/' + rel;          // hub page base = 'assets/'
    } catch (_) {}
    im.onerror = function () { try { if (global.akImgErr) global.akImgErr(im); } catch (_) {} };
    imgCache[key] = im;
    return im;
  }
  function rarityCol(r) {
    try { if (global.AK && global.AK.RARITY_COL && global.AK.RARITY_COL[r]) return global.AK.RARITY_COL[r]; } catch (_) {}
    return ({ Common: '#b9c2cf', Rare: '#5ad0ff', Epic: '#c08bff', Legendary: '#ffce6b', Mythic: '#ff7ad9' })[r] || '#c9a84c';
  }

  // ---- canon faction palette (mirror of engine FACTION_COL) for the canon
  // fallback only; engine cards already carry .color so this is never read for them.
  var FCOL = { boneguard_crew: '#C9772E', zoomie_syndicate: '#FF2E88', leashbreak_tactix: '#7B5CFF', k9_circuitry: '#00E0C0' };
  // Normalize a raw canon.js card to the few fields the roamer + capture screen read.
  function normCanon(c) {
    return {
      name: c.name, breed: c.breed, rarity: c.rarity, cardNumber: c.cardNumber,
      cost: (typeof c.cost === 'number') ? c.cost : 4,
      speed: (typeof c.move_speed === 'number') ? c.move_speed : 1,
      isMythic: !!c.isMythic, factionName: c.class || '',
      color: FCOL[c.factionId] || '#c9a84c', type: 'troop'
    };
  }

  // ============================ SPAWN POOL ===================================
  // Build ONCE from the live 106-card index. Reuse cards BY NAME; never invent.
  // Primary source = ctx.cards() (AK.getCards()). The hub (index.html) currently
  // loads only economy.js, so AK may be absent and ctx.cards() empty -- in that
  // case fall back to the raw canon roster (window.CANON_CARDS from canon.js).
  // See the returned integration note: the hub should load canon.js so the art
  // resolver (akCardArtRel) + this pool resolve REAL units.
  function buildPool(ctx) {
    var pool = [];
    var cards = (ctx.cards && ctx.cards()) || {};
    for (var k in cards) {
      var c = cards[k];
      if (!c || c.type === 'spell' || c.isMythic) continue;   // no spells, no Mythics roaming
      var w = SPAWN_W[c.rarity] || 0;
      if (w <= 0) continue;
      pool.push({ card: c, w: w });
    }
    if (!pool.length && global.CANON_CARDS && global.CANON_CARDS.length) {
      for (var i = 0; i < global.CANON_CARDS.length; i++) {
        var cc = global.CANON_CARDS[i];
        if (!cc || cc.isMythic) continue;                     // CANON_CARDS are all troops; spells live in CANON_SPELLS
        var w2 = SPAWN_W[cc.rarity] || 0;
        if (w2 <= 0) continue;
        pool.push({ card: normCanon(cc), w: w2 });
      }
    }
    return pool;
  }
  function pickCard() {
    var pool = S.pool; if (!pool || !pool.length) return null;
    var tot = 0, i;
    for (i = 0; i < pool.length; i++) tot += pool[i].w;
    var x = nextRand() * tot;
    for (i = 0; i < pool.length; i++) { x -= pool[i].w; if (x < 0) return pool[i].card; }
    return pool[pool.length - 1].card;
  }

  // ---- DERIVED sensor package (synthesis sec 10) ----------------------------
  // Larger/rarer/pricier dogs notice you sooner and roam a wider leash; chase
  // speed is ALWAYS < the player's me.spd (300) so every stray is outrunnable.
  function derive(card) {
    var ri = Math.max(0, RARITY.indexOf(card.rarity));
    var cost = (typeof card.cost === 'number') ? card.cost : (card.canonCost || 4);
    var spd  = (typeof card.speed === 'number') ? card.speed : 1;
    var r = 15 + ri * 2;                                       // body radius
    return {
      r: r,
      detectR: clamp(95 + cost * 4 + ri * 6, 90, 200),         // commits to the chase
      visionR: clamp(95 + cost * 4 + ri * 6, 90, 200) + 60,    // "spots you" (suspicion)
      strikeR: r + 18,                                          // contact -> encounter fires
      chaseLeashR: clamp(270 + cost * 5, 260, 360),            // ANTI-GRIEF give-up radius from home
      chaseSpd: clamp(95 + ri * 12 + spd * 6, 90, 175),        // < player speed (300)
      wanderSpd: 38 + ri * 3
    };
  }

  // ============================ ROAMER LIFECYCLE =============================
  function countWildInZone(ctx, zone) {
    var rs = ctx.world.roamers(), n = 0;
    for (var i = 0; i < rs.length; i++) if (rs[i]._enc && rs[i].zone === zone) n++;
    return n;
  }
  function totalWild(ctx) {
    var rs = ctx.world.roamers(), n = 0;
    for (var i = 0; i < rs.length; i++) if (rs[i]._enc) n++;
    return n;
  }
  function pruneIfNeeded(ctx) {
    if (totalWild(ctx) < MAX_TOTAL) return;
    var rs = ctx.world.roamers();
    for (var i = 0; i < rs.length; i++) {           // drop the first stray that is NOT in the active zone
      if (rs[i]._enc && rs[i].zone !== ctx.zoneId) { ctx.world.removeRoamer(rs[i]); return; }
    }
  }
  function spawnWild(ctx) {
    if (global.AKKarma && global.AKKarma.rollEncounter) {  // KARMA HOOK (deep-dive Part 3): friendly/hostile branch
      var _ke = global.AKKarma.rollEncounter(ctx.zoneId, ctx);
      if (_ke && _ke.kind !== 'hostile') {
        if (_ke.kind !== 'nothing') { try { global.AKKarma.spawnFriendly(ctx.zoneId, ctx, _ke); } catch (_e) {} }
        return;
      }
    }
    var card = pickCard(); if (!card) return;
    var d = derive(card);
    var WW = ctx.world.WORLD_W, WH = ctx.world.WORLD_H, x = 0, y = 0, ok = false, tries = 0;
    while (!ok && tries++ < 12) {                    // place away from the player, inside bounds
      x = 60 + nextRand() * (WW - 120);
      y = 60 + nextRand() * (WH - 120);
      if (ctx.world.distToMe(x, y) > SPAWN_AWAY) ok = true;
    }
    if (!ok) return;
    ctx.world.addRoamer({
      _enc: true, id: 'wild_' + card.cardNumber + '_' + (Date.now() % 100000), zone: ctx.zoneId,
      x: x, y: y, r: d.r, card: card, sens: d, face: 1,
      home: { x: x, y: y }, state: 'wander', wt: 0, tx: x, ty: y,
      scanT: 0, alert: 0, cool: 1.0, fleeT: 0, dead: false,
      update: roamerUpdate, draw: roamerDraw
    });
    if (++S.sinceSave >= 5) { persistSeed(ctx); S.sinceSave = 0; }
  }

  function moveToward(self, tx, ty, step, ctx) {
    var dx = tx - self.x, dy = ty - self.y, m = Math.hypot(dx, dy);
    if (m > 0.001) { self.x += dx / m * step; self.y += dy / m * step; self.face = dx < 0 ? -1 : 1; }
    self.x = clamp(self.x, 24, ctx.world.WORLD_W - 24);
    self.y = clamp(self.y, 24, ctx.world.WORLD_H - 24);
  }

  // host calls this once per rAF (only IN_ZONE && !interiorOpen && !overlay)
  function roamerUpdate(dt, self, ctx) {
    if (self.dead) return;
    if (self.cool > 0) self.cool -= dt;
    var d = self.sens;
    var dist = ctx.world.distToMe(self.x, self.y);

    // 5Hz aggro rescan (synthesis perf note: don't flip state per-frame)
    self.scanT -= dt;
    if (self.scanT <= 0) {
      self.scanT = 0.2;
      if (self.state !== 'flee') {
        var distHome = Math.hypot(self.x - self.home.x, self.y - self.home.y);
        if (dist <= d.detectR && self.cool <= 0) self.state = 'chase';
        else if (self.state === 'chase') {
          if (distHome > d.chaseLeashR || dist > d.visionR * 1.5) self.state = 'flee';   // ANTI-GRIEF give-up
        } else if (dist <= d.visionR) self.alert = Math.max(self.alert, 0.6);            // suspicious "?"
      }
    }
    if (self.alert > 0) self.alert -= dt * 0.5;

    if (self.state === 'chase') {
      self.alert = 1;
      moveToward(self, ctx.me.x, ctx.me.y, d.chaseSpd * dt, ctx);
      if (dist <= d.strikeR && !S.engaging && self.cool <= 0) startEncounter(self, ctx);
    } else if (self.state === 'flee') {
      self.fleeT += dt;
      moveToward(self, self.home.x, self.home.y, d.chaseSpd * 0.8 * dt, ctx);
      if (Math.hypot(self.x - self.home.x, self.y - self.home.y) < 36 || self.fleeT > 6) { self.state = 'wander'; self.fleeT = 0; }
    } else { // wander -- gentle drift around home (Math.random, not the spawn cursor)
      self.wt -= dt;
      if (self.wt <= 0 || Math.hypot(self.x - self.tx, self.y - self.ty) < 14) {
        self.wt = 2 + Math.random() * 3;
        self.tx = clamp(self.home.x + (Math.random() - 0.5) * 260, 50, ctx.world.WORLD_W - 50);
        self.ty = clamp(self.home.y + (Math.random() - 0.5) * 260, 50, ctx.world.WORLD_H - 50);
      }
      moveToward(self, self.tx, self.ty, d.wanderSpd * dt, ctx);
    }
  }

  // host calls this once per rAF (g = the hub canvas 2D ctx; auto-culled off-screen)
  function roamerDraw(g, self, ctx) {
    var X = ctx.world.wx(self.x), Y = ctx.world.wy(self.y), r = self.r;
    g.save();
    // ground shadow
    g.globalAlpha = 0.35; g.fillStyle = '#000';
    g.beginPath(); g.ellipse(X, Y + r * 0.8, r * 0.9, r * 0.4, 0, 0, 6.2832); g.fill();
    g.globalAlpha = 1;
    // body: real card art if loaded, else a faction-color token w/ breed initial
    var im = dogImg(self.card), drew = false;
    if (im && im.complete && im.naturalWidth > 0) {
      g.save();
      g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.closePath(); g.clip();
      try { g.drawImage(im, X - r, Y - r, r * 2, r * 2); drew = true; } catch (_) {}
      g.restore();
    }
    if (!drew) {
      g.fillStyle = self.card.color || '#c9a84c';
      g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.fill();
      g.fillStyle = '#0c0a08'; g.font = '900 ' + Math.round(r * 1.1) + 'px Inter,system-ui';
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText((self.card.breed || self.card.name || '?').charAt(0).toUpperCase(), X, Y + 1);
    }
    // ring -- gold idle, red when chasing
    g.lineWidth = 2; g.strokeStyle = self.state === 'chase' ? '#ff5a4d' : 'rgba(201,168,76,.85)';
    g.beginPath(); g.arc(X, Y, r + 2, 0, 6.2832); g.stroke();
    // name tag
    g.font = '800 10px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    var nm = self.card.name, tw = g.measureText(nm).width + 10;
    g.fillStyle = 'rgba(8,8,12,.72)'; g.fillRect(X - tw / 2, Y - r - 18, tw, 13);
    g.fillStyle = '#e8d9a8'; g.fillText(nm, X, Y - r - 8);
    // alert glyph: "!" committed chase, "?" suspicious (the avoidable tell)
    if (self.state === 'chase' || self.alert > 0) {
      g.font = '900 16px Inter,system-ui';
      g.fillStyle = self.state === 'chase' ? '#ff5a4d' : '#ffe08a';
      g.fillText(self.state === 'chase' ? '!' : '?', X, Y - r - 22);
    }
    g.restore();
  }

  // ---- soulbound capture grant (NO gems, NO $BCARDD/ALK) --------------------
  // mercy: 'spare' | 'break' | null. Writes the del Toro loyalty/trust ledger on
  // the captured card so the bond (or the scar) persists in YOUR save.
  function grantCapture(ctx, card, mercy) {
    if (!ctx.econ) return;
    try { ctx.econ.addCopy(card.name, 1); } catch (_) {}     // soft, usable copy (collection + Garage upgrades)
    // Capture-origin copies are SOULBOUND. The dex/ledger lives in p.captures.
    // TODO-SERVER: ak-trade (wave 6) escrow MUST consult p.captures and reject
    // trading copies obtained only via capture -- enforced server-side, not here.
    try {
      ctx.econ.mutateProfile(function (p) {
        if (!p.captures || typeof p.captures !== 'object') p.captures = {};
        p.captures[card.name] = (p.captures[card.name] | 0) + 1;
        // del Toro MERCY ledger: per-card loyalty (grows over time elsewhere) under
        // a permanent trust ceiling. SPARE = low loyalty / full ceiling (earned).
        // BREAK = quick utility / capped ceiling (it never fully trusts you).
        if (!p.soulbound || typeof p.soulbound !== 'object') p.soulbound = {};
        var broke = (mercy === 'break');
        var sb = p.soulbound[card.name];
        if (!sb || typeof sb !== 'object') {
          sb = {
            loyalty:  broke ? 0.50 : 0.15,   // SPARE starts LOW (loyalty is earned over time)
            trustCap: broke ? 0.40 : 1.00,   // BREAK = PERMANENT trust penalty (capped ceiling)
            broken:   broke,
            spared:   !broke,
            since:    Date.now()
          };
        } else {
          // re-captured: a later BREAK permanently scars the ceiling for good.
          if (broke) { sb.broken = true; sb.spared = false; sb.trustCap = Math.min((sb.trustCap != null ? sb.trustCap : 1.00), 0.40); }
          sb.loyalty = Math.max((sb.loyalty || 0), broke ? 0.50 : (sb.loyalty || 0.15));
        }
        var cap = (sb.trustCap != null) ? sb.trustCap : 1.00;
        if (sb.loyalty > cap) sb.loyalty = cap;               // loyalty can never exceed the trust ceiling
        p.soulbound[card.name] = sb;
        p.encSeed = S.seed | 0;
      });
    } catch (_) {}
    try { if (global.AKQuests && global.AKQuests.reportEvent) global.AKQuests.reportEvent('captures', 1); } catch (_) {}
    playSfx('reward');
  }

  // ============================ CAPTURE MINI-GAME ============================
  // Pokemon throw -> leash sling. Wear stamina below the LEASH ZONE, then sling
  // the leash on the gold band. Catch chance climbs as stamina drops (the HP
  // threshold). 3-shake suspense. Out of leashes -> the stray bolts.
  function roundRect(g, x, y, w, h, r) {
    if (w < 2 * r) r = w / 2; if (h < 2 * r) r = h / 2;
    g.beginPath();
    g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }
  function drawBtn(g, rc, label, primary) {
    g.save();
    g.fillStyle = primary ? '#e8c55a' : 'rgba(20,17,10,.85)';
    roundRect(g, rc.x, rc.y, rc.w, rc.h, 9); g.fill();
    if (!primary) { g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.5)'; roundRect(g, rc.x, rc.y, rc.w, rc.h, 9); g.stroke(); }
    g.fillStyle = primary ? '#15110a' : '#b9a76a';
    g.font = '800 12px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(label, rc.x + rc.w / 2, rc.y + rc.h / 2 + 1);
    g.restore();
  }

  // ---- standoff text helpers (the long fuse) --------------------------------
  function wrapText(g, text, x, y, maxW, lh) {
    var words = ('' + text).split(' '), line = '', yy = y, i;
    for (i = 0; i < words.length; i++) {
      var test = line ? line + ' ' + words[i] : words[i];
      if (g.measureText(test).width > maxW && line) { g.fillText(line, x, yy); line = words[i]; yy += lh; }
      else line = test;
    }
    if (line) g.fillText(line, x, yy);
  }
  function factionKey(card) {
    var f = ((card.factionName || '') + ' ' + (card.name || '')).toLowerCase();
    if (/bone|guard|grave|skull/.test(f))      return 'boneguard';
    if (/zoom|syndic|speed|blitz/.test(f))     return 'zoomie';
    if (/leash|break|tactix|rebel|free/.test(f)) return 'leashbreak';
    if (/k9|circuit|cyber|byte|volt|mech/.test(f)) return 'k9';
    return 'generic';
  }
  function trashLine(card, beat) {
    var bank = STANDOFF_LINES[factionKey(card)] || STANDOFF_LINES.generic;
    var ln = bank[Math.min(beat, bank.length - 1)] || bank[0];
    return ln.replace('{breed}', (card.breed || 'stray'));
  }

  function startEncounter(self, ctx) {
    if (S.engaging) return;
    S.engaging = true;
    var card = self.card;
    var maxStam = 100, stam = 100, throws = THROWS;
    var phase = 'standoff';            // standoff | aim | shake | mercy
    var pos = 0, dir = 1, sweep = 1.5; // reticle sweep [0..1]
    var shakeT = 0, shakeN = 0, pendingCaught = false, pulse = 0;
    var resultStr = 'leave';
    var btnLeave = null, btnRead = null, btnLeash = null, btnStrike = null, btnSpare = null, btnBreak = null;
    var ratioBase = (CATCH_MOD[card.rarity] != null) ? CATCH_MOD[card.rarity] : 1;
    var ratio = ratioBase;
    // long fuse + mercy state
    var beat = 0, read = 0, tension = 0, clock = 0, nextTick = TENSION_TICK_STEP;
    var strikePayoff = 1, mercyChoice = null;

    function hit(rc, x, y) { return rc && x >= rc.x && x <= rc.x + rc.w && y >= rc.y && y <= rc.y + rc.h; }

    // shared catch math -- UNCHANGED formula, just factored so doThrow + SPARE reuse it.
    function catchChance(acc) {
      var frac = stam / maxStam;
      var below = (frac < CAP_THRESHOLD) ? 1 : 0.25;          // soft HP-threshold gate
      return clamp((1 - frac) * (1 - frac) * (0.5 + acc * 0.5) * ratio * below, 0, 0.96);
    }
    // LEASH commit: the long-fuse payoff -- each beat READ rattled the stray, so it
    // enters the capture mini-game nearer the LEASH ZONE with a better catch ratio.
    function commitLeash() {
      stam = clamp(maxStam - read * RATTLE_PER_BEAT, maxStam * 0.5, maxStam);
      ratio = ratioBase * (1 + read * LEASH_RATIO_PER_BEAT);
      phase = 'aim';
      playSfx('tap');
    }
    function openMercy() {
      if (phase !== 'mercy') { phase = 'mercy'; pulse = 1; playSfx('tap'); }
    }

    function doThrow() {
      var acc = clamp(1 - Math.abs(pos - 0.5) / 0.5, 0, 1);   // 1 = dead center (gold band)
      var weaken = (0.12 + acc * 0.33) * maxStam;             // clean hit ~45%, graze ~12%
      stam = Math.max(0, stam - weaken);
      pendingCaught = (Math.random() < catchChance(acc));
      throws--;
      phase = 'shake'; shakeT = 0; shakeN = 0; pulse = 1;
      playSfx('tap');
    }
    function resolve() {
      if (pendingCaught) {
        // a catch landed -> route through the SPARE/BREAK soul choice (mercy after).
        if (mercyChoice) { resultStr = 'caught'; api.close('caught'); }
        else openMercy();
      } else if (mercyChoice === 'spare') {
        // a respectful SPARE leash slipped -- it is still beaten, offer mercy again.
        if (throws <= 0) { resultStr = 'escaped'; api.close('escaped'); }
        else { mercyChoice = null; phase = 'mercy'; }
      } else if (stam / maxStam < CAP_THRESHOLD) {
        openMercy();                   // beaten below the LEASH ZONE -> mercy choice
      } else if (throws <= 0) { resultStr = 'escaped'; api.close('escaped'); }
      else { phase = 'aim'; }          // broke loose but leashes left -> keep trying
    }

    // portrait drawer -- assumes the origin is already translated to its center.
    // shared by the standoff, the capture screen, and the mercy screen.
    function drawPortrait(g, pr) {
      g.fillStyle = 'rgba(10,9,7,.9)'; roundRect(g, -pr / 2 - 8, -pr / 2 - 8, pr + 16, pr + 16, 14); g.fill();
      g.lineWidth = 2; g.strokeStyle = rarityCol(card.rarity); roundRect(g, -pr / 2 - 8, -pr / 2 - 8, pr + 16, pr + 16, 14); g.stroke();
      g.save(); roundRect(g, -pr / 2, -pr / 2, pr, pr, 10); g.clip();
      var im = dogImg(card), drew = false;
      if (im && im.complete && im.naturalWidth > 0) { try { g.drawImage(im, -pr / 2, -pr / 2, pr, pr); drew = true; } catch (_) {} }
      if (!drew) {
        g.fillStyle = card.color || '#c9a84c'; g.fillRect(-pr / 2, -pr / 2, pr, pr);
        g.fillStyle = '#0c0a08'; g.font = '900 ' + Math.round(pr * 0.5) + 'px Inter,system-ui';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText((card.breed || card.name || '?').charAt(0).toUpperCase(), 0, 2);
      }
      g.restore();
    }

    // ---- THE STANDOFF (Tarantino long fuse) -- the scene BEFORE the catch -----
    function drawStandoff(g, vp) {
      var W = vp.w, H = vp.h;
      g.save();
      var bg = g.createRadialGradient(W / 2, H * 0.40, 40, W / 2, H * 0.40, Math.max(W, H) * 0.85);
      bg.addColorStop(0, 'rgba(26,21,16,.96)'); bg.addColorStop(1, 'rgba(6,6,10,.98)');
      g.fillStyle = bg; g.fillRect(0, 0, W, H);

      g.textAlign = 'center';
      g.fillStyle = '#ff7a4d'; g.font = '900 12px Inter,system-ui';
      g.fillText('THE STANDOFF', W / 2, 38);
      g.fillStyle = '#e8c55a'; g.font = '900 22px Cinzel, "Playfair Display", serif';
      g.fillText('WILD ENCOUNTER', W / 2, 62);

      // portrait -- a slow menace breathe scaled by the tension
      var pr = Math.min(104, W * 0.30), py = H * 0.28;
      var breathe = Math.sin(clock * 4) * 2 * tension;
      g.save(); g.translate(W / 2, py + breathe); drawPortrait(g, pr); g.restore();

      g.textAlign = 'center'; g.textBaseline = 'alphabetic';
      g.fillStyle = '#f2e6c0'; g.font = '800 16px Inter,system-ui';
      g.fillText(card.name, W / 2, py + pr / 2 + 28);
      g.fillStyle = rarityCol(card.rarity); g.font = '700 10px Inter,system-ui';
      g.fillText((card.rarity || '').toUpperCase() + '  -  ' + (card.factionName || 'STRAY'), W / 2, py + pr / 2 + 43);

      // trash-talk box -- gritty quote, faction-colored accent bar
      var boxW = Math.min(360, W * 0.86), boxX = (W - boxW) / 2, boxY = py + pr / 2 + 56, boxH = 56;
      g.fillStyle = 'rgba(8,8,12,.72)'; roundRect(g, boxX, boxY, boxW, boxH, 10); g.fill();
      g.globalAlpha = 0.6; g.lineWidth = 1; g.strokeStyle = card.color || '#c9a84c';
      roundRect(g, boxX, boxY, boxW, boxH, 10); g.stroke(); g.globalAlpha = 1;
      g.fillStyle = card.color || '#c9a84c'; g.fillRect(boxX, boxY, 3, boxH);
      g.fillStyle = '#ffdca8'; g.font = 'italic 700 13px Georgia, "Times New Roman", serif';
      g.textAlign = 'left';
      wrapText(g, '"' + trashLine(card, beat) + '"', boxX + 14, boxY + 21, boxW - 26, 17);

      // TENSION METER (the fuse)
      var tmW = Math.min(320, W * 0.74), tmX = (W - tmW) / 2, tmY = boxY + boxH + 24, tmH = 10;
      g.textAlign = 'left'; g.fillStyle = 'rgba(232,217,168,.85)'; g.font = '700 9px Inter,system-ui';
      g.fillText('TENSION', tmX, tmY - 5);
      g.fillStyle = 'rgba(255,255,255,.08)'; roundRect(g, tmX, tmY, tmW, tmH, 5); g.fill();
      var tc = tension < 0.5 ? '#ffce6b' : (tension < 0.85 ? '#ff9a4d' : '#ff5a4d');
      g.fillStyle = tc; roundRect(g, tmX, tmY, Math.max(0, tmW * tension), tmH, 5); g.fill();
      g.textAlign = 'right'; g.fillStyle = 'rgba(232,217,168,.7)'; g.font = '700 9px Inter,system-ui';
      g.fillText('LEASH +' + Math.round(read * LEASH_RATIO_PER_BEAT * 100) + '%   STRIKE x' + (1 + read * STRIKE_PAYOFF_PER_BEAT).toFixed(1), tmX + tmW, tmY - 5);

      // buttons
      var by = tmY + tmH + 18;
      if (beat < MAX_BEATS - 1) {
        btnRead = { x: (W - Math.min(360, W * 0.86)) / 2, y: by, w: Math.min(360, W * 0.86), h: 30 };
        drawBtn(g, btnRead, 'READ THE ROOM  (' + (beat + 1) + '/' + MAX_BEATS + ')', false);
        by += 38;
      } else { btnRead = null; }
      var rowW = Math.min(360, W * 0.86), rowX = (W - rowW) / 2, half = (rowW - 10) / 2;
      btnLeash = { x: rowX, y: by, w: half, h: 42 };
      drawBtn(g, btnLeash, 'LEASH', true);
      btnStrike = { x: rowX + half + 10, y: by, w: half, h: 42 };
      g.fillStyle = '#a32218'; roundRect(g, btnStrike.x, btnStrike.y, half, 42, 9); g.fill();
      g.fillStyle = '#ffd9cf'; g.font = '800 13px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText('STRIKE', btnStrike.x + half / 2, btnStrike.y + 15);
      g.font = '700 8px Inter,system-ui'; g.fillStyle = 'rgba(255,217,207,.85)';
      g.fillText('-' + STRIKE_KARMA_COST + ' karma', btnStrike.x + half / 2, btnStrike.y + 30);
      g.textBaseline = 'alphabetic';

      g.textAlign = 'center'; g.fillStyle = 'rgba(201,168,76,.6)'; g.font = '600 9px Inter,system-ui';
      g.fillText('LEASH: de-escalate, harder catch, no karma   ·   STRIKE: fight, faster, costs karma', W / 2, by + 58);

      btnLeave = { x: 14, y: 14, w: 96, h: 30 }; drawBtn(g, btnLeave, 'BACK OFF', false);
      g.restore();
    }

    // ---- THE MERCY (del Toro) -- the soul choice AFTER it is beaten ----------
    function drawMercy(g, vp) {
      var W = vp.w, H = vp.h;
      g.save();
      var bg = g.createRadialGradient(W / 2, H * 0.40, 40, W / 2, H * 0.40, Math.max(W, H) * 0.85);
      bg.addColorStop(0, 'rgba(24,15,12,.96)'); bg.addColorStop(1, 'rgba(6,5,8,.98)');
      g.fillStyle = bg; g.fillRect(0, 0, W, H);

      g.textAlign = 'center';
      g.fillStyle = '#7CFFb0'; g.font = '900 12px Inter,system-ui';
      g.fillText('IT IS BEATEN', W / 2, 40);
      g.fillStyle = '#e8c55a'; g.font = '900 20px Cinzel, "Playfair Display", serif';
      g.fillText('THE MERCY', W / 2, 64);

      var pr = Math.min(94, W * 0.28), py = H * 0.30;
      g.save(); g.translate(W / 2, py); drawPortrait(g, pr); g.restore();

      g.textAlign = 'center'; g.textBaseline = 'alphabetic';
      g.fillStyle = '#f2e6c0'; g.font = '800 15px Inter,system-ui';
      g.fillText(card.name + ' bares its throat.', W / 2, py + pr / 2 + 28);
      g.fillStyle = 'rgba(232,217,168,.7)'; g.font = '600 11px Inter,system-ui';
      g.fillText('How you take it decides the dog you keep.', W / 2, py + pr / 2 + 45);

      var rowW = Math.min(360, W * 0.86), rowX = (W - rowW) / 2, half = (rowW - 12) / 2, by = py + pr / 2 + 64, bh = 54;
      // SPARE
      btnSpare = { x: rowX, y: by, w: half, h: bh };
      g.fillStyle = '#1f6e44'; roundRect(g, btnSpare.x, btnSpare.y, half, bh, 10); g.fill();
      g.lineWidth = 1; g.strokeStyle = '#7CFFb0'; roundRect(g, btnSpare.x, btnSpare.y, half, bh, 10); g.stroke();
      g.fillStyle = '#d6ffe6'; g.font = '800 14px Inter,system-ui'; g.textAlign = 'center';
      g.fillText('SPARE', btnSpare.x + half / 2, by + 20);
      g.font = '600 8px Inter,system-ui'; g.fillStyle = 'rgba(214,255,230,.85)';
      g.fillText('it joins soulbound', btnSpare.x + half / 2, by + 34);
      g.fillText('loyalty earned over time', btnSpare.x + half / 2, by + 45);
      // BREAK
      btnBreak = { x: rowX + half + 12, y: by, w: half, h: bh };
      g.fillStyle = '#7a1d14'; roundRect(g, btnBreak.x, btnBreak.y, half, bh, 10); g.fill();
      g.lineWidth = 1; g.strokeStyle = '#ff5a4d'; roundRect(g, btnBreak.x, btnBreak.y, half, bh, 10); g.stroke();
      g.fillStyle = '#ffd9cf'; g.font = '800 14px Inter,system-ui';
      g.fillText('BREAK', btnBreak.x + half / 2, by + 20);
      g.font = '600 8px Inter,system-ui'; g.fillStyle = 'rgba(255,217,207,.9)';
      g.fillText('guaranteed, faster', btnBreak.x + half / 2, by + 34);
      g.fillText('permanent trust penalty', btnBreak.x + half / 2, by + 45);

      g.fillStyle = 'rgba(232,217,168,.55)'; g.font = '600 9px Inter,system-ui';
      g.fillText(throws + ' leashes left', W / 2, by + bh + 18);

      btnLeave = { x: 14, y: 14, w: 96, h: 30 }; drawBtn(g, btnLeave, 'BACK OFF', false);
      g.restore();
    }

    function drawCapture(g, vp) {
      var W = vp.w, H = vp.h;
      g.save();
      var bg = g.createRadialGradient(W / 2, H * 0.42, 40, W / 2, H * 0.42, Math.max(W, H) * 0.8);
      bg.addColorStop(0, 'rgba(26,21,16,.96)'); bg.addColorStop(1, 'rgba(6,6,10,.98)');
      g.fillStyle = bg; g.fillRect(0, 0, W, H);

      g.textAlign = 'center';
      g.fillStyle = '#e8c55a'; g.font = '900 22px Cinzel, "Playfair Display", serif';
      g.fillText('WILD ENCOUNTER', W / 2, 52);
      g.fillStyle = 'rgba(201,168,76,.7)'; g.font = '700 12px Inter,system-ui';
      g.fillText('a stray ' + (card.breed || 'dog') + ' blocks the alley', W / 2, 74);

      // portrait
      var pr = Math.min(120, W * 0.34), px = W / 2, py = H * 0.40;
      var shk = (phase === 'shake') ? Math.sin(shakeT * 30 + shakeN * 2) * 8 * (1 - shakeT / 0.42) : 0;
      g.save();
      g.translate(px + shk, py);
      drawPortrait(g, pr);
      g.restore();

      // name + rarity
      g.textAlign = 'center'; g.textBaseline = 'alphabetic';
      g.fillStyle = '#f2e6c0'; g.font = '800 18px Inter,system-ui';
      g.fillText(card.name, W / 2, py + pr / 2 + 34);
      g.fillStyle = rarityCol(card.rarity); g.font = '700 11px Inter,system-ui';
      g.fillText((card.rarity || '').toUpperCase() + '  -  ' + (card.factionName || ''), W / 2, py + pr / 2 + 50);

      // stamina bar + LEASH ZONE threshold marker
      var bw = Math.min(320, W * 0.7), bx = (W - bw) / 2, by = py + pr / 2 + 72, bh = 14;
      g.fillStyle = 'rgba(255,255,255,.08)'; roundRect(g, bx, by, bw, bh, 7); g.fill();
      var frac = stam / 100;
      g.fillStyle = (frac < CAP_THRESHOLD) ? '#7CFFb0' : '#ffce6b';
      roundRect(g, bx, by, Math.max(0, bw * frac), bh, 7); g.fill();
      var thx = bx + bw * CAP_THRESHOLD;
      g.strokeStyle = '#ff5a4d'; g.lineWidth = 2; g.beginPath(); g.moveTo(thx, by - 3); g.lineTo(thx, by + bh + 3); g.stroke();
      g.fillStyle = 'rgba(232,217,168,.85)'; g.font = '700 10px Inter,system-ui'; g.textAlign = 'left';
      g.fillText('STAMINA', bx, by - 6);
      g.textAlign = 'right'; g.fillStyle = 'rgba(255,90,77,.9)'; g.fillText('LEASH ZONE', thx - 4, by - 6);

      // leash pips + count
      for (var i = 0; i < THROWS; i++) {
        var lx = bx + 12 + i * 22, ly = by + bh + 22;
        g.beginPath(); g.arc(lx, ly, 7, 0, 6.2832);
        g.fillStyle = (i < throws) ? '#e8c55a' : 'rgba(255,255,255,.12)'; g.fill();
      }
      g.fillStyle = 'rgba(232,217,168,.8)'; g.font = '700 10px Inter,system-ui'; g.textAlign = 'right';
      g.fillText(throws + ' LEASHES', bx + bw, by + bh + 26);

      // aim track or shake suspense
      var ty2 = H - 118, tw = Math.min(360, W * 0.8), txx = (W - tw) / 2, th = 18;
      if (phase === 'aim') {
        g.fillStyle = 'rgba(255,255,255,.07)'; roundRect(g, txx, ty2, tw, th, 9); g.fill();
        var bandW = tw * 0.18, bandX = txx + tw * 0.5 - bandW / 2;
        g.fillStyle = 'rgba(232,197,90,.5)'; roundRect(g, bandX, ty2, bandW, th, 9); g.fill();
        var mx = txx + tw * pos;
        g.fillStyle = '#fff'; g.fillRect(mx - 2, ty2 - 4, 4, th + 8);
        g.fillStyle = '#e8d9a8'; g.font = '700 12px Inter,system-ui'; g.textAlign = 'center';
        g.fillText('TAP to sling the leash -- hit the GOLD band', W / 2, ty2 - 12);
      } else {
        g.fillStyle = '#ffd76b'; g.font = '900 16px Inter,system-ui'; g.textAlign = 'center';
        var dots = ['.', '..', '...'][shakeN % 3];
        g.fillText('the leash tightens' + dots, W / 2, ty2 + 12);
      }

      // corner action (the fight choice now lives up front in the standoff)
      btnLeave = { x: 14, y: 14, w: 96, h: 34 };
      drawBtn(g, btnLeave, 'BACK OFF', false);

      g.restore();
    }

    var api = ctx.overlay.open({
      id: 'encounter_capture',
      onFrame: function (g, dt, vp) {
        clock += dt;
        if (phase === 'standoff') {
          tension = clamp(tension + dt * TENSION_RATE, 0, 1);   // the fuse burns
          if (tension >= nextTick && nextTick <= 1) { playSfx('tap'); nextTick += TENSION_TICK_STEP; }  // tick as it fills
          drawStandoff(g, vp); return;
        }
        if (phase === 'aim') { pos += dir * sweep * dt; if (pos > 1) { pos = 1; dir = -1; } else if (pos < 0) { pos = 0; dir = 1; } }
        else if (phase === 'shake') { shakeT += dt; if (shakeT > 0.42) { shakeT = 0; shakeN++; if (shakeN >= 3) resolve(); } }
        if (pulse > 0) pulse = Math.max(0, pulse - dt * 2);
        if (phase === 'mercy') { drawMercy(g, vp); return; }
        drawCapture(g, vp);
      },
      onPointer: function (evt) {
        if (evt.type !== 'pointerdown') return;
        var x = evt.clientX, y = evt.clientY;
        if (hit(btnLeave, x, y)) { resultStr = 'leave'; api.close('leave'); return; }
        if (phase === 'standoff') {
          if (btnRead && hit(btnRead, x, y)) {              // READ THE ROOM -> let it talk longer
            if (beat < MAX_BEATS - 1) { beat++; read = beat; tension = clamp(tension + TENSION_PER_READ, 0, 1); playSfx('tap'); duckBed(180); }
            return;
          }
          if (hit(btnLeash, x, y)) { commitLeash(); return; }   // de-escalate -> capture mini-game
          if (hit(btnStrike, x, y)) {                            // fight -> the battler, costs karma
            try { if (global.AKKarma && global.AKKarma.addKarma) global.AKKarma.addKarma(ctx.zoneId, -STRIKE_KARMA_COST, ctx); } catch (_) {}
            strikePayoff = +(1 + read * STRIKE_PAYOFF_PER_BEAT).toFixed(2);   // long fuse -> bigger payoff
            playSfx('tap'); duckBed(420);                       // the HIT on STRIKE
            api.close('battle'); return;
          }
          return;
        }
        if (phase === 'mercy') {
          if (hit(btnSpare, x, y)) {                            // SPARE -> respectful leash (intact catch math)
            mercyChoice = 'spare';
            if (pendingCaught) {                                // a catch already landed -> SPARE just sets the bond
              resultStr = 'caught'; playSfx('reward'); api.close('caught'); return;
            }
            pendingCaught = (Math.random() < catchChance(0.85)); // else one clean, respectful attempt
            throws--; phase = 'shake'; shakeT = 0; shakeN = 0; pulse = 1; playSfx('tap');
            return;
          }
          if (hit(btnBreak, x, y)) {                            // BREAK -> faster, guaranteed, scarred
            mercyChoice = 'break'; pendingCaught = true; resultStr = 'caught';
            playSfx('reward'); duckBed(300); api.close('caught'); return;
          }
          return;
        }
        if (phase === 'aim') doThrow();
      },
      onClose: function (res) {
        S.engaging = false;
        var out = res || resultStr;
        if (out === 'caught') {
          grantCapture(ctx, card, mercyChoice);
          var msg = (mercyChoice === 'spare')
            ? 'SPARED ' + card.name + '. It joins your crew. Loyalty must be earned.'
            : (mercyChoice === 'break')
              ? 'BROKE ' + card.name + ' to the leash. Yours now, but it will never fully trust you.'
              : 'LEASHED ' + card.name + '! A new copy joins your crew.';
          ctx.showBanner(msg, 2.2);
          self.dead = true; ctx.world.removeRoamer(self);
        } else if (out === 'escaped') {
          ctx.showBanner(card.name + ' slipped the leash and bolted.', 1.6);
          self.dead = true; ctx.world.removeRoamer(self);
        } else if (out === 'battle') {
          // route to the battler: short single-board encounter (engine convoyMode=false),
          // this card fielded as the rival rig. modes.js (wave 8) defines the win-condition.
          // Park the stray (cool + flee) so it can't re-fire startEncounter during the
          // ~480ms fade before the page navigates to game.html. payoff rides the long fuse
          // (extra field; harmless to the FROZEN engine if it goes unread).
          self.state = 'flee'; self.cool = 10; self.alert = 0;
          ctx.battle.launch({ mode: 'encounter', nemesis: { card: card.cardNumber, name: card.name, tier: 1 }, label: 'STREET FIGHT', payoff: strikePayoff });
        } else {
          // backed off -> the stray gives ground (anti-grief; no re-trigger for a beat)
          self.state = 'flee'; self.cool = 5; self.alert = 0;
        }
      }
    });
  }

  // ============================ REGISTRATION =================================
  global.AK_SYSTEMS.register({
    id: 'encounters',
    init: function (ctx) {
      var p = profile(ctx);
      if (p && typeof p.encSeed === 'number' && p.encSeed) S.seed = p.encSeed | 0;
      else S.seed = (Date.now() & 0x7fffffff) || 1;       // first run: pick a cursor, then it persists
      S.pool = buildPool(ctx);
      S.lastZone = ctx.zoneId;
      S.spawnCD = 0.8;                                     // first stray shortly after entering the world
    },
    onTick: function (dt, ctx) {
      if (!S.pool) S.pool = buildPool(ctx);
      if (ctx.zoneId !== S.lastZone) { S.lastZone = ctx.zoneId; S.spawnCD = Math.min(S.spawnCD, 1.2); }
      if (S.engaging) return;
      S.spawnCD -= dt;
      if (S.spawnCD <= 0) {
        S.spawnCD = SPAWN_MIN + Math.random() * (SPAWN_MAX - SPAWN_MIN);
        pruneIfNeeded(ctx);
        if (countWildInZone(ctx, ctx.zoneId) < MAX_PER_ZONE && totalWild(ctx) < MAX_TOTAL) spawnWild(ctx);
      }
    },
    onDrawWorld: function (ctx) {
      // light tension cue: a danger pulse at the bottom edge while a stray is on your tail
      var rs = ctx.world.roamers(), chasing = false, near = 1e9;
      for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (r._enc && r.zone === ctx.zoneId && r.state === 'chase') {
          chasing = true;
          var d = ctx.world.distToMe(r.x, r.y); if (d < near) near = d;
        }
      }
      if (!chasing) return;
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      var a = clamp(1 - near / 420, 0.06, 0.32);
      g.save();
      var grd = g.createLinearGradient(0, H, 0, H - 90);
      grd.addColorStop(0, 'rgba(255,60,50,' + a + ')'); grd.addColorStop(1, 'rgba(255,60,50,0)');
      g.fillStyle = grd; g.fillRect(0, H - 90, W, 90);
      g.restore();
    }
  });

  /* ========================================================================== *
   * STREET EVENTS (P5 -- captivation plan "intervene/ignore street events").
   * --------------------------------------------------------------------------
   * Random STREET EVENTS surface while you WALK a district: a MUGGING, a
   * BACK-ALLEY DEAL, or a STRAY IN TROUBLE. You can INTERVENE (a fight OR a
   * choice, with a karma + soft-loot consequence) or IGNORE it (the block
   * remembers either way). Reuses the long-fuse STANDOFF style (a SIZE IT UP
   * read burns a tension fuse + raises the payoff) and the canon crew voice
   * (the same STANDOFF_LINES bank). The offline curiosity gap of the GTA feel.
   *
   * DETERMINISTIC-BY-TIME: whether (and what) an event spawns is hashed from a
   * PT-anchored time WINDOW + the district id -- no client RNG decides outcome,
   * so parity holds across devices (placement near you uses Math.random, which
   * is cosmetic and never gates a reward). THROTTLED (one window per district,
   * a cooldown after each resolve) and DISMISSIBLE (BACK OFF; markers expire).
   *
   * PARITY LAW: rewards are gold / scrap / bones / keys / frags / SP ONLY, never
   * gems; the rescued stray is a SOULBOUND copy (it reuses grantCapture -- the
   * wild-encounter card path, non-tradeable). Nothing here is pay-to-win.
   *
   * Self-contained: a SECOND AK_SYSTEMS module (id 'streetevents') + the
   * window.AKStreetEvents hook. Edits no shared file; the encounters module
   * above is untouched. Tagged _se so the encounters/karma prune+cap ignore it.
   * ========================================================================== */
  var SE_PT_OFFSET_MS = 8 * 3600 * 1000;   // anchor the clock to LOCAL PT (UTC-8, the operator TZ)
  var SE_WINDOW_MS    = 4 * 60 * 1000;     // one street-event window per district (the throttle)
  var SE_SPAWN_CHANCE = 0.6;               // share of windows that actually carry an event
  var SE_MARKER_LIFE  = 42;                // seconds a marker lingers before the moment passes
  var SE_DWELL_MIN    = 2.0;               // must be walking the block this long before one surfaces
  var SE_COOLDOWN     = 12;                // seconds after a resolve before the next can surface
  var SE_SPAWN_AWAY   = 200;               // place it off your exact spot
  var SE_KARMA_GOOD   = 14;                // base district karma for stepping in
  var SE_KARMA_IGNORE = 6;                 // district karma lost for walking past (the block sees)
  var SE_SIZEUP_MAX   = 2;                 // long-fuse reads available (raise the payoff)
  var SE_SIZEUP_KARMA = 4;                 // each SIZE IT UP read adds this much intervene karma

  // The 3 street-event types. blurb()/hint render the scene; loot/thanks are
  // SOFT only (gems are impossible -- grantList drops them). fight -> routes to
  // the battler; rescue -> the stray joins soulbound (the wild-encounter path).
  var SE_EVENTS = {
    mugging: {
      id: 'mugging', title: 'A MUGGING', glyph: '🔪', ring: '#ff5a4d',
      interveneLabel: 'STEP IN', ignoreLabel: 'WALK PAST', fight: true,
      hint: 'STEP IN: a street fight   ·   WALK PAST: the block remembers',
      blurb: function (crew, vBreed) { return 'A ' + crew + ' enforcer has a ' + vBreed + ' pinned to the fence, shaking it down for everything it carries. Square up and the block owes you.'; },
      thanks: [['bones', 2], ['gold', 45]]          // handed up front; the rest rides the fight payoff
    },
    deal: {
      id: 'deal', title: 'A BACK-ALLEY DEAL', glyph: '💰', ring: '#ffce6b',
      interveneLabel: 'BUST IT', ignoreLabel: 'LOOK AWAY', fight: false,
      hint: 'BUST IT: seize the stash   ·   LOOK AWAY: let it slide',
      blurb: function (crew) { return 'Two ' + crew + ' runners are moving a contraband stash in the shadows. Bust it and the block is cleaner -- and the stash is yours.'; },
      loot: [['gold', [90, 160]], ['scrap', [3, 6], 'Common']]
    },
    stray: {
      id: 'stray', title: 'A STRAY IN TROUBLE', glyph: '🐾', ring: '#7CFFb0',
      interveneLabel: 'RESCUE', ignoreLabel: 'LEAVE IT', fight: false, rescue: true,
      hint: 'RESCUE: it joins you, soulbound   ·   LEAVE IT: walk on',
      blurb: function (crew, vName) { return vName + ' is cornered by a pack of toughs in the alley. Pull it out and it owes you its life -- it runs with you now.'; },
      loot: [['bones', [2, 4]]]
    }
  };

  // module state (separate from the encounters S; tagged so they never collide)
  var S2 = { ctx: null, engaging: false, dwell: 0, cool: 2.5, lastZone: '', lastBucket: {} };

  // ---- deterministic-by-time helpers (FNV-1a hash -> mulberry32 sub-RNG) ----
  function seHash(str) {
    var h = 2166136261 >>> 0;
    for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function seMulberry(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), a | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function ptBucket(now) { return Math.floor(((now || Date.now()) - SE_PT_OFFSET_MS) / SE_WINDOW_MS); }

  // Is an event due for this district + PT window? Returns {type,h,bucket,zone} or null.
  // The hash decides BOTH whether it fires and which type -- fully deterministic.
  function dueFor(zoneId, bucket) {
    var h = seHash('SE|' + bucket + '|' + zoneId);
    var rng = seMulberry(h);
    if (rng() >= SE_SPAWN_CHANCE) return null;               // no event this window
    var types = ['mugging', 'deal', 'stray'];
    var type = types[Math.floor(rng() * types.length)];
    return { type: type, h: h, bucket: bucket, zone: zoneId };
  }

  // Raw card objects for actor faces (reuse the encounters pool; generic fallback
  // keeps it functional even on a card-less headless load).
  function sePool(ctx) {
    var src = (S.pool && S.pool.length) ? S.pool : buildPool(ctx);
    var out = [];
    for (var i = 0; i < src.length; i++) { if (src[i] && src[i].card) out.push(src[i].card); }
    if (!out.length) out = [{ name: 'Stray', breed: 'mutt', rarity: 'Common', color: '#c9a84c', factionName: '', _generic: true }];
    return out;
  }
  function poolByRarity(pool, rarities) {
    var out = [];
    for (var i = 0; i < pool.length; i++) if (rarities.indexOf(pool[i].rarity) >= 0) out.push(pool[i]);
    return out.length ? out : pool;
  }
  function pickFrom(arr, rng) { return (arr && arr.length) ? arr[Math.floor(rng() * arr.length)] : null; }

  // ---- soft-reward grant (gems = hard no-op; deterministic amounts via rng) --
  function grantList(ctx, list, rng) {
    var got = [];
    (list || []).forEach(function (r) {
      var kind = r[0], amt = r[1], rar = r[2];
      if (kind === 'gems') return;                           // server-only; never here
      if (Array.isArray(amt)) { var lo = amt[0], hi = amt[1]; amt = lo + Math.floor(rng() * (hi - lo + 1)); }
      amt = amt | 0; if (amt <= 0) return;
      try { if (ctx.currency && ctx.currency.grant) ctx.currency.grant(kind, amt, rar); } catch (_) {}
      got.push({ kind: kind, amt: amt, rarity: rar });
    });
    return got.map(function (g) {
      var n = { gold: 'gold', scrap: (g.rarity || '') + ' scrap', bones: 'bones', keys: 'keys', fragments: 'frags', sp: 'SP' }[g.kind] || g.kind;
      return '+' + g.amt + ' ' + n;
    }).join('  ');
  }

  // resolve the player's verdict -> karma + loot consequence (and the fight route).
  function seResolve(ctx, self, res, reads) {
    var ev = self.ev, zone = self.zone;
    function karma(n) { try { if (global.AKKarma && global.AKKarma.addKarma) return global.AKKarma.addKarma(zone, n, ctx); } catch (_) {} return null; }

    if (res === 'intervene') {
      var bonus = (reads | 0) * SE_SIZEUP_KARMA, kAmt = SE_KARMA_GOOD + bonus;
      karma(kAmt);
      try { if (global.AKQuests && global.AKQuests.reportEvent) global.AKQuests.reportEvent('street_event', 1); } catch (_) {}

      if (ev.fight) {                                         // MUGGING -> the STREET FIGHT (combat tie-in)
        var gotStr = grantList(ctx, ev.thanks, seMulberry(self.h ^ 0x1B873593));   // thank-you up front (persists across the nav)
        playSfx('reward');
        self.done = true; ctx.world.removeRoamer(self);
        ctx.showBanner('You stepped in. +' + kAmt + ' karma' + (gotStr ? ('  ·  ' + gotStr) : ''), 1.8);
        var payoff = +(1 + (reads | 0) * 0.25).toFixed(2);    // long fuse -> bigger battle payoff
        var ag = self.aggressor || {};
        try {
          ctx.battle.launch({ mode: 'encounter', nemesis: { card: ag.cardNumber, name: ag.name || 'a mugger', tier: 1 }, label: 'STREET FIGHT', payoff: payoff });
        } catch (_) {}
        return;
      }
      if (ev.rescue) {                                        // STRAY IN TROUBLE -> it joins soulbound (wild-encounter path)
        var gs = grantList(ctx, ev.loot, seMulberry(self.h ^ 0x27D4EB2F));
        if (self.victim && !self.victim._generic) { try { grantCapture(ctx, self.victim, 'spare'); } catch (_) {} }
        playSfx('reward');
        self.done = true; ctx.world.removeRoamer(self);
        ctx.showBanner('Saved ' + ((self.victim && self.victim.name) || 'the stray') + '. It runs with you now, soulbound.  ' + gs + '  ·  +' + kAmt + ' karma', 2.4);
        return;
      }
      // BACK-ALLEY DEAL -> bust it, seize the stash (no fight; they scatter)
      var g2 = grantList(ctx, ev.loot, seMulberry(self.h ^ 0x165667B1));
      playSfx('reward');
      self.done = true; ctx.world.removeRoamer(self);
      ctx.showBanner('Busted the deal. Stash seized.  ' + g2 + '  ·  +' + kAmt + ' karma', 2.2);
      return;
    }

    if (res === 'ignore') {                                   // walk past -- the block saw you
      karma(-SE_KARMA_IGNORE);
      self.done = true; ctx.world.removeRoamer(self);
      ctx.showBanner('You walked past. The block saw it.  -' + SE_KARMA_IGNORE + ' karma', 1.8);
      return;
    }
    // BACK OFF / dismiss -- no verdict; give it a beat, it lingers then expires.
    self.cool = 6;
  }

  // host calls this once per rAF (only IN_ZONE && !interior && !overlay).
  function seUpdate(dt, self, ctx) {
    if (self.done) return;
    if (self.cool > 0) self.cool -= dt;
    self.pulse = (self.pulse + dt) % 2;
    self.life -= dt;
    if (self.life <= 0) { self.done = true; ctx.world.removeRoamer(self); return; }   // the moment passes (dismissible)
    if (!S2.engaging && self.cool <= 0 && ctx.world.distToMe(self.x, self.y) < self.r + 30) seOpen(self, ctx);
  }

  // world marker -- a gold-ringed scene pin with a fuse arc (time left), label +
  // the "!" curiosity tell. Cheap: no per-frame allocation, all primitives.
  function seDraw(g, self, ctx) {
    var X = ctx.world.wx(self.x), Y = ctx.world.wy(self.y), r = self.r, ev = self.ev;
    g.save();
    g.globalAlpha = 0.35; g.fillStyle = '#000';
    g.beginPath(); g.ellipse(X, Y + r * 0.8, r * 0.9, r * 0.4, 0, 0, 6.2832); g.fill();
    g.globalAlpha = 1;
    g.fillStyle = 'rgba(12,10,8,.92)'; g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.fill();
    g.fillStyle = '#f2e6c0'; g.font = Math.round(r * 1.05) + 'px Inter,system-ui';
    g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(ev.glyph, X, Y + 1);
    // pulsing event ring
    var pl = 0.55 + 0.45 * Math.abs(Math.sin((self.pulse || 0) * Math.PI));
    g.lineWidth = 2.5; g.strokeStyle = ev.ring; g.globalAlpha = pl;
    g.beginPath(); g.arc(X, Y, r + 3, 0, 6.2832); g.stroke(); g.globalAlpha = 1;
    // fuse arc -- time left before the moment passes (cheap sensory countdown)
    var frac = clamp(self.life / SE_MARKER_LIFE, 0, 1);
    g.lineWidth = 2; g.strokeStyle = 'rgba(232,197,90,.85)';
    g.beginPath(); g.arc(X, Y, r + 7, -1.5708, -1.5708 + 6.2832 * frac); g.stroke();
    // label tag
    g.font = '800 10px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    var nm = ev.title, tw = g.measureText(nm).width + 10;
    g.fillStyle = 'rgba(8,8,12,.72)'; g.fillRect(X - tw / 2, Y - r - 19, tw, 13);
    g.fillStyle = '#e8d9a8'; g.fillText(nm, X, Y - r - 9);
    // curiosity "!" tell
    g.font = '900 15px Inter,system-ui'; g.fillStyle = ev.ring; g.fillText('!', X, Y - r - 24);
    g.restore();
  }

  // place a street-event marker for a due window (placement uses Math.random --
  // cosmetic only). Returns the roamer handle (or null if it declined to place).
  function seSpawn(ctx, due) {
    if (!ctx || !ctx.world || !ctx.world.addRoamer || !due) return null;
    var ev = SE_EVENTS[due.type]; if (!ev) return null;
    var pool = sePool(ctx);
    var arng = seMulberry(due.h ^ 0x51ED2701);
    var aggressor = pickFrom(poolByRarity(pool, ['Rare', 'Epic', 'Legendary']), arng) || pickFrom(pool, arng);
    var victim = pickFrom(poolByRarity(pool, ['Common', 'Rare']), arng) || pickFrom(pool, arng);
    var WW = ctx.world.WORLD_W, WH = ctx.world.WORLD_H, x = 0, y = 0, ok = false, tries = 0;
    while (!ok && tries++ < 14) {
      x = 70 + Math.random() * (WW - 140); y = 70 + Math.random() * (WH - 140);
      if (ctx.world.distToMe(x, y) > SE_SPAWN_AWAY) ok = true;
    }
    if (!ok) return null;
    var handle = {
      _se: true, zone: ctx.zoneId, id: 'se_' + due.type + '_' + (Date.now() % 100000),
      x: x, y: y, r: 18, ev: ev, h: due.h, aggressor: aggressor, victim: victim,
      pulse: 0, cool: 0.6, life: SE_MARKER_LIFE, done: false,
      update: seUpdate, draw: seDraw
    };
    ctx.world.addRoamer(handle);
    return handle;
  }

  // ---- THE SCENE overlay (reuse the long-fuse standoff style) ---------------
  function seOpen(self, ctx) {
    if (S2.engaging) return;
    if (!ctx.overlay || !ctx.overlay.open) { seResolve(ctx, self, 'leave', 0); return; }   // headless: no crash, just back off
    S2.engaging = true;
    var ev = self.ev, card = ev.rescue ? self.victim : self.aggressor, foe = self.aggressor || {};
    var crew = 'a rival crew';
    try { if (global.AKKarma && global.AKKarma.getZoneFaction) { var f = global.AKKarma.getZoneFaction(self.zone); if (f && f.crew) crew = f.crew; } } catch (_) {}
    var vBreed = (self.victim && self.victim.breed) || 'stray', vName = (self.victim && self.victim.name) || 'a stray';
    var blurb = ev.rescue ? ev.blurb(crew, vName) : (ev.id === 'mugging' ? ev.blurb(crew, vBreed) : ev.blurb(crew));
    var reads = 0, tension = 0, clock = 0, nextTick = TENSION_TICK_STEP;
    var btnLeave = null, btnRead = null, btnGo = null, btnNo = null;

    function hit(rc, x, y) { return rc && x >= rc.x && x <= rc.x + rc.w && y >= rc.y && y <= rc.y + rc.h; }
    function sePortrait(g, c, pr) {
      g.fillStyle = 'rgba(10,9,7,.9)'; roundRect(g, -pr / 2 - 8, -pr / 2 - 8, pr + 16, pr + 16, 14); g.fill();
      g.lineWidth = 2; g.strokeStyle = rarityCol(c && c.rarity); roundRect(g, -pr / 2 - 8, -pr / 2 - 8, pr + 16, pr + 16, 14); g.stroke();
      g.save(); roundRect(g, -pr / 2, -pr / 2, pr, pr, 10); g.clip();
      var im = c ? dogImg(c) : null, drew = false;
      if (im && im.complete && im.naturalWidth > 0) { try { g.drawImage(im, -pr / 2, -pr / 2, pr, pr); drew = true; } catch (_) {} }
      if (!drew) {
        g.fillStyle = (c && c.color) || '#c9a84c'; g.fillRect(-pr / 2, -pr / 2, pr, pr);
        g.fillStyle = '#0c0a08'; g.font = '900 ' + Math.round(pr * 0.5) + 'px Inter,system-ui';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(((c && (c.breed || c.name)) || '?').charAt(0).toUpperCase(), 0, 2);
      }
      g.restore();
    }

    function draw(g, vp) {
      var W = vp.w, H = vp.h;
      g.save();
      var bg = g.createRadialGradient(W / 2, H * 0.40, 40, W / 2, H * 0.40, Math.max(W, H) * 0.85);
      bg.addColorStop(0, 'rgba(26,21,16,.96)'); bg.addColorStop(1, 'rgba(6,6,10,.98)');
      g.fillStyle = bg; g.fillRect(0, 0, W, H);

      g.textAlign = 'center';
      g.fillStyle = ev.ring; g.font = '900 12px Inter,system-ui';
      g.fillText('STREET EVENT', W / 2, 38);
      g.fillStyle = '#e8c55a'; g.font = '900 22px Cinzel, "Playfair Display", serif';
      g.fillText(ev.title, W / 2, 62);

      // focal portrait -- a slow menace breathe scaled by the tension
      var pr = Math.min(102, W * 0.30), py = H * 0.25;
      var breathe = Math.sin(clock * 4) * 2 * tension;
      g.save(); g.translate(W / 2, py + breathe); sePortrait(g, card, pr);
      g.fillStyle = '#f2e6c0'; g.font = Math.round(pr * 0.32) + 'px Inter,system-ui';
      g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(ev.glyph, pr / 2 - 2, pr / 2 - 2);
      g.restore();

      g.textAlign = 'center'; g.textBaseline = 'alphabetic';
      g.fillStyle = '#f2e6c0'; g.font = '800 16px Inter,system-ui';
      g.fillText((card && card.name) || 'A stray', W / 2, py + pr / 2 + 26);
      g.fillStyle = rarityCol(card && card.rarity); g.font = '700 10px Inter,system-ui';
      g.fillText(((card && card.rarity) || '').toUpperCase() + '  -  ' + crew, W / 2, py + pr / 2 + 41);

      // snarl box -- reuse the long-fuse standoff bank for the threat's voice
      var boxW = Math.min(360, W * 0.86), boxX = (W - boxW) / 2, boxY = py + pr / 2 + 52, boxH = 44;
      g.fillStyle = 'rgba(8,8,12,.72)'; roundRect(g, boxX, boxY, boxW, boxH, 10); g.fill();
      g.fillStyle = (foe.color || ev.ring); g.fillRect(boxX, boxY, 3, boxH);
      g.fillStyle = '#ffdca8'; g.font = 'italic 700 12px Georgia, "Times New Roman", serif'; g.textAlign = 'left';
      wrapText(g, '"' + trashLine(foe, reads) + '"', boxX + 14, boxY + 18, boxW - 26, 15);

      // the scene blurb
      g.fillStyle = '#d9cfa6'; g.font = '600 11px Inter,system-ui'; g.textAlign = 'left';
      wrapText(g, blurb, boxX, boxY + boxH + 16, boxW, 15);

      // THE MOMENT fuse + karma preview
      var tmW = Math.min(320, W * 0.74), tmX = (W - tmW) / 2, tmY = boxY + boxH + 74, tmH = 9;
      g.textAlign = 'left'; g.fillStyle = 'rgba(232,217,168,.85)'; g.font = '700 9px Inter,system-ui';
      g.fillText('THE MOMENT', tmX, tmY - 5);
      g.fillStyle = 'rgba(255,255,255,.08)'; roundRect(g, tmX, tmY, tmW, tmH, 5); g.fill();
      var tc = tension < 0.5 ? '#ffce6b' : (tension < 0.85 ? '#ff9a4d' : '#ff5a4d');
      g.fillStyle = tc; roundRect(g, tmX, tmY, Math.max(0, tmW * tension), tmH, 5); g.fill();
      g.textAlign = 'right'; g.fillStyle = 'rgba(232,217,168,.7)'; g.font = '700 9px Inter,system-ui';
      g.fillText('KARMA +' + (SE_KARMA_GOOD + reads * SE_SIZEUP_KARMA), tmX + tmW, tmY - 5);

      // buttons
      var by = tmY + tmH + 16;
      if (reads < SE_SIZEUP_MAX) {
        btnRead = { x: (W - Math.min(360, W * 0.86)) / 2, y: by, w: Math.min(360, W * 0.86), h: 28 };
        drawBtn(g, btnRead, 'SIZE IT UP  (' + (reads + 1) + '/' + SE_SIZEUP_MAX + ')', false);
        by += 36;
      } else { btnRead = null; }
      var rowW = Math.min(360, W * 0.86), rowX = (W - rowW) / 2, half = (rowW - 10) / 2;
      btnGo = { x: rowX, y: by, w: half, h: 44 };
      drawBtn(g, btnGo, ev.interveneLabel, true);
      btnNo = { x: rowX + half + 10, y: by, w: half, h: 44 };
      drawBtn(g, btnNo, ev.ignoreLabel, false);

      g.textAlign = 'center'; g.fillStyle = 'rgba(201,168,76,.6)'; g.font = '600 9px Inter,system-ui';
      g.fillText(ev.hint, W / 2, by + 58);

      btnLeave = { x: 14, y: 14, w: 96, h: 30 }; drawBtn(g, btnLeave, 'BACK OFF', false);
      g.restore();
    }

    var api = ctx.overlay.open({
      id: 'street_event',
      onFrame: function (g, dt, vp) {
        clock += dt;
        tension = clamp(tension + dt * TENSION_RATE, 0, 1);   // the fuse burns
        if (tension >= nextTick && nextTick <= 1) { playSfx('tap'); nextTick += TENSION_TICK_STEP; }
        draw(g, vp);
      },
      onPointer: function (evt) {
        if (evt.type !== 'pointerdown') return;
        var x = evt.clientX, y = evt.clientY;
        if (hit(btnLeave, x, y)) { api.close('leave'); return; }
        if (btnRead && hit(btnRead, x, y)) {                  // SIZE IT UP -> read longer, raise the payoff
          if (reads < SE_SIZEUP_MAX) { reads++; tension = clamp(tension + TENSION_PER_READ, 0, 1); playSfx('tap'); duckBed(180); }
          return;
        }
        if (hit(btnGo, x, y)) { api.close('intervene'); return; }
        if (hit(btnNo, x, y)) { api.close('ignore'); return; }
      },
      onClose: function (res) {
        S2.engaging = false;
        var out = res || 'leave';
        if (out === 'intervene' || out === 'ignore') { S2.cool = SE_COOLDOWN; S2.dwell = 0; }
        seResolve(ctx, self, out, reads);
      }
    });
  }

  function seActiveInZone(ctx) {
    var rs = ctx.world.roamers();
    for (var i = 0; i < rs.length; i++) if (rs[i]._se && rs[i].zone === ctx.zoneId && !rs[i].done) return true;
    return false;
  }

  // ---- the streetevents AK_SYSTEMS module (the self-contained event hook) ---
  global.AK_SYSTEMS.register({
    id: 'streetevents',
    init: function (ctx) { S2.ctx = ctx; S2.dwell = 0; S2.cool = 2.5; S2.lastZone = ctx.zoneId; S2.lastBucket = {}; },
    onTick: function (dt, ctx) {
      if (S2.engaging) return;
      if (ctx.zoneId !== S2.lastZone) { S2.lastZone = ctx.zoneId; S2.dwell = 0; S2.cool = Math.max(S2.cool, 2.0); }   // fresh block -> a beat before one surfaces
      if (S2.cool > 0) { S2.cool -= dt; return; }
      S2.dwell += dt;
      if (S2.dwell < SE_DWELL_MIN) return;                    // must be walking the block first
      if (seActiveInZone(ctx)) return;                        // one event at a time
      var zone = ctx.zoneId, bucket = ptBucket();
      if (S2.lastBucket[zone] === bucket) return;             // this window already handled in this district
      var due = dueFor(zone, bucket);
      S2.lastBucket[zone] = bucket;                           // consume the window (spawn or not -> the throttle)
      if (due) seSpawn(ctx, due);
    },
    onDrawWorld: function (ctx) {
      // cheap sensory cue: a soft gold pulse at the top edge while an unhandled event is near.
      var rs = ctx.world.roamers(), near = 1e9, found = false;
      for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (r._se && r.zone === ctx.zoneId && !r.done) { found = true; var d = ctx.world.distToMe(r.x, r.y); if (d < near) near = d; }
      }
      if (!found) return;
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      var a = clamp(1 - near / 460, 0.04, 0.20);
      g.save();
      var grd = g.createLinearGradient(0, 0, 0, 80);
      grd.addColorStop(0, 'rgba(232,197,90,' + a.toFixed(3) + ')'); grd.addColorStop(1, 'rgba(232,197,90,0)');
      g.fillStyle = grd; g.fillRect(0, 0, W, 80);
      g.restore();
    }
  });

  /* PUBLIC HOOK -- window.AKStreetEvents (the self-contained event hook for the
     integration pass). isDue() is the deterministic-by-time gate; spawnNow() is
     the force-spawn used by the integration/test pass; active() reports state. */
  global.AKStreetEvents = {
    EVENTS: SE_EVENTS,
    ptBucket: ptBucket,
    isDue: function (zoneId, now) { return dueFor(zoneId || (S2.ctx && S2.ctx.zoneId), ptBucket(now)); },
    spawnNow: function (ctx, type) {
      ctx = ctx || S2.ctx; if (!ctx || !ctx.world) return null;
      var bucket = ptBucket();
      var due = (type && SE_EVENTS[type])
        ? { type: type, h: seHash('SE|' + bucket + '|' + ctx.zoneId + '|' + type), bucket: bucket, zone: ctx.zoneId }
        : (dueFor(ctx.zoneId, bucket) || { type: 'mugging', h: seHash('SE|forced|' + Date.now()), bucket: bucket, zone: ctx.zoneId });
      return seSpawn(ctx, due);
    },
    resolve: seResolve,
    active: function (ctx) { ctx = ctx || S2.ctx; return ctx ? seActiveInZone(ctx) : false; }
  };

})(typeof window !== 'undefined' ? window : globalThis);
