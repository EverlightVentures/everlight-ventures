/* Alley Kingz -- RAID WAVES, BOSS MECHANICS + EXTRACTION (window.AK_RAIDWAVES)
 * AK-WAVES 2026-07-18 / AK-RAIDV2
 *
 * A raid is not "clear the board". It is an EXTRACTION raid: the base keeps answering in escalating
 * waves until the clock runs out, loot is CARRIED rather than banked, and getting OUT is the win
 * condition. Dying does not just cost you the fight, it costs you the haul.
 *
 * THIS FILE OWNS
 *   - the wave clock: when each wave lands, driven by the defender's real difficulty profile
 *   - the boss: 5 mechanic tiers gated by the defender's watcher rarity
 *   - the extraction ruleset: what you keep depending on how you left
 *
 * COMPOSITION LIVES IN raidparams.js, NOT HERE. That module decides how many waves, who is in them,
 * how hard they hit, the trap/wall/map budget and the loot ceiling, all derived from the DEFENDER's
 * Town Hall, card levels and watcher rarity. It is pure and headless so it can run unchanged on a
 * server tick. This file is the runtime that acts on that plan.
 *
 * BOSS TIERS (rarity gates the ceiling, per the v2 spec)
 *   1 brute     3x hp, no mechanics
 *   2 summoner  + minion spawns
 *   3 phased    + phase shift at 50% (faster, hits harder)
 *   4 warlord   + environmental hazards
 *   5 kingz     + rage at 25% and invulnerability windows   (Mythic only)
 *
 * Everything is guarded: a missing RAID, missing params or missing econ is a no-op, and nothing
 * here may throw inside the frame loop.
 */
