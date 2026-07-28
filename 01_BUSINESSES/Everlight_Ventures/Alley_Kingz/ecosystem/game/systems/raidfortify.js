/* Alley Kingz -- RAID FORTIFICATIONS: WALLS, TRAPS, SPAWN POINTS (window.AK_RAIDFORT)
 * AK-FORT 2026-07-18
 *
 * raidparams.js decides HOW MANY walls and traps a base has (0 walls / 0 traps at TH1 rising to
 * 52 walls / 12 traps at TH10). Nothing built them. This module does.
 *
 * WHAT THIS ADDS
 *   WALLS   a destructible perimeter around the core. They BLOCK you, so a TH10 base is a siege
 *           instead of a jog: you breach, or you find the gap. HP and armor scale by tier, matching
 *           the v2 ladder (chain link -> concrete -> reinforced steel -> blast wall -> composite).
 *   TRAPS   hidden until you touch them, one use each, and each does something different: spike
 *           (slow + bleed), oil (burn over time), emp (kills your abilities for 5s), gas (lingering
 *           area damage), tripwire (no damage, but it CALLS A WAVE EARLY, which is worse).
 *   SPAWNS  wave defenders now enter from the base perimeter near the core instead of appearing at
 *           random screen edges, so a wave reads as the base answering rather than as spawn soup.
 *
 * COLLISION: walls are injected by WRAPPING window.AK_COLLISION.obstaclesFor, the same pattern
 * buildmode.js already uses for placed structures. No host edits, no second physics path, and the
 * wrap removes itself when the raid ends.
 *
 * Everything is guarded and headless-safe; generation is pure so it can be unit-tested.
 */
