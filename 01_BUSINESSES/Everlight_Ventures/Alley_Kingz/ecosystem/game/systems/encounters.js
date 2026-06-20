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
  var SPAWN_MIN     = 7.0;      // seconds between spawn attempts (random)
  var SPAWN_MAX     = 13.0;
  var SPAWN_AWAY    = 220;      // never spawn within this px of the player
  var THROWS        = 4;        // leash throws per encounter (out -> the stray bolts)
  var CAP_THRESHOLD = 0.45;     // stamina fraction below which the catch gets real traction
  var RARITY        = ['Common', 'Rare', 'Epic', 'Legendary', 'Mythic'];
  // rarity -> base catch multiplier (rarer = harder; Mythics never roam so 0)
  var CATCH_MOD = { Common: 1.0, Rare: 0.82, Epic: 0.6, Legendary: 0.42, Mythic: 0 };
  // rarity -> spawn weight (toward Common/Rare; Mythics excluded entirely)
  var SPAWN_W   = { Common: 60, Rare: 28, Epic: 9, Legendary: 3, Mythic: 0 };

  // ============================ MODULE STATE =================================
  var S = { pool: null, seed: 1, spawnCD: 1.5, lastZone: '', engaging: false, sinceSave: 0 };
  var imgCache = {};

  function profile(ctx) { try { return ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function playSfx(n) { try { if (global.AK && global.AK.playSfx) global.AK.playSfx(n); } catch (_) {} }

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
  function grantCapture(ctx, card) {
    if (!ctx.econ) return;
    try { ctx.econ.addCopy(card.name, 1); } catch (_) {}     // soft, usable copy (collection + Garage upgrades)
    // Capture-origin copies are SOULBOUND. The dex/ledger lives in p.captures.
    // TODO-SERVER: ak-trade (wave 6) escrow MUST consult p.captures and reject
    // trading copies obtained only via capture -- enforced server-side, not here.
    try {
      ctx.econ.mutateProfile(function (p) {
        if (!p.captures || typeof p.captures !== 'object') p.captures = {};
        p.captures[card.name] = (p.captures[card.name] | 0) + 1;
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

  function startEncounter(self, ctx) {
    if (S.engaging) return;
    S.engaging = true;
    var card = self.card;
    var maxStam = 100, stam = 100, throws = THROWS;
    var phase = 'aim';                 // aim | shake
    var pos = 0, dir = 1, sweep = 1.5; // reticle sweep [0..1]
    var shakeT = 0, shakeN = 0, pendingCaught = false, pulse = 0;
    var resultStr = 'leave';
    var btnFight = null, btnLeave = null;
    var ratio = (CATCH_MOD[card.rarity] != null) ? CATCH_MOD[card.rarity] : 1;

    function hit(rc, x, y) { return rc && x >= rc.x && x <= rc.x + rc.w && y >= rc.y && y <= rc.y + rc.h; }

    function doThrow() {
      var acc = clamp(1 - Math.abs(pos - 0.5) / 0.5, 0, 1);   // 1 = dead center (gold band)
      var weaken = (0.12 + acc * 0.33) * maxStam;             // clean hit ~45%, graze ~12%
      stam = Math.max(0, stam - weaken);
      var frac = stam / maxStam;
      var below = (frac < CAP_THRESHOLD) ? 1 : 0.25;          // soft HP-threshold gate
      var chance = clamp((1 - frac) * (1 - frac) * (0.5 + acc * 0.5) * ratio * below, 0, 0.96);
      pendingCaught = (Math.random() < chance);
      throws--;
      phase = 'shake'; shakeT = 0; shakeN = 0; pulse = 1;
      playSfx('tap');
    }
    function resolve() {
      if (pendingCaught) { resultStr = 'caught'; api.close('caught'); }
      else if (throws <= 0) { resultStr = 'escaped'; api.close('escaped'); }
      else { phase = 'aim'; }          // broke loose but leashes left -> keep trying
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

      // corner actions
      btnLeave = { x: 14, y: 14, w: 96, h: 34 };
      drawBtn(g, btnLeave, 'BACK OFF', false);
      btnFight = { x: W - 150, y: H - 50, w: 136, h: 38 };
      drawBtn(g, btnFight, 'STREET FIGHT', true);

      g.restore();
    }

    var api = ctx.overlay.open({
      id: 'encounter_capture',
      onFrame: function (g, dt, vp) {
        if (phase === 'aim') { pos += dir * sweep * dt; if (pos > 1) { pos = 1; dir = -1; } else if (pos < 0) { pos = 0; dir = 1; } }
        else if (phase === 'shake') { shakeT += dt; if (shakeT > 0.42) { shakeT = 0; shakeN++; if (shakeN >= 3) resolve(); } }
        if (pulse > 0) pulse = Math.max(0, pulse - dt * 2);
        drawCapture(g, vp);
      },
      onPointer: function (evt) {
        if (evt.type !== 'pointerdown') return;
        var x = evt.clientX, y = evt.clientY;
        if (hit(btnLeave, x, y)) { resultStr = 'leave'; api.close('leave'); return; }
        if (hit(btnFight, x, y)) { api.close('battle'); return; }
        if (phase === 'aim') doThrow();
      },
      onClose: function (res) {
        S.engaging = false;
        var out = res || resultStr;
        if (out === 'caught') {
          grantCapture(ctx, card);
          ctx.showBanner('LEASHED ' + card.name + '! A new copy joins your crew.', 2.0);
          self.dead = true; ctx.world.removeRoamer(self);
        } else if (out === 'escaped') {
          ctx.showBanner(card.name + ' slipped the leash and bolted.', 1.6);
          self.dead = true; ctx.world.removeRoamer(self);
        } else if (out === 'battle') {
          // route to the battler: short single-board encounter (engine convoyMode=false),
          // this card fielded as the rival rig. modes.js (wave 8) defines the win-condition.
          // Park the stray (cool + flee) so it can't re-fire startEncounter during the
          // ~480ms fade before the page navigates to game.html.
          self.state = 'flee'; self.cool = 10; self.alert = 0;
          ctx.battle.launch({ mode: 'encounter', nemesis: { card: card.cardNumber, name: card.name, tier: 1 }, label: 'STREET FIGHT' });
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
      S.spawnCD = 1.5;                                     // first stray shortly after entering the world
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
})(typeof window !== 'undefined' ? window : globalThis);
