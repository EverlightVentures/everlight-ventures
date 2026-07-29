/* game/systems/modes.js -- AK_SYSTEMS "modes" wave (Wave 8).
 * =====================================================================
 * DEEP NET-NEW MODES (the Mobile-Legends / CoD-Mobile layer of the
 * 14-game fusion, AK_MASTER_GAME_DESIGN_SYNTHESIS sec 8 + the camera/mode
 * matrix sec 15). Every camera + renderer here lives ENTIRELY in this
 * module, drawn into a fresh ctx.overlay.open(...) Canvas2D layer. The
 * battler (engine.js) is NEVER forked or touched by an overlay mode.
 *
 *   1. WORLD-MOBA  (mode 'world-moba')  -- overhead real-time lane push.
 *      Persistent gold / health / energy TASKBAR HUD + 3 skill buttons +
 *      virtual stick + minimap, hero-vs-hero DUEL with minion waves and two
 *      cores. Reuses the 106 cards BY NAME (your lead card = hero, a Mythic/
 *      Legendary rival = enemy hero, Commons = minions) at their REAL canon
 *      stats. Heroes respawn; cracking the rival CORE wins.   [PLAYABLE MVP]
 *
 *   2. GULAG       (mode 'gulag')       -- CoD-Mobile 1v1 jump-out shooter.
 *      Tighter, gritty camera, cover blocks, bullets, strafing rival AI that
 *      takes cover when hurt + only shoots with line-of-sight.   [PLAYABLE MVP]
 *
 *   3. ENCOUNTER ROUTER (routeEncounter) -- the resolve-by-MOVE decision moment
 *      (synthesis sec 15): a wild stray locks eyes, you pick how to play it:
 *        COLLIDE  -> Tower Battle  (engine, AK.newMatch via ctx.battle.launch)
 *        SWERVE   -> World-MOBA duel (overlay, this module)
 *        JUMP OUT -> Gulag 1v1      (overlay, this module)
 *        RUN      -> avoid (symbol-encounter is dodgeable).      [PLAYABLE MVP]
 *      The `encounters` + `raid` waves can call this on proximity; the STREET
 *      keeper exposes it as "STREET ENCOUNTER".
 *
 *   4. ENGINE WIN-CONDITION MODES (window.AK_MODES.survival / .encounter) --
 *      pure win-condition overlays on the EXISTING battler, read by the
 *      engine.js seam (contract sec 6.C) on game.html. They use ONLY existing
 *      engine state (towers/crowns/time) and NEVER fork the loop.  [PLAYABLE MVP]
 *
 * HARD-RULE COMPLIANCE
 *   - 2.5D Canvas2D only; no engine primitives added; battler untouched.
 *   - Crypto gate: every payout is SOFT currency / cosmetic only, per-result
 *     capped, routed through ctx.currency (grant('gems') is a host no-op).
 *     NO $BCARDD / ALK in any reward, ever. Gems are server-only.
 *   - New state = falsy-default fields (p.modes:{}, shared p.bones:0) written
 *     through AK_ECON.mutateProfile -- a zero-state profile stays byte-identical.
 *   - Reuse the 106 cards + 6 handlers BY NAME (ctx.cards()); no generic units.
 *   - "crew" never "clan"; gritty gold cyberpunk dog-gang voice everywhere.
 *   - Headless-safe: zero top-level DOM/localStorage; module load never throws.
 *
 * FUTURE RESEARCH PASSES (clearly marked below, NOT shipped here):
 *   - World-MOBA: 5v5, draft/ban, jungle buffs + a Lord objective, per-card
 *     unique skill kits (read card.ability semantics), multiplayer netcode.
 *   - Gulag:      2v2, weapon loadouts, grenades, killcam, ranked redemption.
 *   - Both:       server-authoritative result validation (// TODO-SERVER).
 * ===================================================================== */
