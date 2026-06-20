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
    try {
      if (kind === 'moba') {
        if (win) { ctx.currency.grant('gold', Math.round(rand(140, 220))); ctx.currency.grant('scrap', 2, 'Rare'); ctx.currency.grant('bones', 5); }
        else     { ctx.currency.grant('gold', 30); ctx.currency.grant('bones', 1); }
      } else { // gulag
        if (win) { ctx.currency.grant('gold', Math.round(rand(90, 150))); ctx.currency.grant('scrap', 5, 'Common'); ctx.currency.grant('bones', 3); }
        else     { ctx.currency.grant('gold', 20); }
      }
    } catch (_e) {}
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

  /* -------------------------------------------------------- draw primitives */
  function dogChip(g, x, y, r, fill, ring, letter) {
    g.save();
    g.beginPath(); g.arc(x, y, r, 0, 2 * PI); g.closePath();
    g.fillStyle = fill; g.fill();
    if (ring) { g.lineWidth = 2; g.strokeStyle = ring; g.stroke(); }
    if (letter) { g.fillStyle = '#0a0a0e'; g.font = '900 ' + Math.round(r * 1.05) + 'px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(letter, x, y + 1); }
    g.restore();
  }
  function bar(g, x, y, w, h, frac, fill, bg) {
    g.save();
    g.fillStyle = bg || 'rgba(8,8,14,.8)'; g.fillRect(x, y, w, h);
    g.fillStyle = fill; g.fillRect(x, y, w * clamp(frac, 0, 1), h);
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.5)'; g.strokeRect(x, y, w, h);
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
    var foeName  = opts.enemyHero || pickEnemyHero(roster, heroName);
    var minPool  = cheapNames(roster);

    var AW = 920, AH = 1560;                 // tall lane arena (world coords)
    var WAVE_INT = 11, MAX_MIN = 7;          // minion cadence + per-side cap
    var MATCH_T = 150;                       // hard match clock (sec)
    var HERO_RESPAWN = 6;                    // sec to respawn a fallen hero

    var ents = [], fx = [];
    var S = { t: MATCH_T, over: false, win: false, gold: 0, lvl: 1, kills: 0,
              energy: 100, eMax: 100, waveT: 3, sg: { mob: 0, blast: 0, ult: 0 } };
    var inp = { mvId: null, mox: 0, moy: 0, mvx: 0, mvy: 0 };
    var hero = null, foe = null, allyCore = null, foeCore = null, vp = null, api = null;
    var BTN = {};

    function mk(name, team, x, y, kind) {
      var s = statline(roster[name] || EMBED[name] || {});
      var e = {
        kind: kind, name: name, team: team, x: x, y: y,
        r: kind === 'core' ? 40 : (kind === 'hero' ? 22 : 14),
        maxHp: kind === 'core' ? 4200
              : (kind === 'hero' ? clamp(Math.round(s.rawHp / 3.2), 420, 1600)
                                 : clamp(Math.round(s.rawHp / 9),   60,  900)),
        hp: 0,
        dmg: kind === 'core' ? 120
            : (kind === 'hero' ? clamp(Math.round(s.rawDmg * 0.9), 26, 320)
                               : clamp(Math.round(s.rawDmg * 0.6), 14, 240)),
        rngPx: kind === 'core' ? 150 : (26 + s.rangeTiles * 16),
        spd: kind === 'core' ? 0 : (s.moveBase * (kind === 'minion' ? 0.85 : 1)),
        atkInt: kind === 'core' ? 0.9 : s.atkInterval,
        atkT: 0, dead: false, respawnT: 0, hitFx: 0, think: 0, strafe: 1,
        rarity: s.rarity, ability: s.abilityName, baseDmg: 0, baseMaxHp: 0
      };
      e.hp = e.maxHp; e.baseDmg = e.dmg; e.baseMaxHp = e.maxHp;
      return e;
    }

    function build() {
      allyCore = mk('$BCARDD', 0, AW / 2, AH - 110, 'core'); allyCore.name = 'YOUR CORE';
      foeCore  = mk(foeName,  1, AW / 2, 110,        'core'); foeCore.name  = 'RIVAL CORE';
      hero     = mk(heroName, 0, AW / 2, AH - 240, 'hero');
      foe      = mk(foeName,  1, AW / 2, 240,        'hero');
      ents = [allyCore, foeCore, hero, foe];
    }
    build();   // SYNCHRONOUS init -- step() never sees nulls (frame-1-safe).

    function spawnWave() {
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

    function doAttack(att, tgt) {
      tgt.hp -= att.dmg; tgt.hitFx = 0.12;
      fx.push({ x1: att.x, y1: att.y, x2: tgt.x, y2: tgt.y, life: 0.12, col: att.team === 0 ? '#e8c55a' : '#ff6b6b' });
      if (tgt.hp <= 0 && !tgt.dead) {
        tgt.dead = true; tgt.respawnT = (tgt.kind === 'hero') ? HERO_RESPAWN : 0;
        if (att.team === 0 && tgt.kind !== 'core') {      // last-hit gold (Mobile Legends)
          S.gold += tgt.kind === 'hero' ? 90 : 22;
          if (att === hero) S.kills += tgt.kind === 'hero' ? 2 : 1;
        }
      }
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
      e.dead = false; e.hp = e.maxHp; e.atkT = 0;
      e.x = core.x + rand(-30, 30); e.y = core.y + (e.team === 0 ? -90 : 90);
    }

    function aiHero(e, dt) {
      e.think -= dt;
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
          if (ht && hero.atkT <= 0) { doAttack(hero, ht); hero.atkT = hero.atkInt; }
          continue;
        }
        if (e === foe) { aiHero(e, dt); continue; }

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

      for (var f = fx.length - 1; f >= 0; f--) { fx[f].life -= dt; if (fx[f].life <= 0) fx.splice(f, 1); }
      // cull dead minions only -- cores + heroes persist (heroes respawn)
      ents = ents.filter(function (e) { return e.kind !== 'minion' || !e.dead; });

      if (!S.over) {
        if (foeCore.hp <= 0) { S.over = true; S.win = true; finish(); }
        else if (allyCore.hp <= 0) { S.over = true; S.win = false; finish(); }
        else if (S.t <= 0) { S.over = true; S.win = (foeCore.hp / foeCore.maxHp) < (allyCore.hp / allyCore.maxHp); finish(); }
      }
    }

    function useSkill(which) {
      if (S.over || hero.dead) return;
      var cost = which === 'mob' ? 20 : (which === 'blast' ? 35 : 70);
      if (S.energy < cost || S.sg[which] > 0) return;
      S.energy -= cost;
      if (which === 'mob') {                               // DASH toward stick dir (else up-lane)
        var m = hyp(inp.mvx, inp.mvy); var ux = 0, uy = -1;
        if (m > 0.05) { ux = inp.mvx / m; uy = inp.mvy / m; }
        hero.x = clamp(hero.x + ux * 150, 30, AW - 30); hero.y = clamp(hero.y + uy * 150, 30, AH - 30);
        S.sg.mob = 4; fx.push({ x1: hero.x, y1: hero.y, x2: hero.x, y2: hero.y, life: 0.2, col: '#7CFFb0' });
      } else if (which === 'blast') {                      // AoE burst around the hero
        for (var i = 0; i < ents.length; i++) { var o = ents[i]; if (o.dead || o.team === 0) continue; if (hyp(o.x - hero.x, o.y - hero.y) < 95) doAttack(hero, o); }
        S.sg.blast = 7; fx.push({ ring: true, x: hero.x, y: hero.y, life: 0.35, col: '#ff9d5c' });
      } else {                                             // ULT = the hero's named card ability: heavy nuke + self-heal
        var t = nearestEnemy(hero, 1e9);
        if (t) { var save = hero.dmg; hero.dmg = Math.round(hero.dmg * 4); doAttack(hero, t); hero.dmg = save; }
        hero.hp = Math.min(hero.maxHp, hero.hp + Math.round(hero.maxHp * 0.25));
        S.sg.ult = 18; fx.push({ ring: true, x: t ? t.x : hero.x, y: t ? t.y : hero.y, life: 0.5, col: '#ff8fae' });
      }
      // TODO-RESEARCH: per-card unique skill kits (read card.ability semantics),
      // jungle buffs + a Lord objective, draft/ban, 5v5, multiplayer netcode.
    }

    function finish() {
      grantReward(ctx, S.win, 'moba');
      recordResult(ctx, 'world-moba', S.win, S.kills * 10 + (S.win ? 100 : 0));
      // TODO-SERVER: server-authoritative result + crew leaderboard (ride ak_grants).
      setTimeout(function () { if (api) api.close({ win: S.win, kills: S.kills }); }, 1400);
    }

    function layoutButtons() {
      var bx = vp.w - 56, by = vp.h - 60;
      BTN.ult   = { x: bx,      y: by - 96, r: 30 };
      BTN.blast = { x: bx - 78, y: by - 36, r: 26 };
      BTN.mob   = { x: bx,      y: by,      r: 26 };
    }
    function w2s(x, y, cam) { return { x: x - cam.x, y: y - cam.y }; }

    function draw(g, _vp) {
      vp = _vp;
      if (!BTN.ult) layoutButtons();
      var camX = AW <= vp.w ? (AW - vp.w) / 2 : clamp(hero.x - vp.w / 2, 0, AW - vp.w);
      var camY = AH <= vp.h ? (AH - vp.h) / 2 : clamp(hero.y - vp.h / 2, 0, AH - vp.h);
      var cam = { x: camX, y: camY };

      g.fillStyle = '#0a0c12'; g.fillRect(0, 0, vp.w, vp.h);
      // lane
      var l = w2s(AW / 2 - 80, 0, cam), r2 = w2s(AW / 2 + 80, 0, cam);
      g.fillStyle = 'rgba(201,168,76,.05)'; g.fillRect(l.x, -cam.y, 160, AH);
      g.strokeStyle = 'rgba(201,168,76,.12)'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(l.x, -cam.y); g.lineTo(l.x, AH - cam.y); g.moveTo(r2.x, -cam.y); g.lineTo(r2.x, AH - cam.y); g.stroke();

      // fx beams + rings
      for (var fi = 0; fi < fx.length; fi++) { var x = fx[fi]; g.save();
        if (x.ring) { g.globalAlpha = clamp(x.life * 2, 0, 1); g.strokeStyle = x.col; g.lineWidth = 3; var p = w2s(x.x, x.y, cam); g.beginPath(); g.arc(p.x, p.y, 95 * (1 - x.life), 0, 2 * PI); g.stroke(); }
        else { g.globalAlpha = clamp(x.life * 6, 0, 1); g.strokeStyle = x.col; g.lineWidth = 2; var a = w2s(x.x1, x.y1, cam), b = w2s(x.x2, x.y2, cam); g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke(); }
        g.restore();
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
        var fill = e.team === 0 ? '#caa84c' : '#b8434c';
        var ring = e === hero ? '#fff' : rarColor(e.rarity);
        if (e.kind === 'core') { g.save(); g.fillStyle = e.team === 0 ? '#1c2a18' : '#2a1418'; g.strokeStyle = ring; g.lineWidth = 3; g.beginPath(); g.arc(sp.x, sp.y, e.r, 0, 2 * PI); g.fill(); g.stroke(); g.restore(); }
        else dogChip(g, sp.x, sp.y, e.r + (e.hitFx > 0 ? 2 : 0), fill, ring, chipLetter(e.name));
        bar(g, sp.x - e.r, sp.y - e.r - 8, e.r * 2, 4, e.hp / e.maxHp, e.team === 0 ? '#6be08a' : '#ff6b6b');
      }
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
      g.textAlign = 'center'; g.fillStyle = '#7fc8ff'; g.font = '700 11px Inter,sans-serif'; g.fillText('WORLD MOBA  ·  ' + hero.name + '  vs  ' + foe.name, vp.w / 2, 20);
      g.restore();
      // bottom-left health + energy taskbar
      bar(g, 14, vp.h - 40, 150, 12, hero.hp / hero.maxHp, '#6be08a');
      bar(g, 14, vp.h - 24, 150, 9, S.energy / S.eMax, '#5ab0ff');
      g.fillStyle = '#cfe'; g.font = '700 9px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle';
      g.fillText('HP', 168, vp.h - 34); g.fillText('EN', 168, vp.h - 19);
      // skill buttons (right): DASH / BLAST / ULT(named ability)
      btnCircle(g, BTN.mob,   S.energy >= 20 && S.sg.mob <= 0   && !hero.dead, '>', 'DASH');
      btnCircle(g, BTN.blast, S.energy >= 35 && S.sg.blast <= 0 && !hero.dead, '*', 'BLAST');
      btnCircle(g, BTN.ult,   S.energy >= 70 && S.sg.ult <= 0   && !hero.dead, '!', (hero.ability || 'ULT').slice(0, 6).toUpperCase());
      // minimap (top-right)
      var mw = 56, mh = 88, mx = vp.w - mw - 8, my = 44;
      g.save(); g.fillStyle = 'rgba(8,8,14,.7)'; g.fillRect(mx, my, mw, mh);
      g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1; g.strokeRect(mx, my, mw, mh);
      for (var i = 0; i < ents.length; i++) { var e = ents[i]; if (e.dead) continue; g.fillStyle = e.team === 0 ? '#e8c55a' : '#ff6b6b'; g.beginPath(); g.arc(mx + (e.x / AW) * mw, my + (e.y / AH) * mh, e.kind === 'core' ? 3 : (e.kind === 'hero' ? 2.5 : 1.5), 0, 2 * PI); g.fill(); }
      g.restore();
      if (S.over) centerBanner(g, vp, S.win ? 'CORE CRACKED -- YOU RULE THE LANE' : 'YOUR CORE FELL -- RUN IT BACK', S.win ? '#6be08a' : '#ff6b6b');
    }

    function pointer(evt) {
      if (!vp) return;                                     // ignore taps before the first frame lays out vp/buttons
      var x = evt.clientX, y = evt.clientY, t = evt.type;
      if (t === 'pointerdown') {
        for (var k in BTN) { var b = BTN[k]; if (hyp(x - b.x, y - b.y) <= b.r + 6) { useSkill(k); return; } }
        if (x < vp.w * 0.5) { inp.mvId = evt.pointerId; inp.mox = x; inp.moy = y; inp.mvx = 0; inp.mvy = 0; }
      } else if (t === 'pointermove') {
        if (evt.pointerId === inp.mvId) { var dx = x - inp.mox, dy = y - inp.moy, m = hyp(dx, dy), cl = Math.min(m, 50) / 50, u = m || 1; inp.mvx = dx / u * cl; inp.mvy = dy / u * cl; }
      } else { if (evt.pointerId === inp.mvId) { inp.mvId = null; inp.mvx = 0; inp.mvy = 0; } }
    }

    if (ctx.showBanner) ctx.showBanner('WORLD MOBA -- push the lane', 1.4);
    api = ctx.overlay.open({
      id: 'mode_world_moba',
      onFrame: function (g, dt, _vp) { if (!S.over) step(dt); else { for (var f = fx.length - 1; f >= 0; f--) { fx[f].life -= dt; if (fx[f].life <= 0) fx.splice(f, 1); } } draw(g, _vp); },
      onPointer: function (evt) { pointer(evt); },
      onClose: function (res) { if (ctx.showBanner && res) ctx.showBanner(res.win ? 'MOBA WON · loot banked' : 'MOBA lost', 1.6); if (opts.onResult) try { opts.onResult(res); } catch (_e) {} }
    });
    return api;
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
    var fighters = {}, bullets = [], S = { t: 0, over: false, win: false };
    var inp = { mvId: null, mox: 0, moy: 0, mvx: 0, mvy: 0, aimId: null, ax: 0, ay: 0, firing: false };
    var vp = null, api = null;
    var TF = { sc: 1, ox: 0, oy: 0 };        // arena<->screen transform (set in draw)

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
      var you = fighters.you, rv = fighters.rv;
      you.fireT -= dt; if (you.hitFx > 0) you.hitFx -= dt; if (rv.hitFx > 0) rv.hitFx -= dt;
      moveF(you, inp.mvx, inp.mvy, dt);
      if (inp.firing && !you.dead) {                       // aim in ARENA coords (inp.ax/ay), light snap to rival
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
        dogChip(g, X(f.x), Y(f.y), (f.r + (f.hitFx > 0 ? 2 : 0)) * sc, fill, k === 'you' ? '#fff' : rarColor(f.rarity), chipLetter(f.name));
        bar(g, X(f.x) - f.r * sc, Y(f.y) - (f.r + 9) * sc, f.r * 2 * sc, 4, f.hp / f.maxHp, f.team === 0 ? '#6be08a' : '#ff6b6b'); });
      drawHUD(g);
    }
    function drawHUD(g) {
      g.save(); g.fillStyle = 'rgba(6,6,12,.82)'; g.fillRect(0, 0, vp.w, 36);
      g.fillStyle = '#ff8a6b'; g.font = '900 13px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText('THE GULAG · 1v1 · win your way back', vp.w / 2, 18); g.restore();
      var you = fighters.you, rv = fighters.rv;
      bar(g, 14, vp.h - 26, 150, 12, you.hp / you.maxHp, '#6be08a');
      g.fillStyle = '#cfe'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle'; g.fillText(you.name, 14, vp.h - 38);
      bar(g, vp.w - 164, 44, 150, 10, rv.hp / rv.maxHp, '#ff6b6b');
      g.fillStyle = '#f9b'; g.textAlign = 'right'; g.fillText(rv.name, vp.w - 14, 56);
      g.save(); g.globalAlpha = .5; g.strokeStyle = '#e8c55a'; g.lineWidth = 1.5; g.beginPath(); g.arc(vp.w - 60, vp.h - 70, 40, 0, 2 * PI); g.stroke();
      g.fillStyle = '#e8c55a'; g.font = '700 10px Inter,sans-serif'; g.textAlign = 'center'; g.fillText('AIM+FIRE', vp.w - 60, vp.h - 70); g.restore();
      if (S.over) centerBanner(g, vp, S.win ? "YOU'RE BACK IN -- GULAG WON" : 'DROPPED IN THE GULAG', S.win ? '#6be08a' : '#ff6b6b');
    }

    function pointer(evt) {
      if (!vp) return;                                     // ignore taps before the first frame lays out vp/transform
      var x = evt.clientX, y = evt.clientY, t = evt.type;
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
      onFrame: function (g, dt, _vp) { if (!S.over) step(dt); draw(g, _vp); },
      onPointer: function (evt) { pointer(evt); },
      onClose: function (res) { if (ctx.showBanner && res) ctx.showBanner(res.win ? 'GULAG WON · back in the fight' : 'GULAG lost', 1.6); if (opts.onResult) try { opts.onResult(res); } catch (_e) {} }
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
        dogChip(g, vp.w / 2, vp.h * 0.32, 38, '#caa84c', rarColor(rar), chipLetter(name));
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

  // Expose the overlay launchers + router so the encounters / raid waves can
  // call them (ctx defaults to window.AK_CTX).
  global.AK_MODES.openWorldMoba  = function (ctx, o) { return openWorldMoba(ctx || global.AK_CTX, o); };
  global.AK_MODES.openGulag      = function (ctx, o) { return openGulag(ctx || global.AK_CTX, o); };
  global.AK_MODES.routeEncounter = routeEncounter;

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
        { label: 'STREET ENCOUNTER', primary: false, onClick: function (c) { routeEncounter({ ctx: c }); } }
      ]
    });
  }

  if (global.AK_SYSTEMS) {
    global.AK_SYSTEMS.register({
      id: 'modes',
      init: function (ctx) { try { ensureFetch(ctx); } catch (_e) {} },   // warm the roster cache; no per-frame work
      onEnterBuilding: function (b, ctx) {
        if (!b || b.id !== 'STREET') return false;                        // claim ONLY THE STREET (contract Section 4)
        renderStreetPicker(ctx, b);
        return true;
      }
    });
  }

})(typeof window !== 'undefined' ? window : globalThis);
