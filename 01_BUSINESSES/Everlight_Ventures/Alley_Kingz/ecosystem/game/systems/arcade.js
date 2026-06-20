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
 *   - Crypto gate: rewards are GOLD + BONES only (soft, server-free). Never
 *     gems / $BCARDD / ALK. ctx.currency.grant('gems') is already a no-op.
 *   - All state lives behind the falsy-default field p.arcade (added once by the
 *     Lead in economy.js ensureShape). We self-heal it if absent so the module
 *     is byte-identical on a zero-state profile and safe before bootstrap.
 *   - Cards reused BY NAME from ctx.cards() (106 roster) as wild strays / runner;
 *     card art auto-loads via window.akCardArtRel with a glyph fallback.
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
  function cardFor(ctx, name) { try { var c = ctx.cards(); return (c && c[name]) || null; } catch (_) { return null; } }

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
    if (im && im.complete && im.naturalWidth > 0) {
      g.beginPath(); g.arc(x, y, r, 0, 7); g.closePath(); g.clip();
      try { g.drawImage(im, x - r, y - r, r * 2, r * 2); } catch (_) {}
      g.restore();
      g.strokeStyle = accent || GOLD; g.lineWidth = 2.5;
      g.beginPath(); g.arc(x, y, r, 0, 7); g.stroke();
    } else {
      g.fillStyle = accent || GOLD_D; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
      g.strokeStyle = 'rgba(0,0,0,.35)'; g.lineWidth = 2; g.stroke();
      txt(g, glyph || '🐕', x, y + 1, Math.round(r * 1.1), '#0c0a07', 'center', '700');
      g.restore();
    }
  }

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

  // Apply caps, write best/plays/daily ledger, then grant soft currency.
  // rawGold/rawBones = what the run earned; returns the actual paid summary.
  function grantReward(ctx, id, rawGold, rawBones, score) {
    var e = econ(ctx);
    var out = { gold: 0, bones: 0, score: score | 0, best: 0, capped: false, gameId: id };
    if (!e) return out;
    var d = today();
    e.mutateProfile(function (p) {
      if (!p.arcade || typeof p.arcade !== 'object') p.arcade = {};
      var a = p.arcade;
      var m = a._meta || { day: d, gold: 0, bones: 0, plays: 0 };
      if (m.day !== d) m = { day: d, gold: 0, bones: 0, plays: 0 };
      var g = a[id] || { best: 0, plays: 0, lastReward: 0 };

      var gRoom = Math.max(0, DAILY_GOLD_CAP - (m.gold | 0));
      var bRoom = Math.max(0, DAILY_BONES_CAP - (m.bones | 0));
      var payG = clamp(rawGold | 0, 0, gRoom);
      var payB = clamp(rawBones | 0, 0, bRoom);
      out.capped = (payG < (rawGold | 0)) || (payB < (rawBones | 0));

      g.plays = (g.plays | 0) + 1;
      g.lastReward = payG;
      if ((score | 0) > (g.best | 0)) g.best = score | 0;
      m.gold = (m.gold | 0) + payG; m.bones = (m.bones | 0) + payB; m.plays = (m.plays | 0) + 1;
      a[id] = g; a._meta = m;
      out.gold = payG; out.bones = payB; out.best = g.best | 0;
    });
    // soft-currency grants ride the sanctioned ctx helper (one atomic write each)
    if (out.gold > 0) ctx.currency.grant('gold', out.gold);
    if (out.bones > 0) ctx.currency.grant('bones', out.bones);
    return out;
  }

  /* ====================================================================== *
   * SHARED OVERLAY CHROME (background, close button, intro, over screen)
   * Each game def supplies: { id,title,how,unit,accent, reset, frame, tap }
   * reset(vp,ctx) -> run-state ; frame(g,dt,vp,run,ctx) -> result|null ;
   * tap(px,py,vp,run,ctx). The launcher owns intro/over/close + reward grant.
   * ====================================================================== */
  function drawBg(g, vp) {
    g.fillStyle = INK; g.fillRect(0, 0, vp.w, vp.h);
    var grd = g.createRadialGradient(vp.w / 2, vp.h * 0.34, 30, vp.w / 2, vp.h * 0.5, Math.max(vp.w, vp.h));
    grd.addColorStop(0, '#16111d'); grd.addColorStop(1, INK);
    g.fillStyle = grd; g.fillRect(0, 0, vp.w, vp.h);
  }
  function drawChrome(g, vp, def, st) {
    // title strip
    txt(g, def.title, vp.w / 2, 30, 17, GOLD, 'center', '900');
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
    var p = panel(g, vp, 280); var cx = vp.w / 2;
    txt(g, def.title, cx, p.y + 40, 24, GOLD, 'center', '900');
    var words = String(def.how).split(' '), line = '', yy = p.y + 88, lim = p.w - 48;
    g.font = '600 14px Inter, system-ui, sans-serif';
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + ' ' + words[i] : words[i];
      if (g.measureText(test).width > lim && line) { txt(g, line, cx, yy, 14, DIM, 'center', '600'); line = words[i]; yy += 22; }
      else line = test;
    }
    if (line) txt(g, line, cx, yy, 14, DIM, 'center', '600');
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
    txt(g, 'RUN OVER', cx, p.y + 38, 22, GOLD, 'center', '900');
    txt(g, 'SCORE  ' + (s.score | 0) + ' ' + def.unit, cx, p.y + 78, 16, TXT, 'center', '800');
    txt(g, 'BEST  ' + (s.best | 0) + ' ' + def.unit, cx, p.y + 104, 13, DIM, 'center', '600');
    txt(g, '+ ' + (s.gold | 0) + ' GOLD' + (s.bones ? '   + ' + s.bones + ' BONES' : ''), cx, p.y + 142, 17, TEAL, 'center', '900');
    if (s.capped) txt(g, '(daily haul cap reached)', cx, p.y + 166, 11, RED, 'center', '600');
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
        drawBg(g, vp);
        if (st.phase === 'play') {
          var res = null;
          try { res = def.frame(g, dt, vp, st.run, ctx); } catch (_e) { res = { gold: 0, bones: 0, score: 0 }; }
          if (res) {
            st.summary = grantReward(ctx, def.id, res.gold, res.bones, res.score);
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
      if (res && (res.gold || res.bones)) {
        var t = '+' + (res.gold | 0) + ' gold' + (res.bones ? '  +' + res.bones + ' bones' : '');
        ctx.showBanner('ARCADE HAUL  ' + t + (res.capped ? '  (capped)' : ''), 2.0);
      } else if (res) {
        ctx.showBanner('NICE RUN -- daily haul maxed', 1.6);
      }
    } catch (_b) {}
    if (opts && opts.keeper) try { renderArcadeKeeper(ctx); } catch (_k) {}
    if (opts && opts.onDone) try { opts.onDone(res); } catch (_d) {}
  }

  /* ====================================================================== *
   * GAME 1 -- BONE DIG (grid-match / concentration)
   * ====================================================================== */
  var DIG_ICONS = [
    { g: '🦴', c: GOLD },     // bone
    { g: '⚙️', c: '#ff9d5c' },// gear
    { g: '⚡', c: TEAL },           // bolt
    { g: '👑', c: GOLD },     // crown
    { g: '🐾', c: '#9B8CFF' },// paw
    { g: '🔧', c: RED },      // wrench
    { g: '💎', c: '#7fc8ff' },// gem
    { g: '🃏', c: '#7FE3A0' } // card
  ];
  var bone_dig = {
    id: 'bone_dig', title: 'BONE DIG', unit: 'pts', accent: GOLD,
    how: 'Flip tiles two at a time. Match the buried bones before the 60s clock runs dry. Clear the board for a perfect haul.',
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
        if (tile.match) { g.fillStyle = 'rgba(124,255,224,.16)'; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.fill(); g.strokeStyle = TEAL; g.lineWidth = 2; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.stroke(); txt(g, DIG_ICONS[tile.sym].g, rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.4), DIG_ICONS[tile.sym].c, 'center'); }
        else if (tile.flip) { g.fillStyle = 'rgba(232,197,90,.14)'; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.fill(); g.strokeStyle = GOLD; g.lineWidth = 2; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.stroke(); txt(g, DIG_ICONS[tile.sym].g, rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.4), DIG_ICONS[tile.sym].c, 'center'); }
        else { g.fillStyle = 'rgba(28,22,16,.95)'; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.fill(); g.strokeStyle = 'rgba(201,168,76,.35)'; g.lineWidth = 1.5; rr(g, rc.x, rc.y, rc.w, rc.h, 10); g.stroke(); txt(g, '🦴', rc.x + rc.w / 2, rc.y + rc.h / 2, Math.round(cell * 0.3), 'rgba(201,168,76,.30)', 'center'); }
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
      if (r.grid[r.first].sym === t.sym) { r.grid[r.first].match = true; t.match = true; r.matches++; r.combo++; r.score += 10; r.first = -1; }
      else { r.combo = 0; r.lockT = 0.7; }   // frame flips both back after the peek
    }
  };

  /* ====================================================================== *
   * GAME 2 -- ALLEY DASH (one-tap endless runner)
   * ====================================================================== */
  var alley_dash = {
    id: 'alley_dash', title: 'ALLEY DASH', unit: 'm', accent: TEAL,
    how: 'TAP to jump (double-tap = double jump). Dodge the pound drones. Go the distance -- gold scales with how far the pack runs.',
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
          if (r.gx + r.r * 0.7 > o.x && r.gx - r.r * 0.7 < o.x + o.w && r.gy + r.r > oy) r.dead = true;
        }
      } else r.overT += dt;
      // ground
      g.strokeStyle = 'rgba(124,255,224,.35)'; g.lineWidth = 2; g.beginPath(); g.moveTo(0, groundY); g.lineTo(vp.w, groundY); g.stroke();
      g.fillStyle = 'rgba(124,255,224,.5)';
      for (var x = -((r.scroll) % 80); x < vp.w; x += 80) g.fillRect(x, groundY + 6, 34, 3);
      // obstacles (pound drones)
      for (var j = 0; j < r.obs.length; j++) { var b = r.obs[j], by = groundY - b.h; g.fillStyle = 'rgba(192,57,43,.85)'; rr(g, b.x, by, b.w, b.h, 5); g.fill(); g.strokeStyle = '#ff7a6b'; g.lineWidth = 1.5; rr(g, b.x, by, b.w, b.h, 5); g.stroke(); txt(g, '⛔', b.x + b.w / 2, by + b.h / 2, Math.min(b.w, 20), '#fff', 'center'); }
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
      if (r.grounded) { r.vy = -880; r.jumps = 1; r.grounded = false; }
      else if (r.jumps < 2) { r.vy = -780; r.jumps = 2; }
    }
  };

  /* ====================================================================== *
   * GAME 3 -- WHACK-A-STRAY (reaction)
   * ====================================================================== */
  function rollKind() { var x = Math.random(); if (x < 0.12) return 'gold'; if (x < 0.30) return 'pup'; return 'stray'; }
  var whack = {
    id: 'whack', title: 'WHACK-A-STRAY', unit: 'pts', accent: '#9B8CFF',
    how: 'TAP the strays before they duck. The gold $BCARDD is a jackpot. Do NOT whack your own crew pup -- it kills your combo.',
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
        // hole
        g.fillStyle = 'rgba(0,0,0,.55)'; g.beginPath(); g.ellipse(hx, hy + rad * 0.55, rad * 1.05, rad * 0.5, 0, 0, 7); g.fill();
        var HH = r.holes[m];
        if (HH.kind && HH.up > 0.02) {
          var dy = rad * (1 - HH.up), accent = HH.kind === 'gold' ? GOLD : HH.kind === 'pup' ? '#7FE3A0' : '#cdbb86';
          var gl = HH.kind === 'gold' ? '👑' : HH.kind === 'pup' ? '🐶' : '🐕';
          drawDog(g, cardFor(ctx, HH.card), gl, hx, hy - rad * 0.2 + dy, rad * 0.92, accent);
          if (HH.kind === 'pup') { txt(g, 'CREW', hx, hy - rad * 1.05 + dy, 10, '#7FE3A0', 'center', '900'); }
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
          if (H.kind === 'stray') { r.combo++; r.score += 1 + Math.floor(r.combo / 4); r.pops.push({ x: geo.cx, y: geo.cy, t: 0.5, s: '+' + (1 + Math.floor(r.combo / 4)), good: true }); }
          else if (H.kind === 'gold') { r.combo++; r.score += 5; r.pops.push({ x: geo.cx, y: geo.cy, t: 0.6, s: '+5!', good: true }); }
          else { r.combo = 0; r.score = Math.max(0, r.score - 2); r.pops.push({ x: geo.cx, y: geo.cy, t: 0.5, s: '-2', good: false }); }
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
    reset: function (vp, ctx) { return { pos: 0, dir: 1, speed: 0.95, lo: 0.42, hi: 0.58, swings: 0, max: 8, hits: 0, score: 0, flash: 0, flashGood: false }; },
    frame: function (g, dt, vp, r, ctx) {
      r.pos += r.dir * r.speed * dt; if (r.pos > 1) { r.pos = 1; r.dir = -1; } else if (r.pos < 0) { r.pos = 0; r.dir = 1; }
      if (r.flash > 0) r.flash -= dt;
      var bx = vp.w * 0.12, bw = vp.w * 0.76, by = vp.h * 0.5, bh = 30;
      g.fillStyle = 'rgba(30,24,40,.95)'; rr(g, bx, by, bw, bh, 8); g.fill();
      g.fillStyle = 'rgba(176,123,255,.40)'; rr(g, bx + bw * r.lo, by, bw * (r.hi - r.lo), bh, 6); g.fill();
      var mx = bx + bw * r.pos; g.fillStyle = r.flash > 0 ? (r.flashGood ? TEAL : RED) : GOLD; g.fillRect(mx - 3, by - 10, 6, bh + 20);
      txt(g, 'SWING ' + r.swings + '/' + r.max, vp.w / 2, by - 50, 15, TXT, 'center', '800');
      txt(g, 'HITS ' + r.hits, vp.w / 2, by + 64, 15, '#b07bff', 'center', '800');
      if (r.swings >= r.max) return { gold: r.hits * 8, bones: r.hits >= 7 ? 2 : 0, score: r.hits };
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      if (r.swings >= r.max) return;
      var good = r.pos >= r.lo && r.pos <= r.hi; r.swings++; r.flash = 0.25; r.flashGood = good;
      if (good) { r.hits++; r.score++; r.speed += 0.08; var c = (r.hi - r.lo) * 0.86, mid = (r.lo + r.hi) / 2; r.lo = mid - c / 2; r.hi = mid + c / 2; }
    }
  };
  var forge_temper = {
    id: 'forge_temper', title: 'CARD FORGE -- TEMPER', unit: 'pts', accent: '#ff9d5c',
    how: 'The blade heats and cools. TAP to quench inside the gold band -- dead center is a perfect temper. You get 3 quenches; best one counts.',
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
      txt(g, 'QUENCH ' + r.used + '/' + r.attempts, vp.w / 2, gtop - 28, 15, TXT, 'center', '800');
      txt(g, 'BEST TEMPER ' + r.best, vp.w / 2, gtop + gh + 34, 15, '#ff9d5c', 'center', '800');
      if (r.used >= r.attempts && r.flash <= 0) return { gold: r.best * 4, bones: r.best >= 90 ? 2 : 0, score: r.best };
      return null;
    },
    tap: function (px, py, vp, r, ctx) {
      if (r.used >= r.attempts || r.locked) return;
      r.used++; r.locked = true; r.flash = 0.6;
      var q = Math.round(100 * (1 - Math.min(1, Math.abs(r.val - 0.5) / 0.5)));  // 100 at dead center
      if (q > r.best) r.best = q;
    }
  };

  /* ====================================================================== *
   * registry of all games + public API
   * ====================================================================== */
  var GAMES = { bone_dig: bone_dig, alley_dash: alley_dash, whack: whack, gem_tap: gem_tap, forge_temper: forge_temper };

  function renderArcadeKeeper(ctx) {
    var room = goldRoom(ctx);
    var line = room > 0
      ? ('Step right up. Haul left today: ' + room + ' gold. Pick your hustle, hot dog.')
      : 'Daily haul\'s tapped out, champ -- but the cabinets are free. Run it for the high score.';
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
    }
  });

})(typeof window !== 'undefined' ? window : globalThis);