(function (global) {
  'use strict';
  var ID = 'raidwaves';

  function R() { return global.RAID || null; }
  function P() { var r = R(); return (r && r.rp) || null; }

  // ---- wave clock ---------------------------------------------------------
  // RAID.t counts DOWN. Wave cadence comes from the difficulty profile (raidSeconds / maxWaves), so
  // a TH1 street fight and a TH10 siege both pace correctly instead of sharing one constant.
  function elapsed(r) {
    if (typeof r._wStart !== 'number') r._wStart = (typeof r.t === 'number') ? r.t : 90;
    return Math.max(0, r._wStart - (r.t || 0));
  }
  function cadence(p) {
    if (p && p.waveIntervalSec > 0) return p.waveIntervalSec;
    return 20;
  }
  function dueWave(r, p) {
    var iv = cadence(p), lead = Math.min(8, Math.round(iv * 0.25));
    var e = elapsed(r);
    if (e < lead) return 0;
    var n = Math.floor((e - lead) / iv) + 1;
    var max = (p && p.maxWaves) || 5;
    return Math.min(n, max);
  }

  // ---- spawning from the real plan ---------------------------------------
  // Units are materialised in the EXACT shape index.html already creates for defenders, so the
  // existing step/draw/collision paths pick them up with no host changes.
  function toEntity(u, r, extra) {
    var W = global.WORLD_W || 1700, H = global.WORLD_H || 1300;
    var x, y;
    // Prefer the base's own perimeter spawn points (raidfortify places them on the wall ring), so a
    // wave reads as THEIR BASE answering. Random screen edges made waves look like spawn soup.
    var sp = (r.fort && r.fort.spawns && r.fort.spawns.length) ? r.fort.spawns : null;
    if (sp) {
      var s = sp[Math.floor(Math.random() * sp.length)];
      x = s.x + (Math.random() * 60 - 30); y = s.y + (Math.random() * 60 - 30);
    } else {
      var side = Math.floor(Math.random() * 4), pad = 90;
      if (side === 0) { x = Math.random() * W; y = -pad; }
      else if (side === 1) { x = W + pad; y = Math.random() * H; }
      else if (side === 2) { x = Math.random() * W; y = H + pad; }
      else { x = -pad; y = Math.random() * H; }
    }
    var e = {
      x: x, y: y, hx: x, hy: y, zi: r.zi | 0, r: 18,
      hp: u.hp, maxHp: u.hp, spd: 88, atkT: 0, wind: 0, rwind: 0,
      ranged: (u.role === 'watcher'), name: u.name, dead: false,
      lvl: u.level, rarity: u.rarity, role: u.role
    };
    if (extra) for (var k in extra) e[k] = extra[k];
    return e;
  }

  function spawnWave(r, n) {
    var p = P();
    var plan = r._plan;
    if (!plan) {
      try {
        if (global.AK_RAIDPARAMS && r._defProfile) {
          var cbn = {}; var L = global.CANON_CARDS || [];
          for (var i = 0; i < L.length; i++) cbn[L[i].name] = L[i];
          plan = r._plan = global.AK_RAIDPARAMS.planWaves(r._defProfile, cbn, p);
        }
      } catch (_e) {}
    }
    var w = plan && plan[n - 1];
    var spawned = 0;

    if (w && w.units && w.units.length) {
      for (var u = 0; u < w.units.length; u++) { r.defenders.push(toEntity(w.units[u], r)); spawned++; }
      if (w.boss) spawnBoss(r, w, p);
    } else {
      // fallback: no plan (generated target with no roster) -> scale off the tier so a raid is
      // never silently empty
      var tier = (r.target && (r.target.tier | 0)) || 1;
      var cnt = Math.min(10, 3 + n);
      for (var q = 0; q < cnt; q++) {
        var hp = Math.round((220 + tier * 24) * (1 + 0.22 * (n - 1)));
        r.defenders.push(toEntity({ name: 'Watchdog', hp: hp, level: tier, rarity: 'Common', role: 'lieutenant' }, r));
        spawned++;
      }
      if (p && n >= (p.maxWaves || 5)) spawnBoss(r, { bossTier: p.bossTier || 1 }, p);
    }

    r._wave = n;
    try {
      if (global.showBanner) global.showBanner('WAVE ' + n + (w && w.boss ? ' -- THE KINGZ STAND' : ' INBOUND -- ' + spawned + ' ON YOU'), 1.8);
      if (global.akRaidShake) global.akRaidShake();
    } catch (_e) {}
    return spawned;
  }

  // ---- the boss -----------------------------------------------------------
  function spawnBoss(r, w, p) {
    try {
      if (r._boss) return;
      var tier = (w && w.bossTier) || (p && p.bossTier) || 1;
      var lead = (w && w.units && w.units.length) ? w.units[w.units.length - 1] : null;
      var base = lead ? lead.hp : 2500;
      var b = toEntity({
        name: (lead && lead.name) || 'THE WARDEN',
        hp: Math.round(base * 3),                       // every tier is at least 3x hp
        level: (lead && lead.level) || 1,
        rarity: (p && p.watcherRarity) || 'Common',
        role: 'boss'
      }, r, { boss: true, tier: tier, phase: 1, rage: false, invuln: false, _mt: 0, _ht: 0, _it: 0 });
      b.r = 26; b.spd = 76;
      r.defenders.push(b);
      r._boss = b;
      if (global.showBanner) global.showBanner('BOSS: ' + b.name.toUpperCase() + '  [' + ((p && p.bossType) || 'brute').toUpperCase() + ']', 2.2);
    } catch (_e) {}
  }

  // Boss behaviour, ticked each frame. Each tier stacks on the one below it.
  function stepBoss(r, dt) {
    var b = r._boss;
    if (!b || b.dead) return;
    var frac = b.maxHp > 0 ? (b.hp / b.maxHp) : 1;

    // tier 2+: keep calling bodies in
    if (b.tier >= 2) {
      b._mt += dt;
      if (b._mt >= 30) {
        b._mt = 0;
        var n = 2 + (b.tier >= 4 ? 1 : 0);
        for (var i = 0; i < n; i++) {
          r.defenders.push(toEntity({ name: 'Runner', hp: Math.round(b.maxHp * 0.06), level: b.lvl, rarity: 'Common', role: 'minion' }, r));
        }
        if (global.showBanner) global.showBanner(b.name.toUpperCase() + ' CALLS IN BLOOD', 1.2);
      }
    }
    // tier 3+: phase shift at 50%
    if (b.tier >= 3 && b.phase === 1 && frac <= 0.5) {
      b.phase = 2; b.spd = Math.round(b.spd * 1.3);
      if (global.showBanner) global.showBanner(b.name.toUpperCase() + ' SHIFTS -- HE STOPS PLAYING', 1.6);
      if (global.akRaidShake) global.akRaidShake();
    }
    // tier 4+: environmental hazards
    if (b.tier >= 4) {
      b._ht += dt;
      if (b._ht >= 12) {
        b._ht = 0;
        try {
          r.fx = r.fx || [];
          r.fx.push({ kind: 'hazard', x: b.x + (Math.random() * 240 - 120), y: b.y + (Math.random() * 240 - 120), r: 70, life: 5, dps: Math.round(b.maxHp * 0.004) });
          if (global.showBanner) global.showBanner('THE BLOCK TURNS ON YOU', 1.1);
        } catch (_e) {}
      }
    }
    // tier 5 (Mythic only): rage at 25% + invulnerability windows
    if (b.tier >= 5) {
      if (!b.rage && frac <= 0.25) {
        b.rage = true; b.spd = Math.round(b.spd * 2); b._dmgMul = 2;
        if (global.showBanner) global.showBanner(b.name.toUpperCase() + ' IS RAGING -- BACK OFF', 2.0);
        if (global.akRaidShake) global.akRaidShake();
      }
      b._it += dt;
      if (!b.invuln && b._it >= 10) { b.invuln = true; b._it = 0; }
      else if (b.invuln && b._it >= 2) { b.invuln = false; b._it = 0; }
    }
  }

  // ---- hazards: age them, and make them actually HURT ---------------------
  // Caught in review: the raid draw loop never iterates RAID.fx, so hazards pushed there were
  // invisible AND harmless -- a silent no-op. This module owns them end to end instead: it ages
  // them here, damages the player standing in one, and paints them in onDrawWorld below.
  function stepHazards(r, dt) {
    if (!r.fx || !r.fx.length) return;
    for (var i = r.fx.length - 1; i >= 0; i--) {
      var f = r.fx[i];
      if (!f || f.kind !== 'hazard') continue;
      f.life -= dt;
      if (f.life <= 0) { r.fx.splice(i, 1); continue; }
      try {
        var m = global.me;
        if (m && Math.hypot(m.x - f.x, m.y - f.y) < f.r) {
          r.hp = Math.max(0, r.hp - (f.dps || 8) * dt);
          if (global.akRaidShake && Math.random() < 0.04) global.akRaidShake();
        }
      } catch (_e) {}
    }
  }

  function drawHazards() {
    try {
      var r = R(); if (!r || !r.fx || !r.fx.length) return;
      var C = global.AK_CTX && global.AK_CTX.world; if (!C || !C.g) return;
      var g = C.g;
      for (var i = 0; i < r.fx.length; i++) {
        var f = r.fx[i]; if (!f || f.kind !== 'hazard') continue;
        var X = C.wx(f.x), Y = C.wy(f.y);
        var pulse = 0.55 + 0.45 * Math.sin((r.fxT || 0) * 6 + i);
        g.save();
        g.globalAlpha = Math.min(1, f.life / 5) * 0.5;
        g.fillStyle = 'rgba(255,86,48,' + (0.22 * pulse).toFixed(3) + ')';
        g.beginPath(); g.arc(X, Y, f.r, 0, 7); g.fill();
        g.globalAlpha = Math.min(1, f.life / 5);
        g.strokeStyle = 'rgba(255,120,60,' + (0.5 + 0.4 * pulse).toFixed(3) + ')';
        g.lineWidth = 3; g.setLineDash([10, 8]); g.lineDashOffset = -(r.fxT || 0) * 30;
        g.beginPath(); g.arc(X, Y, f.r, 0, 7); g.stroke(); g.setLineDash([]);
        g.restore();
      }
    } catch (_e) {}
  }

  function tick(dt) {
    var r = R();
    if (!r || r.over || !Array.isArray(r.defenders)) return;
    var p = P();
    var want = dueWave(r, p);
    if (want > 0 && want > (r._wave | 0)) spawnWave(r, want);
    stepBoss(r, dt);
    stepHazards(r, dt);
  }

  // ---- extraction ---------------------------------------------------------
  var OUTCOME = { EXTRACT: 'extract', SURRENDER: 'surrender', TIMEOUT: 'timeout', WIPE: 'wipe' };
  var KEEP = { extract: 1, surrender: 0.5, timeout: 0.5, wipe: 0 };
  function keepFraction(o) { return (typeof KEEP[o] === 'number') ? KEEP[o] : 0; }
  function keepsBag(o) { return keepFraction(o) > 0; }

  // Move the carried bag into the secured pool. Called when the player stands in the extraction
  // zone: secured loot can NEVER be lost, which is what makes a mid-raid run back meaningful.
  function secure(r) {
    r = r || R();
    var moved = 0;
    try {
      if (!r || !r.bag) return 0;
      r.secured = r.secured || {};
      for (var k in r.bag) {
        var v = r.bag[k] | 0; if (v <= 0) continue;
        r.secured[k] = (r.secured[k] | 0) + v; r.bag[k] = 0; moved += v;
      }
      if (moved > 0 && global.showBanner) global.showBanner('HAUL SECURED -- ' + moved + ' BANKED', 1.4);
    } catch (_e) {}
    return moved;
  }

  // Spill what did not make it out. Not destroyed: dropped, so a later run can reclaim it.
  function spillBag(r) {
    try {
      if (!r || !r.bag || !global.akRaidDrop) return 0;
      var px = (global.me && global.me.x) || 0, py = (global.me && global.me.y) || 0, n = 0;
      for (var k in r.bag) {
        var amt = r.bag[k] | 0; if (amt <= 0) continue;
        global.akRaidDrop(px + (Math.random() * 60 - 30), py + (Math.random() * 60 - 30), k, amt); n++;
      }
      r.bag = {};
      return n;
    } catch (_e) { return 0; }
  }

  function downSquad(r) {
    try {
      var INF = global.AK_INFIRMARY; if (!INF || !INF.downCard) return 0;
      var squad = (r && r.squad) || [];
      if (!squad.length && global.heroCard) { var h = global.heroCard(); if (h) squad = [h.name || h.id]; }
      var n = 0;
      for (var i = 0; i < squad.length; i++) { try { INF.downCard(squad[i]); n++; } catch (_e2) {} }
      return n;
    } catch (_e) { return 0; }
  }

  function resolve(outcome) {
    var r = R(), res = { outcome: outcome, kept: 0, spilled: 0, downed: 0 };
    try {
      if (!r) return res;
      var f = keepFraction(outcome);
      res.kept = f;
      if (f < 1) res.spilled = spillBag(r);
      if (outcome !== OUTCOME.EXTRACT) res.downed = downSquad(r);
    } catch (_e) {}
    return res;
  }

  var api = {
    id: ID,
    init: function () {},
    onTick: function (dt) { try { tick(dt); } catch (_e) {} },
    onDrawWorld: function () { try { drawHazards(); } catch (_e) {} }
  };
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(api); } catch (_e) {}

  global.AK_RAIDWAVES = {
    OUTCOME: OUTCOME, KEEP: KEEP,
    resolve: resolve, keepsBag: keepsBag, keepFraction: keepFraction,
    secure: secure, spillBag: spillBag, downSquad: downSquad,
    spawnWave: spawnWave, spawnBoss: spawnBoss, stepBoss: stepBoss,
    dueWave: dueWave, cadence: cadence,
    wave: function () { var r = R(); return r ? (r._wave | 0) : 0; },
    boss: function () { var r = R(); return r ? r._boss : null; },
    _tick: tick
  };
})(typeof window !== 'undefined' ? window : this);