(function (global) {
  'use strict';

  // ---- wall tiers by Town Hall (v2 ladder) --------------------------------
  var WALL_TIERS = [
    { upTo: 2,  name: 'Chain Link',       hp: 260,  armor: 0,    col: '#8d9099' },
    { upTo: 4,  name: 'Concrete Barrier', hp: 620,  armor: 0.10, col: '#a3a097' },
    { upTo: 6,  name: 'Reinforced Steel', hp: 1400, armor: 0.22, col: '#8f9aa6' },
    { upTo: 8,  name: 'Blast Wall',       hp: 2600, armor: 0.34, col: '#7d8794' },
    { upTo: 10, name: 'Composite',        hp: 4200, armor: 0.45, col: '#6f7e90' }
  ];
  function wallTier(th) {
    for (var i = 0; i < WALL_TIERS.length; i++) if (th <= WALL_TIERS[i].upTo) return WALL_TIERS[i];
    return WALL_TIERS[WALL_TIERS.length - 1];
  }

  // ---- trap kinds ---------------------------------------------------------
  // Each is a different problem, not a different damage number.
  var TRAPS = {
    spike: { name: 'SPIKE STRIP', col: '#c9cdd4', dmg: 55,  slow: 0.45, slowT: 3.0, msg: 'SPIKES -- YOU ARE LIMPING' },
    oil:   { name: 'OIL SLICK',   col: '#ff7a3c', dmg: 30,  dot: 14, dotT: 5.0,     msg: 'YOU ARE BURNING' },
    emp:   { name: 'EMP MINE',    col: '#7fd7ff', dmg: 20,  emp: 5.0,               msg: 'EMP -- ABILITIES DOWN' },
    gas:   { name: 'POISON GAS',  col: '#9be36d', dmg: 15,  dot: 10, dotT: 6.0, area: 90, msg: 'GAS -- GET OUT OF IT' },
    wire:  { name: 'TRIPWIRE',    col: '#e8c55a', dmg: 0,   callWave: true,         msg: 'TRIPWIRE -- THEY KNOW YOU ARE HERE' }
  };
  var TRAP_ORDER = ['spike', 'oil', 'wire', 'emp', 'gas'];   // unlocks as trap budget grows

  function rng(seed) { var s = (seed | 0) || 1; return function () { s = (s * 1664525 + 1013904223) | 0; return ((s >>> 8) & 0xffffff) / 0xffffff; }; }

  /* Build the fortifications for a raid. Pure: give it the params + the core position, get walls,
   * traps and spawn points back. */
  function generate(params, core, seed) {
    var out = { walls: [], traps: [], spawns: [], tier: null };
    try {
      if (!params) return out;
      var R = rng(seed || 1234);
      var th = params.th || 1;
      var tier = wallTier(th);
      out.tier = tier;
      var cx = (core && core.x) || 850, cy = (core && core.y) || 650;

      // WALLS: concentric rings around the core, with deliberate gaps so there is always a way in.
      var n = params.wallCount | 0;
      if (n > 0) {
        var rings = th >= 7 ? 2 : 1, per = Math.ceil(n / rings);
        for (var ring = 0; ring < rings; ring++) {
          var rad = 240 + ring * 150;
          var gapAt = Math.floor(R() * per);                 // one gap per ring: the obvious approach
          for (var i = 0; i < per && out.walls.length < n; i++) {
            if (i === gapAt || i === ((gapAt + 1) % per)) continue;   // 2-segment gap = a real door
            var a = (i / per) * Math.PI * 2;
            out.walls.push({
              x: cx + Math.cos(a) * rad, y: cy + Math.sin(a) * rad,
              w: 54, h: 54, hp: tier.hp, maxHp: tier.hp, armor: tier.armor,
              col: tier.col, name: tier.name, dead: false, ring: ring
            });
          }
        }
      }

      // TRAPS: inside the wall line, hidden until touched. Variety unlocks with the budget.
      var tn = params.trapCount | 0;
      var kinds = TRAP_ORDER.slice(0, Math.max(1, Math.min(TRAP_ORDER.length, Math.ceil(tn / 2))));
      for (var t = 0; t < tn; t++) {
        var ta = R() * Math.PI * 2, tr = 90 + R() * 190;
        out.traps.push({
          x: cx + Math.cos(ta) * tr, y: cy + Math.sin(ta) * tr,
          kind: kinds[t % kinds.length], r: 34, armed: true, seen: false
        });
      }

      // SPAWNS: on the wall ring, so waves walk in from the perimeter of THEIR base.
      var sn = 6;
      for (var s = 0; s < sn; s++) {
        var sa = (s / sn) * Math.PI * 2 + 0.3;
        out.spawns.push({ x: cx + Math.cos(sa) * 430, y: cy + Math.sin(sa) * 430 });
      }
    } catch (_e) {}
    return out;
  }

  // ---- collision wrap -----------------------------------------------------
  // Same trick buildmode.js uses: wrap obstaclesFor so live walls join the obstacle set the movement
  // resolver already consults. Restored on raid end so nothing leaks into the hub.
  var _origObstacles = null;
  function installCollision() {
    try {
      var C = global.AK_COLLISION;
      if (!C || !C.obstaclesFor || _origObstacles) return;
      _origObstacles = C.obstaclesFor;
      C.obstaclesFor = function (zone) {
        var base = [];
        try { base = _origObstacles.call(C, zone) || []; } catch (_e) { base = []; }
        try {
          var r = global.RAID;
          if (r && !r.over && r.fort && r.fort.walls && (r.zi | 0) === 0) {
            var live = [];
            for (var i = 0; i < r.fort.walls.length; i++) {
              var w = r.fort.walls[i];
              if (!w.dead) live.push({ type: 'rect', x: w.x - w.w / 2, y: w.y - w.h / 2, w: w.w, h: w.h });
            }
            if (live.length) return base.concat(live);
          }
        } catch (_e2) {}
        return base;
      };
    } catch (_e) {}
  }
  function removeCollision() {
    try { if (_origObstacles && global.AK_COLLISION) { global.AK_COLLISION.obstaclesFor = _origObstacles; _origObstacles = null; } } catch (_e) {}
  }

  // ---- runtime ------------------------------------------------------------
  function ensure(r) {
    if (!r || r.fort || !r.rp) return;
    var core = r.core || null;
    r.fort = generate(r.rp, core, (r.target && r.target.seed) || 1234);
    installCollision();
    try {
      if (r.fort.walls.length && global.showBanner) {
        global.showBanner(r.fort.tier.name.toUpperCase() + ' PERIMETER -- ' + r.fort.walls.length + ' SEGMENTS', 1.8);
      }
    } catch (_e) {}
  }

  function trigger(r, tp) {
    try {
      var d = TRAPS[tp.kind] || TRAPS.spike;
      tp.armed = false; tp.seen = true; tp.flash = 1;
      if (d.dmg) r.hp = Math.max(0, r.hp - d.dmg);
      if (d.slow) { r.slowT = d.slowT; r.slowMul = d.slow; }
      if (d.dot) { r.dotT = d.dotT; r.dotDps = d.dot; }
      if (d.emp) { r.empT = d.emp; }
      if (d.area) { r.fx = r.fx || []; r.fx.push({ kind: 'hazard', x: tp.x, y: tp.y, r: d.area, life: d.dotT || 5, dps: d.dot || 10 }); }
      if (d.callWave && global.AK_RAIDWAVES && global.AK_RAIDWAVES.spawnWave) {
        var nx = (r._wave | 0) + 1, mx = (r.rp && r.rp.maxWaves) || 5;
        if (nx <= mx) { global.AK_RAIDWAVES.spawnWave(r, nx); r._wave = nx; }
      }
      if (global.showBanner) global.showBanner(d.msg, 1.6);
      if (global.akRaidShake) global.akRaidShake();
    } catch (_e) {}
  }

  function tick(dt) {
    try {
      var r = global.RAID;
      if (!r || r.over) { if (_origObstacles) removeCollision(); return; }
      ensure(r);
      if (!r.fort) return;

      // trap proximity
      var m = global.me;
      if (m && (r.zi | 0) === 0) {
        for (var i = 0; i < r.fort.traps.length; i++) {
          var tp = r.fort.traps[i];
          if (!tp.armed) { if (tp.flash > 0) tp.flash -= dt; continue; }
          if (Math.hypot(m.x - tp.x, m.y - tp.y) < tp.r) trigger(r, tp);
        }
      }
      // BREACHING: push against a wall and you ram it down. Armor bleeds the damage off, so a
      // Composite wall at TH10 is a real commitment while Chain Link goes down in seconds. Without
      // this a wall is just a maze; with it, "breach or find the gap" becomes the actual decision.
      if (m && (r.zi | 0) === 0 && r.fort.walls.length) {
        var moving = Math.hypot(m.vx || 0, m.vy || 0) > 4;
        for (var wi = 0; wi < r.fort.walls.length; wi++) {
          var w = r.fort.walls[wi]; if (w.dead) continue;
          if (Math.abs(m.x - w.x) < w.w / 2 + (m.r || 20) && Math.abs(m.y - w.y) < w.h / 2 + (m.r || 20)) {
            if (!moving) continue;
            var ram = 220 * (1 - (w.armor || 0)) * dt;      // per second, armor-reduced
            w.hp -= ram;
            if (w.hp <= 0) {
              w.dead = true;
              try {
                if (global.showBanner) global.showBanner('BREACHED -- ' + w.name.toUpperCase() + ' DOWN', 1.4);
                if (global.akRaidShake) global.akRaidShake();
                if (global.akRaidDrop) global.akRaidDrop(w.x, w.y, 'stone', 2 + Math.floor(Math.random() * 3));
              } catch (_e3) {}
            }
          }
        }
      }
      // status effects the traps applied
      if (r.slowT > 0) { r.slowT -= dt; if (r.slowT <= 0) r.slowMul = 1; }
      if (r.empT > 0) r.empT -= dt;
      if (r.dotT > 0) { r.dotT -= dt; r.hp = Math.max(0, r.hp - (r.dotDps || 0) * dt); }
    } catch (_e) {}
  }

  function draw() {
    try {
      var r = global.RAID; if (!r || !r.fort) return;
      var C = global.AK_CTX && global.AK_CTX.world; if (!C || !C.g) return;
      if ((r.zi | 0) !== 0) return;
      var g = C.g, t = r.fxT || 0;

      // walls
      for (var i = 0; i < r.fort.walls.length; i++) {
        var w = r.fort.walls[i]; if (w.dead) continue;
        var X = C.wx(w.x), Y = C.wy(w.y);
        if (X < -80 || X > C.W + 80 || Y < -80 || Y > C.H + 80) continue;
        var frac = w.maxHp > 0 ? w.hp / w.maxHp : 1;
        g.save();
        g.fillStyle = 'rgba(0,0,0,.34)';
        g.fillRect(X - w.w / 2 + 3, Y - w.h / 2 + 5, w.w, w.h);
        g.fillStyle = w.col; g.globalAlpha = 0.55 + 0.45 * frac;
        g.fillRect(X - w.w / 2, Y - w.h / 2, w.w, w.h);
        g.globalAlpha = 1;
        g.strokeStyle = 'rgba(0,0,0,.5)'; g.lineWidth = 2;
        g.strokeRect(X - w.w / 2, Y - w.h / 2, w.w, w.h);
        if (frac < 1) {   // damage read
          g.fillStyle = 'rgba(255,80,60,.85)';
          g.fillRect(X - w.w / 2, Y + w.h / 2 - 4, w.w * (1 - frac), 3);
        }
        g.restore();
      }

      // traps: only visible once found, so the first one always costs you
      for (var k = 0; k < r.fort.traps.length; k++) {
        var tp = r.fort.traps[k]; if (!tp.seen) continue;
        var d = TRAPS[tp.kind] || TRAPS.spike;
        var TX = C.wx(tp.x), TY = C.wy(tp.y);
        if (TX < -60 || TX > C.W + 60 || TY < -60 || TY > C.H + 60) continue;
        var pulse = (tp.flash > 0) ? 1 : 0.35 + 0.2 * Math.sin(t * 3 + k);
        g.save();
        g.globalAlpha = pulse;
        g.strokeStyle = d.col; g.lineWidth = 2; g.setLineDash([6, 6]);
        g.beginPath(); g.arc(TX, TY, tp.r, 0, 7); g.stroke(); g.setLineDash([]);
        g.fillStyle = d.col; g.globalAlpha = pulse * 0.18;
        g.beginPath(); g.arc(TX, TY, tp.r, 0, 7); g.fill();
        if (tp.flash > 0) {
          g.globalAlpha = 1; g.fillStyle = d.col; g.font = '800 10px Inter,system-ui';
          g.textAlign = 'center'; g.fillText(d.name, TX, TY - tp.r - 6);
        }
        g.restore();
      }
    } catch (_e) {}
  }

  var api = {
    id: 'raidfortify',
    init: function () {},
    onTick: function (dt) { try { tick(dt || 0); } catch (_e) {} },
    onDrawWorld: function () { try { draw(); } catch (_e) {} }
  };
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(api); } catch (_e) {}

  global.AK_RAIDFORT = {
    WALL_TIERS: WALL_TIERS, TRAPS: TRAPS, TRAP_ORDER: TRAP_ORDER,
    wallTier: wallTier, generate: generate, trigger: trigger,
    installCollision: installCollision, removeCollision: removeCollision,
    _tick: tick, _draw: draw
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_RAIDFORT;
})(typeof window !== 'undefined' ? window : this);
