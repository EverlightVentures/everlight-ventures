/* game/systems/arcade.js -- AK_SYSTEMS module: THE ARCADE (wave 7).
 * ----------------------------------------------------------------------------
 * Self-contained per the MODULE_CONTRACT. Touches NO shared files. Owns ONE
 * building interior (ARCADE, THE_STRIP) and runs every mini-game on the host's
 * full-screen Canvas2D overlay (ctx.overlay.open). Soft-currency payouts only,
 * gated by a per-day anti-farm cap (LOOT_TABLE cap philosophy).
 *
 * RESPONSIBILITY
 *   - 3 standalone games:  bone_dig (grid-match)  |  alley_dash (endless runner)
 *                          |  whack (whack-a-stray reaction)
 *   - 2 embedded micro-game STUBS callable by other buildings via
 *     window.AK_ARCADE.play(id, ctx, opts):  gem_tap (mining tap-rhythm, for the
 *     Gem Mine) + forge_temper (quench-timing, for the Card Forge).
 *
 * HARD RULES honored:
 *   - 2.5D Canvas2D only; battler NEVER touched (these are overlay mini-games).
 *   - Crypto gate: rewards are SOFT CREW-TRAINING only -- gold + bones + skill
 *     points + produce + scrap + a few shared-rank trophies. The cabinets FEED
 *     the ONE game (crew training avenue), they are NOT standalone toys. Never
 *     gems / $BCARDD / ALK. ctx.currency.grant('gems') is already a no-op.
 *   - All state lives behind the falsy-default field p.arcade (added once by the
 *     Lead in economy.js ensureShape). We self-heal it if absent so the module
 *     is byte-identical on a zero-state profile and safe before bootstrap.
 *   - Cards reused BY NAME from the roster as wild strays / runner; card art
 *     resolves through window.CANON_CARDS + window.akCardArtRel to the REAL
 *     portrait. The emoji glyph is a TRUE last-resort fallback only.
 *   - "crew" never "clan"; gritty gold cyberpunk dog-gang voice in keeper copy.
 *
 * Headless-safe: no top-level DOM/localStorage; bails on pages without the
 * registry; every Image()/canvas touch is browser-gated + guarded.
 * ========================================================================== */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;                 // hub-only module

  /* ---- palette (mirrors the Everlight gold cyberpunk theme) -------------- */
  var GOLD = '#e8c55a', GOLD_D = '#c9a84c', TEAL = '#7CFFE0', RED = '#C0392B',
      TXT = '#E8E8E8', DIM = '#9a8f6a', INK = '#06060a';

  /* ---- anti-farm daily caps (soft-currency budget per device-day) -------- */
  var DAILY_GOLD_CAP = 500, DAILY_BONES_CAP = 20;
  /* ---- CREW TRAINING daily caps (CROWN CLIMB phase 6 -- the arcade is a
   *      TRAINING RUNG that FEEDS the RPG, never a standalone toy). A good run
   *      trickles crew XP into the ONE game: skill points + produce + a FEW
   *      pips on the shared rank ladder. Kept tight + on its OWN daily ledger
   *      so the cabinets can never be farmed past the cap. Soft + parity-safe;
   *      NEVER gems. -------------------------------------------------------- */
  var DAILY_SP_CAP = 6, DAILY_PRODUCE_CAP = 60, DAILY_TROPHY_CAP = 15, DAILY_SCRAP_CAP = 4;

  /* ---- card pools referenced BY NAME (real roster cards) ----------------- */
  var WILD_STRAYS = ['Neon Whippet', 'Turbo Jack', 'Copper Chow', 'Pixel Greyhound',
    'Circuit Shiba', 'Drift Sheltie', 'Byte Beagle', 'Echo Dalmatian',
    'Static Sheba Inu', 'Grit Bulldog', 'Brick Bullmastiff', 'Tank Pug'];
  var GOLD_DOG = '$BCARDD';           // the mascot = the jackpot pop
  var CREW_PUP = 'Vibe Shih Tzu';     // your own crew pup -- do NOT whack

  /* ====================================================================== *
   * small helpers
   * ====================================================================== */
  function econ(ctx) { return (ctx && ctx.econ) ? ctx.econ : (global.AK_ECON || null); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function ri(lo, hi) { return lo + Math.floor(Math.random() * (hi - lo + 1)); }
  function today() { try { return new Date().toDateString(); } catch (_) { return 'd'; } }
  // Resolve a roster name to its CANONICAL record -- the one window.akCardArtRel
  // needs (it carries cardNumber, so the real .webp portrait always loads).
  // CANON_CARDS is preferred BECAUSE the host's live ctx.cards() map can omit
  // cardNumber (=> art path '' => glyph); the canon record never does. This is
  // the card-art fix: every dog drawn in a cabinet gets a real portrait.
  function canonByName(name) {
    if (!name) return null;
    var L = global.CANON_CARDS; if (!L || !L.length) return null;
    for (var i = 0; i < L.length; i++) { var c = L[i]; if (c && (c.name === name || c.id === name)) return c; }
    return null;
  }
  function cardFor(ctx, name) {
    var c = canonByName(name); if (c) return c;                 // real portrait path (preferred)
    try { var m = ctx.cards(); return (m && m[name]) || null; } catch (_) { return null; }
  }

  function rr(g, x, y, w, h, rad) {
    g.beginPath(); g.moveTo(x + rad, y);
    g.arcTo(x + w, y, x + w, y + h, rad); g.arcTo(x + w, y + h, x, y + h, rad);
    g.arcTo(x, y + h, x, y, rad);         g.arcTo(x, y, x + w, y, rad); g.closePath();
  }
  function txt(g, s, x, y, size, col, align, weight) {
    g.fillStyle = col || TXT; g.textAlign = align || 'center'; g.textBaseline = 'middle';
    g.font = (weight || '700') + ' ' + size + 'px Inter, system-ui, sans-serif';
    g.fillText(s, x, y);
  }
  // Brand header type: Cinzel (matches loadscreen + shop + encounters board).
  function htxt(g, s, x, y, size, col, weight) {
    g.fillStyle = col || GOLD; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = (weight || '900') + ' ' + size + 'px Cinzel, "Playfair Display", serif';
    g.fillText(s, x, y);
  }
  function hitC(px, py, b) { return !!b && Math.hypot(px - b.x, py - b.y) <= b.r; }
  function hitR(px, py, b) { return !!b && px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h; }

  /* ---- optional card-art loader (graceful glyph fallback) ---------------- */
  var _img = {};
  function cardImg(card) {
    if (!card || typeof Image === 'undefined' || !global.akCardArtRel) return null;
    var rel = ''; try { rel = global.akCardArtRel(card); } catch (_) { rel = ''; }
    if (!rel) return null;
    if (_img.hasOwnProperty(rel)) return _img[rel];
    var im = new Image(); _img[rel] = im;
    im.onerror = function () { if (global.akImgErr && global.akImgErr(im)) return; _img[rel] = null; };
    try { im.src = 'assets/' + rel; } catch (_) { _img[rel] = null; }
    return im;
  }
  function drawDog(g, card, glyph, x, y, r, accent) {
    var im = cardImg(card);
    g.save();
    if (im && im.complete && im.naturalWidth > 0) {              // REAL card portrait
      g.beginPath(); g.arc(x, y, r, 0, 7); g.closePath(); g.clip();
      try { g.drawImage(im, x - r, y - r, r * 2, r * 2); } catch (_) {}
      g.restore();
      g.strokeStyle = accent || GOLD; g.lineWidth = 2.5;
      g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke();
      return;
    }
    // accent disc placeholder. If a real portrait IS on the way (im != null, art
    // still streaming in), we do NOT draw the emoji -- the portrait pops in a
    // frame later. The glyph is the TRUE last resort: no canon card / no art.
    g.fillStyle = accent || GOLD_D; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    g.strokeStyle = 'rgba(0,0,0,.35)'; g.lineWidth = 2; g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke();
    if (!im) txt(g, glyph || '🐕', x, y + 1, Math.round(r * 1.1), '#0c0a07', 'center', '700');
    g.restore();
  }

  /* ---- AK-ARCART 2026-07-18: REAL-ART MANIFEST ---------------------------
   * Every cabinet was drawing pure JS primitives on a procedural backdrop while
   * the build ships ~1.7k real assets. Each game now names a themed photo plate
   * (comic panel / hub art / interior art) plus the icon sprites that stand in
   * for its emoji glyphs. Every path below was verified present on disk on
   * 2026-07-18 and every one is ALREADY referenced by index.html, so the files
   * are warm in cache by the time a cabinet opens. Loading is lazy (first frame
   * that asks) and each slot has an onerror that nulls it, so a missing or
   * renamed file degrades to the exact primitive rendering that shipped before.
   * ---------------------------------------------------------------------- */
  var ART_BG = {
    bone_dig:     'assets/hub/the_undercity_bg.png',   // digging under the city
    alley_dash:   'assets/story/0000_rooftops.jpg',    // comic panel: the rooftop run
    whack:        'assets/story/0000_kennel.jpg',      // comic panel: the stray kennel
    gem_tap:      'assets/interiors/gem_mine.png',     // the Gem Mine rock face
    forge_temper: 'assets/interiors/card_forge.png'    // the Card Forge bench
  };
  var ART_SPR = {
    dig_bone:   'assets/icons/chip_bones.png',
    dig_gear:   'assets/icons/chip_builder.png',
    dig_bolt:   'assets/icons/abil_bolt.png',
    dig_crown:  'assets/icons/season_crown.png',
    dig_paw:    'assets/icons/chip_paw.png',
    dig_wrench: 'assets/icons/tool_crowbar.png',
    dig_gem:    'assets/icons/chip_gem.png',
    dig_card:   'assets/icons/chip_story.png',
    dig_back:   'assets/icons/loot_bag.png',           // face-down tile = a buried stash
    drone:      'assets/icons/spell_trap.png',         // alley_dash pound drone
    crew_tag:   'assets/icons/chip_crew.png',          // whack: do NOT hit your own
    drill:      'assets/icons/tool_drill.png',         // gem_tap sweep head
    vein:       'assets/icons/chip_gem.png',           // gem_tap pay band
    anvil:      'assets/icons/icon_forge.png'          // forge_temper header
  };

  // Lazy image slot. Absent key = never asked, null = dead (caller paints its
  // primitive), Image = in flight or ready. A dead path is never retried.
  var _art = {};
  function art(path) {
    if (!path || typeof Image === 'undefined') return null;
    if (_art.hasOwnProperty(path)) return _art[path];
    var im = new Image(); _art[path] = im;
    im.onerror = function () { _art[path] = null; };
    try { im.src = path; } catch (_) { _art[path] = null; }
    return im;
  }
  function ready(im) { return !!(im && im.complete && im.naturalWidth > 0); }
  // Five of these icons are 1024x1024 on disk. Downscaling a 1MP source to a
  // 44px tile 16 times a frame would eat the phone's budget, so each sprite is
  // rasterized ONCE per 4px size bucket into an offscreen canvas (same single-
  // slot trick buildBg already uses) and blitted from there afterwards.
  var _sprCv = {};
  function sprCanvas(key, size) {
    var im = art(ART_SPR[key]); if (!ready(im)) return null;
    if (typeof document === 'undefined' || !document.createElement) return null;
    var px = Math.max(8, Math.round(size / 4) * 4), ck = key + '@' + px;
    if (_sprCv.hasOwnProperty(ck)) return _sprCv[ck];
    var cv = null;
    try {
      cv = document.createElement('canvas'); cv.width = px; cv.height = px;
      var c = cv.getContext('2d');
      if (!c) cv = null;
      else { try { c.imageSmoothingQuality = 'high'; } catch (_q) {} c.drawImage(im, 0, 0, px, px); }
    } catch (_) { cv = null; }
    _sprCv[ck] = cv; return cv;
  }
  // Centered sprite blit. Returns false when the art is not up (missing, dead or
  // still streaming) so the caller falls straight back to its original glyph.
  function drawSpr(g, key, x, y, size, alpha) {
    var src = sprCanvas(key, size);
    if (!src) { var im = art(ART_SPR[key]); if (!ready(im)) return false; src = im; }   // no offscreen: blit source
    g.save(); if (alpha !== undefined) g.globalAlpha = alpha;
    try { g.drawImage(src, x - size / 2, y - size / 2, size, size); }
    catch (_) { g.restore(); return false; }
    g.restore(); return true;
  }
  // cover-fit a photo across the viewport (no squash on any phone aspect)
  function drawCover(g, im, w, h) {
    var iw = im.naturalWidth, ih = im.naturalHeight; if (!iw || !ih) return;
    var s = Math.max(w / iw, h / ih), dw = iw * s, dh = ih * s;
    try { g.drawImage(im, (w - dw) / 2, (h - dh) / 2, dw, dh); } catch (_) {}
  }

  /* ---- AK-ARCART 2026-07-18: sensory layer bridge -------------------------
   * systems/juice.js is already on disk and loaded at index.html:440, AHEAD of
   * this file. We write NO new effects: impact/reward moments call the shared
   * ladder (J.impact picks the 5-tier haptic + shake amplitude, J.raritySting
   * and J.bonus fire the reward rungs). Every call is guarded, so a page
   * without juice.js keeps the old silent behaviour.
   * ---------------------------------------------------------------------- */
  function JU() { return global.AK_JUICE || null; }
  // impact -> haptic now + a shake amplitude parked on the run state. The
  // launcher reads r._shT / r._sh and translates the canvas on play frames.
  function jolt(r, mag) {
    var j = JU(), amp = 0;
    if (j && j.impact) { try { amp = (j.impact(mag) || {}).shake | 0; } catch (_) {} }
    if (r && amp > 0) { r._sh = Math.max(r._sh | 0, amp); r._shT = 0.24; }
    return amp;
  }
  function jhap(k) { var j = JU(); if (j && j.haptic) { try { j.haptic(k); } catch (_) {} } }
  function jsting(rar) { var j = JU(); if (j && j.raritySting) { try { j.raritySting(rar); } catch (_) {} } }
  function jbonus(n) { var j = JU(); if (j && j.bonus) { try { j.bonus(n); } catch (_) {} } }

  /* ====================================================================== *
   * profile slice (p.arcade) -- daily ledger + per-game records
   *   p.arcade = { _meta:{day,gold,bones,plays}, <gameId>:{best,plays,lastReward} }
   * ====================================================================== */
  function arcadeSnapshot(ctx) {
    var e = econ(ctx);
    var snap = { day: today(), dayGold: 0, dayBones: 0, dayPlays: 0, games: {} };
    if (!e) return snap;
    var p = e.loadProfile(); var a = (p && p.arcade && typeof p.arcade === 'object') ? p.arcade : {};
    var m = a._meta || {};
    if (m.day === snap.day) { snap.dayGold = m.gold | 0; snap.dayBones = m.bones | 0; snap.dayPlays = m.plays | 0; }
    snap.games = a; return snap;
  }
  function bestFor(ctx, id) {
    var e = econ(ctx); if (!e) return 0;
    var p = e.loadProfile(); var g = (p.arcade && p.arcade[id]) || {}; return g.best | 0;
  }
  function goldRoom(ctx) { var s = arcadeSnapshot(ctx); return Math.max(0, DAILY_GOLD_CAP - s.dayGold); }

  // Apply caps, write best/plays/daily ledgers, then grant soft currency + the
  // CREW-TRAINING yield that feeds the RPG. res = the run's frame result
  // {gold,bones,score}; def supplies an optional def.train(res) ->
  // {sp,produce,scrap,trophies}. Every crew reward is soft + parity-safe (never
  // gems) and rides its OWN daily ledger, so the cabinets feed the pack but can
  // never be farmed past the cap. Returns the paid summary (+ a crew note).
  function grantReward(ctx, def, res) {
    res = res || {};
    var id = def.id, rawGold = res.gold | 0, rawBones = res.bones | 0, score = res.score | 0;
    var e = econ(ctx);
    var out = { gold: 0, bones: 0, score: score, best: 0, capped: false, gameId: id,
                sp: 0, produce: 0, scrap: 0, trophies: 0, note: '' };
    if (!e) return out;
    // per-game crew-training WANT (guarded; weak runs yield 0 so only good runs feed)
    var want = { sp: 0, produce: 0, scrap: 0, trophies: 0 }, wantAny = false;
    if (def.train) {
      try {
        var t = def.train(res) || {};
        want.sp = t.sp | 0; want.produce = t.produce | 0; want.scrap = t.scrap | 0; want.trophies = t.trophies | 0;
        wantAny = (want.sp + want.produce + want.scrap + want.trophies) > 0;
      } catch (_t) {}
    }
    var d = today();
    e.mutateProfile(function (p) {
      if (!p.arcade || typeof p.arcade !== 'object') p.arcade = {};
      var a = p.arcade;
      var m = a._meta || { day: d, gold: 0, bones: 0, plays: 0 };
      if (m.day !== d) m = { day: d, gold: 0, bones: 0, plays: 0 };
      var g = a[id] || { best: 0, plays: 0, lastReward: 0 };

      var gRoom = Math.max(0, DAILY_GOLD_CAP - (m.gold | 0));
      var bRoom = Math.max(0, DAILY_BONES_CAP - (m.bones | 0));
      var payG = clamp(rawGold, 0, gRoom);
      var payB = clamp(rawBones, 0, bRoom);
      // crew-training rooms -- own daily ledger fields (falsy-default => zero-state safe)
      var spRoom = Math.max(0, DAILY_SP_CAP - (m.sp | 0));
      var prRoom = Math.max(0, DAILY_PRODUCE_CAP - (m.produce | 0));
      var trRoom = Math.max(0, DAILY_TROPHY_CAP - (m.trophies | 0));
      var scRoom = Math.max(0, DAILY_SCRAP_CAP - (m.scrap | 0));
      var paySP = clamp(want.sp, 0, spRoom), payPr = clamp(want.produce, 0, prRoom);
      var payTr = clamp(want.trophies, 0, trRoom), paySc = clamp(want.scrap, 0, scRoom);
      out.capped = (payG < rawGold) || (payB < rawBones) ||
                   (paySP < want.sp) || (payPr < want.produce) || (payTr < want.trophies) || (paySc < want.scrap);

      // crew XP lands INSIDE this atomic write (soft fields only; gems untouched)
      if (paySP > 0) p.sp = Math.max(0, (p.sp | 0) + paySP);
      if (payPr > 0) p.produce = Math.max(0, (p.produce | 0) + payPr);
      if (paySc > 0) { if (!p.scrap || typeof p.scrap !== 'object') p.scrap = {}; p.scrap.Common = Math.max(0, (p.scrap.Common | 0) + paySc); }

      g.plays = (g.plays | 0) + 1;
      g.lastReward = payG;
      if (score > (g.best | 0)) g.best = score;
      m.gold = (m.gold | 0) + payG; m.bones = (m.bones | 0) + payB; m.plays = (m.plays | 0) + 1;
      m.sp = (m.sp | 0) + paySP; m.produce = (m.produce | 0) + payPr;
      m.trophies = (m.trophies | 0) + payTr; m.scrap = (m.scrap | 0) + paySc;
      a[id] = g; a._meta = m;
      out.gold = payG; out.bones = payB; out.best = g.best | 0;
      out.sp = paySP; out.produce = payPr; out.scrap = paySc; out.trophies = payTr;
    });
    // soft-currency grants ride the sanctioned ctx helper (one atomic write each)
    if (out.gold > 0) ctx.currency.grant('gold', out.gold);
    if (out.bones > 0) ctx.currency.grant('bones', out.bones);
    // rank pips move the ONE shared ladder via the AK_ECON helper (its own write)
    if (out.trophies > 0 && e.addTrophies) { try { e.addTrophies(out.trophies); } catch (_r) {} }
    out.note = crewNote(def, out, wantAny);
    return out;
  }

  // One-line gritty crew-contribution note for the over screen + close banner --
  // ties the cabinet run back to the pack's climb (the mini-game FEEDS the RPG).
  function crewNote(def, out, wantAny) {
    var bits = [];
    if (out.sp > 0) bits.push('+' + out.sp + ' skill');
    if (out.produce > 0) bits.push('+' + out.produce + ' supplies');
    if (out.scrap > 0) bits.push('+' + out.scrap + ' scrap');
    if (out.trophies > 0) bits.push('+' + out.trophies + ' rank');
    if (bits.length) return (def.crewLead || 'Your crew sharpened up') + ' -- ' + bits.join(', ');
    if (wantAny) return 'Crew\'s tapped for the day -- come back fresh tomorrow.';
    return 'Crew clocked in -- run it cleaner to level the pack.';
  }

  /* ====================================================================== *
   * SHARED OVERLAY CHROME (background, close button, intro, over screen)
   * Each game def supplies: { id,title,how,unit,accent, reset, frame, tap }
   * reset(vp,ctx) -> run-state ; frame(g,dt,vp,run,ctx) -> result|null ;
   * tap(px,py,vp,run,ctx). The launcher owns intro/over/close + reward grant.
   * ====================================================================== */
  // Gritty gold-cyberpunk board backdrop. Built ONCE per viewport size into an
  // offscreen canvas (single-slot cache) and blitted with one drawImage/frame --
  // so the grid + scanlines + vignette cost nothing in the hot loop (no per-frame
  // shadowBlur, transforms only). Static texture -> prefers-reduced-motion N/A.
  var _bg = { key: '', cv: null };
  function buildBg(w, h) {
    var cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    var g = cv.getContext('2d'); if (!g) return null;
    // warm dark base + radial core (brand dark #15110a over INK)
    g.fillStyle = INK; g.fillRect(0, 0, w, h);
    var core = g.createRadialGradient(w / 2, h * 0.34, 30, w / 2, h * 0.5, Math.max(w, h));
    core.addColorStop(0, '#15110a'); core.addColorStop(1, INK);
    g.fillStyle = core; g.fillRect(0, 0, w, h);
    // neon city under-glow rising from the floor
    var glow = g.createRadialGradient(w / 2, h * 1.04, 20, w / 2, h * 1.04, h * 0.72);
    glow.addColorStop(0, 'rgba(201,168,76,.16)'); glow.addColorStop(1, 'rgba(201,168,76,0)');
    g.fillStyle = glow; g.fillRect(0, 0, w, h);
    // --- gold perspective grid floor (lower ~42%) ---
    var horizon = h * 0.58, vx = w / 2;
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.10)';
    var cols = 14;
    for (var i = 0; i <= cols; i++) {           // verticals converge to vanishing point
      g.beginPath(); g.moveTo(vx, horizon); g.lineTo((i / cols) * w, h); g.stroke();
    }
    for (var k = 1; k <= 9; k++) {              // horizontals recede (ease toward floor)
      var t = k / 9, yy = horizon + (h - horizon) * (t * t);
      g.globalAlpha = 0.04 + 0.10 * t;
      g.beginPath(); g.moveTo(0, yy); g.lineTo(w, yy); g.stroke();
    }
    g.globalAlpha = 1;
    g.strokeStyle = 'rgba(232,197,90,.22)'; g.lineWidth = 1.5;   // horizon glow line
    g.beginPath(); g.moveTo(0, horizon); g.lineTo(w, horizon); g.stroke();
    // --- CRT scanlines (mirrors shop.css repeating-linear scanline) ---
    g.fillStyle = 'rgba(0,0,0,.10)';
    for (var y = 0; y < h; y += 3) g.fillRect(0, y, w, 1);
    // --- vignette ---
    var vg = g.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.3, w / 2, h / 2, Math.max(w, h) * 0.62);
    vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.55)');
    g.fillStyle = vg; g.fillRect(0, 0, w, h);
    // --- inset gold edge frame (glass vocabulary) ---
    g.strokeStyle = 'rgba(201,168,76,.30)'; g.lineWidth = 1.5;
    rr(g, 4, 4, w - 8, h - 8, 14); g.stroke();
    return cv;
  }
  function drawBg(g, vp, gameId) {
    // AK-ARCART 2026-07-18: themed photo plate UNDER the procedural chrome. The
    // grid + scanlines + vignette still paint (at 55%) so the board reads the
    // same; if the plate is missing we take the original full-opacity path.
    var photo = gameId ? art(ART_BG[gameId]) : null, lit = ready(photo);
    if (lit) {
      g.save();
      try {
        drawCover(g, photo, vp.w, vp.h);
        g.fillStyle = 'rgba(6,6,10,.58)'; g.fillRect(0, 0, vp.w, vp.h);  // keep the play field legible
      } catch (_p) { lit = false; }
      g.restore();
    }
    if (typeof document === 'undefined' || !document.createElement) {   // headless fallback
      if (lit) return;
      g.fillStyle = INK; g.fillRect(0, 0, vp.w, vp.h);
      var grd = g.createRadialGradient(vp.w / 2, vp.h * 0.34, 30, vp.w / 2, vp.h * 0.5, Math.max(vp.w, vp.h));
      grd.addColorStop(0, '#15110a'); grd.addColorStop(1, INK);
      g.fillStyle = grd; g.fillRect(0, 0, vp.w, vp.h); return;
    }
    var w = Math.max(1, Math.round(vp.w)), h = Math.max(1, Math.round(vp.h)), key = w + 'x' + h;
    if (_bg.key !== key || !_bg.cv) { try { _bg.cv = buildBg(w, h); _bg.key = key; } catch (_e) { _bg.cv = null; } }
    if (_bg.cv) {
      try {
        if (lit) { g.save(); g.globalAlpha = 0.55; g.drawImage(_bg.cv, 0, 0, vp.w, vp.h); g.restore(); }
        else g.drawImage(_bg.cv, 0, 0, vp.w, vp.h);
        return;
      } catch (_d) {}
    }
    if (!lit) { g.fillStyle = INK; g.fillRect(0, 0, vp.w, vp.h); }       // last-resort fill
  }
  function drawChrome(g, vp, def, st) {
    // title strip
    htxt(g, def.title, vp.w / 2, 30, 17, GOLD);
    // close (X) -- top right, always live
    var cb = { x: vp.w - 30, y: 32, r: 17 }; st.btns.close = cb;
    g.fillStyle = 'rgba(192,57,43,.22)'; g.beginPath(); g.arc(cb.x, cb.y, cb.r, 0, 7); g.fill();
    g.strokeStyle = RED; g.lineWidth = 2; g.beginPath(); g.arc(cb.x, cb.y, cb.r, 0, 7); g.stroke();
    txt(g, '✕', cb.x, cb.y + 1, 16, '#ffd5cf', 'center', '900');
  }
  function panel(g, vp, h) {
    var w = Math.min(vp.w - 48, 420), x = (vp.w - w) / 2, y = (vp.h - h) / 2;
    g.fillStyle = 'rgba(10,9,14,.86)'; rr(g, x, y, w, h, 16); g.fill();
    g.strokeStyle = 'rgba(201,168,76,.55)'; g.lineWidth = 2; rr(g, x, y, w, h, 16); g.stroke();
    return { x: x, y: y, w: w, h: h };
  }
  function drawIntro(g, vp, def, ctx, st) {
    var p = panel(g, vp, 300); var cx = vp.w / 2;
    htxt(g, def.title, cx, p.y + 40, 24, GOLD);
    var words = String(def.how).split(' '), line = '', yy = p.y + 88, lim = p.w - 48;
    g.font = '600 14px Inter, system-ui, sans-serif';
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + ' ' + words[i] : words[i];
      if (g.measureText(test).width > lim && line) { txt(g, line, cx, yy, 14, DIM, 'center', '600'); line = words[i]; yy += 22; }
      else line = test;
    }
    if (line) txt(g, line, cx, yy, 14, DIM, 'center', '600');
    txt(g, 'TRAINS YOUR CREW -- skill, supplies + rank feed the pack', cx, p.y + p.h - 100, 11, GOLD_D, 'center', '700');
    txt(g, 'BEST: ' + bestFor(ctx, def.id) + ' ' + def.unit, cx, p.y + p.h - 78, 13, TEAL, 'center', '700');
    var room = goldRoom(ctx);
    txt(g, room > 0 ? ('Daily haul left: ' + room + ' gold') : 'Daily haul maxed -- play for glory', cx, p.y + p.h - 56, 12, DIM, 'center', '600');
    // big tap-to-play pulse
    var pulse = 0.5 + 0.5 * Math.sin(Date.now() / 320);
    g.globalAlpha = 0.65 + 0.35 * pulse;
    txt(g, 'TAP TO PLAY', cx, p.y + p.h - 28, 18, GOLD, 'center', '900');
    g.globalAlpha = 1;
  }
  function drawOver(g, vp, def, st) {
    var s = st.summary || { gold: 0, bones: 0, score: 0, best: 0, capped: false };
    var p = panel(g, vp, 300); var cx = vp.w / 2;
    htxt(g, 'RUN OVER', cx, p.y + 38, 22, GOLD);
    txt(g, 'SCORE  ' + (s.score | 0) + ' ' + def.unit, cx, p.y + 78, 16, TXT, 'center', '800');
    txt(g, 'BEST  ' + (s.best | 0) + ' ' + def.unit, cx, p.y + 104, 13, DIM, 'center', '600');
    txt(g, '+ ' + (s.gold | 0) + ' GOLD' + (s.bones ? '   + ' + s.bones + ' BONES' : ''), cx, p.y + 134, 17, TEAL, 'center', '900');
    if (s.note) {
      g.font = '700 12px Inter, system-ui, sans-serif';
      var nf = (g.measureText(s.note).width > p.w - 28) ? 10.5 : 12;
      txt(g, s.note, cx, p.y + 162, nf, GOLD, 'center', '700');   // crew-contribution note (FEEDS the RPG)
    }
    if (s.capped) txt(g, '(daily cap reached)', cx, p.y + 184, 11, RED, 'center', '600');
    // buttons
    var bw = (p.w - 56) / 2, by = p.y + p.h - 60, bh = 42;
    var again = { x: p.x + 20, y: by, w: bw, h: bh }, exit = { x: p.x + p.w - 20 - bw, y: by, w: bw, h: bh };
    st.btns.again = again; st.btns.exit = exit;
    g.fillStyle = GOLD_D; rr(g, again.x, again.y, bw, bh, 10); g.fill();
    txt(g, 'PLAY AGAIN', again.x + bw / 2, by + bh / 2, 14, '#15110a', 'center', '900');
    g.fillStyle = 'rgba(201,168,76,.12)'; rr(g, exit.x, exit.y, bw, bh, 10); g.fill();
    g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1.5; rr(g, exit.x, exit.y, bw, bh, 10); g.stroke();
    txt(g, 'EXIT', exit.x + bw / 2, by + bh / 2, 14, DIM, 'center', '800');
  }

  function launchGame(ctx, def, opts) {
    if (!ctx || !ctx.overlay || !def) return false;
    opts = opts || {};
    var st = { phase: 'intro', run: null, summary: null, btns: {} };
    var api = ctx.overlay.open({
      id: 'arcade_' + def.id,
      onFrame: function (g, dt, vp) {
        drawBg(g, vp, def.id);                          // AK-ARCART: themed photo plate
        if (st.phase === 'play') {
          // AK-ARCART 2026-07-18: juice shake. Amplitude comes from AK_JUICE.impact
          // (the shared 5-tier ladder) via jolt(); we only decay + translate here,
          // and only over the play field so the chrome never wobbles.
          var r = st.run, sx = 0, sy = 0;
          if (r && r._shT > 0) {
            r._shT -= dt;
            var amp = (r._sh | 0) * clamp(r._shT / 0.24, 0, 1);
            sx = (Math.random() * 2 - 1) * amp; sy = (Math.random() * 2 - 1) * amp;
            if (r._shT <= 0) { r._sh = 0; r._shT = 0; }
          }
          if (sx || sy) { g.save(); g.translate(sx, sy); }
          var res = null;
          try { res = def.frame(g, dt, vp, st.run, ctx); } catch (_e) { res = { gold: 0, bones: 0, score: 0 }; }
          if (sx || sy) g.restore();
          if (res) {
            st.summary = grantReward(ctx, def, res);
            // AK-ARCART: reward rungs climb with how many ledgers actually paid
            // (juice.js bonus_1..4), then one sting sized to the best line item.
            var S = st.summary, rung = 0;
            if (S.gold > 0) rung++;
            if (S.bones > 0) rung++;
            if (S.sp > 0 || S.produce > 0 || S.scrap > 0) rung++;
            if (S.trophies > 0) rung++;
            if (rung > 0) { jbonus(rung); jsting(S.trophies > 0 ? 'Legendary' : (S.bones > 0 ? 'Epic' : 'Rare')); }
            if (opts.onReward) try { opts.onReward(st.summary); } catch (_o) {}
            st.phase = 'over';
          }
        }
        drawChrome(g, vp, def, st);
        if (st.phase === 'intro') drawIntro(g, vp, def, ctx, st);
        else if (st.phase === 'over') drawOver(g, vp, def, st);
      },
      onPointer: function (evt) {
        if (!evt || evt.type !== 'pointerdown') return;
        var px = evt.clientX, py = evt.clientY, vp = api.vp;
        if (hitC(px, py, st.btns.close)) { api.close(st.phase === 'over' ? st.summary : null); return; }
        if (st.phase === 'intro') { st.run = def.reset(vp, ctx); st.phase = 'play'; return; }
        if (st.phase === 'play') { try { def.tap && def.tap(px, py, vp, st.run, ctx); } catch (_e) {} return; }
        if (st.phase === 'over') {
          if (hitR(px, py, st.btns.again)) { st.summary = null; st.run = def.reset(vp, ctx); st.phase = 'play'; return; }
          if (hitR(px, py, st.btns.exit)) { api.close(st.summary); return; }
        }
      },
      onClose: function (res) { onGameClose(ctx, res, opts); }
    });
    return true;
  }

  function onGameClose(ctx, res, opts) {
    try {
      if (res && res.note && (res.sp || res.produce || res.scrap || res.trophies)) {
        ctx.showBanner(res.note, 2.4);                          // crew-training feed (the RPG payoff)
      } else if (res && (res.gold || res.bones)) {
        var t = '+' + (res.gold | 0) + ' gold' + (res.bones ? '  +' + res.bones + ' bones' : '');
        ctx.showBanner('ARCADE HAUL  ' + t + (res.capped ? '  (capped)' : ''), 2.0);
      } else if (res) {
        ctx.showBanner('NICE RUN -- crew\'s maxed for the day', 1.6);
      }
    } catch (_b) {}
    if (opts && opts.keeper) try { renderArcadeKeeper(ctx); } catch (_k) {}
    if (opts && opts.onDone) try { opts.onDone(res); } catch (_d) {}
  }

  /* ====================================================================== *
   * GAME 1 -- BONE DIG (grid-match / concentration)
   * ====================================================================== */
  // AK-ARCART 2026-07-18: each face now names a real icon (k); the emoji is the
  // fallback the tile paints only while the art is dead or still streaming.
  var DIG_ICONS = [
    { g: '🦴', c: GOLD,      k: 'dig_bone' },   // bone
    { g: '⚙️', c: '#ff9d5c', k: 'dig_gear' },  // gear
    { g: '⚡', c: TEAL,            k: 'dig_bolt' },   // bolt
    { g: '👑', c: GOLD,      k: 'dig_crown' },  // crown
    { g: '🐾', c: '#9B8CFF', k: 'dig_paw' },   // paw
    { g: '🔧', c: RED,       k: 'dig_wrench' },// wrench
    { g: '💎', c: '#7fc8ff', k: 'dig_gem' },   // gem
    { g: '🃏', c: '#7FE3A0', k: 'dig_card' }   // card
  ];
  // one tile face: real icon, else the original glyph draw
  function digFace(g, sym, x, y, sz) {
    var ic = DIG_ICONS[sym]; if (!ic) return;
    if (drawSpr(g, ic.k, x, y, sz)) return;
    txt(g, ic.g, x, y, Math.round(sz * 0.9), ic.c, 'center');
  }
  var bone_dig = {
    id: 'bone_dig', title: 'BONE DIG', unit: 'pts', accent: GOLD,
    how: 'Flip tiles two at a time. Match the buried bones before the 60s clock runs dry. Clear the board for a perfect haul.',
    crewLead: 'Crew dug the block\'s stashes',
    // memory drill -> sharper instincts (skill) + dug-up supplies; a perfect
    // clear unearths a scrap part. No rank pips (digging is not proving ground).
    train: function (res) {
      var sc = res.score | 0, perfect = (res.bones | 0) > 0;   // bones pay ONLY on a full clear
      return { sp: perfect ? 2 : (sc >= 400 ? 1 : 0),
        produce: clamp(Math.floor(sc / 120), 0, 8),
        scrap: perfect ? 1 : 0, trophies: 0 };
    },
    reset: function (vp, ctx) {
      var syms = []; for (var i = 0; i < 8; i++) { syms.push(i); syms.push(i); }
      for (var j = syms.length - 1; j > 0; j--) { var k = Math.floor(Math.random() * (j + 1)); var t = syms[j]; syms[j] = syms[k]; syms[k] = t; }
      return { grid: syms.map(function (s) { return { sym: s, flip: false, match: false }; }),
        first: -1, lockT: 0, time: 60, matches: 0, combo: 0, score: 0, cells: [] };
    },
    frame: function (g, dt, vp, r, ctx) {
      if (r.lockT > 0) { r.lockT -= dt; if (r.lockT <= 0) { for (var i = 0; i < 16; i++) if (r.grid[i].flip && !r.grid[i].match) r.grid[i].flip = false; r.first = -1; } }
      else r.time -= dt;
      // layout 4x4
      var side = Math.min(vp.w - 40, vp.h - 200), cell = side / 4, ox = (vp.w - side) / 2, oy = 96, pad = cell * 0.08;
      r.cells = [];
      for (var n = 0; n < 16; n++) {
        var cxx = ox + (n % 4) * cell, cyy = oy + Math.floor(n / 4) * cell;
        var tile = r.grid[n]; r.cells.push({ x: cxx + pad, y: cyy + pad, w: cell - pad * 2, h: cell - pad * 2 });
        var rc = r.cells[n];
        // AK-ARCART: faces + the buried-stash back are real icons now (glyph fallback inside digFace/drawSpr)
        if (tile.match) { g.fillStyle = 'rgba(124,255,224,.16)'; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.fill(); g.strokeStyle = TEAL; g.lineWidth = 2; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.stroke(); digFace(g, tile.sym, rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.44)); }
        else if (tile.flip) { g.fillStyle = 'rgba(232,197,90,.14)'; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.fill(); g.strokeStyle = GOLD; g.lineWidth = 2; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.stroke(); digFace(g, tile.sym, rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.44)); }
        else { g.fillStyle = 'rgba(28,22,16,.95)'; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.fill(); g.strokeStyle = 'rgba(201,168,76,.35)'; g.lineWidth = 1.5; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.stroke(); if (!drawSpr(g, 'dig_back', rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.36), 0.4)) txt(g, '🦴', rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.3), 'rgba(201,168,76,.30)', 'center'); }
      }
      // hud
      txt(g, 'TIME ' + Math.max(0, Math.ceil(r.time)), ox + 4, 64, 15, r.time < 10 ? RED : TXT, 'left', '800');
      txt(g, 'PAIRS ' + r.matches + '/8', ox + side - 4, 64, 15, GOLD, 'right', '800');
      if (r.matches >= 8 || r.time <= 0) {
        var tb = Math.max(0, Math.round(r.time)), perfect = r.matches >= 8;
        return { gold: r.matches * 10 + (perfect ? tb * 2 : 0), bones: perfect ? 3 : 0, score: r.matches * 100 + tb + r.combo * 15 };
      }
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      if (r.lockT > 0) return;
      var idx = -1; for (var i = 0; i < r.cells.length; i++) if (hitR(px, py, r.cells[i])) { idx = i; break; }
      if (idx < 0) return; var t = r.grid[idx]; if (t.flip || t.match) return;
      t.flip = true;
      if (r.first < 0) { r.first = idx; return; }
      // AK-ARCART: juice on the dig -- a match escalates with the combo, a miss taps the low rung
      if (r.grid[r.first].sym === t.sym) { r.grid[r.first].match = true; t.match = true; r.matches++; r.combo++; r.score += 10; r.first = -1; jolt(r, 55 + r.combo * 22); }
      else { r.combo = 0; r.lockT = 0.7; jhap('hit_1'); }   // frame flips both back after the peek
    }
  };

  /* ====================================================================== *
   * GAME 2 -- ALLEY DASH (one-tap endless runner)
   * ====================================================================== */
  var alley_dash = {
    id: 'alley_dash', title: 'ALLEY DASH', unit: 'm', accent: TEAL,
    how: 'TAP to jump (double-tap = double jump). Dodge the pound drones. Go the distance -- gold scales with how far the pack runs.',
    crewLead: 'Pack ran the block till dawn',
    // roadwork -> conditioning (skill) + scavenged supplies; the further the pack
    // runs the more it proves itself, so distance also climbs the shared rank.
    train: function (res) {
      var d = res.score | 0;
      return { sp: clamp(Math.floor(d / 250), 0, 3),
        produce: clamp(Math.floor(d / 30), 0, 12),
        scrap: d >= 600 ? 1 : 0,
        trophies: (d >= 200 ? 1 : 0) + (d >= 450 ? 1 : 0) + (d >= 750 ? 1 : 0) };
    },
    reset: function (vp, ctx) {
      var groundY = vp.h - 86;
      return { gx: vp.w * 0.26, gy: groundY - 26, vy: 0, r: 26, grounded: true, jumps: 0,
        obs: [], spawnT: 0.9, speed: 330, dist: 0, dead: false, overT: 0, scroll: 0 };
    },
    frame: function (g, dt, vp, r, ctx) {
      var groundY = vp.h - 86;
      if (!r.dead) {
        r.speed += 13 * dt; r.dist += r.speed * dt / 26; r.scroll = (r.scroll + r.speed * dt) % 80;
        r.vy += 2300 * dt; r.gy += r.vy * dt;
        if (r.gy >= groundY - r.r) { r.gy = groundY - r.r; r.vy = 0; r.grounded = true; r.jumps = 0; } else r.grounded = false;
        r.spawnT -= dt;
        if (r.spawnT <= 0) { r.obs.push({ x: vp.w + 30, w: ri(22, 40), h: ri(34, 66) }); r.spawnT = clamp(1.15 - r.speed / 1300, 0.52, 1.1) * (0.8 + Math.random() * 0.55); }
        for (var i = r.obs.length - 1; i >= 0; i--) {
          var o = r.obs[i]; o.x -= r.speed * dt;
          if (o.x + o.w < -20) { r.obs.splice(i, 1); continue; }
          var oy = groundY - o.h;
          if (r.gx + r.r * 0.7 > o.x && r.gx - r.r * 0.7 < o.x + o.w && r.gy + r.r > oy) { r.dead = true; jolt(r, 260); }   // AK-ARCART: top-rung wipeout
        }
      } else r.overT += dt;
      // ground
      g.strokeStyle = 'rgba(124,255,224,.35)'; g.lineWidth = 2; g.beginPath(); g.moveTo(0, groundY); g.lineTo(vp.w, groundY); g.stroke();
      g.fillStyle = 'rgba(124,255,224,.5)';
      for (var x = -((r.scroll) % 80); x < vp.w; x += 80) g.fillRect(x, groundY + 6, 34, 3);
      // obstacles (pound drones)
      // AK-ARCART: the drone is real hazard art; the red block is the fallback
      for (var j = 0; j < r.obs.length; j++) {
        var b = r.obs[j], by = groundY - b.h;
        if (drawSpr(g, 'drone', b.x + b.w / 2, by + b.h / 2, Math.max(b.w, b.h) * 1.2)) continue;
        g.fillStyle = 'rgba(192,57,43,.85)'; rr(g, b.x, by, b.w, b.h, 5); g.fill(); g.strokeStyle = '#ff7a6b'; g.lineWidth = 1.5; rr(g, b.x, by, b.w, b.h, 5); g.stroke(); txt(g, '⛔', b.x + b.w / 2, by + b.h / 2, Math.min(b.w, 20), '#fff', 'center');
      }
      // runner ($BCARDD)
      drawDog(g, cardFor(ctx, GOLD_DOG), '🐕', r.gx, r.gy, r.r, GOLD);
      // hud
      txt(g, Math.floor(r.dist) + ' m', vp.w / 2, 62, 18, GOLD, 'center', '900');
      if (r.dead && r.overT > 0.5) {
        var dist = Math.floor(r.dist);
        return { gold: clamp(Math.floor(dist / 6), 0, 180), bones: dist >= 400 ? 3 : (dist >= 200 ? 1 : 0), score: dist };
      }
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      if (r.dead) return;
      // AK-ARCART: launch haptic off the shared ladder (deploy = the light kick)
      if (r.grounded) { r.vy = -880; r.jumps = 1; r.grounded = false; jhap('deploy'); }
      else if (r.jumps < 2) { r.vy = -780; r.jumps = 2; jhap('card_draw'); }
    }
  };

  /* ====================================================================== *
   * GAME 3 -- WHACK-A-STRAY (reaction)
   * ====================================================================== */
  function rollKind() { var x = Math.random(); if (x < 0.12) return 'gold'; if (x < 0.30) return 'pup'; return 'stray'; }
  var whack = {
    id: 'whack', title: 'WHACK-A-STRAY', unit: 'pts', accent: '#9B8CFF',
    how: 'TAP the strays before they duck. The gold $BCARDD is a jackpot. Do NOT whack your own crew pup -- it kills your combo.',
    crewLead: 'Crew drilled hands on the strays',
    // sparring -> reflexes (skill) + a little scavenge; beating back rival strays
    // is combat proof, so a sharp score climbs the shared rank ladder.
    train: function (res) {
      var s = res.score | 0;
      return { sp: clamp(Math.floor(s / 18), 0, 3),
        produce: clamp(Math.floor(s / 12), 0, 6),
        scrap: 0,
        trophies: (s >= 20 ? 1 : 0) + (s >= 45 ? 1 : 0) + (s >= 70 ? 1 : 0) };
    },
    reset: function (vp, ctx) {
      var holes = []; for (var i = 0; i < 9; i++) holes.push({ kind: null, card: null, up: 0, life: 0, max: 1 });
      return { holes: holes, time: 30, score: 0, combo: 0, spawnT: 0.5, geo: [], pops: [] };
    },
    frame: function (g, dt, vp, r, ctx) {
      r.time -= dt;
      r.spawnT -= dt;
      if (r.spawnT <= 0 && r.time > 0) {
        var empty = []; for (var i = 0; i < 9; i++) if (!r.holes[i].kind) empty.push(i);
        if (empty.length) {
          var h = empty[ri(0, empty.length - 1)], k = rollKind();
          var hl = clamp(1.3 - (30 - r.time) / 45, 0.62, 1.3);
          r.holes[h].kind = k; r.holes[h].life = hl; r.holes[h].max = hl; r.holes[h].up = 0;
          r.holes[h].card = (k === 'gold') ? GOLD_DOG : (k === 'pup') ? CREW_PUP : WILD_STRAYS[ri(0, WILD_STRAYS.length - 1)];
        }
        r.spawnT = clamp(0.8 - (30 - r.time) / 60, 0.3, 0.8);
      }
      for (var n = 0; n < 9; n++) { var H = r.holes[n]; if (H.kind) { H.life -= dt; H.up = Math.sin(clamp(1 - H.life / H.max, 0, 1) * Math.PI); if (H.life <= 0) { H.kind = null; H.up = 0; } } }
      // layout 3x3
      var side = Math.min(vp.w - 40, vp.h - 200), cell = side / 3, ox = (vp.w - side) / 2, oy = 100, rad = cell * 0.34;
      r.geo = [];
      for (var m = 0; m < 9; m++) {
        var hx = ox + (m % 3) * cell + cell / 2, hy = oy + Math.floor(m / 3) * cell + cell / 2;
        r.geo.push({ cx: hx, cy: hy, r: rad });
        // hole (dark pit + gritty gold rim)
        g.fillStyle = 'rgba(0,0,0,.55)'; g.beginPath(); g.ellipse(hx, hy + rad * 0.55, rad * 1.05, rad * 0.5, 0, 0, 7); g.fill();
        g.strokeStyle = 'rgba(201,168,76,.45)'; g.lineWidth = 2; g.beginPath(); g.ellipse(hx, hy + rad * 0.55, rad * 1.05, rad * 0.5, 0, 0, 7); g.stroke();
        var HH = r.holes[m];
        if (HH.kind && HH.up > 0.02) {
          var dy = rad * (1 - HH.up), accent = HH.kind === 'gold' ? GOLD : HH.kind === 'pup' ? '#7FE3A0' : '#cdbb86';
          var gl = HH.kind === 'gold' ? '👑' : HH.kind === 'pup' ? '🐶' : '🐕';
          drawDog(g, cardFor(ctx, HH.card), gl, hx, hy - rad * 0.2 + dy, rad * 0.92, accent);
          // AK-ARCART: the do-not-hit marker is the real crew chip, glyph text as fallback
          if (HH.kind === 'pup' && !drawSpr(g, 'crew_tag', hx, hy - rad * 1.25 + dy, 22)) { txt(g, 'CREW', hx, hy - rad * 1.05 + dy, 10, '#7FE3A0', 'center', '900'); }
        }
      }
      // pops
      for (var q = r.pops.length - 1; q >= 0; q--) { var P = r.pops[q]; P.t -= dt; if (P.t <= 0) { r.pops.splice(q, 1); continue; } g.globalAlpha = clamp(P.t / 0.5, 0, 1); txt(g, P.s, P.x, P.y - (0.5 - P.t) * 40, 16, P.good ? TEAL : RED, 'center', '900'); g.globalAlpha = 1; }
      // hud
      txt(g, 'TIME ' + Math.max(0, Math.ceil(r.time)), ox + 4, 66, 15, r.time < 6 ? RED : TXT, 'left', '800');
      txt(g, 'SCORE ' + r.score, ox + side - 4, 66, 15, GOLD, 'right', '800');
      if (r.combo > 2) txt(g, 'x' + r.combo + ' COMBO', vp.w / 2, 66, 13, TEAL, 'center', '800');
      if (r.time <= 0) return { gold: clamp(r.score * 4, 0, 160), bones: r.score >= 45 ? 2 : 0, score: r.score };
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      for (var i = 0; i < 9; i++) {
        var geo = r.geo[i], H = r.holes[i]; if (!geo || !H.kind || H.up <= 0.35) continue;
        if (Math.hypot(px - geo.cx, py - (geo.cy - geo.r * 0.2)) <= geo.r) {
          // AK-ARCART: the hand landing is graded by the shared 5-tier impact ladder
          if (H.kind === 'stray') { r.combo++; r.score += 1 + Math.floor(r.combo / 4); r.pops.push({ x: geo.cx, y: geo.cy, t: 0.5, s: '+' + (1 + Math.floor(r.combo / 4)), good: true }); jolt(r, 25 + r.combo * 12); }
          else if (H.kind === 'gold') { r.combo++; r.score += 5; r.pops.push({ x: geo.cx, y: geo.cy, t: 0.6, s: '+5!', good: true }); jolt(r, 240); jsting('Legendary'); }   // the mascot IS the jackpot
          else { r.combo = 0; r.score = Math.max(0, r.score - 2); r.pops.push({ x: geo.cx, y: geo.cy, t: 0.5, s: '-2', good: false }); jhap('defeat'); }
          H.kind = null; H.up = 0; H.life = 0; return;
        }
      }
    }
  };

  /* ====================================================================== *
   * EMBEDDED MICRO-GAME STUBS (callable by other buildings)
   *   AK_ARCADE.play('gem_tap',  ctx, {keeper, onDone, onReward})  // Gem Mine
   *   AK_ARCADE.play('forge_temper', ctx, {...})                   // Card Forge
   * Functional but intentionally light -- the production wave wires these into
   * its GEM / FORGE keepers. // TODO: production may route forge output to scrap
   * by passing its own onReward (these stubs pay GOLD via the shared cap path).
   * ====================================================================== */
  var gem_tap = {
    id: 'gem_tap', title: 'GEM MINE -- VEIN STRIKE', unit: 'hits', accent: '#b07bff',
    how: 'A drill bit sweeps the rock face. TAP when it crosses the glowing vein. 8 swings -- land the rhythm for a clean haul.',
    crewLead: 'Crew worked the vein',
    // mining -> raw supplies + forge scrap; a clean vein (high hits) yields a
    // little crafting skill. No rank pips (labor, not proving ground).
    train: function (res) {
      var h = res.score | 0;
      return { sp: h >= 7 ? 1 : 0,
        produce: clamp(h * 3, 0, 24),
        scrap: (h >= 6 ? 1 : 0) + (h >= 8 ? 1 : 0),
        trophies: 0 };
    },
    reset: function (vp, ctx) { return { pos: 0, dir: 1, speed: 0.95, lo: 0.42, hi: 0.58, swings: 0, max: 8, hits: 0, score: 0, flash: 0, flashGood: false }; },
    frame: function (g, dt, vp, r, ctx) {
      r.pos += r.dir * r.speed * dt; if (r.pos > 1) { r.pos = 1; r.dir = -1; } else if (r.pos < 0) { r.pos = 0; r.dir = 1; }
      if (r.flash > 0) r.flash -= dt;
      var bx = vp.w * 0.12, bw = vp.w * 0.76, by = vp.h * 0.5, bh = 30;
      g.fillStyle = 'rgba(30,24,40,.95)'; rr(g, bx, by, bw, bh, 8); g.fill();
      g.fillStyle = 'rgba(176,123,255,.40)'; rr(g, bx + bw * r.lo, by, bw * (r.hi - r.lo), bh, 6); g.fill();
      // AK-ARCART: real gem marks the pay band, real drill bit rides the sweep
      drawSpr(g, 'vein', bx + bw * (r.lo + r.hi) / 2, by + bh / 2, bh * 1.1, 0.92);
      var mx = bx + bw * r.pos; g.fillStyle = r.flash > 0 ? (r.flashGood ? TEAL : RED) : GOLD; g.fillRect(mx - 3, by - 10, 6, bh + 20);
      drawSpr(g, 'drill', mx, by - 30, 34);
      txt(g, 'SWING ' + r.swings + '/' + r.max, vp.w / 2, by - 50, 15, TXT, 'center', '800');
      txt(g, 'HITS ' + r.hits, vp.w / 2, by + 64, 15, '#b07bff', 'center', '800');
      if (r.swings >= r.max) return { gold: r.hits * 8, bones: r.hits >= 7 ? 2 : 0, score: r.hits };
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      if (r.swings >= r.max) return;
      var good = r.pos >= r.lo && r.pos <= r.hi; r.swings++; r.flash = 0.25; r.flashGood = good;
      // AK-ARCART: a struck vein climbs the impact ladder with the streak; a dud taps rung 1
      if (good) { r.hits++; r.score++; r.speed += 0.08; var c = (r.hi - r.lo) * 0.86, mid = (r.lo + r.hi) / 2; r.lo = mid - c / 2; r.hi = mid + c / 2; jolt(r, 60 + r.hits * 22); }
      else jhap('hit_1');
    }
  };
  var forge_temper = {
    id: 'forge_temper', title: 'CARD FORGE -- TEMPER', unit: 'pts', accent: '#ff9d5c',
    how: 'The blade heats and cools. TAP to quench inside the gold band -- dead center is a perfect temper. You get 3 quenches; best one counts.',
    crewLead: 'Crew tempered fresh steel',
    // smithing -> forge scrap + smith skill on a clean temper, plus a little
    // produce off-cut. No rank pips (craft bench, not proving ground).
    train: function (res) {
      var b = res.score | 0;
      return { sp: (b >= 80 ? 1 : 0) + (b >= 98 ? 1 : 0),
        produce: clamp(Math.floor(b / 12), 0, 8),
        scrap: (b >= 70 ? 1 : 0) + (b >= 95 ? 1 : 0),
        trophies: 0 };
    },
    reset: function (vp, ctx) { return { val: 0, dir: 1, speed: 0.8, attempts: 3, used: 0, best: 0, flash: 0, locked: false }; },
    frame: function (g, dt, vp, r, ctx) {
      if (!r.locked) { r.val += r.dir * r.speed * dt; if (r.val > 1) { r.val = 1; r.dir = -1; } else if (r.val < 0) { r.val = 0; r.dir = 1; } }
      if (r.flash > 0) { r.flash -= dt; if (r.flash <= 0) r.locked = false; }
      var gx = vp.w / 2, gtop = vp.h * 0.24, gh = vp.h * 0.42, gw = 46;
      // gauge
      var grd = g.createLinearGradient(0, gtop, 0, gtop + gh); grd.addColorStop(0, '#ff5a2c'); grd.addColorStop(0.5, GOLD); grd.addColorStop(1, '#3a6cff');
      g.fillStyle = grd; rr(g, gx - gw / 2, gtop, gw, gh, 10); g.fill();
      // ideal band (center)
      var bandC = 0.5, bandH = 0.14, by = gtop + gh * (1 - (bandC + bandH / 2)); var bh = gh * bandH;
      g.strokeStyle = '#fff'; g.lineWidth = 2; g.strokeRect(gx - gw / 2 - 4, by, gw + 8, bh);
      // marker
      var my = gtop + gh * (1 - r.val); g.fillStyle = r.flash > 0 ? '#fff' : '#0c0a07'; g.fillRect(gx - gw / 2 - 14, my - 3, gw + 28, 6);
      drawSpr(g, 'anvil', vp.w / 2, gtop - 62, 40);   // AK-ARCART: the forge itself sits over the gauge
      txt(g, 'QUENCH ' + r.used + '/' + r.attempts, vp.w / 2, gtop - 28, 15, TXT, 'center', '800');
      txt(g, 'BEST TEMPER ' + r.best, vp.w / 2, gtop + gh + 34, 15, '#ff9d5c', 'center', '800');
      if (r.used >= r.attempts && r.flash <= 0) return { gold: r.best * 4, bones: r.best >= 90 ? 2 : 0, score: r.best };
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      if (r.used >= r.attempts || r.locked) return;
      r.used++; r.locked = true; r.flash = 0.6;
      var q = Math.round(100 * (1 - Math.min(1, Math.abs(r.val - 0.5) / 0.5)));  // 100 at dead center
      // AK-ARCART: the quench hits as hard as it was clean; a true temper stings
      jolt(r, q * 2.4);
      if (q >= 95) jsting('Epic');
      if (q > r.best) r.best = q;
    }
  };

  /* ====================================================================== *
   * registry of all games + public API
   * ====================================================================== */
  var GAMES = { bone_dig: bone_dig, alley_dash: alley_dash, whack: whack, gem_tap: gem_tap, forge_temper: forge_temper };

  /* ---- AK-ARCVID 2026-07-02: ambient video backdrop on the arcade's MAIN
   * panel only (the keeper card / interior screen). Panel <video> pattern:
   * muted loop autoplay playsinline, absolute behind the card content inside
   * #int-bg (its ::after dark gradient keeps painting on top), opacity .45,
   * pointer-events none. onerror removes the node + marks it dead, so the
   * (possibly not-yet-generated) assets/ui_mp4/arcade_amb.mp4 degrades to the
   * existing interior art with zero flicker. Singleton element; the throttled
   * onTick guard pauses/hides it the moment the interior closes, another
   * keeper takes the panel, or the tab hides. ------------------------------ */
  var _ambVid = null, _ambDead = false, _ambChk = 0;
  function mountArcadeAmb() {
    if (_ambDead || typeof document === 'undefined') return;
    var bg = document.getElementById('int-bg'); if (!bg) return;
    if (!_ambVid) {
      var v = document.createElement('video');
      v.id = 'ak-arc-amb'; v.muted = true; v.loop = true; v.autoplay = true;
      v.playsInline = true; v.setAttribute('playsinline', '');
      v.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.45;pointer-events:none;';
      v.onerror = function () { _ambDead = true; _ambVid = null; try { v.remove(); } catch (_) {} };
      v.src = 'assets/ui_mp4/arcade_amb.mp4';
      _ambVid = v;
    }
    if (_ambVid.parentNode !== bg) bg.appendChild(_ambVid);
    _ambVid.style.display = '';
    try { _ambVid.play().catch(function () {}); } catch (_) {}
  }
  function tickArcadeAmb() {
    if (!_ambVid || typeof document === 'undefined') return;
    var now = Date.now(); if (now - _ambChk < 400) return; _ambChk = now;   // throttled -- 60fps safe
    var host = document.getElementById('interior'), pl = document.getElementById('int-place');
    var live = !document.hidden && host && host.style.display !== 'none' &&
               host.style.display !== '' && pl && pl.textContent === 'THE ARCADE';
    if (live) { if (_ambVid.paused) { try { _ambVid.play().catch(function () {}); } catch (_) {} } _ambVid.style.display = ''; }
    else { if (!_ambVid.paused) { try { _ambVid.pause(); } catch (_) {} } _ambVid.style.display = 'none'; }
  }

  function renderArcadeKeeper(ctx) {
    var room = goldRoom(ctx);
    var line = room > 0
      ? ('Step up. These cabinets ain\'t toys -- every run trains your crew. Haul left today: ' + room + ' gold.')
      : 'Haul\'s tapped out, champ -- but every run still trains the crew. Run it.';
    ctx.ui.keeperCard({
      place: 'THE ARCADE', glyph: '🕹️', name: 'Joystick Jonah',
      line: line,
      interiorArt: 'assets/interiors/arcade.png',
      buttons: [
        { label: 'BONE DIG   (best ' + bestFor(ctx, 'bone_dig') + ')', primary: true,
          onClick: function (c) { launchGame(c, GAMES.bone_dig, { keeper: true }); } },
        { label: 'ALLEY DASH   (best ' + bestFor(ctx, 'alley_dash') + 'm)',
          onClick: function (c) { launchGame(c, GAMES.alley_dash, { keeper: true }); } },
        { label: 'WHACK-A-STRAY   (best ' + bestFor(ctx, 'whack') + ')',
          onClick: function (c) { launchGame(c, GAMES.whack, { keeper: true }); } }
      ]
    });
    try { mountArcadeAmb(); } catch (_) {}   // AK-ARCVID: ambient backdrop behind the keeper card
  }

  // public bridge so the production wave (Gem Mine / Card Forge keepers) can
  // launch the embedded micro-games without importing this file.
  global.AK_ARCADE = {
    GAMES: GAMES,
    play: function (id, ctx, opts) { var d = GAMES[id]; if (!d) return false; return launchGame(ctx, d, opts || {}); },
    openArcade: function (ctx) { try { renderArcadeKeeper(ctx); return true; } catch (_) { return false; } },
    goldRoom: goldRoom
  };

  /* ---- module registration --------------------------------------------- */
  global.AK_SYSTEMS.register({
    id: 'arcade',
    onEnterBuilding: function (b, ctx) {
      if (!b || b.id !== 'ARCADE') return false;   // claim ONLY THE_STRIP/ARCADE
      renderArcadeKeeper(ctx);
      return true;                                 // host shows the panel + suppresses 'soon'
    },
    onTick: function () { try { tickArcadeAmb(); } catch (_) {} }   // AK-ARCVID: pause/hide the ambient loop off-panel + on tab-hide (throttled)
  });

})(typeof window !== 'undefined' ? window : globalThis);
