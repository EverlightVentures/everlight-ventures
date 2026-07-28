/* game/systems/worldverbs.js -- AK_SYSTEMS module: WORLD VERBS / HARVEST LAYER.
 *
 * THE EARN-HALF OF THE CLASH-OF-CLANS LOOP, rebuilt to AK_RESOURCE_ECONOMY_DESIGN
 * (secs 3, 4, 8). buildmode.js SPENDS wood/stone/metal; this module lets you EARN
 * them by WORKING the street -- and working now means TOOLS + TIME, not a free grab:
 *
 *  - TOOL-GATED (sec 3): T0 "Bare Paws" CANNOT work any node. Each node sets a
 *    minimum tool TIER + a tool TYPE (Axe=wood, Pickaxe=stone, Crowbar=scrap/metal,
 *    Drill=rare metal). Walk up with too low a tier and you get "NEED A BETTER
 *    {TOOL}". Tools live in the profile (p.tools via AK_ECON, falsy-default {});
 *    durability decrements per completed harvest and a broken tier falls back to
 *    the next owned tier. The tool LADDER + state helpers are owned by economy.js
 *    (AK_ECON.toolFor / buyTool / spendDurability / TOOL_TIERS) -- the single
 *    source of truth; this module only READS the gate + SPENDS durability. A small
 *    internal mirror keeps the gate alive in a headless harness with no AK_ECON.
 *
 *  - TWO CLOCKS (sec 4):
 *      (A) GATHER CHANNEL -- tapping a ripe node starts a timed channel of
 *          effective_seconds = base_channel x toolTimeMult x (1 / builderSpeed).
 *          The dog WORKS (gold progress ring, alpha-only, no shadowBlur); the
 *          harvest lands ONLY when the channel finishes (driven by accumulated dt
 *          in onTick, so it is deterministic + headless-drivable).
 *      (B) NODE RESPAWN -- on harvest the node depletes and regrows over the node
 *          table's respawn window (8 min small / ~25 min mid / 45-90 min rare),
 *          stepping growthStage 0->1->2->3 (the existing drawNode depletion art).
 *          State persists in p.nodes (falsy-default; {zoneId:{key:{r,d}}}).
 *
 *  - PATTERNED PLACEMENT (sec 8): each district draws its nodes to a PATTERN
 *    (orchard rows / rubble grid / boulevard clusters / scrap field / pipe runs /
 *    perimeter ring / quay line) using themed node families, biased per district,
 *    seeded deterministically, and still run through ALL the original clearance
 *    filters (doors / plaza / corridor spines / edges / debris / min-spacing).
 *
 * onDrawWorld renders each node as a gritty gold-cyberpunk Canvas2D vector sprite
 * (or the wv_*.png sprite when ripe + loaded) whose growthStage shows depletion;
 * the channeling node gets a filling gold arc. Off-screen nodes are culled. NO
 * shadowBlur in the per-frame loop. prefers-reduced-motion drops the idle pulse.
 *
 * HOST HOOKS (additive; no edits to engine.js / the draw loop):
 *   1. index.html already loads  <script src="systems/worldverbs.js?v=N"></script>
 *      after economy.js + the other systems. worldverbs EARNS the wood/stone/metal
 *      buildmode SPENDS, and READS AK_ECON tool state.
 *   2. economy.js ensureShape falsy-defaults  p.wood/p.stone/p.metal (shared with
 *      buildmode), p.nodes (depletion), p.tools (AK-TOOLS). A fresh profile stays
 *      byte-identical until the first harvest / tool buy writes an entry.
 *   3. Collision: harvest nodes are NON-solid (you walk up + tap). This module
 *      never feeds AK_COLLISION; it only READS AK_COLLISION.OBSTACLES at gen-time
 *      to keep nodes off fences / cars / rubble.
 *
 * Headless-safe: bails if no AK_SYSTEMS; no top-level DOM/localStorage; the DOM
 * prompt mounts lazily inside init() (guarded by typeof document). Loads in the
 * node harness beside the other modules with zero conflict; all state goes through
 * AK_ECON.mutateProfile.
 */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;                 // hub-only module (battler / bare pages skip it)

  var GOLD = '#e8c55a', GOLD_DK = '#c9a84c';
  var HARVEST_RANGE = 80;                         // tap-prompt proximity (world units ~ px)
  var PICKUP_RANGE = 36;                          // AK-DROPS: walk within this (world units) of a ground drop to bank it
  var DROP_TTL = 90000;                           // AK-DROPS: ms a drop lingers before it despawns (the "someone else grabbed it" fiction)
  var MIN = 60000;                                // ms per minute (respawn table)

  /* ---------------------------------------------------------------------- *
   * NODE CATALOG (AK_RESOURCE_ECONOMY_DESIGN sec 4.3 -- the number table)
   *   mat:'wood'|'stone'|'metal' = flat profile currencies (shared w/ buildmode);
   *        'scrap' = the EXISTING rarity-keyed pocket (rar names the rarity).
   *   alt:    a second yield line (Wreck = metal + scrap).
   *   tool:   which tool TYPE works it (axe/pickaxe/crowbar/drill).
   *   minTier:minimum tool tier required (1..4) -- below it: "NEED A BETTER {TOOL}".
   *   channel:base ACTIVE seconds to work it (clock A; scaled by tool + builder).
   *   amount: base yield (exact -- the tool tier supplies the bonus).
   *   dur:    respawn window in ms (clock B; small 8-12 min, mid ~25-35, rare 45-90).
   *   draw:   the vector family (TREE/ROCK/SCRAP/PIPE); big = size multiplier.
   *   sprite: ripe-node PNG -- the in-world draw AND the HARVEST-prompt icon.
   *   glyph:  LAST-RESORT emoji fallback ONLY (de-emojified 2026-06-26). The live
   *           UI uses the sprite when loaded, else a clean mat-tinted CSS chip;
   *           this field renders nowhere in the normal path now.
   * ---------------------------------------------------------------------- */
  var NODE_TYPES = {
    BRUSHWOOD: { mat: 'wood',  tool: 'axe',     minTier: 1, channel: 6,  amount: 8,  dur: 8 * MIN,  draw: 'TREE',  big: 0.85, glyph: '🪵', label: 'WOOD',  sprite: 'assets/sprites/wv_tree.png'  },
    HARDWOOD:  { mat: 'wood',  tool: 'axe',     minTier: 2, channel: 16, amount: 22, dur: 25 * MIN, draw: 'TREE',  big: 1.30, glyph: '🪵', label: 'WOOD',  sprite: 'assets/sprites/wv_tree.png'  },
    RUBBLE:    { mat: 'stone', tool: 'pickaxe', minTier: 1, channel: 8,  amount: 8,  dur: 12 * MIN, draw: 'ROCK',  big: 0.85, glyph: '🪨', label: 'STONE', sprite: 'assets/sprites/wv_rock.png'  },
    BOULDER:   { mat: 'stone', tool: 'pickaxe', minTier: 2, channel: 18, amount: 24, dur: 35 * MIN, draw: 'ROCK',  big: 1.35, glyph: '🪨', label: 'STONE', sprite: 'assets/sprites/wv_rock.png'  },
    SCRAP:     { mat: 'scrap', rar: 'Common', tool: 'crowbar', minTier: 1, channel: 7,  amount: 12, dur: 10 * MIN, draw: 'SCRAP', big: 1.00, glyph: '⚙️', label: 'SCRAP', sprite: 'assets/sprites/wv_scrap.png' },
    WRECK:     { mat: 'metal', alt: { mat: 'scrap', rar: 'Common', amount: 6 }, tool: 'crowbar', minTier: 2, channel: 16, amount: 5, dur: 30 * MIN, draw: 'SCRAP', big: 1.35, glyph: '🔩', label: 'METAL', sprite: 'assets/sprites/wv_scrap.png' },
    PIPE:      { mat: 'metal', tool: 'crowbar', minTier: 3, channel: 14, amount: 5,  dur: 45 * MIN, draw: 'PIPE',  big: 1.00, glyph: '🔩', label: 'METAL', sprite: 'assets/sprites/wv_pipe.png'  },
    RAREVEIN:  { mat: 'metal', tool: 'drill',  minTier: 4, channel: 28, amount: 10, dur: 90 * MIN, draw: 'PIPE',  big: 1.45, jackpot: true, contested: true, glyph: '💠', label: 'METAL', sprite: 'assets/sprites/wv_pipe.png' }
  };

  // Internal tool-tier MIRROR -- canonical = AK_ECON.TOOL_TIERS. Used ONLY when a
  // headless harness loads worldverbs without economy.js (the gate must still work).
  var TOOL_TIERS_MIRROR = [
    { tier: 0, timeMult: 1.00, bonusLoot: 0.00, rareDrop: 0.00, durability: Infinity },
    { tier: 1, timeMult: 1.00, bonusLoot: 0.00, rareDrop: 0.00, durability: 25 },
    { tier: 2, timeMult: 0.74, bonusLoot: 0.15, rareDrop: 0.05, durability: 60 },
    { tier: 3, timeMult: 0.56, bonusLoot: 0.30, rareDrop: 0.10, durability: 120 },
    { tier: 4, timeMult: 0.40, bonusLoot: 0.50, rareDrop: 0.18, durability: 240 }
  ];

  /* AK-NODEART: lazy image cache for the RIPE harvest-node sprite. Headless-safe
   * (no Image() in node -> spriteImg() returns null -> drawNode uses the procedural
   * vector). A 404/decode marks the path dead. Depleted stages (0-2) ALWAYS use the
   * procedural draw so the stump/rubble depletion feedback is preserved. */
  var _imgCache = {};
  function spriteImg(path) {
    if (!path || typeof Image === 'undefined') return null;
    var im = _imgCache[path];
    if (im === undefined) { im = new Image(); im.onerror = function () { _imgCache[path] = null; }; im.src = path; _imgCache[path] = im; }
    return im;
  }
  function spriteReady(im) { return !!(im && im.complete && im.naturalWidth > 0); }

  /* ---------------------------------------------------------------------- *
   * PLACEMENT PATTERNS (sec 8) -- each live district reads as a PLACE, not noise.
   * PATTERN[zoneId] = { shape, nodes[], count }. Unlisted zones fall back to
   * GROUND_BIAS + 'scatter'. Generators emit CANDIDATE points; the existing
   * clearance filters then run, so placement stays legal.
   * ---------------------------------------------------------------------- */
  var PATTERN = {
    HOME_TURF:    { shape: 'rows',    nodes: ['BRUSHWOOD', 'BRUSHWOOD', 'HARDWOOD'],            count: 6 },   // orchard rows, low (safe home yard)
    DOWNTOWN:     { shape: 'grid',    nodes: ['RUBBLE', 'RUBBLE', 'BOULDER'],                   count: 9 },   // rubble grid, med (teardown lot)
    NEON_HEIGHTS: { shape: 'cluster', nodes: ['RUBBLE', 'BRUSHWOOD', 'RUBBLE', 'BOULDER'],      count: 8 },   // boulevard clumps, med
    THE_YARDS:    { shape: 'scatter', nodes: ['SCRAP', 'SCRAP', 'WRECK'],                       count: 12 },  // scrap field, high (junkyard rows)
    FACTORY_ROW:  { shape: 'line',    nodes: ['PIPE', 'WRECK', 'PIPE'],                         count: 10 },  // pipe runs, med-high
    THE_STRIP:    { shape: 'ring',    nodes: ['SCRAP', 'RUBBLE'],                               count: 9 },   // perimeter ring, med (open center)
    THE_DOCKS:    { shape: 'quay',    nodes: ['PIPE', 'WRECK', 'PIPE', 'WRECK', 'RAREVEIN'],    count: 11 }   // quay line, high (metal-rich top faucet + rare veins)
  };
  var RARE_CAP = 2;                                  // Rare veins per zone (the top of the supply curve)

  // per-ground fallback for any zone NOT in PATTERN (locked / future zones).
  var GROUND_BIAS = {
    uptown:  ['BRUSHWOOD', 'BRUSHWOOD', 'HARDWOOD', 'RUBBLE', 'SCRAP'],
    midtown: ['RUBBLE', 'RUBBLE', 'BOULDER', 'BRUSHWOOD', 'SCRAP'],
    docks:   ['SCRAP', 'SCRAP', 'WRECK', 'PIPE', 'RUBBLE'],
    _def:    ['BRUSHWOOD', 'RUBBLE', 'SCRAP', 'PIPE']
  };

  // Candidate-point generators. (WW,WH)=world bounds, (cx,cy)=centre plaza, rng, n=target count.
  var GENERATORS = {
    rows: function (WW, WH, cx, cy, rng, n) {          // orchard rows flanking the plaza
      var pts = [], cols = [WW * 0.24, WW * 0.76], per = Math.ceil(n / 2) + 3;
      for (var c = 0; c < cols.length; c++) for (var i = 0; i < per; i++) {
        pts.push({ x: cols[c] + (rng() - 0.5) * 36, y: 170 + (WH - 340) * (i / (per - 1)) });
      }
      return pts;
    },
    grid: function (WW, WH, cx, cy, rng) {             // lattice in the interior
      var pts = [], cols = 4, rowsN = 4;
      for (var r = 0; r < rowsN; r++) for (var c = 0; c < cols; c++) {
        pts.push({ x: WW * (0.18 + 0.64 * (c / (cols - 1))) + (rng() - 0.5) * 30,
                   y: WH * (0.18 + 0.64 * (r / (rowsN - 1))) + (rng() - 0.5) * 30 });
      }
      return pts;
    },
    cluster: function (WW, WH, cx, cy, rng) {          // boulevard clumps
      var pts = [], clusters = 3;
      for (var k = 0; k < clusters; k++) {
        var ccx = WW * (0.20 + 0.6 * rng()), ccy = WH * (0.20 + 0.6 * rng()), m = 3 + Math.floor(rng() * 3);
        for (var i = 0; i < m; i++) pts.push({ x: ccx + (rng() - 0.5) * 150, y: ccy + (rng() - 0.5) * 150 });
      }
      return pts;
    },
    scatter: function (WW, WH, cx, cy, rng) {          // staggered heaps (junkyard) / fallback
      var pts = [], cols = 5, rowsN = 4;
      for (var r = 0; r < rowsN; r++) for (var c = 0; c < cols; c++) {
        var off = (r % 2) ? (WW * 0.64 / (cols - 1)) / 2 : 0;
        pts.push({ x: WW * 0.18 + (WW * 0.64) * (c / (cols - 1)) + off + (rng() - 0.5) * 28,
                   y: WH * 0.16 + (WH * 0.68) * (r / (rowsN - 1)) + (rng() - 0.5) * 28 });
      }
      return pts;
    },
    line: function (WW, WH, cx, cy, rng, n) {          // straight pipe runs along walls
      var pts = [], runs = [WH * 0.22, WH * 0.74], per = Math.ceil(n / 2) + 3;
      for (var r = 0; r < runs.length; r++) for (var i = 0; i < per; i++) {
        pts.push({ x: 170 + (WW - 340) * (i / (per - 1)), y: runs[r] + (rng() - 0.5) * 24 });
      }
      return pts;
    },
    ring: function (WW, WH, cx, cy, rng, n) {          // perimeter ring (open center)
      var pts = [], total = n + 8, rx = WW * 0.40, ry = WH * 0.40;
      for (var i = 0; i < total; i++) {
        var a = (i / total) * Math.PI * 2;
        pts.push({ x: cx + Math.cos(a) * rx + (rng() - 0.5) * 26, y: cy + Math.sin(a) * ry + (rng() - 0.5) * 26 });
      }
      return pts;
    },
    quay: function (WW, WH, cx, cy, rng, n) {          // single row along the water edge + a short stub
      var pts = [], y0 = WH * 0.82, per = n + 5;
      for (var i = 0; i < per; i++) pts.push({ x: 165 + (WW - 330) * (i / (per - 1)), y: y0 + (rng() - 0.5) * 22 });
      for (var j = 0; j < 3; j++) pts.push({ x: WW * (0.3 + 0.4 * (j / 2)), y: WH * 0.6 + (rng() - 0.5) * 24 });
      return pts;
    }
  };

  /* ---------------------------------------------------------------------- *
   * MODULE STATE (no DOM here)
   * ---------------------------------------------------------------------- */
  var WV = {
    ctx: null, btn: null, btn2: null, btnIc: null, btnTx: null, row: null, clock: 0, sweepT: 0, reduce: false,
    gen: {},                       // zoneId -> [node]   (deterministic; cached)
    nearKey: null,                 // node under the prompt right now
    channel: null,                 // active gather channel { zid, key, elapsed, dur, node }
    drops: [],                     // AK-DROPS: ground drops from MANUAL harvest { zid,x,y,type,mat,rar,amount,alt,rareScrap,born } (session-only, ephemeral)
    jobs: [],                      // AK-DISPATCH: active dispatched-builder harvests (persist to p.fieldJobs)
    upDogs: [],                    // AK-UPGRADEDOG: VISIBLE builder dogs for BUILDING upgrades (cosmetic; index.html pushes via showUpgradeDog) { zid,nx,ny,hx,hy,t0,work,until,art,name }
    jobsLoaded: false,
    last: null,                    // AK-HARVESTAPI: structured outcome of the most recent doHarvest (see rec/harvestInfo)
    ver: 0, _p: null, _pv: -1      // ver-cached profile read for NODE state (p.nodes changes only through us)
  };
  var coll = null;

  function freshProfile() { try { return WV.ctx && WV.ctx.econ ? WV.ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function prof() { if (WV._pv !== WV.ver || !WV._p) { WV._p = freshProfile(); WV._pv = WV.ver; } return WV._p; }
  function bump() { WV.ver++; }

  /* ====================================================================== *
   * TOOL GATE / TIMING (reads AK_ECON; internal mirror for headless)
   * ====================================================================== */
  function tierDef(tier) {
    var E = global.AK_ECON;
    if (E && E.TOOL_TIERS && E.TOOL_TIERS[tier]) return E.TOOL_TIERS[tier];
    return TOOL_TIERS_MIRROR[Math.max(0, Math.min(4, tier | 0))];
  }
  // Equipped tool for a type -> {tier,def}. Prefers AK_ECON.toolFor; internal
  // fallback reads p.tools directly so the gate works without AK_ECON helpers.
  function toolForP(p, type) {
    var E = global.AK_ECON;
    if (E && typeof E.toolFor === 'function') { try { return E.toolFor(p, type); } catch (_) {} }
    var t = (p && p.tools && p.tools[type]) || null;
    var tier = t ? Math.max(0, Math.min(4, t.tier | 0)) : 0;
    var def = tierDef(tier);
    return { type: type, tier: tier, def: def, timeMult: def.timeMult, bonusLoot: def.bonusLoot, rareDrop: def.rareDrop };
  }
  function spendDur(type, n) {
    if (n <= 0) return;
    var E = global.AK_ECON;
    if (E && typeof E.spendDurability === 'function') { try { E.spendDurability(type, n); return; } catch (_) {} }
    if (!WV.ctx || !WV.ctx.econ) return;             // internal fallback (mirrors economy.js break logic)
    WV.ctx.econ.mutateProfile(function (p) {
      var t = p.tools && p.tools[type]; if (!t) return;
      var def = tierDef(t.tier); if (def.durability === Infinity) return;
      t.dur = (t.dur | 0) - n;
      while (t.dur <= 0) {
        var owned = (Array.isArray(t.owned) && t.owned.length) ? t.owned.slice().sort(function (a, b) { return a - b; }) : [t.tier];
        var idx = owned.indexOf(t.tier);
        if (idx > 0) { t.tier = owned[idx - 1]; t.dur = tierDef(t.tier).durability; }
        else { t.dur = tierDef(t.tier).durability; break; }
      }
    });
  }
  // The skill<->time lever. Manual channel uses the player's lead card (resolved by
  // crew.js); here we feed lvl 1 so the Town Hall still speeds work -- parity-safe
  // (TH is earned, never a gem unlock). builderSpeed >= 1 always.
  function builderSpeedNow() {
    var E = global.AK_ECON;
    if (E && typeof E.builderSpeed === 'function') {
      try { var p = prof(); return E.builderSpeed(1, (p && p.townHall) || 1) || 1; } catch (_) {}
    }
    return 1;
  }
  function toolLabel(type) { return String(type || 'TOOL').toUpperCase(); }
  // faction-affinity bonus (sec 3.2) -- the active builder dog's faction is owned by
  // crew.js; until that lands this is a parity-safe 0 (tier bonus still applies).
  function factionBonus() { return 0; }

  /* ====================================================================== *
   * (1) PATTERNED NODE PLACEMENT (sec 8) -- deterministic, clearance-legal
   * ====================================================================== */
  function hashStr(s) { var h = 2166136261 >>> 0; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function mulberry32(a) { return function () { a |= 0; a = (a + 0x6D2B79F5) | 0; var t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  // UNWRAPPED starter obstacle set (never includes buildmode's placed walls, so
  // node placement is stable regardless of builds).
  function startObstacles(zone) {
    if (!zone) return [];
    if (zone.obstacles && zone.obstacles.length) return zone.obstacles;
    return (coll && coll.OBSTACLES && coll.OBSTACLES[zone.id]) || [];
  }

  function genZone(zone) {
    if (!zone) return [];
    var zid = zone.id;
    if (WV.gen[zid]) return WV.gen[zid];
    var WW = (WV.ctx && WV.ctx.world && WV.ctx.world.WORLD_W) || 1700;
    var WH = (WV.ctx && WV.ctx.world && WV.ctx.world.WORLD_H) || 1300;
    var cxp = WW / 2, cyp = WH / 2;                                // centre plaza (~850,650)
    var rng = mulberry32(hashStr('AKWVP|' + zid));                 // pattern-era salt
    var spec = PATTERN[zid] || null, shape, typeSeq, count;
    if (spec) { shape = spec.shape; typeSeq = spec.nodes; count = spec.count; }
    else { shape = 'scatter'; typeSeq = (GROUND_BIAS[zone.ground] || GROUND_BIAS._def); count = 6 + Math.floor(rng() * 4); }

    var obs = startObstacles(zone), doors = [], foots = [];
    (zone.buildings || []).forEach(function (b) {
      doors.push({ x: b.x, y: b.y + (b.h || 0) / 2 });            // door faces y + h/2
      foots.push({ x: b.x, y: b.y, w: (b.w || 0), h: (b.h || 0) });
    });
    var edges = [], ed = zone.edges || {};
    for (var k in ed) { if (ed.hasOwnProperty(k) && ed[k] && ed[k].spawn) edges.push(ed[k].spawn); }

    var accepted = [], rareCount = 0;
    function legal(x, y) {                                          // ALL the original clearance rules, unchanged
      if (x < 130 || x > WW - 130 || y < 130 || y > WH - 130) return false;
      if (Math.abs(x - cxp) < 95) return false;                    // vertical N/S spine
      if (Math.abs(y - cyp) < 105) return false;                   // horizontal W/E spine
      if (Math.hypot(x - cxp, y - cyp) < 160) return false;        // plaza bubble
      var i;
      for (i = 0; i < doors.length; i++) if (Math.hypot(x - doors[i].x, y - doors[i].y) < 120) return false;
      for (i = 0; i < foots.length; i++) { var f = foots[i]; if (Math.abs(x - f.x) < f.w / 2 + 46 && Math.abs(y - f.y) < f.h / 2 + 46) return false; }
      for (i = 0; i < edges.length; i++) if (Math.hypot(x - edges[i].x, y - edges[i].y) < 175) return false;
      if (coll && coll.blocks && coll.blocks(x, y, 34, obs)) return false;     // off fences / cars / rubble
      for (i = 0; i < accepted.length; i++) if (Math.hypot(x - accepted[i].x, y - accepted[i].y) < 96) return false;
      return true;
    }
    function pushNode(x, y) {
      x = Math.round(x); y = Math.round(y);
      var type = typeSeq[accepted.length % typeSeq.length];
      if (type === 'RAREVEIN' && rareCount >= RARE_CAP) type = 'WRECK';         // rare veins capped per zone
      if (type === 'RAREVEIN') rareCount++;
      var def = NODE_TYPES[type] || NODE_TYPES.SCRAP;
      accepted.push({
        key: 'n' + accepted.length, x: x, y: y, type: type,
        mat: def.mat, rar: def.rar || null, alt: def.alt || null,
        tool: def.tool, minTier: def.minTier, channel: def.channel,
        amount: def.amount, dur: def.dur, jackpot: !!def.jackpot
      });
    }
    // (1) pattern candidates first
    var cands = (GENERATORS[shape] || GENERATORS.scatter)(WW, WH, cxp, cyp, rng, count) || [];
    for (var ci = 0; ci < cands.length && accepted.length < count; ci++) {
      if (legal(cands[ci].x, cands[ci].y)) pushNode(cands[ci].x, cands[ci].y);
    }
    // (2) random top-up so a cluttered zone still gets its full faucet
    var tries = 0;
    while (accepted.length < count && tries < 600) {
      tries++;
      var rx = 130 + rng() * (WW - 260), ry = 130 + rng() * (WH - 260);
      if (legal(rx, ry)) pushNode(rx, ry);
    }
    WV.gen[zid] = accepted;
    return accepted;
  }

  /* ====================================================================== *
   * (2) DEPLETION STATE  (p.nodes[zid][key] = {r:readyAt, d:durMs})
   * ====================================================================== */
  function entryOf(zid, key) { var p = prof(); return (p && p.nodes && p.nodes[zid] && p.nodes[zid][key]) || null; }
  function isRipe(now, e) { return !e || now >= e.r; }
  function stageOf(now, e) {
    if (!e || now >= e.r) return 3;                               // ripe / fully grown
    var frac = (e.r - now) / (e.d || 1);                          // time REMAINING (1 = just harvested)
    return frac > 0.66 ? 0 : (frac > 0.33 ? 1 : 2);
  }
  function nodeByKey(zone, key) { var ns = genZone(zone); for (var i = 0; i < ns.length; i++) if (ns[i].key === key) return ns[i]; return null; }

  /* ====================================================================== *
   * (3) HARVEST -- gate -> grant -> deplete+respawn -> spend durability
   *     doHarvest is the SYNCHRONOUS completion primitive (the channel calls it
   *     when its timer lands; also exposed for the headless harness).
   * ====================================================================== */
  function grantMat(pp, mat, rar, amount, CAP, SELL, onOverflow) {
    if (amount <= 0) return;
    if (mat === 'scrap') {
      if (!pp.scrap || typeof pp.scrap !== 'object') pp.scrap = {};
      var rk = rar || 'Common';
      pp.scrap[rk] = Math.max(0, (pp.scrap[rk] | 0) + amount);
    } else {
      var cur = Math.max(0, pp[mat] | 0), room = Math.max(0, CAP - cur);
      var add = Math.min(amount, room), over = amount - add;
      pp[mat] = cur + add;
      if (over > 0) { var g = Math.round(over * (SELL[mat] || 1)); pp.coins = Math.max(0, (pp.coins | 0) + g); if (onOverflow) onOverflow(g, over); }   // AK-HARVESTAPI: 2nd arg = overflow UNITS (gold is arg 1) so harvestInfo can report banked vs sold
    }
  }

  /* AK-HARVESTAPI 2026-07-18: doHarvest keeps its plain boolean return (every
   * existing caller -- advanceChannel, tickJobs, AK_WORLDVERBS.harvest and
   * tests/worldverbs_probe.js -- reads it as one), so rec() records the FULL
   * outcome on the side instead. harvestInfo() below reads it back. This is the
   * structured {ok,material,amount,banked,overflow,gold,error} shape a caller
   * needs to tell "no tool" from "still regrowing" from "banked 8 wood", without
   * a second copy of the yield math existing anywhere to drift out of sync. */
  function rec(ok, error, extra) {
    var r = { ok: !!ok, error: error || null, key: null, zid: null, type: null,
              material: null, rarity: null, label: null, amount: 0, banked: 0,
              overflow: 0, gold: 0, dropped: false, respawnMs: 0, readyAt: 0, remainMs: 0 };
    if (extra) for (var k in extra) if (extra.hasOwnProperty(k)) r[k] = extra[k];
    WV.last = r;
    return !!ok;
  }

  // doHarvest is the SYNCHRONOUS completion primitive. DEFAULT = auto-bank (the
  // dispatched-builder dog "delivers" the haul; also the headless force-complete).
  // Pass {drop:true} (the MANUAL channel) to instead DROP the yield on the ground as
  // a walk-over collectible: SAME node deplete + durability + pop, but NOTHING banks
  // until the player walks over the drop (see tickDrops/collectDrop). A node yields
  // EITHER a drop OR a bank -- never both (no double-grant).
  function doHarvest(ctx, key, opts) {
    if (!ctx) return rec(false, 'NO_CTX');
    var asDrop = !!(opts && opts.drop);
    var zone = ctx.activeZone, zid = ctx.zoneId, node = nodeByKey(zone, key);
    if (!node) return rec(false, 'NO_NODE', { key: key, zid: zid });
    var now = Date.now();
    // ripeness is read FRESH from p.nodes on every call (never off a caller-held node
    // object), so re-firing harvest on the same key cannot re-grant -- the respawn
    // clock is the only thing that reopens a node.
    var ent = entryOf(zid, key);
    if (!isRipe(now, ent)) {
      ctx.showBanner('STILL REGROWING', 0.9);
      return rec(false, 'NOT_READY', { key: key, zid: zid, type: node.type, material: node.mat,
                                       readyAt: ent.r, remainMs: Math.max(0, ent.r - now) });
    }
    // (gate) no tool / too low a tier -> refuse, NOTHING is spent or depleted
    var tf = toolForP(freshProfile(), node.tool);
    if ((tf.tier | 0) < node.minTier) {
      ctx.showBanner('NEED A BETTER ' + toolLabel(node.tool), 1.2);
      return rec(false, 'NEED_TOOL', { key: key, zid: zid, type: node.type, material: node.mat,
                                       tool: node.tool, minTier: node.minTier, tier: tf.tier | 0 });
    }
    var E = global.AK_ECON || (ctx.econ && ctx.econ.MAT_CAP != null ? ctx.econ : null);
    var CAP = (E && E.MAT_CAP) || 2000;
    var SELL = (E && E.MAT_SELL) || { wood: 2, stone: 3, metal: 5 };
    var bonus = (tf.bonusLoot || 0) + factionBonus(ctx, node);   // tier loot bonus (+faction, parity-capped at the tier ceiling)
    var yieldAmt = Math.max(1, Math.round(node.amount * (1 + bonus)));
    // AK-DISTRICTS (city-depth #1): this district's SPECIALTY resource yields +20% here. Each neighborhood
    // of a faction-city has its own economic character -- mine metal in the Rusted forge row, wood on home turf.
    var dspec = (global.AK_DISTRICTS && global.AK_DISTRICTS.specialty) ? global.AK_DISTRICTS.specialty(zid) : null;
    var isSpec = !!(dspec && dspec === node.mat);
    if (isSpec) yieldAmt = Math.max(yieldAmt + 1, Math.round(yieldAmt * (global.AK_DISTRICTS.specialtyMult || 1.2)));
    var altAmt = node.alt ? Math.max(1, Math.round(node.alt.amount * (1 + bonus))) : 0;
    var rareHit = (tf.rareDrop || 0) > 0 && Math.random() < tf.rareDrop;
    var rareBonus = rareHit ? Math.max(1, Math.round(yieldAmt * 0.5)) : 0;   // (c) rare-drop: a richer pull (soft-currency only)
    var jackpotRare = !!(rareHit && node.jackpot);
    var d = NODE_TYPES[node.type];
    // (e) spend durability (T4 spends 0 on T1-class nodes) -- authoritative in economy.js
    var durCost = ((tf.tier | 0) >= 4 && node.minTier <= 1) ? 0 : 1;

    if (asDrop) {
      // MANUAL path: deplete + spend durability + pop, but DROP the haul on the ground.
      // The drop carries the EXACT bundle the bank path would grant; it banks on walk-over.
      ctx.econ.mutateProfile(function (pp) {                                                            // (d) deplete + respawn
        if (!pp.nodes || typeof pp.nodes !== 'object') pp.nodes = {};
        if (!pp.nodes[zid] || typeof pp.nodes[zid] !== 'object') pp.nodes[zid] = {};
        pp.nodes[zid][key] = { r: now + node.dur, d: node.dur };
      });
      spendDur(node.tool, durCost);
      bump();
      spawnDrop(zid, node, yieldAmt + rareBonus, altAmt, jackpotRare);                                  // primary+rare share the mat line (as bank would)
      ctx.showBanner('MINED!  +' + yieldAmt + ' ' + d.label + (rareBonus ? '  +RICH VEIN' : '') + (isSpec ? '  ★ district specialty' : ''), 1.2);
      updatePrompt(ctx);
      return rec(true, null, { key: key, zid: zid, type: node.type, material: node.mat, rarity: node.rar || null,
                               label: d.label, amount: yieldAmt + rareBonus, dropped: true, respawnMs: node.dur, readyAt: now + node.dur });
    }

    // DEFAULT path: auto-bank the yield into the profile (dispatched builder / headless force-complete).
    var overflowGold = 0, overflowUnits = 0;
    ctx.econ.mutateProfile(function (pp) {
      grantMat(pp, node.mat, node.rar, yieldAmt, CAP, SELL, function (g, ov) { overflowGold += g; overflowUnits += ov | 0; });      // (a) primary
      if (node.alt) grantMat(pp, node.alt.mat, node.alt.rar, altAmt, CAP, SELL, function (g, ov) { overflowGold += g; overflowUnits += ov | 0; });  // (b) alt (Wreck = metal + scrap)
      if (rareBonus) {
        grantMat(pp, node.mat, node.rar, rareBonus, CAP, SELL, function (g, ov) { overflowGold += g; overflowUnits += ov | 0; });
        if (jackpotRare) { if (!pp.scrap || typeof pp.scrap !== 'object') pp.scrap = {}; pp.scrap.Rare = Math.max(0, (pp.scrap.Rare | 0) + 1); }
      }
      if (!pp.nodes || typeof pp.nodes !== 'object') pp.nodes = {};                                     // (d) deplete + respawn
      if (!pp.nodes[zid] || typeof pp.nodes[zid] !== 'object') pp.nodes[zid] = {};
      pp.nodes[zid][key] = { r: now + node.dur, d: node.dur };
    });
    spendDur(node.tool, durCost);
    bump();
    if (overflowGold > 0) ctx.showBanner('STORE FULL -- SOLD +' + overflowGold + ' GOLD', 1.4);
    else ctx.showBanner('+' + yieldAmt + ' ' + d.label + (rareBonus ? '  +RICH VEIN' : '') + (isSpec ? '  ★ district specialty' : ''), 1.2);
    updatePrompt(ctx);
    var _tot = yieldAmt + rareBonus;
    return rec(true, null, { key: key, zid: zid, type: node.type, material: node.mat, rarity: node.rar || null,
                             label: d.label, amount: _tot, banked: Math.max(0, _tot - overflowUnits),
                             overflow: overflowUnits, gold: overflowGold, respawnMs: node.dur, readyAt: now + node.dur });
  }

  // sweep expired (regrown) entries back to ripe -- the persisted "regrow"
  function sweepExpired(ctx) {
    var zid = ctx.zoneId, p = prof(), z = p && p.nodes && p.nodes[zid];
    if (!z) return;
    var now = Date.now(), dead = [];
    for (var key in z) { if (z.hasOwnProperty(key) && z[key] && now >= z[key].r) dead.push(key); }
    if (!dead.length) return;
    ctx.econ.mutateProfile(function (pp) {
      var zz = pp.nodes && pp.nodes[zid]; if (!zz) return;
      for (var i = 0; i < dead.length; i++) delete zz[dead[i]];
      var any = false; for (var kk in zz) { if (zz.hasOwnProperty(kk)) { any = true; break; } }
      if (!any) delete pp.nodes[zid];
    });
    bump();
  }

  /* ====================================================================== *
   * (3b) GROUND DROPS -- the MANUAL harvest drops the haul on the ground as a
   *   walk-over collectible instead of auto-banking it. The player walks OVER the
   *   drop (within PICKUP_RANGE) to bank it via the SAME grantMat/econ path the
   *   auto-bank uses, so amounts match exactly (a node = a drop OR a bank, never
   *   both -> no double-grant). Uncollected drops linger then despawn after
   *   DROP_TTL -- the "someone else (enemy/teammate) grabbed it" fiction; true
   *   multiplayer contest is a later server step. Drops are session-only +
   *   ephemeral on purpose (NOT persisted) -- a reload reads as a despawn.
   * ====================================================================== */
  function spawnDrop(zid, node, amount, altAmt, jackpotRare) {
    WV.drops.push({
      zid: zid, x: node.x, y: node.y, type: node.type,
      mat: node.mat, rar: node.rar || null, amount: Math.max(0, amount | 0),
      alt: node.alt ? { mat: node.alt.mat, rar: node.alt.rar || null, amount: Math.max(0, altAmt | 0) } : null,
      rareScrap: jackpotRare ? 1 : 0, born: Date.now()
    });
  }
  function collectDrop(ctx, dr) {                                  // walked over a drop -> bank it (identical econ path to auto-bank)
    var E = global.AK_ECON || (ctx.econ && ctx.econ.MAT_CAP != null ? ctx.econ : null);
    var CAP = (E && E.MAT_CAP) || 2000, SELL = (E && E.MAT_SELL) || { wood: 2, stone: 3, metal: 5 };
    var overflowGold = 0;
    ctx.econ.mutateProfile(function (pp) {
      grantMat(pp, dr.mat, dr.rar, dr.amount, CAP, SELL, function (g) { overflowGold += g; });
      if (dr.alt) grantMat(pp, dr.alt.mat, dr.alt.rar, dr.alt.amount, CAP, SELL, function (g) { overflowGold += g; });
      if (dr.rareScrap) { if (!pp.scrap || typeof pp.scrap !== 'object') pp.scrap = {}; pp.scrap.Rare = Math.max(0, (pp.scrap.Rare | 0) + dr.rareScrap); }
    });
    bump();
    var def = NODE_TYPES[dr.type] || {}, label = def.label || String(dr.mat || 'LOOT').toUpperCase();
    if (overflowGold > 0) ctx.showBanner('STORE FULL -- SOLD +' + overflowGold + ' GOLD', 1.3);
    else ctx.showBanner('+' + dr.amount + ' ' + label + ' collected', 1.0);
  }
  function tickDrops(ctx) {                                        // walk-over collect + TTL despawn (LIVE; headless just lets them despawn)
    if (!WV.drops.length) return;
    var now = Date.now(), zid = ctx.zoneId, keep = [];
    var canReach = !!(ctx.world && typeof ctx.world.distToMe === 'function');
    for (var i = 0; i < WV.drops.length; i++) {
      var dr = WV.drops[i];
      if (now - dr.born >= DROP_TTL) continue;                    // lingered too long -> despawn (someone else's now)
      if (dr.zid === zid && canReach && ctx.world.distToMe(dr.x, dr.y) <= PICKUP_RANGE) { collectDrop(ctx, dr); continue; }
      keep.push(dr);
    }
    WV.drops = keep;
  }

  /* ====================================================================== *
   * (4) GATHER CHANNEL (clock A) -- tap a ripe node, the dog WORKS for time
   * ====================================================================== */
  function effChannelSec(ctx, node) {
    var tf = toolForP(freshProfile(), node.tool);
    var tm = (tf.timeMult != null ? tf.timeMult : (tf.def && tf.def.timeMult)) || 1;
    return Math.max(0.5, node.channel * tm / (builderSpeedNow() || 1));
  }
  function channelFrac() { var ch = WV.channel; return ch ? Math.max(0, Math.min(1, ch.elapsed / (ch.dur || 1))) : 0; }
  function startChannel(ctx, key) {
    if (!ctx) return false;
    if (WV.channel) { if (WV.channel.key === key && WV.channel.zid === ctx.zoneId) return false; WV.channel = null; }
    var zone = ctx.activeZone, zid = ctx.zoneId, node = nodeByKey(zone, key);
    if (!node) return false;
    if (!isRipe(Date.now(), entryOf(zid, key))) { ctx.showBanner('STILL REGROWING', 0.9); return false; }
    var tf = toolForP(freshProfile(), node.tool);
    if ((tf.tier | 0) < node.minTier) { ctx.showBanner('NEED A BETTER ' + toolLabel(node.tool), 1.2); return false; }
    WV.channel = { zid: zid, key: key, elapsed: 0, dur: effChannelSec(ctx, node), node: node };
    updatePrompt(ctx);
    return true;
  }
  function cancelChannel(ctx, banner) {
    WV.channel = null;
    if (ctx && banner) ctx.showBanner(banner, 1.0);
    if (ctx) updatePrompt(ctx);
  }
  function advanceChannel(ctx, dt) {
    var ch = WV.channel; if (!ch) return;
    if (ctx.zoneId !== ch.zid) { cancelChannel(); return; }                       // changed zone -> drop
    var node = nodeByKey(ctx.activeZone, ch.key); if (!node) { cancelChannel(); return; }
    if (global.AK_BUILDMODE && global.AK_BUILDMODE.isActive && global.AK_BUILDMODE.isActive()) { cancelChannel(); return; }
    // walked away -> interrupt (LIVE only; headless has no player to move, so it never cancels on range)
    if (typeof document !== 'undefined' && ctx.world && typeof ctx.world.distToMe === 'function'
        && ctx.world.distToMe(node.x, node.y) > HARVEST_RANGE + 50) { cancelChannel(ctx, 'INTERRUPTED'); return; }
    ch.elapsed += dt;
    if (ch.elapsed >= ch.dur) { var key = ch.key; WV.channel = null; doHarvest(ctx, key, { drop: true }); }   // channel landed -> DROP the haul (you walk over it to bank)
  }

  /* ====================================================================== *
   * (5) THE FLOATING "HARVEST" PROMPT  (one-thumb; lazy DOM)
   * ====================================================================== */
  /* AK-DEEMOJI 2026-06-26: the HARVEST prompt's node icon. Priority mirrors the
   * in-world drawNode -- the EXISTING wv_*.png sprite when loaded, else a clean
   * mat-tinted CSS chip, else (only if styling is impossible) the emoji glyph.
   * Writes to the DOM ONLY on change (cached _ic / _disp) so it is free per-frame. */
  var ICON_CSS = 'width:17px;height:17px;border-radius:4px;flex:0 0 auto;line-height:17px;' +
    'text-align:center;font-size:13px;background-size:cover;background-position:center;background-repeat:no-repeat;';
  function paintNodeIcon(el, def) {
    if (!el) return;
    var im = def && spriteImg(def.sprite);
    if (im && spriteReady(im)) {                                   // (1) the real node sprite
      if (el._ic !== def.sprite) {
        el.style.backgroundImage = 'url("' + def.sprite + '")';
        el.style.backgroundColor = 'transparent'; el.style.border = '1px solid rgba(21,17,10,.4)';
        el.textContent = ''; el._ic = def.sprite;
      }
    } else if (def && def.mat) {                                   // (2) clean mat-tinted chip (NOT an emoji)
      var key = 'm:' + def.mat;
      if (el._ic !== key) {
        var c = dropColor(def.mat);
        el.style.backgroundImage = 'linear-gradient(155deg,' + c + ',rgba(0,0,0,.45))';
        el.style.backgroundColor = c; el.style.border = '1px solid rgba(21,17,10,.4)';
        el.textContent = ''; el._ic = key;
      }
    } else {                                                       // (3) last-resort: the emoji glyph (styling unavailable)
      var gk = 'g:' + ((def && def.glyph) || '');
      if (el._ic !== gk) { el.style.backgroundImage = 'none'; el.style.border = '0'; el.style.backgroundColor = 'transparent'; el.textContent = (def && def.glyph) || ''; el._ic = gk; }
    }
  }
  function showIcon(el, def) { if (!el) return; if (el._disp !== 1) { el.style.display = 'inline-block'; el._disp = 1; } paintNodeIcon(el, def); }
  function hideIcon(el) { if (!el) return; if (el._disp !== 0) { el.style.display = 'none'; el._disp = 0; } }
  function setLabel(str) { if (WV.btnTx) WV.btnTx.textContent = str; else if (WV.btn) WV.btn.textContent = str; }   // primary-button text (icon-safe)

  function mountButton() {
    if (typeof document === 'undefined') return null;
    if (WV.btn || document.getElementById('ak-wv-btn')) {
      WV.btn = document.getElementById('ak-wv-btn'); WV.btn2 = WV.btn2 || document.getElementById('ak-wv-btn2');
      if (WV.btn) { WV.btnIc = WV.btnIc || WV.btn.querySelector('i'); WV.btnTx = WV.btnTx || WV.btn.querySelector('span'); }
      return WV.btn;
    }
    var common = 'position:fixed;bottom:calc(86px + env(safe-area-inset-bottom));z-index:11;display:none;' +
      'align-items:center;gap:7px;padding:11px 16px;border-radius:13px;cursor:pointer;-webkit-tap-highlight-color:transparent;' +
      'font-family:Inter,system-ui,sans-serif;font-weight:900;font-size:13px;letter-spacing:.03em;box-shadow:0 4px 14px rgba(0,0,0,.5);';
    // PRIMARY = HARVEST (manual channel: stay + work it yourself). Sits just LEFT of centre.
    var b = document.createElement('button'); b.id = 'ak-wv-btn'; b.type = 'button';
    b.style.cssText = common + 'left:50%;transform:translateX(calc(-100% - 4px));background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:1px solid rgba(21,17,10,.4);';
    b.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (!WV.ctx) return;
      if (WV.channel) { cancelChannel(WV.ctx, 'STOPPED'); }              // tap during work = stop
      else if (WV.nearKey) startChannel(WV.ctx, WV.nearKey);            // tap a ripe node = start the channel
    });
    var bi = document.createElement('i'); bi.style.cssText = ICON_CSS; bi.style.display = 'none'; bi._disp = 0; bi._ic = null; b.appendChild(bi);   // AK-DEEMOJI: sprite / mat-chip icon (no emoji)
    var bt = document.createElement('span'); b.appendChild(bt);
    WV.btnIc = bi; WV.btnTx = bt;
    document.body.appendChild(b); WV.btn = b;
    // SECONDARY = SEND DOG (dispatch a builder -> walk away). Sits just RIGHT of centre.
    var b2 = document.createElement('button'); b2.id = 'ak-wv-btn2'; b2.type = 'button';
    b2.style.cssText = common + 'left:50%;transform:translateX(4px);background:linear-gradient(180deg,#2a3340,#1a212b);color:#e8c55a;border:1px solid rgba(232,197,90,.55);';
    b2.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      if (WV.ctx && WV.nearKey) dispatchBuilder(WV.ctx, WV.nearKey);     // send a dog, then you can leave
    });
    document.body.appendChild(b2); WV.btn2 = b2;
    return b;
  }
  function hidePrompt() { WV.nearKey = null; if (WV.btn) WV.btn.style.display = 'none'; if (WV.btn2) WV.btn2.style.display = 'none'; }

  function updatePrompt(ctx) {
    if (typeof document === 'undefined') return;                  // headless: no prompt, channel/harvest still callable
    var btn = WV.btn || mountButton(); if (!btn) return;
    if (global.AK_BUILDMODE && global.AK_BUILDMODE.isActive && global.AK_BUILDMODE.isActive()) { hidePrompt(); return; }
    var b2 = WV.btn2; function hide2() { if (b2) b2.style.display = 'none'; }
    // channel in progress -> WORKING NN% (manual path); no SEND DOG mid-channel
    if (WV.channel && WV.channel.zid === ctx.zoneId) {
      WV.nearKey = WV.channel.key;
      hideIcon(WV.btnIc); setLabel('WORKING  ' + Math.round(channelFrac() * 100) + '%');
      btn.style.opacity = '1'; btn.style.filter = 'none'; btn.style.display = 'flex';
      hide2();
      return;
    }
    // AK-HARVESTAPI 2026-07-18: the walk-up search is now the PUBLIC nodeNear(), so the
    // prompt and any other caller resolve "what is workable here" through one function.
    // ctx.world.distToMe is Math.hypot(me.x-x, me.y-y) (index.html:3108), so feeding
    // ctx.me straight in is the same test this loop ran inline.
    var _m = ctx.me || { x: 1e9, y: 1e9 };                        // AK_CTX always carries me (index.html:3090); a host without it just gets no prompt, never a throw
    var zid = ctx.zoneId, best = nodeNear(ctx.activeZone, _m.x, _m.y, HARVEST_RANGE);
    if (!best) { hidePrompt(); return; }
    WV.nearKey = best.key;
    var t = NODE_TYPES[best.type], tf = toolForP(freshProfile(), best.tool), gated = (tf.tier | 0) < best.minTier;
    if (gated) {                                                  // surface the gate proactively (tap still banners)
      hideIcon(WV.btnIc); setLabel('NEED A BETTER ' + toolLabel(best.tool));
      btn.style.opacity = '.7'; btn.style.filter = 'grayscale(.4)';
    } else {
      showIcon(WV.btnIc, t); setLabel('HARVEST  +' + best.amount + ' ' + t.label);
      btn.style.opacity = '1'; btn.style.filter = 'none';
    }
    btn.style.display = 'flex';
    // SEND DOG: only when the node is workable, no dog is already on it, and a builder slot is free.
    if (b2) {
      if (!gated && !jobOnNode(zid, best.key) && freeBuilders() > 0) {
        var secs = Math.round(effChannelSec(ctx, best));
        b2.textContent = 'SEND DOG  ' + secs + 's';
        b2.style.opacity = '1'; b2.style.filter = 'none'; b2.style.display = 'flex';
      } else { b2.style.display = 'none'; }
    }
  }

  /* ====================================================================== *
   * (6) RENDER -- themed vector nodes, growthStage depletion, channel arc.
   *     transform/alpha only; NO per-frame shadowBlur.
   * ====================================================================== */
  function drawNode(g, X, Y, def, stage, ripe, pulse) {
    var B = def.big || 1, sc = [0.0, 0.45, 0.72, 1.0][stage] * B, fam = def.draw;
    g.save();
    var _sim = spriteImg(def.sprite);
    if (stage >= 3 && spriteReady(_sim)) {                        // AK-NODEART: ripe node = real sprite
      var _S = 56 * B; g.drawImage(_sim, X - _S / 2, Y - _S * 0.78, _S, _S);
    } else if (fam === 'TREE') {
      g.fillStyle = '#3a2716'; g.fillRect(X - 6, Y - 1, 12, 11);  // stump base
      if (stage === 0) { g.fillStyle = '#2e7d32'; g.fillRect(X - 1, Y - 7, 2, 7); } // regrow sprout
      else {
        var th = 8 + 16 * sc; g.fillStyle = '#5d3b1f'; g.fillRect(X - 4, Y - th, 8, th);
        var r = 11 + 17 * sc, cyT = Y - th - r * 0.35;
        g.fillStyle = '#2e7d32'; g.beginPath(); g.arc(X, cyT, r, 0, 7); g.fill();
        g.fillStyle = '#3fa34d'; g.beginPath(); g.arc(X - r * 0.45, cyT + r * 0.15, r * 0.6, 0, 7); g.fill();
        g.strokeStyle = GOLD_DK; g.lineWidth = 1.5; g.beginPath(); g.arc(X, cyT, r, 0, 7); g.stroke();
      }
    } else if (fam === 'ROCK') {
      if (stage === 0) {                                          // cracked rubble
        g.fillStyle = '#565a61';
        g.beginPath(); g.arc(X - 6, Y + 3, 5, 0, 7); g.arc(X + 5, Y + 4, 4, 0, 7); g.arc(X, Y + 1, 4, 0, 7); g.fill();
      } else {
        var R = 10 + 15 * sc;
        g.fillStyle = '#6c6f76'; g.beginPath(); g.arc(X, Y - 2, R, 0, 7); g.fill();
        g.fillStyle = '#565a61'; g.beginPath(); g.arc(X - R * 0.5, Y + 3, R * 0.55, 0, 7); g.fill();
        g.strokeStyle = 'rgba(20,20,26,.55)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X - R * 0.3, Y - R * 0.4); g.lineTo(X, Y); g.lineTo(X + R * 0.2, Y + R * 0.3); g.stroke();
        g.strokeStyle = GOLD_DK; g.lineWidth = 1.5; g.beginPath(); g.arc(X, Y - 2, R, 0, 7); g.stroke();
      }
    } else if (fam === 'SCRAP') {
      var w = 18 + 16 * sc, h = 11 + 9 * sc;
      g.fillStyle = '#2a2620';
      g.beginPath(); g.moveTo(X - w / 2, Y + h / 2); g.lineTo(X - w / 4, Y - h / 2); g.lineTo(X + w / 6, Y); g.lineTo(X + w / 2, Y - h / 3); g.lineTo(X + w / 2, Y + h / 2); g.closePath(); g.fill();
      g.strokeStyle = '#9aa7b3'; g.lineWidth = 1.2;
      g.beginPath(); g.moveTo(X - w / 4, Y + h / 2); g.lineTo(X - w / 6, Y - h / 3); g.moveTo(X + w / 6, Y + h / 3); g.lineTo(X + w / 4, Y - h / 2); g.stroke();
      if (stage >= 2) { g.fillStyle = GOLD; g.fillRect(X - 4, Y - h / 3, 2, 2); g.fillRect(X + 5, Y - 1, 2, 2); }
      g.strokeStyle = GOLD_DK; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X - w / 2 - 1, Y + h / 2); g.lineTo(X + w / 2 + 1, Y + h / 2); g.stroke();
    } else { // PIPE / RARE VEIN
      var pw = 22 + 14 * sc, ph = 10;
      g.fillStyle = '#39434e'; g.fillRect(X - pw / 2, Y - ph / 2, pw, ph);
      g.fillStyle = 'rgba(127,200,255,.22)'; g.fillRect(X - pw / 2, Y - ph / 2, pw, 3);
      g.fillStyle = '#9aa7b3'; g.fillRect(X - pw / 2 - 3, Y - ph / 2 - 2, 5, ph + 4); g.fillRect(X + pw / 2 - 2, Y - ph / 2 - 2, 5, ph + 4);
      if (def.jackpot && stage >= 1) {                            // rare-vein violet ore glint
        g.fillStyle = '#c9a8ff'; g.beginPath(); g.arc(X - pw * 0.18, Y, 2.6, 0, 7); g.arc(X + pw * 0.2, Y - 1, 2.1, 0, 7); g.fill();
      } else if (stage >= 2) { g.fillStyle = '#7fc8ff'; g.beginPath(); g.arc(X, Y + ph / 2 + 3, 2.4, 0, 7); g.fill(); }
      g.strokeStyle = def.jackpot ? '#c9a8ff' : GOLD; g.lineWidth = 1.5; g.strokeRect(X - pw / 2, Y - ph / 2, pw, ph);
    }
    if (ripe && !WV.reduce) {                                     // "ready" gold pulse (alpha only, NO shadowBlur)
      var a = 0.22 + 0.16 * (0.5 + 0.5 * Math.sin(pulse * 3));
      g.strokeStyle = 'rgba(232,197,90,' + a.toFixed(3) + ')'; g.lineWidth = 2;
      g.beginPath(); g.arc(X, Y - 4, 26 * B, 0, 7); g.stroke();
    } else if (ripe) {                                            // reduced-motion: a static ready ring
      g.strokeStyle = 'rgba(232,197,90,.3)'; g.lineWidth = 2; g.beginPath(); g.arc(X, Y - 4, 26 * B, 0, 7); g.stroke();
    }
    g.restore();
  }
  function drawChannelArc(g, X, Y, frac, B) {                     // filling gold progress ring (alpha/stroke only)
    g.save();
    g.strokeStyle = 'rgba(232,197,90,.18)'; g.lineWidth = 3.5;
    g.beginPath(); g.arc(X, Y - 4, 30 * B, 0, 7); g.stroke();
    g.strokeStyle = 'rgba(232,197,90,.95)'; g.lineWidth = 3.5;
    g.beginPath(); g.arc(X, Y - 4, 30 * B, -Math.PI / 2, -Math.PI / 2 + frac * Math.PI * 2); g.stroke();
    g.restore();
  }
  function dropColor(mat) {                                        // mat-tinted nugget fill for the procedural fallback token
    return mat === 'wood' ? '#7a4f25' : (mat === 'stone' ? '#7d8088' : (mat === 'metal' ? '#9aa7b3' : '#caa64a'));
  }
  function drawDrop(g, X, Y, def, clock) {                         // AK-DROPS: a small pickable loot token -- gentle bob + gold "collect" pulse (alpha/transform only, NO shadowBlur)
    g.save();
    var bob = WV.reduce ? 0 : Math.sin(clock * 3 + X * 0.05) * 2.4, cy = Y - 7 - bob;
    g.fillStyle = 'rgba(0,0,0,.30)'; g.beginPath(); g.ellipse(X, Y + 1, 8, 3, 0, 0, 7); g.fill();          // ground shadow
    var im = spriteImg(def.sprite);
    if (spriteReady(im)) {                                         // reuse the node sprite, shrunk to a token
      var S = 24; g.drawImage(im, X - S / 2, cy - S / 2, S, S);
    } else {                                                       // procedural mat-colored nugget (headless / sprite not ready)
      g.fillStyle = dropColor(def.mat);
      g.beginPath(); g.moveTo(X, cy - 7); g.lineTo(X + 7, cy); g.lineTo(X, cy + 7); g.lineTo(X - 7, cy); g.closePath(); g.fill();
      g.strokeStyle = GOLD_DK; g.lineWidth = 1.4; g.stroke();
    }
    if (!WV.reduce) {                                              // gold "collect me" pulse ring
      var a = 0.30 + 0.24 * (0.5 + 0.5 * Math.sin(clock * 4));
      g.strokeStyle = 'rgba(232,197,90,' + a.toFixed(3) + ')'; g.lineWidth = 2;
      g.beginPath(); g.arc(X, cy, 15, 0, 7); g.stroke();
    } else {
      g.strokeStyle = 'rgba(232,197,90,.35)'; g.lineWidth = 2; g.beginPath(); g.arc(X, cy, 15, 0, 7); g.stroke();
    }
    g.restore();
  }

  /* ====================================================================== *
   * (6b) DISPATCHED BUILDER HARVEST -- "send a dog, walk away" (sec 5)
   *   SEND DOG on a ripe node -> a builder dog trots out from the nearest
   *   building (the hut), works the node over a WALL-CLOCK timer (so you can
   *   walk off), banks the yield via doHarvest the moment it lands, then trots
   *   home + frees the slot. Concurrency cap = AK_ECON.builderCap(TH) -- the
   *   SAME source that feeds the Foreman, so tools/cards/builders all agree.
   *   Jobs persist to p.fieldJobs; one whose timer lands while you're in another
   *   district banks the instant you walk back (Clash-style collect-on-return).
   * ====================================================================== */
  var WALK_OUT = 1.6, WALK_BACK = 1.2;                            // cosmetic trot seconds; the WORK clock is what gates the yield
  function builderCapNow() {
    var E = global.AK_ECON, p = prof();
    try { if (E && E.effectiveBuilderCap) return E.effectiveBuilderCap(p) || 1;   // AK-BUILDERS: count hired (gold-bought) slots, not just the TH cap
          if (E && E.builderCap) return (E.builderCap((p && p.townHall) || 1) + (((p && p.bonusBuilders) | 0))) || 1; } catch (_) {}
    return 1;
  }
  // AK-BUILDERCAP 2026-06-25: builders are ONE shared pool -- harvest dispatch
  // (p.fieldJobs) AND building upgrades (p.prod upUntil>now) draw from the SAME
  // builderCap. We read AK_ECON.buildersBusy (the single source) so SEND DOG can
  // never push past the cap when building upgrades are already eating slots (and
  // vice versa). Pass a fresh profile at the dispatch GATE; the per-frame button
  // uses the ver-cached prof() (60fps; staleness is cosmetic, the gate is authoritative).
  function busyBuilders(p) {
    var E = global.AK_ECON;
    if (E && typeof E.buildersBusy === 'function') { try { return E.buildersBusy(p || prof()); } catch (_) {} }
    return WV.jobs.length;                                    // headless / no-AK_ECON fallback (harvest jobs only)
  }
  function freeBuilders(p) { return Math.max(0, builderCapNow() - busyBuilders(p)); }
  function shortName(n) { n = String(n || 'Pup'); return n.length > 12 ? n.slice(0, 11) + '…' : n; }
  // AK-DECKCARD 2026-06-22: the dispatched worker is a REAL card from your deck -- the cards ARE the town's
  // people (operator). Resolve the card's portrait art (window.CANON_CARDS + akCardArtRel) + its live level.
  function cardArtFor(name) {
    try { var L = global.CANON_CARDS || []; for (var i = 0; i < L.length; i++) { var c = L[i]; if (c && (c.name === name || c.id === name)) { if (global.akCardArtRel) { var rel = global.akCardArtRel(c); if (rel) return 'assets/' + rel; } break; } } } catch (_) {}
    return null;
  }
  function cardLvlFor(name) { try { var E = global.AK_ECON, p = prof(); if (E && E.cardLevel) return E.cardLevel(p, name) | 0; } catch (_) {} return 1; }
  function pickBuilder() {
    var name = null, lvl = 1;
    try { var B = global.AK_BUILDMODE; if (B && B.builders) { var bs = B.builders() || []; for (var i = 0; i < bs.length; i++) { if (bs[i] && bs[i].card) { name = bs[i].card; lvl = bs[i].lvl || 1; break; } } } } catch (_) {}   // an assigned foreman card first
    if (!name) { try { var p = prof(); if (p && Array.isArray(p.owned) && p.owned.length) { name = p.owned[WV.jobs.length % p.owned.length]; lvl = cardLvlFor(name); } } catch (_) {} }   // else a real owned deck card (varied by job index)
    if (!name) name = 'Packmate';
    return { name: name, lvl: lvl || 1, art: cardArtFor(name) };
  }
  function nearestHut(ctx) {                                      // the dog emerges from the nearest building door; fallback plaza
    var z = ctx.activeZone, bs = (z && z.buildings) || [], best = null, bd = 1e9, cx = ((ctx.world && ctx.world.WORLD_W) || 1700) / 2, cy = ((ctx.world && ctx.world.WORLD_H) || 1300) / 2;
    for (var i = 0; i < bs.length; i++) { var b = bs[i], d = Math.hypot(b.x - cx, b.y - cy); if (d < bd) { bd = d; best = b; } }
    if (best) return { x: best.x, y: best.y + (best.h || 0) / 2 + 16 };
    return { x: cx, y: cy };
  }
  function saveJobs() {
    if (!WV.ctx || !WV.ctx.econ) return;
    try { WV.ctx.econ.mutateProfile(function (p) { p.fieldJobs = WV.jobs.map(function (j) { return { zid: j.zid, key: j.key, t0: j.t0, work: j.work, bn: j.bn, bl: j.bl, banked: !!j.banked }; }); }); } catch (_) {}
  }
  function loadJobs() {
    if (WV.jobsLoaded) return; WV.jobsLoaded = true;
    try { var p = prof(), arr = (p && p.fieldJobs) || [];
      WV.jobs = arr.map(function (j) { return { zid: j.zid, key: j.key, t0: j.t0, work: j.work, bn: j.bn, bl: j.bl, art: cardArtFor(j.bn), banked: !!j.banked, bx: 0, by: 0, hx: 0, hy: 0, nx: 0, ny: 0 }; });
    } catch (_) { WV.jobs = []; }
  }
  function jobOnNode(zid, key) { for (var i = 0; i < WV.jobs.length; i++) if (WV.jobs[i].zid === zid && WV.jobs[i].key === key) return WV.jobs[i]; return null; }
  function jobPhase(j, now) {                                     // -> {p:'out'|'work'|'back'|'done', t:0..1}
    var el = (now - j.t0) / 1000;
    if (el < WALK_OUT) return { p: 'out', t: WALK_OUT ? el / WALK_OUT : 1 };
    if (el < WALK_OUT + j.work) return { p: 'work', t: j.work ? (el - WALK_OUT) / j.work : 1 };
    if (el < WALK_OUT + j.work + WALK_BACK) return { p: 'back', t: WALK_BACK ? (el - WALK_OUT - j.work) / WALK_BACK : 1 };
    return { p: 'done', t: 1 };
  }
  function dispatchBuilder(ctx, key) {
    if (!ctx) return false;
    var zid = ctx.zoneId, node = nodeByKey(ctx.activeZone, key); if (!node) return false;
    if (jobOnNode(zid, key)) { ctx.showBanner && ctx.showBanner('A DOG IS ALREADY ON IT', 1.0); return false; }
    if (!isRipe(Date.now(), entryOf(zid, key))) { ctx.showBanner && ctx.showBanner('STILL REGROWING', 0.9); return false; }
    var tf = toolForP(freshProfile(), node.tool);
    if ((tf.tier | 0) < node.minTier) { ctx.showBanner && ctx.showBanner('NEED A BETTER ' + toolLabel(node.tool), 1.2); return false; }
    if (freeBuilders(freshProfile()) <= 0) { ctx.showBanner && ctx.showBanner('ALL ' + builderCapNow() + ' BUILDERS BUSY', 1.4); return false; }   // fresh read: count building-upgrade slots too (shared cap)
    var b = pickBuilder(), hut = nearestHut(ctx);
    // AK-DECKCARD: the dispatched CARD's level drives its work speed (a higher-level dog works faster) -- ties card level -> harvest, the deck-as-people depth.
    var _tf = toolForP(freshProfile(), node.tool), _tm = (_tf.timeMult != null ? _tf.timeMult : (_tf.def && _tf.def.timeMult)) || 1;
    var _bs = 1; try { var E = global.AK_ECON, pp = prof(); if (E && E.builderSpeed) _bs = E.builderSpeed(b.lvl || 1, (pp && pp.townHall) || 1) || 1; } catch (_) {}
    var _work = Math.max(0.5, node.channel * _tm / _bs);
    WV.jobs.push({ zid: zid, key: key, t0: Date.now(), work: _work, bn: b.name, bl: b.lvl, art: b.art, banked: false,
                   nx: node.x, ny: node.y, hx: hut.x, hy: hut.y, bx: hut.x, by: hut.y });
    saveJobs();
    bump();                                                  // refresh the ver-cached profile so freeBuilders/SEND DOG button reflect the new job immediately
    ctx.showBanner && ctx.showBanner(shortName(b.name) + (b.lvl ? ' (Lv' + b.lvl + ')' : '') + ' is on the job', 1.4);
    try { updatePrompt(ctx); } catch (_) {}
    return true;
  }
  function tickJobs(ctx) {
    if (!WV.jobs.length) return;
    var now = Date.now(), changed = false, keep = [];
    for (var i = 0; i < WV.jobs.length; i++) {
      var j = WV.jobs[i], inZone = (j.zid === ctx.zoneId), ph = jobPhase(j, now);
      var workDone = (now - j.t0) / 1000 >= WALK_OUT + j.work;
      if (workDone && !j.banked && inZone) {                      // bank needs the live node -> only in the job's zone
        try { doHarvest(ctx, j.key); } catch (_) {}
        j.banked = true; changed = true;
      }
      if (ph.p === 'done' && j.banked) { changed = true; continue; }   // dog home + yield banked -> drop the job
      if (inZone) {                                               // visual trot position
        if (ph.p === 'out') { j.bx = j.hx + (j.nx - j.hx) * ph.t; j.by = j.hy + (j.ny - j.hy) * ph.t; }
        else if (ph.p === 'work') { j.bx = j.nx; j.by = j.ny + 16; }
        else { j.bx = j.nx + (j.hx - j.nx) * ph.t; j.by = j.ny + (j.hy - j.ny) * ph.t; }
      }
      keep.push(j);
    }
    WV.jobs = keep;
    if (changed) saveJobs();
  }
  function drawTimerBar(g, X, Y, frac, label) {                   // countdown bar above a worked node (transform/fill only)
    var w = 48, h = 6;
    g.save();
    g.fillStyle = 'rgba(8,8,14,.85)'; g.fillRect(X - w / 2 - 2, Y - 2, w + 4, h + 4);
    g.fillStyle = 'rgba(232,197,90,.20)'; g.fillRect(X - w / 2, Y, w, h);
    g.fillStyle = 'rgba(232,197,90,.95)'; g.fillRect(X - w / 2, Y, w * Math.max(0, Math.min(1, frac)), h);
    g.fillStyle = '#e8e8e8'; g.font = '700 9px Inter,sans-serif'; g.textAlign = 'center';
    g.fillText(label, X, Y - 5);
    g.restore();
  }
  function drawWorkerDog(g, X, Y, working, clock, art) {          // the dispatched dog = a REAL deck card (its portrait); procedural fallback if art not ready / headless
    g.save();
    g.fillStyle = 'rgba(0,0,0,.32)'; g.beginPath(); g.ellipse(X, Y + 9, 10, 3.5, 0, 0, 7); g.fill();
    var bob = working && !WV.reduce ? Math.abs(Math.sin(clock * 8)) * 2.2 : 0, cy = Y - bob, R = 11;
    var im = art ? spriteImg(art) : null;
    if (spriteReady(im)) {                                        // AK-DECKCARD: the actual card portrait, clipped to the token + gold ring
      g.save(); g.beginPath(); g.arc(X, cy, R, 0, 7); g.closePath(); g.clip();
      g.drawImage(im, X - R, cy - R - 2, R * 2, R * 2 + 5); g.restore();
      g.strokeStyle = '#e8c55a'; g.lineWidth = 2; g.beginPath(); g.arc(X, cy, R, 0, 7); g.stroke();
    } else {                                                      // procedural fallback (art still loading / headless / no art)
      g.fillStyle = '#caa64a'; g.beginPath(); g.arc(X, cy, 8, 0, 7); g.fill();
      g.fillStyle = '#15110a';
      g.beginPath(); g.moveTo(X - 7, cy - 5); g.lineTo(X - 9, cy - 11); g.lineTo(X - 3, cy - 7); g.closePath(); g.fill();
      g.beginPath(); g.moveTo(X + 7, cy - 5); g.lineTo(X + 9, cy - 11); g.lineTo(X + 3, cy - 7); g.closePath(); g.fill();
      g.strokeStyle = '#e8c55a'; g.lineWidth = 1.6; g.beginPath(); g.arc(X, cy, 8, 0, 7); g.stroke();
      g.fillStyle = '#15110a'; g.beginPath(); g.arc(X - 3, cy - 1, 1.4, 0, 7); g.arc(X + 3, cy - 1, 1.4, 0, 7); g.fill();
    }
    if (working) { g.strokeStyle = 'rgba(232,197,90,.65)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X + R - 1, cy + 2); g.lineTo(X + R + 4, cy + 5 - bob); g.stroke(); }
    g.restore();
  }

  /* ====================================================================== *
   * (6c) UPGRADE BUILDER DOG -- the VISIBLE worker for a BUILDING upgrade.
   *   index.html akOpenUpgrade pushes one here the instant an upgrade starts;
   *   the SAME deck-card dog trots out from the nearest hut to the building,
   *   WORKS there for the build duration, then trots home. Purely COSMETIC --
   *   the upgrade itself (and its builder-slot accounting via AK_ECON.buildersBusy
   *   on p.prod) is owned by index.html; this only renders the dog so an upgrade
   *   in flight LOOKS like a dog on the job (mirrors the harvest dispatch visual).
   *   Session-only (a reload keeps the upgrade but drops the cosmetic dog).
   * ====================================================================== */
  function showUpgradeDog(zid, x, y, durSec, art, name) {
    if (!zid) return false;
    var now = Date.now(), work = Math.max(0.5, +durSec || 0.5);
    var hut = (WV.ctx ? nearestHut(WV.ctx) : { x: +x || 0, y: (+y || 0) + 60 });
    var nx = +x || 0, ny = (+y || 0) + 14;                                              // work spot = building door (slightly below centre)
    WV.upDogs = WV.upDogs.filter(function (d) { return !(d.zid === zid && d.nx === nx && d.ny === ny); });   // one dog per building (re-upgrade replaces)
    WV.upDogs.push({ zid: zid, nx: nx, ny: ny, hx: hut.x, hy: hut.y, t0: now, work: work, until: now + work * 1000, art: art || null, name: name || 'Builder' });
    return true;
  }
  function clearUpgradeDog(zid, x, y) {
    var nx = +x || 0, ny = (+y || 0) + 14;
    WV.upDogs = WV.upDogs.filter(function (d) { return !(d.zid === zid && d.nx === nx && d.ny === ny); });
  }
  function tickUpDogs() {
    if (!WV.upDogs.length) return;
    var now = Date.now(), keep = [];
    for (var i = 0; i < WV.upDogs.length; i++) {
      var d = WV.upDogs[i];
      if ((now - d.t0) / 1000 < WALK_OUT + d.work + WALK_BACK) keep.push(d);            // out -> work -> back, then despawn
    }
    WV.upDogs = keep;
  }

  /* ====================================================================== *
   * (7) PUBLIC NODE QUERIES   (AK-HARVESTAPI 2026-07-18)
   *   worldverbs owns the harvestable nodes -- their types, yields, tool gates,
   *   respawn clocks, labels and art. It is the ONLY node table; a second one
   *   drifts by definition (they disagreed about what a tree costs to work the
   *   day the second one was written). These are the read seams any other system
   *   needs so nobody has to stand one up again: resolve a district by OBJECT or
   *   by bare id, look a node up by key, find the nearest ripe one to any point,
   *   ask when a type grows back. All read-only -- the only way to bank a yield
   *   is harvest()/harvestInfo(), which always re-reads ripeness from p.nodes.
   * ====================================================================== */
  function zoneRef(z) {
    if (!z) return (WV.ctx && WV.ctx.activeZone) || null;    // no arg = the district you are standing in
    if (typeof z !== 'string') return z;
    var Z = WV.ctx && WV.ctx.ZONES;                          // the hub ctx carries the district table
    return (Z && Z[z]) || null;                              // unknown id -> null (genZone needs the REAL zone to place legally)
  }
  // nearest RIPE node to a world point. Depleted nodes are not "near" -- they are
  // gone until they regrow. Same strict < HARVEST_RANGE test updatePrompt uses.
  function nodeNear(zone, x, y, range) {
    var z = zoneRef(zone); if (!z) return null;
    var ns = genZone(z), zid = z.id, now = Date.now();
    var rng = (range == null ? HARVEST_RANGE : range), best = null, bd = rng;
    for (var i = 0; i < ns.length; i++) {
      var n = ns[i];
      if (!isRipe(now, entryOf(zid, n.key))) continue;
      var d = Math.hypot(x - n.x, y - n.y);
      if (d < bd) { bd = d; best = n; }
    }
    return best;
  }
  function resetNodes(zid) {                                 // test / debug seam: force regrow (every district when zid is omitted)
    if (!WV.ctx || !WV.ctx.econ) return false;
    WV.ctx.econ.mutateProfile(function (pp) {
      if (!pp.nodes) return;
      if (zid) delete pp.nodes[zid]; else pp.nodes = {};
    });
    bump();
    return true;
  }

  /* ====================================================================== *
   * REGISTER
   * ====================================================================== */
  global.AK_SYSTEMS.register({
    id: 'worldverbs',
    init: function (ctx) {
      WV.ctx = ctx;
      coll = global.AK_COLLISION || null;
      try { WV.reduce = (typeof matchMedia !== 'undefined') && matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (_r) {}
      try { loadJobs(); } catch (_lj) {}                          // AK-DISPATCH: rehydrate in-flight builder jobs (walk-away survives reload)
      try { mountButton(); } catch (_e) {}
    },
    onTick: function (dt, ctx) {
      WV.clock += dt;
      WV.sweepT += dt;
      if (WV.channel) { try { advanceChannel(ctx, dt); } catch (_e0) {} }
      try { tickJobs(ctx); } catch (_ej) {}                       // AK-DISPATCH: advance dispatched-builder harvests + bank on completion
      try { tickUpDogs(); } catch (_eu) {}                        // AK-UPGRADEDOG: despawn building-upgrade dogs once they've trotted home
      try { tickDrops(ctx); } catch (_ed) {}                      // AK-DROPS: collect manual-harvest drops on walk-over + despawn stale ones
      if (WV.sweepT >= 1.5) { WV.sweepT = 0; try { sweepExpired(ctx); } catch (_e) {} }
      try { updatePrompt(ctx); } catch (_e2) {}
    },
    onDrawWorld: function (ctx) {
      var g = ctx.world.g; if (!g) return;
      var nodes = genZone(ctx.activeZone), zid = ctx.zoneId;
      var W = ctx.world.W, H = ctx.world.H, now = Date.now();
      var chKey = (WV.channel && WV.channel.zid === zid) ? WV.channel.key : null;
      var chFrac = chKey ? channelFrac() : 0;
      for (var i = 0; i < nodes.length; i++) {
        var nd = nodes[i], X = ctx.world.wx(nd.x), Y = ctx.world.wy(nd.y);
        if (X < -50 || X > W + 50 || Y < -60 || Y > H + 60) continue;   // cull
        var e = entryOf(zid, nd.key), ripe = isRipe(now, e), def = NODE_TYPES[nd.type];
        drawNode(g, X, Y, def, stageOf(now, e), ripe && nd.key !== chKey, WV.clock);
        if (nd.key === chKey) drawChannelArc(g, X, Y, chFrac, def.big || 1);
      }
      // AK-DROPS: manual-harvest ground drops -- walk over them to bank (collected in onTick)
      for (var di = 0; di < WV.drops.length; di++) {
        var dr = WV.drops[di]; if (dr.zid !== zid) continue;
        var DX = ctx.world.wx(dr.x), DY = ctx.world.wy(dr.y);
        if (DX < -40 || DX > W + 40 || DY < -50 || DY > H + 50) continue;   // cull
        drawDrop(g, DX, DY, NODE_TYPES[dr.type] || {}, WV.clock);
      }
      // AK-DISPATCH: dispatched-builder visuals -- the trotting dog + a countdown timer bar over the worked node
      for (var ji = 0; ji < WV.jobs.length; ji++) {
        var j = WV.jobs[ji]; if (j.zid !== zid) continue;
        var ph = jobPhase(j, now), NX = ctx.world.wx(j.nx), NY = ctx.world.wy(j.ny);
        if (ph.p === 'out') { drawTimerBar(g, NX, NY - 42, 0, 'INCOMING'); }
        else if (ph.p === 'work') { drawTimerBar(g, NX, NY - 42, ph.t, Math.max(0, Math.ceil(j.work * (1 - ph.t))) + 's'); }
        var BX = ctx.world.wx(j.bx), BY = ctx.world.wy(j.by);
        if (BX > -30 && BX < W + 30 && BY > -40 && BY < H + 40) drawWorkerDog(g, BX, BY, ph.p === 'work', WV.clock, j.art);
      }
      // AK-UPGRADEDOG: the VISIBLE dog working a BUILDING upgrade -- trot out, work at the building, trot home (cosmetic mirror of the harvest dispatch dog)
      for (var ui = 0; ui < WV.upDogs.length; ui++) {
        var ud = WV.upDogs[ui]; if (ud.zid !== zid) continue;
        var uel = (now - ud.t0) / 1000, uph, ut, ubx, uby;
        if (uel < WALK_OUT) { uph = 'out'; ut = WALK_OUT ? uel / WALK_OUT : 1; ubx = ud.hx + (ud.nx - ud.hx) * ut; uby = ud.hy + (ud.ny - ud.hy) * ut; }
        else if (uel < WALK_OUT + ud.work) { uph = 'work'; ubx = ud.nx; uby = ud.ny; }
        else { uph = 'back'; ut = WALK_BACK ? (uel - WALK_OUT - ud.work) / WALK_BACK : 1; ubx = ud.nx + (ud.hx - ud.nx) * ut; uby = ud.ny + (ud.hy - ud.ny) * ut; }
        var UNX = ctx.world.wx(ud.nx), UNY = ctx.world.wy(ud.ny);
        if (uph === 'out') { drawTimerBar(g, UNX, UNY - 46, 0, 'BUILDING'); }
        else if (uph === 'work') { var urem = Math.max(0, Math.ceil((ud.until - now) / 1000)); drawTimerBar(g, UNX, UNY - 46, ud.work ? (uel - WALK_OUT) / ud.work : 1, urem + 's'); }
        var UBX = ctx.world.wx(ubx), UBY = ctx.world.wy(uby);
        if (UBX > -30 && UBX < W + 30 && UBY > -40 && UBY < H + 40) drawWorkerDog(g, UBX, UBY, uph === 'work', WV.clock, ud.art);
      }
    }
  });

  // public API (host buttons + verification harness)
  global.AK_WORLDVERBS = {
    NODE_TYPES: NODE_TYPES,
    PATTERN: PATTERN,
    TOOL_TIERS: TOOL_TIERS_MIRROR,                   // mirror; canonical = AK_ECON.TOOL_TIERS
    nodes: function () { return WV.ctx ? genZone(WV.ctx.activeZone).slice() : []; },
    nodesForZone: function (zone) { return genZone(zone); },
    // --- AK-HARVESTAPI 2026-07-18: the single-source-of-truth node API. Takes a zone
    // OBJECT or a bare district id; omit it entirely for the district you are in. ---
    RANGE: HARVEST_RANGE,
    nodesFor: function (zone) { var z = zoneRef(zone); return z ? genZone(z) : []; },
    nodeAt: function (zone, key) { var z = zoneRef(zone); return z ? nodeByKey(z, key) : null; },
    nodeNear: function (zone, x, y, range) { return nodeNear(zone, x, y, range); },
    isReadyIn: function (zone, key) { var z = zoneRef(zone); return z ? isRipe(Date.now(), entryOf(z.id, key)) : true; },
    respawnMs: function (type) { var d = NODE_TYPES[type]; return d ? d.dur : 0; },
    resetNodes: resetNodes,
    // structured harvest: {ok,error,material,amount,banked,overflow,gold,respawnMs,...}
    // so a caller can tell NEED_TOOL from NOT_READY from a real haul. Same gate, same
    // yield math, same respawn write as harvest() -- it IS harvest(), just reported.
    harvestInfo: function (key, opts) { WV.last = null; doHarvest(WV.ctx, key, opts); return WV.last; },   // no ctx -> doHarvest records NO_CTX
    lastHarvest: function () { return WV.last; },
    startChannel: function (key) { return WV.ctx ? startChannel(WV.ctx, key) : false; },
    cancelChannel: function () { cancelChannel(WV.ctx); },
    channel: function () { return WV.channel ? { key: WV.channel.key, frac: channelFrac(), dur: WV.channel.dur, elapsed: WV.channel.elapsed } : null; },
    effChannelSec: function (key) { var n = WV.ctx ? nodeByKey(WV.ctx.activeZone, key) : null; return n ? effChannelSec(WV.ctx, n) : 0; },
    harvest: function (key, opts) { return WV.ctx ? doHarvest(WV.ctx, key, opts) : false; },   // synchronous force-complete (default auto-bank; pass {drop:true} to drop)
    drops: function () { return WV.drops.slice(); },   // AK-DROPS: live ground drops awaiting walk-over collect
    toolFor: function (type) { return toolForP(freshProfile(), type); },
    isRipe: function (key) { return WV.ctx ? isRipe(Date.now(), entryOf(WV.ctx.zoneId, key)) : true; },
    stage: function (key) { return WV.ctx ? stageOf(Date.now(), entryOf(WV.ctx.zoneId, key)) : 3; },
    dispatch: function (key) { return WV.ctx ? dispatchBuilder(WV.ctx, key) : false; },   // AK-DISPATCH: send a builder dog (walk-away harvest)
    showUpgradeDog: showUpgradeDog,        // AK-UPGRADEDOG: (zid,x,y,durSec,art,name) -> spawn the VISIBLE building-upgrade dog (index.html calls this on upgrade start)
    clearUpgradeDog: clearUpgradeDog,      // (zid,x,y) -> remove an upgrade dog early (e.g. cancel)
    refresh: function () { bump(); },      // AK-BUILDERCAP: force the ver-cached profile to re-read (call after index.html mutates p.prod so the SEND DOG button reflects upgrade slots)
    builderCap: builderCapNow,
    freeBuilders: freeBuilders,
    jobs: function () { var now = Date.now(); return WV.jobs.map(function (j) { return { zid: j.zid, key: j.key, work: j.work, builder: j.bn, phase: jobPhase(j, now).p, banked: !!j.banked }; }); },
    mountButton: mountButton
  };

})(typeof window !== 'undefined' ? window : globalThis);