(function (global) {
  'use strict';

  /* ---------------------------------------------------------------- utils */
  var PI = Math.PI;
  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function hyp(dx, dy) { return Math.sqrt(dx * dx + dy * dy); }

  /* --------------------------------------------------- card roster sourcing
   * Primary source = ctx.cards() (= AK.getCards(), the 106-card index) when the
   * engine is present. The hub (index.html) does NOT load engine.js, so we
   * lazy-fetch ../data/cards.json once and cache it, seeding the very first
   * frame from a small REAL-name embed so a mode is never empty / never generic.
   */
  var _roster = null;       // name -> raw card def
  var _fetching = false;

  // Real names + real canon stats (verified against data/cards.json). Seed only.
  var EMBED = {
    '$BCARDD':         { name: '$BCARDD',         rarity: 'Mythic',    cardNumber: '0001', role: 'Vanguard',   hp: 2850, damage: 180, attack_speed: 0.7,  move_speed: 0.55, range: 1, cost: 9, ability: { name: 'Crownbreaker' } },
    'Jagged':          { name: 'Jagged',          rarity: 'Mythic',    cardNumber: '0013', role: 'Assassin',   hp: 1900, damage: 230, attack_speed: 1.1,  move_speed: 1.1,  range: 1, cost: 6, ability: { name: 'Shadow Fang' } },
    'Rosco':           { name: 'Rosco',           rarity: 'Mythic',    cardNumber: '0025', role: 'Skirmisher', hp: 1600, damage: 170, attack_speed: 0.95, move_speed: 0.85, range: 3, cost: 6, ability: { name: 'Leashbreak' } },
    'Crown Foxhound':  { name: 'Crown Foxhound',  rarity: 'Mythic',    cardNumber: '0037', role: 'Striker',    hp: 1900, damage: 230, attack_speed: 1.1,  move_speed: 1.1,  range: 1, cost: 6, ability: { name: 'Royal Hunt' } },
    'Stonejaw':        { name: 'Stonejaw',        rarity: 'Legendary', cardNumber: '0002', role: 'Vanguard',   hp: 2850, damage: 145, attack_speed: 0.7,  move_speed: 0.55, range: 1, cost: 8, ability: { name: 'Armor Pulse' } },
    'Iron Rottweiler': { name: 'Iron Rottweiler', rarity: 'Epic',      cardNumber: '0004', role: 'Vanguard',   hp: 2850, damage: 155, attack_speed: 0.7,  move_speed: 0.55, range: 1, cost: 7, ability: { name: 'Overclock Rage' } },
    'Balboa':          { name: 'Balboa',          rarity: 'Epic',      cardNumber: '0003', role: 'Striker',    hp: 1500, damage: 175, attack_speed: 1.05, move_speed: 0.85, range: 1, cost: 5, ability: { name: 'Haymaker' } },
    'Grit Bulldog':    { name: 'Grit Bulldog',    rarity: 'Rare',      cardNumber: '0006', role: 'Striker',    hp: 1300, damage: 150, attack_speed: 1.05, move_speed: 0.85, range: 1, cost: 3, ability: { name: 'Brawler' } },
    'Alloy Akita':     { name: 'Alloy Akita',     rarity: 'Rare',      cardNumber: '0007', role: 'Lancer',     hp: 1100, damage: 180, attack_speed: 0.95, move_speed: 0.85, range: 2, cost: 4, ability: { name: 'Shock Push' } },
    'Tank Pug':        { name: 'Tank Pug',        rarity: 'Common',    cardNumber: '0010', role: 'Support',    hp: 750,  damage: 45,  attack_speed: 0.9,  move_speed: 0.85, range: 3, cost: 2, ability: { name: 'Shield Bark' } },
    'Neon Whippet':    { name: 'Neon Whippet',    rarity: 'Common',    cardNumber: '0014', role: 'Skirmisher', hp: 600,  damage: 75,  attack_speed: 1.1,  move_speed: 1.05, range: 1, cost: 2, ability: { name: 'Zoom' } },
    'Byte Beagle':     { name: 'Byte Beagle',     rarity: 'Common',    cardNumber: '0040', role: 'Hacker',     hp: 550,  damage: 80,  attack_speed: 1.0,  move_speed: 0.9,  range: 4, cost: 3, ability: { name: 'Ping' } },
    'Turbo Jack':      { name: 'Turbo Jack',      rarity: 'Common',    cardNumber: '0015', role: 'Skirmisher', hp: 1050, damage: 110, attack_speed: 0.95, move_speed: 1.0,  range: 1, cost: 3, ability: { name: 'Dash' } }
  };

  // keep only fieldable mobile character cards (drop structures; spells aren't
  // flagged in cards.json by type but carry no movement -- dropping Structure
  // roles is enough to keep heroes/minions real and ambulatory).
  function filterRoster(map) {
    var out = {};
    for (var n in map) {
      var c = map[n];
      if (!c || !c.name) continue;
      if (c.role === 'Structure' || c.isStructure || c.type === 'spell') continue;
      out[n] = c;
    }
    return Object.keys(out).length ? out : map;
  }

  function ensureFetch(ctx) {
    if (_roster || _fetching) return;
    try {
      var m = ctx && ctx.cards && ctx.cards();          // live engine index (hub usually lacks it)
      if (m && typeof m === 'object' && Object.keys(m).length) { _roster = filterRoster(m); return; }
    } catch (_e) {}
    if (typeof fetch !== 'function') return;
    _fetching = true;
    var paths = ['../data/cards.json', 'data/cards.json'];
    (function tryPath(i) {
      if (i >= paths.length) { _fetching = false; return; }
      fetch(paths[i]).then(function (r) { return r.json(); }).then(function (d) {
        var arr = (d && d.cards) || [], map = {};
        for (var k = 0; k < arr.length; k++) { var c = arr[k]; if (c && c.name) map[c.name] = c; }
        if (Object.keys(map).length) _roster = filterRoster(map); else tryPath(i + 1);
        _fetching = false;
      }).catch(function () { _fetching = false; tryPath(i + 1); });
    })(0);
  }

  function getRoster(ctx) {
    if (_roster) return _roster;
    ensureFetch(ctx);
    return EMBED;   // real-name canon seed until the fetch lands
  }

  // raw card -> normalized combat stat line (the REAL card stats, scaled later)
  function statline(card) {
    card = card || {};
    var as = num(card.attack_speed, 1.0);
    return {
      name:        card.name || 'Stray',
      rarity:      card.rarity || 'Common',
      cardNumber:  card.cardNumber || null,
      abilityName: (card.ability && card.ability.name) || 'Finisher',
      rawHp:       num(card.hp, 800),
      rawDmg:      num(card.damage, 80),
      atkInterval: clamp(1 / Math.max(0.35, as), 0.5, 2.2),   // seconds between hits
      moveBase:    56 + num(card.move_speed, 0.8) * 120,      // px/s
      rangeTiles:  num(card.range, 2)
    };
  }

  function rarColor(r) {
    return ({ Common: '#9fb0c0', Rare: '#5ad0c0', Epic: '#c9a8ff', Legendary: '#ffd76b', Mythic: '#ff8fae' })[r] || '#9fb0c0';
  }
  function chipLetter(name) { return (name || '?').replace('$', '')[0] || '?'; }

  // Player's lead card -> hero. Prefer the active deck, else first owned that is
  // a real fieldable card, else the king ($BCARDD), else any roster name.
  function playerHeroName(ctx, roster) {
    try {
      var p = ctx.econ && ctx.econ.loadProfile();
      if (p) {
        var d = p.deck || p.activeDeck || p.deckNames;
        if (Array.isArray(d)) { for (var i = 0; i < d.length; i++) if (d[i] && roster[d[i]]) return d[i]; }
        if (Array.isArray(p.owned)) { for (var j = 0; j < p.owned.length; j++) if (roster[p.owned[j]]) return p.owned[j]; }
      }
    } catch (_e) {}
    return roster['$BCARDD'] ? '$BCARDD' : Object.keys(roster)[0];
  }

  function pickEnemyHero(roster, notName) {
    var names = Object.keys(roster), pool = [];
    for (var i = 0; i < names.length; i++) {
      var c = roster[names[i]];
      if (names[i] === notName) continue;
      if (c && (c.rarity === 'Mythic' || c.rarity === 'Legendary' || c.rarity === 'Epic')) pool.push(names[i]);
    }
    if (!pool.length) pool = names.filter(function (n) { return n !== notName; });
    return pool.length ? pool[Math.floor(Math.random() * pool.length)] : notName;
  }

  function cheapNames(roster) {
    var names = Object.keys(roster), out = [];
    for (var i = 0; i < names.length; i++) {
      var c = roster[names[i]];
      if (c && c.rarity === 'Common' && num(c.cost, 9) <= 3) out.push(names[i]);
    }
    if (out.length < 2) out = names.filter(function (n) { var c = roster[n]; return c && (c.rarity === 'Common' || c.rarity === 'Rare'); });
    if (!out.length) out = names;
    return out;
  }

  /* ----------------------------------------------------- rewards + records
   * Soft-currency ONLY, per-result capped (mirrors LOOT_TABLE anti-farm).
   * Never grants gems / $BCARDD / ALK -- parity-safe by construction.
   */
  function grantReward(ctx, win, kind) {
    if (!ctx || !ctx.currency) return;
    /* AK-FIX-lane-D:modes.js 2026-07-28: STREET PAY MULTIPLIER -- level-scaled soft
     * payout applied to gold + scrap only (bones/rank untouched). Guarded so a
     * not-yet-wired economy.js reads as 1x; zero-state payout is byte-identical. */
    var pay = (global.AK_ECON && AK_ECON.streetPayMult) ? AK_ECON.streetPayMult() : 1;
    function sp(n) { return Math.max(1, Math.round(n * pay)); }
    try {
      if (kind === 'moba') {
        if (win) { ctx.currency.grant('gold', sp(rand(140, 220))); ctx.currency.grant('scrap', sp(2), 'Rare'); ctx.currency.grant('bones', 5); }
        else     { ctx.currency.grant('gold', sp(30)); ctx.currency.grant('bones', 1); }
      } else { // gulag
        if (win) { ctx.currency.grant('gold', sp(rand(90, 150))); ctx.currency.grant('scrap', sp(5), 'Common'); ctx.currency.grant('bones', 3); }
        else     { ctx.currency.grant('gold', sp(20)); }
      }
    } catch (_e) {}
    // AK-RANK 2026-06-22: every battle moves the ONE shared rank (the same ladder the tower climbs). Win = +, loss = small -.
    try { if (ctx.econ && ctx.econ.addTrophies) ctx.econ.addTrophies(win ? (kind === 'moba' ? 18 : 12) : -6); } catch (_e) {}
  }

  function recordResult(ctx, modeId, win, score) {
    try {
      ctx.econ.mutateProfile(function (p) {
        if (!p.modes || typeof p.modes !== 'object') p.modes = {};
        var m = p.modes[modeId] || (p.modes[modeId] = { wins: 0, losses: 0, best: 0 });
        if (win) m.wins = (m.wins | 0) + 1; else m.losses = (m.losses | 0) + 1;
        if (typeof score === 'number' && score > (m.best | 0)) m.best = score | 0;
      });
    } catch (_e) {}
  }

  /* AK-FIX-lane-D:modes.js 2026-07-28 -- HEROES BOX IN COMBAT.
   * The gulag/MOBA overlays already track the player's hits; wire each landed
   * PLAYER hit to the selected hero's REAL GLB combat clip (JAB/HOOK/STRIKE) via
   * the SAME driver the hub emote rail uses (AK_HEROACTIONS.play(label)). Rotates
   * labels for variety and is throttled so rapid fire fires a punch, not a strobe.
   * Fully guarded: no 3D layer / headless load -> silent no-op (reads like today).
   * We do NOT touch akheroactions.js / hub3d.js -- only consume their public play(). */
  var _boxActT = 0, _boxRot = 0;
  var BOX_LABELS = ['JAB', 'HOOK', 'STRIKE'];
  function boxNowMs() { try { return (global.performance && global.performance.now) ? global.performance.now() : Date.now(); } catch (_e) { return Date.now(); } }
  function boxHeroHit(label) {
    try {
      var t = boxNowMs();
      if (t - _boxActT < 360) return;                    // ~2.7 strikes/sec cap
      var HA = global.AK_HEROACTIONS, H3 = global.__hero3d;
      var lab = label || BOX_LABELS[(_boxRot++) % BOX_LABELS.length];
      if (HA && typeof HA.play === 'function') { _boxActT = t; HA.play(lab); return; }
      if (H3 && typeof H3.play === 'function') { _boxActT = t; H3.play(lab); return; }   // future direct-handle path -- guarded
    } catch (_e) {}
  }

  /* ---- AK-CARDART 2026-06-29: REAL card portraits on units (no placeholder
   * circles). Resolve a unit's art by NAME against window.CANON_CARDS through the
   * canonical window.akCardArtRel resolver (prefix 'assets/'), cache the Image at
   * module level (mirrors population.js _imgs), webp->png via akImgErr. Headless-
   * safe: no Image() in node -> null -> dogChip falls back to the letter-chip. */
  var _cardImgs = {};       // name -> Image | null (null = known-dead, stop retrying)
  var _canonByName = null;  // lazy name -> canon card def index
  function canonCard(name) {
    if (!name) return null;
    if (!_canonByName) {
      _canonByName = {};
      try { var L = global.CANON_CARDS || []; for (var i = 0; i < L.length; i++) { var c = L[i]; if (c && c.name) _canonByName[c.name] = c; } } catch (_e) {}
    }
    return _canonByName[name] || null;
  }
  function cardArtImg(name, cardNumber) {
    if (!name || typeof Image === 'undefined') return null;
    var im = _cardImgs[name]; if (im !== undefined) return im;     // cached (incl. known-dead null)
    im = null;
    try {
      var c = canonCard(name) || { name: name, cardNumber: cardNumber };
      var rel = global.akCardArtRel ? global.akCardArtRel(c) : '';
      if (rel) {
        im = new Image();
        im.onerror = function () { try { if (global.akImgErr && global.akImgErr(im)) return; } catch (_e) {} _cardImgs[name] = null; };
        im.src = 'assets/' + rel;
      }
    } catch (_e2) { im = null; }
    _cardImgs[name] = im; return im;
  }

  /* ---- AK-BASEASSAULT art: load a hub/sprite PNG once (district ground + facades). ---- */
  var _hubImgs = {};
  function hubImg(file) {
    if (!file || typeof Image === 'undefined') return null;
    var im = _hubImgs[file]; if (im !== undefined) return im;
    im = new Image(); im.onerror = function () { _hubImgs[file] = null; }; im.src = file;
    _hubImgs[file] = im; return im;
  }
  function imgReady(im) { return !!(im && im.complete && im.naturalWidth > 0); }

  /* ---- AK-RESTYLE grit: a one-time grain tile + a gold-cyberpunk vignette (60fps-safe). ---- */
  var _grain = null, _grainTried = false;
  function grainTile() {
    if (_grainTried) return _grain; _grainTried = true;
    try {
      if (typeof document === 'undefined') return null;
      var c = document.createElement('canvas'); c.width = 64; c.height = 64; var gc = c.getContext('2d');
      var id = gc.createImageData(64, 64), d = id.data;
      for (var i = 0; i < d.length; i += 4) { var v = (Math.random() * 255) | 0; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 16; }
      gc.putImageData(id, 0, 0); _grain = c;
    } catch (_e) { _grain = null; }
    return _grain;
  }
  function drawGrit(g, vp) {
    g.save();
    try {
      var vg = g.createRadialGradient(vp.w / 2, vp.h * 0.46, Math.min(vp.w, vp.h) * 0.30, vp.w / 2, vp.h * 0.5, Math.max(vp.w, vp.h) * 0.78);
      vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.55)');
      g.fillStyle = vg; g.fillRect(0, 0, vp.w, vp.h);
    } catch (_v) {}
    var gt = grainTile();
    if (gt) { try { var pat = g.createPattern(gt, 'repeat'); if (pat) { g.globalAlpha = 0.5; g.fillStyle = pat; g.fillRect(0, 0, vp.w, vp.h); } } catch (_e) {} }
    g.restore();
  }

  /* -------------------------------------------------------- draw primitives */
  // dogChip: a unit chip. When `name` resolves to a loaded card portrait, the art
  // is clipped into the arc + the colored ring is drawn on top; otherwise it falls
  // back to the fill + letter-chip. The ring always renders (team/rarity tell).
  function dogChip(g, x, y, r, fill, ring, letter, name, cardNumber) {
    g.save();
    var im = (name && r >= 5) ? cardArtImg(name, cardNumber) : null;
    var hasArt = !!(im && im.complete && im.naturalWidth > 0);
    if (hasArt) {
      g.beginPath(); g.arc(x, y, r, 0, 2 * PI); g.closePath(); g.clip();
      g.drawImage(im, x - r, y - r, r * 2, r * 2);
    } else {
      g.beginPath(); g.arc(x, y, r, 0, 2 * PI); g.closePath();
      g.fillStyle = fill; g.fill();
      if (letter) { g.fillStyle = '#0a0a0e'; g.font = '900 ' + Math.round(r * 1.05) + 'px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(letter, x, y + 1); }
    }
    g.restore();
    if (ring) { g.save(); g.lineWidth = 2; g.strokeStyle = ring; g.beginPath(); g.arc(x, y, r, 0, 2 * PI); g.stroke(); g.restore(); }
  }
  function bar(g, x, y, w, h, frac, fill, bg) {
    g.save();
    g.fillStyle = bg || 'rgba(8,8,14,.8)'; g.fillRect(x, y, w, h);
    g.fillStyle = fill; g.fillRect(x, y, w * clamp(frac, 0, 1), h);
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.5)'; g.strokeRect(x, y, w, h);
    g.restore();
  }
  // AK-RESTYLE: a diegetic NOTCHED gauge (segmented gold bars) per the UI brief -- not a flat fill.
  function barNotch(g, x, y, w, h, frac, fill) {
    frac = clamp(frac, 0, 1);
    g.save();
    g.fillStyle = 'rgba(6,6,10,.85)'; g.fillRect(x, y, w, h);
    var seg = Math.max(4, Math.round(w / 9)), gap = 1, sw = (w - (seg - 1) * gap) / seg, on = Math.round(seg * frac);
    for (var i = 0; i < seg; i++) { g.fillStyle = i < on ? fill : 'rgba(40,38,32,.6)'; g.fillRect(x + i * (sw + gap), y, sw, h); }
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.55)'; g.strokeRect(x - 0.5, y - 0.5, w + 1, h + 1);
    g.restore();
  }
  function btnCircle(g, b, ready, glyph, sub) {
    g.save();
    g.beginPath(); g.arc(b.x, b.y, b.r, 0, 2 * PI); g.closePath();
    g.fillStyle = ready ? 'rgba(201,168,76,.22)' : 'rgba(40,40,50,.55)'; g.fill();
    g.lineWidth = 2.5; g.strokeStyle = ready ? '#e8c55a' : 'rgba(150,150,160,.5)'; g.stroke();
    g.fillStyle = ready ? '#e8c55a' : '#888'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = '900 18px Inter,sans-serif'; g.fillText(glyph, b.x, b.y - 4);
    g.font = '700 9px Inter,sans-serif'; g.fillText(sub, b.x, b.y + b.r - 9);
    g.restore();
  }
  // MOBA spell/skill button: chip + a radial cooldown sweep (cdFrac 1->0 = recharging).
  function drawBtn(g, b, ready, glyph, sub, col, cdFrac) {
    col = col || '#e8c55a';
    g.save();
    g.beginPath(); g.arc(b.x, b.y, b.r, 0, 2 * PI); g.closePath();
    g.fillStyle = ready ? 'rgba(12,14,22,.85)' : 'rgba(34,34,42,.7)'; g.fill();
    g.lineWidth = 2.5; g.strokeStyle = ready ? col : 'rgba(150,150,160,.45)'; g.stroke();
    g.fillStyle = ready ? col : '#7a7a82'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = '900 ' + Math.round(b.r * 0.78) + 'px Inter,sans-serif'; g.fillText(glyph, b.x, b.y - 3);
    if (sub) { g.font = '800 9px Inter,sans-serif'; g.fillText(sub, b.x, b.y + b.r - 8); }
    if (cdFrac > 0) {                                       // Mobile-Legends radial cooldown mask
      g.beginPath(); g.moveTo(b.x, b.y);
      g.arc(b.x, b.y, b.r - 1, -PI / 2, -PI / 2 + 2 * PI * clamp(cdFrac, 0, 1));
      g.closePath(); g.fillStyle = 'rgba(6,6,12,.6)'; g.fill();
    }
    g.restore();
  }
  function centerBanner(g, vp, txt, col) {
    g.save();
    g.fillStyle = 'rgba(6,6,12,.80)'; g.fillRect(0, vp.h / 2 - 30, vp.w, 60);
    g.fillStyle = col || '#e8c55a'; g.font = '900 18px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(txt, vp.w / 2, vp.h / 2);
    g.restore();
  }
  function fmtClock(s) { s = Math.max(0, Math.ceil(s)); var m = Math.floor(s / 60); var r = s % 60; return m + ':' + (r < 10 ? '0' : '') + r; }

  /* ===================================================================== */
  /* WORLD-MOBA  (mode 'world-moba') -- Mobile Legends overhead lane push.    */
  /* Hero-vs-hero DUEL + minion waves + two cores; respawns; crack the core.  */
  /* ===================================================================== */
  function openWorldMoba(ctx, opts) {
    if (!ctx || !ctx.overlay) return null;
    opts = opts || {};
    var roster   = getRoster(ctx);
    var heroName = opts.heroName || playerHeroName(ctx, roster);
    // AK-BASEASSAULT 2026-06-29: a raid hands the TARGET's real base layout via
    // opts.raidTarget -> render their district (buildings + Watch) as the battlefield.
    // enemyHero may arrive as a NEMESIS BLOB ({card,name,...}) from the raid handoff -- normalize to a name.
    var RT = opts.raidTarget || null;
    var ASSAULT = !!(RT && Array.isArray(RT.layout) && RT.layout.length);
    var RT_ACCENT = (RT && RT.accent) || '#e8c55a';
    var ASSAULT_GROUND = 'assets/hub/midtown_ground.png';   // the district turf the player knows from the hub
    var rawFoe = opts.enemyHero;
    var foeName = (rawFoe && typeof rawFoe === 'object') ? (rawFoe.name || rawFoe.card) : rawFoe;
    if (!foeName || !(roster[foeName] || EMBED[foeName])) foeName = pickEnemyHero(roster, heroName);
    var minPool  = cheapNames(roster);
    // AK-TYPES 2026-06-22: type advantage in the world-map raid (engine.js untouched -- this is modes' OWN combat loop).
    // Your hero's element vs the rival's scales YOUR side's damage +/-20%. Shown to the player at raid start.
    var pType = (global.AK_TYPES) ? AK_TYPES.typeOf(heroName) : 'Stray';
    var eType = (global.AK_TYPES) ? AK_TYPES.typeOf(foeName)  : 'Stray';
    var typeMult = (global.AK_TYPES) ? AK_TYPES.eff(pType, eType) : 1.0;
    try { if (typeMult !== 1 && ctx.showBanner && global.AK_TYPES) ctx.showBanner('TYPE  ' + AK_TYPES.label(pType) + ' vs ' + AK_TYPES.label(eType) + '  ' + (typeMult > 1 ? 'SUPER EFFECTIVE +20%' : 'resisted -20%'), 2.6); } catch (_e) {}

    var AW = 920, AH = 1560;                 // tall lane arena (world coords)
    var WAVE_INT = 11, MAX_MIN = 7;          // minion cadence + per-side cap
    var MATCH_T = 150;                       // hard match clock (sec)
    var HERO_RESPAWN = 6;                    // sec to respawn a fallen hero
    var MAX_ALLY = 4;                        // deployed deck-card units cap (60fps guard)
    var MAX_SHOTS = 40;                      // laser/projectile pool cap -- no runaway alloc
    var LASER_SPD = 640, LASER_LIFE = 1.15, LASER_R = 15, FIRE_CD = 0.17;   // Twisted-Metal arsenal tuning

    // reduced-motion: keep the FIGHT, drop the flourish (extra sparks + aura pulse). Defensive.
    var REDUCED = false;
    try { REDUCED = (typeof matchMedia === 'function') && matchMedia('(prefers-reduced-motion:reduce)').matches; } catch (_rm) {}

    var ents = [], fx = [], shots = [];
    var S = { t: MATCH_T, over: false, win: false, gold: 0, lvl: 1, kills: 0, stars: 0, baseMaxHp: 0,
              energy: 100, eMax: 100, waveT: 3, sg: { fire: 0, mob: 0, ult: 0 } };
    // twin-stick: LEFT half = move joystick, RIGHT half = aim + auto-fire lasers.
    var inp = { mvId: null, mox: 0, moy: 0, mvx: 0, mvy: 0, aimId: null, aox: 0, aoy: 0, ax: 0, ay: 0 };
    var hero = null, foe = null, allyCore = null, foeCore = null, vp = null, api = null;
    var BTN = {};
    var heroStat = statline(roster[heroName] || EMBED[heroName] || {});   // HUD stat readout source

    // fx is bounded -- drop the oldest rather than grow unbounded under heavy fire.
    function pushFx(o) { if (fx.length > 64) fx.shift(); fx.push(o); }
    // AK-RESTYLE: a rubble burst when a building falls -- gold for the Town Hall, dust for walls.
    function spawnDebris(x, y, big) {
      var n = big ? 10 : 6;
      for (var i = 0; i < n; i++) { var a = rand(0, 2 * PI), v = rand(60, big ? 230 : 150);
        pushFx({ debris: true, x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 50, life: rand(0.4, 0.85), col: big ? '#e8c55a' : '#b9a76a', sz: rand(2, big ? 6 : 4) }); }
    }

    function mk(name, team, x, y, kind) {
      var s = statline(roster[name] || EMBED[name] || {});
      var maxHp, dmg, r, rngPx, spd, atkInt;
      if (kind === 'core')      { maxHp = 4200; dmg = 120; r = 40; rngPx = 150; spd = 0; atkInt = 0.9; }
      else if (kind === 'hero') { maxHp = clamp(Math.round(s.rawHp / 3.2), 420, 1600); dmg = clamp(Math.round(s.rawDmg * 0.9), 26, 320); r = 22; rngPx = 26 + s.rangeTiles * 16; spd = s.moveBase;        atkInt = s.atkInterval; }
      else if (kind === 'ally') { maxHp = clamp(Math.round(s.rawHp / 5),   200, 1400); dmg = clamp(Math.round(s.rawDmg * 0.75), 20, 300); r = 16; rngPx = 26 + s.rangeTiles * 16; spd = s.moveBase * 0.95; atkInt = s.atkInterval; }
      else                      { maxHp = clamp(Math.round(s.rawHp / 9),    60,  900); dmg = clamp(Math.round(s.rawDmg * 0.6),  14, 240); r = 14; rngPx = 26 + s.rangeTiles * 16; spd = s.moveBase * 0.85; atkInt = s.atkInterval; }
      var e = {
        kind: kind, name: name, team: team, x: x, y: y, r: r,
        maxHp: maxHp, hp: 0, dmg: dmg, rngPx: rngPx, spd: spd, atkInt: atkInt,
        atkT: 0, dead: false, respawnT: 0, hitFx: 0, think: 0, strafe: 1, fireT: rand(0, 1),
        rarity: s.rarity, ability: s.abilityName, baseDmg: 0, baseMaxHp: 0,
        faceX: 0, faceY: -1,
        kstreak: 0, ktier: 0   // AK-KILLSTREAK: kills-this-life + the 3-tier power-up state (Mario-Star / CoD mythic)
      };
      if (e.team === 0 && typeMult !== 1) e.dmg = Math.max(1, Math.round(e.dmg * typeMult));   // AK-TYPES: your side's type advantage
      e.hp = e.maxHp; e.baseDmg = e.dmg; e.baseMaxHp = e.maxHp;
      return e;
    }

    // AK-BASEASSAULT: map the target's normalized 0..100 base plot into the upper
    // district of the arena; the raider enters from the gate at the bottom.
    function bxA(lx) { return clamp(AW * 0.12 + (num(lx, 50) / 100) * AW * 0.76, 40, AW - 40); }
    function byA(ly) { return clamp(150 + (num(ly, 36) / 100) * (AH * 0.60 - 150), 120, AH * 0.66); }
    var STRUCT_HP_DEF = { CORE: 4200, WALL: 200, STONE: 500, METAL: 1200, BARRICADE: 120, GEM: 700, MINT: 700, FORGE: 850, LAB: 750, GEN: 900 };
    function mkStruct(s) {                                   // one damageable enemy building (Clash-style)
      var type = (s && s.type) || 'WALL', isCore = (type === 'CORE');
      var maxHp = clamp(num(s && (s.maxHp || s.hp), 0) || STRUCT_HP_DEF[type] || 300, 60, 14000);
      var e = { kind: 'struct', stype: type, isCore: isCore, name: (s && s.name) || type, team: 1,
                x: bxA(s && s.x), y: byA(s && s.y),
                r: isCore ? 48 : (type === 'METAL' ? 30 : type === 'STONE' ? 28 : type === 'BARRICADE' ? 24 : 26),
                maxHp: maxHp, hp: maxHp, dmg: 0, rngPx: 0, spd: 0, atkInt: 1.0, atkT: 0,
                dead: false, hitFx: 0, rarity: 'Common', ability: '', baseDmg: 0, baseMaxHp: maxHp,
                faceX: 0, faceY: -1, kstreak: 0, ktier: 0, defShoot: (isCore || type === 'METAL') };
      if (isCore)                { e.dmg = 110; e.rngPx = 160; }   // the Town Hall returns fire
      else if (type === 'METAL') { e.dmg = 55;  e.rngPx = 150; }   // metal towers shoot too
      return e;
    }
    // the WATCH: a marquee defender + a few rival dogs (real cards BY NAME) the target placed.
    function buildWatch() {
      var src = (RT && (Array.isArray(RT.roster) ? RT.roster : (Array.isArray(RT.crew) ? RT.crew : []))) || [];
      var pool = [];
      for (var i = 0; i < src.length; i++) { var n = src[i]; if (n && (roster[n] || EMBED[n])) pool.push(n); }
      if (!pool.length) pool = cheapNames(roster);
      var boss = (foeName && (roster[foeName] || EMBED[foeName])) ? foeName : pool[0];
      var names = [];
      for (var k = 0; k < pool.length && names.length < 4; k++) if (pool[k] !== boss) names.push(pool[k]);
      return { boss: boss, names: names };                  // boss + up to 4 (defender cap = 60fps guard)
    }

    function build() {
      if (ASSAULT) {                                        // ----- enter the TARGET's district -----
        var GATE_Y = AH * 0.63;                             // the gate line -- you breach from here, the base is right ahead
        allyCore = mk('$BCARDD', 0, AW / 2, clamp(GATE_Y + 120, 0, AH - 40), 'core'); allyCore.name = 'YOUR CREW';
        ents = [allyCore];
        var coreStruct = null, bmax = 0, cnt = 0;
        for (var i = 0; i < RT.layout.length && cnt < 22; i++) {     // cap structures (60fps guard)
          var st = mkStruct(RT.layout[i]); ents.push(st); cnt++; bmax += st.maxHp | 0;
          if (st.isCore && !coreStruct) coreStruct = st;
        }
        if (!coreStruct) { coreStruct = mkStruct({ type: 'CORE', x: 50, y: 34, maxHp: RT.coreHp }); ents.push(coreStruct); bmax += coreStruct.maxHp | 0; }
        S.baseMaxHp = bmax;
        foeCore = coreStruct;                               // Town Hall = win target + foe respawn anchor
        hero = mk(heroName, 0, AW / 2, GATE_Y, 'hero');     // spawn AT the gate, on the base's doorstep -- in the action, fully controllable
        hero.spd = Math.max(hero.spd, 250);                 // snappy traversal of the district (no slow crawl across a tall map)
        var watch = buildWatch();
        foe = mk(watch.boss, 1, foeCore.x, foeCore.y + 64, 'hero');  // marquee defender guards the hall
        foe.defender = true; foe.guardX = foe.x; foe.guardY = foe.y;
        ents.push(foe);
        for (var w = 0; w < watch.names.length; w++) {
          var ang = -PI / 2 + (w / Math.max(1, watch.names.length)) * PI * 2;
          var gx = clamp(foeCore.x + Math.cos(ang) * 150, 40, AW - 40);
          var gy = clamp(foeCore.y + Math.sin(ang) * 120 + 60, 120, AH * 0.58);
          var d = mk(watch.names[w], 1, gx, gy, 'minion'); d.defender = true; d.guardX = gx; d.guardY = gy;
          ents.push(d);
        }
        // AK-CARDART: kick the unit portraits loading NOW so they render as REAL art, not the letter fallback.
        try { var pl = [heroName, watch.boss].concat(watch.names); for (var pi = 0; pi < pl.length; pi++) cardArtImg(pl[pi]); } catch (_pl) {}
        return;
      }
      allyCore = mk('$BCARDD', 0, AW / 2, AH - 110, 'core'); allyCore.name = 'YOUR CORE';
      foeCore  = mk(foeName,  1, AW / 2, 110,        'core'); foeCore.name  = 'RIVAL CORE';
      hero     = mk(heroName, 0, AW / 2, AH - 240, 'hero');
      foe      = mk(foeName,  1, AW / 2, 240,        'hero');
      ents = [allyCore, foeCore, hero, foe];
    }
    build();   // SYNCHRONOUS init -- step() never sees nulls (frame-1-safe).

    // ARSENAL: up to 3 of YOUR deck cards become castable SPELLS -- each casts its
    // OWN canon ability using its REAL stats (hp/damage/range). Always filled so the
    // spell bar is never empty (deck -> owned -> cheap roster fallback).
    var arsenal = (function () {
      var out = [], seen = {}; seen[heroName] = 1;
      function add(n) {
        if (!n || seen[n] || out.length >= 3) return;
        var raw = roster[n] || EMBED[n]; if (!raw) return;
        seen[n] = 1;
        out.push({ name: n, s: statline(raw), ab: (raw.ability && raw.ability.name) || 'Finisher',
                   cost: num(raw.cost, 4), cd: 0, cdMax: clamp(6 + num(raw.cost, 4), 6, 16) });
      }
      try {
        var p = ctx.econ && ctx.econ.loadProfile && ctx.econ.loadProfile();
        var d = p && (p.deck || p.activeDeck || p.deckNames);
        if (Array.isArray(d)) for (var i = 0; i < d.length; i++) add(d[i]);
        if (p && Array.isArray(p.owned)) for (var j = 0; j < p.owned.length; j++) add(p.owned[j]);
      } catch (_e) {}
      var pool = cheapNames(roster); for (var k = 0; k < pool.length; k++) add(pool[k]);
      return out;
    })();

    function spawnWave() {
      if (ASSAULT) return;   // a base assault has no lane minion waves -- the placed Watch defends
      for (var team = 0; team < 2; team++) {
        var alive = 0; for (var i = 0; i < ents.length; i++) if (ents[i].kind === 'minion' && ents[i].team === team && !ents[i].dead) alive++;
        if (alive >= MAX_MIN) continue;
        var baseY = team === 0 ? AH - 150 : 150;
        for (var k = 0; k < 3; k++) {
          var nm = minPool[Math.floor(Math.random() * minPool.length)];
          ents.push(mk(nm, team, AW / 2 + (k - 1) * 34 + rand(-8, 8), baseY + (team === 0 ? -1 : 1) * rand(0, 20), 'minion'));
        }
      }
    }

    function nearestEnemy(e, maxD) {
      var best = null, bd = maxD || 1e9;
      for (var i = 0; i < ents.length; i++) {
        var o = ents[i]; if (o.dead || o.team === e.team) continue;
        var d = hyp(o.x - e.x, o.y - e.y);
        if (d < bd) { bd = d; best = o; }
      }
      return best;
    }

    // KILL CREDIT (shared by melee + lasers + spells): the 3-tier DOG-GOD power-up
    // (stacks), the kill-heal, the needle-drop punch, and the last-hit gold/KO.
    function creditKill(att, tgt) {
      // AK-KILLSTREAK 2026-06-22: the KILLER scales up per kill -- 3 tiers (1 / 3 / 5+ kills), stat buff STACKS,
      // + a heal on kill (Mario-Star vibe). Resets to base when the unit itself dies (respawn). Both teams (lively + fair).
      if (att && !att.dead && att.kind !== 'core') {
        var prevTier = att.ktier | 0;   // AK-NEEDLEDROP: remember the old tier so we fire ONLY on a tier-UP
        att.kstreak = (att.kstreak | 0) + 1;
        att.ktier = att.kstreak >= 5 ? 3 : (att.kstreak >= 3 ? 2 : 1);
        att.dmg   = Math.round((att.baseDmg | 0) * (1 + 0.22 * att.ktier));
        att.maxHp = Math.round((att.baseMaxHp | 0) * (1 + 0.12 * att.ktier));
        att.hp    = Math.min(att.maxHp, att.hp + Math.round((att.baseMaxHp | 0) * 0.10));   // kill-heal
        // AK-NEEDLEDROP 2026-06-26 (Tarantino): on the PLAYER's DOG-GOD tier-up ONLY (the 1/3/5 escalation),
        // duck the district ambient bed + drop a short in-key percussive stinger. Higher tier = bigger drop.
        // A PUNCH, not every hit (gated on att === hero && ktier actually rose). Silent if music is off/absent.
        if (att === hero && att.ktier > prevTier && typeof window !== 'undefined') {
          try {
            if (window.AK_DISTRICTMUSIC && typeof window.AK_DISTRICTMUSIC.needleDrop === 'function') window.AK_DISTRICTMUSIC.needleDrop(att.ktier);
            else window.dispatchEvent(new CustomEvent('ak:needledrop', { detail: { intensity: att.ktier } }));
          } catch (_e) {}
        }
      }
      if (att && att.team === 0 && tgt.kind !== 'core') {  // last-hit gold (Mobile Legends)
        S.gold += tgt.kind === 'hero' ? 90 : 22;
        if (att === hero) S.kills += tgt.kind === 'hero' ? 2 : 1;
      }
    }
    function applyHit(att, tgt, dmg) {                      // damage + kill bookkeeping (no beam fx -- caller draws)
      tgt.hp -= dmg; tgt.hitFx = 0.12;
      if (tgt.hp <= 0 && !tgt.dead) {
        tgt.dead = true; tgt.respawnT = (tgt.kind === 'hero') ? HERO_RESPAWN : 0;
        if (tgt.kind === 'struct') spawnDebris(tgt.x, tgt.y, tgt.isCore);   // AK-RESTYLE: building falls -> rubble
        creditKill(att, tgt);
      }
    }
    function doAttack(att, tgt) {                           // melee / auto -- a short beam from att to tgt
      pushFx({ x1: att.x, y1: att.y, x2: tgt.x, y2: tgt.y, life: 0.12, col: att.team === 0 ? '#e8c55a' : '#ff6b6b' });
      applyHit(att, tgt, att.dmg);
    }

    /* ---- TWISTED-METAL ARSENAL: real-time AIMED lasers/projectiles ---- */
    function aimDir() {                                     // right-stick aim -> last face -> nearest foe -> up-lane
      if (inp.ax || inp.ay) { var m = hyp(inp.ax, inp.ay) || 1; return { x: inp.ax / m, y: inp.ay / m }; }
      if (hero.faceX || hero.faceY) { var n = hyp(hero.faceX, hero.faceY) || 1; return { x: hero.faceX / n, y: hero.faceY / n }; }
      var t = nearestEnemy(hero, 1e9); if (t) { var dx = t.x - hero.x, dy = t.y - hero.y, d = hyp(dx, dy) || 1; return { x: dx / d, y: dy / d }; }
      return { x: 0, y: -1 };
    }
    function spawnShot(x, y, ux, uy, dmg, col, team) {
      var m = hyp(ux, uy) || 1; ux /= m; uy /= m;
      if (shots.length >= MAX_SHOTS) shots.shift();         // cap -- recycle oldest
      shots.push({ x: x, y: y, vx: ux * LASER_SPD, vy: uy * LASER_SPD, life: LASER_LIFE, dmg: dmg, col: col, team: team, r: LASER_R });
      if (!REDUCED) pushFx({ x1: x, y1: y, x2: x + ux * 20, y2: y + uy * 20, life: 0.07, col: col });   // muzzle flash
    }
    function fireLaser(ux, uy) {                            // hero primary fire (the fire button + aim)
      if (S.over || hero.dead) return;
      if (hyp(ux, uy) < 0.05) { var t = nearestEnemy(hero, 1e9); if (t) { ux = t.x - hero.x; uy = t.y - hero.y; } else { ux = 0; uy = -1; } }
      var m = hyp(ux, uy) || 1; hero.faceX = ux / m; hero.faceY = uy / m;
      spawnShot(hero.x, hero.y, hero.faceX, hero.faceY, Math.round(hero.dmg * 0.85), '#7fe9ff', 0);
    }
    function stepShots(dt) {
      for (var i = shots.length - 1; i >= 0; i--) {
        var sh = shots[i]; sh.x += sh.vx * dt; sh.y += sh.vy * dt; sh.life -= dt;
        var hit = null;
        for (var j = 0; j < ents.length; j++) { var o = ents[j]; if (o.dead || o.team === sh.team) continue; if (hyp(o.x - sh.x, o.y - sh.y) <= sh.r + o.r) { hit = o; break; } }
        if (hit) { applyHit(sh.team === 0 ? hero : foe, hit, sh.dmg); if (sh.team === 0) boxHeroHit(); /* AK-FIX-lane-D:modes.js 2026-07-28: box the hero on a landed laser hit */ if (!REDUCED) pushFx({ ring: true, x: sh.x, y: sh.y, life: 0.18, col: sh.col, rmax: 28 }); shots.splice(i, 1); continue; }
        if (sh.life <= 0 || sh.x < -40 || sh.x > AW + 40 || sh.y < -40 || sh.y > AH + 40) shots.splice(i, 1);
      }
    }
    function countAllies() { var n = 0; for (var i = 0; i < ents.length; i++) if (ents[i].kind === 'ally' && !ents[i].dead) n++; return n; }
    function baseDestroyedPct() {                          // AK-BASEASSAULT: CoC-style % of the target's base wrecked
      if (!S.baseMaxHp) return 0;
      var removed = 0;
      for (var i = 0; i < ents.length; i++) { var e = ents[i]; if (e.kind === 'struct') removed += (e.maxHp | 0) - (e.dead ? 0 : (e.hp | 0)); }
      return clamp(removed / S.baseMaxHp, 0, 1);
    }

    /* ---- CARD SPELL: deploy a deck card as a UNIT + cast its ability (real stats) ---- */
    function castCard(idx) {
      if (S.over || hero.dead) return;
      var a = arsenal[idx]; if (!a || a.cd > 0 || S.energy < 26) return;
      S.energy -= 26; a.cd = a.cdMax;
      if (countAllies() < MAX_ALLY) {                       // the card fights on as a UNIT with its real stats
        var u = mk(a.name, 0, clamp(hero.x + rand(-28, 28), 30, AW - 30), clamp(hero.y + rand(8, 40), 30, AH - 30), 'ally');
        ents.push(u);
        if (!REDUCED) pushFx({ ring: true, x: u.x, y: u.y, life: 0.4, col: rarColor(a.s.rarity), rmax: 70 });
      }
      var dir = aimDir();
      if (a.s.rangeTiles >= 3) {                            // ranged ability -> a 3-laser volley using the card's damage
        for (var v = 0; v < 3; v++) {
          var ang = (v - 1) * 0.20, c = Math.cos(ang), sn = Math.sin(ang);
          spawnShot(hero.x, hero.y, dir.x * c - dir.y * sn, dir.x * sn + dir.y * c, Math.round(a.s.rawDmg * 0.5), rarColor(a.s.rarity), 0);
        }
      } else {                                              // melee ability -> an AoE nova using the card's damage
        var dmg = Math.round(a.s.rawDmg * 0.7);
        for (var i = 0; i < ents.length; i++) { var o = ents[i]; if (o.dead || o.team === 0) continue; if (hyp(o.x - hero.x, o.y - hero.y) < 112) applyHit(hero, o, dmg); }
        pushFx({ ring: true, x: hero.x, y: hero.y, life: 0.4, col: rarColor(a.s.rarity), rmax: 112 });
      }
      try { if (ctx.showBanner) ctx.showBanner(a.name + ' -- ' + a.ab, 1.0); } catch (_e) {}
    }

    function levelFromGold() {
      while (S.gold >= 100 * S.lvl) {                     // simple item/level curve
        S.gold -= 100 * S.lvl; S.lvl++;
        hero.dmg = Math.round(hero.dmg * 1.12);
        hero.maxHp = Math.round(hero.maxHp * 1.1);
        hero.hp = Math.min(hero.maxHp, hero.hp + Math.round(hero.maxHp * 0.12));
      }
    }

    function respawn(e, core) {
      e.dead = false; e.kstreak = 0; e.ktier = 0; e.dmg = e.baseDmg; e.maxHp = e.baseMaxHp;   // AK-KILLSTREAK: power-up ends on death
      e.hp = e.maxHp; e.atkT = 0;
      e.x = core.x + rand(-30, 30); e.y = core.y + (e.team === 0 ? -90 : 90);
    }

    function aiHero(e, dt) {
      e.think -= dt; e.fireT -= dt;
      if (e.think <= 0) { e.think = rand(0.7, 1.4); e.strafe = Math.random() < 0.5 ? -1 : 1; }
      var low = e.hp < e.maxHp * 0.3;
      var aim;
      if (low) { aim = foeCore; }                          // retreat to own core to regen-heal
      else { aim = nearestEnemy(e, 1e9) || allyCore; }
      var dx = aim.x - e.x, dy = aim.y - e.y, d = hyp(dx, dy) || 1;
      var reach = e.rngPx + aim.r * 0.5;
      if (low) {                                           // run home, regen near core
        e.x += (dx / d) * e.spd * dt; e.y += (dy / d) * e.spd * dt;
        if (hyp(foeCore.x - e.x, foeCore.y - e.y) < 120) e.hp = Math.min(e.maxHp, e.hp + e.maxHp * 0.10 * dt);
        return;
      }
      if (e.fireT <= 0 && d > e.rngPx * 0.8) { spawnShot(e.x, e.y, dx, dy, Math.round(e.dmg * 0.6), '#ff7a7a', 1); e.fireT = 1.15; }   // rival returns fire -- dodge it
      if (d > reach) {                                     // close with a little strafe juke
        var px = -dy / d, py = dx / d;
        e.x += ((dx / d) + px * e.strafe * 0.35) * e.spd * dt;
        e.y += ((dy / d) + py * e.strafe * 0.35) * e.spd * dt;
      } else if (e.atkT <= 0) { doAttack(e, aim); e.atkT = e.atkInt; }
    }

    function step(dt) {
      S.t -= dt;
      if (S.energy < S.eMax) S.energy = Math.min(S.eMax, S.energy + 13 * dt);
      S.waveT -= dt; if (S.waveT <= 0) { spawnWave(); S.waveT = WAVE_INT; }
      for (var s in S.sg) if (S.sg[s] > 0) S.sg[s] = Math.max(0, S.sg[s] - dt);
      for (var ci = 0; ci < arsenal.length; ci++) if (arsenal[ci].cd > 0) arsenal[ci].cd = Math.max(0, arsenal[ci].cd - dt);
      if ((inp.ax || inp.ay) && S.sg.fire <= 0 && !hero.dead) { fireLaser(inp.ax, inp.ay); S.sg.fire = FIRE_CD; }   // right-stick auto-fire
      stepShots(dt);
      levelFromGold();

      for (var i = 0; i < ents.length; i++) {
        var e = ents[i];
        if (e.hitFx > 0) e.hitFx -= dt;
        if (e.atkT > 0) e.atkT -= dt;

        if (e.dead) {                                      // respawn heroes; minions stay down
          if (e.kind === 'hero') { e.respawnT -= dt; if (e.respawnT <= 0) respawn(e, e === hero ? allyCore : foeCore); }
          continue;
        }

        if (e === hero) {                                  // player-controlled
          var mvm = hyp(inp.mvx, inp.mvy);
          if (mvm > 0.01) { hero.x += (inp.mvx / mvm) * hero.spd * dt * Math.min(1, mvm); hero.y += (inp.mvy / mvm) * hero.spd * dt * Math.min(1, mvm); }
          hero.x = clamp(hero.x, 30, AW - 30); hero.y = clamp(hero.y, 30, AH - 30);
          var ht = nearestEnemy(hero, hero.rngPx + 6);     // auto-attack in range
          if (ht && hero.atkT <= 0) { doAttack(hero, ht); hero.atkT = hero.atkInt; boxHeroHit(); }   /* AK-FIX-lane-D:modes.js 2026-07-28: box the hero on a landed melee hit */
          continue;
        }
        if (e === foe) { aiHero(e, dt); continue; }

        if (e.kind === 'struct') {                         // AK-BASEASSAULT: static building -- only the Hall + metal towers fire
          if (e.defShoot && e.dmg > 0) { var stt = nearestEnemy(e, e.rngPx); if (stt && e.atkT <= 0) { doAttack(e, stt); e.atkT = e.atkInt; } }
          continue;
        }
        if (e.defender) {                                  // a Watch defender: engage intruders, else hold the post
          var fE = nearestEnemy(e, 380);
          if (fE) {
            var dxx = fE.x - e.x, dyy = fE.y - e.y, dd = hyp(dxx, dyy) || 1, rr = e.rngPx + fE.r * 0.5;
            if (dd > rr) { e.x += (dxx / dd) * e.spd * dt; e.y += (dyy / dd) * e.spd * dt; }
            else if (e.atkT <= 0) { doAttack(e, fE); e.atkT = e.atkInt; }
          } else {
            var gx = e.guardX - e.x, gy = e.guardY - e.y, gd = hyp(gx, gy);
            if (gd > 6) { e.x += (gx / gd) * e.spd * dt * 0.8; e.y += (gy / gd) * e.spd * dt * 0.8; }
          }
          continue;
        }

        if (e.kind === 'core') {                           // turret: shoot anything in range
          var ct = nearestEnemy(e, e.rngPx);
          if (ct && e.atkT <= 0) { doAttack(e, ct); e.atkT = e.atkInt; }
          continue;
        }
        // minion march + fight (push toward the enemy core, brawl on contact)
        var aim = nearestEnemy(e, 240) || (e.team === 0 ? foeCore : allyCore);
        var dx = aim.x - e.x, dy = aim.y - e.y, d = hyp(dx, dy) || 1;
        var reach = e.rngPx + aim.r * 0.5;
        if (d > reach) { e.x += (dx / d) * e.spd * dt; e.y += (dy / d) * e.spd * dt; }
        else if (e.atkT <= 0) { doAttack(e, aim); e.atkT = e.atkInt; }
      }

      for (var f = fx.length - 1; f >= 0; f--) { var fxo = fx[f]; if (fxo.debris) { fxo.x += fxo.vx * dt; fxo.y += fxo.vy * dt; fxo.vy += 320 * dt; } fxo.life -= dt; if (fxo.life <= 0) fx.splice(f, 1); }
      // cull dead minions + spent allies -- cores + heroes persist (heroes respawn)
      ents = ents.filter(function (e) { return (e.kind === 'minion' || e.kind === 'ally') ? !e.dead : true; });

      if (!S.over) {
        if (ASSAULT) {                                     // AK-BASEASSAULT: crack the Town Hall / wipe the base = WIN
          var coreDead = foeCore.dead || (foeCore.hp | 0) <= 0;
          var liveStruct = 0; for (var qi = 0; qi < ents.length; qi++) { var q = ents[qi]; if (q.kind === 'struct' && !q.dead) liveStruct++; }
          if (coreDead || liveStruct === 0) { S.over = true; S.win = true; S.stars = 3; finish(); }
          else if (S.t <= 0) { var pct = baseDestroyedPct(); S.stars = pct >= 0.99 ? 3 : (pct >= 0.75 ? 2 : (pct >= 0.5 ? 1 : 0)); S.over = true; S.win = pct >= 0.5; finish(); }
        } else if (foeCore.hp <= 0) { S.over = true; S.win = true; finish(); }
        else if (allyCore.hp <= 0) { S.over = true; S.win = false; finish(); }
        else if (S.t <= 0) { S.over = true; S.win = (foeCore.hp / foeCore.maxHp) < (allyCore.hp / allyCore.maxHp); finish(); }
      }
    }

    function useSkill(which) {
      if (S.over || hero.dead) return;
      if (which === 'fire') {                              // TWISTED-METAL primary -- aimed laser, cooldown-gated (free)
        if (S.sg.fire > 0) return;
        fireLaser(hero.faceX, hero.faceY); S.sg.fire = FIRE_CD; return;
      }
      if (which === 'mob') {                               // DASH toward stick dir (else up-lane)
        if (S.energy < 20 || S.sg.mob > 0) return; S.energy -= 20;
        var m = hyp(inp.mvx, inp.mvy); var ux = 0, uy = -1;
        if (m > 0.05) { ux = inp.mvx / m; uy = inp.mvy / m; }
        hero.x = clamp(hero.x + ux * 150, 30, AW - 30); hero.y = clamp(hero.y + uy * 150, 30, AH - 30);
        hero.faceX = ux; hero.faceY = uy;
        S.sg.mob = 4; pushFx({ x1: hero.x, y1: hero.y, x2: hero.x, y2: hero.y, life: 0.2, col: '#7CFFb0' }); return;
      }
      if (which === 'ult') {                               // ULT = the hero's named card ability: heavy nuke + self-heal
        if (S.energy < 70 || S.sg.ult > 0) return; S.energy -= 70;
        var t = nearestEnemy(hero, 1e9);
        if (t) { var save = hero.dmg; hero.dmg = Math.round(hero.dmg * 4); doAttack(hero, t); hero.dmg = save; }
        hero.hp = Math.min(hero.maxHp, hero.hp + Math.round(hero.maxHp * 0.25));
        S.sg.ult = 18; pushFx({ ring: true, x: t ? t.x : hero.x, y: t ? t.y : hero.y, life: 0.5, col: '#ff8fae', rmax: 95 }); return;
      }
      // TODO-RESEARCH: jungle buffs + a Lord objective, draft/ban, 5v5, multiplayer netcode.
    }

    function finish() {
      // AK-BASEASSAULT: in a RAID the loot is the TARGET's stash, granted by the
      // caller's onResult (target.reward) -- so suppress the generic MOBA payout and
      // only move rank, keeping the loot exactly-once. A plain MOBA still pays soft reward.
      if (ASSAULT) { try { if (ctx.econ && ctx.econ.addTrophies) ctx.econ.addTrophies(S.win ? 22 : -8); } catch (_e) {} }
      else grantReward(ctx, S.win, 'moba');
      recordResult(ctx, ASSAULT ? 'raid-assault' : 'world-moba', S.win, S.kills * 10 + (S.win ? 100 : 0));
      // TODO-SERVER: server-authoritative result + crew leaderboard (ride ak_grants).
      setTimeout(function () { if (api) api.close({ win: S.win, kills: S.kills, stars: S.stars | 0 }); }, 1400);
    }

    function layoutButtons() {
      var pad = 14;
      var R = Math.max(27, Math.min(34, vp.w * 0.088));     // FIRE (primary)
      var r = Math.max(20, Math.min(26, vp.w * 0.064));     // skills + spells
      var cx = vp.w - R - pad, cy = vp.h - R - pad;
      BTN.fire = { x: cx,                 y: cy,                 r: R };
      BTN.mob  = { x: cx - (R + r + 8),   y: cy + 2,             r: r };
      BTN.ult  = { x: cx + 2,             y: cy - (R + r + 8),   r: r };
      // card-spell arsenal: a row hugging the bottom, growing leftward from the cluster
      var sy = vp.h - r - pad, sx = cx - (R + r + 8) - (r + 12);
      for (var i = 0; i < arsenal.length; i++) BTN['s' + i] = { x: sx - i * (r * 2 + 9), y: sy, r: r, spell: i };
    }
    function w2s(x, y, cam) { return { x: x - cam.x, y: y - cam.y }; }
    function simpleStruct(g, x, y, e) {                    // fallback building draw (raidscene sprite art absent / headless)
      var r = e.r;
      g.save();
      g.fillStyle = e.isCore ? '#15110a' : '#2a2620'; g.fillRect(x - r, y - r, r * 2, r * 2);
      g.lineWidth = 2; g.strokeStyle = e.isCore ? '#e8c55a' : RT_ACCENT; g.strokeRect(x - r, y - r, r * 2, r * 2);
      g.fillStyle = e.isCore ? '#e8c55a' : '#b9a76a'; g.font = '900 ' + Math.round(r * 0.9) + 'px Inter,sans-serif';
      g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(e.isCore ? '♛' : String(e.stype || 'B').charAt(0), x, y + 1);
      g.restore();
    }

    function draw(g, _vp) {
      vp = _vp;
      if (!BTN.fire) layoutButtons();
      var camX = AW <= vp.w ? (AW - vp.w) / 2 : clamp(hero.x - vp.w / 2, 0, AW - vp.w);
      var camY = AH <= vp.h ? (AH - vp.h) / 2 : clamp(hero.y - vp.h / 2, 0, AH - vp.h);
      var cam = { x: camX, y: camY };

      g.fillStyle = '#0a0c12'; g.fillRect(0, 0, vp.w, vp.h);
      if (ASSAULT) {                                       // AK-BASEASSAULT: their REAL district floor (hub ground tile) + the breach gate
        var plot = w2s(AW * 0.04, 90, cam), plotW = AW * 0.92, plotH = AH * 0.66;
        var grd = hubImg(ASSAULT_GROUND);
        if (imgReady(grd)) {                               // tile the district ground the player knows (capped -- 60fps)
          g.save(); g.beginPath(); g.rect(plot.x, plot.y, plotW, plotH); g.clip();
          var ts = 256, tiles = 0;
          for (var gyT = plot.y; gyT < plot.y + plotH && tiles < 40; gyT += ts)
            for (var gxT = plot.x; gxT < plot.x + plotW && tiles < 40; gxT += ts) { g.drawImage(grd, gxT, gyT, ts, ts); tiles++; }
          g.globalAlpha = 0.34; g.fillStyle = '#0a0c12'; g.fillRect(plot.x, plot.y, plotW, plotH); g.restore();   // darken for unit contrast
        } else { g.fillStyle = 'rgba(201,168,76,.05)'; g.fillRect(plot.x, plot.y, plotW, plotH); }
        g.save(); g.globalAlpha = 0.6; g.lineWidth = 2; g.strokeStyle = RT_ACCENT; g.strokeRect(plot.x, plot.y, plotW, plotH); g.restore();
        // the GATE you breach from (a gold dashed threshold at the base front)
        var gateY = w2s(0, AH * 0.62, cam).y, gxa = w2s(AW * 0.30, 0, cam).x, gxb = w2s(AW * 0.70, 0, cam).x;
        g.save(); g.strokeStyle = '#e8c55a'; g.globalAlpha = 0.85; g.lineWidth = 3; if (g.setLineDash) g.setLineDash([11, 7]);
        g.beginPath(); g.moveTo(gxa, gateY); g.lineTo(gxb, gateY); g.stroke(); if (g.setLineDash) g.setLineDash([]);
        g.fillStyle = '#e8c55a'; g.font = '900 10px Inter,sans-serif'; g.textAlign = 'center'; g.fillText('▲ BREACH GATE ▲', (gxa + gxb) / 2, gateY + 14); g.restore();
      } else {
        // lane
        var l = w2s(AW / 2 - 80, 0, cam), r2 = w2s(AW / 2 + 80, 0, cam);
        g.fillStyle = 'rgba(201,168,76,.05)'; g.fillRect(l.x, -cam.y, 160, AH);
        g.strokeStyle = 'rgba(201,168,76,.12)'; g.lineWidth = 2;
        g.beginPath(); g.moveTo(l.x, -cam.y); g.lineTo(l.x, AH - cam.y); g.moveTo(r2.x, -cam.y); g.lineTo(r2.x, AH - cam.y); g.stroke();
      }

      // fx beams + rings + debris
      for (var fi = 0; fi < fx.length; fi++) { var x = fx[fi]; g.save();
        if (x.debris) { g.globalAlpha = clamp(x.life * 2, 0, 1); var dpt = w2s(x.x, x.y, cam); g.fillStyle = x.col; g.fillRect(dpt.x, dpt.y, x.sz, x.sz); }
        else if (x.ring) { g.globalAlpha = clamp(x.life * 2, 0, 1); g.strokeStyle = x.col; g.lineWidth = 3; var p = w2s(x.x, x.y, cam); g.beginPath(); g.arc(p.x, p.y, (x.rmax || 95) * (1 - x.life), 0, 2 * PI); g.stroke(); }
        else { g.globalAlpha = clamp(x.life * 6, 0, 1); g.strokeStyle = x.col; g.lineWidth = 2; var a = w2s(x.x1, x.y1, cam), b = w2s(x.x2, x.y2, cam); g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke(); }
        g.restore();
      }
      // lasers / projectiles in flight (the Twisted-Metal arsenal)
      for (var si = 0; si < shots.length; si++) {
        var sh = shots[si], hpt = w2s(sh.x, sh.y, cam);
        if (hpt.x < -30 || hpt.x > vp.w + 30 || hpt.y < -30 || hpt.y > vp.h + 30) continue;
        var sm = hyp(sh.vx, sh.vy) || 1, tx = hpt.x - sh.vx / sm * 15, ty = hpt.y - sh.vy / sm * 15;
        g.save(); g.strokeStyle = sh.col; g.lineWidth = 3; g.beginPath(); g.moveTo(tx, ty); g.lineTo(hpt.x, hpt.y); g.stroke();
        g.fillStyle = sh.col; g.beginPath(); g.arc(hpt.x, hpt.y, 3, 0, 2 * PI); g.fill(); g.restore();
      }
      // entities
      for (var i = 0; i < ents.length; i++) {
        var e = ents[i];
        if (e.dead && e.kind !== 'core') {                 // show a respawn pip for a downed hero
          if (e.kind === 'hero') { var dp = w2s(e === hero ? allyCore.x : foeCore.x, (e === hero ? allyCore.y - 70 : foeCore.y + 70), cam);
            g.save(); g.globalAlpha = .8; g.fillStyle = e.team === 0 ? '#e8c55a' : '#ff6b6b'; g.font = '700 11px Inter,sans-serif'; g.textAlign = 'center'; g.fillText('respawn ' + Math.ceil(e.respawnT) + 's', dp.x, dp.y); g.restore(); }
          continue;
        }
        var sp = w2s(e.x, e.y, cam);
        if (sp.x < -60 || sp.x > vp.w + 60 || sp.y < -60 || sp.y > vp.h + 60) continue;
        if (e.kind === 'struct') {                         // AK-BASEASSAULT: damageable building (build-mode sprite look)
          var ssz = e.r * 2;
          if (global.AK_RAIDSCENE && typeof global.AK_RAIDSCENE.drawStruct === 'function') {
            try { global.AK_RAIDSCENE.drawStruct(g, { type: e.stype, hp: e.hp, maxHp: e.maxHp, name: e.name }, sp.x, sp.y, ssz, RT_ACCENT); }
            catch (_ds) { simpleStruct(g, sp.x, sp.y, e); }
          } else simpleStruct(g, sp.x, sp.y, e);
          if (e.hitFx > 0) { g.save(); g.globalAlpha = clamp(e.hitFx * 5, 0, 0.6); g.fillStyle = '#fff'; g.fillRect(sp.x - e.r, sp.y - e.r, e.r * 2, e.r * 2); g.restore(); }
          barNotch(g, sp.x - e.r, sp.y - e.r - 9, e.r * 2, 5, e.hp / e.maxHp, e.isCore ? '#e8c55a' : '#ff8a6b');
          continue;
        }
        var fill = e.team === 0 ? '#caa84c' : '#b8434c';
        var ring = e === hero ? '#fff' : rarColor(e.rarity);
        if (e.kind === 'core') { g.save(); g.fillStyle = e.team === 0 ? '#1c2a18' : '#2a1418'; g.strokeStyle = ring; g.lineWidth = 3; g.beginPath(); g.arc(sp.x, sp.y, e.r, 0, 2 * PI); g.fill(); g.stroke(); g.restore(); }
        else dogChip(g, sp.x, sp.y, e.r + (e.hitFx > 0 ? 2 : 0), fill, ring, chipLetter(e.name), e.name);
        if (e.ktier > 0 && e.kind !== 'core') {   // AK-KILLSTREAK: the Mario-Star aura -- tier 1 green / 2 gold / 3 magenta + star pips
          var kc = e.ktier >= 3 ? '#ff3df0' : (e.ktier >= 2 ? '#ffd76b' : '#7CFFb0');
          var pulse = REDUCED ? 0.72 : (0.5 + 0.3 * Math.abs(Math.sin((S.t || 0) * 5)));   // static under reduced-motion
          g.save(); g.globalAlpha = pulse; g.strokeStyle = kc; g.lineWidth = 1.5 + e.ktier;
          g.beginPath(); g.arc(sp.x, sp.y, e.r + 4 + e.ktier * 2, 0, 2 * PI); g.stroke();
          g.globalAlpha = 1; g.fillStyle = kc; g.font = '700 9px Inter,sans-serif'; g.textAlign = 'center';
          g.fillText('★'.repeat(e.ktier), sp.x, sp.y - e.r - 6); g.restore();
        }
        bar(g, sp.x - e.r, sp.y - e.r - 8, e.r * 2, 4, e.hp / e.maxHp, e.team === 0 ? '#6be08a' : '#ff6b6b');
      }
      // aim reticle (right-stick) -- the Twisted-Metal targeting feel
      if (!S.over && !hero.dead && (inp.ax || inp.ay)) {
        var hsp = w2s(hero.x, hero.y, cam), am = hyp(inp.ax, inp.ay) || 1, axx = inp.ax / am, ayy = inp.ay / am;
        g.save(); g.globalAlpha = 0.55; g.strokeStyle = '#7fe9ff'; g.lineWidth = 2;
        g.beginPath(); g.moveTo(hsp.x, hsp.y); g.lineTo(hsp.x + axx * 92, hsp.y + ayy * 92); g.stroke();
        g.beginPath(); g.arc(hsp.x + axx * 92, hsp.y + ayy * 92, 7, 0, 2 * PI); g.stroke(); g.restore();
      }
      // left move-stick ring (when held)
      if (inp.mvId != null) {
        g.save(); g.globalAlpha = 0.4; g.strokeStyle = '#e8c55a'; g.lineWidth = 2;
        g.beginPath(); g.arc(inp.mox, inp.moy, 46, 0, 2 * PI); g.stroke();
        g.globalAlpha = 0.5; g.fillStyle = '#e8c55a'; g.beginPath(); g.arc(inp.mox + inp.mvx * 46, inp.moy + inp.mvy * 46, 15, 0, 2 * PI); g.fill(); g.restore();
      }
      if (ASSAULT && !REDUCED) drawGrit(g, vp);             // AK-RESTYLE: gold-cyberpunk vignette + grain (over world, under HUD)
      drawHUD(g);
    }

    function drawHUD(g) {
      // top taskbar: gold + level + kills + clock + mode title (Mobile Legends)
      g.save();
      g.fillStyle = 'rgba(6,6,12,.82)'; g.fillRect(0, 0, vp.w, 40);
      g.fillStyle = '#e8c55a'; g.font = '900 14px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle';
      g.fillText('GOLD ' + S.gold, 12, 20);
      g.fillText('LV ' + S.lvl, 104, 20);
      g.fillText('KO ' + S.kills, 158, 20);
      g.fillStyle = '#cfe'; g.fillText(fmtClock(S.t), 212, 20);
      g.textAlign = 'center'; g.font = '700 11px Inter,sans-serif';
      if (ASSAULT) { g.fillStyle = '#e8c55a'; g.fillText((opts.label || 'RAID') + '   BASE ' + Math.round(baseDestroyedPct() * 100) + '%', vp.w / 2, 20); }
      else { g.fillStyle = '#7fc8ff'; g.fillText(opts.label || ('WORLD MOBA  ·  ' + hero.name + '  vs  ' + foe.name), vp.w / 2, 20); }
      g.restore();
      // hero health + energy + a small MOBA stat readout (top-left)
      bar(g, 14, 48, 168, 12, hero.hp / hero.maxHp, '#6be08a');
      bar(g, 14, 64, 168, 9, S.energy / S.eMax, '#5ab0ff');
      g.fillStyle = '#cfe'; g.font = '700 9px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle';
      g.fillText('HP', 186, 54); g.fillText('EN', 186, 69);
      g.fillStyle = hero.ktier > 0 ? '#ffd76b' : '#b9a76a'; g.font = '700 9px Inter,sans-serif';
      g.fillText('DMG ' + hero.dmg + '   AS ' + (1 / Math.max(0.3, hero.atkInt)).toFixed(1) + '   RNG ' + heroStat.rangeTiles + (hero.ktier > 0 ? '   DOG-GOD ' + hero.ktier : ''), 14, 82);
      if (ASSAULT) {                                         // AK-RESTYLE: a notched gold gauge for the target base's integrity
        barNotch(g, 14, 92, 168, 6, 1 - baseDestroyedPct(), '#e8c55a');
        g.fillStyle = '#b9a76a'; g.font = '700 8px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText('TARGET BASE INTEGRITY', 14, 104);
      }
      // ARSENAL (right): FIRE laser + DASH + ULT(named ability) + the deck-card SPELLS
      drawBtn(g, BTN.fire, S.sg.fire <= 0 && !hero.dead,                  '◎', 'FIRE', '#7fe9ff', S.sg.fire / FIRE_CD);
      drawBtn(g, BTN.mob,  S.energy >= 20 && S.sg.mob <= 0 && !hero.dead, '»', 'DASH', '#7CFFb0', S.sg.mob / 4);
      drawBtn(g, BTN.ult,  S.energy >= 70 && S.sg.ult <= 0 && !hero.dead, '★', (hero.ability || 'ULT').slice(0, 5).toUpperCase(), '#ff8fae', S.sg.ult / 18);
      for (var k = 0; k < arsenal.length; k++) {
        var a = arsenal[k], b = BTN['s' + k]; if (!b) continue;
        drawBtn(g, b, a.cd <= 0 && S.energy >= 26 && !hero.dead, chipLetter(a.name), a.ab.slice(0, 5).toUpperCase(), rarColor(a.s.rarity), a.cd / a.cdMax);
      }
      // minimap (top-right)
      var mw = 56, mh = 88, mx = vp.w - mw - 8, my = 44;
      g.save(); g.fillStyle = 'rgba(8,8,14,.7)'; g.fillRect(mx, my, mw, mh);
      g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1; g.strokeRect(mx, my, mw, mh);
      for (var i = 0; i < ents.length; i++) { var e = ents[i]; if (e.dead) continue; g.fillStyle = e.team === 0 ? '#e8c55a' : '#ff6b6b'; g.beginPath(); g.arc(mx + (e.x / AW) * mw, my + (e.y / AH) * mh, e.kind === 'core' ? 3 : (e.kind === 'hero' ? 2.5 : 1.5), 0, 2 * PI); g.fill(); }
      g.restore();
      if (S.over) {
        if (ASSAULT) centerBanner(g, vp, S.win ? ('BASE WIPED -- ' + (S.stars | 0) + '★ LOOT SECURED') : 'RAID REPELLED -- FALL BACK', S.win ? '#6be08a' : '#ff6b6b');
        else centerBanner(g, vp, S.win ? 'CORE CRACKED -- YOU RULE THE LANE' : 'YOUR CORE FELL -- RUN IT BACK', S.win ? '#6be08a' : '#ff6b6b');
      }
    }

    function pointer(evt) {
      if (!vp) return;                                     // ignore taps before the first frame lays out vp/buttons
      var x = evt.clientX, y = evt.clientY, t = evt.type;
      if (t === 'pointerdown') {
        for (var k in BTN) { var b = BTN[k]; if (hyp(x - b.x, y - b.y) <= b.r + 6) { if (b.spell != null) castCard(b.spell); else useSkill(k); return; } }
        if (x < vp.w * 0.5) { inp.mvId = evt.pointerId; inp.mox = x; inp.moy = y; inp.mvx = 0; inp.mvy = 0; }   // LEFT half = move
        else { inp.aimId = evt.pointerId; inp.aox = x; inp.aoy = y; inp.ax = 0; inp.ay = 0; useSkill('fire'); } // RIGHT half = aim; tap also fires
      } else if (t === 'pointermove') {
        if (evt.pointerId === inp.mvId) { var dx = x - inp.mox, dy = y - inp.moy, m = hyp(dx, dy), cl = Math.min(m, 50) / 50, u = m || 1; inp.mvx = dx / u * cl; inp.mvy = dy / u * cl; }
        else if (evt.pointerId === inp.aimId) { var adx = x - inp.aox, ady = y - inp.aoy, am = hyp(adx, ady), au = am || 1, acl = Math.min(am, 46) / 46; inp.ax = adx / au * acl; inp.ay = ady / au * acl; }
      } else {
        if (evt.pointerId === inp.mvId) { inp.mvId = null; inp.mvx = 0; inp.mvy = 0; }
        if (evt.pointerId === inp.aimId) { inp.aimId = null; inp.ax = 0; inp.ay = 0; }
      }
    }

    if (ctx.showBanner) ctx.showBanner(opts.label || 'WORLD MOBA -- push the lane', 1.4);
    api = ctx.overlay.open({
      id: 'mode_world_moba',
      onFrame: function (g, dt, _vp) { if (!S.over) step(dt); else { for (var f = fx.length - 1; f >= 0; f--) { fx[f].life -= dt; if (fx[f].life <= 0) fx.splice(f, 1); } } draw(g, _vp); },
      onPointer: function (evt) { pointer(evt); },
      onClose: function (res) { if (ctx.showBanner && res) ctx.showBanner(res.win ? 'MOBA WON · loot banked' : 'MOBA lost', 1.6); if (opts.onResult) try { opts.onResult(res); } catch (_e) {} }
    });
    return api;
  }

  /* ===================================================================== */
  /* AK-GULAGFPS 2026-07-18 -- FIRST-PERSON RENDER PATH for the Gulag.
   * The gulag LOGIC LAYER IS UNTOUCHED. step() / aiThink() / fire() / moveF()
   * still own every position, hit, LOS test and win condition; this layer only
   * (a) DRAWS that same state through an eye-height Three.js camera and (b)
   * maps look-drag to yaw before handing the SAME inp.mvx/mvy/ax/ay the 2D
   * path always used straight back to step(). Nothing here decides an outcome:
   * cover, bullets and hp are READ, never recomputed.
   *
   * HARD GATE: window.AK_THREE.ok(). No boot lane, no WebGL, a throw during
   * scene build, or a context lost mid-match all fall through to the EXISTING
   * Canvas2D renderer, unchanged, on the very next frame. A missing Three.js
   * CANNOT break a mode that works today.
   *
   * It renders to its OWN offscreen WebGL canvas and blits into the overlay's
   * Canvas2D via drawImage, so index.html's overlay host needs no change and
   * the 2D HUD still paints on top exactly as before.
   * ===================================================================== */
  var EYE = 26, COVER_H = 34, WALL_H = 96;   // arena units ARE world units (1:1 with the 2D AW/AH grid)
  var LOOK_SENS = 0.0055, PITCH_MAX = 0.55;

  // The boot lane's handoff (systems/three_boot.js). Its ok() is false until someone
  // has awaited ready(), and NOTHING calls ready() on its own, so warming the loader
  // is this lane's job. ready() never throws and never rejects; it owns no renderer
  // and no canvas, so warming it costs zero WebGL contexts.
  function warmThree() {
    var B = global.AK_THREE;
    if (!B || typeof B.ready !== 'function') return;
    try { B.ready(); } catch (_e) {}
  }
  function threeLib() {
    var B = global.AK_THREE;
    if (!B || typeof B.ok !== 'function') return null;
    var live = false; try { live = !!B.ok(); } catch (_e) { return null; }
    if (!live) { warmThree(); return null; }               // not up yet: kick the load, caller stays 2D this frame
    var T = null;
    if (typeof B.get === 'function') { try { T = B.get(); } catch (_e2) { T = null; } }
    if (!T) T = B.THREE || B.lib || global.THREE || null;
    return (T && T.Scene && T.WebGLRenderer && T.PerspectiveCamera && T.Mesh) ? T : null;
  }
  /* THE ONE RENDERER. three_boot's budget block is explicit: ONE WebGLRenderer for the
   * whole game, shared by every 3D mode, because a phone starts evicting contexts around
   * 8 and the model-viewer hub pool already spends 5. So this parks the singleton on
   * window.AK_THREE_RENDERER, reuses it if another 3D lane got there first, and NEVER
   * disposes it on mode exit (a disposed singleton would blind the next lane). Per-match
   * scene resources ARE disposed. Other 3D lanes: read this global before you construct.  */
  function sharedRenderer(T) {
    var R = global.AK_THREE_RENDERER || null;
    if (R && R.domElement) return R;
    var cv = document.createElement('canvas');
    R = new T.WebGLRenderer({ canvas: cv, antialias: false, alpha: false, preserveDrawingBuffer: true });
    R.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));   // three_boot law: never above 2
    try { global.AK_THREE_RENDERER = R; } catch (_e) {}
    return R;
  }
  /* three_boot: "On entering a full-3D mode, drop the model-viewer ally pool first."
   * Frees up to 4 contexts so the hero model-viewer + this renderer stay inside the wall. */
  function allyPool(on) {
    try { var p = global.__ak3d; if (p && typeof p.on === 'boolean') { var was = p.on; p.on = !!on; return was; } } catch (_e) {}
    return null;
  }
  function juiceImpact(dmg) {                 // systems/juice.js owns the 5-tier feel; never reimplemented here
    try { if (global.AK_JUICE && typeof global.AK_JUICE.impact === 'function') return global.AK_JUICE.impact(dmg); } catch (_e) {}
    return null;
  }

  /* Builds the first-person view of an ALREADY-BUILT gulag arena. Returns null
   * (-> caller keeps the 2D renderer) on any gate miss or build failure.       */
  function gulagFPS(AW, AH, cover) {
    if (typeof document === 'undefined') return null;
    var T = threeLib();
    if (!T) return null;

    var cv, ren, scene, cam, rvGrp, gun, flash, flashLight, rvFlash, rvMixer = null, allyWas = null;   // AK-GULAGWALK: rvMixer drives the opponent's walk clip
    var junk = [], pool = [], dead = false;
    var yaw = 0, pitch = 0, recoil = 0, flashT = 0, rvFlashT = 0, shake = 0, mark = 0;
    var stick = { x: 0, y: 0 }, lx = 0, ly = 0, lastW = 0, lastH = 0;
    var lastYouHp = -1, lastRvHp = -1, lastFireT = 0, lastRvFireT = 0;

    function mat(cls, o) { var m = new T[cls](o); junk.push(m); return m; }
    function geo(cls, a, b, c) { var gg = new T[cls](a, b, c); junk.push(gg); return gg; }
    function box(w, h, d, col, em, x, y, z) {
      var m = new T.Mesh(geo('BoxGeometry', w, h, d), mat('MeshLambertMaterial', { color: col, emissive: em }));
      m.position.set(x, y, z); scene.add(m); return m;
    }
    function WX(x) { return x - AW / 2; }     // arena -> world (2D +y is south, so it maps straight to +z)
    function WZ(y) { return y - AH / 2; }

    try {
      ren = sharedRenderer(T); cv = ren.domElement;
      allyWas = allyPool(false);                            // free the hub's model-viewer ally contexts for the match
      scene = new T.Scene();
      if (T.Fog) scene.fog = new T.Fog(0x0a0810, 140, 700);
      cam = new T.PerspectiveCamera(72, 1, 1, 1600);
      cam.rotation.order = 'YXZ';

      // lights: deliberately generous so BOTH the legacy and the physical
      // intensity regimes land somewhere visible, and every material carries an
      // emissive floor so a bad regime can never render the bunker pitch black.
      var amb = new T.AmbientLight(0xffffff, 1.0); scene.add(amb);
      var key = new T.DirectionalLight(0xffe0a0, 1.8); key.position.set(0.4, 1, 0.25); scene.add(key);

      // floor + ceiling: the same slab the 2D path fills with #12100c
      var fl = new T.Mesh(geo('PlaneGeometry', AW, AH), mat('MeshLambertMaterial', { color: 0x12100c, emissive: 0x0a0906 }));
      fl.rotation.x = -PI / 2; scene.add(fl);
      var ce = new T.Mesh(geo('PlaneGeometry', AW, AH), mat('MeshLambertMaterial', { color: 0x08070a, emissive: 0x050408 }));
      ce.rotation.x = PI / 2; ce.position.y = WALL_H; scene.add(ce);

      /* AK-GULAGMAP 2026-07-28 (operator: "i added gulag_3d.glb which should be the map for the
       * gulag battle"). Load the real gulag environment GLB and drop it INSIDE the procedural
       * bunker. Same discipline as AK-GULAGHERO / AK-BLDMODELS: async load, bbox-normalise to the
       * arena footprint, seat feet on the floor, force DoubleSide so interior walls render from
       * inside (the townhall see-through lesson), and force an emissive floor so a dark export is
       * never pitch-black. The procedural floor + walls stay as an INSTANT-ON fallback and a
       * collision-truth stand-in -- gulag collision reads the 2D `cover` array + arena bounds, never
       * this mesh, so the map is purely visual and cannot wall the player in. Lifted ~1u off y=0 so
       * the map's own floor never z-fights the procedural plane it sits on. */
      try {
        if (T && typeof (global.AK_THREE && global.AK_THREE.loadGLB) === 'function') {
          global.AK_THREE.loadGLB('assets/models/gulag_3d.glb', function (glb) {
            try {
              var mo = glb && (glb.scene || glb); if (!mo || !scene) return;
              var mbb = new T.Box3().setFromObject(mo), msz = mbb.getSize(new T.Vector3());
              // fit the map's horizontal footprint to the arena's larger dimension so the walls
              // land roughly where the extruded perimeter boxes are.
              var span = Math.max(msz.x || 1, msz.z || 1, 1e-6);
              var ms = (Math.max(AW, AH) * 1.02) / span; mo.scale.setScalar(ms);
              var mbb2 = new T.Box3().setFromObject(mo);
              mo.position.set(0, -mbb2.min.y + 1, 0);   // centred, feet on floor, +1u to kill z-fight
              mo.traverse(function (o) {
                if (!o.isMesh || !o.material) return;
                var arr = Array.isArray(o.material) ? o.material : [o.material];
                for (var mi = 0; mi < arr.length; mi++) {
                  var m = arr[mi]; if (!m) continue;
                  try {
                    if ('side' in m) m.side = T.DoubleSide;                 // see interior walls from inside
                    if ('emissive' in m && m.emissive && m.map && 'emissiveMap' in m) {
                      m.emissive.setHex(0x555555); m.emissiveMap = m.map;    // never pitch-black
                      if ('emissiveIntensity' in m) m.emissiveIntensity = 0.28;
                    }
                    m.needsUpdate = true;
                  } catch (_em) {}
                }
              });
              scene.add(mo);
              // map landed: recede the procedural floor/ceiling so the real environment reads,
              // but keep them (a GLB with an open top still needs the dark ceiling behind fog).
              try { if (fl.material) fl.material.emissive && fl.material.emissive.setHex(0x000000); } catch (_ef) {}
            } catch (_emap) {}
          }, function () {});
        }
      } catch (_egm) {}

      // COVER: read straight off the existing `cover` array, built once (it is static)
      for (var i = 0; i < cover.length; i++) {
        var c = cover[i];
        box(c.w, COVER_H, c.h, 0x33302a, 0x14130f, WX(c.x + c.w / 2), COVER_H / 2, WZ(c.y + c.h / 2));
      }
      // perimeter walls (the gold-edged arena rect of the 2D path, extruded)
      box(AW + 24, WALL_H, 12, 0x1a1814, 0x0c0b09, 0, WALL_H / 2, WZ(0) - 6);
      box(AW + 24, WALL_H, 12, 0x1a1814, 0x0c0b09, 0, WALL_H / 2, WZ(AH) + 6);
      box(12, WALL_H, AH + 24, 0x1a1814, 0x0c0b09, WX(0) - 6, WALL_H / 2, 0);
      box(12, WALL_H, AH + 24, 0x1a1814, 0x0c0b09, WX(AW) + 6, WALL_H / 2, 0);

      // the rival, drawn at whatever position the LOGIC already put him at
      rvGrp = new T.Group();
      var body = new T.Mesh(geo('BoxGeometry', 20, 24, 13), mat('MeshLambertMaterial', { color: 0xb8434c, emissive: 0x3a1418 }));
      body.position.y = 12; rvGrp.add(body);
      var head = new T.Mesh(geo('BoxGeometry', 12, 11, 14), mat('MeshLambertMaterial', { color: 0xd06a6a, emissive: 0x401a1a }));
      head.position.set(0, 29, -3); rvGrp.add(head);
      scene.add(rvGrp);
      rvFlash = new T.Mesh(geo('PlaneGeometry', 16, 16), mat('MeshBasicMaterial', { color: 0xffcf7a, transparent: true, opacity: 0 }));
      rvFlash.position.set(0, 22, -10); rvGrp.add(rvFlash);

      /* AK-GULAGHERO 2026-07-28 (operator: "i need to see my hero and the opponents hero... see
       * bacardi or balboa or whoever"). The rival was a generic red box. Load the OPPONENT's HERO
       * GLB and stand it where the box was, so the enemy is a real dog-gang hero. The box body +
       * head stay as an instant-on fallback and are hidden the moment the GLB lands (GLBs load
       * async; a box-shaped enemy for 300ms beats an invisible one). bbox-normalised to ~30 units
       * (matches the box: body 24 tall + head at 29) and seated on the floor, exactly like the hub
       * hero. The opponent's hero is chosen deterministically DIFFERENT from the player's so a 1v1
       * never mirrors the same dog. */
      try {
        var _roster = ['bcardd', 'balboa', 'jagged', 'rottweiler', 'bulldog', 'malamute'];  // AK-3DALL: full 6-hero pool
        var _mine = (global.AK_HERO || 'bcardd').toString().toLowerCase();
        var _opps = _roster.filter(function (h) { return _mine.indexOf(h) === -1; });
        var _oppSlug = _opps[Math.floor(Math.random() * _opps.length)] || 'jagged';   // random rival from the 5 others
        var _oppUrl = 'assets/models/' + _oppSlug + '.glb';
        if (T && typeof (global.AK_THREE && global.AK_THREE.loadGLB) === 'function') {
          global.AK_THREE.loadGLB(_oppUrl, function (glb) {
            try {
              var o = glb && (glb.scene || glb); if (!o || !rvGrp) return;
              var bb = new T.Box3().setFromObject(o), sz = bb.getSize(new T.Vector3());
              var s2 = 30 / Math.max(sz.y || 1, 1e-6); o.scale.setScalar(s2);
              o.userData._base = s2;   // base scale for the hit-pulse to multiply
              var bb2 = new T.Box3().setFromObject(o); o.position.y = -bb2.min.y;   // feet on floor
              // face the same way the group faces (group already rotates to face the player)
              rvGrp.add(o); rvGrp.userData.hero = o;
              /* AK-GULAGFACE 2026-07-28 (operator: "his back is towards me"). Tripo GLBs face +Z; the
               * group aims its -Z front (where the placeholder box head sat) at the player, so the raw
               * mesh showed its back. Flip the mesh 180 so its front matches the group -> he FACES you. */
              o.rotation.y = PI;
              /* AK-GULAGWALK 2026-07-28 (operator: "stonejaw isn't using his walking animation"). The
               * opponent was a FROZEN static mesh (no mixer anywhere). Drive his real WALK clip -- same
               * measured leg-dominant index the hub uses, so he strides instead of standing. */
              try {
                var _anims = glb && glb.animations;
                if (_anims && _anims.length && T.AnimationMixer) {
                  var _WALK = { bcardd: 10, balboa: 4, jagged: 1, rottweiler: 9, bulldog: 3, malamute: 7 };
                  var _wi = _WALK[_oppSlug]; if (typeof _wi !== 'number' || _wi >= _anims.length) _wi = 0;
                  rvMixer = new T.AnimationMixer(o);
                  rvMixer.clipAction(_anims[_wi]).play();
                }
              } catch (_ewm) {}
              // hide the placeholder box body + head now that the real hero is in
              if (rvGrp.children[0]) rvGrp.children[0].visible = false;
              if (rvGrp.children[1]) rvGrp.children[1].visible = false;
            } catch (_eh) {}
          }, function () {});
        }
      } catch (_eo) {}

      // WEAPON in VIEW SPACE: parented to the camera so it never needs a per-frame transform
      gun = new T.Group();
      var stock = new T.Mesh(geo('BoxGeometry', 3.2, 3.0, 15), mat('MeshLambertMaterial', { color: 0x22201c, emissive: 0x101010 }));
      stock.position.set(0, 0, -3); gun.add(stock);
      var barrel = new T.Mesh(geo('BoxGeometry', 1.5, 1.5, 11), mat('MeshLambertMaterial', { color: 0x3a352c, emissive: 0x1a1814 }));
      barrel.position.set(0, 0.6, -14); gun.add(barrel);
      var grip = new T.Mesh(geo('BoxGeometry', 2.4, 5.2, 3.0), mat('MeshLambertMaterial', { color: 0xcaa84c, emissive: 0x4a3a12 }));
      grip.position.set(0, -3.4, 1.5); gun.add(grip);
      flash = new T.Mesh(geo('PlaneGeometry', 9, 9), mat('MeshBasicMaterial', { color: 0xffe9a8, transparent: true, opacity: 0 }));
      flash.position.set(0, 0.6, -20); gun.add(flash);
      if (T.PointLight) { flashLight = new T.PointLight(0xffd27a, 0, 150); flashLight.position.set(0, 2, -20); gun.add(flashLight); }
      gun.position.set(6.5, -5.6, -12); gun.rotation.y = 0.06;
      cam.add(gun); scene.add(cam);
    } catch (_e3) { if (allyWas !== null) allyPool(allyWas); return null; }   // singleton renderer is NOT disposed, only released

    function bulletMesh(i) {
      while (pool.length <= i) {
        var m = new T.Mesh(geo('BoxGeometry', 3.4, 3.4, 3.4), mat('MeshBasicMaterial', { color: 0xffe08a }));
        m.visible = false; scene.add(m); pool.push(m);
      }
      return pool[i];
    }
    function fwd() { return { x: -Math.sin(yaw), y: -Math.cos(yaw) }; }   // yaw 0 looks -Z == arena north

    var A = {};
    A.active = function () { return !dead; };
    A.yaw = function () { return yaw; };

    /* LOOK + STICK. Runs BEFORE step() and writes only the fields the 2D path
     * already wrote, so step() cannot tell which renderer is driving it.       */
    A.preStep = function (dt, you, inp) {
      if (rvMixer) { try { rvMixer.update(dt); } catch (_emu) {} }   // AK-GULAGWALK: advance the opponent's walk animation every frame
      recoil = Math.max(0, recoil - dt * 7.5);
      flashT = Math.max(0, flashT - dt); rvFlashT = Math.max(0, rvFlashT - dt);
      shake = Math.max(0, shake - dt * 26); mark = Math.max(0, mark - dt);
      var f = fwd(), r = { x: -f.y, y: f.x };                 // screen-right of the look vector
      inp.mvx = f.x * -stick.y + r.x * stick.x;               // stick pushed up (-y) == walk forward
      inp.mvy = f.y * -stick.y + r.y * stick.x;
      inp.ax = you.x + f.x * 400; inp.ay = you.y + f.y * 400; // far aim point; step()'s 90u snap IS the aim assist
    };

    /* POINTER. Left half = the SAME virtual stick (raw vector kept so holding
     * forward through a turn curves the run); right half = look-drag + fire.   */
    A.pointer = function (evt, inp, vp) {
      var x = evt.clientX, y = evt.clientY, t = evt.type;
      if (t === 'pointerdown') {
        if (x < vp.w * 0.5) { inp.mvId = evt.pointerId; inp.mox = x; inp.moy = y; stick.x = 0; stick.y = 0; inp.mvx = 0; inp.mvy = 0; }
        else { inp.aimId = evt.pointerId; lx = x; ly = y; inp.firing = true; }
      } else if (t === 'pointermove') {
        if (evt.pointerId === inp.mvId) {
          var dx = x - inp.mox, dy = y - inp.moy, m = hyp(dx, dy), cl = Math.min(m, 48) / 48, u = m || 1;
          stick.x = dx / u * cl; stick.y = dy / u * cl;
        } else if (evt.pointerId === inp.aimId) {
          yaw -= (x - lx) * LOOK_SENS;                        // drag right == turn right
          pitch = clamp(pitch - (y - ly) * LOOK_SENS * 0.8, -PITCH_MAX, PITCH_MAX);
          lx = x; ly = y;
        }
      } else {
        if (evt.pointerId === inp.mvId) { inp.mvId = null; stick.x = 0; stick.y = 0; inp.mvx = 0; inp.mvy = 0; }
        if (evt.pointerId === inp.aimId) { inp.aimId = null; inp.firing = false; }
      }
    };

    /* DRAW. Returns false on any failure so the caller runs the 2D body in the
     * SAME frame -- a lost WebGL context downgrades instead of blanking.        */
    A.draw = function (g, vp, st) {
      if (dead) return false;
      var you = st.you, rv = st.rv, bullets = st.bullets;
      try {
        if (st.S && st.S.over) { recoil = 0; flashT = 0; rvFlashT = 0; shake = 0; mark = 0; }   // preStep stops on the win frame; settle the view
        if (vp.w !== lastW || vp.h !== lastH) {
          lastW = vp.w; lastH = vp.h;
          cam.aspect = vp.w / Math.max(1, vp.h); cam.updateProjectionMatrix();
          ren.setSize(vp.w, vp.h, false);
        }
        // ---- read the logic layer's edges for feel (never write to it) ----
        if (lastYouHp >= 0 && you.hp < lastYouHp) { var row = juiceImpact(lastYouHp - you.hp); shake = Math.max(shake, row ? row.shake + 3 : 5); }
        if (lastRvHp >= 0 && rv.hp < lastRvHp) { juiceImpact(lastRvHp - rv.hp); mark = 0.18; }
        if (you.fireT > lastFireT + 1e-6) { recoil = 1; flashT = 0.055; }        // fire() just reloaded the timer
        if (rv.fireT > lastRvFireT + 1e-6) { rvFlashT = 0.055; }
        lastYouHp = you.hp; lastRvHp = rv.hp; lastFireT = you.fireT; lastRvFireT = rv.fireT;

        // ---- camera at eye height, on the position the LOGIC owns ----
        var jx = shake ? rand(-shake, shake) * 0.5 : 0, jy = shake ? rand(-shake, shake) * 0.5 : 0;
        cam.position.set(WX(you.x) + jx, EYE + jy, WZ(you.y));
        cam.rotation.y = yaw; cam.rotation.x = pitch + recoil * 0.05;
        gun.position.z = -12 + recoil * 2.6; gun.position.y = -5.6 - recoil * 0.5; gun.rotation.x = recoil * 0.32;
        flash.material.opacity = flashT > 0 ? 0.95 : 0;
        flash.rotation.z = flashT > 0 ? rand(0, PI) : 0;
        if (flashLight) flashLight.intensity = flashT > 0 ? 4 : 0;

        rvGrp.visible = !rv.dead;
        if (!rv.dead) {
          rvGrp.position.set(WX(rv.x), 0, WZ(rv.y));
          rvGrp.rotation.y = Math.atan2(WX(you.x) - WX(rv.x), WZ(you.y) - WZ(rv.y)) + PI;   // face the player
          rvFlash.material.opacity = rvFlashT > 0 ? 0.9 : 0;
          var _rvh = rvGrp.userData && rvGrp.userData.hero;
          if (_rvh) _rvh.scale.setScalar((_rvh.userData._base || 1) * (rv.hitFx > 0 ? 1.12 : 1));
          else rvGrp.children[0].scale.setScalar(rv.hitFx > 0 ? 1.12 : 1);
        }

        // ---- BULLETS: render the array the logic already stepped ----
        for (var b = 0; b < bullets.length; b++) {
          var bu = bullets[b], m = bulletMesh(b);
          m.visible = true; m.position.set(WX(bu.x), EYE - 4, WZ(bu.y));
          m.material.color.setHex(bu.team === 0 ? 0xffe08a : 0xff8a6b);
        }
        for (var p = bullets.length; p < pool.length; p++) pool[p].visible = false;

        ren.render(scene, cam);
        g.drawImage(cv, 0, 0, vp.w, vp.h);
      } catch (_e5) { dead = true; return false; }

      // ---- 2D reticle + hitmarker over the blit; drawHUD still paints after ----
      var cx = vp.w / 2, cy = vp.h / 2, sp = 6 + recoil * 14;
      g.save(); g.strokeStyle = 'rgba(232,197,90,.85)'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(cx - sp - 7, cy); g.lineTo(cx - sp, cy); g.moveTo(cx + sp, cy); g.lineTo(cx + sp + 7, cy);
      g.moveTo(cx, cy - sp - 7); g.lineTo(cx, cy - sp); g.moveTo(cx, cy + sp); g.lineTo(cx, cy + sp + 7); g.stroke();
      if (mark > 0) {
        g.globalAlpha = clamp(mark / 0.18, 0, 1); g.strokeStyle = '#fff'; g.lineWidth = 2.5;
        g.beginPath(); g.moveTo(cx - 11, cy - 11); g.lineTo(cx - 5, cy - 5); g.moveTo(cx + 11, cy - 11); g.lineTo(cx + 5, cy - 5);
        g.moveTo(cx - 11, cy + 11); g.lineTo(cx - 5, cy + 5); g.moveTo(cx + 11, cy + 11); g.lineTo(cx + 5, cy + 5); g.stroke();
      }
      g.restore();
      return true;
    };

    // Per-match teardown. The SHARED renderer survives on purpose (see sharedRenderer);
    // disposing the singleton would blind the next 3D lane and churn a phone context.
    A.dispose = function () {
      dead = true;
      try { for (var i = 0; i < junk.length; i++) if (junk[i] && junk[i].dispose) junk[i].dispose(); } catch (_e6) {}
      try { if (scene && scene.clear) scene.clear(); } catch (_e7) {}
      if (allyWas !== null) allyPool(allyWas);              // hand the hub its model-viewer pool back
      junk = []; pool = []; scene = null; rvMixer = null;   // AK-GULAGWALK: drop the opponent mixer
    };
    A.setHands = function (h) { try { if (gun) gun.visible = !h; } catch (_e) {} };   // AK-GULAGFIST: hide the first-person gun in HANDS mode
    return A;
  }

  /* ===================================================================== */
  /* GULAG  (mode 'gulag') -- CoD-Mobile 1v1 jump-out shooter, tight camera.  */
  /* ===================================================================== */
  function openGulag(ctx, opts) {
    if (!ctx || !ctx.overlay) return null;
    opts = opts || {};
    var roster = getRoster(ctx);
    var youName   = opts.heroName || playerHeroName(ctx, roster);
    var rivalName = opts.rival || pickEnemyHero(roster, youName);

    var AW = 560, AH = 760;                  // tight arena (gulag bunker)
    var cover = [
      { x: AW / 2 - 130, y: AH / 2 - 110, w: 70, h: 26 },
      { x: AW / 2 + 60,  y: AH / 2 - 110, w: 70, h: 26 },
      { x: AW / 2 - 18,  y: AH / 2 - 14,  w: 36, h: 90 },
      { x: AW / 2 - 130, y: AH / 2 + 86,  w: 70, h: 26 },
      { x: AW / 2 + 60,  y: AH / 2 + 86,  w: 70, h: 26 }
    ];
    var fighters = {}, bullets = [], S = { t: 0, over: false, win: false, hands: false, meleeT: 0, hudBtns: [] };   // AK-GULAGFIST: hands=melee mode, gun=shooter
    var inp = { mvId: null, mox: 0, moy: 0, mvx: 0, mvy: 0, aimId: null, ax: 0, ay: 0, firing: false };
    var vp = null, api = null;
    var TF = { sc: 1, ox: 0, oy: 0 };        // arena<->screen transform (set in draw)
    // AK-GULAGFPS 2026-07-18: three_boot loads ASYNC and ok() is false until it lands, so the
    // first-person view ATTACHES LATE rather than never. The match opens on the 2D renderer and
    // upgrades itself the moment three is up. If it never lands, 2D just keeps running: FPS stays
    // null, every call site below is guarded, and the mode is byte-identical to today.
    var FPS = null, fpsAt = 0, fpsOff = false;
    warmThree();
    function fpsTry(t) {
      if (FPS || fpsOff) return;
      if (t < fpsAt) return;
      fpsAt = t + 0.3;
      FPS = gulagFPS(AW, AH, cover);
      if (!FPS && t > 10) fpsOff = true;     // vendor file is not coming; stop probing, stay 2D
    }

    function mkF(name, team, x, y) {
      var s = statline(roster[name] || EMBED[name] || {});
      var f = {
        name: name, team: team, x: x, y: y, r: 16, rarity: s.rarity,
        maxHp: clamp(Math.round(s.rawHp / 9), 90, 360), hp: 0,
        dmg: clamp(Math.round(s.rawDmg / 6), 12, 70),
        fireInt: clamp(s.atkInterval * 0.55, 0.28, 0.95),
        bSpd: 320 + s.rangeTiles * 26, spd: s.moveBase * 1.15,
        fireT: 0, hitFx: 0, dead: false, strafe: 1, think: 0, _sx: 0, _sy: 0
      };
      f.hp = f.maxHp;
      return f;
    }
    fighters.you = mkF(youName, 0, AW / 2, AH - 90);     // SYNCHRONOUS init (frame-1-safe)
    fighters.rv  = mkF(rivalName, 1, AW / 2, 90);

    function blocked(x, y) { for (var i = 0; i < cover.length; i++) { var c = cover[i]; if (x > c.x && x < c.x + c.w && y > c.y && y < c.y + c.h) return true; } return false; }
    function fire(f, tx, ty) {
      if (f.fireT > 0) return; f.fireT = f.fireInt;
      var dx = tx - f.x, dy = ty - f.y, m = hyp(dx, dy) || 1;
      bullets.push({ x: f.x + dx / m * (f.r + 4), y: f.y + dy / m * (f.r + 4), vx: dx / m * f.bSpd, vy: dy / m * f.bSpd, dmg: f.dmg, team: f.team, life: 1.6 });
    }
    /* AK-GULAGFIST 2026-07-28 (operator: "the fight buttons need to be available during gulag... swap
     * between guns or hands"). HANDS mode: a fight button throws a real melee that lands only IN REACH,
     * with a small close-the-gap step (a dash ONLY on a melee, not on movement). Heavier hits reach
     * further + hurt more but recover slower. Damage feeds the same win check as the gun. */
    function melee(kind) {
      var you = fighters.you, rv = fighters.rv;
      if (!you || !rv || you.dead || rv.dead || S.over || S.meleeT > 0) return;
      S.meleeT = kind === 'kick' ? 0.5 : (kind === 'hook' ? 0.42 : 0.3);
      var dx = rv.x - you.x, dy = rv.y - you.y, d = hyp(dx, dy) || 1;
      var reach = kind === 'kick' ? 100 : (kind === 'hook' ? 82 : 68);
      var step2 = Math.min(Math.max(0, d - you.r - rv.r - 6), kind === 'kick' ? 30 : 20);   // dash INTO range, melee only
      if (step2 > 0) { var nx = you.x + dx / d * step2, ny = you.y + dy / d * step2; if (!blocked(nx, you.y)) you.x = nx; if (!blocked(you.x, ny)) you.y = ny; }
      if (hyp(rv.x - you.x, rv.y - you.y) < reach) {
        rv.hp -= (kind === 'kick' ? 46 : (kind === 'hook' ? 34 : 22)); rv.hitFx = 0.18;
        try { if (typeof boxHeroHit === 'function') boxHeroHit(); } catch (_e) {}
        try { if (global.AK_SFX && AK_SFX.play) AK_SFX.play(kind === 'kick' ? 'crit' : 'hit'); } catch (_e2) {}
        if (rv.hp <= 0 && !S.over) { rv.dead = true; S.over = true; S.win = true; finish(); }
      }
    }
    function moveF(f, vx, vy, dt) {
      var nx = clamp(f.x + vx * f.spd * dt, 20, AW - 20), ny = clamp(f.y + vy * f.spd * dt, 20, AH - 20);
      if (!blocked(nx, f.y)) f.x = nx;
      if (!blocked(f.x, ny)) f.y = ny;
    }
    function nearestCover(f) { var best = null, bd = 1e9; for (var i = 0; i < cover.length; i++) { var c = cover[i], cx = c.x + c.w / 2, cy = c.y + c.h / 2, d = hyp(cx - f.x, cy - f.y); if (d < bd) { bd = d; best = { x: cx, y: cy }; } } return best; }
    function lineBlocked(a, b) { var steps = 10; for (var i = 1; i < steps; i++) { var t = i / steps; if (blocked(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)) return true; } return false; }

    function aiThink(f, foe, dt) {
      f.think -= dt; f.fireT -= dt;
      if (f.think <= 0) { f.think = rand(0.5, 1.2); f.strafe = Math.random() < 0.5 ? -1 : 1; }
      var dx = foe.x - f.x, dy = foe.y - f.y, d = hyp(dx, dy) || 1;
      var want = 230;                                      // keep mid range
      var rad = d > want ? 1 : (d < want - 70 ? -1 : 0);   // approach / back off
      var perp = { x: -dy / d, y: dx / d };
      var mvx = (dx / d) * rad + perp.x * f.strafe * 0.8;
      var mvy = (dy / d) * rad + perp.y * f.strafe * 0.8;
      var lowHp = f.hp < f.maxHp * 0.35;                   // duck behind cover when hurt
      if (lowHp) { var c = nearestCover(f); if (c) { mvx = c.x - f.x; mvy = c.y - f.y; var mm = hyp(mvx, mvy) || 1; mvx /= mm; mvy /= mm; } }
      moveF(f, mvx, mvy, dt);
      if (!lineBlocked(f, foe)) fire(f, foe.x, foe.y);     // only shoot with line-of-sight
    }

    function step(dt) {
      S.t += dt;
      if (S.meleeT > 0) S.meleeT -= dt;                    // AK-GULAGFIST: melee recovery
      var you = fighters.you, rv = fighters.rv;
      you.fireT -= dt; if (you.hitFx > 0) you.hitFx -= dt; if (rv.hitFx > 0) rv.hitFx -= dt;
      moveF(you, inp.mvx, inp.mvy, dt);
      if (inp.firing && !you.dead && !S.hands) {           // AK-GULAGFIST: no shooting in HANDS mode. aim in ARENA coords (inp.ax/ay), light snap to rival
        var tx = inp.ax, ty = inp.ay;
        if (hyp(rv.x - tx, rv.y - ty) < 90) { tx = rv.x; ty = rv.y; }
        fire(you, tx, ty);
      }
      if (!rv.dead) aiThink(rv, you, dt);
      for (var i = bullets.length - 1; i >= 0; i--) {
        var b = bullets[i]; b.x += b.vx * dt; b.y += b.vy * dt; b.life -= dt;
        if (b.life <= 0 || b.x < 0 || b.x > AW || b.y < 0 || b.y > AH || blocked(b.x, b.y)) { bullets.splice(i, 1); continue; }
        var tgt = b.team === 0 ? rv : you;
        if (!tgt.dead && hyp(b.x - tgt.x, b.y - tgt.y) < tgt.r) {
          tgt.hp -= b.dmg; tgt.hitFx = 0.12; bullets.splice(i, 1);
          if (b.team === 0) boxHeroHit();                 /* AK-FIX-lane-D:modes.js 2026-07-28: box the hero on a landed player hit */
          if (tgt.hp <= 0 && !S.over) { tgt.dead = true; S.over = true; S.win = (tgt === rv); finish(); }
        }
      }
    }
    // TODO-RESEARCH: 2v2, weapon loadouts, grenades, killcam, ranked redemption ladder.

    function finish() {
      grantReward(ctx, S.win, 'gulag');
      var hpPct = Math.round(fighters.you.hp / fighters.you.maxHp * 100);
      recordResult(ctx, 'gulag', S.win, S.win ? Math.max(1, hpPct) : 0);
      // TODO-SERVER: server-authoritative 1v1 result (ride ak_grants).
      setTimeout(function () { if (api) api.close({ win: S.win }); }, 1400);
    }

    function aimToArena(px, py) { return { x: (px - TF.ox) / TF.sc, y: (py - TF.oy) / TF.sc }; }

    function draw(g, _vp) {
      vp = _vp;
      // AK-GULAGFPS 2026-07-18: first-person blit, then the SAME 2D HUD on top. A
      // false return (no boot lane / WebGL died) drops straight into the 2D body.
      if (FPS && FPS.active() && FPS.draw(g, vp, { you: fighters.you, rv: fighters.rv, bullets: bullets, S: S })) { drawHUD(g); return; }
      var sc = Math.min(vp.w / AW, vp.h / AH) * 0.98;      // tight camera, zoom to fit (gritty close framing)
      var ox = (vp.w - AW * sc) / 2, oy = (vp.h - AH * sc) / 2;
      TF.sc = sc; TF.ox = ox; TF.oy = oy;
      function X(x) { return ox + x * sc; } function Y(y) { return oy + y * sc; }
      g.fillStyle = '#070608'; g.fillRect(0, 0, vp.w, vp.h);
      g.save(); g.fillStyle = '#12100c'; g.fillRect(X(0), Y(0), AW * sc, AH * sc);
      g.strokeStyle = 'rgba(201,168,76,.35)'; g.lineWidth = 2; g.strokeRect(X(0), Y(0), AW * sc, AH * sc); g.restore();
      for (var i = 0; i < cover.length; i++) { var c = cover[i]; g.save(); g.fillStyle = '#33302a'; g.strokeStyle = 'rgba(201,168,76,.4)'; g.lineWidth = 1.5; g.fillRect(X(c.x), Y(c.y), c.w * sc, c.h * sc); g.strokeRect(X(c.x), Y(c.y), c.w * sc, c.h * sc); g.restore(); }
      for (var b = 0; b < bullets.length; b++) { var bu = bullets[b]; g.fillStyle = bu.team === 0 ? '#ffe08a' : '#ff8a6b'; g.beginPath(); g.arc(X(bu.x), Y(bu.y), 3 * sc, 0, 2 * PI); g.fill(); }
      ['you', 'rv'].forEach(function (k) { var f = fighters[k]; if (!f || f.dead) return; var fill = f.team === 0 ? '#caa84c' : '#b8434c';
        f._sx = X(f.x); f._sy = Y(f.y);
        dogChip(g, X(f.x), Y(f.y), (f.r + (f.hitFx > 0 ? 2 : 0)) * sc, fill, k === 'you' ? '#fff' : rarColor(f.rarity), chipLetter(f.name), f.name);
        bar(g, X(f.x) - f.r * sc, Y(f.y) - (f.r + 9) * sc, f.r * 2 * sc, 4, f.hp / f.maxHp, f.team === 0 ? '#6be08a' : '#ff6b6b'); });
      drawHUD(g);
    }
    function drawHUD(g) {
      g.save(); g.fillStyle = 'rgba(6,6,12,.82)'; g.fillRect(0, 0, vp.w, 36);
      g.fillStyle = '#ff8a6b'; g.font = '900 13px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText('THE GULAG · 1v1 · win your way back', vp.w / 2, 18);
      // AK-GULAGHERO 2026-07-28: name the hero the player is fighting AS, so they SEE who they are
      // even in first person. Roster label from the same AK_HERO the model system reads.
      try {
        // AK-GULAGLABEL6 2026-07-28: resolve all SIX playable heroes; the old 3-way check mislabelled
        // rottweiler/bulldog/malamute as $BCARDD once the AK-3DALL roster shipped.
        var _hs = String(global.AK_HERO || 'bcardd').toLowerCase();
        var _hl = _hs.indexOf('balboa') >= 0 ? 'BALBOA'
                : _hs.indexOf('jagged') >= 0 ? 'JAGGED'
                : _hs.indexOf('rott') >= 0 ? 'IRON ROTT'
                : _hs.indexOf('bulldog') >= 0 ? 'GRIT BULL'
                : _hs.indexOf('malamute') >= 0 ? 'BLACKOUT'
                : '$BCARDD';
        g.font = '800 10px Inter, system-ui'; g.fillStyle = '#e8c55a'; g.textAlign = 'left';
        g.fillText('YOU: ' + _hl, 12, 34);
      } catch (_eh) {}
      g.restore();
      var you = fighters.you, rv = fighters.rv;
      bar(g, 14, vp.h - 26, 150, 12, you.hp / you.maxHp, '#6be08a');
      g.fillStyle = '#cfe'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText(you.name, 14, vp.h - 38);
      bar(g, vp.w - 164, 44, 150, 10, rv.hp / rv.maxHp, '#ff6b6b');
      g.fillStyle = '#f9b'; g.textAlign = 'right'; g.fillText(rv.name, vp.w - 14, 56);
      if (!S.hands) {   // AIM+FIRE prompt belongs to GUN mode only
        g.save(); g.globalAlpha = .5; g.strokeStyle = '#e8c55a'; g.lineWidth = 1.5; g.beginPath(); g.arc(vp.w - 60, vp.h - 70, 40, 0, 2 * PI); g.stroke();
        g.fillStyle = '#e8c55a'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'center'; g.fillText('AIM+FIRE', vp.w - 60, vp.h - 70); g.restore();
      }
      /* AK-GULAGFIST 2026-07-28: the GUN/HANDS swap + the fight buttons. Rects are stashed on S.hudBtns
       * so pointer() can claim the tap before the look-drag. Fight buttons only render in HANDS mode. */
      S.hudBtns = [];
      var tw = 86, th = 28, bx = vp.w - tw - 12, by = 64;
      g.save();
      g.fillStyle = S.hands ? 'rgba(255,120,90,.92)' : 'rgba(127,233,255,.88)';
      g.strokeStyle = '#e8c55a'; g.lineWidth = 1.5; g.fillRect(bx, by, tw, th); g.strokeRect(bx, by, tw, th);
      g.fillStyle = '#0a0a0c'; g.font = '900 12px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(S.hands ? 'HANDS' : 'GUN', bx + tw / 2, by + th / 2);
      g.restore();
      S.hudBtns.push({ id: 'swap', x: bx, y: by, w: tw, h: th });
      if (S.hands && !S.over) {
        var _fb = [{ id: 'jab', lab: 'JAB' }, { id: 'hook', lab: 'HOOK' }, { id: 'kick', lab: 'KICK' }];
        for (var _fi = 0; _fi < _fb.length; _fi++) {
          var cx = vp.w - 58, cy = vp.h - 160 - _fi * 66, rr = 27, rdy = S.meleeT <= 0;
          g.save(); g.globalAlpha = rdy ? 1 : 0.4;
          g.fillStyle = 'rgba(20,16,12,.9)'; g.strokeStyle = '#ff8a6b'; g.lineWidth = 2;
          g.beginPath(); g.arc(cx, cy, rr, 0, 2 * PI); g.fill(); g.stroke();
          g.fillStyle = '#ffd76b'; g.font = '900 11px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
          g.fillText(_fb[_fi].lab, cx, cy); g.restore();
          S.hudBtns.push({ id: _fb[_fi].id, x: cx - rr, y: cy - rr, w: rr * 2, h: rr * 2 });
        }
        g.save(); g.fillStyle = '#ff8a6b'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'right'; g.fillText('CLOSE IN + STRIKE', vp.w - 14, vp.h - 66); g.restore();
      }
      try { if (FPS && FPS.setHands) FPS.setHands(S.hands); } catch (_esh) {}   // keep the 3D gun hidden/shown with the mode
      if (S.over) centerBanner(g, vp, S.win ? "YOU'RE BACK IN -- GULAG WON" : 'DROPPED IN THE GULAG', S.win ? '#6be08a' : '#ff6b6b');
    }

    function pointer(evt) {
      if (!vp) return;                                     // ignore taps before the first frame lays out vp/transform
      var x = evt.clientX, y = evt.clientY, t = evt.type;
      if (t === 'pointerdown') {                            // AK-GULAGFIST: the GUN/HANDS swap + fight buttons win the tap before look-drag / move
        for (var _hb = 0; _hb < (S.hudBtns || []).length; _hb++) { var b0 = S.hudBtns[_hb];
          if (x >= b0.x && x <= b0.x + b0.w && y >= b0.y && y <= b0.y + b0.h) {
            if (b0.id === 'swap') { S.hands = !S.hands; try { if (FPS && FPS.setHands) FPS.setHands(S.hands); } catch (_e) {} try { if (global.AK_SFX && AK_SFX.play) AK_SFX.play('tap'); } catch (_e2) {} }
            else { melee(b0.id); }
            return;
          }
        }
      }
      if (FPS && FPS.active()) { FPS.pointer(evt, inp, vp); return; }   // AK-GULAGFPS 2026-07-18: look-drag instead of absolute aim
      if (t === 'pointerdown') {
        if (x < vp.w * 0.5) { inp.mvId = evt.pointerId; inp.mox = x; inp.moy = y; inp.mvx = 0; inp.mvy = 0; }
        else { inp.aimId = evt.pointerId; var a = aimToArena(x, y); inp.ax = a.x; inp.ay = a.y; inp.firing = true; }
      } else if (t === 'pointermove') {
        if (evt.pointerId === inp.mvId) { var dx = x - inp.mox, dy = y - inp.moy, m = hyp(dx, dy), cl = Math.min(m, 48) / 48, u = m || 1; inp.mvx = dx / u * cl; inp.mvy = dy / u * cl; }
        else if (evt.pointerId === inp.aimId) { var a2 = aimToArena(x, y); inp.ax = a2.x; inp.ay = a2.y; }
      } else {
        if (evt.pointerId === inp.mvId) { inp.mvId = null; inp.mvx = 0; inp.mvy = 0; }
        if (evt.pointerId === inp.aimId) { inp.aimId = null; inp.firing = false; }
      }
    }

    if (ctx.showBanner) ctx.showBanner('THE GULAG -- 1v1, winner walks', 1.4);
    api = ctx.overlay.open({
      id: 'mode_gulag',
      // AK-GULAGFPS 2026-07-18: preStep only rewrites inp.mvx/mvy/ax/ay (camera-relative stick + look ray)
      // BEFORE the untouched step() consumes them. Order and step() itself are unchanged in the 2D case.
      onFrame: function (g, dt, _vp) { if (!S.over) { fpsTry(S.t); if (FPS && FPS.active()) FPS.preStep(dt, fighters.you, inp); step(dt); } draw(g, _vp); },
      onPointer: function (evt) { pointer(evt); },
      onClose: function (res) { if (FPS) FPS.dispose(); if (ctx.showBanner && res) ctx.showBanner(res.win ? 'GULAG WON · back in the fight' : 'GULAG lost', 1.6); if (opts.onResult) try { opts.onResult(res); } catch (_e) {} }
    });
    return api;
  }

  /* ===================================================================== */
  /* ENCOUNTER ROUTER -- resolve a wild-dog encounter by the player's MOVE.   */
  /* (collide -> tower battle / swerve -> MOBA / jump-out -> Gulag / run)     */
  /* Called by the encounters + raid waves on proximity, or from THE STREET.  */
  /* ===================================================================== */
  function routeEncounter(opts) {
    opts = opts || {};
    var ctx = opts.ctx || global.AK_CTX;
    if (!ctx) return null;
    var roster = getRoster(ctx);
    var card = opts.card;
    var name = (card && card.name) || (typeof card === 'string' ? card : null);
    if (!name) { var names = cheapNames(roster); name = names[Math.floor(Math.random() * names.length)]; }
    var def = roster[name] || EMBED[name] || {};
    var nem = { card: def.cardNumber || null, name: name, tier: opts.tier || 2 };

    function dispatch(move) {
      if (move === 'collide') { ctx.battle.launch({ mode: 'encounter', nemesis: nem, label: 'ENCOUNTER · ' + name }); }
      else if (move === 'swerve') { openWorldMoba(ctx, { enemyHero: name, onResult: opts.onResult }); }
      else if (move === 'jumpout') { openGulag(ctx, { rival: name, onResult: opts.onResult }); }
      // 'run' / null -> nothing (symbol-encounter avoided)
    }
    if (opts.move) { dispatch(opts.move); return null; }   // programmatic routing (waves can skip the chooser)
    if (!ctx.overlay) { dispatch('collide'); return null; }

    var rar = def.rarity || 'Common', vp = null, BTN = {};
    function layout() {
      var cx = vp.w / 2, baseY = vp.h * 0.55, gap = 64;
      BTN.collide = { x: cx,      y: baseY,            r: 40, lab: 'COLLIDE',  sub: 'TOWER BATTLE', col: '#e8c55a' };
      BTN.swerve  = { x: cx - 96, y: baseY + gap,      r: 34, lab: 'SWERVE',   sub: 'MOBA DUEL',    col: '#7fc8ff' };
      BTN.jumpout = { x: cx + 96, y: baseY + gap,      r: 34, lab: 'JUMP OUT', sub: 'GULAG 1v1',    col: '#ff8a6b' };
      BTN.run     = { x: cx,      y: baseY + gap * 2 + 6, r: 24, lab: 'RUN',   sub: 'avoid',        col: '#9a8f6a' };
    }
    var api = ctx.overlay.open({
      id: 'mode_encounter_router',
      onFrame: function (g, dt, _vp) { vp = _vp; if (!BTN.collide) layout();
        g.fillStyle = 'rgba(6,6,12,.93)'; g.fillRect(0, 0, vp.w, vp.h);
        g.fillStyle = rarColor(rar); g.font = '700 12px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText('WILD ' + rar.toUpperCase() + ' STRAY', vp.w / 2, vp.h * 0.2);
        dogChip(g, vp.w / 2, vp.h * 0.32, 38, '#caa84c', rarColor(rar), chipLetter(name), name, def.cardNumber);
        g.fillStyle = '#e8c55a'; g.font = '900 20px Inter,sans-serif'; g.fillText(name, vp.w / 2, vp.h * 0.32 + 64);
        g.fillStyle = '#b9a76a'; g.font = '600 12px Inter,sans-serif'; g.fillText('It locked eyes. How do you play it?', vp.w / 2, vp.h * 0.45);
        for (var k in BTN) { var b = BTN[k];
          g.save(); g.beginPath(); g.arc(b.x, b.y, b.r, 0, 2 * PI); g.closePath(); g.fillStyle = 'rgba(20,18,12,.9)'; g.fill(); g.lineWidth = 2.5; g.strokeStyle = b.col; g.stroke();
          g.fillStyle = b.col; g.font = '900 12px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(b.lab, b.x, b.y - 4);
          g.fillStyle = '#cfc7b0'; g.font = '600 8px Inter,sans-serif'; g.fillText(b.sub, b.x, b.y + 11); g.restore(); }
      },
      onPointer: function (evt) { if (evt.type !== 'pointerdown' || !BTN.collide) return;
        for (var k in BTN) { var b = BTN[k]; if (hyp(evt.clientX - b.x, evt.clientY - b.y) <= b.r + 6) { api.close(k); return; } } },
      onClose: function (move) { dispatch(move || 'run'); }
    });
    return api;
  }

  /* ===================================================================== */
  /* ENGINE WIN-CONDITION MODES (window.AK_MODES) -- read by the engine.js    */
  /* seam (contract 6.C) on game.html. Use ONLY existing engine state; the    */
  /* battler loop is NEVER forked. These are registered UNCONDITIONALLY so    */
  /* they exist when game.html runs the engine (where initAll never fires).   */
  /* ===================================================================== */
  function kingTower(side) {
    var ts = (side && side.towers) || [];
    for (var i = 0; i < ts.length; i++) if (ts[i] && ts[i].type === 'king') return ts[i];
    return null;
  }
  function towersAlive(side) {
    var ts = (side && side.towers) || [], n = 0;
    for (var i = 0; i < ts.length; i++) if (ts[i] && !ts[i].destroyed && (ts[i].hp | 0) > 0) n++;
    return n;
  }

  global.AK_MODES = global.AK_MODES || {};

  // SURVIVAL -- outlast the clock with your King Tower alive (live AI curve is the waves).
  global.AK_MODES.survival = {
    setup: function (_game) {},
    checkEnd: function (game) {
      var k = kingTower(game && game.player);
      if (k && (k.destroyed || (k.hp | 0) <= 0)) return { result: 'lose', stars: 0 };
      if (num(game.time, 99) <= 0.06) return { result: 'win', stars: clamp(towersAlive(game && game.player), 1, 3) };
      return null;
    },
    hud: function (game) { return 'SURVIVE ' + Math.max(0, Math.ceil(num(game.time, 0))) + 's'; }
  };

  // ENCOUNTER -- a quick duel for the COLLIDE route: first crown wins.
  global.AK_MODES.encounter = {
    setup: function (_game) {},
    checkEnd: function (game) {
      if ((game.player.crowns | 0) >= 1) return { result: 'win', stars: 1 };
      var k = kingTower(game.player);
      if ((game.opponent.crowns | 0) >= 1 || (k && (k.destroyed || (k.hp | 0) <= 0))) return { result: 'lose', stars: 0 };
      return null;
    },
    hud: function (_game) { return 'FIRST CROWN WINS'; }
  };

  /* --------------------------------------------------------------------- *
   * RAID -- WALK-TO-RAID base-as-battlefield (the audit's #1 trust gap).
   * The hub's AK_RAIDSCENE.launch(target) hands a procedural enemy base over
   * via window.AK_RAID_TARGET + localStorage('ak_raid_target') (the frozen
   * ctx.battle.launch only forwards mode/city/level/nemesis). Here we SEED the
   * battlefield from target.layout: the scouted WALLS scale the enemy base's
   * perimeter towers and the CORE (Town Hall) becomes the enemy King tower, all
   * with the spec HP (wood200/stone500/metal1200 -> summed; coreHp -> king).
   *
   * Engine constraint (HARD): engine.js is frozen and exposes no Unit/Tower
   * factory, so a plug-in mode CANNOT spawn arbitrary entities -- it shapes the
   * three destructible base towers the engine already builds (2 perimeter walls
   * + 1 core) from the layout. The full per-wall layout is rendered faithfully
   * in the SCOUT scene (raidscene.js); the battle is "crack the base":
   *   win  = 50%+ of the base destroyed (CoC 1-star line)  -> stars scale to 3
   *   lose = your own King falls, or the clock runs out under 50%
   * Loot (gold/scrap/wood/stone/metal ONLY -- never gems/$BCARDD/ALK) is granted
   * the frame the raid is won, straight to the profile via AK_ECON.
   * --------------------------------------------------------------------- */
  function readRaidTarget() {
    if (global.AK_RAID_TARGET) return global.AK_RAID_TARGET;
    try { if (typeof localStorage !== 'undefined') { var s = localStorage.getItem('ak_raid_target'); if (s) return JSON.parse(s); } } catch (_e) {}
    return null;
  }
  function grantRaidLoot(reward) {
    reward = reward || {}; var E = global.AK_ECON; if (!E) return false;
    // AK-MAT: route wood/stone/metal through the SAME capped grant the harvest
    // faucet uses (excess past MAT_CAP auto-sells to gold) so raid loot can't
    // runaway-inflate materials. Inlined into one atomic write.
    var CAP = (E && E.MAT_CAP) || 2000, SELL = (E && E.MAT_SELL) || { wood: 2, stone: 3, metal: 5 };
    function bankMat(p, kind, amt) {
      amt = amt | 0; if (amt <= 0) return;
      var cur = Math.max(0, p[kind] | 0), room = Math.max(0, CAP - cur), add = Math.min(amt, room), over = amt - add;
      p[kind] = cur + add;
      if (over > 0) p.coins = Math.max(0, (p.coins | 0) + Math.round(over * (SELL[kind] || 1)));
    }
    try {
      if (reward.scrap && E.addScrap) E.addScrap(reward.scrapR || 'Rare', reward.scrap | 0);   // gems/$BCARDD/ALK NEVER granted
      if (E.mutateProfile) E.mutateProfile(function (p) {
        if (reward.gold)  p.coins = Math.max(0, (p.coins | 0) + (reward.gold | 0));
        bankMat(p, 'wood',  reward.wood);
        bankMat(p, 'stone', reward.stone);
        bankMat(p, 'metal', reward.metal);
      });
      return true;
    } catch (_e) { return false; }
  }
  // AK-RAID3STAR: proportional star-bonus loot. The scouted reward is the 1-star
  // (50%) baseline; pushing to 2/3 stars pays scaled extra. Cumulative payout:
  // 1 star = 1.0x, 2 stars = 1.5x, 3 stars = 2.5x of the base scout reward.
  function scaleReward(r, mult) {
    r = r || {};
    return {
      gold:  Math.round(num(r.gold,  0) * mult),
      scrap: Math.round(num(r.scrap, 0) * mult), scrapR: r.scrapR || 'Rare',
      wood:  Math.round(num(r.wood,  0) * mult),
      stone: Math.round(num(r.stone, 0) * mult),
      metal: Math.round(num(r.metal, 0) * mult)
    };
  }
  function sumWallHp(layout) {
    var s = 0; for (var i = 0; i < (layout || []).length; i++) { var o = layout[i]; if (o && o.type !== 'CORE') s += num(o.maxHp, 0); } return s;
  }

  /* ---- SERVER-AUTHORITATIVE raid settlement (ak-raid {action:'resolve'}) ----
   * On a raid WIN against a REAL server base (bot row OR a real player's published
   * snapshot), the SERVER computes + CAPS the loot (anti-cheat), queues it on the
   * shared ak_grants rail, and -- for a real-player base -- pushes a 24h revenge
   * row to that victim. The client then drains the grants via AKSocial.claimGrants.
   *
   * To keep loot EXACTLY-ONCE, the progressive client star tranches below are
   * SUPPRESSED whenever serverWillSettle(R) is true; settleRaidServer() then pays
   * once at the terminal win, star-scaled to mirror the tranche cumulative
   * (1*=1.0x / 2*=1.5x / 3*=2.5x). Signed-out / offline / a procedural fallback id
   * / a server error all degrade to the client grant -- never doubled.            */
  function akRaidClient() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_e) { return null; } }
  function akSignedIn() { try { return !!(global.AKAccount && global.AKAccount.user && global.AKAccount.user()); } catch (_e) { return false; } }
  // a server base id is a real uuid (a bot row, or a victim's user_id). The
  // offline/local procedural ids are all prefixed -> never resolvable server-side.
  function isServerBaseId(id) { return typeof id === 'string' && id.length >= 8 && !/^(bot_|rs_|wm_loc_|wc_)/.test(id); }
  // memoized per-raid: will the SERVER settle this loot? (decided at the first win-lock)
  function serverWillSettle(R) {
    if (!R) return false;
    if (R.serverSettle == null) {
      var t = R.target || {};
      R.serverSettle = !!(t.id && isServerBaseId(t.id) && akRaidClient() && akSignedIn());
    }
    return R.serverSettle;
  }
  function settleRaidServer(R, stars) {
    if (!R || R.settled) return; R.settled = true;
    if (!serverWillSettle(R)) return;                 // offline path: tranches already paid client-side
    var t = R.target || {}, sb = akRaidClient();
    var mult = stars >= 3 ? 2.5 : stars >= 2 ? 1.5 : 1.0;   // mirror the client tranche cumulative
    try {
      sb.functions.invoke('ak-raid', { body: { action: 'resolve', base_id: t.id, revenge: !!t._revenge, won: true, stars: stars } })
        .then(function (r) {
          var d = r && r.data;
          if (d && d.ok && d.looted) {                              // server paid -> drain the queued grants
            try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_e) {}
          } else if (!(d && d.ok)) {                                // hard error -> client fallback (full amount)
            grantRaidLoot(scaleReward(R.reward, mult));
          }
          // d.ok && !looted == already looted this window -> replays are free (intended)
        }, function () { grantRaidLoot(scaleReward(R.reward, mult)); });   // network error -> client fallback
    } catch (_e2) { grantRaidLoot(scaleReward(R.reward, mult)); }
  }

  global.AK_MODES.raid = {
    setup: function (game) {
      // towers are built AFTER the engine calls setup() -> stash the layout now,
      // apply the HP shaping lazily on the first live checkEnd (towers exist by then).
      var target = readRaidTarget() || {};
      // consume the handoff so a stale base can't leak into a later raid
      try { if (typeof localStorage !== 'undefined') localStorage.removeItem('ak_raid_target'); } catch (_e) {}
      try { global.AK_RAID_TARGET = null; } catch (_e2) {}
      var layout = Array.isArray(target.layout) ? target.layout : [];
      game.raid = {
        target: target, layout: layout,
        coreHp: clamp(num(target.coreHp, 4200), 1500, 12000),
        wallHp: sumWallHp(layout),
        reward: target.reward || {},
        structures: layout.length,
        // AK-RAID3STAR: won = the 50% line was crossed (win is then guaranteed);
        // paid1/2/3 = the 1/2/3-star loot tranches were banked (idempotent).
        // serverSettle (null=undecided) + settled gate the server-authoritative path.
        applied: false, won: false, paid1: false, paid2: false, paid3: false, stars: 0, pct: 0,
        serverSettle: null, settled: false
      };
    },
    checkEnd: function (game) {
      var R = game.raid; if (!R) return null;
      var opp = game.opponent, me = game.player;
      if (!opp || !me || !opp.towers || !opp.towers.length) return null;   // countdown: towers not built yet
      // ---- lazy seed: shape the enemy base towers from the scouted layout ----
      if (!R.applied) {
        R.applied = true;
        var core = kingTower(opp);
        var walls = opp.towers.filter(function (t) { return t && t.type !== 'king'; });
        if (core) { core.maxHp = Math.max(core.maxHp | 0, R.coreHp | 0); core.hp = core.maxHp; }
        // WALL COMBAT (#2): the engine is frozen (only 2 perimeter destructibles +
        // 1 king), so the scouted walls (wood200/stone500/metal1200, summed in
        // R.wallHp) are wired in as the ACTUAL armor the raider must chew through on
        // the perimeter towers -- a metal-heavy base really is tougher to crack and
        // the walls GATE the lane until broken (engine towers block units inherently;
        // breaking them opens the path to the core). The perimeter TOTAL is capped at
        // 85% of coreHp so the CORE always stays > 50% of the base (coreShare > 0.5):
        // the 50% win line can only be crossed via core damage, the core still has HP
        // at that crossing, and THIS checkEnd fires the win BEFORE the engine's
        // king-death crown path can pre-empt it (stars + loot stay under our control).
        var wallBudget = Math.min(R.wallHp | 0, Math.round((R.coreHp | 0) * 0.85));   // total perimeter HP < core
        var perWall = walls.length ? Math.max(1, Math.round(wallBudget / walls.length)) : 0;
        for (var w = 0; w < walls.length; w++) { walls[w].maxHp = perWall; walls[w].hp = perWall; }
        R.core = core; R.wallTowers = walls;
        R.allTowers = walls.concat(core ? [core] : []);
        R.totalHp = R.allTowers.reduce(function (s, t) { return s + (t.maxHp | 0); }, 0) || 1;
      }
      // ---- progress: CoC-style % of the base destroyed ----
      var removed = 0, destroyed = 0, all = R.allTowers.length;
      for (var i = 0; i < all; i++) { var t = R.allTowers[i]; removed += ((t.maxHp | 0) - (t.destroyed ? 0 : (t.hp | 0))); if (t.destroyed) destroyed++; }
      var pct = clamp(removed / R.totalHp, 0, 1);
      // CoC star ladder (AK_2D_3D / economy-web): 50% = 1 star, 75% = 2 stars,
      // 100% (or the core down, or essentially-total >=97%) = 3 stars. Reaching
      // 50% no longer ENDS the raid -- it banks a guaranteed win and lets you
      // keep deploying to push toward 2/3 stars for the bonus tranches.
      var coreDead = R.core ? (R.core.destroyed || (R.core.hp | 0) <= 0) : false;
      var full = coreDead || destroyed >= all || pct >= 0.97;
      var stars = full ? 3 : (pct >= 0.75 ? 2 : (pct >= 0.5 ? 1 : 0));
      game.stars = stars; R.stars = stars; R.pct = pct;        // keep live so any end path inherits it

      // ---- progressive star-loot tranches (idempotent; banked even if the
      // clock or the core-death ends the push before checkEnd returns) ----
      // when the SERVER will settle (online + real base id), the client grants are
      // suppressed -- settleRaidServer() pays once, star-scaled, at the terminal win.
      // The phaseAlerts still fire for in-match feel either way.
      if (stars >= 1 && !R.paid1) {
        R.paid1 = true; R.won = true; if (!serverWillSettle(R)) grantRaidLoot(R.reward);               // 1.0x base
        try { game.phaseAlert = { name: 'BASE CRACKED', flavor: '1★ secured -- push to 100% for more loot', ttl: 2.4, dur: 2.4 }; } catch (_e1) {}
      }
      if (stars >= 2 && !R.paid2) {
        R.paid2 = true; if (!serverWillSettle(R)) grantRaidLoot(scaleReward(R.reward, 0.5));           // +0.5x  (cum 1.5x)
        try { game.phaseAlert = { name: '2★ -- BONUS LOOT', flavor: 'Crack the core for the clean sweep', ttl: 2.2, dur: 2.2 }; } catch (_e2) {}
      }
      if (stars >= 3 && !R.paid3) {
        R.paid3 = true; if (!serverWillSettle(R)) grantRaidLoot(scaleReward(R.reward, 1.0)); game.cleanSweep = true;  // +1.0x (cum 2.5x) + best chest
        try { game.phaseAlert = { name: 'BASE WIPED -- 3★', flavor: 'Clean sweep. The block is yours.', ttl: 2.6, dur: 2.6 }; } catch (_e3) {}
      }

      // ---- once the 50% line is crossed the win is LOCKED (CoC rule): shield
      // your own King so an enemy counter-push can't flip a secured raid into a
      // loss. checkWin() (engine) runs BEFORE this seam, so we keep the king
      // topped every frame -- a full king tower can't be deleted in one substep. ----
      var pk = kingTower(me);
      if (R.won && pk) { pk.hp = pk.maxHp; pk.destroyed = false; }

      // ---- TERMINAL: 100% / core-dead -> end now, guaranteed 3 stars + sweep ----
      if (full) { game.stars = 3; settleRaidServer(R, 3); return { result: 'win', stars: 3, cleanSweep: true }; }
      // ---- TERMINAL: pre-50% LOSE -- your own King fell (only possible before the win lock) ----
      if (!R.won && pk && (pk.destroyed || (pk.hp | 0) <= 0)) return { result: 'lose', stars: 0 };
      // ---- TERMINAL: clock out -- bank the win at current stars if 50%+ was reached, else lose ----
      if (num(game.time, 99) <= 0.12) {
        if (R.won) { var fs = clamp(stars, 1, 3); game.stars = fs; settleRaidServer(R, fs); return { result: 'win', stars: fs, cleanSweep: false }; }
        return { result: 'lose', stars: 0 };
      }
      return null;   // raid continues -- keep cracking toward 100%
    },
    hud: function (game) {
      var R = game.raid; if (!R || !R.applied) return 'RAID -- crack the base';
      var st = R.stars | 0;
      var stars = (st >= 1 ? '★' : '☆') + (st >= 2 ? '★' : '☆') + (st >= 3 ? '★' : '☆');
      return 'BASE ' + Math.round(num(R.pct, 0) * 100) + '%  ' + stars + (R.won && !R.paid3 ? '  PUSH 100%' : '');
    }
  };

  /* ===================================================================== */
  /* WORLD-MAP RPG DEFENSE (resolveDefense) -- CORE LOOP CANON line 4 + 5.    */
  /* When a rival clan attacks you ON THE WORLD MAP (NOT the tower lane), your */
  /* default 11-card deck defends RPG-STYLE -- a self-contained auto-skirmish  */
  /* drawn in an overlay, wholly distinct from the FROZEN lane engine. The     */
  /* defense RESOLUTION wires the stakes spine:                                */
  /*   - p.raid.shieldUntil active  -> the Watch held: raid BLOCKED, no fight. */
  /*   - else p.fortify[zone] toughens the pack + the block (factors the ODDS).*/
  /*   - on a LOSS  -> AK_ECON.raidDamage(p,severity) drops the Town Hall (the */
  /*     deck de-levels with it) + every fallen dog is benched via             */
  /*     AK_INFIRMARY.downCard() until it heals.                               */
  /*   - on a WIN   -> the player is PROTECTED (no TH hit, no benched dogs) +   */
  /*     a small soft-currency hold reward.                                    */
  /* Reuses the SAME kill-scaling + needle-drop punch as WORLD-MOBA. Every new */
  /* helper (raidDamage / downCard / fortify / types / districtmusic) is read  */
  /* DEFENSIVELY -- absent ones no-op, never throw. Headless-safe: with no     */
  /* overlay host it runs an instant sim and applies the same consequences.    */
  /* ===================================================================== */
  function shieldUntilOf(p) {                                  // p.raid.shieldUntil is canon; tolerate a flat p.shieldUntil
    if (!p) return 0;
    var r = (p.raid && p.raid.shieldUntil); return num(r, 0) || num(p.shieldUntil, 0) || 0;
  }
  function shieldActive(p) { return shieldUntilOf(p) > Date.now(); }
  function fortifyLevelOf(p, zone) {                           // p.fortify[zone] (0..10); falsy-default 0
    try { if (p && p.fortify && zone != null) return Math.max(0, (p.fortify[zone] | 0)); } catch (_e) {}
    try { if (global.AK_BUILDMODE && AK_BUILDMODE.fortifyLevel) return (AK_BUILDMODE.fortifyLevel(zone) | 0); } catch (_e2) {}
    return 0;
  }
  function fortifyMultOf(level) {                              // canonical level->multiplier (buildmode owns it)
    try { if (global.AK_BUILDMODE && AK_BUILDMODE.fortifyDefense) return AK_BUILDMODE.fortifyDefense(level); } catch (_e) {}
    return 1 + 0.15 * Math.max(0, Math.min(10, level | 0));
  }
  function cardLvlOf(p, name) {                                // deck card level (TH-capped); falsy-default 1
    try { if (global.AK_ECON && AK_ECON.cardLevel) return AK_ECON.cardLevel(p, name); } catch (_e) {}
    return 1;
  }
  function isDownCard(name) {                                  // a dog already in the Infirmary cannot defend
    try { if (global.AK_INFIRMARY && AK_INFIRMARY.isDown) return !!AK_INFIRMARY.isDown(name); } catch (_e) {}
    return false;
  }
  // the 11 dogs that defend: the active deck first, padded from owned, never the
  // downed -- and never empty (a zero-state player still stands on the King).
  function defenderNames(p, roster) {
    var d = (p && (p.deck || p.activeDeck || p.deckNames)) || [];
    var owned = (p && Array.isArray(p.owned)) ? p.owned : [];
    var seen = {}, out = [];
    if (Array.isArray(d)) for (var i = 0; i < d.length; i++) { var n = d[i]; if (n && !seen[n] && roster[n] && !isDownCard(n)) { seen[n] = 1; out.push(n); } }
    for (var j = 0; j < owned.length && out.length < 11; j++) { var m = owned[j]; if (m && !seen[m] && roster[m] && !isDownCard(m)) { seen[m] = 1; out.push(m); } }
    if (!out.length) { var k = roster['$BCARDD'] ? '$BCARDD' : Object.keys(roster)[0]; if (k) out.push(k); }
    return out.slice(0, 11);
  }
  // the raiding party: a marquee boss + cheap runners, sized + scaled by tier.
  function buildRaiders(roster, opts, leadName) {
    var tier = clamp(num(opts.tier, 2), 1, 5);
    var bossName = opts.attacker || opts.bossName || opts.enemyHero || pickEnemyHero(roster, leadName);
    var pool = cheapNames(roster), n = clamp(2 + tier, 3, 7), names = [bossName];
    for (var i = 1; i < n; i++) names.push(pool[Math.floor(Math.random() * pool.length)]);
    return { bossName: bossName, names: names, tier: tier };
  }

  function openDefense(ctx, opts) {
    opts = opts || {};
    ctx = ctx || global.AK_CTX;
    var roster = getRoster(ctx);
    var p = opts.profile || (ctx && ctx.econ && ctx.econ.loadProfile && ctx.econ.loadProfile()) || null;
    var zone = (opts.zone != null) ? opts.zone : ((ctx && ctx.zoneId) || (p && p.zoneId) || null);

    // ---- SHIELD: an active shield means the Watch held -- the raid never lands. ----
    if (shieldActive(p)) {
      try { if (ctx && ctx.showBanner) ctx.showBanner('RAID BLOCKED -- the shield held the block', 2.2); } catch (_e) {}
      var blocked = { result: 'blocked', blocked: true, win: true, fallen: [], zone: zone };
      if (opts.onResult) try { opts.onResult(blocked); } catch (_e2) {}
      return blocked;
    }

    var fortLvl  = fortifyLevelOf(p, zone);
    var fortMult = fortifyMultOf(fortLvl);                     // a fortified district fields a tougher pack + block
    var defNames = defenderNames(p, roster);
    var leadName = defNames[0] || '$BCARDD';
    var atkSpec  = buildRaiders(roster, opts, leadName);
    var tier     = atkSpec.tier;
    var atkScale = 0.85 + 0.18 * tier;                         // raid tier -> attacker HP/dmg

    // type advantage: your lead dog vs the raid boss (modes' OWN combat, engine untouched)
    var pType = (global.AK_TYPES) ? AK_TYPES.typeOf(leadName) : 'Stray';
    var eType = (global.AK_TYPES) ? AK_TYPES.typeOf(atkSpec.bossName) : 'Stray';
    var typeMult = (global.AK_TYPES) ? AK_TYPES.eff(pType, eType) : 1.0;

    var AW = 600, AH = 900, MIDY = AH * 0.40;                  // defenders hold the lower half (the block)
    var ents = [], fx = [], BTN = {}, api = null;
    var S = { over: false, win: false, kills: 0, t: num(opts.clock, 45), rally: 0, rallyLeft: 2,
              fallenSet: {}, settled: false, result: null, visual: false };

    function mkU(name, team, kind, x, y) {
      var s = statline(roster[name] || EMBED[name] || {});
      var lvl = (team === 0) ? cardLvlOf(p, name) : 1;
      var lvlScale = 1 + 0.07 * Math.max(0, lvl - 1);
      var hp, dmg, r, rng, spd, atk;
      if (kind === 'core') { hp = Math.round(1300 * fortMult); dmg = 95; r = 34; rng = 150; spd = 0; atk = 1.0; }
      else {
        hp  = clamp(Math.round(s.rawHp / 6 * lvlScale), 120, 2400);
        dmg = clamp(Math.round(s.rawDmg * 0.7 * lvlScale), 16, 340);
        r = (kind === 'boss') ? 20 : 15; rng = 24 + s.rangeTiles * 15;
        spd = s.moveBase * (kind === 'boss' ? 0.95 : 0.85); atk = s.atkInterval;
        if (team === 0) { hp = Math.round(hp * fortMult); }                 // FORTIFY toughens your pack (factors the odds)
        else { hp = Math.round(hp * atkScale); dmg = Math.round(dmg * atkScale); }
      }
      var e = { name: name, team: team, kind: kind, x: x, y: y, r: r, maxHp: hp, hp: hp, dmg: dmg,
                rngPx: rng, spd: spd, atkInt: atk, atkT: 0, dead: false, hitFx: 0, think: rand(0, 0.6),
                rarity: s.rarity, kstreak: 0, ktier: 0, baseDmg: dmg, baseMaxHp: hp,
                isLead: (team === 0 && kind !== 'core' && name === leadName) };
      if (team === 0 && kind !== 'core' && typeMult !== 1) { e.dmg = Math.max(1, Math.round(e.dmg * typeMult)); e.baseDmg = e.dmg; }
      return e;
    }

    var core = mkU(leadName, 0, 'core', AW / 2, AH - 80); core.name = 'THE BLOCK';
    ents.push(core);
    for (var di = 0; di < defNames.length; di++) {            // your 11 (or fewer) in two rows in front of the block
      var row = di < 6 ? 0 : 1, col = di < 6 ? di : di - 6;
      var per = (row === 0) ? Math.min(6, defNames.length) : Math.max(1, defNames.length - 6);
      var dx = AW * (0.16 + 0.68 * (per <= 1 ? 0.5 : (col / (per - 1))));
      ents.push(mkU(defNames[di], 0, 'def', dx, AH - 240 - row * 72));
    }
    for (var ai = 0; ai < atkSpec.names.length; ai++) {       // raiders march down from the top
      var pe = atkSpec.names.length;
      var ax = AW * (0.18 + 0.64 * (pe <= 1 ? 0.5 : (ai / (pe - 1))));
      ents.push(mkU(atkSpec.names[ai], 1, ai === 0 ? 'boss' : 'raider', ax, 110 + (ai % 2) * 42));
    }

    function nearestFoe(e, maxD) {
      var best = null, bd = maxD || 1e9;
      for (var i = 0; i < ents.length; i++) { var o = ents[i]; if (o.dead || o.team === e.team) continue; var d = hyp(o.x - e.x, o.y - e.y); if (d < bd) { bd = d; best = o; } }
      return best;
    }
    function coreWipe() { return core.dead || (core.hp | 0) <= 0; }

    function dHit(att, tgt) {
      tgt.hp -= att.dmg; tgt.hitFx = 0.12;
      if (S.visual) fx.push({ x1: att.x, y1: att.y, x2: tgt.x, y2: tgt.y, life: 0.12, col: att.team === 0 ? '#e8c55a' : '#ff6b6b' });
      if (tgt.hp <= 0 && !tgt.dead) {
        tgt.dead = true;
        // SAME kill-scaling as WORLD-MOBA: per-kill 3-tier buff (stacks) + a kill-heal.
        if (att && !att.dead && att.kind !== 'core') {
          var prevTier = att.ktier | 0;
          att.kstreak = (att.kstreak | 0) + 1;
          att.ktier   = att.kstreak >= 5 ? 3 : (att.kstreak >= 3 ? 2 : 1);
          att.dmg     = Math.round((att.baseDmg | 0) * (1 + 0.22 * att.ktier));
          att.maxHp   = Math.round((att.baseMaxHp | 0) * (1 + 0.12 * att.ktier));
          att.hp      = Math.min(att.maxHp, att.hp + Math.round((att.baseMaxHp | 0) * 0.10));
          // SAME needle-drop punch: only on YOUR lead dog's tier-up, only while watched.
          if (att.isLead && att.ktier > prevTier && S.visual && typeof window !== 'undefined') {
            try {
              if (window.AK_DISTRICTMUSIC && typeof window.AK_DISTRICTMUSIC.needleDrop === 'function') window.AK_DISTRICTMUSIC.needleDrop(att.ktier);
              else window.dispatchEvent(new CustomEvent('ak:needledrop', { detail: { intensity: att.ktier } }));
            } catch (_e) {}
          }
        }
        if (att.team === 0 && tgt.team === 1) S.kills++;
        if (tgt.team === 0 && tgt.kind !== 'core') S.fallenSet[tgt.name] = 1;   // remember YOUR dead for the Infirmary
      }
    }

    function doRally() {
      if (S.over || S.rallyLeft <= 0 || S.rally > 0) return;
      S.rallyLeft--; S.rally = 10;
      for (var i = 0; i < ents.length; i++) { var e = ents[i]; if (e.team === 0 && e.kind !== 'core' && !e.dead) e.hp = Math.min(e.maxHp, e.hp + Math.round(e.maxHp * 0.25)); }
      try { if (ctx && ctx.showBanner) ctx.showBanner('RALLY -- the pack digs in', 1.2); } catch (_e) {}
      if (S.visual) fx.push({ ring: true, x: core.x, y: core.y - 120, life: 0.4, col: '#7CFFb0' });
    }

    function step(dt) {
      S.t -= dt; if (S.rally > 0) S.rally = Math.max(0, S.rally - dt);
      for (var i = 0; i < ents.length; i++) {
        var e = ents[i];
        if (e.hitFx > 0) e.hitFx -= dt; if (e.atkT > 0) e.atkT -= dt;
        if (e.dead) continue;
        if (e.kind === 'core') { var ct = nearestFoe(e, e.rngPx); if (ct && e.atkT <= 0) { dHit(e, ct); e.atkT = e.atkInt; } continue; }
        var tgt = nearestFoe(e, 1e9);
        if (!tgt) { if (e.team === 1) tgt = core; else continue; }            // raiders with no defender left swarm the block
        var dx = tgt.x - e.x, dy = tgt.y - e.y, d = hyp(dx, dy) || 1, reach = e.rngPx + tgt.r * 0.5;
        if (d > reach) {
          var nx = e.x + (dx / d) * e.spd * dt, ny = e.y + (dy / d) * e.spd * dt;
          if (e.team === 0) ny = Math.max(ny, MIDY);                          // defenders hold the line, never chase past midfield
          e.x = clamp(nx, 20, AW - 20); e.y = clamp(ny, 20, AH - 20);
        } else if (e.atkT <= 0) { dHit(e, tgt); e.atkT = e.atkInt; }
      }
      if (S.visual) for (var f = fx.length - 1; f >= 0; f--) { fx[f].life -= dt; if (fx[f].life <= 0) fx.splice(f, 1); }
      if (!S.over) {
        var raiders = 0; for (var r = 0; r < ents.length; r++) if (ents[r].team === 1 && !ents[r].dead) raiders++;
        if (raiders === 0) finishDefense(true);
        else if (coreWipe()) finishDefense(false);
        else if (S.t <= 0) finishDefense((core.hp / core.maxHp) >= 0.4);      // clock out -- held the block? you win
      }
    }

    function finishDefense(win) {
      if (S.settled) return S.result;
      S.settled = true; S.over = true; S.win = win;
      var fallen = Object.keys(S.fallenSet);
      if (win) {
        // PROTECT THE PLAYER: no Town Hall hit, no benched dogs. Small hold reward.
        /* AK-FIX-lane-D:modes.js 2026-07-28: STREET PAY MULTIPLIER on the defense hold gold (guarded, 1x if unwired). */
        try { if (ctx && ctx.currency) { var _dpay = (global.AK_ECON && AK_ECON.streetPayMult) ? AK_ECON.streetPayMult() : 1; ctx.currency.grant('gold', Math.max(1, Math.round(rand(60, 110) * _dpay))); ctx.currency.grant('bones', 2); } } catch (_e) {}
        try { recordResult(ctx, 'world-defense', true, S.kills * 10 + 100); } catch (_e2) {}
        try { if (ctx && ctx.econ && ctx.econ.addTrophies) ctx.econ.addTrophies(6); } catch (_e3) {}
        S.result = { result: 'win', win: true, blocked: false, fallen: [], zone: zone, fortify: fortLvl, kills: S.kills };
      } else {
        // LOSS: the block fell. Town Hall takes the hit -> the deck de-levels with it.
        var deckN = defNames.length || 1, frac = fallen.length / deckN;
        var sev = (frac >= 0.6 || (coreWipe() && frac >= 0.5)) ? 'devastating' : (frac >= 0.3 ? 'major' : 'minor');
        var de = null;
        try { if (global.AK_ECON && AK_ECON.raidDamage) de = AK_ECON.raidDamage(null, sev); } catch (_e) {}   // null -> atomic self-save (TH down, persisted)
        for (var i = 0; i < fallen.length; i++) { try { if (global.AK_INFIRMARY && AK_INFIRMARY.downCard) AK_INFIRMARY.downCard(fallen[i]); } catch (_e2) {} }
        try { recordResult(ctx, 'world-defense', false, 0); } catch (_e3) {}
        try { if (ctx && ctx.econ && ctx.econ.addTrophies) ctx.econ.addTrophies(-8); } catch (_e4) {}
        S.result = { result: 'lose', win: false, blocked: false, fallen: fallen, severity: sev, deLevel: de, zone: zone, fortify: fortLvl };
      }
      if (S.visual && api) setTimeout(function () { try { if (api) api.close(S.result); } catch (_e) {} }, 1400);
      if (opts.onResult) try { opts.onResult(S.result); } catch (_e) {}
      return S.result;
    }

    function draw(g, vp) {
      var sc = Math.min(vp.w / AW, vp.h / AH) * 0.98;
      var ox = (vp.w - AW * sc) / 2, oy = (vp.h - AH * sc) / 2;
      function X(x) { return ox + x * sc; } function Y(y) { return oy + y * sc; }
      g.fillStyle = '#06070c'; g.fillRect(0, 0, vp.w, vp.h);
      g.save(); g.fillStyle = '#0c0e16'; g.fillRect(X(0), Y(0), AW * sc, AH * sc);
      g.strokeStyle = 'rgba(201,168,76,.3)'; g.lineWidth = 2; g.strokeRect(X(0), Y(0), AW * sc, AH * sc); g.restore();
      g.strokeStyle = 'rgba(201,168,76,.12)'; g.lineWidth = 1; g.beginPath(); g.moveTo(X(0), Y(MIDY)); g.lineTo(X(AW), Y(MIDY)); g.stroke();
      for (var fi = 0; fi < fx.length; fi++) { var x = fx[fi]; g.save();
        if (x.ring) { g.globalAlpha = clamp(x.life * 2, 0, 1); g.strokeStyle = x.col; g.lineWidth = 3; g.beginPath(); g.arc(X(x.x), Y(x.y), 90 * (1 - x.life) * sc, 0, 2 * PI); g.stroke(); }
        else { g.globalAlpha = clamp(x.life * 6, 0, 1); g.strokeStyle = x.col; g.lineWidth = 2; g.beginPath(); g.moveTo(X(x.x1), Y(x.y1)); g.lineTo(X(x.x2), Y(x.y2)); g.stroke(); }
        g.restore(); }
      for (var i = 0; i < ents.length; i++) {
        var e = ents[i]; if (e.dead && e.kind !== 'core') continue;
        var fill = e.team === 0 ? '#caa84c' : '#b8434c';
        var ring = e.isLead ? '#fff' : rarColor(e.rarity);
        if (e.kind === 'core') { g.save(); g.fillStyle = e.hp > 0 ? '#1c2a18' : '#2a1418'; g.strokeStyle = e.hp > 0 ? '#7CFFb0' : '#ff6b6b'; g.lineWidth = 3; g.beginPath(); g.arc(X(e.x), Y(e.y), e.r * sc, 0, 2 * PI); g.fill(); g.stroke(); g.restore(); }
        else dogChip(g, X(e.x), Y(e.y), (e.r + (e.hitFx > 0 ? 2 : 0)) * sc, fill, ring, chipLetter(e.name), e.name);
        if (e.ktier > 0 && e.kind !== 'core') {                              // SAME Mario-Star killstreak aura as the MOBA
          var kc = e.ktier >= 3 ? '#ff3df0' : (e.ktier >= 2 ? '#ffd76b' : '#7CFFb0');
          g.save(); g.globalAlpha = 0.5 + 0.3 * Math.abs(Math.sin((S.t || 0) * 5)); g.strokeStyle = kc; g.lineWidth = 1.5 + e.ktier;
          g.beginPath(); g.arc(X(e.x), Y(e.y), (e.r + 4 + e.ktier * 2) * sc, 0, 2 * PI); g.stroke(); g.restore();
        }
        bar(g, X(e.x) - e.r * sc, Y(e.y) - (e.r + 8) * sc, e.r * 2 * sc, 4, e.hp / e.maxHp, e.team === 0 ? '#6be08a' : '#ff6b6b');
      }
      drawHUD(g, vp);
    }
    function drawHUD(g, vp) {
      g.save(); g.fillStyle = 'rgba(6,6,12,.82)'; g.fillRect(0, 0, vp.w, 38);
      g.fillStyle = '#ff8a6b'; g.font = '900 13px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText('THE BLOCK UNDER RAID -- hold the line', vp.w / 2, 13);
      var raiders = 0; for (var i = 0; i < ents.length; i++) if (ents[i].team === 1 && !ents[i].dead) raiders++;
      g.fillStyle = '#cfe'; g.font = '700 10px Inter,sans-serif'; g.fillText('RAIDERS ' + raiders + '   FORTIFY LV ' + fortLvl + '   ' + fmtClock(S.t), vp.w / 2, 28);
      g.restore();
      bar(g, 14, vp.h - 26, 160, 12, core.hp / core.maxHp, '#7CFFb0');
      g.fillStyle = '#cfe'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText('THE BLOCK', 14, vp.h - 38);
      if (!BTN.rally) BTN.rally = { x: vp.w - 54, y: vp.h - 54, r: 30 };
      btnCircle(g, BTN.rally, S.rallyLeft > 0 && S.rally <= 0 && !S.over, '+', 'RALLY ' + S.rallyLeft);
      if (S.over) centerBanner(g, vp, S.win ? 'BLOCK HELD -- RAID REPELLED' : 'THE BLOCK FELL -- TOWN HALL HIT', S.win ? '#7CFFb0' : '#ff6b6b');
    }
    function pointer(evt) { if (evt.type !== 'pointerdown') return; var b = BTN.rally; if (b && hyp(evt.clientX - b.x, evt.clientY - b.y) <= b.r + 8) doRally(); }

    // ---- HEADLESS path: no overlay host -> instant sim, same consequences. ----
    if (!ctx || !ctx.overlay) {
      var guard = 0;
      while (!S.over && guard++ < 6000) step(1 / 30);
      if (!S.over) finishDefense((core.hp / core.maxHp) >= 0.4);
      return S.result;
    }

    // ---- VISUAL path: RPG auto-skirmish overlay (NOT the lane engine). ----
    S.visual = true;
    if (ctx.showBanner) ctx.showBanner('RAID INBOUND -- defend the block, RPG-style', 1.6);
    try { if (typeMult !== 1 && ctx.showBanner && global.AK_TYPES) ctx.showBanner('TYPE  ' + AK_TYPES.label(pType) + ' vs ' + AK_TYPES.label(eType) + '  ' + (typeMult > 1 ? 'SUPER EFFECTIVE +20%' : 'resisted -20%'), 2.4); } catch (_e) {}
    api = ctx.overlay.open({
      id: 'mode_world_defense',
      onFrame: function (g, dt, _vp) { if (!S.over) step(dt); else { for (var f = fx.length - 1; f >= 0; f--) { fx[f].life -= dt; if (fx[f].life <= 0) fx.splice(f, 1); } } draw(g, _vp); },
      onPointer: function (evt) { pointer(evt); },
      onClose: function (res) { if (ctx.showBanner && res) ctx.showBanner(res.win ? 'BLOCK HELD -- your deck stays max' : 'RAIDED -- Town Hall down, dogs in the Infirmary', 1.8); }
    });
    return api;
  }

  // Expose the overlay launchers + router so the encounters / raid waves can
  // call them (ctx defaults to window.AK_CTX).
  global.AK_MODES.openWorldMoba  = function (ctx, o) { return openWorldMoba(ctx || global.AK_CTX, o); };
  global.AK_MODES.openGulag      = function (ctx, o) { return openGulag(ctx || global.AK_CTX, o); };
  global.AK_MODES.routeEncounter = routeEncounter;
  // WORLD-MAP RPG DEFENSE -- the wired raid resolution (shield / fortify / raidDamage / Infirmary).
  global.AK_MODES.openDefense    = function (ctx, o) { return openDefense(ctx || global.AK_CTX, o); };
  global.AK_MODES.resolveDefense = function (o) { o = o || {}; return openDefense(o.ctx || global.AK_CTX, o); };
  global.AK_MODES.defendWorldRaid = global.AK_MODES.resolveDefense;

  /* ===================================================================== */
  /* HUB MODULE -- owns THE STREET interior (the mode picker). Hub-only.      */
  /* ===================================================================== */
  function renderStreetPicker(ctx, b) {
    ctx.ui.keeperCard({
      place: (b && b.label) || 'THE STREET',
      glyph: '🎮',
      name: 'Switch the Hustler',
      line: "Streets got more than one way to settle it, dog. Pick how you bang it out.",
      interiorArt: 'assets/interiors/merchant.png',
      buttons: [
        { label: 'WORLD MOBA', primary: true,  onClick: function (c) { openWorldMoba(c); } },
        { label: 'GULAG 1v1',  primary: false, onClick: function (c) { openGulag(c); } },
        { label: 'STREET ENCOUNTER', primary: false, onClick: function (c) { routeEncounter({ ctx: c }); } },
        { label: 'DEFEND THE BLOCK', primary: false, onClick: function (c) { openDefense(c, { tier: 3 }); } }
      ]
    });
  }

  if (global.AK_SYSTEMS) {
    global.AK_SYSTEMS.register({
      id: 'modes',
      // warm the roster cache + the three_boot loader (owns no renderer, costs 0 WebGL
      // contexts) so the Gulag opens straight into the FPS view instead of upgrading late.
      init: function (ctx) { try { ensureFetch(ctx); } catch (_e) {} try { warmThree(); } catch (_e2) {} },
      onEnterBuilding: function (b, ctx) {
        if (!b || b.id !== 'STREET') return false;                        // claim ONLY THE STREET (contract Section 4)
        renderStreetPicker(ctx, b);
        return true;
      }
    });
  }

})(typeof window !== 'undefined' ? window : globalThis);
